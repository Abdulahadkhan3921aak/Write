# Write

English-like teaching language that transpiles to C++ with a beginner-friendly PySide6 GUI.

## Features

- Lexer, parser, semantic analyzer (types, container size/bounds, function args), and C++17 codegen.
- Containers (`list`/`array`) with indexing; printing lists/arrays renders as `[1, 2, 3]`.
- GUI editor with syntax highlighting, save/save-as, dirty-tab prompts, split C++ preview, run/compile buttons.
- Diagnostics panel plus inline lint hints (dashed underline) and tooltip suggestions for functions/variables.
- Sample programs in `spec/examples/`; integration tests via pytest.

## Project Structure

- docs/ — syntax, semantics, keywords, GUI notes
- spec/ — grammar and language docs
- spec/examples/ — sample Write programs
- src/compiler/ — lexer, parser, semantic checks, codegen, CLI (`writec`)
- src/gui/ — PySide6 GUI (`python -m gui.app`)
- scripts/ — build/packaging helpers
- tests/ — unit/integration tests

## Getting Started

1) Install deps (recommend venv):

```bash
python -m pip install -r requirements.txt
```

1) CLI transpile/compile/run:

```bash
python -m compiler.writec spec/examples/hello.write --out out.cpp
python -m compiler.writec spec/examples/hello.write --out out.cpp --compile --run
```

1) GUI:

```bash
pip install -e .

python -m gui.app
```

- Ctrl+S / Ctrl+Shift+S to save; closing dirty tabs prompts Save / Don't Save / Cancel.
- Lint shows dashed underlines and tooltips with nearby function/variable suggestions (e.g., after typing `call`).

1) Tests:

```bash
python -m pytest
```

## Roadmap

- Richer autocomplete (live symbol list, snippets) and themeable lint colors.
- "Save All", recent files, and workspace/tab restore.
- Background parse-based linting for deeper checks and hover docs.
- Packaged GUI (PyInstaller) and bundled compiler toolchain on Windows.

## License

MIT License. See LICENSE for details.
