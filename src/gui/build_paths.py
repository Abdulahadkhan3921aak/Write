"""Helpers for planning per-document build artifacts."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass
class BuildPlan:
    input_path: Path
    cpp_path: Path
    bin_path: Path | None
    build_dir: Path

    def ensure_dirs(self) -> None:
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.cpp_path.parent.mkdir(parents=True, exist_ok=True)
        if self.bin_path:
            self.bin_path.parent.mkdir(parents=True, exist_ok=True)


class BuildPaths:
    def __init__(self, temp_root: Path | None = None):
        self.temp_root = temp_root or Path(tempfile.gettempdir()) / "write_ide"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self._build_dirs: dict[int, Path] = {}

    def plan_transpile(self, editor_key: int, saved_path: Path | None) -> BuildPlan:
        build_dir = self._ensure_build_dir(editor_key)
        input_path = build_dir / self._input_name(saved_path)
        cpp_path = build_dir / "output.cpp"
        return BuildPlan(
            input_path=input_path, cpp_path=cpp_path, bin_path=None, build_dir=build_dir
        )

    def plan_compile(
        self, editor_key: int, saved_path: Path | None, is_windows: bool
    ) -> BuildPlan:
        build_dir = self._ensure_build_dir(editor_key)
        input_path = build_dir / self._input_name(saved_path)
        cpp_path = build_dir / "output.cpp"
        bin_name = self._bin_name(saved_path, is_windows)
        bin_dir = saved_path.parent if saved_path else build_dir
        bin_path = bin_dir / bin_name
        return BuildPlan(
            input_path=input_path,
            cpp_path=cpp_path,
            bin_path=bin_path,
            build_dir=build_dir,
        )

    def cleanup_for_editor(self, editor_key: int) -> None:
        path = self._build_dirs.pop(editor_key, None)
        if path and path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def cleanup_all(self) -> None:
        for key in list(self._build_dirs.keys()):
            self.cleanup_for_editor(key)

    def _ensure_build_dir(self, editor_key: int) -> Path:
        if editor_key in self._build_dirs:
            return self._build_dirs[editor_key]
        build_dir = self.temp_root / f"build_{uuid4().hex}"
        build_dir.mkdir(parents=True, exist_ok=True)
        self._build_dirs[editor_key] = build_dir
        return build_dir

    @staticmethod
    def _input_name(saved_path: Path | None) -> str:
        if saved_path:
            return f"{saved_path.stem}.write"
        return "unsaved.write"

    @staticmethod
    def _bin_name(saved_path: Path | None, is_windows: bool) -> str:
        suffix = ".exe" if is_windows else ""
        if saved_path:
            return f"{saved_path.stem}{suffix}"
        return f"program{suffix}"
