"""Typed exceptions for HyperStudy API errors."""


class HyperStudyError(Exception):
    """Base exception for all HyperStudy API errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code from the API (e.g. 'VALIDATION_ERROR').
        status_code: HTTP status code.
        details: Optional dict with additional error context.
    """

    def __init__(self, message, *, code=None, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def __repr__(self):
        parts = [f"HyperStudyError({self.message!r}"]
        if self.code:
            parts[0] = f"{type(self).__name__}({self.message!r}"
            parts.append(f"code={self.code!r}")
        if self.status_code:
            parts.append(f"status_code={self.status_code}")
        return ", ".join(parts) + ")"


class AuthenticationError(HyperStudyError):
    """Raised on 401 — invalid or missing API key."""

    pass


class ForbiddenError(HyperStudyError):
    """Raised on 403 — valid key but insufficient scopes or access."""

    pass


class NotFoundError(HyperStudyError):
    """Raised on 404 — resource does not exist."""

    pass


class ValidationError(HyperStudyError):
    """Raised on 400 — invalid request parameters."""

    pass


class ServerError(HyperStudyError):
    """Raised on 5xx — server-side failure."""

    pass
