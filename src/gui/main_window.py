"""Main window for the Write IDE."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .actions import ActionManager
from .build_paths import BuildPaths
from .editor_widget import EditorWidget
from .keyword_help import KeywordDatabase
from .theme import ThemeManager, ThemeMode

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRITEC = Path(sys.executable)
WRITEC_MODULE = "-m"
WRITEC_ENTRY = "compiler.writec"
SAMPLES_DIR = PROJECT_ROOT / "spec" / "examples"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, workspace: Path | None = None):
        super().__init__()
        self.setWindowTitle("Write IDE (PySide6)")
        self._editor_base_font_size = None
        self._cpp_visible = False
        self._tab_dirty: dict[QtWidgets.QWidget, bool] = {}
        self._lint_overlays: dict[
            QtWidgets.QWidget, list[QtWidgets.QTextEdit.ExtraSelection]
        ] = {}
        self._diag_selection: dict[
            QtWidgets.QWidget, QtWidgets.QTextEdit.ExtraSelection | None
        ] = {}
        self._symbols: dict[QtWidgets.QWidget, dict[str, set[str]]] = {}
        self.settings = QtCore.QSettings("WriteIDE", "Write")
        self.compiler_path = Path(self.settings.value("compiler_path", str(WRITEC)))
        self.compiler_extra_args = self.settings.value("compiler_extra_args", "")
        self.last_opened = self.settings.value("last_opened", None)
        self.workspace_root: Path | None = workspace
        self.proc: QtCore.QProcess | None = None
        self._tab_paths: dict[QtWidgets.QWidget, Path | None] = {}
        self._lint_timer = QtCore.QTimer(self)
        self._lint_timer.setSingleShot(True)
        self._lint_timer.timeout.connect(self._run_lint_pass)
        self._main_vertical_splitter: QtWidgets.QSplitter | None = None
        self._main_horizontal_splitter: QtWidgets.QSplitter | None = None
        self.build_paths = BuildPaths()

        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme(QtWidgets.QApplication.instance())
        self.action_manager = ActionManager(self)

        self._build_ui()
        self._setup_menu()
        QtCore.QTimer.singleShot(0, self._set_default_layout_sizes)
        if self.workspace_root:
            self._set_workspace_root(self.workspace_root)

    def _build_ui(self):
        mono_font = QtGui.QFont("Consolas", 14)

        self.editor_tabs = QtWidgets.QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self._close_tab)
        self.editor_tabs.currentChanged.connect(self._on_tab_changed)
        self.editor_tabs.setMinimumHeight(320)
        self._editor_base_font_size = mono_font.pointSize()

        self.cpp_view = QtWidgets.QPlainTextEdit()
        self.cpp_view.setReadOnly(True)
        self.cpp_view.setPlaceholderText("Generated C++ will appear here…")
        self.cpp_view.setFont(mono_font)

        self.output_tabs = QtWidgets.QTabWidget()
        self.output_tabs.setTabPosition(QtWidgets.QTabWidget.South)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs…")
        self.log_view.setFont(mono_font)
        self.output_tabs.addTab(self.log_view, "Logs")

        self.warn_view = QtWidgets.QPlainTextEdit()
        self.warn_view.setReadOnly(True)
        self.warn_view.setPlaceholderText("Warnings…")
        self.warn_view.setFont(mono_font)
        self.output_tabs.addTab(self.warn_view, "Warnings")

        self.error_view = QtWidgets.QPlainTextEdit()
        self.error_view.setReadOnly(True)
        self.error_view.setPlaceholderText("Errors…")
        self.error_view.setFont(mono_font)
        self.output_tabs.addTab(self.error_view, "Errors")

        self.terminal_view = QtWidgets.QPlainTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setPlaceholderText("Terminal / Output…")
        self.terminal_view.setFont(mono_font)
        self.output_tabs.addTab(self.terminal_view, "Terminal / Output")

        term_input_bar = QtWidgets.QHBoxLayout()
        term_input_bar.setContentsMargins(0, 0, 0, 0)
        term_input_bar.setSpacing(4)
        self.terminal_input = QtWidgets.QLineEdit()
        self.terminal_input.setPlaceholderText("Type input for running program…")
        send_btn = QtWidgets.QPushButton("Send")
        send_btn.clicked.connect(self._send_stdin)
        term_input_bar.addWidget(QtWidgets.QLabel("Stdin:"))
        term_input_bar.addWidget(self.terminal_input, 1)
        term_input_bar.addWidget(send_btn)

        self.diagnostics_view = QtWidgets.QListWidget()
        self.diagnostics_view.itemClicked.connect(self._jump_to_diagnostic)
        self.output_tabs.addTab(self.diagnostics_view, "Diagnostics")

        self.lint_view = QtWidgets.QListWidget()
        self.lint_view.setToolTip("Lightweight linting hints (fast, heuristic)")
        self.output_tabs.addTab(self.lint_view, "Lint")

        self.fs_model = QtWidgets.QFileSystemModel()
        self.fs_model.setFilter(
            QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files
        )
        self.fs_model.setNameFilters(["*.write", "*.txt", "*.cpp", "*"])
        self.fs_model.setNameFilterDisables(False)
        self.fs_model.setRootPath("")

        self.file_view = QtWidgets.QTreeView()
        self.file_view.setModel(self.fs_model)
        self.file_view.setHeaderHidden(True)
        for col in range(1, 4):
            self.file_view.setColumnHidden(col, True)
        self.file_view.doubleClicked.connect(self._open_from_tree)
        self.file_view.setMinimumWidth(200)
        self.file_view.setVisible(False)
        self.file_view.setEnabled(False)

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
        tabs_layout.addLayout(term_input_bar)

        open_btn = QtWidgets.QPushButton("Open…")
        open_btn.clicked.connect(self.open_file)
        open_folder_btn = QtWidgets.QPushButton("Open Folder…")
        open_folder_btn.clicked.connect(self.open_folder)
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self.save_file)
        save_as_btn = QtWidgets.QPushButton("Save As…")
        save_as_btn.clicked.connect(self.save_file_as)
        transpile_btn = QtWidgets.QPushButton("Transpile")
        transpile_btn.clicked.connect(self.transpile_only)
        compile_btn = QtWidgets.QPushButton("Compile")
        compile_btn.clicked.connect(self.compile_only)
        run_btn = QtWidgets.QPushButton("Run")
        run_btn.clicked.connect(self.run_binary)

        self.external_run_checkbox = QtWidgets.QCheckBox(
            "Run in external console (new window)"
        )
        self.external_run_checkbox.setChecked(True)

        self.sample_box = QtWidgets.QComboBox()
        self.sample_box.setMinimumWidth(200)
        self._refresh_samples()
        sample_btn = QtWidgets.QPushButton("Load Sample")
        sample_btn.clicked.connect(self.load_selected_sample)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(open_btn)
        buttons.addWidget(save_btn)
        buttons.addWidget(save_as_btn)
        buttons.addWidget(open_folder_btn)
        buttons.addSpacing(8)
        buttons.addWidget(QtWidgets.QLabel("Sample:"))
        buttons.addWidget(self.sample_box)
        buttons.addWidget(sample_btn)
        buttons.addSpacing(8)
        buttons.addWidget(transpile_btn)
        buttons.addWidget(compile_btn)
        buttons.addWidget(run_btn)
        buttons.addWidget(self.external_run_checkbox)
        buttons.addStretch(1)

        self.code_splitter = QtWidgets.QSplitter()
        self.code_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.code_splitter.addWidget(self.editor_tabs)
        self.code_splitter.addWidget(self.cpp_view)
        self.code_splitter.setSizes([3, 2])
        self.cpp_view.setVisible(self._cpp_visible)
        if not self._cpp_visible:
            self.code_splitter.setSizes([1, 0])

        self._main_vertical_splitter = QtWidgets.QSplitter()
        self._main_vertical_splitter.setOrientation(QtCore.Qt.Vertical)
        self._main_vertical_splitter.addWidget(self.code_splitter)
        self._main_vertical_splitter.addWidget(tabs_container)
        self._main_vertical_splitter.setStretchFactor(0, 5)
        self._main_vertical_splitter.setStretchFactor(1, 1)
        self._main_vertical_splitter.setCollapsible(0, False)
        tabs_container.setMinimumHeight(140)

        self._main_horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._main_horizontal_splitter.addWidget(self.file_view)
        self._main_horizontal_splitter.addWidget(self._main_vertical_splitter)
        self._main_horizontal_splitter.setSizes([1, 4])
        self._main_horizontal_splitter.setCollapsible(1, False)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(buttons)
        layout.addWidget(self._main_horizontal_splitter)
        self.setCentralWidget(central)

    def _setup_menu(self):
        self.action_manager.setup_file_menu(
            on_new=self.new_file,
            on_save=self.save_file,
            on_save_as=self.save_file_as,
            on_open=self.open_file,
        )
        self.action_manager.setup_view_menu(
            on_inc_font=lambda: self._adjust_editor_font(1),
            on_dec_font=lambda: self._adjust_editor_font(-1),
            on_reset_font=self._reset_editor_font,
            on_toggle_split=self._toggle_code_split,
            on_toggle_cpp=self._toggle_cpp_visibility,
            on_theme=self._show_theme_dialog,
        )
        self.action_manager.setup_tools_menu(
            on_set_compiler=self._set_compiler_path,
            on_set_flags=self._set_extra_flags,
            on_keyword_help=self._show_keyword_help_dialog,
        )
        self.action_manager.setup_help_menu()

    # --- editor tab helpers ---
    def _create_editor(self, text: str = "") -> EditorWidget:
        editor = EditorWidget()
        editor.setPlainText(text)
        editor.document().setModified(False)
        editor.textChanged.connect(lambda e=editor: self._on_editor_changed(e))
        editor.cursorPositionChanged.connect(lambda e=editor: self._on_cursor_moved(e))
        self._tab_dirty[editor] = False
        self._lint_overlays[editor] = []
        self._diag_selection[editor] = None
        self._symbols[editor] = {"funcs": set(), "vars": set()}
        return editor

    def _open_text_in_tab(self, text: str, path: Path | None, label: str):
        editor = self._create_editor(text)
        idx = self.editor_tabs.addTab(editor, label)
        self.editor_tabs.setCurrentIndex(idx)
        self._tab_paths[editor] = path
        self._tab_dirty[editor] = False
        self._update_tab_label(editor)
        if path:
            self.editor_tabs.setTabToolTip(idx, str(path))

    def _ensure_tab_for_restore(self, path: Path, text: str):
        editor = self._current_editor()
        if editor and not editor.toPlainText().strip():
            editor.setPlainText(text)
            editor.document().setModified(False)
            self._tab_dirty[editor] = False
            self._set_current_path(path)
            return
        self._open_text_in_tab(text, path, path.name)

    def _current_editor(self) -> QtWidgets.QPlainTextEdit | None:
        widget = self.editor_tabs.currentWidget()
        return widget if isinstance(widget, QtWidgets.QPlainTextEdit) else None

    def _current_path(self) -> Path | None:
        editor = self._current_editor()
        return self._tab_paths.get(editor) if editor else None

    def _set_current_path(self, path: Path | None):
        editor = self._current_editor()
        if not editor:
            return
        self._tab_paths[editor] = path
        self._update_tab_label(editor)
        if path:
            idx = self.editor_tabs.indexOf(editor)
            if idx >= 0:
                self.editor_tabs.setTabToolTip(idx, str(path))

    def _close_tab(self, index: int):
        widget = self.editor_tabs.widget(index)
        if not widget:
            return
        if not self._confirm_close_editor(widget):
            return
        self.build_paths.cleanup_for_editor(id(widget))
        self._tab_paths.pop(widget, None)
        self._tab_dirty.pop(widget, None)
        self._lint_overlays.pop(widget, None)
        self._diag_selection.pop(widget, None)
        widget.deleteLater()
        self.editor_tabs.removeTab(index)

    def _on_tab_changed(self, _index: int):
        self._clear_highlights()

    # --- file ops ---
    def new_file(self):
        self._open_text_in_tab("", None, "Untitled")
        self._log("Created new file")

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Write file",
            str(SAMPLES_DIR),
            "Write Files (*.write)",
        )
        if not path:
            return
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        self._open_text_in_tab(text, p, p.name)
        self._log(f"Opened {p.name}")
        self._store_last_file(p)

    def open_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open folder as workspace", str(PROJECT_ROOT)
        )
        if not path:
            return
        self._set_workspace_root(Path(path))

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

    def _set_workspace_root(self, root: Path):
        self.workspace_root = root
        self.fs_model.setRootPath(str(root))
        self.file_view.setRootIndex(self.fs_model.index(str(root)))
        self.file_view.setVisible(True)
        self.file_view.setEnabled(True)
        self._log(f"Workspace set to {root}")

    def save_file(self):
        editor = self._current_editor()
        if not editor:
            self._warn("No document to save")
            return
        saved = self._save_editor(editor, force_dialog=False)
        if saved:
            p = self._current_path()
            if p:
                self._store_last_file(p)

    def save_file_as(self):
        editor = self._current_editor()
        if not editor:
            self._warn("No document to save")
            return
        saved = self._save_editor(editor, force_dialog=True)
        if saved:
            p = self._current_path()
            if p:
                self._store_last_file(p)

    def load_sample(self, path: Path):
        text = Path(path).read_text(encoding="utf-8")
        self._open_text_in_tab(text, path, path.name)
        self._log(f"Loaded sample {path.name}")
        self._store_last_file(path)

    def load_selected_sample(self):
        selected = self.sample_box.currentData()
        if selected:
            self.load_sample(selected)

    def _open_from_tree(self, index: QtCore.QModelIndex):
        path = Path(self.fs_model.filePath(index))
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            self._open_text_in_tab(text, path, path.name)
            self._log(f"Opened {path.name}")
            self._store_last_file(path)

    # --- Actions ---
    def transpile_only(self):
        editor = self._current_editor()
        if not editor:
            self._warn("No source to transpile")
            return
        src = editor.toPlainText()
        if not src.strip():
            self._warn("No source to transpile")
            return
        self._reset_command_outputs()
        self._stop_process()
        plan = self.build_paths.plan_transpile(id(editor), self._current_path())
        plan.ensure_dirs()
        plan.cpp_path.unlink(missing_ok=True)
        plan.input_path.write_text(src, encoding="utf-8")
        cmd = self._build_cmd(
            [
                str(plan.input_path),
                "--out",
                str(plan.cpp_path),
            ]
        )
        self._run_cmd(cmd)
        if plan.cpp_path.exists():
            self.cpp_view.setPlainText(plan.cpp_path.read_text(encoding="utf-8"))

    def compile_only(self):
        editor = self._current_editor()
        if not editor:
            self._warn("No source to compile")
            return
        src = editor.toPlainText()
        if not src.strip():
            self._warn("No source to compile")
            return
        self._reset_command_outputs()
        self._stop_process()
        plan = self.build_paths.plan_compile(
            id(editor),
            self._current_path(),
            sys.platform.startswith("win"),
        )
        plan.ensure_dirs()
        plan.cpp_path.unlink(missing_ok=True)
        if plan.bin_path:
            plan.bin_path.unlink(missing_ok=True)
        plan.input_path.write_text(src, encoding="utf-8")
        cmd = self._build_cmd(
            [
                str(plan.input_path),
                "--out",
                str(plan.cpp_path),
                "--compile",
                "--out-bin",
                str(plan.bin_path),
            ]
        )
        self._run_cmd(cmd)
        if plan.cpp_path.exists():
            self.cpp_view.setPlainText(plan.cpp_path.read_text(encoding="utf-8"))

    def run_binary(self):
        editor = self._current_editor()
        if not editor:
            self._warn("No source to run")
            return
        src = editor.toPlainText()
        if not src.strip():
            self._warn("No source to run")
            return
        self._reset_command_outputs()
        self._stop_process()
        plan = self.build_paths.plan_compile(
            id(editor),
            self._current_path(),
            sys.platform.startswith("win"),
        )
        plan.ensure_dirs()
        plan.cpp_path.unlink(missing_ok=True)
        if plan.bin_path:
            plan.bin_path.unlink(missing_ok=True)
        plan.input_path.write_text(src, encoding="utf-8")
        cmd = self._build_cmd(
            [
                str(plan.input_path),
                "--out",
                str(plan.cpp_path),
                "--compile",
                "--out-bin",
                str(plan.bin_path),
            ]
        )
        result = self._run_cmd_collect(cmd)
        if result.returncode != 0:
            return
        if plan.cpp_path.exists():
            self.cpp_view.setPlainText(plan.cpp_path.read_text(encoding="utf-8"))
        if plan.bin_path and plan.bin_path.exists():
            if self.external_run_checkbox.isChecked():
                self._run_external_console(plan.bin_path)
            else:
                self._start_process(plan.bin_path)

    def _run_cmd(self, cmd):
        self._log("$ " + " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            self._route_stdout(result.stdout)
        if result.stderr:
            self._error("[stderr]\n" + result.stderr)
        if result.returncode != 0:
            self._error(f"[exit {result.returncode}]")
            self._show_diagnostics(result.stderr)
        else:
            self._log("Command completed successfully")
        return result

    def _run_cmd_collect(self, cmd):
        self._log("$ " + " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            self._route_stdout(result.stdout)
        if result.stderr:
            self._error("[stderr]\n" + result.stderr)
        if result.returncode != 0:
            self._error(f"[exit {result.returncode}]")
            self._show_diagnostics(result.stderr)
        else:
            self._log("Command completed successfully")
        return result

    def _route_stdout(self, stdout: str):
        for line in stdout.splitlines():
            if not line:
                continue
            if (
                line.startswith("[writec]")
                or line.startswith("wrote ")
                or line.startswith("compile:")
                or line.startswith("compiled")
            ):
                self._log(line)
            elif line.startswith("[stdout]"):
                self._terminal(line)
            else:
                self._terminal(line)

    def _build_cmd(self, args: list[str]):
        cmd = [str(self.compiler_path), WRITEC_MODULE, WRITEC_ENTRY]
        cmd.extend(args)
        if self.compiler_extra_args:
            cmd.extend(self.compiler_extra_args.split())
        return cmd

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
        for v in (self.warn_view, self.error_view, self.terminal_view):
            v.clear()
        self.diagnostics_view.clear()
        self.lint_view.clear()
        self._clear_highlights()
        self.terminal_input.clear()
        self.cpp_view.clear()

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
        editor = self._current_editor()
        if not editor:
            return
        font = editor.font()
        size = font.pointSize() or self._editor_base_font_size or 10
        new_size = max(6, size + delta)
        font.setPointSize(new_size)
        editor.setFont(font)
        self.cpp_view.setFont(font)

    def _reset_editor_font(self):
        if not self._editor_base_font_size:
            return
        editor = self._current_editor()
        if not editor:
            return
        font = editor.font()
        font.setPointSize(self._editor_base_font_size)
        editor.setFont(font)
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

    def _refresh_samples(self):
        self.sample_box.clear()
        samples = sorted(SAMPLES_DIR.glob("*.write"))
        for p in samples:
            self.sample_box.addItem(p.name, p)
        if samples:
            self.sample_box.setCurrentIndex(0)

    # --- settings helpers ---
    def _store_last_file(self, path: Path):
        self.last_opened = str(path)
        self.settings.setValue("last_opened", str(path))

    def _restore_last_file(self):
        if not self.last_opened:
            return
        p = Path(self.last_opened)
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
                self._ensure_tab_for_restore(p, text)
                self._set_current_path(p if p.suffix == ".write" else None)
                self._log(f"Restored {p.name}")
            except Exception:
                pass

    def _set_compiler_path(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select compiler executable",
            str(self.compiler_path if self.compiler_path else PROJECT_ROOT),
            "Python or executable (*.exe *.bat *.cmd);;All files (*)",
        )
        if path:
            self.compiler_path = Path(path)
            self.settings.setValue("compiler_path", str(path))

    def _set_extra_flags(self):
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            "Extra flags",
            "Extra flags passed to compiler (space-separated):",
            QtWidgets.QLineEdit.Normal,
            self.compiler_extra_args,
        )
        if ok:
            self.compiler_extra_args = text
            self.settings.setValue("compiler_extra_args", text)

    def _show_theme_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Theme Settings")
        dialog.setMinimumWidth(300)

        layout = QtWidgets.QVBoxLayout(dialog)
        group = QtWidgets.QGroupBox("Theme Mode")
        group_layout = QtWidgets.QVBoxLayout(group)

        light_radio = QtWidgets.QRadioButton("Light")
        dark_radio = QtWidgets.QRadioButton("Dark")
        system_radio = QtWidgets.QRadioButton("System")

        current_mode = self.theme_manager.current_mode
        if current_mode == ThemeMode.LIGHT:
            light_radio.setChecked(True)
        elif current_mode == ThemeMode.DARK:
            dark_radio.setChecked(True)
        else:
            system_radio.setChecked(True)

        group_layout.addWidget(light_radio)
        group_layout.addWidget(dark_radio)
        group_layout.addWidget(system_radio)
        layout.addWidget(group)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QtWidgets.QDialog.Accepted:
            if light_radio.isChecked():
                self.theme_manager.save_theme_mode(ThemeMode.LIGHT)
            elif dark_radio.isChecked():
                self.theme_manager.save_theme_mode(ThemeMode.DARK)
            else:
                self.theme_manager.save_theme_mode(ThemeMode.SYSTEM)

            self.theme_manager.apply_theme(QtWidgets.QApplication.instance())
            self._log(f"Theme changed to {self.theme_manager.current_mode.value}")

    def _show_keyword_help_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Keyword Help")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QtWidgets.QVBoxLayout(dialog)
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Search:")
        search_input = QtWidgets.QLineEdit()
        search_input.setPlaceholderText("Type keyword to search…")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)

        table = QtWidgets.QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Keyword", "Description"])
        table.horizontalHeader().setStretchLastSection(True)

        keywords = KeywordDatabase.get_all_keywords()

        def _populate_table(filter_text: str = ""):
            table.setRowCount(0)
            for keyword in keywords:
                if filter_text.lower() not in keyword.lower():
                    continue
                help_text = KeywordDatabase.get_help(keyword)
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(keyword))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(help_text))

        _populate_table()
        search_input.textChanged.connect(lambda text: _populate_table(text))

        layout.addLayout(search_layout)
        layout.addWidget(table)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    # --- process helpers ---
    def _start_process(self, bin_path: Path):
        self._stop_process()
        self.proc = QtCore.QProcess(self)
        self.proc.setProgram(str(bin_path))
        self.proc.setWorkingDirectory(str(bin_path.parent))
        self.proc.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        self.proc.readyReadStandardError.connect(self._on_proc_stderr)
        self.proc.finished.connect(self._on_proc_finished)
        self.proc.start()
        self._terminal(f"[run] {bin_path}")

    def _stop_process(self):
        if self.proc and self.proc.state() != QtCore.QProcess.NotRunning:
            self.proc.kill()
            self.proc.waitForFinished(200)
        self.proc = None

    def _on_proc_stdout(self):
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardOutput()).decode(errors="ignore")
        if data:
            self._terminal(data.rstrip("\n"))

    def _on_proc_stderr(self):
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardError()).decode(errors="ignore")
        if data:
            self._error(data.rstrip("\n"))

    def _on_proc_finished(self, code: int, _status):
        self._log(f"[run exit {code}]")
        self.proc = None

    def _run_external_console(self, bin_path: Path):
        if sys.platform.startswith("win"):
            try:
                subprocess.Popen(
                    ["cmd.exe", "/k", str(bin_path)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(bin_path.parent),
                )
                self._log(f"[run external] {bin_path}")
            except Exception as exc:
                self._error(f"Failed to launch external console: {exc}")
        else:
            terminal = shutil.which("x-terminal-emulator") or shutil.which(
                "gnome-terminal"
            )
            if not terminal:
                self._error("No system terminal found to launch external run")
                return
            subprocess.Popen([terminal, "-e", str(bin_path)], cwd=str(bin_path.parent))
            self._log(f"[run external] {bin_path}")

    def _send_stdin(self):
        if not self.proc or self.proc.state() == QtCore.QProcess.NotRunning:
            self._warn("No running program to send input to")
            return
        text = self.terminal_input.text()
        if not text:
            return
        self.proc.write((text + "\n").encode())
        self.terminal_input.clear()

    # --- diagnostics helpers ---
    def _show_diagnostics(self, stderr: str):
        self.diagnostics_view.clear()
        self._clear_highlights()
        if not stderr:
            return
        pattern = re.compile(r"at (\d+):(\d+)")
        line_col: tuple[int, int] | None = None
        for line in stderr.splitlines():
            m = pattern.search(line)
            if m:
                line_col = (int(m.group(1)), int(m.group(2)))
            item = QtWidgets.QListWidgetItem(line)
            item.setData(QtCore.Qt.UserRole, line_col)
            self.diagnostics_view.addItem(item)
        if line_col:
            self._highlight_location(*line_col)
            self.output_tabs.setCurrentWidget(self.diagnostics_view)

        for hint in self._lint_hints(stderr):
            item = QtWidgets.QListWidgetItem(f"Hint: {hint}")
            item.setData(QtCore.Qt.UserRole, None)
            self.diagnostics_view.addItem(item)

    def _highlight_location(self, line: int, col: int):
        editor = self._current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        cursor.movePosition(QtGui.QTextCursor.Down, n=line - 1)
        cursor.movePosition(QtGui.QTextCursor.Right, n=max(col - 1, 0))
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        selection = QtWidgets.QTextEdit.ExtraSelection()
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QColor("#ffebee"))
        selection.format = fmt
        selection.cursor = cursor
        self._diag_selection[editor] = selection
        self._apply_all_selections(editor)

    def _clear_highlights(self):
        editor = self._current_editor()
        if editor:
            self._diag_selection[editor] = None
            self._apply_all_selections(editor)

    def _set_default_layout_sizes(self):
        if self._cpp_visible:
            self.code_splitter.setSizes([3, 2])
        else:
            self.code_splitter.setSizes([1, 0])
        if self._main_vertical_splitter:
            self._main_vertical_splitter.setSizes([10, 3])
            self._main_vertical_splitter.setStretchFactor(0, 10)
            self._main_vertical_splitter.setStretchFactor(1, 3)
            self._main_vertical_splitter.setCollapsible(0, False)
        if self._main_horizontal_splitter:
            self._main_horizontal_splitter.setSizes([1, 5])
            self._main_horizontal_splitter.setCollapsible(1, False)

    def _ensure_layout_sizes(self):
        self._set_default_layout_sizes()
        if not self._main_vertical_splitter:
            return
        sizes = self._main_vertical_splitter.sizes()
        if len(sizes) >= 2:
            total = sum(sizes)
            if total > 0 and sizes[0] < total * 0.6:
                self._main_vertical_splitter.setSizes(
                    [int(total * 0.75), int(total * 0.25)]
                )

    def _apply_all_selections(self, editor: QtWidgets.QPlainTextEdit):
        selections = list(self._lint_overlays.get(editor, []))
        diag = self._diag_selection.get(editor)
        if diag:
            selections.append(diag)
        editor.setExtraSelections(selections)

    def _jump_to_diagnostic(self, item: QtWidgets.QListWidgetItem):
        data = item.data(QtCore.Qt.UserRole)
        if data:
            line, col = data
            self._highlight_location(line, col)
            editor = self._current_editor()
            if editor:
                editor.setFocus()

    def _lint_hints(self, stderr: str) -> list[str]:
        hints: list[str] = []
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
        return hints

    # --- lint helpers ---
    def _on_editor_changed(self, editor: QtWidgets.QPlainTextEdit):
        self._mark_dirty(editor, True)
        self._schedule_lint(editor)

    def _schedule_lint(self, editor: QtWidgets.QPlainTextEdit):
        if len(editor.toPlainText()) > 8000:
            self.lint_view.clear()
            self.lint_view.addItem("Lint skipped: file too large for quick pass")
            return
        self._lint_timer.stop()
        self._lint_timer.setProperty("editor", editor)
        self._lint_timer.start(200)

    def _run_lint_pass(self):
        editor = self._lint_timer.property("editor")
        if not isinstance(editor, QtWidgets.QPlainTextEdit):
            return
        text = editor.toPlainText()
        hints = self._compute_lint_hints(text)
        self._update_symbol_index(editor, text)
        self.lint_view.clear()
        if not hints:
            self.lint_view.addItem("No lint hints")
            self._lint_overlays[editor] = []
            self._apply_all_selections(editor)
            return
        overlays = []
        for line, hint in hints:
            prefix = f"L{line}: " if line else ""
            self.lint_view.addItem(prefix + hint)
            if line:
                cursor = editor.textCursor()
                cursor.movePosition(QtGui.QTextCursor.Start)
                cursor.movePosition(QtGui.QTextCursor.Down, n=line - 1)
                cursor.select(QtGui.QTextCursor.LineUnderCursor)
                sel = QtWidgets.QTextEdit.ExtraSelection()
                fmt = QtGui.QTextCharFormat()
                fmt.setUnderlineStyle(QtGui.QTextCharFormat.DashUnderline)
                fmt.setUnderlineColor(QtGui.QColor("#c77d00"))
                fmt.setBackground(QtGui.QColor(255, 244, 229, 60))
                sel.format = fmt
                sel.cursor = cursor
                overlays.append(sel)
        self._lint_overlays[editor] = overlays
        self._apply_all_selections(editor)

    def _compute_lint_hints(self, text: str) -> list[tuple[int | None, str]]:
        hints: list[tuple[int | None, str]] = []
        lines = text.splitlines()
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

        for i, ln in enumerate(lines):
            if "arguments" in ln and ":" not in ln:
                hints.append((i + 1, "Add ':' after arguments: (a:int, b:float)"))

        for i, ln in enumerate(lines):
            if "call" in ln and "arguments" not in ln:
                hints.append((i + 1, "Call syntax: call name with arguments:(… )"))

        for i, ln in enumerate(lines):
            if ln.rstrip() != ln:
                hints.append((i + 1, "Trailing whitespace"))

        for i, ln in enumerate(lines):
            if "list" in ln and "size" not in ln:
                hints.append(
                    (i + 1, "Lists usually need a size: list size 5 set my_list")
                )

        return hints

    def _update_symbol_index(self, editor: QtWidgets.QPlainTextEdit, text: str):
        lines = text.splitlines()
        funcs: set[str] = set()
        vars_: set[str] = set()
        for ln in lines:
            fn_match = re.search(r"\bfunc(?:tion)?\s+\"([^\"]+)\"", ln)
            if fn_match:
                funcs.add(fn_match.group(1))
            for pat in [
                r"\bmake\s+([A-Za-z_][\w]*)",
                r"\bset\s+([A-Za-z_][\w]*)",
                r"\binput\s+([A-Za-z_][\w]*)",
            ]:
                m = re.search(pat, ln)
                if m:
                    vars_.add(m.group(1))
        self._symbols[editor] = {"funcs": funcs, "vars": vars_}
        if isinstance(editor, EditorWidget):
            editor.set_symbols(funcs, vars_)

    def _on_cursor_moved(self, editor: QtWidgets.QPlainTextEdit):
        pass

    def closeEvent(self, event: QtGui.QCloseEvent):
        if not self._confirm_close_all_tabs():
            event.ignore()
            return
        self._stop_process()
        self.build_paths.cleanup_all()
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._ensure_layout_sizes)

    # --- dirty-tracking and save helpers ---
    def _mark_dirty(self, editor: QtWidgets.QPlainTextEdit, dirty: bool):
        self._tab_dirty[editor] = dirty
        editor.document().setModified(dirty)
        self._update_tab_label(editor)

    def _update_tab_label(self, editor: QtWidgets.QWidget):
        idx = self.editor_tabs.indexOf(editor)
        if idx < 0:
            return
        path = self._tab_paths.get(editor)
        base = path.name if path else "Untitled"
        dirty = self._tab_dirty.get(editor, False)
        label = f"*{base}" if dirty else base
        self.editor_tabs.setTabText(idx, label)

    def _save_editor(
        self, editor: QtWidgets.QPlainTextEdit, *, force_dialog: bool = False
    ) -> bool:
        if not editor:
            return False
        current_path = self._tab_paths.get(editor)
        initial_dir = (
            current_path.parent if current_path else self.workspace_root or PROJECT_ROOT
        )
        path: Path | None = None
        if force_dialog or not current_path:
            selected, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Write file",
                str(initial_dir),
                "Write Files (*.write)",
            )
            if not selected:
                return False
            path = Path(selected)
        else:
            path = current_path
        if not path:
            return False
        path.write_text(editor.toPlainText(), encoding="utf-8")
        self._tab_paths[editor] = path
        self._mark_dirty(editor, False)
        self._log(f"Saved {path.name}")
        return True

    def _confirm_close_editor(self, editor: QtWidgets.QPlainTextEdit) -> bool:
        if not self._tab_dirty.get(editor):
            return True
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Unsaved changes")
        msg.setText("Save changes before closing?")
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Save
            | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel
        )
        msg.setDefaultButton(QtWidgets.QMessageBox.Save)
        choice = msg.exec()
        if choice == QtWidgets.QMessageBox.Cancel:
            return False
        if choice == QtWidgets.QMessageBox.Save:
            return self._save_editor(editor)
        return True

    def _confirm_close_all_tabs(self) -> bool:
        for idx in reversed(range(self.editor_tabs.count())):
            editor = self.editor_tabs.widget(idx)
            if isinstance(editor, QtWidgets.QPlainTextEdit):
                if not self._confirm_close_editor(editor):
                    return False
        return True
