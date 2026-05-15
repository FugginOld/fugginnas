import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    _REPO_ROOT / "routes/apply.py",
    _REPO_ROOT / "routes/nonraid.py",
]


def _has_inline_sse_subprocess_loop(source: str) -> bool:
    """
    Guard rule (narrow):
    - A local `_stream` function contains BOTH:
      1) subprocess loop markers (`subprocess.Popen` or `for line in proc.stdout`)
      2) direct SSE line yield marker (any of: `yield f"data:`, `yield f'data:`,
         `yield "data:`, `yield 'data:`).
    This flags old inline SSE subprocess loop style while allowing delegation
    to `sse_subprocess(...)`.
    """
    chunks = source.split("def _stream(")
    for chunk in chunks[1:]:
        # Limit to stream function body region heuristically by cutting at next top-level def/decorator.
        body = chunk.split("\n\ndef ", 1)[0].split("\n\n@", 1)[0]
        has_subprocess_loop = ("subprocess.Popen" in body) or ("for line in proc.stdout" in body)
        has_direct_sse_yield = bool(re.search(r"""yield\s+f?['"]data:""", body))
        if has_subprocess_loop and has_direct_sse_yield:
            return True
    return False


def test_guard_detector_catches_known_old_inline_pattern_fixture():
    old_pattern = """
def _stream():
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        yield f"data: {line.rstrip()}\\n\\n"
    proc.wait()
    if proc.returncode != 0:
        yield f"data: ERROR (exit {proc.returncode})\\n\\n"
"""
    assert _has_inline_sse_subprocess_loop(old_pattern) is True


def test_no_inline_sse_subprocess_loops_in_target_routes():
    offenders = []
    for path in TARGETS:
        src = path.read_text(encoding="utf-8")
        if _has_inline_sse_subprocess_loop(src):
            offenders.append(str(path))
    assert offenders == [], f"Inline SSE subprocess loop(s) detected in: {offenders}"
