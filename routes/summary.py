from flask import Blueprint, jsonify

from system.apply_utils import build_file_manifest

summary_bp = Blueprint("summary", __name__)


@summary_bp.get("/api/summary")
def get_summary():
    files = build_file_manifest()
    return jsonify({"files": files}), 200
