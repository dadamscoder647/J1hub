"""Utilities for validating incoming Flask requests."""

from __future__ import annotations

from typing import Iterable

from flask import Request
from werkzeug.exceptions import BadRequest


def parse_json_request(
    req: Request,
    *,
    required_keys: Iterable[str] | None = None,
    allow_empty: bool = False,
) -> dict:
    """Return the parsed JSON body or raise a 400 error."""

    if not req.is_json:
        raise BadRequest("Request content type must be application/json.")

    data = req.get_json(silent=False)
    if data is None:
        raise BadRequest("Request JSON body is required.")

    if not isinstance(data, dict):
        raise BadRequest("Request JSON payload must be an object.")

    if not data and not allow_empty:
        raise BadRequest("Request JSON body must not be empty.")

    if required_keys:
        missing = [key for key in required_keys if not data.get(key)]
        if missing:
            raise BadRequest(
                "Missing required fields: {}.".format(
                    ", ".join(sorted(missing))
                )
            )

    return data
