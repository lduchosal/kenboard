"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration loaded from environment variables."""

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "dashboard")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "dashboard")
    DB_NAME: str = os.getenv("DB_NAME", "dashboard")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
