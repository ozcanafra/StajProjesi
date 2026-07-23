from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TargetCreate(BaseModel):
    domain: str


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: str
    is_verified: bool
    verification_token: str
    created_at: datetime


class TargetVerifyInstructions(BaseModel):
    record_name: str
    record_value: str
    instructions: str
