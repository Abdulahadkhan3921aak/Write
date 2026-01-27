"""Entry point for the Write IDE GUI."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from .main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 700)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
