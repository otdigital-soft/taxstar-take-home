from flask import current_app, g
from pymongo import ASCENDING, DESCENDING, MongoClient


def init_db(app, mongo_client=None):
    """Attach a Mongo client to the app and ensure indexes exist."""
    if mongo_client is not None:
        app.extensions["mongo_client"] = mongo_client
    else:
        app.extensions["mongo_client"] = MongoClient(app.config["MONGO_URI"])

    with app.app_context():
        db = get_db()
        ensure_indexes(db)
        migrate_legacy_invoice_amounts(db)

    app.teardown_appcontext(_teardown_db)


def ensure_indexes(db):
    db.users.create_index("email", unique=True)
    db.entities.create_index(
        [("owner_id", ASCENDING), ("created_at", DESCENDING)],
    )
    db.invoices.create_index(
        [
            ("entity_id", ASCENDING),
            ("status", ASCENDING),
            ("created_at", DESCENDING),
        ],
    )
    db.invoices.create_index(
        [("entity_id", ASCENDING), ("invoice_number", ASCENDING)],
        unique=True,
    )


def migrate_legacy_invoice_amounts(db):
    """One-time-ish upgrade: float/string `amount` → integer `amount_minor`."""
    from api.money import parse_amount_to_minor

    for doc in db.invoices.find({"amount_minor": {"$exists": False}, "amount": {"$exists": True}}):
        try:
            minor = parse_amount_to_minor(doc["amount"])
        except ValueError:
            continue
        db.invoices.update_one(
            {"_id": doc["_id"]},
            {"$set": {"amount_minor": minor}, "$unset": {"amount": ""}},
        )


def _teardown_db(_exc):
    g.pop("db", None)


def get_db():
    if "db" not in g:
        client = current_app.extensions["mongo_client"]
        g.db = client[current_app.config["MONGO_DB"]]
    return g.db
