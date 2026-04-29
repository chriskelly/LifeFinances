"""Helpers for consistent JSON success and error responses for `/api` routes."""

from collections.abc import Mapping
from typing import Any

from flask import Response, jsonify


def json_success(body: Mapping[str, Any], status: int = 200) -> tuple[Response, int]:
    """Build a JSON success response."""
    return jsonify(dict(body)), status


def json_error(
    *,
    message: str,
    status: int,
    code: str | None = None,
    details: str | None = None,
) -> tuple[Response, int]:
    """
    Build a JSON error body matching OpenAPI ``ErrorBody``.

    Args:
        message (str): The error message for the client.
        status (int): HTTP status code to return, e.g.:
            400 - Bad Request (invalid input, shape, or YAML)
            404 - Not Found (resource or endpoint not found)
            409 - Conflict (edit conflict)
            422 - Unprocessable Entity (validation failed)
            500 - Internal Server Error (unexpected server exception)
        code (str, optional): Application-specific error code, if any.
        details (str, optional): More detailed explanation.

    Returns:
        tuple[Response, int]: Flask JSON response and HTTP status.
    """
    err: dict[str, Any] = {"message": message}
    if code is not None:
        err["code"] = code
    if details is not None:
        err["details"] = details
    return jsonify({"error": err}), status
