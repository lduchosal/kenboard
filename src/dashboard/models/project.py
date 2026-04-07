"""Project models."""

from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Input model for creating a project."""

    name: str = Field(..., min_length=1, max_length=250)
    acronym: str = Field(..., min_length=1, max_length=4)
    cat: str = Field(..., min_length=1)
    status: Literal["active", "archived"] = "active"
    default_who: str = Field("", max_length=100)


class ProjectUpdate(BaseModel):
    """Input model for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=250)
    acronym: str | None = Field(None, min_length=1, max_length=4)
    cat: str | None = None
    status: Literal["active", "archived"] | None = None
    default_who: str | None = Field(None, max_length=100)
    project_order: list[str] | None = None


class Project(BaseModel):
    """Full project model returned by the API."""

    id: str
    cat_id: str
    name: str
    acronym: str
    status: str
    position: int
    default_who: str = ""
