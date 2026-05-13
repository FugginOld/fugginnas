from flask import Blueprint, jsonify, request

from system.state import write_state

mover_bp = Blueprint("mover", __name__)


@mover_bp.post("/api/mover")
def set_mover():
    data = request.get_json(silent=True) or {}

    schedule_time = data.get("schedule_time", "03:00")
    age_hours = data.get("age_hours", 24)
    min_free_pct = data.get("min_free_pct", 20)

    if not isinstance(age_hours, int) or age_hours < 0:
        return jsonify({"error": "age_hours must be a non-negative integer"}), 400
    if not isinstance(min_free_pct, int) or not (0 <= min_free_pct <= 100):
        return jsonify({"error": "min_free_pct must be 0-100"}), 400

    write_state({
        "mover_schedule_time": schedule_time,
        "mover_age_hours": age_hours,
        "mover_min_free_pct": min_free_pct,
    })
    return jsonify({"ok": True}), 200
