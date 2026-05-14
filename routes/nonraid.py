from flask import Blueprint, Response, jsonify, request, stream_with_context

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
from system.state import write_state

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
    import subprocess

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
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                yield f"data: {line.rstrip()}\n\n"
            proc.wait()
            if proc.returncode != 0:
                yield f"data: ERROR (exit {proc.returncode})\n\n"
                return
        yield "data: NonRAID install complete\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.post("/api/nonraid/create")
def post_nonraid_create():
    import subprocess

    def _stream():
        proc = subprocess.Popen(
            ["nmdctl", "create"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            yield f"data: {line.rstrip()}\n\n"
        proc.wait()
        if proc.returncode == 0:
            yield "data: Array created successfully\n\n"
        else:
            yield f"data: ERROR (exit {proc.returncode})\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.post("/api/nonraid/config")
def set_nonraid_config():
    data = request.get_json(silent=True) or {}

    parity_mode = data.get("parity_mode", "single")
    filesystem = data.get("filesystem", "xfs")
    luks = data.get("luks", False)
    turbo_write = data.get("turbo_write", False)
    check_schedule = data.get("check_schedule", "quarterly")

    if parity_mode not in _VALID_PARITY:
        return jsonify({"error": "invalid parity_mode"}), 400
    if filesystem not in _VALID_FS:
        return jsonify({"error": "invalid filesystem", "valid": sorted(_VALID_FS)}), 400

    write_state({
        "nonraid_parity_mode": parity_mode,
        "nonraid_filesystem": filesystem,
        "nonraid_luks": luks,
        "nonraid_turbo_write": turbo_write,
        "nonraid_check_schedule": check_schedule,
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
    mode = data.get("mode", "NOCORRECT").upper()
    if mode not in _VALID_CHECK_MODES:
        return jsonify({"error": "mode must be CORRECT or NOCORRECT"}), 400

    def _stream():
        proc = nmdctl_check(mode)
        for line in proc.stdout:
            yield f"data: {line.rstrip()}\n\n"
        proc.wait()
        yield f"data: Check complete (exit {proc.returncode})\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")


@nonraid_bp.get("/api/nonraid/check/status")
def get_nonraid_check_status():
    return jsonify(parse_nmdstat()), 200
