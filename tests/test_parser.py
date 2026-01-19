import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from compiler.lexer import Lexer
from compiler.parser import Parser, ParseError
from compiler import ast as ast_nodes


def parse(code: str):
    tokens = Lexer(code).scan()
    return Parser(tokens).parse()


def test_parse_assignment_and_print():
    program = parse("set x to 1\nprint x")
    assert len(program.statements) == 2
    assert isinstance(program.statements[0], ast_nodes.Assign)
    assert isinstance(program.statements[1], ast_nodes.Print)


def test_parse_if_else():
    code = """
    if x is greater than 2 then
        print "hi"
    else
        print "lo"
    end if
    """
    program = parse(code)
    assert isinstance(program.statements[0], ast_nodes.If)
    if_stmt = program.statements[0]
    assert if_stmt.else_body is not None


def test_parse_while():
    code = "while x < 3 do\n set x to add x and 1\nend while"
    program = parse(code)
    assert isinstance(program.statements[0], ast_nodes.While)


def test_parse_for():
    code = "for i from 1 to 3 do\n print i\nend for"
    program = parse(code)
    assert isinstance(program.statements[0], ast_nodes.For)


def test_parse_power():
    code = "set p to power x and 2"
    program = parse(code)
    assign = program.statements[0]
    assert isinstance(assign.expr, ast_nodes.Power)


def test_parse_declaration_and_input():
    program = parse("make a as int\ninput a")
    assert isinstance(program.statements[0], ast_nodes.Declaration)
    assert isinstance(program.statements[1], ast_nodes.Input)


def test_parse_errors_on_bad_token():
    with pytest.raises(Exception):
        parse("$")


def test_parse_print_multiple_values():
    program = parse('print "Hello, ", name')
    stmt = program.statements[0]
    assert isinstance(stmt, ast_nodes.Print)
    assert len(stmt.values) == 2
