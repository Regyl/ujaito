"""Connectively API errors."""

from __future__ import annotations


class ConnectivelyError(Exception):
    def __init__(self, message: str, *, status: int) -> None:
        super().__init__(message)
        self.status = status


class ValidationError(ConnectivelyError):
    pass


class AuthError(ConnectivelyError):
    pass


class ForbiddenError(ConnectivelyError):
    pass
