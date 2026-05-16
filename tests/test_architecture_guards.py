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
    tree = ast.parse(source)

    direct_names = {"build_file_manifest"}
    module_aliases = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "system.apply_utils":
                for alias in node.names:
                    if alias.name == "build_file_manifest":
                        direct_names.add(alias.asname or alias.name)
            if node.module == "system":
                for alias in node.names:
                    if alias.name == "apply_utils":
                        module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "system.apply_utils":
                    if alias.asname:
                        module_aliases.add(alias.asname)
                    else:
                        module_aliases.add("system")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name) and node.func.id in direct_names:
            return True

        if isinstance(node.func, ast.Attribute) and node.func.attr == "build_file_manifest":
            owner = node.func.value
            if isinstance(owner, ast.Name):
                if owner.id in module_aliases:
                    return True
            elif (
                isinstance(owner, ast.Attribute)
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "system"
                and owner.attr == "apply_utils"
            ):
                return True

    return False


def _status_composition_ast_violations(source: str, *, allow_interprocedural: bool = False) -> list[str]:
    """
    Lightweight semantic guard.
    Default scope is intra-function provenance inside get_status().
    When allow_interprocedural=True, permit a constrained one-hop resolution for
    local helper functions that immediately return canonical builder results.
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

    function_defs: dict[str, ast.FunctionDef] = {}
    if allow_interprocedural:
        for top_level_node in tree.body:
            if isinstance(top_level_node, ast.FunctionDef):
                function_defs[top_level_node.name] = top_level_node

    get_status = None
    for top_node in tree.body:
        if isinstance(top_node, ast.FunctionDef) and top_node.name == "get_status":
            get_status = top_node
            break
    if get_status is None:
        return sorted(targets)

    builder_vars: dict[str, str] = {}

    def _function_return_builder_call(fn: ast.FunctionDef) -> str | None:
        """
        Resolve the returned builder provenance for a helper function.

        Intentionally constrained:
        - One-hop only (helper must return a canonical builder call or a simple name alias of one).
        - Local function defs only (no imports/modules).
        """
        helper_builder_vars: dict[str, str] = {}

        def _resolve_value(value: ast.AST) -> str | None:
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if value.func.id in expected_builders.values():
                    return value.func.id
                return None
            if isinstance(value, ast.Name):
                return helper_builder_vars.get(value.id)
            return None

        for stmt in fn.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue  # docstring
            if isinstance(stmt, ast.Return):
                if stmt.value is None:
                    return None
                return _resolve_value(stmt.value)
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                resolved = _resolve_value(stmt.value)
                if resolved is not None:
                    helper_builder_vars[stmt.targets[0].id] = resolved
                continue
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
                resolved = _resolve_value(stmt.value)
                if resolved is not None:
                    helper_builder_vars[stmt.target.id] = resolved
                continue
            # Anything else increases false positives; bail out.
            return None

        return None

    def _resolve_any_builder_from_helper_call(value: ast.AST) -> str | None:
        if not allow_interprocedural:
            return None
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)):
            return None

        helper_name = value.func.id
        if helper_name in expected_builders.values():
            return helper_name

        helper_def = function_defs.get(helper_name)
        if helper_def is None:
            return None

        return _function_return_builder_call(helper_def)

    def _is_builder_value(key: str, value: ast.AST) -> bool:
        # Accepted provenance is intentionally narrow:
        # - direct builder call
        # - name alias that resolves to a builder call
        # - for "shares", a single-level ["shares"] subscript from build_shares_status(...)
        expected = expected_builders[key]
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            if value.func.id == expected:
                return True
            helper_builder = _resolve_any_builder_from_helper_call(value)
            return helper_builder is not None and helper_builder == expected
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
            resolved = _resolve_any_builder_from_helper_call(value)
            builder_vars[target.id] = resolved or value.func.id
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

    for walk_node in ast.walk(get_status):
        if (
            not isinstance(walk_node, ast.Assign)
            or len(walk_node.targets) != 1
            or not isinstance(walk_node.targets[0], ast.Subscript)
        ):
            continue
        sub = walk_node.targets[0]
        if isinstance(sub, ast.Subscript):
            if not (isinstance(sub.value, ast.Name) and sub.value.id == "status"):
                continue
            if not (isinstance(sub.slice, ast.Constant) and isinstance(sub.slice.value, str)):
                continue
            key = sub.slice.value
            if key not in targets:
                continue
            seen.add(key)
            if isinstance(walk_node.value, ast.Dict):
                violations.append(key)
                continue
            if not _is_builder_value(key, walk_node.value):
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


def test_manifest_wrapper_guard_catches_alias_import_pattern_fixture():
    old_pattern = """
import system.apply_utils as au
def do_apply():
    return au.build_file_manifest()
"""
    assert _has_route_level_manifest_wrapper_usage(old_pattern) is True


def test_manifest_wrapper_guard_ignores_strings_and_comments_fixture():
    good_pattern = '''
def do_apply():
    # build_file_manifest()
    note = "build_file_manifest()"
    return note
'''
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


def test_status_composition_guard_ast_rejects_dict_literal_via_name_alias():
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


def test_status_composition_guard_ast_allows_subscript_from_builder_result():
    good = """
def get_status():
    state = {}
    shares_status = build_shares_status(state)
    status = {
        "pool": build_pool_status(state),
        "shares": shares_status["shares"],
        "snapraid": build_snapraid_status(state),
        "nonraid": build_nonraid_status(state),
    }
    return status
"""
    assert _status_composition_ast_violations(good) == []


def test_status_composition_guard_ast_rejects_cross_function_passthrough():
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


def test_status_composition_guard_ast_allows_one_hop_helper_passthrough_when_enabled():
    good = """
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
    assert _status_composition_ast_violations(good, allow_interprocedural=True) == []


def test_status_composition_guard_ast_rejects_two_hop_helper_chain_even_when_enabled():
    bad = """
def pool_leaf(state):
    return build_pool_status(state)

def make_pool(state):
    return pool_leaf(state)

def get_status():
    state = {}
    status = {}
    status["pool"] = make_pool(state)
    status["shares"] = build_shares_status(state)
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "pool" in _status_composition_ast_violations(bad, allow_interprocedural=True)


def test_status_composition_guard_ast_allows_single_level_shares_subscript():
    good = """
def get_status():
    state = {}
    shares_status = build_shares_status(state)
    status = {}
    status["pool"] = build_pool_status(state)
    status["shares"] = shares_status["shares"]
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert _status_composition_ast_violations(good) == []


def test_status_composition_guard_ast_rejects_nested_subscript_shares():
    bad = """
def get_status():
    state = {}
    shares_status = build_shares_status(state)
    status = {}
    status["pool"] = build_pool_status(state)
    # Single-level shares_status["shares"] is allowed; deeper subscripts are not.
    status["shares"] = shares_status["services"]["smbd"]
    status["snapraid"] = build_snapraid_status(state)
    status["nonraid"] = build_nonraid_status(state)
    return status
"""
    assert "shares" in _status_composition_ast_violations(bad)


def test_status_composition_guard_ast_rejects_chained_call():
    bad = """
def get_status():
    state = {}
    status = {}
    status["pool"] = build_pool_status(state).copy()
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
