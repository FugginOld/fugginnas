import subprocess


_DISALLOWED_SHELL_CHARS = set(";|&`$<>")
_ALLOWED_NMDCTL_CHECK_MODES = {"CORRECT", "NOCORRECT"}


def _validate_command(command):
    if not isinstance(command, (list, tuple)) or not command:
        raise ValueError("command must be a non-empty list/tuple of strings")
    for part in command:
        if not isinstance(part, str) or not part.strip():
            raise ValueError("each command argument must be a non-empty string")
        if any(ch in part for ch in _DISALLOWED_SHELL_CHARS):
            raise ValueError("command contains disallowed shell metacharacters")


def _validate_allowed_command(command):
    if (
        len(command) == 3
        and command[0] == "nmdctl"
        and command[1] == "check"
        and command[2] in _ALLOWED_NMDCTL_CHECK_MODES
    ):
        return
    raise ValueError("command is not in the allowlist")


def sse_subprocess(cmd, done_msg, error_msg, popen_factory=None):
    """Stream a subprocess as SSE events.

    Contract:
    - Forward each process output line as SSE-framed text: ``data: ...\\n\\n``.
    - On exit code 0, emit one done sentinel when ``done_msg`` is not ``None``.
    - On non-zero exit, emit one error sentinel from ``error_msg``.
    - ``{returncode}`` and ``{stderr}`` placeholders are available in sentinels.
    - ``stderr`` placeholder is sourced from the last non-empty forwarded line.
    """
    spawn = popen_factory or (
        lambda command: (
            _validate_command(command),
            _validate_allowed_command(command),
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            ),
        )[1]
    )
    proc = spawn(cmd)

    lines = []
    for line in (proc.stdout or []):
        clean = line.rstrip()
        lines.append(clean)
        yield f"data: {clean}\n\n"

    proc.wait()
    detail = ""
    for line in reversed(lines):
        if line.strip():
            detail = line.strip()
            break

    if proc.returncode == 0:
        if done_msg is not None:
            yield f"data: {done_msg.format(returncode=proc.returncode, stderr=detail)}\n\n"
        return

    yield f"data: {error_msg.format(returncode=proc.returncode, stderr=detail)}\n\n"
