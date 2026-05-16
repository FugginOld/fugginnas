import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    _REPO_ROOT / "routes/apply.py",
    _REPO_ROOT / "routes/nonraid.py",
]
ROUTES_DIR = _REPO_ROOT / "routes"
WRITE_STATE_ALLOWLIST: set[str] = set()
STATUS_FILE = _REPO_ROOT / "system" / "status.py"


def _has_inline_sse_subprocess_loop(source: str) -> bool:
    """
    Guard rule (narrow):
    - A local `_stream` function contains BOTH:
      1) subprocess loop markers (`subprocess.Popen` or `for line in proc.stdout`)
      2) direct SSE line yield marker (any of: `yield f"data:`, `yield f'data:`,
         `yield "data:`, `yield 'data:'`).
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


def _has_route_level_manifest_wrapper_usage(source: str) -> bool:
    """
    Guard rule:
    - Disallow route-level calls to `build_file_manifest(...)` wrapper.
    - Allow explicit-state seam `build_file_manifest_for_state(...)`.
    """
    return bool(re.search(r"\bbuild_file_manifest\s*\(", source))


def _status_composition_ast_violations(source: str) -> list[str]:
    """
    Lightweight semantic guard.
    Scope is intentionally limited to intra-function provenance inside get_status().
    This does not attempt cross-function or interprocedural data-flow verification.
    """
    tree = ast.parse(source)
    expected_builders = {
        "pool": "build_pool_status",
        "shares": "build_shares_status",
        "snapraid": "build_snapraid_status",
        "nonraid": "build_nonraid_status",
    }
    targets = set(expected_builders.keys())
    violations: list[str] = []
    seen: set[str] = set()

    get_status = None
    for top_node in tree.body:
        if isinstance(top_node, ast.FunctionDef) and top_node.name == "get_status":
            get_status = top_node
            break
    if get_status is None:
        return sorted(targets)

    builder_vars: dict[str, str] = {}

    def _is_builder_value(key: str, value: ast.AST) -> bool:
        expected = expected_builders[key]
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            return value.func.id == expected
        if isinstance(value, ast.Name):
            return builder_vars.get(value.id) == expected
        if key == "shares" and isinstance(value, ast.Subscript):
            if (
                isinstance(value.value, ast.Name)
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "shares"
            ):
                return builder_vars.get(value.value.id) == "build_shares_status"
        return False

    for stmt in get_status.body:
        target = None
        value = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            target = stmt.target
            value = stmt.value
        else:
            continue

        if isinstance(target, ast.Name) and isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            builder_vars[target.id] = value.func.id
            continue

        if isinstance(target, ast.Name) and isinstance(value, ast.Name):
            if value.id in builder_vars:
                builder_vars[target.id] = builder_vars[value.id]
            continue

        if isinstance(target, ast.Name) and target.id == "status" and isinstance(value, ast.Dict):
            for key_node, value_node in zip(value.keys, value.values):
                if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
                    continue
                key = key_node.value
                if key not in targets:
                    continue
                seen.add(key)
                if not _is_builder_value(key, value_node):
                    violations.append(key)
            continue

    for node in ast.walk(get_status):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Subscript):
            continue
        sub = node.targets[0]
        if isinstance(sub, ast.Subscript):
            if not (isinstance(sub.value, ast.Name) and sub.value.id == "status"):
                continue
            if not (isinstance(sub.slice, ast.Constant) and isinstance(sub.slice.value, str)):
                continue
            key = sub.slice.value
            if key not in targets:
                continue
            seen.add(key)
            if isinstance(node.value, ast.Dict):
                violations.append(key)
                continue
            if not _is_builder_value(key, node.value):
                violations.append(key)

    for key in targets - seen:
        violations.append(key)

    return sorted(set(violations))


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


def test_manifest_wrapper_guard_catches_known_old_pattern_fixture():
    old_pattern = """
def do_apply():
    manifest = build_file_manifest()
    return manifest
"""
    assert _has_route_level_manifest_wrapper_usage(old_pattern) is True


def test_manifest_wrapper_guard_allows_explicit_state_seam_fixture():
    good_pattern = """
def do_apply():
    state = read_state()
    manifest = build_file_manifest_for_state(state)
    return manifest
"""
    assert _has_route_level_manifest_wrapper_usage(good_pattern) is False


def test_no_inline_sse_subprocess_loops_in_target_routes():
    offenders = []
    for path in TARGETS:
        src = path.read_text(encoding="utf-8")
        if _has_inline_sse_subprocess_loop(src):
            offenders.append(str(path))
    assert offenders == [], f"Inline SSE subprocess loop(s) detected in: {offenders}"


def test_route_modules_direct_write_state_usage_is_allowlisted():
    offenders = []
    for path in sorted(ROUTES_DIR.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if re.search(r"\bwrite_state\s*\(", src) and path.name not in WRITE_STATE_ALLOWLIST:
            offenders.append(path.name)
    assert offenders == [], f"Direct write_state usage in non-allowlisted routes: {offenders}"


def test_route_modules_do_not_use_manifest_wrapper():
    offenders = []
    for path in sorted(ROUTES_DIR.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if _has_route_level_manifest_wrapper_usage(src):
            offenders.append(path.name)
    assert offenders == [], f"Route-level build_file_manifest wrapper usage detected: {offenders}"


def test_status_composition_guard_ast_catches_inline_panel_fixture():
    bad = """
def get_status():
    state = {}
    status = {}
    status["pool"] = {"mount": "/mnt/pool"}
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad)


def test_status_composition_guard_ast_allows_builder_fixture():
    good = """
def get_status():
    state = {}
    status = {}
    status["pool"] = build_pool_status(state)
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert _status_composition_ast_violations(good) == []


def test_status_composition_guard_ast_catches_non_builder_assignment_fixture():
    bad = """
def get_status():
    state = {}
    status = {}
    pool_status = {"mount": "/mnt/pool"}
    status["pool"] = pool_status
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad)


def test_status_composition_guard_ast_allows_local_alias_indirection_fixture():
    good = """
def get_status():
    state = {}
    status = {}
    pool_panel = build_pool_status(state)
    alias_1 = pool_panel
    alias_2 = alias_1
    status["pool"] = alias_2
    shares_status = build_shares_status(state)
    status["shares"] = shares_status["shares"]
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert _status_composition_ast_violations(good) == []


def test_status_composition_guard_ast_rejects_unknown_helper_indirection_fixture():
    bad = """
def get_status():
    state = {}
    status = {}
    helper = derive_pool_panel(state)
    status["pool"] = helper
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad)


def test_status_composition_guard_ast_rejects_dict_literal_name_bypass_fixture():
    bad = """
def get_status():
    state = {}
    build_pool_status(state)  # decoy call
    pool_status = {"mount": "/mnt/pool"}
    status = {
        "pool": pool_status,
        "shares": build_shares_status(state),
        "snapraid": build_snapraid_status(state),
        "nonraid": build_nonraid_status(state),
    }
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad)


def test_status_composition_guard_ast_rejects_cross_function_passthrough_fixture():
    bad = """
def make_pool(state):
    return build_pool_status(state)

def get_status():
    state = {}
    status = {}
    status["pool"] = make_pool(state)
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad)


def test_status_get_status_composes_panel_builders():
    src = STATUS_FILE.read_text(encoding="utf-8")
    required_calls = [
        "build_pool_status(state)",
        "build_shares_status(state)",
        "build_snapraid_status(state)",
        "build_nonraid_status(state)",
    ]
    for call in required_calls:
        assert call in src, f"Missing composition call in get_status(): {call}"

    assert _status_composition_ast_violations(src) == []
