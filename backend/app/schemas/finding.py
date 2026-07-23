from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module: str
    severity: str
    title: str
    description: str
    evidence: dict
    created_at: datetime
