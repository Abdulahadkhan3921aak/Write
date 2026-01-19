"""Simple CLI to lex a Write source file and print tokens."""

import argparse
from pathlib import Path

from .lexer import Lexer, LexerError


def main() -> int:
    parser = argparse.ArgumentParser(description="Lex a Write source file")
    parser.add_argument("path", type=Path, help="Path to Write source (.write)")
    args = parser.parse_args()

    try:
        text = args.path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"error: file not found: {args.path}")
        return 1

    try:
        tokens = Lexer(text).scan()
    except LexerError as e:
        print(f"lexer error: {e}")
        return 1

    for t in tokens:
        print(f"{t.kind.name}\t{t.lexeme!r}\t(line {t.line})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
