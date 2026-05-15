import pytest

from system.sse import sse_subprocess


class _Proc:
    def __init__(self, lines, returncode):
        self.stdout = lines
        self.returncode = returncode

    def wait(self):
        return self.returncode


@pytest.mark.parametrize(
    "name,lines,returncode,done_msg,error_msg,expected",
    [
        (
            "success_with_done",
            ["alpha\n", "beta\n"],
            0,
            "Done",
            "ERROR (exit {returncode})",
            ["data: alpha\n\n", "data: beta\n\n", "data: Done\n\n"],
        ),
        (
            "success_without_done",
            ["alpha\n"],
            0,
            None,
            "ERROR (exit {returncode})",
            ["data: alpha\n\n"],
        ),
        (
            "failure_with_stderr_placeholder",
            ["step one\n", "fatal boom\n"],
            7,
            "Done",
            "ERROR (exit {returncode}): {stderr}",
            ["data: step one\n\n", "data: fatal boom\n\n", "data: ERROR (exit 7): fatal boom\n\n"],
        ),
        (
            "empty_stdout_success",
            [],
            0,
            "Done",
            "ERROR (exit {returncode})",
            ["data: Done\n\n"],
        ),
        (
            "empty_stdout_failure",
            [],
            3,
            "Done",
            "ERROR (exit {returncode}): {stderr}",
            ["data: ERROR (exit 3): \n\n"],
        ),
    ],
)
def test_sse_subprocess_contract_cases(name, lines, returncode, done_msg, error_msg, expected):
    def _spawn(_cmd):
        return _Proc(lines, returncode)

    out = list(sse_subprocess(["cmd"], done_msg, error_msg, popen_factory=_spawn))
    assert out == expected, name


def test_sse_subprocess_uses_custom_popen_factory():
    calls = []

    def _spawn(cmd):
        calls.append(cmd)
        return _Proc(["ok\n"], 0)

    out = list(sse_subprocess(["nmdctl", "check"], "Done", "ERR (exit {returncode})", popen_factory=_spawn))
    assert calls == [["nmdctl", "check"]]
    assert out[-1] == "data: Done\n\n"


def test_sse_subprocess_contract_doc_present():
    doc = sse_subprocess.__doc__ or ""
    assert "SSE" in doc
    assert "data: ...\\n\\n" in doc
