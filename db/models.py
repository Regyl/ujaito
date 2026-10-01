"""PostgreSQL connection settings."""

from __future__ import annotations

import os


def _postgres_settings() -> dict[str, str]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "db": os.environ.get("POSTGRES_DB", "connectively"),
        "user": os.environ.get("POSTGRES_USER", "connectively"),
        "password": os.environ.get("POSTGRES_PASSWORD", "connectively"),
    }


def postgres_connect_kwargs() -> dict[str, str]:
    settings = _postgres_settings()
    return {
        "host": settings["host"],
        "port": settings["port"],
        "dbname": settings["db"],
        "user": settings["user"],
        "password": settings["password"],
    }
