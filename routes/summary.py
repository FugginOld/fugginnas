from flask import Blueprint, jsonify

from system.apply_utils import build_file_manifest_for_state
from system.state import read_state

summary_bp = Blueprint("summary", __name__)


@summary_bp.get("/api/summary")
def get_summary():
    state = read_state()
    files = build_file_manifest_for_state(state)
    return jsonify({"files": files}), 200
