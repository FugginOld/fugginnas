import subprocess


def sse_subprocess(cmd, done_msg, error_msg):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    lines = []
    for line in proc.stdout:
        clean = line.rstrip()
        lines.append(clean)
        yield f"data: {clean}\n\n"

    proc.wait()
    if proc.returncode == 0:
        yield f"data: {done_msg}\n\n"
        return

    detail = ""
    for line in reversed(lines):
        if line.strip():
            detail = line.strip()
            break
    yield f"data: {error_msg.format(returncode=proc.returncode, stderr=detail)}\n\n"
