from datetime import date, timedelta

import mongomock
import pytest

from app import create_app
from config import Config


@pytest.fixture
def client():
    mongo = mongomock.MongoClient()
    app = create_app(config_object=Config, mongo_client=mongo)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _signup(client, email: str, name: str = "User"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "secret12", "name": name},
    )
    assert resp.status_code == 201, resp.get_json()
    data = resp.get_json()
    return {"Authorization": f"Bearer {data['token']}"}, data["user"]


@pytest.fixture
def auth_headers(client):
    headers, _ = _signup(client, "alice@example.com", "Alice")
    return headers


def test_signup_and_login(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "bob@example.com", "password": "secret12", "name": "Bob"},
    )
    assert signup.status_code == 201
    assert "token" in signup.get_json()

    duplicate = client.post(
        "/api/auth/signup",
        json={"email": "bob@example.com", "password": "secret12", "name": "Bob"},
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "duplicate_email"

    login = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "secret12"},
    )
    assert login.status_code == 200
    assert "token" in login.get_json()

    bad = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401
    assert bad.get_json()["error"]["code"] == "invalid_credentials"


def test_entities_require_auth(client):
    resp = client.post("/api/entities", json={"name": "Acme", "trn": "TRN-12345"})
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "missing_token"


def test_create_and_list_entities_masks_trn(client, auth_headers):
    create = client.post(
        "/api/entities",
        json={"name": "Acme Corp", "trn": "TRN-12345"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    data = create.get_json()
    assert data["name"] == "Acme Corp"
    assert data["trn_masked"] == "******2345"
    assert "trn" not in data

    from flask import current_app

    with client.application.app_context():
        raw = current_app.extensions["mongo_client"][Config.MONGO_DB].entities.find_one()
        assert "trn" not in raw
        assert "trn_encrypted" in raw
        assert raw["trn_encrypted"] != "TRN-12345"
        assert raw["trn_encrypted"] != b"TRN-12345"

    listed = client.get("/api/entities", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.get_json()) == 1
    assert listed.get_json()[0]["trn_masked"].startswith("******")


def test_invoice_validation_and_money(client, auth_headers):
    entity = client.post(
        "/api/entities",
        json={"name": "Acme", "trn": "TRN-1"},
        headers=auth_headers,
    ).get_json()

    bad_amount = client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-1",
            "amount": "-10",
            "currency": "USD",
            "issue_date": "2024-01-01",
            "due_date": "2024-01-15",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert bad_amount.status_code == 400
    assert bad_amount.get_json()["error"]["code"] == "validation_error"

    bad_dates = client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-2",
            "amount": "100.00",
            "currency": "USD",
            "issue_date": "2024-01-15",
            "due_date": "2024-01-01",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert bad_dates.status_code == 400

    created = client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-3",
            "amount": "1250.50",
            "currency": "usd",
            "issue_date": "2024-01-01",
            "due_date": "2024-01-31",
            "status": "sent",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    invoice = created.get_json()
    assert invoice["amount"] == "1250.50"
    assert invoice["currency"] == "USD"

    from flask import current_app

    with client.application.app_context():
        raw = current_app.extensions["mongo_client"][Config.MONGO_DB].invoices.find_one()
        assert raw["amount_minor"] == 125050
        assert "amount" not in raw


def test_invoice_crud_filter_and_transitions(client, auth_headers):
    entity = client.post(
        "/api/entities",
        json={"name": "Acme", "trn": "TRN-1"},
        headers=auth_headers,
    ).get_json()

    created = client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-100",
            "amount": "250.50",
            "currency": "USD",
            "issue_date": "2024-01-01",
            "due_date": "2024-01-31",
            "status": "sent",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    invoice = created.get_json()

    client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-101",
            "amount": "50.00",
            "currency": "USD",
            "issue_date": "2024-02-01",
            "due_date": "2099-02-28",
            "status": "draft",
        },
        headers=auth_headers,
    )

    filtered = client.get(
        f"/api/invoices?entity_id={entity['id']}&status=sent",
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    # INV-100 may be effective overdue depending on today; filter uses effective_status
    items = filtered.get_json()
    assert all(i["effective_status"] == "sent" for i in items)

    patched = client.patch(
        f"/api/invoices/{invoice['id']}",
        json={"status": "paid"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.get_json()["status"] == "paid"

    # paid → draft is forbidden
    forbidden = client.patch(
        f"/api/invoices/{invoice['id']}",
        json={"status": "draft"},
        headers=auth_headers,
    )
    assert forbidden.status_code == 409
    assert forbidden.get_json()["error"]["code"] == "forbidden_status_transition"


def test_effective_status_overdue_without_mutating_storage(client, auth_headers):
    entity = client.post(
        "/api/entities",
        json={"name": "Acme", "trn": "TRN-1"},
        headers=auth_headers,
    ).get_json()

    past_due = (date.today() - timedelta(days=5)).isoformat()
    issue = (date.today() - timedelta(days=20)).isoformat()

    created = client.post(
        "/api/invoices",
        json={
            "entity_id": entity["id"],
            "invoice_number": "INV-OLD",
            "amount": "10.00",
            "currency": "USD",
            "issue_date": issue,
            "due_date": past_due,
            "status": "sent",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    data = created.get_json()
    assert data["status"] == "sent"
    assert data["effective_status"] == "overdue"

    from flask import current_app

    with client.application.app_context():
        raw = current_app.extensions["mongo_client"][Config.MONGO_DB].invoices.find_one(
            {"invoice_number": "INV-OLD"}
        )
        assert raw["status"] == "sent"


def test_user_cannot_access_another_users_resources(client):
    alice_headers, _ = _signup(client, "alice2@example.com", "Alice")
    bob_headers, _ = _signup(client, "bob2@example.com", "Bob")

    alice_entity = client.post(
        "/api/entities",
        json={"name": "Alice Co", "trn": "TRN-AAAA"},
        headers=alice_headers,
    ).get_json()

    alice_invoice = client.post(
        "/api/invoices",
        json={
            "entity_id": alice_entity["id"],
            "invoice_number": "INV-A1",
            "amount": "99.00",
            "currency": "USD",
            "issue_date": "2024-01-01",
            "due_date": "2099-01-31",
            "status": "sent",
        },
        headers=alice_headers,
    ).get_json()

    get_entity = client.get(
        f"/api/entities/{alice_entity['id']}",
        headers=bob_headers,
    )
    assert get_entity.status_code == 404
    assert get_entity.get_json()["error"]["code"] == "not_found"

    create_on_alice = client.post(
        "/api/invoices",
        json={
            "entity_id": alice_entity["id"],
            "invoice_number": "INV-HACK",
            "amount": "1.00",
            "currency": "USD",
            "issue_date": "2024-01-01",
            "due_date": "2024-01-02",
            "status": "draft",
        },
        headers=bob_headers,
    )
    assert create_on_alice.status_code == 404

    list_alice = client.get(
        f"/api/invoices?entity_id={alice_entity['id']}",
        headers=bob_headers,
    )
    assert list_alice.status_code == 404

    patch_alice = client.patch(
        f"/api/invoices/{alice_invoice['id']}",
        json={"status": "paid"},
        headers=bob_headers,
    )
    assert patch_alice.status_code == 404

    still_sent = client.get(
        f"/api/invoices?entity_id={alice_entity['id']}&status=sent",
        headers=alice_headers,
    )
    assert still_sent.status_code == 200
    assert len(still_sent.get_json()) == 1
    assert still_sent.get_json()[0]["status"] == "sent"


def test_duplicate_invoice_number_per_entity(client, auth_headers):
    entity = client.post(
        "/api/entities",
        json={"name": "Acme", "trn": "TRN-1"},
        headers=auth_headers,
    ).get_json()

    payload = {
        "entity_id": entity["id"],
        "invoice_number": "INV-DUP",
        "amount": "10.00",
        "currency": "USD",
        "issue_date": "2024-01-01",
        "due_date": "2024-01-31",
        "status": "draft",
    }
    assert client.post("/api/invoices", json=payload, headers=auth_headers).status_code == 201
    dup = client.post("/api/invoices", json=payload, headers=auth_headers)
    assert dup.status_code == 409
    assert dup.get_json()["error"]["code"] == "duplicate_invoice_number"


def test_malformed_json(client, auth_headers):
    resp = client.post(
        "/api/entities",
        data="{not-json",
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "malformed_json"
