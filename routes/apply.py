from flask import Blueprint, Response, stream_with_context

from system.apply_utils import apply_all_for_state, backup_fstab, build_file_manifest_for_state
from system.sse import sse_subprocess
from system.state import read_state

apply_bp = Blueprint("apply", __name__)


@apply_bp.post("/api/apply")
def do_apply():
    def _stream():
        state = read_state()
        manifest = build_file_manifest_for_state(state)
        paths = [e["path"] for e in manifest]

        yield f"data: Starting apply ({len(paths)} files)\n\n"

        if "/etc/fstab" in paths:
            yield "data: Backing up /etc/fstab\n\n"
            backup_fstab("/etc/fstab")
            yield "data: OK\n\n"

        written = apply_all_for_state(state)

        for path in written:
            yield f"data: Wrote {path}\n\n"

        if state.get("backend") == "snapraid":
            for timer in ("snapraid-sync.timer", "snapraid-scrub.timer"):
                for event in sse_subprocess(
                    ["systemctl", "enable", "--now", timer],
                    f"systemctl enable {timer}: OK",
                    f"systemctl enable {timer}: WARN: {{stderr}}",
                ):
                    yield event

        for event in sse_subprocess(
            ["systemctl", "enable", "--now", "FugginNAS-mover.timer"],
            "systemctl enable FugginNAS-mover.timer: OK",
            "systemctl enable FugginNAS-mover.timer: WARN: {stderr}",
        ):
            yield event

        yield "data: Apply complete\n\n"

    return Response(stream_with_context(_stream()), mimetype="text/event-stream")
