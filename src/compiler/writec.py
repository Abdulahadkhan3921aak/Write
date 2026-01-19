"""writec: transpile Write source to C++ and optionally compile/run."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .semantic import Analyzer, SemanticError
from .codegen import Codegen


def main() -> int:
    ap = argparse.ArgumentParser(description="Transpile Write source to C++")
    ap.add_argument("input", type=Path, help="Input .write file")
    ap.add_argument(
        "--out", type=Path, default=None, help="Output .cpp file (default: input.cpp)"
    )
    ap.add_argument(
        "--compile",
        action="store_true",
        help="Compile generated C++ using detected compiler (g++/clang++)",
    )
    ap.add_argument(
        "--run",
        action="store_true",
        help="Run the binary after compile (implies --compile)",
    )
    ap.add_argument(
        "--cc",
        default=None,
        help="C++ compiler executable to use (default: auto-detect g++ then clang++)",
    )
    ap.add_argument(
        "--std",
        default="c++17",
        help="C++ standard flag (default: c++17)",
    )
    ap.add_argument(
        "--out-bin",
        type=Path,
        default=None,
        help="Output binary path (default: input stem + .exe on Windows, stem otherwise)",
    )
    args = ap.parse_args()

    out_path = args.out or args.input.with_suffix(".cpp")
    bin_path = args.out_bin or _default_bin_path(args.input)

    if args.run:
        args.compile = True

    try:
        src = args.input.read_text(encoding="utf-8")
    except FileNotFoundError:
        log_error(f"file not found: {args.input}")
        return 1

    try:
        log_step("lexing")
        tokens = Lexer(src).scan()
        log_step("parsing")
        program = Parser(tokens).parse()
        log_step("semantic checks")
        Analyzer(src).analyze(program)
        log_step("codegen")
        cpp = Codegen().generate(program)
    except (LexerError, ParseError, SemanticError, Exception) as e:
        log_error(str(e))
        return 1

    out_path.write_text(cpp, encoding="utf-8")
    print(f"wrote {out_path}")

    if args.compile:
        cc = _choose_cc(args.cc)
        log_step(f"compiling with {cc}")
        ok = _compile(cc, args.std, out_path, bin_path)
        if not ok:
            return 1
        print(f"compiled -> {bin_path}")
        if args.run:
            log_step("running binary")
            rc = _run_binary(bin_path)
            return rc
    return 0


def _default_bin_path(input_path: Path) -> Path:
    stem = input_path.with_suffix("").name
    ext = ".exe" if os.name == "nt" else ""
    return input_path.with_name(stem + ext)


def _choose_cc(preferred: str | None) -> str:
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.extend(["g++", "clang++"])
    if os.name == "nt":
        candidates.append("cl")
    for cc in candidates:
        if shutil.which(cc):
            return cc
    tried = ", ".join(candidates)
    raise SystemExit(
        "error: no C++ compiler found. Tried: "
        + tried
        + "\nInstall g++ (MinGW/WSL) or clang++, or pass --cc <path>."
    )


def _compile(cc: str, std: str, cpp_path: Path, bin_path: Path) -> bool:
    if cc == "cl":
        std_flag = "/std:c++17" if std == "c++17" else f"/std:{std}"
        cmd = [cc, str(cpp_path), f"/Fe:{bin_path}", std_flag]
    else:
        cmd = [cc, f"-std={std}", str(cpp_path), "-o", str(bin_path)]
    print("compile:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    _print_stream("stdout", result.stdout)
    _print_stream("stderr", result.stderr)
    return result.returncode == 0


def _run_binary(bin_path: Path) -> int:
    print(f"run: {bin_path}")
    result = subprocess.run([str(bin_path)], capture_output=True, text=True)
    _print_stream("stdout", result.stdout)
    _print_stream("stderr", result.stderr)
    return result.returncode


def log_step(msg: str) -> None:
    print(f"[writec] {msg}...")


def log_error(msg: str) -> None:
    print(f"[writec:error] {msg}")


def _print_stream(label: str, data: str) -> None:
    if data:
        print(f"[{label}]", end=" ")
        print(data, end="")


if __name__ == "__main__":
    raise SystemExit(main())
