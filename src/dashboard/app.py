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
from dashboard.logging import get_logger, setup_logging
from dashboard.routes import (
    categories_bp,
    keys_bp,
    projects_bp,
    tasks_bp,
    users_bp,
)
from dashboard.routes.pages import bp as pages_bp

log = get_logger("app")


def create_app() -> Flask:
    """Create and configure the Flask application."""
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

    # Trust the X-Forwarded-* headers set by the nginx reverse proxy so
    # that url_for(_external=True) generates https:// URLs (needed for
    # OIDC redirect_uri) and request.remote_addr reflects the real client
    # IP (needed for rate limiting). x_for=1 x_proto=1 x_host=1 means
    # "trust exactly one proxy hop" — matching the nginx → gunicorn setup
    # in INSTALL.md section 9.
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[assignment]

    # Only enable CORS when an explicit origin allow-list is configured.
    # No allow-list ⇒ browsers enforce same-origin (the secure default).
    if Config.KENBOARD_CORS_ORIGINS:
        CORS(
            app,
            origins=Config.KENBOARD_CORS_ORIGINS,
            supports_credentials=True,
        )

    # User session auth (Flask-Login). Must run before init_auth so that
    # the API middleware can detect a logged-in user via current_user.
    init_login_manager(app)

    # OIDC auth (optional, cf. auth_oidc.py). Silent no-op when the
    # OIDC_* env vars are not set. Registers /oidc/login + /oidc/callback.
    init_oidc(app)

    # API key auth middleware (always enforced; tests opt-out via LOGIN_DISABLED)
    init_auth(app)

    # Custom Jinja2 filter for JS string escaping in onclick attributes
    def jsesc(s: str) -> str:
        """Escape a string for use inside JS single-quoted strings."""
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    app.jinja_env.filters["jsesc"] = jsesc

    # Request logging
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

    @app.after_request
    def security_headers(response: Any) -> Any:
        """Apply hardening HTTP headers to every response.

        ``script-src`` and ``style-src`` keep ``'unsafe-inline'`` because
        the templates use inline ``onclick=`` handlers and ``style=``
        attributes throughout. The rest of the policy still blocks
        loading external scripts, framing (clickjacking), object/embed
        and ``<base>`` injection.

        HSTS is only set when the request is observed over HTTPS so the
        header isn't accidentally cached over plain HTTP in dev.
        """
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
        # Strip the Werkzeug/Python version fingerprint.
        response.headers["Server"] = "kenboard"
        return response

    # Error handler for Pydantic validation errors
    from pydantic import ValidationError
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[dict[str, Any], int]:
        """Return 422 for Pydantic validation errors."""
        log.warning("validation_error", path=request.path, errors=e.errors())
        if debug:
            return {"error": "Validation error", "details": e.errors()}, 422
        return {"error": "Validation error"}, 422

    @app.errorhandler(Exception)
    def handle_error(e: Exception) -> Any:
        """Log and return 500 for unhandled exceptions.

        HTTPException (abort 401/403/404/...) is left to Flask's default
        handling so the original status code propagates.
        """
        if isinstance(e, HTTPException):
            return e
        log.error("unhandled_error", path=request.path, error=str(e), exc_info=True)
        return {"error": "Internal server error"}, 500

    # Public onboarding route (no auth, returns 200 text/plain so
    # WebFetch and similar tools can read the body). Registered before
    # the auth middleware so it is never intercepted.
    from dashboard.onboarding import onboard_bp

    app.register_blueprint(onboard_bp)

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(keys_bp)

    # Convenience routes for static assets at root. ``methods=["GET"]`` is
    # spelled explicitly per Sonar python:S6965 — Flask defaults to GET only,
    # but the explicit form is clearer and prevents accidental method drift.
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

    log.info("app_started", debug=debug)
    return app
