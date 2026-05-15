from flask import Blueprint, Response, jsonify, request, stream_with_context

from system.sse import sse_subprocess
from system.nonraid_utils import (
    is_nonraid_installed,
    nmdctl_check,
    nmdctl_mount,
    nmdctl_start,
    nmdctl_stop,
    nmdctl_status,
    nmdctl_unmount,
    parse_nmdstat,
)
from system.state import read_state, write_state

nonraid_bp = Blueprint("nonraid", __name__)

_VALID_CHECK_MODES = {"CORRECT", "NOCORRECT"}
_VALID_FS = {"xfs", "btrfs", "ext4", "zfs"}
_VALID_PARITY = {"single", "dual"}


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
        cmds = [
            ["apt-get", "install", "-y", "gpg"],
            [
                "bash", "-c",
                'wget -qO- "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x0B1768BC3340D235F3A5CB25186129DABB062BFD"'
                " | gpg --dearmor -o /usr/share/keyrings/nonraid-ppa.gpg",
            ],
            [
                "bash", "-c",
                'echo "deb [signed-by=/usr/share/keyrings/nonraid-ppa.gpg]'
                ' https://ppa.launchpadcontent.net/qvr/nonraid/ubuntu noble main"'
                " | tee /etc/apt/sources.list.d/nonraid-ppa.list",
            ],
            ["apt-get", "update"],
            ["apt-get", "install", "-y",
             "linux-headers-amd64",
             "nonraid-dkms", "nonraid-tools"],
        ]
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
        for event in sse_subprocess(
            ["nmdctl", "create"],
            "Array created successfully",
            "ERROR (exit {returncode})",
        ):
            yield event

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.post("/api/nonraid/config")
def set_nonraid_config():
    data = request.get_json(silent=True) or {}

    parity_mode = data.get("parity_mode", "single")
    filesystem = data.get("filesystem", "xfs")
    luks = data.get("luks", False)
    turbo_write = data.get("turbo_write", False)
    check_schedule = data.get("check_schedule", "quarterly")
    check_correct = data.get("check_correct", False)
    check_speed_limit = data.get("check_speed_limit", 200)

    if parity_mode not in _VALID_PARITY:
        return jsonify({"error": "invalid parity_mode"}), 400
    if filesystem not in _VALID_FS:
        return jsonify({"error": "invalid filesystem", "valid": sorted(_VALID_FS)}), 400
    if not isinstance(check_speed_limit, int) or not (10 <= check_speed_limit <= 1000):
        return jsonify({"error": "check_speed_limit must be 10–1000 MB/s"}), 400

    write_state({
        "nonraid_parity_mode": parity_mode,
        "nonraid_filesystem": filesystem,
        "nonraid_luks": luks,
        "nonraid_turbo_write": turbo_write,
        "nonraid_check_schedule": check_schedule,
        "nonraid_check_correct": check_correct,
        "nonraid_check_speed_limit": check_speed_limit,
    })
    return jsonify({"ok": True}), 200


@nonraid_bp.post("/api/nonraid/roles")
def post_nonraid_roles():
    data = request.get_json(silent=True) or {}
    parity_disks = data.get("parity_disks", [])
    data_disks = data.get("data_disks", [])

    state = read_state()
    parity_mode = state.get("nonraid_parity_mode", "single")
    expected = 2 if parity_mode == "dual" else 1

    if len(parity_disks) != expected:
        return jsonify({"error": f"parity_mode '{parity_mode}' requires exactly {expected} parity disk(s)"}), 400
    if not data_disks:
        return jsonify({"error": "at least one data disk is required"}), 400
    if set(parity_disks) & set(data_disks):
        return jsonify({"error": "a disk cannot be assigned both parity and data roles"}), 400

    write_state({
        "nonraid_parity_disks": parity_disks,
        "nonraid_data_disks": data_disks,
    })
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
    # honour explicit override; fall back to stored preference
    if "mode" in data:
        mode = data["mode"].upper()
        if mode not in _VALID_CHECK_MODES:
            return jsonify({"error": "mode must be CORRECT or NOCORRECT"}), 400
    else:
        state = read_state()
        mode = "CORRECT" if state.get("nonraid_check_correct") else "NOCORRECT"

    safe_mode = {
        "CORRECT": "CORRECT",
        "NOCORRECT": "NOCORRECT",
    }[mode]

    def _stream():
        for event in sse_subprocess(
            ["nmdctl", "check", safe_mode],
            "Check complete (exit {returncode})",
            "Check complete (exit {returncode})",
            popen_factory=lambda _cmd: nmdctl_check(safe_mode),
        ):
            yield event

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.get("/api/nonraid/check/status")
def get_nonraid_check_status():
    return jsonify(parse_nmdstat()), 200
