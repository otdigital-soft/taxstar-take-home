from flask import Flask
from flask_cors import CORS

from config import Config
from api.auth.routes import auth_bp
from api.entities.routes import entities_bp
from api.invoices.routes import invoices_bp
from db import init_db


def create_app(config_object=None, mongo_client=None):
    """Application factory. Pass mongo_client to inject a mock in tests."""
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
    )

    init_db(app, mongo_client=mongo_client)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(entities_bp, url_prefix="/api/entities")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
