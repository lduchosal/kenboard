"""Flask application factory."""

import os
import time
from pathlib import Path

from flask import Flask, request
from flask.typing import ResponseReturnValue
from flask.wrappers import Response
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from dashboard.auth import init_auth
from dashboard.auth_oidc import init_oidc
from dashboard.auth_user import init_login_manager
from dashboard.config import Config
from dashboard.email import init_email
from dashboard.errors import API_PATH_PREFIX, register_error_handlers
from dashboard.logging import get_logger, setup_logging
from dashboard.onboarding import onboard_bp
from dashboard.perf import init_perf
from dashboard.routes import (
    categories_bp,
    keys_bp,
    projects_bp,
    tasks_bp,
    users_bp,
    wiki_bp,
)
from dashboard.routes.pages import bp as pages_bp

log = get_logger("app")

# Path prefix used to differentiate API/XHR clients (which expect JSON) from
# browser callers (which want HTML). Centralised so request-logging and the
# error-content-negotiation logic stay in lockstep.


# -- Helper: security & proxy ------------------------------------------------


def _configure_security(app: Flask) -> None:
    """Set up reverse-proxy trust, CORS, and hardening response headers."""
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[assignment]

    if Config.KENBOARD_CORS_ORIGINS:
        CORS(app, origins=Config.KENBOARD_CORS_ORIGINS, supports_credentials=True)

    @app.after_request
    def security_headers(response: Response) -> Response:
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
        request._start_time = time.time()  # type: ignore[attr-defined] # noqa: SLF001 — stash volontaire sur request
        if request.path.startswith(API_PATH_PREFIX):
            log.debug(
                "request",
                method=request.method,
                path=request.path,
                body=request.get_json(silent=True),
            )

    @app.after_request
    def log_response(response: Response) -> Response:
        """Log outgoing response."""
        if request.path.startswith(API_PATH_PREFIX):
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


def _register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints."""
    # Import-for-side-effect : attache les pages admin au blueprint pages
    # (#806). Local — admin_pages importe pages, top-level serait circulaire
    # via dashboard.routes.
    from dashboard.routes import admin_pages  # noqa: F401,PLC0415

    app.register_blueprint(onboard_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(keys_bp)
    app.register_blueprint(wiki_bp)


def _register_static_routes(app: Flask) -> None:
    """Register convenience routes that serve static assets at root URLs."""

    @app.route("/style.css", methods=["GET"])
    def serve_css() -> ResponseReturnValue:
        """Serve stylesheet from root URL."""
        return app.send_static_file("style.css")

    @app.route("/app.js", methods=["GET"])
    def serve_js() -> ResponseReturnValue:
        """Serve the Vite-bundled app from root URL (#251)."""
        return app.send_static_file("dist/app.js")

    @app.route("/app.js.map", methods=["GET"])
    def serve_js_map() -> ResponseReturnValue:
        """Serve the Vite source map so DevTools can debug the bundle."""
        return app.send_static_file("dist/app.js.map")

    @app.route("/sortable.min.js", methods=["GET"])
    def serve_sortable() -> ResponseReturnValue:
        """Serve vendored Sortable.js from root URL."""
        return app.send_static_file("sortable.min.js")

    @app.route("/marked.min.js", methods=["GET"])
    def serve_marked() -> ResponseReturnValue:
        """Serve vendored marked.js from root URL."""
        return app.send_static_file("marked.min.js")

    @app.route("/dompurify.min.js", methods=["GET"])
    def serve_dompurify() -> ResponseReturnValue:
        """Serve vendored DOMPurify from root URL."""
        return app.send_static_file("dompurify.min.js")

    @app.route("/favicon.ico", methods=["GET"])
    def favicon() -> ResponseReturnValue:
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
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
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
    register_error_handlers(app, debug=debug)
    _register_blueprints(app)
    _register_static_routes(app)

    # #199 defense-in-depth
    if app.config.get("LOGIN_DISABLED") and not debug and not app.config.get("TESTING"):
        msg = (
            "LOGIN_DISABLED=True is set but DEBUG=False. This would bypass "
            "authentication in production. Refusing to start. Remove "
            "LOGIN_DISABLED from your config or set DEBUG=True (dev/test only)."
        )
        raise RuntimeError(msg)

    log.info("app_started", debug=debug)
    return app
