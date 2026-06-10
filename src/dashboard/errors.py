"""Error handling — Pydantic 422s, friendly 500s and task auto-filing (#268, #517).

Split out of ``app.py`` (ken #806). ``register_error_handlers`` is wired by
``create_app``; everything else is internal plumbing.
"""

from __future__ import annotations

import secrets
import time
import traceback
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from flask import Flask, Request, jsonify, make_response, render_template, request
from flask.typing import ResponseReturnValue
from pydantic import ValidationError

from dashboard import db
from dashboard.config import Config
from dashboard.logging import get_logger

log = get_logger("app")

# Paths under this prefix get JSON error responses (vs HTML pages).
API_PATH_PREFIX = "/api/"

# Fields whose validation failures are surfaced verbatim to the user (#198).
_PASSWORD_FIELDS = {"password", "new_password", "old_password"}


def _safe_pydantic_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Make Pydantic's ``.errors()`` JSON-serializable.

    Pydantic 2 embeds the original exception under ``ctx.error`` for ``value_error``
    validators, which Flask's JSON provider refuses to serialize. We stringify the
    exception so debug responses stay useful without crashing.
    """
    cleaned: list[dict[str, Any]] = []
    for err in errors:
        err_copy: dict[str, Any] = dict(err)
        ctx = err_copy.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            err_copy["ctx"] = {**ctx, "error": str(ctx["error"])}
        cleaned.append(err_copy)
    return cleaned


def _extract_password_error(details: list[dict[str, Any]]) -> str | None:
    """Return a user-facing message when a password field failed validation.

    Our custom ``validate_password_strength`` raises ``ValueError`` whose message is
    already actionable (length requirement, zxcvbn score, zxcvbn feedback). We surface
    that instead of the generic "Validation error" so the UI modal can tell the user
    *why* the password was rejected (#198).
    """
    for err in details:
        loc = err.get("loc") or ()
        if not loc:
            continue
        field = loc[0] if isinstance(loc, (list, tuple)) else loc
        if field not in _PASSWORD_FIELDS:
            continue
        msg = err.get("msg", "")
        if not isinstance(msg, str):
            continue
        msg = msg.removeprefix("Value error, ")
        if msg and ("Password" in msg or err.get("type") == "value_error"):
            return msg
    return None


def _error_task_description(
    error_id: str, error_class: str, original: BaseException, route: str
) -> str:
    """Build the markdown body of an auto-filed 500 task (#517)."""
    tb = "".join(
        traceback.format_exception(type(original), original, original.__traceback__)
    )
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return (
        "## Erreur 500 auto-détectée (#517)\n\n"
        f"- **error_id:** {error_id}\n"
        f"- **Route:** {request.method} {request.path} (rule: {route})\n"
        f"- **Type:** {error_class}\n"
        f"- **Message:** {original}\n"
        f"- **Quand:** {now}\n\n"
        "### Traceback\n\n```\n" + tb + "\n```\n\n"
        "### À faire\n\n"
        "- [ ] Reproduire\n"
        "- [ ] Écrire un test de non-régression\n"
        "- [ ] Corriger\n"
    )[:60000]


def _autocreate_error_task(
    error_id: str, error_class: str, original: BaseException, route: str
) -> None:
    """Best-effort: file an unhandled 500 as a BUG task on the configured board.

    Off unless ``KENBOARD_ERROR_PROJECT_ID`` is set (#517). Inserts directly via the
    query layer (no self-HTTP → no auth juggling or recursion) and dedups on an open
    task with the same signature so a recurring error doesn't spam the board. Never
    raises — a failure here must not mask the 500 already being returned to the caller.
    """
    project_id = Config.KENBOARD_ERROR_PROJECT_ID
    if not project_id:
        return
    # Anti-loop: a failure on the task-create path must not try to create a task.
    if request.path.startswith("/api/v1/tasks"):
        return
    try:
        title = f"BUG / 500 {error_class} @ {route}"[:250]
        conn = db.get_connection()
        queries = db.load_queries()
        try:
            if queries.task_find_open_by_title(
                conn, project_id=project_id, title=title
            ):
                return  # already filed and still open — don't duplicate
            description = _error_task_description(
                error_id, error_class, original, route
            )
            max_pos = queries.task_max_position(
                conn, project_id=project_id, status="todo"
            )
            queries.task_create(
                conn,
                project_id=project_id,
                title=title,
                description=description,
                attachement=None,
                status="todo",
                who=Config.KENBOARD_ERROR_WHO,
                due_date=None,
                position=max_pos + 1,
            )
            log.info("autocreate_error_task", error_id=error_id, project_id=project_id)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — ne pas re-crasher le handler 500
        log.warning("autocreate_error_task_failed", error_id=error_id, exc_info=True)


def _wants_json(req: Request) -> bool:
    """Return True when the caller looks like an API/XHR consumer."""
    if req.path.startswith(API_PATH_PREFIX):
        return True
    accept = req.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def _register_validation_handler(app: Flask, *, debug: bool) -> None:
    """Register the 422 handler for Pydantic validation errors."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> ResponseReturnValue:
        """Return 422 for Pydantic validation errors."""
        details = _safe_pydantic_errors(e.errors())
        log.warning("validation_error", path=request.path, errors=details)
        password_msg = _extract_password_error(details)
        if password_msg:
            body: dict[str, Any] = {"error": password_msg, "field": "password"}
            if debug:
                body["details"] = details
            return make_response(jsonify(body), 422)
        body = {"error": "Validation error"}
        if debug:
            body["details"] = details
        return make_response(jsonify(body), 422)


def _fatal_response(error_id: str, error_class: str) -> ResponseReturnValue:
    """500 body: JSON for API/XHR callers, friendly HTML page for browsers."""
    if _wants_json(request):
        return make_response(
            jsonify({"error": "Internal server error", "error_id": error_id}),
            500,
        )
    return make_response(
        render_template(
            "error_fatal.html",
            status_code=500,
            error_class=error_class,
            error_id=error_id,
        ),
        500,
    )


def _register_fatal_handler(app: Flask) -> None:
    """Register the friendly fatal-error handler for unhandled 500s (#268).

    Bound on the explicit HTTP 500 status (not on the generic ``Exception`` base class)
    so 4xx ``HTTPException`` subclasses keep their default rendering, and Sonar
    python:S5793 stays happy. Flask wraps any uncaught exception into an
    ``InternalServerError`` when ``PROPAGATE_EXCEPTIONS`` is False (the production
    default), and exposes the original exception via ``e.original_exception``.
    """

    @app.errorhandler(500)
    def handle_internal_server_error(e: Exception) -> ResponseReturnValue:
        """Friendly fatal-error response for unhandled 500s (#268).

        API callers (anything under ``/api/`` or asking for JSON) keep the existing
        JSON-shaped response so the client-side ``apiCall`` flow doesn't break. Browser
        callers get an HTML page with the HTTP code, the original exception class name,
        and a short reference id they can quote when reporting the problem to the
        administrator.
        """
        # Drill down to the underlying cause so logs and the rendered
        # ``Type`` field reflect e.g. ``OperationalError`` instead of the
        # generic Werkzeug ``InternalServerError`` wrapper.
        original = getattr(e, "original_exception", None) or e
        error_id = f"E-{int(time.time()):x}-{secrets.token_hex(2)}"
        error_class = type(original).__name__
        log.error(
            "unhandled_error",
            path=request.path,
            error=str(original),
            error_class=error_class,
            error_id=error_id,
            exc_info=True,
        )
        # #517: best-effort — file this 500 as a task on the configured board.
        route = str(request.url_rule) if request.url_rule else request.path
        _autocreate_error_task(error_id, error_class, original, route)
        return _fatal_response(error_id, error_class)


def register_error_handlers(app: Flask, *, debug: bool) -> None:
    """Register Pydantic validation and generic error handlers."""
    _register_validation_handler(app, debug=debug)
    _register_fatal_handler(app)
