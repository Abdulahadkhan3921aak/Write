import sys
from pathlib import Path

import pytest

# Make src importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from compiler.lexer import Lexer, TokenKind  # noqa: E402


def kinds(code: str):
    return [t.kind for t in Lexer(code).scan()]


def test_assignment_and_add():
    tokens = kinds("set x to add y and 3")
    assert tokens == [
        TokenKind.KEYWORD,  # set
        TokenKind.IDENT,  # x
        TokenKind.KEYWORD,  # to
        TokenKind.KEYWORD,  # add
        TokenKind.IDENT,  # y
        TokenKind.KEYWORD,  # and
        TokenKind.NUMBER,  # 3
        TokenKind.EOF,
    ]


def test_if_mixed_ops():
    code = """
    if x is greater than 2 and y <= 5 then
        print "ok"
    end if
    """
    tokens = kinds(code)
    assert tokens[:10] == [
        TokenKind.KEYWORD,  # if
        TokenKind.IDENT,  # x
        TokenKind.KEYWORD,  # is
        TokenKind.KEYWORD,  # greater
        TokenKind.KEYWORD,  # than
        TokenKind.NUMBER,  # 2
        TokenKind.KEYWORD,  # and
        TokenKind.IDENT,  # y
        TokenKind.LTE,  # <=
        TokenKind.NUMBER,  # 5
    ]
    assert tokens[-1] == TokenKind.EOF


def test_while_with_symbols():
    code = "while !(a == 0 | b == 0) do\n end while"
    tokens = kinds(code)
    assert TokenKind.BANG in tokens
    assert TokenKind.LPAREN in tokens
    assert TokenKind.PIPE in tokens
    assert tokens[-1] == TokenKind.EOF


def test_for_loop():
    code = "for i from 1 to 3 do\n print i\nend for"
    tokens = kinds(code)
    assert tokens[:7] == [
        TokenKind.KEYWORD,  # for
        TokenKind.IDENT,  # i
        TokenKind.KEYWORD,  # from
        TokenKind.NUMBER,  # 1
        TokenKind.KEYWORD,  # to
        TokenKind.NUMBER,  # 3
        TokenKind.KEYWORD,  # do
    ]


def test_power_and_equals():
    code = "set p = x ^ 2"
    tokens = kinds(code)
    assert TokenKind.EQ in tokens
    assert TokenKind.CARET in tokens
    assert TokenKind.NUMBER in tokens
    assert tokens[-1] == TokenKind.EOF


def test_unterminated_string_raises():
    with pytest.raises(Exception):
        Lexer('print "oops').scan()


def test_function_tokens():
    tokens = kinds('function "f" (a:int, b, c="hi")\nend function')
    assert TokenKind.KEYWORD in tokens  # function keyword
    assert TokenKind.STRING in tokens  # name
    assert TokenKind.COLON in tokens
    assert TokenKind.LPAREN in tokens and TokenKind.RPAREN in tokens
    assert TokenKind.KEYWORD in tokens  # end/function pair


def test_return_tokens():
    tokens = kinds('function "f"()\nreturn 1, 2\nend function')
    assert TokenKind.KEYWORD in tokens
