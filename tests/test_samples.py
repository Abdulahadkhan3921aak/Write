import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from compiler.codegen import Codegen  # noqa: E402
from compiler.lexer import Lexer  # noqa: E402
from compiler.parser import Parser  # noqa: E402
from compiler.semantic import Analyzer, SemanticError  # noqa: E402


GOOD_SAMPLES = [
    "hello.write",
    "logic.write",
    "loops.write",
    "factorial.write",
    "functions.write",
    "containers_sized.write",
    "functions_and_calls.write",
    "full_language_tour.write",
    "named_args_and_defaults.write",
    "io_and_conditions.write",
]

NEGATIVE_SAMPLES = [
    "diagnostics_showcase.write",
]


@pytest.mark.parametrize("filename", GOOD_SAMPLES)
def test_samples_parse_analyze_codegen(filename: str):
    sample_path = ROOT / "spec" / "examples" / filename
    source = sample_path.read_text(encoding="utf-8")
    tokens = Lexer(source).scan()
    program = Parser(tokens).parse()
    Analyzer(source).analyze(program)
    cpp = Codegen().generate(program)
    assert cpp.strip(), "generated C++ should not be empty"


@pytest.mark.parametrize("filename", NEGATIVE_SAMPLES)
def test_negative_samples_raise_semantic_error(filename: str):
    sample_path = ROOT / "spec" / "examples" / filename
    source = sample_path.read_text(encoding="utf-8")
    tokens = Lexer(source).scan()
    program = Parser(tokens).parse()
    with pytest.raises(SemanticError):
        Analyzer(source).analyze(program)
