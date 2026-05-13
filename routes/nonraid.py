from flask import Blueprint, request, jsonify
from system.state import write_state

nonraid_bp = Blueprint('nonraid', __name__)

VALID_LEVELS = {0, 1, 5, 6, 10}


@nonraid_bp.post('/api/nonraid')
def set_nonraid():
    data = request.get_json(silent=True) or {}
    devices = data.get('devices')
    level = data.get('level')

    if not devices:
        return jsonify({'error': 'devices required and must be non-empty'}), 400
    if level is None:
        return jsonify({'error': 'level required'}), 400
    if level not in VALID_LEVELS:
        return jsonify({'error': f'level must be one of {sorted(VALID_LEVELS)}'}), 400

    name = data.get('name', 'md0')
    write_state({'nonraid': {'devices': devices, 'level': level, 'name': name}})
    return jsonify({'ok': True})
