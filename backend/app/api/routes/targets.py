import dns.resolver
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_target
from app.core.config import settings
from app.db.session import get_db
from app.models.target import Target
from app.models.user import User
from app.schemas.target import TargetCreate, TargetOut, TargetVerifyInstructions

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
def create_target(
    payload: TargetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Target:
    domain = payload.domain.strip().lower()
    target = Target(owner_id=current_user.id, domain=domain)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("", response_model=list[TargetOut])
def list_targets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Target]:
    return db.query(Target).filter(Target.owner_id == current_user.id).order_by(Target.created_at.desc()).all()


@router.get("/{target_id}", response_model=TargetOut)
def get_target(
    target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Target:
    return get_owned_target(target_id, db, current_user)


@router.get("/{target_id}/verify-instructions", response_model=TargetVerifyInstructions)
def verify_instructions(
    target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> TargetVerifyInstructions:
    target = get_owned_target(target_id, db, current_user)
    record_name = f"{settings.VERIFICATION_TXT_PREFIX}.{target.domain}"
    return TargetVerifyInstructions(
        record_name=record_name,
        record_value=target.verification_token,
        instructions=(
            f"DNS ayarlarinizda '{record_name}' adiyla bir TXT kaydi olusturup "
            f"degerini '{target.verification_token}' olarak ayarlayin, sonra /verify ucunu cagirin."
        ),
    )


@router.post("/{target_id}/verify", response_model=TargetOut)
def verify_target(
    target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Target:
    target = get_owned_target(target_id, db, current_user)

    if not settings.SKIP_TARGET_VERIFICATION:
        record_name = f"{settings.VERIFICATION_TXT_PREFIX}.{target.domain}"
        try:
            answers = dns.resolver.resolve(record_name, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"TXT kaydi bulunamadi veya sorgulanamadi: {exc}",
            ) from exc

        found = any(target.verification_token in b.decode() for rdata in answers for b in rdata.strings)
        if not found:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dogrulama token'i eslesmedi")

    target.is_verified = True
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(
    target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    target = get_owned_target(target_id, db, current_user)
    db.delete(target)
    db.commit()
