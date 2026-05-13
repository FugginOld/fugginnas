from flask import Blueprint, jsonify

from system.apply_utils import apply_all

apply_bp = Blueprint("apply", __name__)


@apply_bp.post("/api/apply")
def do_apply():
    applied = apply_all()
    return jsonify({"ok": True, "applied": applied}), 200
