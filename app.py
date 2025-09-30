"""Application factory."""

import os

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from config import Config
from models import db
from routes.auth import auth_bp
from routes.listings import listings_bp
from routes.verify import admin_bp, verify_bp

migrate = Migrate()
jwt = JWTManager()


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    upload_dir = app.config.get("UPLOAD_DIR")
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(verify_bp, url_prefix="/verify")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(listings_bp, url_prefix="/listings")

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"})

    return app
