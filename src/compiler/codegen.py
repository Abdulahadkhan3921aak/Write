"""Write-to-C++ code generation.

Emits a self-contained C++ program (int/float, iostream, cmath). No semantic/type analysis yet; assumes AST is well-formed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

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
        self._emit("#include <tuple>")
        self._emit("#include <vector>")
        self._emit("#include <sstream>")
        self._emit("using namespace std;")
        self._emit("")
        self._emit(
            "// Runtime helpers (keep small; ready for future library extraction)"
        )
        self._emit("namespace write_runtime {")
        self._push()
        self._emit("template <typename T>")
        self._emit("inline void read_value(T& v) { cin >> v; }")
        self._emit("inline void read_value(std::string& v) { getline(cin >> ws, v); }")
        self._emit("inline std::string fmt_vector(const std::vector<double>& v) {")
        self._push()
        self._emit("std::ostringstream oss;")
        self._emit("oss << '[';")
        self._emit("for (size_t i = 0; i < v.size(); ++i) {")
        self._push()
        self._emit("if (i) oss << ", ";")
        self._emit("oss << v[i];")
        self._pop()
        self._emit("}")
        self._emit("oss << ']';")
        self._emit("return oss.str();")
        self._pop()
        self._emit("}")
        self._pop()
        self._emit("} // namespace write_runtime")
        self._emit("")
        for fn in program.functions:
            self._emit_function(fn)
            self._emit("")

        self._emit("int main() {")
        self._push()
        self.env = {}
        for stmt in program.statements:
            self._stmt(stmt)
        self._emit("return 0;")
        self._pop()
        self._emit("}")
        return "\n".join(self.lines)

    # --- statements ---
    def _stmt(self, node: ast.Stmt):
        if isinstance(node, ast.Declaration):
            declared_type = node.type or "float"
            cpp_type = self._cpp_type(declared_type)
            self.env[node.name] = declared_type
            if node.type in {"list", "array"}:
                if node.size is not None:
                    size_code, _ = self._expr(node.size)
                    self._emit(f"{cpp_type} {node.name}({size_code}, 0.0);")
                else:
                    self._emit(f"{cpp_type} {node.name};")
            else:
                init_suffix = " = 0.0" if declared_type == "float" else ""
                self._emit(f"{cpp_type} {node.name}{init_suffix};")
            return
        if isinstance(node, ast.Input):
            if node.type:
                cpp_type = self._cpp_type(node.type)
                self.env[node.name] = node.type
                self._emit(f"{cpp_type} {node.name};")
            prompt = node.prompt
            self._emit_input(node.name, self.env.get(node.name), prompt)
            return
        if isinstance(node, ast.Assign):
            expr, expr_type = self._expr(node.expr)
            declared = getattr(node, "type", None)
            if node.name in self.env:
                self._emit(f"{node.name} = {expr};")
                if declared:
                    self.env[node.name] = declared
            else:
                decl_type = self._cpp_type(declared or expr_type or "auto")
                self.env[node.name] = declared or expr_type or "auto"
                self._emit(f"{decl_type} {node.name} = {expr};")
            return
        if isinstance(node, ast.IndexAssign):
            idx_code, _ = self._expr(node.index)
            expr_code, _ = self._expr(node.expr)
            self._emit(f"{node.name}[{idx_code}] = {expr_code};")
            return
        if isinstance(node, ast.Print):
            parts = []
            for v in node.values:
                code, typ = self._expr(v)
                parts.append(self._format_for_stream(code, typ))
            joined = " << ".join(parts) if parts else '""'
            self._emit(f"cout << {joined} << endl;")
            return
        if isinstance(node, ast.If):
            self._if_stmt(node)
            return
        if isinstance(node, ast.While):
            cond, _ = self._expr(node.cond)
            self._emit(f"while ({cond}) {{")
            self._push()
            for s in node.body:
                self._stmt(s)
            self._pop()
            self._emit("}")
            return
        if isinstance(node, ast.For):
            start, _ = self._expr(node.start)
            end, _ = self._expr(node.end)
            self._emit(
                f"for (auto {node.var} = {start}; {node.var} <= {end}; ++{node.var}) {{"
            )
            self._push()
            for s in node.body:
                self._stmt(s)
            self._pop()
            self._emit("}")
            return
        if isinstance(node, ast.Call):
            args_code = [self._expr(a.value)[0] for a in node.args]
            call = f"{self._func_name(node.name)}({', '.join(args_code)})"
            self._emit(call + ";")
            return
        if isinstance(node, ast.Return):
            self._emit_return(node)
            return
        raise TypeError(f"Unhandled stmt: {node}")

    def _if_stmt(self, node: ast.If):
        cond, _ = self._expr(node.first.cond)
        self._emit(f"if ({cond}) {{")
        self._push()
        for s in node.first.body:
            self._stmt(s)
        self._pop()
        self._emit("}")
        for br in node.elifs:
            cond, _ = self._expr(br.cond)
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

    def _emit_function(self, fn: ast.Function):
        fn_name = self._func_name(fn.name)
        prev_env = self.env
        self.env = {}

        param_strings: List[str] = []
        for idx, p in enumerate(fn.params):
            cpp_type = self._cpp_type(p.type or "auto")
            if p.name not in self.env:
                self.env[p.name] = p.type or "auto"
            default_src = ""
            if p.default is not None:
                default_code, _ = self._expr(p.default)
                default_src = f" = {default_code}"
            param_strings.append(f"{cpp_type} {p.name}{default_src}")

        returns_value, returns_multi = self._function_returns(fn.body)
        ret_type = "auto" if returns_value else "void"
        signature = f"{ret_type} {fn_name}({', '.join(param_strings)})"
        self._emit(signature + " {")
        self._push()
        for stmt in fn.body:
            self._stmt(stmt)
        if returns_value is False and not returns_multi:
            pass
        self._pop()
        self._emit("}")
        self.env = prev_env

    def _function_returns(self, body: List[ast.Stmt]) -> tuple[bool, bool]:
        returns_value = False
        returns_multi = False
        for stmt in body:
            if isinstance(stmt, ast.Return):
                if stmt.values:
                    returns_value = True
                    if len(stmt.values) > 1:
                        returns_multi = True
                else:
                    returns_value = False or returns_value
            elif isinstance(stmt, (ast.If, ast.While, ast.For)):
                # shallow scan nested blocks
                nested_body = []
                if isinstance(stmt, ast.If):
                    nested_body.extend(stmt.first.body)
                    for br in stmt.elifs:
                        nested_body.extend(br.body)
                    if stmt.else_body:
                        nested_body.extend(stmt.else_body)
                elif isinstance(stmt, ast.While):
                    nested_body.extend(stmt.body)
                elif isinstance(stmt, ast.For):
                    nested_body.extend(stmt.body)
                nested_ret_val, nested_multi = self._function_returns(nested_body)
                returns_value = returns_value or nested_ret_val
                returns_multi = returns_multi or nested_multi
        return returns_value, returns_multi

    # --- expressions ---
    def _expr(self, node: ast.Expr) -> Tuple[str, Optional[str]]:
        if isinstance(node, ast.Number):
            typ = "float" if "." in node.value else "int"
            return node.value, typ
        if isinstance(node, ast.String):
            return f'"{node.value}"', "string"
        if isinstance(node, ast.Var):
            return node.name, self.env.get(node.name)
        if isinstance(node, ast.Index):
            idx_code, _ = self._expr(node.index)
            return f"{node.name}[{idx_code}]", "float"
        if isinstance(node, ast.Unary):
            inner, typ = self._expr(node.right)
            op = "!" if node.op == "not" else node.op
            result_type = "bool" if op == "!" else typ
            return f"({op}{inner})", result_type
        if isinstance(node, ast.Binary):
            left_code, left_type = self._expr(node.left)
            right_code, right_type = self._expr(node.right)
            op = self._map_bin_op(node.op)
            result_type = self._binary_result_type(node.op, left_type, right_type)
            return f"({left_code} {op} {right_code})", result_type
        if isinstance(node, ast.Power):
            base_code, base_type = self._expr(node.base)
            exp_code, exp_type = self._expr(node.exponent)
            result_type: Optional[str] = None
            if base_type in {"int", "float"} and exp_type in {"int", "float"}:
                result_type = "float" if "float" in (base_type, exp_type) else "int"
            return f"pow({base_code}, {exp_code})", result_type
        raise TypeError(f"Unhandled expr: {node}")

    def _emit_return(self, node: ast.Return):
        if not node.values:
            self._emit("return;")
            return
        parts = [self._expr(v)[0] for v in node.values]
        if len(parts) == 1:
            self._emit(f"return {parts[0]};")
        else:
            joined = ", ".join(parts)
            self._emit(f"return std::make_tuple({joined});")

    def _map_bin_op(self, op: str) -> str:
        word_ops = {
            "add": "+",
            "subtract": "-",
            "multiply": "*",
            "divide": "/",
        }
        return word_ops.get(op, op)

    def _binary_result_type(
        self, op: str, left: Optional[str], right: Optional[str]
    ) -> Optional[str]:
        numeric_ops = {"+", "-", "*", "/", "add", "subtract", "multiply", "divide"}
        if op in numeric_ops:
            if "float" in (left, right):
                return "float"
            if left == "int" and right == "int":
                return "int"
            return left or right
        if op in {"==", "!=", ">", "<", ">=", "<=", "and", "or", "&", "|"}:
            return "bool"
        return None

    def _cpp_type(self, typ: str) -> str:
        return {
            "int": "int",
            "float": "float",
            "string": "string",
            "bool": "bool",
            "list": "std::vector<double>",
            "array": "std::vector<double>",
        }.get(typ, "auto")

    def _format_for_stream(self, code: str, typ: Optional[str]) -> str:
        if typ in {"list", "array"}:
            return f"write_runtime::fmt_vector({code})"
        return code

    def _emit_input(self, name: str, typ: Optional[str], prompt: Optional[str]):
        if prompt:
            self._emit(f'cout << "{prompt}"; cout.flush();')
        self._emit(f"write_runtime::read_value({name});")

    # --- helpers ---
    def _emit(self, line: str):
        self.lines.append("    " * self.indent + line)

    def _push(self):
        self.indent += 1

    def _pop(self):
        self.indent = max(0, self.indent - 1)

    def _func_name(self, raw: str) -> str:
        safe = re.sub(r"[^0-9A-Za-z_]", "_", raw)
        if safe and safe[0].isdigit():
            safe = "fn_" + safe
        return safe or "fn"


__all__ = ["Codegen"]
