from flask import Blueprint, jsonify, request

from system.state import read_state, write_known_state

shares_bp = Blueprint("shares", __name__)

_VALID_PROTOCOLS = {"smb", "nfs", "both"}


@shares_bp.post("/api/shares")
def add_share():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    path = data.get("path")
    protocol = data.get("protocol")

    if not name:
        return jsonify({"error": "name required"}), 400
    if not path:
        return jsonify({"error": "path required"}), 400
    if protocol not in _VALID_PROTOCOLS:
        return jsonify({"error": "invalid protocol", "valid": sorted(_VALID_PROTOCOLS)}), 400

    share = {
        "name": name,
        "path": path,
        "protocol": protocol,
        "smb_guest_ok": data.get("smb_guest_ok", True),
        "smb_username": data.get("smb_username", ""),
        "smb_password": data.get("smb_password", ""),
        "nfs_allowed_hosts": data.get("nfs_allowed_hosts", "192.168.0.0/16"),
        "nfs_readonly": data.get("nfs_readonly", False),
    }

    state = read_state()
    shares = state.get("shares", [])
    shares.append(share)
    write_known_state({"shares": shares})
    return jsonify({"ok": True}), 200
