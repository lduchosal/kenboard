"""User models."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Input model for creating a user."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., max_length=50)
    password: str | None = Field(None, min_length=1, max_length=200)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Input model for updating a user."""

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=50)
    password: str | None = Field(None, min_length=1, max_length=200)
    is_admin: bool | None = None


class User(BaseModel):
    """Public user model returned by the API (no password hash)."""

    id: str
    name: str
    color: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
