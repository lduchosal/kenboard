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
    KENBOARD_AUTH_ENFORCED: bool = (
        os.getenv("KENBOARD_AUTH_ENFORCED", "false").lower() == "true"
    )
