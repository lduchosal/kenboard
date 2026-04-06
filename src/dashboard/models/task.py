"""Task models."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Input model for creating a task."""

    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=250)
    description: str = ""
    status: Literal["todo", "doing", "review", "done"] = "todo"
    who: str = ""
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Input model for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=250)
    description: str | None = None
    status: Literal["todo", "doing", "review", "done"] | None = None
    who: str | None = None
    due_date: date | None = None
    position: int | None = None


class Task(BaseModel):
    """Full task model returned by the API."""

    id: int
    project_id: str
    title: str
    description: str
    status: str
    who: str
    due_date: date | None
    position: int
    created_at: datetime
    updated_at: datetime
