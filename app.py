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

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.listings import listings_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(listings_bp, url_prefix="/listings")

    @app.route("/")
    def root():
        return jsonify({"status": "ok"})

    return app