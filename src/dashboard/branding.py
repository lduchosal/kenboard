"""Configurable branding: display name, logo and favicon (#1159).

Values come from ``Config.KENBOARD_*`` and are read at call time so tests (and a config
reload) can override them with ``monkeypatch.setattr(Config, ...)``.
"""

from flask import Flask

from dashboard.config import Config


def page_title(*parts: str) -> str:
    """Build a board page ``<title>``: the short name, then ``parts`` joined by `` / ``.

    Args:
        parts: trailing segments (page or category name), empty ones skipped.

    Returns:
        ``"<short>"`` alone, or ``"<short> / <part> / ..."``.
    """
    return " / ".join([Config.KENBOARD_SHORT_TITLE, *(p for p in parts if p)])


def brand_context() -> dict[str, dict[str, str]]:
    """Expose the branding values to every Jinja template as ``brand``.

    Returns:
        ``{"brand": {"title", "logo", "logo_alt", "favicon"}}``.
    """
    return {
        "brand": {
            "title": Config.KENBOARD_TITLE,
            "logo": Config.KENBOARD_LOGO,
            "logo_alt": Config.KENBOARD_LOGO_ALT,
            "favicon": Config.KENBOARD_FAVICON,
        }
    }


def init_branding(app: Flask) -> None:
    """Register the ``brand`` context processor on ``app``.

    Args:
        app: the Flask application.
    """
    app.context_processor(brand_context)
