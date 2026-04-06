"""Flask application factory."""

import os
from typing import Any

from flask import Flask
from flask_cors import CORS

from dashboard.routes import categories_bp, projects_bp, tasks_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "..", ""),
        static_url_path="",
    )

    CORS(app)

    # Error handler for Pydantic validation errors
    from pydantic import ValidationError

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError) -> tuple[dict[str, Any], int]:
        """Return 422 for Pydantic validation errors."""
        return {"error": "Validation error", "details": e.errors()}, 422

    # Register API blueprints
    app.register_blueprint(categories_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)

    # Serve index.html at root
    @app.route("/")
    def index() -> Any:
        """Serve the dashboard."""
        return app.send_static_file("index.html")

    return app
