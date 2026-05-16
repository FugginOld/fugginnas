from flask import Blueprint, jsonify, request

from system.state import write_known_state

pool_bp = Blueprint("pool", __name__)

_VALID_WRITE_POLICIES = {"mfs", "lfs", "existing"}


@pool_bp.post("/api/pool")
def set_pool():
    data = request.get_json(silent=True) or {}

    pool_mount = data.get("pool_mount")
    cache_mount = data.get("cache_mount")
    data_mounts = data.get("data_mounts")
    write_policy = data.get("write_policy", "mfs")

    if not pool_mount:
        return jsonify({"error": "pool_mount required"}), 400
    if not cache_mount:
        return jsonify({"error": "cache_mount required"}), 400
    if not data_mounts:
        return jsonify({"error": "data_mounts must be a non-empty list"}), 400
    if write_policy not in _VALID_WRITE_POLICIES:
        return jsonify({"error": "invalid write_policy", "valid": sorted(_VALID_WRITE_POLICIES)}), 400

    write_known_state({
        "pool_mount": pool_mount,
        "cache_mount": cache_mount,
        "data_mounts": data_mounts,
        "write_policy": write_policy,
    })
    return jsonify({"pool_mount": pool_mount, "cache_mount": cache_mount,
                    "data_mounts": data_mounts, "write_policy": write_policy}), 200
