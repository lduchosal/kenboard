"""Flask route blueprints."""

from dashboard.routes.categories import bp as categories_bp
from dashboard.routes.projects import bp as projects_bp
from dashboard.routes.tasks import bp as tasks_bp

__all__ = ["categories_bp", "projects_bp", "tasks_bp"]
