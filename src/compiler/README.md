# Compiler skeleton

Planned components:

- Lexer: tokenize keywords, identifiers, numbers, strings, operators, punctuation
- Parser: LL-style parsing per grammar in spec/grammar.md
- AST: node definitions for statements/expressions
- Semantic checks: scopes, types, undefined identifiers, basic type rules
- Codegen: emit C/C++ (and optionally direct C) with minimal runtime helpers (print/power)
- CLI entry: transpile Write source to C/C++ and optionally invoke system compiler

Implementation language: TBD (Python is a likely choice for speed of delivery). Wire this directory accordingly when chosen.
