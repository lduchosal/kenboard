"""Category models."""

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Input model for creating a category."""

    name: str = Field(..., min_length=1, max_length=250)
    color: str = Field(..., max_length=50)


class CategoryUpdate(BaseModel):
    """Input model for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=250)
    color: str | None = Field(None, max_length=50)
    project_order: list[str] | None = None


class Category(BaseModel):
    """Full category model returned by the API."""

    id: str
    name: str
    color: str
    position: int
