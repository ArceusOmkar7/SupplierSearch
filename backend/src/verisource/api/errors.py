"""Owner-safe errors; never serialize exceptions, validation inputs or source payloads."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", ""),
                "details": details or {},
            }
        },
        headers={"Cache-Control": "no-store"},
    )


class Rejection(HTTPException):
    """HTTP failure with a stable code and owner-safe field details (never submitted values)."""

    def __init__(self, status: int, code: str, message: str, details: dict[str, Any]) -> None:
        super().__init__(status, detail=code)
        self.code, self.public_message, self.details = code, message, details


def reject(status: int, code: str, message: str, **details: Any) -> Rejection:
    return Rejection(status, code, message, details)


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    status = exc.status_code if isinstance(exc, HTTPException) else 500
    if isinstance(exc, Rejection):
        return error_response(request, status, exc.code, exc.public_message, exc.details)
    messages = {
        400: ("bad_request", "The request could not be accepted."),
        401: ("unauthenticated", "Sign in to continue."),
        403: ("request_rejected", "The request could not be authorized."),
        404: ("not_found", "This resource is unavailable."),
        409: ("invalid_state", "This action is unavailable in the current state."),
        412: ("stale_version", "Reload the current revision before continuing."),
        413: ("too_large", "The file exceeds a supported limit."),
        415: ("unsupported_type", "Only PDF documents are supported."),
        422: ("invalid_fields", "Check the submitted fields."),
        429: ("rate_limited", "Too many requests. Try again later."),
        503: ("dependency_unavailable", "A local dependency is unavailable."),
    }
    code, message = messages.get(status, ("request_failed", "The request failed."))
    return error_response(request, status, code, message)


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(request, 422, "invalid_fields", "Check the submitted fields.")


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(request, 500, "internal_error", "The request could not be completed.")
