"""Task models."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class _DueDateMixin:
    """Mixin for parsing due_date from dd.mm or ISO format."""

    due_date: date | str | None

    def parsed_due_date(self) -> date | None:
        """Parse due_date from dd.mm or ISO format."""
        if self.due_date is None:
            return None
        if isinstance(self.due_date, date):
            return self.due_date
        s = str(self.due_date).strip()
        if not s:
            return None
        if "." in s and len(s) <= 5:
            parts = s.split(".")
            day, month = int(parts[0]), int(parts[1])
            return date(date.today().year, month, day)
        return date.fromisoformat(s)


class TaskCreate(_DueDateMixin, BaseModel):
    """Input model for creating a task."""

    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=250)
    description: str = ""
    status: Literal["todo", "doing", "review", "done"] = "todo"
    who: str = ""
    due_date: date | str | None = None


class TaskUpdate(_DueDateMixin, BaseModel):
    """Input model for updating a task."""

    project_id: str | None = None
    title: str | None = Field(None, min_length=1, max_length=250)
    description: str | None = None
    status: Literal["todo", "doing", "review", "done"] | None = None
    who: str | None = None
    due_date: date | str | None = None
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
