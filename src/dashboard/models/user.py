"""User models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Input model for creating a user."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., max_length=50)
    password: str | None = Field(None, min_length=1, max_length=200)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Input model for updating a user.

    Password changes are deliberately **not** part of this model since
    #53. Use ``POST /api/v1/users/<id>/password`` (self-service, requires
    the old password) or ``POST /api/v1/users/<id>/reset-password``
    (admin-only) instead. Extra fields are silently dropped so older
    clients that still send ``password`` here can't sneak it through.
    """

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=50)
    is_admin: bool | None = None


class PasswordChange(BaseModel):
    """Self-service password change.

    Owner-only, requires the old password.
    """

    old_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)


class PasswordReset(BaseModel):
    """Admin-only password reset.

    Does not require the old password.
    """

    new_password: str = Field(..., min_length=8, max_length=200)


class User(BaseModel):
    """Public user model returned by the API (no password hash)."""

    id: str
    name: str
    color: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
