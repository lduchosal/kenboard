"""Flask application factory."""

import os
from typing import Any

from flask import Flask
from flask_cors import CORS

from dashboard.routes import categories_bp, projects_bp, tasks_bp
from dashboard.routes.pages import bp as pages_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=root_dir,
        static_url_path="/static",
    )

    CORS(app)

    # Custom Jinja2 filter for JS string escaping in onclick attributes
    def jsesc(s: str) -> str:
        """Escape a string for use inside JS single-quoted strings."""
        return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    app.jinja_env.filters["jsesc"] = jsesc

    # Error handler for Pydantic validation errors
    from pydantic import ValidationError

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[dict[str, Any], int]:
        """Return 422 for Pydantic validation errors."""
        return {"error": "Validation error", "details": e.errors()}, 422

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)

    # Serve static assets (CSS, JS)
    @app.route("/style.css")
    def serve_css() -> Any:
        """Serve stylesheet."""
        return app.send_static_file("style.css")

    @app.route("/app.js")
    def serve_js() -> Any:
        """Serve JavaScript."""
        return app.send_static_file("app.js")

    return app
