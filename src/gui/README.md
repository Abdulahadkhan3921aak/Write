# GUI skeleton

Goal: beginner-friendly desktop GUI to edit Write programs, transpile to C/C++, and run.

Implemented scaffold (PySide6):

- Editor pane (left), C++ output pane (top-right), log pane (bottom-right)
- Buttons: Open, Save As, Transpile, Compile, Run
- Samples menu loads spec/examples/*.write
- Syntax highlighting for keywords/numbers/strings/comments
- Uses compiler.writec via subprocess (so semantics/codegen stay single-source)

Run locally (needs PySide6 installed in env):

```
python -m gui.app
```

Packaging: PyInstaller for Windows EXE; optionally bundle a lightweight compiler toolchain (MinGW/Clang) or require a preinstalled compiler.
