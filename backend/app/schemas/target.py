import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def normalize_domain(raw: str) -> str:
    """Strips a scheme (http://, https://), any path/query, and surrounding
    whitespace so users can paste a full URL and still get a clean hostname.
    Without this, e.g. 'https://example.com/' would be scanned as
    'https://https://example.com/' - always failing the same way regardless
    of target."""
    value = raw.strip()
    value = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", value)
    value = value.split("/", 1)[0]
    value = value.split("?", 1)[0]
    value = value.split("#", 1)[0]
    return value.strip().lower()


class TargetCreate(BaseModel):
    domain: str

    @field_validator("domain")
    @classmethod
    def _normalize_domain(cls, value: str) -> str:
        normalized = normalize_domain(value)
        if not normalized:
            raise ValueError("Gecerli bir domain girin")
        return normalized


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
