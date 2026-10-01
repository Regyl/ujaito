"""LM Studio API errors."""

from __future__ import annotations


class LmStudioError(Exception):
    def __init__(self, message: str, *, status: int) -> None:
        super().__init__(message)
        self.status = status
