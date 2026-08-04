from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify
from pydantic import ValidationError

from api.errors import invalid_id, not_found, validation_error
from api.request_utils import parse_json_body
from api.schemas import CreateEntityRequest, EntityResponse, mask_trn
from auth_utils import jwt_required
from crypto import decrypt_trn, encrypt_trn
from db import get_db

entities_bp = Blueprint("entities", __name__)


def _entity_response(doc: dict) -> EntityResponse:
    plain = decrypt_trn(doc["trn_encrypted"])
    return EntityResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        trn_masked=mask_trn(plain),
        created_at=doc["created_at"].isoformat() if doc.get("created_at") else None,
    )


@entities_bp.post("")
@jwt_required
def create_entity():
    body, err = parse_json_body()
    if err:
        return err
    try:
        data = CreateEntityRequest.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    now = datetime.now(timezone.utc)
    doc = {
        "name": data.name,
        "trn_encrypted": encrypt_trn(data.trn),
        "owner_id": ObjectId(g.current_user_id),
        "created_at": now,
    }
    result = get_db().entities.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify(_entity_response(doc).model_dump(mode="json")), 201


@entities_bp.get("")
@jwt_required
def list_entities():
    cursor = get_db().entities.find({"owner_id": ObjectId(g.current_user_id)}).sort(
        "created_at", -1
    )
    return jsonify([_entity_response(doc).model_dump(mode="json") for doc in cursor])


@entities_bp.get("/<entity_id>")
@jwt_required
def get_entity(entity_id: str):
    try:
        oid = ObjectId(entity_id)
    except InvalidId:
        return invalid_id("entity")

    doc = get_db().entities.find_one(
        {"_id": oid, "owner_id": ObjectId(g.current_user_id)}
    )
    if not doc:
        return not_found("Entity")
    return jsonify(_entity_response(doc).model_dump(mode="json"))
