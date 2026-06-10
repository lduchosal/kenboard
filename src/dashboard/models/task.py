"""Task models."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

# Reject HTML angle brackets in the title (defense-in-depth against
# stored XSS via task title — cf. ticket #51).
NO_ANGLE_BRACKETS = r"^[^<>]*$"

# tasks.description is MySQL TEXT — max 65,535 *bytes* in utf8mb4. Reject
# anything larger up front so an oversized body is a clean 422 instead of
# a pymysql DataError 1406 → HTTP 500 (#511). We count encoded bytes (not
# characters) because that is exactly what the column limit measures.
DESCRIPTION_MAX_BYTES = 65_535
# "dd.mm" short-form due date: at most 5 chars (e.g. "31.12").
_SHORT_DATE_MAX_LEN = 5


def _within_text_column(value: str) -> str:
    """Reject a description that would overflow the TEXT column (#511)."""
    if len(value.encode("utf-8")) > DESCRIPTION_MAX_BYTES:
        msg = f"description exceeds {DESCRIPTION_MAX_BYTES} bytes"
        raise ValueError(msg)
    return value


BoundedDescription = Annotated[str, AfterValidator(_within_text_column)]


# tasks.attachement is MySQL MEDIUMTEXT — max 16 MB *bytes* in utf8mb4.
# Stores the paintbrush extension's SVG annotation layer (#541, epic
# decision (b): annotations only, transparent). Reject anything larger
# up front for the same reason as ``description``.
ATTACHEMENT_MAX_BYTES = 16_777_215


def _within_mediumtext_column(value: str) -> str:
    """Reject an attachement that would overflow the MEDIUMTEXT column (#541)."""
    if len(value.encode("utf-8")) > ATTACHEMENT_MAX_BYTES:
        msg = f"attachement exceeds {ATTACHEMENT_MAX_BYTES} bytes"
        raise ValueError(msg)
    return value


BoundedAttachement = Annotated[str, AfterValidator(_within_mediumtext_column)]


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
        if "." in s and len(s) <= _SHORT_DATE_MAX_LEN:
            parts = s.split(".")
            day, month = int(parts[0]), int(parts[1])
            # Local date wanted: "dd.mm" input means the user's current
            # calendar year, not UTC's (#785).
            return date(date.today().year, month, day)  # noqa: DTZ011
        return date.fromisoformat(s)


class TaskCreate(_DueDateMixin, BaseModel):
    """Input model for creating a task."""

    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=250, pattern=NO_ANGLE_BRACKETS)
    description: BoundedDescription = ""
    attachement: BoundedAttachement | None = None
    status: Literal["todo", "doing", "review", "done"] = "todo"
    who: str = ""
    due_date: date | str | None = None


class TaskUpdate(_DueDateMixin, BaseModel):
    """Input model for updating a task."""

    project_id: str | None = None
    title: str | None = Field(
        None, min_length=1, max_length=250, pattern=NO_ANGLE_BRACKETS
    )
    description: BoundedDescription | None = None
    attachement: BoundedAttachement | None = None
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
    attachement: str | None = None
    status: str
    who: str
    due_date: date | None
    position: int
    created_at: datetime
    updated_at: datetime
