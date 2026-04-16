"""User models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dashboard.password_strength import validate_password_strength

UserScope = Literal["read", "write"]


def _check_password_strength(v: str | None) -> str | None:
    """Run the shared strength policy on a password field (#198).

    ``None`` is passed through because several models accept an optional
    password (e.g. ``UserCreate`` lets admins create a user with no
    password, to be set later via ``kenboard set-password``).
    """
    if v is None or v == "":
        return v
    validate_password_strength(v)
    return v


class UserCreate(BaseModel):
    """Input model for creating a user."""

    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    color: str = Field(..., max_length=50)
    password: str | None = Field(None, max_length=200)
    is_admin: bool = False

    _validate_password = field_validator("password")(_check_password_strength)


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
    new_password: str = Field(..., max_length=200)

    _validate_new = field_validator("new_password")(_check_password_strength)


class PasswordReset(BaseModel):
    """Admin-only password reset.

    Does not require the old password.
    """

    new_password: str = Field(..., max_length=200)

    _validate_new = field_validator("new_password")(_check_password_strength)


class UserCategoryScope(BaseModel):
    """One (category_id, scope) entry attached to a user (#197).

    Mirrors :class:`dashboard.models.api_key.ApiKeyScope` but at the
    category level, because humans are granted access to whole boards
    while API keys stay scoped per-project.
    """

    category_id: str
    scope: UserScope


class UserScopeUpdate(BaseModel):
    """Input for ``PUT /api/v1/users/<id>/scopes``.

    The full scope list replaces the existing one atomically (clear + add in a
    transaction), mirroring how API-key scopes are updated.
    """

    scopes: list[UserCategoryScope] = Field(default_factory=list)


class User(BaseModel):
    """Public user model returned by the API (no password hash)."""

    id: str
    name: str
    email: str | None = None
    color: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    scopes: list[UserCategoryScope] = Field(default_factory=list)
