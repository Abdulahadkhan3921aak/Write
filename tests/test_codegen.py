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
    assert "read_value(a);" in cpp
    assert "a = (a + 1);" in cpp


def test_input_prompt_codegen():
    cpp = transpile('input "Prompt" user as string')
    assert 'cout << "Prompt"; cout.flush();' in cpp
    assert "write_runtime::read_value(user);" in cpp


def test_function_codegen_and_call():
    code = 'function "greet"(name:string="world")\n print "hello " name\nend function\ncall "greet" with arguments:("write")'
    cpp = transpile(code)
    assert "void greet" in cpp
    assert "hello " in cpp
    assert 'greet("write")' in cpp


def test_return_codegen_single():
    code = 'function "square"(x:int)\n return multiply x and x\nend function\ncall "square" with arguments:(4)'
    cpp = transpile(code)
    assert "auto square" in cpp
    assert "return (x * x);" in cpp


def test_return_codegen_multiple():
    code = 'function "swap"(a, b)\n return b, a\nend function\ncall "swap" with arguments:(1,2)'
    cpp = transpile(code)
    assert "auto swap" in cpp
    assert "std::make_tuple" in cpp
