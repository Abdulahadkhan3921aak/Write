"""Ensure local 'src' is importable when running tools from project root.
Python auto-imports sitecustomize if present on sys.path; project root is on sys.path when you run from here.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent
src = root / "src"
if src.exists():
    sys.path.insert(0, str(src))
