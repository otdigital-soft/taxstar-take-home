from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from pydantic import ValidationError

from api.errors import (
    conflict,
    forbidden_transition,
    invalid_id,
    not_found,
    validation_error,
)
from api.money import parse_amount_to_minor
from api.request_utils import parse_json_body
from api.schemas import (
    CreateInvoiceRequest,
    UpdateInvoiceRequest,
    invoice_response_from_doc,
)
from api.status_rules import can_transition, effective_status
from auth_utils import jwt_required
from db import get_db

invoices_bp = Blueprint("invoices", __name__)


def _current_owner_id() -> ObjectId:
    return ObjectId(g.current_user_id)


def _owned_entity(entity_id: ObjectId):
    return get_db().entities.find_one(
        {"_id": entity_id, "owner_id": _current_owner_id()}
    )


def _invoice_accessible(invoice: dict | None) -> bool:
    if not invoice:
        return False
    return _owned_entity(invoice["entity_id"]) is not None


def _owned_entity_ids() -> list[ObjectId]:
    return [
        doc["_id"]
        for doc in get_db().entities.find(
            {"owner_id": _current_owner_id()}, {"_id": 1}
        )
    ]


@invoices_bp.post("")
@jwt_required
def create_invoice():
    body, err = parse_json_body()
    if err:
        return err
    try:
        data = CreateInvoiceRequest.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    try:
        entity_oid = ObjectId(data.entity_id)
    except InvalidId:
        return invalid_id("entity")

    if not _owned_entity(entity_oid):
        return not_found("Entity")

    now = datetime.now(timezone.utc)
    doc = {
        "entity_id": entity_oid,
        "owner_id": _current_owner_id(),
        "invoice_number": data.invoice_number,
        "amount_minor": parse_amount_to_minor(data.amount),
        "currency": data.currency.upper(),
        "issue_date": data.issue_date.isoformat(),
        "due_date": data.due_date.isoformat(),
        "status": data.status,
        "created_at": now,
    }
    try:
        result = get_db().invoices.insert_one(doc)
    except DuplicateKeyError:
        return conflict(
            "duplicate_invoice_number",
            "Invoice number already exists for this entity.",
        )
    doc["_id"] = result.inserted_id
    return jsonify(invoice_response_from_doc(doc).model_dump(mode="json")), 201


@invoices_bp.get("")
@jwt_required
def list_invoices():
    entity_id = request.args.get("entity_id")
    status_filter = request.args.get("status")

    if entity_id:
        try:
            entity_oid = ObjectId(entity_id)
        except InvalidId:
            return invalid_id("entity")
        if not _owned_entity(entity_oid):
            return not_found("Entity")
        query: dict = {"entity_id": entity_oid}
    else:
        query = {"entity_id": {"$in": _owned_entity_ids()}}

    cursor = get_db().invoices.find(query).sort("created_at", -1)
    invoices = list(cursor)

    if status_filter:
        allowed = {"draft", "sent", "paid", "overdue"}
        if status_filter not in allowed:
            return validation_error_from_fields(
                {"status": "Invalid status filter."}
            )
        invoices = [
            doc
            for doc in invoices
            if effective_status(doc["status"], doc["due_date"]) == status_filter
        ]

    return jsonify(
        [
            invoice_response_from_doc(doc).model_dump(mode="json")
            for doc in invoices
        ]
    )


def validation_error_from_fields(fields: dict[str, str]):
    from api.errors import error_response

    return error_response(
        "validation_error",
        "The request contains invalid fields.",
        400,
        fields=fields,
    )


@invoices_bp.patch("/<invoice_id>")
@jwt_required
def update_invoice(invoice_id: str):
    body, err = parse_json_body()
    if err:
        return err
    try:
        data = UpdateInvoiceRequest.model_validate(body)
    except ValidationError as exc:
        return validation_error(exc)

    try:
        oid = ObjectId(invoice_id)
    except InvalidId:
        return invalid_id("invoice")

    invoice = get_db().invoices.find_one({"_id": oid})
    if not _invoice_accessible(invoice):
        return not_found("Invoice")

    current = invoice["status"]
    target = data.status
    if not can_transition(current, target):
        return forbidden_transition(current, target)

    result = get_db().invoices.find_one_and_update(
        {"_id": oid},
        {"$set": {"status": target}},
        return_document=ReturnDocument.AFTER,
    )
    return jsonify(invoice_response_from_doc(result).model_dump(mode="json"))
