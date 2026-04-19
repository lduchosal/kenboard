"""ApiKey models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Scope = Literal["read", "write", "admin"]


class ApiKeyScope(BaseModel):
    """A single (project_id, scope) pair attached to an api_key."""

    project_id: str = Field(..., min_length=1)
    scope: Scope


class ApiKeyCreate(BaseModel):
    """Input model for creating an api_key."""

    label: str = Field(..., min_length=1, max_length=100)
    expires_at: datetime | None = None
    user_id: str | None = Field(None, min_length=1, max_length=36)
    scopes: list[ApiKeyScope] = Field(default_factory=list)


class ApiKeyUpdate(BaseModel):
    """Input model for updating an api_key."""

    label: str | None = Field(None, min_length=1, max_length=100)
    expires_at: datetime | None = None
    user_id: str | None = Field(None, min_length=1, max_length=36)
    scopes: list[ApiKeyScope] | None = None


class ApiKey(BaseModel):
    """Public api_key model returned by the API (no key in clear, no hash)."""

    id: str
    user_id: str | None = None
    label: str
    expires_at: datetime | None
    last_used_at: datetime | None
    last_used_ip: str | None = None
    last_used_agent: str | None = None
    revoked_at: datetime | None
    created_at: datetime
    scopes: list[ApiKeyScope] = Field(default_factory=list)


class ApiKeyCreated(ApiKey):
    """Returned ONCE on creation, includes the plain text key."""

    key: str
