"""Diagnostics and linting system for Write IDE."""

from __future__ import annotations

import re
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets


class DiagnosticsHelper:
    """Helper for managing diagnostics and linting."""

    @staticmethod
    def parse_diagnostics(stderr: str) -> list[tuple[int, int, str]]:
        """Parse compiler diagnostics from stderr."""
        diagnostics = []
        pattern = re.compile(r"at (\d+):(\d+)")

        for line in stderr.splitlines():
            m = pattern.search(line)
            if m:
                line_no = int(m.group(1))
                col_no = int(m.group(2))
                diagnostics.append((line_no, col_no, line))

        return diagnostics

    @staticmethod
    def generate_lint_hints(stderr: str) -> list[str]:
        """Generate helpful lint hints from compiler output."""
        hints = []
        lowered = stderr.lower() if stderr else ""

        if "function" in lowered or "call" in lowered:
            hints.append(
                'Function syntax: function "name" arguments: (a:int, b:float, c="hi") … end_function'
            )
            hints.append(
                'Call syntax: call "name" with arguments:(first=5, second=4.2) or call "name" with arguments:(5,4.2)'
            )

        if "unexpected token" in lowered or "expected" in lowered:
            hints.append(
                "Check commas inside argument lists and close with end_function/end_func"
            )

        if "list" in lowered:
            hints.append("List declaration: make mylist as list of size 10")

        return hints

    @staticmethod
    def compute_lightweight_hints(text: str) -> list[tuple[int | None, str]]:
        """Compute lightweight linting hints for current document."""
        hints = []
        lines = text.splitlines()

        # Check function/end_function balance
        func_opens = [
            i + 1 for i, ln in enumerate(lines) if re.search(r"\bfunc(tion)?\b", ln)
        ]
        func_closes = [
            i + 1
            for i, ln in enumerate(lines)
            if "end_function" in ln or "end_func" in ln
        ]
        if len(func_opens) != len(func_closes):
            hints.append(
                (
                    func_opens[0] if func_opens else None,
                    "Function/end_function count is mismatched",
                )
            )

        # Check arguments syntax
        for i, ln in enumerate(lines):
            if "arguments" in ln and ":" not in ln:
                hints.append((i + 1, "Add ':' after arguments: (a:int, b:float)"))

        # Check call syntax
        for i, ln in enumerate(lines):
            if "call" in ln and "arguments" not in ln:
                hints.append((i + 1, "Call syntax: call name with arguments:(…)"))

        # Check trailing whitespace
        for i, ln in enumerate(lines):
            if ln.rstrip() != ln:
                hints.append((i + 1, "Trailing whitespace"))

        # Check list declarations
        for i, ln in enumerate(lines):
            if "list" in ln and "size" not in ln:
                hints.append(
                    (i + 1, "Lists usually need a size: make mylist as list of size 5")
                )

        return hints


class DiagnosticsPanel(QtWidgets.QWidget):
    """Panel for displaying diagnostics with filtering."""

    def __init__(self, parent=None):
        """Initialize diagnostics panel."""
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["All", "Errors", "Warnings", "Hints"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setAlternatingRowColors(True)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)
        layout.addWidget(self.list_widget)

        self._diagnostics = []

    def set_diagnostics(self, diagnostics: list[tuple[int, int, str]]) -> None:
        """Set diagnostics to display."""
        self._diagnostics = diagnostics
        self._update_list()

    def _update_list(self) -> None:
        """Update the list widget based on current filter."""
        self.list_widget.clear()
        filter_type = self.filter_combo.currentText()

        for line_no, col_no, msg in self._diagnostics:
            if filter_type == "All" or filter_type.lower() in msg.lower():
                item = QtWidgets.QListWidgetItem(f"L{line_no}:{col_no} {msg}")
                item.setData(QtCore.Qt.UserRole, (line_no, col_no))
                self.list_widget.addItem(item)

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._update_list()

    def get_selected_location(self) -> tuple[int, int] | None:
        """Get location of selected diagnostic."""
        item = self.list_widget.currentItem()
        if item:
            return item.data(QtCore.Qt.UserRole)
        return None
