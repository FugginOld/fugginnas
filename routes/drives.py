import subprocess

from flask import Blueprint, jsonify

from system.drive_utils import list_drives

drives_bp = Blueprint("drives", __name__)


@drives_bp.get("/api/drives")
def get_drives():
    try:
        drives = list_drives()
    except subprocess.CalledProcessError:
        return jsonify({"error": "lsblk failed"}), 500
    return jsonify({"drives": drives}), 200
