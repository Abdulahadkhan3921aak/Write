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


def log_feature(name: str):
    # Helps surface which language feature a test is exercising when run with -s
    print(f"[feature] {name}")


def parse(code: str):
    tokens = Lexer(code).scan()
    return Parser(tokens).parse()


def test_parse_assignment_and_print():
    log_feature("assignment and print")
    program = parse("set x to 1\nprint x")
    assert len(program.statements) == 2
    assert isinstance(program.statements[0], ast_nodes.Assign)
    assert isinstance(program.statements[1], ast_nodes.Print)


def test_parse_if_else():
    log_feature("if/else")
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
    log_feature("while loop")
    code = "while x < 3 do\n set x to add x and 1\nend while"
    program = parse(code)
    assert isinstance(program.statements[0], ast_nodes.While)


def test_parse_for():
    log_feature("for loop")
    code = "for i from 1 to 3 do\n print i\nend for"
    program = parse(code)
    assert isinstance(program.statements[0], ast_nodes.For)


def test_parse_power():
    log_feature("power expression")
    code = "set p to power x and 2"
    program = parse(code)
    assign = program.statements[0]
    assert isinstance(assign.expr, ast_nodes.Power)


def test_parse_declaration_and_input():
    log_feature("declaration with type and input")
    program = parse("make a as int\ninput a")
    assert isinstance(program.statements[0], ast_nodes.Declaration)
    assert program.statements[0].type == "int"
    assert isinstance(program.statements[1], ast_nodes.Input)


def test_parse_typeless_declaration():
    log_feature("typeless make declaration")
    program = parse("make x\nset x to 5")
    decl = program.statements[0]
    assert isinstance(decl, ast_nodes.Declaration)
    assert decl.type is None


def test_parse_list_and_array_types():
    log_feature("list/array declarations")
    program = parse("make items as list\nmake arr as array")
    decl1, decl2 = program.statements[0], program.statements[1]
    assert isinstance(decl1, ast_nodes.Declaration)
    assert decl1.type == "list"
    assert isinstance(decl2, ast_nodes.Declaration)
    assert decl2.type == "array"


def test_parse_errors_on_bad_token():
    log_feature("error on bad token")
    with pytest.raises(Exception):
        parse("$")


def test_parse_print_multiple_values():
    log_feature("print multiple values")
    program = parse('print "Hello, ", name')
    stmt = program.statements[0]
    assert isinstance(stmt, ast_nodes.Print)
    assert len(stmt.values) == 2


def test_parse_print_adjacent_without_commas():
    log_feature("print adjacent values")
    program = parse('print "Hi " name')
    stmt = program.statements[0]
    assert isinstance(stmt, ast_nodes.Print)
    assert len(stmt.values) == 2


def test_parse_input_with_prompt():
    log_feature("input with prompt")
    program = parse('input "What is your name" user as string')
    stmt = program.statements[0]
    assert isinstance(stmt, ast_nodes.Input)
    assert stmt.prompt == "What is your name"


def test_parse_less_than_or_equal_phrase():
    log_feature("comparison phrase")
    program = parse("while i is less than or equal to n do\n end while")
    stmt = program.statements[0]
    assert isinstance(stmt, ast_nodes.While)


def test_parse_function_and_call():
    log_feature("function definition and call")
    code = 'function "add"(a:int, b:int)\n    set c to add a and b\n    return c\nend function\ncall "add" with arguments:(5,4)'
    program = parse(code)
    assert len(program.functions) == 1
    assert program.functions[0].name == "add"
    assert len(program.functions[0].params) == 2
    assert isinstance(program.statements[0], ast_nodes.Call)


def test_parse_return_multiple():
    log_feature("multiple return values")
    code = 'function "pair"(x, y)\n return x, y\nend function'
    program = parse(code)
    fn = program.functions[0]
    assert any(isinstance(s, ast_nodes.Return) for s in fn.body)


def test_parse_typed_set_and_add_phrase():
    log_feature("typed set and add phrase")
    code = "set x:int to 6\nset x to add 6 to x"
    program = parse(code)
    first = program.statements[0]
    second = program.statements[1]
    assert isinstance(first, ast_nodes.Assign)
    assert first.type == "int"
    assert isinstance(second, ast_nodes.Assign)
    assert isinstance(second.expr, ast_nodes.Binary)
    assert second.expr.op == "+"


def test_parse_inplace_add_and_sub():
    log_feature("in-place add and sub")
    code = "set x:int to 6\nadd 6 to x\nsub 2 from x"
    program = parse(code)
    add_stmt = program.statements[1]
    sub_stmt = program.statements[2]
    assert isinstance(add_stmt, ast_nodes.Assign)
    assert add_stmt.name == "x"
    assert isinstance(add_stmt.expr, ast_nodes.Binary)
    assert add_stmt.expr.op == "+"
    assert isinstance(sub_stmt, ast_nodes.Assign)
    assert sub_stmt.expr.op == "-"
