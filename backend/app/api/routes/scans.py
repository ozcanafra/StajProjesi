from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_owned_target
from app.db.session import get_db
from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import AVAILABLE_MODULES, ScanCreate, ScanDetailOut, ScanOut

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


@router.get("/scans/{scan_id}", response_model=ScanDetailOut)
def get_scan(scan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Scan:
    scan = (
        db.query(Scan)
        .options(joinedload(Scan.findings), joinedload(Scan.report), joinedload(Scan.target))
        .filter(Scan.id == scan_id)
        .first()
    )
    if scan is None or scan.target.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan
