from flask import Blueprint, jsonify, request

from system.state import write_state

backend_bp = Blueprint("backend", __name__)

_VALID_BACKENDS = {"snapraid", "nonraid", "mergerfs"}


@backend_bp.post("/api/backend")
def set_backend():
    data = request.get_json(silent=True) or {}
    backend = data.get("backend")
    if backend not in _VALID_BACKENDS:
        return jsonify({"error": "invalid backend", "valid": sorted(_VALID_BACKENDS)}), 400
    write_state({"backend": backend})
    return jsonify({"backend": backend}), 200
