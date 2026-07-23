import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def generate_verification_token() -> str:
    return secrets.token_hex(16)


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    verification_token: Mapped[str] = mapped_column(String(64), default=generate_verification_token)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="targets")
    scans: Mapped[list["Scan"]] = relationship(back_populates="target", cascade="all, delete-orphan")
