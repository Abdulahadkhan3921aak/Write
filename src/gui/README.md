# GUI skeleton

Goal: beginner-friendly desktop GUI to edit Write programs, transpile to C/C++, and run.

Implemented scaffold (PySide6):

- Editor pane (left), C++ output pane (top-right), log pane (bottom-right)
- Buttons: Open, Save, Save As, Transpile, Compile, Run (Ctrl+S / Ctrl+Shift+S shortcuts)
- Samples menu loads spec/examples/*.write
- Syntax highlighting for keywords/numbers/strings/comments
- Uses compiler.writec via subprocess (so semantics/codegen stay single-source)
- Unsaved tabs prompt: closing a dirty tab or quitting asks Save / Don’t Save / Cancel, with tab label `*` for unsaved changes
- Lightweight lint tab + inline highlights: fast heuristic hints (function/end balance, argument colons, call syntax, trailing spaces, list size) with debounce, size guard, and line-highlighting in the editor

Run locally (needs PySide6 installed in env):

```
python -m gui.app
```

Packaging: PyInstaller for Windows EXE; optionally bundle a lightweight compiler toolchain (MinGW/Clang) or require a preinstalled compiler.
