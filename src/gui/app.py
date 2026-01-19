"""PySide6 GUI for the Write language."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRITEC = PROJECT_ROOT / "write" / "Scripts" / "python.exe"
WRITEC_MODULE = "-m"
WRITEC_ENTRY = "compiler.writec"
SAMPLES_DIR = PROJECT_ROOT / "spec" / "examples"


class WriteHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        kw_format = QtGui.QTextCharFormat()
        kw_format.setForeground(QtGui.QColor("#0057b7"))
        kw_format.setFontWeight(QtGui.QFont.Bold)
        keywords = [
            "set",
            "to",
            "print",
            "if",
            "else",
            "end",
            "then",
            "while",
            "do",
            "for",
            "from",
            "and",
            "or",
            "not",
            "is",
            "greater",
            "less",
            "equal",
            "than",
            "add",
            "subtract",
            "multiply",
            "divide",
            "power",
        ]
        for kw in keywords:
            pattern = QtCore.QRegularExpression(rf"\b{kw}\b")
            self.rules.append((pattern, kw_format))

        num_format = QtGui.QTextCharFormat()
        num_format.setForeground(QtGui.QColor("#b71c1c"))
        self.rules.append((QtCore.QRegularExpression(r"\b\d+(\.\d+)?\b"), num_format))

        str_format = QtGui.QTextCharFormat()
        str_format.setForeground(QtGui.QColor("#2e7d32"))
        self.rules.append(
            (QtCore.QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), str_format)
        )

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#9e9e9e"))
        self.rules.append((QtCore.QRegularExpression(r"#.*"), comment_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_path: Path | None = None
        self.setWindowTitle("Write IDE (PySide6)")
        self._editor_base_font_size = None
        self._cpp_visible = True
        self._build_ui()
        self._setup_menu()

    def _build_ui(self):
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setPlaceholderText("Write code here…")
        WriteHighlighter(self.editor.document())
        self._editor_base_font_size = self.editor.font().pointSize()

        self.cpp_view = QtWidgets.QPlainTextEdit()
        self.cpp_view.setReadOnly(True)
        self.cpp_view.setPlaceholderText("Generated C++ will appear here…")

        self.output_tabs = QtWidgets.QTabWidget()
        self.output_tabs.setTabPosition(QtWidgets.QTabWidget.South)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs…")
        self.output_tabs.addTab(self.log_view, "Logs")

        self.warn_view = QtWidgets.QPlainTextEdit()
        self.warn_view.setReadOnly(True)
        self.warn_view.setPlaceholderText("Warnings…")
        self.output_tabs.addTab(self.warn_view, "Warnings")

        self.error_view = QtWidgets.QPlainTextEdit()
        self.error_view.setReadOnly(True)
        self.error_view.setPlaceholderText("Errors…")
        self.output_tabs.addTab(self.error_view, "Errors")

        self.terminal_view = QtWidgets.QPlainTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setPlaceholderText("Terminal / Output…")
        self.output_tabs.addTab(self.terminal_view, "Terminal / Output")

        clear_bar = QtWidgets.QHBoxLayout()
        clear_bar.setContentsMargins(0, 0, 0, 0)
        clear_bar.setSpacing(4)

        self._add_clear_button(clear_bar, "Clear Logs", self.log_view)
        self._add_clear_button(clear_bar, "Clear Warnings", self.warn_view)
        self._add_clear_button(clear_bar, "Clear Errors", self.error_view)
        self._add_clear_button(clear_bar, "Clear Output", self.terminal_view)
        clear_bar.addStretch(1)

        tabs_container = QtWidgets.QWidget()
        tabs_layout = QtWidgets.QVBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)
        tabs_layout.addLayout(clear_bar)
        tabs_layout.addWidget(self.output_tabs)

        open_btn = QtWidgets.QPushButton("Open…")
        open_btn.clicked.connect(self.open_file)
        save_btn = QtWidgets.QPushButton("Save As…")
        save_btn.clicked.connect(self.save_file)
        transpile_btn = QtWidgets.QPushButton("Transpile")
        transpile_btn.clicked.connect(self.transpile_only)
        compile_btn = QtWidgets.QPushButton("Compile")
        compile_btn.clicked.connect(self.compile_only)
        run_btn = QtWidgets.QPushButton("Run")
        run_btn.clicked.connect(self.run_binary)
        load_sample_btn = QtWidgets.QPushButton("Load Sample…")
        load_sample_btn.clicked.connect(self.open_sample)

        buttons = QtWidgets.QHBoxLayout()
        for b in [
            open_btn,
            save_btn,
            load_sample_btn,
            transpile_btn,
            compile_btn,
            run_btn,
        ]:
            buttons.addWidget(b)
        buttons.addStretch(1)

        self.code_splitter = QtWidgets.QSplitter()
        self.code_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.code_splitter.addWidget(self.editor)
        self.code_splitter.addWidget(self.cpp_view)
        self.code_splitter.setSizes([3, 2])

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.addWidget(self.code_splitter)
        splitter.addWidget(tabs_container)
        splitter.setSizes([3, 1])

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(buttons)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _setup_menu(self):
        menubar = self.menuBar()
        view_menu = menubar.addMenu("View")

        inc_font = QtWidgets.QAction("Increase Editor Font", self)
        inc_font.triggered.connect(lambda: self._adjust_editor_font(1))
        dec_font = QtWidgets.QAction("Decrease Editor Font", self)
        dec_font.triggered.connect(lambda: self._adjust_editor_font(-1))
        reset_font = QtWidgets.QAction("Reset Editor Font", self)
        reset_font.triggered.connect(self._reset_editor_font)

        toggle_split = QtWidgets.QAction("Toggle Code Split Orientation", self)
        toggle_split.triggered.connect(self._toggle_code_split)

        toggle_cpp = QtWidgets.QAction("Show/Hide C++ Pane", self)
        toggle_cpp.triggered.connect(self._toggle_cpp_visibility)

        view_menu.addAction(inc_font)
        view_menu.addAction(dec_font)
        view_menu.addAction(reset_font)
        view_menu.addSeparator()
        view_menu.addAction(toggle_split)
        view_menu.addAction(toggle_cpp)

    # --- file ops ---
    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Write file",
            str(SAMPLES_DIR),
            "Write Files (*.write)",
        )
        if not path:
            return
        self._current_path = Path(path)
        text = self._current_path.read_text(encoding="utf-8")
        self.editor.setPlainText(text)
        self._log(f"Opened {self._current_path.name}")

    def open_sample(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load sample",
            str(SAMPLES_DIR),
            "Write Files (*.write)",
        )
        if not path:
            return
        self.load_sample(Path(path))

    def save_file(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Write file",
            str(self._current_path.parent if self._current_path else PROJECT_ROOT),
            "Write Files (*.write)",
        )
        if not path:
            return
        self._current_path = Path(path)
        self._current_path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self._log(f"Saved {self._current_path.name}")

    def load_sample(self, path: Path):
        self._current_path = None
        text = Path(path).read_text(encoding="utf-8")
        self.editor.setPlainText(text)
        self._log(f"Loaded sample {path.name}")

    # --- Actions ---
    def transpile_only(self):
        src = self.editor.toPlainText()
        if not src.strip():
            self._warn("No source to transpile")
            return
        self._reset_command_outputs()
        tmp_in = PROJECT_ROOT / "tmp_gui_input.write"
        tmp_cpp = PROJECT_ROOT / "tmp_gui_output.cpp"
        tmp_in.write_text(src, encoding="utf-8")
        cmd = [
            str(WRITEC),
            WRITEC_MODULE,
            WRITEC_ENTRY,
            str(tmp_in),
            "--out",
            str(tmp_cpp),
        ]
        self._run_cmd(cmd)
        if tmp_cpp.exists():
            self.cpp_view.setPlainText(tmp_cpp.read_text(encoding="utf-8"))

    def compile_only(self):
        src = self.editor.toPlainText()
        if not src.strip():
            self._warn("No source to compile")
            return
        self._reset_command_outputs()
        tmp_in = PROJECT_ROOT / "tmp_gui_input.write"
        tmp_cpp = PROJECT_ROOT / "tmp_gui_output.cpp"
        tmp_bin = PROJECT_ROOT / (
            "tmp_gui_output.exe" if sys.platform.startswith("win") else "tmp_gui_output"
        )
        tmp_in.write_text(src, encoding="utf-8")
        cmd = [
            str(WRITEC),
            WRITEC_MODULE,
            WRITEC_ENTRY,
            str(tmp_in),
            "--out",
            str(tmp_cpp),
            "--compile",
            "--out-bin",
            str(tmp_bin),
        ]
        self._run_cmd(cmd)
        if tmp_cpp.exists():
            self.cpp_view.setPlainText(tmp_cpp.read_text(encoding="utf-8"))

    def run_binary(self):
        src = self.editor.toPlainText()
        if not src.strip():
            self._warn("No source to run")
            return
        self._reset_command_outputs()
        tmp_in = PROJECT_ROOT / "tmp_gui_input.write"
        tmp_cpp = PROJECT_ROOT / "tmp_gui_output.cpp"
        tmp_bin = PROJECT_ROOT / (
            "tmp_gui_output.exe" if sys.platform.startswith("win") else "tmp_gui_output"
        )
        tmp_in.write_text(src, encoding="utf-8")
        cmd = [
            str(WRITEC),
            WRITEC_MODULE,
            WRITEC_ENTRY,
            str(tmp_in),
            "--out",
            str(tmp_cpp),
            "--run",
            "--out-bin",
            str(tmp_bin),
        ]
        self._run_cmd(cmd)
        if tmp_cpp.exists():
            self.cpp_view.setPlainText(tmp_cpp.read_text(encoding="utf-8"))

    def _run_cmd(self, cmd):
        self._terminal("$ " + " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            self._terminal("[stdout]\n" + result.stdout)
        if result.stderr:
            self._error("[stderr]\n" + result.stderr)
        if result.returncode != 0:
            self._error(f"[exit {result.returncode}]")
        else:
            self._log("Command completed successfully")

    def _log(self, msg: str):
        self._append_to_tab(self.log_view, msg)

    def _warn(self, msg: str):
        self._append_to_tab(self.warn_view, msg, focus=True)

    def _error(self, msg: str):
        self._append_to_tab(self.error_view, msg, focus=True)

    def _terminal(self, msg: str):
        self._append_to_tab(self.terminal_view, msg, focus=True)

    def _append_to_tab(
        self, view: QtWidgets.QPlainTextEdit, msg: str, focus: bool = False
    ):
        view.appendPlainText(msg)
        if focus:
            self.output_tabs.setCurrentWidget(view)

    def _reset_command_outputs(self):
        """Clear non-log tabs so each action starts fresh."""
        for v in (self.warn_view, self.error_view, self.terminal_view):
            v.clear()

    def _add_clear_button(
        self, layout: QtWidgets.QHBoxLayout, label: str, view: QtWidgets.QPlainTextEdit
    ):
        btn = QtWidgets.QPushButton(label)
        btn.setFixedHeight(22)
        btn.setToolTip(label)
        btn.clicked.connect(view.clear)
        layout.addWidget(btn)

    # --- view helpers ---
    def _adjust_editor_font(self, delta: int):
        font = self.editor.font()
        size = font.pointSize() or self._editor_base_font_size or 10
        new_size = max(6, size + delta)
        font.setPointSize(new_size)
        self.editor.setFont(font)
        self.cpp_view.setFont(font)

    def _reset_editor_font(self):
        if not self._editor_base_font_size:
            return
        font = self.editor.font()
        font.setPointSize(self._editor_base_font_size)
        self.editor.setFont(font)
        self.cpp_view.setFont(font)

    def _toggle_code_split(self):
        current = self.code_splitter.orientation()
        new_orientation = (
            QtCore.Qt.Vertical
            if current == QtCore.Qt.Horizontal
            else QtCore.Qt.Horizontal
        )
        self.code_splitter.setOrientation(new_orientation)

    def _toggle_cpp_visibility(self):
        self._cpp_visible = not self._cpp_visible
        self.cpp_view.setVisible(self._cpp_visible)
        if self._cpp_visible:
            self.code_splitter.setSizes([3, 2])
        else:
            self.code_splitter.setSizes([1, 0])


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
