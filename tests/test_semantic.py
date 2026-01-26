import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import Analyzer, SemanticError


def log_feature(name: str):
    print(f"[feature] {name}")


def analyze(code: str):
    tokens = Lexer(code).scan()
    program = Parser(tokens).parse()
    Analyzer(code).analyze(program)


def test_undefined_variable():
    log_feature("undefined variable")
    with pytest.raises(SemanticError):
        analyze("print x")


def test_string_in_arithmetic_disallowed():
    log_feature("string in arithmetic disallowed")
    with pytest.raises(SemanticError):
        analyze('set x to add "hi" and 1')


def test_numeric_ok():
    log_feature("numeric arithmetic allowed")
    analyze("set x to add 1 and 2")  # should not raise


def test_for_requires_numeric_bounds():
    log_feature("for bounds numeric check")
    with pytest.raises(SemanticError):
        analyze('for i from "a" to 3 do\n print i\nend for')


def test_power_requires_numeric():
    log_feature("power numeric operands")
    with pytest.raises(SemanticError):
        analyze('set p to power "a" and 2')


def test_comparison_type_mismatch():
    log_feature("comparison type mismatch")
    with pytest.raises(SemanticError):
        analyze('if "a" > 1 then\n print 1\nend if')


def test_redeclaration_error():
    log_feature("redeclaration error")
    with pytest.raises(SemanticError):
        analyze("make x as int\nmake x as int")


def test_input_requires_declaration():
    log_feature("input requires declaration")
    with pytest.raises(SemanticError):
        analyze("input y")


def test_type_mismatch_assignment():
    log_feature("type mismatch assignment")
    with pytest.raises(SemanticError):
        analyze("make s as string\nset s to add 1 and 2")


def test_typeless_declaration_allows_assignment():
    log_feature("typeless declaration allowed")
    analyze("make x\nset x to 5")


def test_list_and_array_types_allowed():
    log_feature("list/array types allowed")
    analyze("make items as list\nmake arr as array")


def test_unary_not_allows_boolean_expr():
    log_feature("boolean not expression")
    analyze("set a to 1\nset b to 0\nif !(a == 0 | b == 0) then\n print a\nend if")


def test_function_call_typechecking():
    log_feature("function call typechecking")
    code = 'function "f"(a:int, b:int)\n set c to add a and b\n return c\nend function\ncall "f" with arguments:(1, 2)'
    analyze(code)  # should not raise


def test_function_call_missing_arg():
    log_feature("function call missing arg")
    code = 'function "f"(a:int, b:int)\n set c to add a and b\n return c\nend function\ncall "f" with arguments:(1)'
    with pytest.raises(SemanticError):
        analyze(code)


def test_return_outside_function_error():
    log_feature("return outside function")
    with pytest.raises(SemanticError):
        analyze("return 1")


def test_index_literal_out_of_bounds_read():
    log_feature("index literal out of bounds read")
    with pytest.raises(SemanticError):
        analyze("make xs as list of size 3\nset y to xs[3]")


def test_index_literal_out_of_bounds_write():
    log_feature("index literal out of bounds write")
    with pytest.raises(SemanticError):
        analyze("make xs as array of size 2\nset xs[2] to 5")


def test_index_literal_in_bounds_ok():
    log_feature("index literal in bounds ok")
    analyze("make xs as list of size 2\nset xs[1] to 5\nset y to xs[1]")
