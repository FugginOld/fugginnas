import subprocess
import tempfile

from flask import Blueprint, jsonify, request

from system.snapraid_conf import generate_conf
from system.state import read_state, write_state

snapraid_bp = Blueprint("snapraid", __name__)

_VALID_SCRUB = {"weekly", "monthly", "off"}
_VALID_PARITY = {"single", "dual"}


@snapraid_bp.post("/api/snapraid")
def set_snapraid():
    data = request.get_json(silent=True) or {}

    parity_mode = data.get("parity_mode", "single")
    parity_disks = data.get("parity_disks") or []
    data_mounts = data.get("data_mounts") or []
    sync_time = data.get("sync_time", "02:00")
    scrub_schedule = data.get("scrub_schedule", "weekly")

    if parity_mode not in _VALID_PARITY:
        return jsonify({"error": "invalid parity_mode"}), 400
    if not parity_disks:
        return jsonify({"error": "parity_disks required"}), 400
    if parity_mode == "dual" and len(parity_disks) < 2:
        return jsonify({"error": "dual parity requires two parity_disks"}), 400
    if scrub_schedule not in _VALID_SCRUB:
        return jsonify({"error": "invalid scrub_schedule", "valid": sorted(_VALID_SCRUB)}), 400

    write_state({
        "snapraid_parity_mode": parity_mode,
        "snapraid_parity_disks": parity_disks,
        "snapraid_data_mounts": data_mounts,
        "snapraid_sync_time": sync_time,
        "snapraid_scrub_schedule": scrub_schedule,
    })
    return jsonify({"ok": True}), 200


@snapraid_bp.get("/api/snapraid/dry-run")
def snapraid_dry_run():
    state = read_state()
    if not state.get("snapraid_parity_disks"):
        return jsonify({"error": "snapraid not configured"}), 400

    conf = generate_conf(
        parity_disks=state.get("snapraid_parity_disks", []),
        data_mounts=state.get("snapraid_data_mounts", []),
        parity_mode=state.get("snapraid_parity_mode", "single"),
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(conf)
        tmp_path = f.name

    result = subprocess.run(
        ['snapraid', '-c', tmp_path, 'status'],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return jsonify({"ok": True, "output": result.stdout})
    return jsonify({"ok": False, "error": result.stderr}), 500
