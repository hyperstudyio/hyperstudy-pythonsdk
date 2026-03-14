"""Low-level HTTP transport wrapping requests.Session."""

from __future__ import annotations

import os
from typing import Any

import requests

from .exceptions import (
    AuthenticationError,
    ForbiddenError,
    HyperStudyError,
    NotFoundError,
    ServerError,
    ValidationError,
)

_STATUS_MAP = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
}


class HttpTransport:
    """Thin wrapper around ``requests.Session`` for the HyperStudy API.

    * Sets ``X-API-Key`` header on every request.
    * Parses the standard ``{status, metadata, data}`` response envelope.
    * Maps HTTP error codes to typed exceptions.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.hyperstudy.io/api/v3",
        timeout: int = 30,
    ):
        resolved_key = api_key or os.environ.get("HYPERSTUDY_API_KEY")
        if not resolved_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key= or set the HYPERSTUDY_API_KEY "
                "environment variable.",
                code="MISSING_API_KEY",
                status_code=401,
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": resolved_key,
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict[str, Any] | None = None) -> dict:
        return self._request("PUT", path, json=json)

    def delete(self, path: str, params: dict[str, Any] | None = None) -> dict:
        return self._request("DELETE", path, params=params)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)

        resp = self._session.request(method, url, **kwargs)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: requests.Response) -> dict:
        """Parse the JSON envelope and raise on errors."""
        try:
            body = resp.json()
        except ValueError:
            if resp.status_code >= 500:
                raise ServerError(
                    f"Server returned {resp.status_code} with non-JSON body",
                    code="SERVER_ERROR",
                    status_code=resp.status_code,
                )
            raise HyperStudyError(
                f"Unexpected non-JSON response ({resp.status_code})",
                status_code=resp.status_code,
            )

        # API-level error envelope: {"status": "error", "error": {...}}
        if body.get("status") == "error":
            err = body.get("error", {})
            message = err.get("message", resp.reason or "Unknown error")
            code = err.get("code", "UNKNOWN")
            details = err.get("details")
            exc_cls = _STATUS_MAP.get(resp.status_code, HyperStudyError)
            if resp.status_code >= 500:
                exc_cls = ServerError
            raise exc_cls(
                message, code=code, status_code=resp.status_code, details=details
            )

        # Non-2xx without error envelope
        if not resp.ok:
            exc_cls = _STATUS_MAP.get(resp.status_code, HyperStudyError)
            if resp.status_code >= 500:
                exc_cls = ServerError
            raise exc_cls(
                resp.reason or f"HTTP {resp.status_code}",
                status_code=resp.status_code,
            )

        return body
