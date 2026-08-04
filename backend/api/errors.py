from __future__ import annotations

from flask import jsonify
from pydantic import ValidationError


def error_response(
    code: str,
    message: str,
    status: int,
    fields: dict[str, str] | None = None,
):
    payload: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if fields:
        payload["error"]["fields"] = fields
    return jsonify(payload), status


def malformed_json():
    return error_response(
        "malformed_json",
        "Request body must be valid JSON.",
        400,
    )


def validation_error(exc: ValidationError):
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc") or ()
        # Skip internal model-validator roots when a field path exists.
        key_parts = [str(p) for p in loc if p != "__root__"]
        key = ".".join(key_parts) if key_parts else "_form"
        if key not in fields:
            fields[key] = err.get("msg") or "Invalid value"
    return error_response(
        "validation_error",
        "The request contains invalid fields.",
        400,
        fields=fields,
    )


def invalid_id(resource: str = "resource"):
    return error_response(
        "invalid_id",
        f"Invalid {resource} id.",
        400,
    )


def unauthorized(message: str = "Authentication required.", code: str = "unauthorized"):
    return error_response(code, message, 401)


def not_found(resource: str = "Resource"):
    return error_response("not_found", f"{resource} not found.", 404)


def conflict(code: str, message: str):
    return error_response(code, message, 409)


def forbidden_transition(current: str, target: str):
    return error_response(
        "forbidden_status_transition",
        f"Cannot transition invoice status from '{current}' to '{target}'.",
        409,
        fields={"status": f"Transition {current} → {target} is not allowed."},
    )
