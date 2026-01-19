# Tests

Plan test coverage:

- Lexer: tokenization of keywords, identifiers, numbers, strings, operators
- Parser: valid/invalid programs; precedence/associativity cases
- Semantics: undefined variables, type checks (if enforced), loop/condition rules
- Codegen: snapshot tests comparing generated C/C++ for fixtures in spec/examples
- GUI: smoke tests for compile/run flows once implemented
