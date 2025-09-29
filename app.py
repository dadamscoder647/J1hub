import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()
jwt = JWTManager()

def create_app(config_object: str | type | None = None, **config_overrides):
    app = Flask(__name__)
    if config_object is None:
        app.config.from_object("config.Config")
    else:
        app.config.from_object(config_object)

    if config_overrides:
        app.config.update(config_overrides)

    default_upload_folder = os.path.join(app.root_path, "uploads")
    app.config.setdefault("UPLOAD_FOLDER", default_upload_folder)
    app.config.setdefault("UPLOAD_URL_PREFIX", "/uploads")

    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from routes.verify import verify_bp

    app.register_blueprint(verify_bp)

    @app.route("/")
    def root():
        return jsonify({"status": "ok"})

    return app