import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


PROGRAM = """set name to "Irfan Haider"
print "My teacher name is " , name
print "What is your name"
input myName as string
print "hello " myName
"""


def test_run_end_to_end_with_input():
    # Skip if no native compiler available.
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ not available for integration run")

    project_root = Path(__file__).resolve().parents[1]
    writec = [sys.executable, "-m", "compiler.writec"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src_path = tmpdir / "prog.write"
        cpp_path = tmpdir / "prog.cpp"
        bin_path = tmpdir / ("prog.exe" if os.name == "nt" else "prog")
        src_path.write_text(PROGRAM, encoding="utf-8")

        compile_cmd = writec + [
            str(src_path),
            "--out",
            str(cpp_path),
            "--compile",
            "--out-bin",
            str(bin_path),
        ]
        compile_result = subprocess.run(
            compile_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert compile_result.returncode == 0, compile_result.stderr
        assert bin_path.exists()

        run_result = subprocess.run(
            [str(bin_path)],
            input="Student\n",
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert run_result.returncode == 0
        stdout = run_result.stdout.splitlines()
        # We expect two lines before input, then a response line after providing input.
        assert "My teacher name is Irfan Haider" in stdout[0]
        assert "What is your name" in stdout[1]
        assert any(line.startswith("hello Student") for line in stdout)
