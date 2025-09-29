"""Authentication blueprint placeholder."""

from flask import Blueprint, jsonify

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/ping", methods=["GET"])
def auth_ping():
    """Simple endpoint to confirm the auth blueprint is registered."""
    return jsonify({"status": "auth-ok"})
