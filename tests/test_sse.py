from unittest.mock import patch

from system.sse import sse_subprocess


class _Proc:
    def __init__(self, lines, returncode):
        self.stdout = lines
        self.returncode = returncode

    def wait(self):
        return self.returncode


def test_sse_subprocess_forwards_lines_and_done_on_success():
    with patch("system.sse.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _Proc(["hello\n", "world\n"], 0)
        out = list(sse_subprocess(["echo", "ok"], "Done", "ERR (exit {returncode})"))

    assert out == [
        "data: hello\n\n",
        "data: world\n\n",
        "data: Done\n\n",
    ]


def test_sse_subprocess_forwards_lines_and_error_on_failure():
    with patch("system.sse.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _Proc(["bad news\n"], 2)
        out = list(
            sse_subprocess(
                ["false"],
                "Done",
                "ERROR (exit {returncode})",
            )
        )

    assert out == [
        "data: bad news\n\n",
        "data: ERROR (exit 2)\n\n",
    ]
