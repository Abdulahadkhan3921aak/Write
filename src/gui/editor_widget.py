"""Enhanced editor widget with completions and hover help."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .completions import CompletionPopup, CompletionProvider
from .highlighter import WriteHighlighter
from .keyword_help import KeywordDatabase


class EditorWidget(QtWidgets.QPlainTextEdit):
    """Enhanced plain text editor with completions and hover help."""

    def __init__(self, parent=None):
        """Initialize editor widget."""
        super().__init__(parent)
        self.setPlaceholderText("Write code here…")
        mono_font = QtGui.QFont("Consolas", 14)
        self.setFont(mono_font)

        # Setup syntax highlighting
        WriteHighlighter(self.document())

        # Setup completions
        self.completion_provider = CompletionProvider(
            KeywordDatabase.get_all_keywords()
        )
        self.completion_popup = CompletionPopup(self)
        self.completion_popup.completion_selected.connect(self._on_completion_selected)

        # Setup hover help
        self.setMouseTracking(True)
        self._last_hovered_word = ""

        # Ghost text (grayed out prediction)
        self._ghost_text = ""
        self._show_ghost = False

        # Connect signals
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)

        # Store symbols for completions
        self._symbols = {"funcs": set(), "vars": set()}

    def set_symbols(self, funcs: set[str], vars_: set[str]) -> None:
        """Update available symbols for completions."""
        self._symbols = {"funcs": funcs, "vars": vars_}
        self.completion_provider.set_symbols(funcs, vars_)

    def _on_text_changed(self):
        """Handle text changes."""
        # Could trigger background linting or other analysis here
        pass

    def _on_cursor_moved(self):
        """Handle cursor movement - check for completions."""
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()

        # Extract word being typed
        prefix = block_text[:pos_in_block]
        word = self._extract_current_word(prefix)

        if len(word) > 1:
            # Show completions popup on typing
            self._show_completions(word, prefix)
        else:
            self.completion_popup.hide()

        # Check for hover help
        self._check_hover_help(block_text, pos_in_block)

    def _extract_current_word(self, text: str) -> str:
        """Extract the word being typed from prefix."""
        # Simple extraction: find word boundaries
        import re

        matches = list(re.finditer(r"\b\w+$", text))
        if matches:
            return matches[-1].group(0)
        return ""

    def _show_completions(self, word: str, context: str) -> None:
        """Show completion popup."""
        completions = self.completion_provider.get_completions(word, context)

        if not completions:
            self.completion_popup.hide()
            return

        # Position popup at cursor
        cursor = self.textCursor()
        cursor_rect = self.cursorRect(cursor)
        global_pos = self.mapToGlobal(cursor_rect.bottomLeft())

        self.completion_popup.show_at_cursor(global_pos, completions)

        # Show ghost text if single best match
        best = self.completion_provider.get_best_completion(word, context)
        if best and best != word:
            self._show_ghost_text(best[len(word) :])
        else:
            self._show_ghost_text("")

    def _show_ghost_text(self, ghost: str) -> None:
        """Display grayed-out ghost text prediction."""
        self._ghost_text = ghost
        self._show_ghost = bool(ghost)
        self.viewport().update()

    def _check_hover_help(self, block_text: str, pos_in_block: int) -> None:
        """Check for keyword help at cursor position."""
        import re

        # Find all words in line
        words = re.findall(r"\w+", block_text)
        for match in re.finditer(r"\w+", block_text):
            if match.start() <= pos_in_block <= match.end():
                word = match.group(0)
                if word != self._last_hovered_word:
                    self._last_hovered_word = word
                    help_text = KeywordDatabase.get_help(word)
                    if help_text:
                        cursor_rect = self.cursorRect(self.textCursor())
                        global_pos = self.mapToGlobal(cursor_rect.bottomRight())
                        QtWidgets.QToolTip.showText(global_pos, help_text, self)
                return

        QtWidgets.QToolTip.hideText()
        self._last_hovered_word = ""

    def _on_completion_selected(self, completion: str) -> None:
        """Insert selected completion."""
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()

        # Find the word start
        prefix = block_text[:pos_in_block]
        word = self._extract_current_word(prefix)

        if word:
            # Replace the word with completion
            cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
            cursor.movePosition(
                QtGui.QTextCursor.Right,
                QtGui.QTextCursor.MoveAnchor,
                pos_in_block - len(word),
            )
            cursor.movePosition(
                QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor, len(word)
            )
            cursor.insertText(completion)
            self.setTextCursor(cursor)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Handle key press events."""
        # Handle completion popup navigation
        if self.completion_popup.isVisible():
            if event.key() == QtCore.Qt.Key_Up:
                self.completion_popup.select_previous()
                return
            elif event.key() == QtCore.Qt.Key_Down:
                self.completion_popup.select_next()
                return
            elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Tab):
                selected = self.completion_popup.get_selected()
                if selected:
                    self._on_completion_selected(selected)
                    return
            elif event.key() == QtCore.Qt.Key_Escape:
                self.completion_popup.hide()
                return

        # Handle manual completion trigger (Ctrl+Space)
        if (
            event.key() == QtCore.Qt.Key_Space
            and event.modifiers() & QtCore.Qt.ControlModifier
        ):
            cursor = self.textCursor()
            block_text = cursor.block().text()
            pos_in_block = cursor.positionInBlock()
            prefix = block_text[:pos_in_block]
            word = self._extract_current_word(prefix)
            self._show_completions(word, prefix)
            return

        # Default key handling
        super().keyPressEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint editor with ghost text."""
        super().paintEvent(event)

        if not self._show_ghost or not self._ghost_text:
            return

        cursor = self.textCursor()
        cursor_rect = self.cursorRect(cursor)

        painter = QtGui.QPainter(self.viewport())
        painter.setFont(self.font())
        painter.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 120)))

        x = cursor_rect.left()
        y = cursor_rect.top()
        painter.drawText(x, y + self.fontMetrics().ascent(), self._ghost_text)
        painter.end()
