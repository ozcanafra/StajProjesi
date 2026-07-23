from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_owned_target
from app.db.session import get_db
from app.models.scan import STATUS_COMPLETED, Scan
from app.models.user import User
from app.schemas.scan import AVAILABLE_MODULES, ScanCreate, ScanDetailOut, ScanDiffOut, ScanOut
from app.services.diff import compute_diff
from app.services.pdf_report import build_report_pdf

router = APIRouter(prefix="/api", tags=["scans"])


@router.post("/targets/{target_id}/scans", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
def create_scan(
    target_id: int,
    payload: ScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scan:
    target = get_owned_target(target_id, db, current_user)
    if not target.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tarama baslatmadan once hedef domain sahiplik dogrulamasini tamamlamalisiniz",
        )

    modules = [m for m in payload.modules if m in AVAILABLE_MODULES]
    if not modules:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gecerli en az bir modul secmelisiniz")

    scan = Scan(target_id=target.id, modules=modules)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    from app.tasks.scan_tasks import run_scan_task

    run_scan_task.delay(scan.id)

    return scan


@router.get("/targets/{target_id}/scans", response_model=list[ScanOut])
def list_scans(
    target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Scan]:
    target = get_owned_target(target_id, db, current_user)
    return db.query(Scan).filter(Scan.target_id == target.id).order_by(Scan.created_at.desc()).all()


def _get_owned_scan(scan_id: int, db: Session, current_user: User) -> Scan:
    scan = (
        db.query(Scan)
        .options(joinedload(Scan.findings), joinedload(Scan.report), joinedload(Scan.target))
        .filter(Scan.id == scan_id)
        .first()
    )
    if scan is None or scan.target.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


@router.get("/scans/{scan_id}", response_model=ScanDetailOut)
def get_scan(scan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Scan:
    return _get_owned_scan(scan_id, db, current_user)


@router.get("/scans/{scan_id}/diff", response_model=ScanDiffOut)
def get_scan_diff(
    scan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ScanDiffOut:
    scan = _get_owned_scan(scan_id, db, current_user)

    previous = (
        db.query(Scan)
        .options(joinedload(Scan.findings))
        .filter(
            Scan.target_id == scan.target_id,
            Scan.status == STATUS_COMPLETED,
            Scan.id != scan.id,
            Scan.created_at < scan.created_at,
        )
        .order_by(Scan.created_at.desc())
        .first()
    )

    if previous is None:
        return ScanDiffOut(
            previous_scan_id=None,
            previous_created_at=None,
            risk_score_delta=None,
            new_findings=[],
            resolved_findings=[],
            persisting_count=0,
        )

    diff = compute_diff(scan.findings, previous.findings)
    risk_delta = None
    if scan.risk_score is not None and previous.risk_score is not None:
        risk_delta = scan.risk_score - previous.risk_score

    return ScanDiffOut(
        previous_scan_id=previous.id,
        previous_created_at=previous.created_at,
        risk_score_delta=risk_delta,
        new_findings=diff["new"],
        resolved_findings=diff["resolved"],
        persisting_count=len(diff["persisting"]),
    )


@router.get("/scans/{scan_id}/report.pdf")
def download_report_pdf(
    scan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Response:
    scan = _get_owned_scan(scan_id, db, current_user)
    if scan.report is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu tarama icin henuz bir rapor yok")

    pdf_bytes = build_report_pdf(scan.target.domain, scan, scan.report, scan.findings)
    filename = f"sentrascan-{scan.target.domain}-{scan.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
