"""Category models."""

from pydantic import BaseModel, Field

# Allow either a hex literal (#abc / #aabbcc) or a CSS variable
# reference (var(--name)). Anything else is rejected at validation
# time so the value can be safely interpolated into an inline
# ``style="background:..."`` attribute without CSS injection.
COLOR_PATTERN = r"^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^var\(--[a-z0-9-]+\)$"


class CategoryCreate(BaseModel):
    """Input model for creating a category."""

    name: str = Field(..., min_length=1, max_length=250)
    color: str = Field(..., max_length=50, pattern=COLOR_PATTERN)


class CategoryUpdate(BaseModel):
    """Input model for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=250)
    color: str | None = Field(None, max_length=50, pattern=COLOR_PATTERN)
    project_order: list[str] | None = None


class Category(BaseModel):
    """Full category model returned by the API."""

    id: str
    name: str
    color: str
    position: int
