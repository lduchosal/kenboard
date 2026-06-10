"""Activity log helper (#261).

A thin wrapper around the ``activity_log!`` aiosql query that resolves the current user
identity (session, API key, or anonymous) and serialises the optional ``details``
payload to JSON for MySQL storage.

Called from each task route handler after the mutation has succeeded so failures don't
leave a phantom log row pointing at a non-existent target.
"""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any

from flask import g
from flask_login import current_user

ACTION_CREATE = "create"
ACTION_SAVE = "save"
ACTION_MOVE = "move"
ACTION_DELETE = "delete"


def _principal_name() -> str:
    """Best-effort label for the actor behind the current request.

    Cookie-session users contribute their name; API-key callers fall back to the
    principal string set by the auth middleware. Anonymous calls (tests with
    ``LOGIN_DISABLED``, unauthenticated reads) yield an empty string — the row still
    records the *what*, just not the *who*.
    """
    # Outside an app context (CLI snapshot, unit-test write through a raw
    # connection) the Flask-Login proxy resolves to None and accessing
    # ``is_authenticated`` raises AttributeError. Fall through to the
    # API-key principal in those cases, then to "" if even ``g`` isn't
    # bound (truly out-of-context).
    with suppress(RuntimeError, AttributeError):
        if current_user.is_authenticated:
            return getattr(current_user, "name", "") or ""
    with suppress(RuntimeError):
        return str(g.get("api_auth_principal") or "")
    return ""


def log_activity(  # noqa: PLR0913 — un kwarg par colonne d'activité, par design
    conn: Any,
    queries: Any,
    *,
    project_id: str,
    action: str,
    target_id: str | int,
    target_type: str = "task",
    details: dict[str, Any] | None = None,
) -> None:
    """Append one activity row.

    Failures here MUST not surface to the caller — the activity log is a best-effort
    observability channel, not a transactional invariant. We log + swallow so a
    malformed JSON or a brief table-lock does not roll back the user's actual mutation.
    """
    try:
        queries.activity_log(
            conn,
            project_id=project_id,
            user_name=_principal_name(),
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=json.dumps(details) if details is not None else None,
        )
    except Exception as e:  # noqa: BLE001
        # Don't let observability break the write path. Log so a failure
        # doesn't simply vanish during debugging.
        logging.getLogger(__name__).warning("log_activity failed: %s", e)
