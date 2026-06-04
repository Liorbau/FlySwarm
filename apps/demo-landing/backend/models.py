from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr


class SignupRecord(BaseModel):
    email: EmailStr
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
