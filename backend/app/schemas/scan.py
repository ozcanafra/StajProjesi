from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.finding import FindingOut
from app.schemas.report import ReportOut

AVAILABLE_MODULES = ("recon", "headers_tls", "webvuln")


class ScanCreate(BaseModel):
    modules: list[str] = list(AVAILABLE_MODULES)


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    status: str
    modules: list[str]
    risk_score: float | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ScanDetailOut(ScanOut):
    findings: list[FindingOut] = []
    report: ReportOut | None = None


class ScanDiffOut(BaseModel):
    previous_scan_id: int | None
    previous_created_at: datetime | None
    risk_score_delta: float | None
    new_findings: list[FindingOut]
    resolved_findings: list[FindingOut]
    persisting_count: int
