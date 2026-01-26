"""Syntax highlighting rules for the Write language."""

from __future__ import annotations

from PySide6 import QtCore, QtGui


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
            "sub",
            "multiply",
            "divide",
            "power",
            "function",
            "func",
            "list",
            "array",
            "end_function",
            "end_func",
            "arguments",
            "arg",
            "args",
            "return",
            "with",
            "call",
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
