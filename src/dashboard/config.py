"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration loaded from environment variables."""

    # App runtime (CRUD only)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "dashboard")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "dashboard")

    # Migrations (DDL: CREATE, ALTER, DROP)
    DB_MIGRATE_USER: str = os.getenv("DB_MIGRATE_USER", "dashboard_admin")
    DB_MIGRATE_PASSWORD: str = os.getenv("DB_MIGRATE_PASSWORD", "")

    # Test runtime (CRUD only, separate DB)
    DB_TEST_USER: str = os.getenv("DB_TEST_USER", "dashboard_test")
    DB_TEST_PASSWORD: str = os.getenv("DB_TEST_PASSWORD", "")
    DB_TEST_NAME: str = os.getenv("DB_TEST_NAME", "dashboard_test")

    # Test migrations (DDL on test DB)
    DB_TEST_MIGRATE_USER: str = os.getenv(
        "DB_TEST_MIGRATE_USER", "dashboard_test_admin"
    )
    DB_TEST_MIGRATE_PASSWORD: str = os.getenv("DB_TEST_MIGRATE_PASSWORD", "")

    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # API key authentication (cf. doc/api-keys.md)
    KENBOARD_ADMIN_KEY: str = os.getenv("KENBOARD_ADMIN_KEY", "")

    # User session authentication (cf. doc/auth-user.md)
    KENBOARD_SECRET_KEY: str = os.getenv("KENBOARD_SECRET_KEY", "")

    # CORS allow-list (comma-separated origins). Empty = no CORS headers,
    # browsers fall back to same-origin policy (the secure default — the
    # built-in templates are served by Flask itself, so cross-origin is
    # only needed when an external client talks to the API).
    KENBOARD_CORS_ORIGINS: list[str] = [
        s.strip()
        for s in os.getenv("KENBOARD_CORS_ORIGINS", "").split(",")
        if s.strip()
    ]

    # Set to true when kenboard is served over HTTPS (directly or behind
    # a TLS-terminating reverse proxy). Enables Secure cookies and HSTS.
    KENBOARD_HTTPS: bool = os.getenv("KENBOARD_HTTPS", "false").lower() == "true"
