import subprocess


def sse_subprocess(cmd, done_msg, error_msg, popen_factory=None):
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
    for line in proc.stdout:
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
