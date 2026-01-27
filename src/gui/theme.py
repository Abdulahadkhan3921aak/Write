"""Theme management for Write IDE with light/dark/system modes."""

from __future__ import annotations

from enum import Enum

from PySide6 import QtCore, QtGui, QtWidgets


class ThemeMode(Enum):
    """Theme mode enumeration."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeManager:
    """Manages application theme with persistence."""

    KEYWORD_COLOR_LIGHT = "#0057b7"
    KEYWORD_COLOR_DARK = "#569cd6"
    NUMBER_COLOR_LIGHT = "#b71c1c"
    NUMBER_COLOR_DARK = "#ce9178"
    STRING_COLOR_LIGHT = "#2e7d32"
    STRING_COLOR_DARK = "#6a9955"
    COMMENT_COLOR_LIGHT = "#9e9e9e"
    COMMENT_COLOR_DARK = "#6a9955"

    BG_LIGHT = "#ffffff"
    BG_DARK = "#1e1e1e"
    FG_LIGHT = "#000000"
    FG_DARK = "#e0e0e0"
    EDITOR_BG_LIGHT = "#ffffff"
    EDITOR_BG_DARK = "#252526"
    EDITOR_FG_LIGHT = "#000000"
    EDITOR_FG_DARK = "#d4d4d4"

    def __init__(self):
        """Initialize theme manager."""
        self.settings = QtCore.QSettings("WriteIDE", "Write")
        self.current_mode = self._load_theme_mode()
        self._palettes = {
            ThemeMode.LIGHT: self._create_light_palette(),
            ThemeMode.DARK: self._create_dark_palette(),
        }

    def _load_theme_mode(self) -> ThemeMode:
        """Load theme mode from settings."""
        saved = self.settings.value("theme_mode", "system")
        try:
            return ThemeMode(saved)
        except ValueError:
            return ThemeMode.SYSTEM

    def save_theme_mode(self, mode: ThemeMode) -> None:
        """Save theme mode to settings."""
        self.current_mode = mode
        self.settings.setValue("theme_mode", mode.value)

    def get_active_mode(self) -> ThemeMode:
        """Get the currently active theme mode."""
        if self.current_mode == ThemeMode.SYSTEM:
            # Simple heuristic: check if palette is dark
            app = QtWidgets.QApplication.instance()
            if app:
                return (
                    ThemeMode.DARK
                    if self._is_dark_palette(app.palette())
                    else ThemeMode.LIGHT
                )
            return ThemeMode.LIGHT
        return self.current_mode

    def get_palette(self) -> QtGui.QPalette:
        """Get the appropriate palette for current mode."""
        active = self.get_active_mode()
        return self._palettes[active]

    def apply_theme(self, app: QtWidgets.QApplication) -> None:
        """Apply theme to application."""
        palette = self.get_palette()
        app.setPalette(palette)

    def _create_light_palette(self) -> QtGui.QPalette:
        """Create light theme palette."""
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(self.BG_LIGHT))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(self.FG_LIGHT))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(self.EDITOR_BG_LIGHT))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#f5f5f5"))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(self.EDITOR_FG_LIGHT))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#f0f0f0"))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(self.FG_LIGHT))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#0078d4"))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(self.BG_LIGHT))
        return palette

    def _create_dark_palette(self) -> QtGui.QPalette:
        """Create dark theme palette."""
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(self.BG_DARK))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(self.FG_DARK))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(self.EDITOR_BG_DARK))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#3e3e42"))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(self.EDITOR_FG_DARK))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#3e3e42"))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(self.FG_DARK))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#005a9e"))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(self.FG_DARK))
        return palette

    @staticmethod
    def _is_dark_palette(palette: QtGui.QPalette) -> bool:
        """Check if palette is dark-themed."""
        bg = palette.color(QtGui.QPalette.Window)
        return bg.lightness() < 128

    def get_syntax_colors(self) -> dict[str, str]:
        """Get syntax highlighting colors for current theme."""
        active = self.get_active_mode()
        if active == ThemeMode.DARK:
            return {
                "keyword": self.KEYWORD_COLOR_DARK,
                "number": self.NUMBER_COLOR_DARK,
                "string": self.STRING_COLOR_DARK,
                "comment": self.COMMENT_COLOR_DARK,
            }
        return {
            "keyword": self.KEYWORD_COLOR_LIGHT,
            "number": self.NUMBER_COLOR_LIGHT,
            "string": self.STRING_COLOR_LIGHT,
            "comment": self.COMMENT_COLOR_LIGHT,
        }
