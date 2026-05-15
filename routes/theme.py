from flask import Blueprint, jsonify, request

from system.state import get_theme as read_theme, read_state, write_known_state

theme_bp = Blueprint("theme", __name__)

VALID_THEMES = {
    "default", "nord", "dracula", "solarized-dark", "gruvbox",
    "monokai", "catppuccin", "tokyo-night", "one-dark",
    "material", "github-dark", "synthwave",
    "tron-blue", "tron-red",
}


@theme_bp.get("/api/theme")
def get_theme():
    state = read_state()
    return jsonify({"theme": read_theme(state)}), 200


@theme_bp.post("/api/theme")
def post_theme():
    data = request.get_json(silent=True) or {}
    name = data.get("theme")
    if not name:
        return jsonify({"error": "theme name required"}), 400
    if name not in VALID_THEMES:
        return jsonify({"error": "unknown theme", "valid": sorted(VALID_THEMES)}), 400
    write_known_state({"theme": name})
    return jsonify({"ok": True}), 200
