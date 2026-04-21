"""Flask application factory."""

import os
import time
from typing import Any

from flask import Flask, request
from flask_cors import CORS

from dashboard.auth import init_auth
from dashboard.auth_oidc import init_oidc
from dashboard.auth_user import init_login_manager
from dashboard.config import Config
from dashboard.email import init_email
from dashboard.logging import get_logger, setup_logging
from dashboard.perf import init_perf
from dashboard.routes import (
    categories_bp,
    keys_bp,
    projects_bp,
    tasks_bp,
    users_bp,
)
from dashboard.routes.pages import bp as pages_bp

log = get_logger("app")


# -- Helper: security & proxy ------------------------------------------------


def _configure_security(app: Flask) -> None:
    """Set up reverse-proxy trust, CORS, and hardening response headers."""
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[assignment]

    if Config.KENBOARD_CORS_ORIGINS:
        CORS(app, origins=Config.KENBOARD_CORS_ORIGINS, supports_credentials=True)

    @app.after_request
    def security_headers(response: Any) -> Any:
        """Apply hardening HTTP headers to every response."""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        response.headers["Server"] = "kenboard"
        return response


# -- Helper: request logging --------------------------------------------------


def _register_request_logging(app: Flask) -> None:
    """Register before/after request hooks for API request logging."""

    @app.before_request
    def log_request() -> None:
        """Log incoming request."""
        request._start_time = time.time()  # type: ignore[attr-defined]
        if request.path.startswith("/api/"):
            log.debug(
                "request",
                method=request.method,
                path=request.path,
                body=request.get_json(silent=True),
            )

    @app.after_request
    def log_response(response: Any) -> Any:
        """Log outgoing response."""
        if request.path.startswith("/api/"):
            duration = time.time() - getattr(request, "_start_time", time.time())
            log.info(
                "response",
                method=request.method,
                path=request.path,
                status=response.status_code,
                duration_ms=round(duration * 1000),
            )
        return response


# -- Helper: error handlers ---------------------------------------------------

_PASSWORD_FIELDS = {"password", "new_password", "old_password"}


def _safe_pydantic_errors(errors: Any) -> list[dict[str, Any]]:
    """Make Pydantic's ``.errors()`` JSON-serializable.

    Pydantic 2 embeds the original exception under ``ctx.error`` for
    ``value_error`` validators, which Flask's JSON provider refuses to
    serialize. We stringify the exception so debug responses stay
    useful without crashing.
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

    Our custom ``validate_password_strength`` raises ``ValueError`` whose
    message is already actionable (length requirement, zxcvbn score,
    zxcvbn feedback). We surface that instead of the generic "Validation
    error" so the UI modal can tell the user *why* the password was
    rejected (#198).
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


def _register_error_handlers(app: Flask, debug: bool) -> None:
    """Register Pydantic validation and generic error handlers."""
    from pydantic import ValidationError
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[dict[str, Any], int]:
        """Return 422 for Pydantic validation errors."""
        details = _safe_pydantic_errors(e.errors())
        log.warning("validation_error", path=request.path, errors=details)
        password_msg = _extract_password_error(details)
        if password_msg:
            body: dict[str, Any] = {"error": password_msg, "field": "password"}
            if debug:
                body["details"] = details
            return body, 422
        if debug:
            return {"error": "Validation error", "details": details}, 422
        return {"error": "Validation error"}, 422

    @app.errorhandler(Exception)
    def handle_error(e: Exception) -> Any:
        """Log and return 500 for unhandled exceptions."""
        if isinstance(e, HTTPException):
            return e
        log.error("unhandled_error", path=request.path, error=str(e), exc_info=True)
        return {"error": "Internal server error"}, 500


# -- Helper: static routes & blueprints --------------------------------------


def _register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints."""
    from dashboard.onboarding import onboard_bp

    app.register_blueprint(onboard_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(keys_bp)


def _register_static_routes(app: Flask) -> None:
    """Register convenience routes that serve static assets at root URLs."""

    @app.route("/style.css", methods=["GET"])
    def serve_css() -> Any:
        """Serve stylesheet from root URL."""
        return app.send_static_file("style.css")

    @app.route("/app.js", methods=["GET"])
    def serve_js() -> Any:
        """Serve JavaScript from root URL."""
        return app.send_static_file("app.js")

    @app.route("/sortable.min.js", methods=["GET"])
    def serve_sortable() -> Any:
        """Serve vendored Sortable.js from root URL."""
        return app.send_static_file("sortable.min.js")

    @app.route("/marked.min.js", methods=["GET"])
    def serve_marked() -> Any:
        """Serve vendored marked.js from root URL."""
        return app.send_static_file("marked.min.js")

    @app.route("/dompurify.min.js", methods=["GET"])
    def serve_dompurify() -> Any:
        """Serve vendored DOMPurify from root URL."""
        return app.send_static_file("dompurify.min.js")

    @app.route("/favicon.ico", methods=["GET"])
    def favicon() -> Any:
        """Return empty favicon."""
        return "", 204


# -- Factory ------------------------------------------------------------------


def create_app() -> Flask:
    """Create and configure the Flask application.

    Raises:
        RuntimeError: when ``LOGIN_DISABLED`` is set on the app config
            while ``DEBUG`` is off (#199 defense-in-depth).
    """
    debug = os.getenv("DEBUG", "false").lower() == "true"
    setup_logging(debug=debug)

    # CSRF strategy (cf. sonar python:S4502): kenboard does not use
    # Flask-WTF CSRFProtect. Cookie-authenticated unsafe requests are
    # protected by an Origin/Referer same-host check in the API auth
    # middleware (see ``dashboard.auth._enforce_cookie_session`` and
    # ``dashboard.auth._origin_matches_host``). Bearer-token requests
    # do not need CSRF protection because the token is never sent
    # automatically by the browser. Both flows are covered by
    # ``tests/unit/test_csrf.py``.
    app = Flask(  # NOSONAR — CSRF via Origin/Referer check in auth.py, not Flask-WTF
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/static",
    )

    _configure_security(app)

    # Custom Jinja2 filter for JS string escaping in onclick attributes
    def jsesc(s: str) -> str:
        """Escape a string for use inside JS single-quoted strings."""
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    app.jinja_env.filters["jsesc"] = jsesc

    # Initialization order matters: login manager → OIDC → email → perf → auth
    init_login_manager(app)
    init_oidc(app)
    init_email(app)
    init_perf(app)
    init_auth(app)

    _register_request_logging(app)
    _register_error_handlers(app, debug)
    _register_blueprints(app)
    _register_static_routes(app)

    # #199 defense-in-depth
    if app.config.get("LOGIN_DISABLED") and not debug and not app.config.get("TESTING"):
        raise RuntimeError(
            "LOGIN_DISABLED=True is set but DEBUG=False. This would bypass "
            "authentication in production. Refusing to start. Remove "
            "LOGIN_DISABLED from your config or set DEBUG=True (dev/test only)."
        )

    log.info("app_started", debug=debug)
    return app
