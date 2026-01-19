"""Write-to-C++ code generation.

Emits a self-contained C++ program (int/float, iostream, cmath). No semantic/type analysis yet; assumes AST is well-formed.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from . import ast


class Codegen:
    def __init__(self):
        self.lines: List[str] = []
        self.indent = 0
        self.env: Dict[str, str] = {}

    def generate(self, program: ast.Program) -> str:
        self.lines = []
        self.indent = 0
        self.env = {}
        self._emit("#include <iostream>")
        self._emit("#include <cmath>")
        self._emit("#include <string>")
        self._emit("using namespace std;")
        self._emit("")
        self._emit("int main() {")
        self._push()
        for stmt in program.statements:
            self._stmt(stmt)
        self._emit("return 0;")
        self._pop()
        self._emit("}")
        return "\n".join(self.lines)

    # --- statements ---
    def _stmt(self, node: ast.Stmt):
        if isinstance(node, ast.Declaration):
            cpp_type = self._cpp_type(node.type)
            self.env[node.name] = node.type
            self._emit(f"{cpp_type} {node.name};")
            return
        if isinstance(node, ast.Input):
            if node.type:
                cpp_type = self._cpp_type(node.type)
                self.env[node.name] = node.type
                self._emit(f"{cpp_type} {node.name};")
            self._emit_input(node.name, self.env.get(node.name))
            return
        if isinstance(node, ast.Assign):
            expr = self._expr(node.expr)
            if node.name in self.env:
                self._emit(f"{node.name} = {expr};")
            else:
                self.env[node.name] = "auto"
                self._emit(f"auto {node.name} = {expr};")
            return
        if isinstance(node, ast.Print):
            parts = [self._expr(v) for v in node.values]
            joined = " << ".join(parts) if parts else '""'
            self._emit(f"cout << {joined} << endl;")
            return
        if isinstance(node, ast.If):
            self._if_stmt(node)
            return
        if isinstance(node, ast.While):
            cond = self._expr(node.cond)
            self._emit(f"while ({cond}) {{")
            self._push()
            for s in node.body:
                self._stmt(s)
            self._pop()
            self._emit("}")
            return
        if isinstance(node, ast.For):
            start = self._expr(node.start)
            end = self._expr(node.end)
            self._emit(
                f"for (auto {node.var} = {start}; {node.var} <= {end}; ++{node.var}) {{"
            )
            self._push()
            for s in node.body:
                self._stmt(s)
            self._pop()
            self._emit("}")
            return
        raise TypeError(f"Unhandled stmt: {node}")

    def _if_stmt(self, node: ast.If):
        cond = self._expr(node.first.cond)
        self._emit(f"if ({cond}) {{")
        self._push()
        for s in node.first.body:
            self._stmt(s)
        self._pop()
        self._emit("}")
        for br in node.elifs:
            cond = self._expr(br.cond)
            self._emit(f"else if ({cond}) {{")
            self._push()
            for s in br.body:
                self._stmt(s)
            self._pop()
            self._emit("}")
        if node.else_body is not None:
            self._emit("else {")
            self._push()
            for s in node.else_body:
                self._stmt(s)
            self._pop()
            self._emit("}")

    # --- expressions ---
    def _expr(self, node: ast.Expr) -> str:
        if isinstance(node, ast.Number):
            return node.value
        if isinstance(node, ast.String):
            return f'"{node.value}"'
        if isinstance(node, ast.Var):
            return node.name
        if isinstance(node, ast.Unary):
            return f"({node.op}{self._expr(node.right)})"
        if isinstance(node, ast.Binary):
            op = self._map_bin_op(node.op)
            return f"({self._expr(node.left)} {op} {self._expr(node.right)})"
        if isinstance(node, ast.Power):
            return f"pow({self._expr(node.base)}, {self._expr(node.exponent)})"
        raise TypeError(f"Unhandled expr: {node}")

    def _map_bin_op(self, op: str) -> str:
        word_ops = {
            "add": "+",
            "subtract": "-",
            "multiply": "*",
            "divide": "/",
        }
        return word_ops.get(op, op)

    def _cpp_type(self, typ: str) -> str:
        return {
            "int": "int",
            "float": "float",
            "string": "string",
            "bool": "bool",
        }.get(typ, "auto")

    def _emit_input(self, name: str, typ: Optional[str]):
        # Simple extraction; for strings we accept cin >> name to keep scope small.
        self._emit(f"cin >> {name};")

    # --- helpers ---
    def _emit(self, line: str):
        self.lines.append("    " * self.indent + line)

    def _push(self):
        self.indent += 1

    def _pop(self):
        self.indent = max(0, self.indent - 1)


__all__ = ["Codegen"]
