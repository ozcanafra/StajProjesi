from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_score: float
    executive_summary: str
    technical_summary: str
    prioritized_findings: list
    created_at: datetime


class ChatMessageIn(BaseModel):
    question: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime
