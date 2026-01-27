"""Menu and action system for Write IDE."""

from __future__ import annotations

from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets


class ActionManager:
    """Manages menus and shortcuts for the application."""

    def __init__(self, parent: QtWidgets.QMainWindow):
        """Initialize action manager."""
        self.parent = parent
        self.actions = {}

    def setup_file_menu(
        self,
        on_new: Callable,
        on_save: Callable,
        on_save_as: Callable,
        on_open: Callable,
    ) -> QtWidgets.QMenu:
        """Setup File menu."""
        menu = self.parent.menuBar().addMenu("File")

        new_action = QtGui.QAction("New File", self.parent)
        new_action.setShortcut(QtGui.QKeySequence.New)
        new_action.triggered.connect(on_new)
        menu.addAction(new_action)
        self.actions["new"] = new_action

        open_action = QtGui.QAction("Open File", self.parent)
        open_action.setShortcut(QtGui.QKeySequence.Open)
        open_action.triggered.connect(on_open)
        menu.addAction(open_action)
        self.actions["open"] = open_action

        menu.addSeparator()

        save_action = QtGui.QAction("Save", self.parent)
        save_action.setShortcut(QtGui.QKeySequence.Save)
        save_action.triggered.connect(on_save)
        menu.addAction(save_action)
        self.actions["save"] = save_action

        save_as_action = QtGui.QAction("Save As…", self.parent)
        save_as_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(on_save_as)
        menu.addAction(save_as_action)
        self.actions["save_as"] = save_as_action

        return menu

    def setup_view_menu(
        self,
        on_inc_font: Callable,
        on_dec_font: Callable,
        on_reset_font: Callable,
        on_toggle_split: Callable,
        on_toggle_cpp: Callable,
        on_theme: Callable,
    ) -> QtWidgets.QMenu:
        """Setup View menu."""
        menu = self.parent.menuBar().addMenu("View")

        inc_font = QtGui.QAction("Increase Editor Font", self.parent)
        inc_font.triggered.connect(on_inc_font)
        menu.addAction(inc_font)

        dec_font = QtGui.QAction("Decrease Editor Font", self.parent)
        dec_font.triggered.connect(on_dec_font)
        menu.addAction(dec_font)

        reset_font = QtGui.QAction("Reset Editor Font", self.parent)
        reset_font.triggered.connect(on_reset_font)
        menu.addAction(reset_font)

        menu.addSeparator()

        toggle_split = QtGui.QAction("Toggle Code Split Orientation", self.parent)
        toggle_split.triggered.connect(on_toggle_split)
        menu.addAction(toggle_split)

        toggle_cpp = QtGui.QAction("Show/Hide C++ Pane", self.parent)
        toggle_cpp.triggered.connect(on_toggle_cpp)
        menu.addAction(toggle_cpp)

        menu.addSeparator()

        theme_action = QtGui.QAction("Theme Settings", self.parent)
        theme_action.triggered.connect(on_theme)
        menu.addAction(theme_action)

        return menu

    def setup_tools_menu(
        self,
        on_set_compiler: Callable,
        on_set_flags: Callable,
        on_keyword_help: Callable,
    ) -> QtWidgets.QMenu:
        """Setup Tools menu."""
        menu = self.parent.menuBar().addMenu("Tools")

        set_compiler = QtGui.QAction("Set Compiler Path…", self.parent)
        set_compiler.triggered.connect(on_set_compiler)
        menu.addAction(set_compiler)

        set_flags = QtGui.QAction("Set Extra Flags…", self.parent)
        set_flags.triggered.connect(on_set_flags)
        menu.addAction(set_flags)

        menu.addSeparator()

        help_action = QtGui.QAction("Keyword Help", self.parent)
        help_action.triggered.connect(on_keyword_help)
        menu.addAction(help_action)

        return menu

    def setup_help_menu(self) -> QtWidgets.QMenu:
        """Setup Help menu."""
        menu = self.parent.menuBar().addMenu("Help")

        about_action = QtGui.QAction("About Write IDE", self.parent)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        return menu

    def _show_about(self) -> None:
        """Show about dialog."""
        QtWidgets.QMessageBox.about(
            self.parent,
            "About Write IDE",
            "Write IDE - A language IDE for the Write language\n\n"
            "Features:\n"
            "• Syntax highlighting\n"
            "• Code completion\n"
            "• Error diagnostics\n"
            "• C++ code generation\n"
            "• Interactive execution\n",
        )
