from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), unique=True, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    technical_summary: Mapped[str] = mapped_column(Text, default="")
    prioritized_findings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan: Mapped["Scan"] = relationship(back_populates="report")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
