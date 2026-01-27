"""Code completion system for the Write IDE."""

from __future__ import annotations

from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets


class CompletionModel(QtCore.QAbstractListModel):
    """Model for code completions."""

    def __init__(self, items: list[str] | None = None, parent=None):
        """Initialize completion model."""
        super().__init__(parent)
        self.items = items or []

    def rowCount(self, parent=None) -> int:
        """Return number of completions."""
        return len(self.items)

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.DisplayRole):
        """Return completion item data."""
        if not index.isValid() or index.row() >= len(self.items):
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.items[index.row()]
        return None

    def set_items(self, items: list[str]) -> None:
        """Update completion items."""
        self.beginResetModel()
        self.items = items
        self.endResetModel()


class CompletionPopup(QtWidgets.QListView):
    """Popup completion list view."""

    completion_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        """Initialize completion popup."""
        super().__init__(parent)
        self.model = CompletionModel()
        self.setModel(self.model)
        # Use tooltip-style window so it never steals focus from the editor.
        self.setWindowFlags(QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFocusProxy(parent)
        self.setMaximumHeight(220)
        self.setMaximumWidth(340)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(
            """
            QListView {
                background: #1e1e1e;
                color: #e5e5e5;
                border: 1px solid #3a3a3a;
                padding: 4px;
                outline: none;
            }
            QListView::item { padding: 4px 6px; }
            QListView::item:selected { background: #264f78; color: #ffffff; }
            """
        )
        self.clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, index: QtCore.QModelIndex) -> None:
        """Handle completion selection."""
        if index.isValid():
            text = self.model.data(index, QtCore.Qt.DisplayRole)
            if text:
                self.completion_selected.emit(text)
                self.hide()

    def show_at_cursor(self, pos: QtCore.QPoint, items: list[str]) -> None:
        """Show popup at cursor position with items."""
        if not items:
            self.hide()
            return
        self.model.set_items(items)
        self.move(pos)
        self.show()
        # Select first item
        if self.model.rowCount() > 0:
            self.setCurrentIndex(self.model.index(0, 0))

    def select_next(self) -> None:
        """Select next completion."""
        idx = self.currentIndex()
        if idx.isValid() and idx.row() < self.model.rowCount() - 1:
            self.setCurrentIndex(self.model.index(idx.row() + 1, 0))

    def select_previous(self) -> None:
        """Select previous completion."""
        idx = self.currentIndex()
        if idx.isValid() and idx.row() > 0:
            self.setCurrentIndex(self.model.index(idx.row() - 1, 0))

    def get_selected(self) -> str | None:
        """Get currently selected completion."""
        idx = self.currentIndex()
        if idx.isValid():
            return self.model.data(idx, QtCore.Qt.DisplayRole)
        return None


class CompletionProvider:
    """Provides completions based on context."""

    def __init__(self, keywords: list[str] | None = None):
        """Initialize completion provider."""
        self.keywords = keywords or []
        self.symbols = {"funcs": set(), "vars": set()}

    def set_symbols(self, funcs: set[str], vars_: set[str]) -> None:
        """Update available symbols."""
        self.symbols = {"funcs": funcs, "vars": vars_}

    def get_completions(self, prefix: str, context: str = "") -> list[str]:
        """Get completion candidates for prefix and context."""
        lower_prefix = prefix.lower()
        candidates = []

        # Add matching keywords
        candidates.extend([k for k in self.keywords if k.startswith(lower_prefix)])

        # Add matching functions if in "call" context
        if "call" in context.lower():
            candidates.extend(
                [f for f in self.symbols["funcs"] if f.startswith(prefix)]
            )
        # Add matching variables if in assignment context
        elif any(ctx in context.lower() for ctx in ["set", "make", "input"]):
            candidates.extend([v for v in self.symbols["vars"] if v.startswith(prefix)])

        # Remove duplicates and sort
        return sorted(set(candidates))

    def get_best_completion(self, prefix: str, context: str = "") -> str | None:
        """Get single best completion if confidence is high."""
        completions = self.get_completions(prefix, context)
        if len(completions) == 1:
            return completions[0]
        return None
