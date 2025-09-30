"""Application factory."""

import json
import os
import time
import uuid

from flask import Flask, jsonify, g, request
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

try:
    from flask_cors import CORS as _CORS
except Exception:
    def _CORS(app, resources=None, supports_credentials=False, **kwargs):  # no-op if lib missing
        if app is None:
            return None

        origins = "*"
        if isinstance(resources, dict):
            for value in resources.values():
                origins = value.get("origins", origins)
                break

        if not isinstance(origins, (list, tuple, set)):
            allowed = [origins]
        else:
            allowed = list(origins)

        @app.after_request
        def _add_cors_headers(response):
            origin = request.headers.get("Origin")
            allow_origin = None

            if allowed == ["*"]:
                allow_origin = origin or "*"
            elif origin and origin in allowed:
                allow_origin = origin
            elif allowed:
                allow_origin = allowed[0]

            if allow_origin:
                response.headers.setdefault("Access-Control-Allow-Origin", allow_origin)
            if supports_credentials:
                response.headers.setdefault("Access-Control-Allow-Credentials", "true")
            return response

        return None

CORS = _CORS

try:
    from flask_limiter import Limiter as _Limiter
    from flask_limiter.util import get_remote_address
except Exception:
    class _Limiter:
        def __init__(
            self,
            key_func=None,
            default_limits=None,
            storage_uri=None,
            headers_enabled=True,
            key_prefix="",
        ):
            self.key_func = key_func or (lambda: "127.0.0.1")
            self.default_limits = default_limits or []
            self.storage_uri = storage_uri
            self.headers_enabled = headers_enabled
            self.key_prefix = key_prefix
            self._max_requests = None
            self._window_seconds = None
            self._buckets: dict[str, dict[str, float]] = {}

        def _parse_limit(self):
            if not self.default_limits:
                return None

            limit = self.default_limits[0]
            if callable(limit):
                limit = limit()

            if isinstance(limit, str):
                parts = limit.split()
                try:
                    count = int(parts[0])
                except (ValueError, IndexError):
                    return None

                unit = "".join(parts[1:]).lower()
                if "second" in unit:
                    window = 1
                elif "minute" in unit:
                    window = 60
                elif "hour" in unit:
                    window = 3600
                else:
                    window = 60
                return count, window

            if isinstance(limit, (int, float)):
                return int(limit), 60

            return None

        def init_app(self, app):
            parsed = self._parse_limit()
            if not parsed:
                return

            self._max_requests, self._window_seconds = parsed

            @app.before_request
            def _check_rate_limit():  # pragma: no cover - fallback logic
                key = self.key_func()
                bucket = self._buckets.get(key)
                now = time.time()

                if not bucket or now - bucket["start"] >= self._window_seconds:
                    bucket = {"start": now, "count": 0}
                    self._buckets[key] = bucket

                bucket["count"] += 1
                if bucket["count"] > self._max_requests:
                    raise TooManyRequests(description="Rate limit exceeded")

        def limit(self, *args, **kwargs):  # pragma: no cover - compatibility stub
            def decorator(func):
                return func

            return decorator

    def get_remote_address():
        return "127.0.0.1"

Limiter = _Limiter
from werkzeug.exceptions import HTTPException, TooManyRequests

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
