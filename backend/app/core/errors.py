"""Domain-level exceptions mapped to HTTP status codes in the API layer."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for business rule violations (HTTP 422)."""

    status_code = 422

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    status_code = 422


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class PermissionDeniedError(DomainError):
    status_code = 403


class AuthenticationError(DomainError):
    status_code = 401
