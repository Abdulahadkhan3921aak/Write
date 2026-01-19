"""
Write language lexer skeleton.

Tokenizes keywords, identifiers, numbers, strings, and operators per spec/lexer.md.
This is a minimal scaffold; fill in scan logic next.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenKind(Enum):
    # Single / multi-char operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    BANG = auto()
    AMP = auto()
    PIPE = auto()
    EQEQ = auto()
    EQ = auto()
    NEQ = auto()
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()

    # Literals / identifiers
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    # Keywords (store lexeme to disambiguate phrases in parser)
    KEYWORD = auto()

    EOF = auto()


KEYWORDS = {
    "set",
    "to",
    "print",
    "make",
    "input",
    "as",
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
    # arithmetic words can be treated as keywords if desired
    "add",
    "subtract",
    "multiply",
    "divide",
    "power",
    "int",
    "float",
    "string",
    "bool",
}


@dataclass
class Token:
    kind: TokenKind
    lexeme: str
    line: int
    col: int


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.start = 0

    def scan(self) -> List[Token]:
        while not self._is_at_end():
            self.start = self.pos
            c = self._advance()

            # Whitespace / newlines
            if c in " \t\r":
                continue
            if c == "\n":
                self.line += 1
                self.col = 1
                continue

            # Comment (line, starting with #)
            if c == "#":
                self._skip_until_newline()
                continue

            # Strings
            if c == '"':
                self._string()
                continue

            # Numbers
            if c.isdigit():
                self._number()
                continue

            # Ident / keyword
            if c.isalpha() or c == "_":
                self._identifier()
                continue

            # Operators / punctuation (longest match handled by branching)
            if c == "=":
                if self._match("="):
                    self._add(TokenKind.EQEQ)
                else:
                    self._add(TokenKind.EQ)
                continue
            if c == "!":
                if self._match("="):
                    self._add(TokenKind.NEQ)
                else:
                    self._add(TokenKind.BANG)
                continue
            if c == ">":
                if self._match("="):
                    self._add(TokenKind.GTE)
                else:
                    self._add(TokenKind.GT)
                continue
            if c == "<":
                if self._match("="):
                    self._add(TokenKind.LTE)
                else:
                    self._add(TokenKind.LT)
                continue
            if c == "&":
                self._add(TokenKind.AMP)
                continue
            if c == "|":
                self._add(TokenKind.PIPE)
                continue
            if c == "+":
                self._add(TokenKind.PLUS)
                continue
            if c == "-":
                self._add(TokenKind.MINUS)
                continue
            if c == "*":
                self._add(TokenKind.STAR)
                continue
            if c == "/":
                self._add(TokenKind.SLASH)
                continue
            if c == "^":
                self._add(TokenKind.CARET)
                continue
            if c == "(":
                self._add(TokenKind.LPAREN)
                continue
            if c == ")":
                self._add(TokenKind.RPAREN)
                continue
            if c == ",":
                self._add(TokenKind.COMMA)
                continue

            raise LexerError(f"Unhandled character '{c}' at {self.line}:{self.col}")

        self.tokens.append(Token(TokenKind.EOF, "", self.line, self.col))
        return self.tokens

    def _add(self, kind: TokenKind, lexeme: Optional[str] = None) -> None:
        text = lexeme if lexeme is not None else self.source[self.start : self.pos]
        self.tokens.append(Token(kind, text, self.line, self.col))

    def _is_at_end(self) -> bool:
        return self.pos >= self.length

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        self.col += 1
        return ch

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.pos]

    def _match(self, expected: str) -> bool:
        if self._is_at_end() or self.source[self.pos] != expected:
            return False
        self.pos += 1
        self.col += 1
        return True

    def _skip_until_newline(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _string(self) -> None:
        # Scan until closing quote, supporting escaped quotes/backslashes.
        escaped = False
        while not self._is_at_end():
            ch = self._advance()
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                # Include content without surrounding quotes
                lexeme = self.source[self.start + 1 : self.pos - 1]
                self._add(TokenKind.STRING, lexeme)
                return
            if ch == "\n":
                self.line += 1
                self.col = 1
        raise LexerError(f"Unterminated string at {self.line}:{self.col}")

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()  # consume '.'
            while self._peek().isdigit():
                self._advance()
        lexeme = self.source[self.start : self.pos]
        self._add(TokenKind.NUMBER, lexeme)

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[self.start : self.pos]
        if text in KEYWORDS:
            self._add(TokenKind.KEYWORD, text)
        else:
            self._add(TokenKind.IDENT, text)

    def _peek_next(self) -> str:
        if self.pos + 1 >= self.length:
            return "\0"
        return self.source[self.pos + 1]


__all__ = ["Lexer", "Token", "TokenKind", "LexerError", "KEYWORDS"]
