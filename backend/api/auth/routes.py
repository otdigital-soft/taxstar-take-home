from flask import Blueprint, jsonify
from pydantic import ValidationError

from api.errors import conflict, unauthorized, validation_error
from api.request_utils import parse_json_body
from api.schemas import AuthResponse, LoginRequest, SignupRequest, UserResponse
from auth_utils import create_access_token, hash_password, verify_password
from db import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    body, err = parse_json_body()
    if err:
        return err
    try:
        data = SignupRequest.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    db = get_db()
    if db.users.find_one({"email": data.email.lower()}):
        return conflict("duplicate_email", "Email already registered.")

    result = db.users.insert_one(
        {
            "email": data.email.lower(),
            "password_hash": hash_password(data.password),
            "name": data.name,
        }
    )
    user_id = str(result.inserted_id)
    token = create_access_token(user_id)
    response = AuthResponse(
        token=token,
        user=UserResponse(id=user_id, email=data.email.lower(), name=data.name),
    )
    return jsonify(response.model_dump(mode="json")), 201


@auth_bp.post("/login")
def login():
    body, err = parse_json_body()
    if err:
        return err
    try:
        data = LoginRequest.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    user = get_db().users.find_one({"email": data.email.lower()})
    if not user or not verify_password(user["password_hash"], data.password):
        return unauthorized(
            "Invalid email or password.",
            code="invalid_credentials",
        )

    user_id = str(user["_id"])
    token = create_access_token(user_id)
    response = AuthResponse(
        token=token,
        user=UserResponse(id=user_id, email=user["email"], name=user["name"]),
    )
    return jsonify(response.model_dump(mode="json"))
