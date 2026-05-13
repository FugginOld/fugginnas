from flask import Blueprint, jsonify

from system.status import get_status

status_bp = Blueprint("status", __name__)


@status_bp.get("/api/status")
def get_status_route():
    return jsonify(get_status()), 200
