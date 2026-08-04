from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from api.money import parse_amount_to_minor
from api.status_rules import effective_status

InvoiceStatus = Literal["draft", "sent", "paid", "overdue"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class EntityResponse(BaseModel):
    id: str
    name: str
    trn_masked: str
    created_at: str | None = None


class InvoiceResponse(BaseModel):
    id: str
    entity_id: str
    invoice_number: str
    amount: str
    currency: str
    issue_date: date
    due_date: date
    status: InvoiceStatus
    effective_status: InvoiceStatus
    created_at: str | None = None


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class CreateEntityRequest(BaseModel):
    name: str = Field(min_length=1)
    trn: str = Field(min_length=1)


class CreateInvoiceRequest(BaseModel):
    entity_id: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    amount: str = Field(min_length=1, description="Decimal amount as a string, e.g. '1250.50'")
    currency: str = Field(min_length=1, max_length=10)
    issue_date: date
    due_date: date
    status: InvoiceStatus = "draft"

    @field_validator("amount")
    @classmethod
    def amount_to_minor(cls, value: str) -> str:
        # Validate early; conversion happens in the route via parse_amount_to_minor.
        parse_amount_to_minor(value)
        return str(value).strip()

    @model_validator(mode="after")
    def due_after_issue(self):
        if self.due_date <= self.issue_date:
            raise ValueError("due_date must fall after issue_date")
        return self


class UpdateInvoiceRequest(BaseModel):
    status: InvoiceStatus


def mask_trn(plain: str) -> str:
    digits = plain.strip()
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{'*' * 6}{digits[-4:]}"


def invoice_response_from_doc(doc: dict) -> InvoiceResponse:
    from api.money import amount_minor_from_doc, minor_to_amount_str

    stored = doc["status"]
    due = doc["due_date"]
    return InvoiceResponse(
        id=str(doc["_id"]),
        entity_id=str(doc["entity_id"]),
        invoice_number=doc["invoice_number"],
        amount=minor_to_amount_str(amount_minor_from_doc(doc)),
        currency=doc["currency"],
        issue_date=date.fromisoformat(doc["issue_date"]),
        due_date=date.fromisoformat(due),
        status=stored,
        effective_status=effective_status(stored, due),
        created_at=doc["created_at"].isoformat() if doc.get("created_at") else None,
    )
