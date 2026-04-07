"""Flask application factory."""

import os
import time
from typing import Any

from flask import Flask, request
from flask_cors import CORS

from dashboard.auth import init_auth
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

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/static",
    )

    CORS(app)

    # API key auth middleware (no-op when KENBOARD_AUTH_ENFORCED=false)
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

    # Error handler for Pydantic validation errors
    from pydantic import ValidationError

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[dict[str, Any], int]:
        """Return 422 for Pydantic validation errors."""
        log.warning("validation_error", path=request.path, errors=e.errors())
        return {"error": "Validation error", "details": e.errors()}, 422

    @app.errorhandler(Exception)
    def handle_error(e: Exception) -> tuple[dict[str, str], int]:
        """Log and return 500 for unhandled exceptions."""
        log.error("unhandled_error", path=request.path, error=str(e), exc_info=True)
        return {"error": "Internal server error"}, 500

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(keys_bp)

    # Convenience routes for static assets at root
    @app.route("/style.css")
    def serve_css() -> Any:
        """Serve stylesheet from root URL."""
        return app.send_static_file("style.css")

    @app.route("/app.js")
    def serve_js() -> Any:
        """Serve JavaScript from root URL."""
        return app.send_static_file("app.js")

    @app.route("/sortable.min.js")
    def serve_sortable() -> Any:
        """Serve vendored Sortable.js from root URL."""
        return app.send_static_file("sortable.min.js")

    @app.route("/marked.min.js")
    def serve_marked() -> Any:
        """Serve vendored marked.js from root URL."""
        return app.send_static_file("marked.min.js")

    @app.route("/favicon.ico")
    def favicon() -> Any:
        """Return empty favicon."""
        return "", 204

    log.info("app_started", debug=debug)
    return app
