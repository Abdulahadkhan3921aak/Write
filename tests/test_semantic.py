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


def analyze(code: str):
    tokens = Lexer(code).scan()
    program = Parser(tokens).parse()
    Analyzer(code).analyze(program)


def test_undefined_variable():
    with pytest.raises(SemanticError):
        analyze("print x")


def test_string_in_arithmetic_disallowed():
    with pytest.raises(SemanticError):
        analyze('set x to add "hi" and 1')


def test_numeric_ok():
    analyze("set x to add 1 and 2")  # should not raise


def test_for_requires_numeric_bounds():
    with pytest.raises(SemanticError):
        analyze('for i from "a" to 3 do\n print i\nend for')


def test_power_requires_numeric():
    with pytest.raises(SemanticError):
        analyze('set p to power "a" and 2')


def test_comparison_type_mismatch():
    with pytest.raises(SemanticError):
        analyze('if "a" > 1 then\n print 1\nend if')


def test_redeclaration_error():
    with pytest.raises(SemanticError):
        analyze("make x as int\nmake x as int")


def test_input_requires_declaration():
    with pytest.raises(SemanticError):
        analyze("input y")


def test_type_mismatch_assignment():
    with pytest.raises(SemanticError):
        analyze("make s as string\nset s to add 1 and 2")
