import subprocess

from flask import Blueprint, Response, stream_with_context

from system.apply_utils import apply_all, backup_fstab, build_file_manifest
from system.state import read_state

apply_bp = Blueprint("apply", __name__)


@apply_bp.post("/api/apply")
def do_apply():
    def _stream():
        state = read_state()
        manifest = build_file_manifest()
        paths = [e["path"] for e in manifest]

        yield f"data: Starting apply ({len(paths)} files)\n\n"

        if "/etc/fstab" in paths:
            yield "data: Backing up /etc/fstab\n\n"
            backup_fstab("/etc/fstab")
            yield "data: OK\n\n"

        written = apply_all()

        for path in written:
            yield f"data: Wrote {path}\n\n"

        if state.get("backend") == "snapraid":
            for timer in ("snapraid-sync.timer", "snapraid-scrub.timer"):
                result = subprocess.run(
                    ["systemctl", "enable", "--now", timer],
                    capture_output=True, text=True,
                )
                status = "OK" if result.returncode == 0 else f"WARN: {result.stderr.strip()}"
                yield f"data: systemctl enable {timer}: {status}\n\n"

        for timer in ("FugginNAS-mover.timer",):
            result = subprocess.run(
                ["systemctl", "enable", "--now", timer],
                capture_output=True, text=True,
            )
            status = "OK" if result.returncode == 0 else f"WARN: {result.stderr.strip()}"
            yield f"data: systemctl enable {timer}: {status}\n\n"

        yield "data: Apply complete\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")
