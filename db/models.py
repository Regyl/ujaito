"""SQLAlchemy models and PostgreSQL URLs shared by Alembic and the Spark job."""

from __future__ import annotations

import os
from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import BigInteger, Boolean, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Question(Base):
    __tablename__ = "questions"

    featured_question_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    public_link: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    is_haro_query: Mapped[bool | None] = mapped_column(Boolean)
    categories: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )


def _postgres_settings() -> dict[str, str]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "db": os.environ.get("POSTGRES_DB", "connectively"),
        "user": os.environ.get("POSTGRES_USER", "connectively"),
        "password": os.environ.get("POSTGRES_PASSWORD", "connectively"),
    }


def postgres_url() -> str:
    settings = _postgres_settings()
    user = quote_plus(settings["user"])
    password = quote_plus(settings["password"])
    database = quote_plus(settings["db"])
    return (
        f"postgresql+psycopg://{user}:{password}"
        f"@{settings['host']}:{settings['port']}/{database}"
    )


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
