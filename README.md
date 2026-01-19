# Write

English-like teaching language (ELang/"Write") that transpiles to C/C++ plus a beginner-friendly GUI. This repo will host the spec, compiler, GUI, examples, and build scripts.

## Layout

- docs/ — narrative docs (syntax, semantics, keywords)
- spec/ — formal grammar and sample programs
- spec/examples/ — source samples in Write
- src/compiler/ — lexer, parser, AST, semantic checks, codegen, CLI
- src/gui/ — GUI app (Python) that drives the compiler
- scripts/ — build/packaging helpers (e.g., transpile+compile pipelines)
- tests/ — unit and integration tests for compiler and GUI

## Status

Scaffolding created. Next steps: pin grammar, implement lexer/parser, and wire GUI to the compiler CLI.
