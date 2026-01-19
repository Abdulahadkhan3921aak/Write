import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.codegen import Codegen


def transpile(code: str) -> str:
    tokens = Lexer(code).scan()
    program = Parser(tokens).parse()
    return Codegen().generate(program)


def test_hello_codegen_contains_main_and_cout():
    cpp = transpile('print "hi"')
    assert "int main()" in cpp
    assert 'cout << "hi"' in cpp


def test_loop_codegen():
    code = """
    for i from 1 to 2 do
        print i
    end for
    """
    cpp = transpile(code)
    assert "for (auto i = 1" in cpp
    assert "cout << i << endl" in cpp


def test_power_codegen():
    cpp = transpile("set p to power x and 2")
    assert "pow(" in cpp
    assert "auto p" in cpp


def test_declare_and_input_codegen():
    cpp = transpile("make a as int\ninput a\nset a to add a and 1")
    assert "int a;" in cpp
    assert "cin >> a;" in cpp
    assert "a = (a + 1);" in cpp
