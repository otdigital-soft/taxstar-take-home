from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from bson import ObjectId
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from api.errors import unauthorized
from db import get_db


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def create_access_token(user_id: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(
        hours=current_app.config["JWT_EXPIRY_HOURS"]
    )
    payload = {"sub": user_id, "exp": expiry}
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return unauthorized(
                "Missing or invalid Authorization header.",
                code="missing_token",
            )
        token = header[7:]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            return unauthorized("Token expired.", code="token_expired")
        except jwt.InvalidTokenError:
            return unauthorized("Invalid token.", code="invalid_token")

        user = get_db().users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            return unauthorized("User not found.", code="unauthorized")

        g.current_user = user
        g.current_user_id = str(user["_id"])
        return fn(*args, **kwargs)

    return wrapper
