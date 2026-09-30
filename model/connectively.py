"""Connectively API data classes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginRequest:
    username: str
    password: str


@dataclass(frozen=True)
class Question:
    question: str
    source: str | None
    due_date: str | None
    publicLink: str | None
    featuredQuestionId: int
    sourceUrl: str | None
    isHaroQuery: bool | None
    categories: list[str]
