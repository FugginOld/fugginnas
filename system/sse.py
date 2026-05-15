import subprocess


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
        lambda command: subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
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
