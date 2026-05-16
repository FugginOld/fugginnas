from flask import Blueprint, Response, jsonify, request, stream_with_context

from system.sse import sse_subprocess
from system.nonraid_utils import (
    build_nonraid_check_operation,
    build_nonraid_config_updates,
    build_nonraid_create_operation,
    build_nonraid_install_commands,
    build_nonraid_roles_updates,
    is_nonraid_installed,
    nmdctl_check,
    nmdctl_mount,
    nmdctl_start,
    nmdctl_status,
    nmdctl_stop,
    nmdctl_unmount,
    parse_nmdstat,
    resolve_nonraid_check_mode,
)
from system.state import read_state, write_known_state

nonraid_bp = Blueprint("nonraid", __name__)


@nonraid_bp.get("/api/nonraid/status")
def get_nonraid_status():
    return jsonify(nmdctl_status()), 200


@nonraid_bp.get("/api/nonraid/install")
def get_nonraid_install():
    installed = is_nonraid_installed()
    return jsonify({"installed": installed}), 200


@nonraid_bp.post("/api/nonraid/install")
def post_nonraid_install():
    def _stream():
        cmds = build_nonraid_install_commands()
        for cmd in cmds:
            yield f"data: Running: {' '.join(cmd)}\n\n"
            for event in sse_subprocess(cmd, None, "ERROR (exit {returncode})"):
                yield event
                if event.startswith("data: ERROR (exit "):
                    return
        yield "data: NonRAID install complete\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.post("/api/nonraid/create")
def post_nonraid_create():
    def _stream():
        operation = build_nonraid_create_operation()
        for event in sse_subprocess(
            operation["cmd"],
            operation["done_msg"],
            operation["error_msg"],
        ):
            yield event

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.post("/api/nonraid/config")
def set_nonraid_config():
    data = request.get_json(silent=True) or {}
    try:
        updates = build_nonraid_config_updates(data)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("invalid filesystem|"):
            return jsonify({"error": "invalid filesystem"}), 400
        return jsonify({"error": "invalid configuration"}), 400
    write_known_state(updates)
    return jsonify({"ok": True}), 200


@nonraid_bp.post("/api/nonraid/roles")
def post_nonraid_roles():
    data = request.get_json(silent=True) or {}
    parity_disks = data.get("parity_disks", [])
    data_disks = data.get("data_disks", [])

    state = read_state()
    parity_mode = state.get("nonraid_parity_mode", "single")
    try:
        updates = build_nonraid_roles_updates(parity_mode, parity_disks, data_disks)
    except ValueError:
        return jsonify({"error": "invalid nonraid roles configuration"}), 400
    write_known_state(updates)
    return jsonify({"ok": True}), 200


@nonraid_bp.post("/api/nonraid/start")
def post_nonraid_start():
    ok, msg = nmdctl_start()
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)


@nonraid_bp.post("/api/nonraid/stop")
def post_nonraid_stop():
    ok, msg = nmdctl_stop()
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)


@nonraid_bp.post("/api/nonraid/mount")
def post_nonraid_mount():
    ok, msg = nmdctl_mount()
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)


@nonraid_bp.post("/api/nonraid/unmount")
def post_nonraid_unmount():
    ok, msg = nmdctl_unmount()
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)


@nonraid_bp.post("/api/nonraid/check")
def post_nonraid_check():
    data = request.get_json(silent=True) or {}
    state = read_state()
    try:
        safe_mode = resolve_nonraid_check_mode(data.get("mode"), state)
    except ValueError:
        return jsonify({"error": "Invalid check mode."}), 400
    operation = build_nonraid_check_operation(safe_mode)

    def _stream():
        for event in sse_subprocess(
            operation["cmd"],
            operation["done_msg"],
            operation["error_msg"],
            popen_factory=lambda _cmd: nmdctl_check(safe_mode),
        ):
            yield event

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.get("/api/nonraid/check/status")
def get_nonraid_check_status():
    return jsonify(parse_nmdstat()), 200
