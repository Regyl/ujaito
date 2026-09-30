"""PostgreSQL JDBC settings for the Spark job."""

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


def jdbc_url() -> str:
    settings = _postgres_settings()
    return (
        f"jdbc:postgresql://{settings['host']}:{settings['port']}/{settings['db']}"
        "?stringtype=unspecified"
    )


def jdbc_properties() -> dict[str, str]:
    settings = _postgres_settings()
    return {
        "user": settings["user"],
        "password": settings["password"],
        "driver": "org.postgresql.Driver",
    }
