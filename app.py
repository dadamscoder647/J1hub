"""Application factory."""

import json
import os
import uuid

from flask import Flask, jsonify, g, request
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from config import Config
from models import db
from routes.auth import auth_bp
from routes.listings import listings_bp
from routes.verify import admin_bp, verify_bp

# Billing routes may be optional; import safely
try:
    from routes.billing import billing_bp  # type: ignore
except Exception:
    billing_bp = None  # register only if present

migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Core subsystems
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # CORS
    CORS(
        app,
        resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        supports_credentials=True,
    )

    # Rate limiting
    storage_uri = app.config.get("RATELIMIT_STORAGE_URI", "memory://")
    headers_enabled = app.config.get("RATELIMIT_HEADERS_ENABLED", True)
    key_prefix = app.config.get("RATELIMIT_KEY_PREFIX") or str(uuid.uuid4())

    global limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[lambda: app.config.get("RATE_LIMIT", "60 per minute")],
        storage_uri=storage_uri,
        headers_enabled=headers_enabled,
        key_prefix=key_prefix,
    )
    limiter.init_app(app)
    app.config["RATELIMIT_KEY_PREFIX"] = key_prefix

    # Ensure uploads directory exists
    upload_dir = app.config.get("UPLOAD_DIR")
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)

    # Blueprints
    app.register_blueprint(verify_bp, url_prefix="/verify")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(listings_bp, url_prefix="/listings")
    if billing_bp:  # only if billing module exists
        app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Health
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"})

    # Errors
    _register_error_handlers(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    """Register JSON error handlers with request IDs."""

    @app.before_request
    def _assign_request_id():  # pragma: no cover
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _add_request_id_header(response):  # pragma: no cover
        request_id = g.get("request_id")
        if request_id:
            response.headers.setdefault("X-Request-ID", request_id)
        return response

    @app.errorhandler(HTTPException)
    def _handle_http_exception(error: HTTPException):
        request_id = g.get("request_id") or str(uuid.uuid4())
        response = error.get_response()
        payload = {
            "error": getattr(error, "name", "Error"),
            "detail": error.description,
            "request_id": request_id,
        }
        response.data = json.dumps(payload)
        response.content_type = "application/json"
        response.headers.setdefault("X-Request-ID", request_id)
        return response

    @app.errorhandler(Exception)
    def _handle_unexpected(error: Exception):  # pragma: no cover
        request_id = g.get("request_id") or str(uuid.uuid4())
        app.logger.exception("Unhandled application error", exc_info=error)
        payload = {
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        }
        response = jsonify(payload)
        response.status_code = 500
        response.headers.setdefault("X-Request-ID", request_id)
        return response


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
