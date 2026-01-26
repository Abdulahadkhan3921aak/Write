"""Semantic analysis for Write.

Checks:
- Undefined variables
- Simple type tagging: int, float, string, bool
- Disallow string arithmetic/power
- Basic comparison compatibility
- Block scoping per control structure
- Optional constant folding
- Decl/Input rules (no redeclare in same scope, input requires declaration unless typed)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from . import ast


class SemanticError(Exception):
    pass


@dataclass
class TypeInfo:
    name: Optional[
        str
    ]  # "int" | "float" | "string" | "bool" | "auto" | container types
    size: Optional[int] = None  # for containers with known literal size


@dataclass
class ParamInfo:
    name: str
    type: Optional[str]
    has_default: bool


@dataclass
class FunctionSig:
    name: str
    params: List[ParamInfo]


Numeric = {"int", "float"}
LogicTypes = {"int", "float", "bool"}
AllTypes = {"int", "float", "string", "bool", "list", "array"}
ContainerTypes = {"list", "array"}


class Analyzer:
    def __init__(self, source: str):
        self.env_stack: list[Dict[str, TypeInfo]] = [{}]
        self.functions: Dict[str, FunctionSig] = {}
        self.function_depth = 0
        self.source_lines = source.splitlines()

    def analyze(self, program: ast.Program) -> None:
        self._register_functions(program.functions)
        for fn in program.functions:
            self._analyze_function(fn)
        for stmt in program.statements:
            self._stmt(stmt)
        self._fold_program(program)

    # --- statements ---
    def _block(self, body: list[ast.Stmt]):
        self._push_env()
        for stmt in body:
            self._stmt(stmt)
        self._pop_env()

    def _register_functions(self, functions: List[ast.Function]):
        for fn in functions:
            if fn.name in self.functions:
                self._err(fn, f"function '{fn.name}' already defined")
            params: List[ParamInfo] = []
            seen: set[str] = set()
            for idx, p in enumerate(fn.params):
                if p.name in seen:
                    self._err(p, f"duplicate parameter '{p.name}'")
                seen.add(p.name)
                inferred_type = p.type
                if p.default is not None:
                    self._push_env()
                    for earlier in params:
                        self._env()[earlier.name] = TypeInfo(earlier.type or "auto")
                    default_type = self._expr(p.default)
                    self._pop_env()
                    if inferred_type:
                        self._ensure_assignable(p, inferred_type, default_type)
                    else:
                        inferred_type = default_type
                params.append(ParamInfo(p.name, inferred_type, p.default is not None))
                p.type = inferred_type
            self.functions[fn.name] = FunctionSig(fn.name, params)

    def _analyze_function(self, fn: ast.Function):
        sig = self.functions.get(fn.name)
        if not sig:
            return
        self._push_env()
        self.function_depth += 1
        for p in sig.params:
            self._env()[p.name] = TypeInfo(p.type or "auto")
        for stmt in fn.body:
            self._stmt(stmt)
        self.function_depth -= 1
        self._pop_env()

    def _check_call(self, node: ast.Call):
        sig = self.functions.get(node.name)
        if not sig:
            known = ", ".join(sorted(self.functions.keys())) or "none"
            self._err(node, f"undefined function '{node.name}'. known: {known}")
        provided: dict[str, str] = {}
        positional_index = 0
        for arg in node.args:
            arg_type = self._expr(arg.value)
            param = None
            if arg.name:
                for p in sig.params:
                    if p.name == arg.name:
                        param = p
                        break
                if param is None:
                    self._err(
                        arg,
                        f"unknown parameter '{arg.name}' for function '{node.name}'",
                    )
                if arg.name in provided:
                    self._err(arg, f"duplicate argument for '{arg.name}'")
            else:
                if positional_index >= len(sig.params):
                    self._err(arg, f"too many arguments for '{node.name}'")
                param = sig.params[positional_index]
                positional_index += 1
            if param.type:
                self._ensure_assignable(arg, param.type, arg_type)
            provided[param.name] = arg_type

        for p in sig.params:
            if p.name not in provided and not p.has_default:
                self._err(
                    node, f"missing argument for '{p.name}' in call to '{node.name}'"
                )

    def _stmt(self, node: ast.Stmt):
        if isinstance(node, ast.Declaration):
            if self._env().get(node.name):
                self._err(node, f"variable '{node.name}' already declared")
            if node.type and node.type not in AllTypes:
                self._err(node, f"unknown type '{node.type}'")
            literal_size = None
            if node.type in ContainerTypes and node.size is not None:
                size_type = self._expr(node.size)
                if size_type not in Numeric:
                    self._err(node, "container size must be numeric")
                literal_size = self._literal_int_value(node.size)
            self._env()[node.name] = TypeInfo(node.type or "auto", literal_size)
            return
        if isinstance(node, ast.Input):
            if node.type:
                if self._env().get(node.name):
                    self._err(node, f"variable '{node.name}' already declared")
                if node.type not in AllTypes:
                    self._err(node, f"unknown type '{node.type}'")
                self._env()[node.name] = TypeInfo(node.type)
            else:
                existing = self._lookup(node.name)
                if not existing:
                    self._err(node, f"variable '{node.name}' not declared before input")
            return
        if isinstance(node, ast.Assign):
            t = self._expr(node.expr)
            if node.type:
                if node.type not in AllTypes:
                    self._err(node, f"unknown type '{node.type}'")
                existing = self._lookup(node.name)
                if existing and existing.name not in {None, "auto", node.type}:
                    self._ensure_assignable(node, existing.name, node.type)
                self._ensure_assignable(node, node.type, t)
                self._env()[node.name] = TypeInfo(node.type)
            else:
                existing = self._lookup(node.name)
                if existing:
                    self._ensure_assignable(node, existing.name, t)
                    self._env()[node.name] = existing  # ensure current scope sees it
                else:
                    self._env()[node.name] = TypeInfo(t)
            return
        if isinstance(node, ast.IndexAssign):
            base = self._lookup(node.name)
            if not base:
                self._err(node, f"variable '{node.name}' not declared")
            if base.name not in ContainerTypes:
                self._err(node, f"indexing requires list/array (got {base.name})")
            idx_type = self._expr(node.index)
            if idx_type not in Numeric:
                self._err(node, "index must be numeric")
            idx_literal = self._literal_int_value(node.index)
            if base.size is not None and idx_literal is not None:
                if idx_literal < 0 or idx_literal >= base.size:
                    self._err(
                        node,
                        f"index {idx_literal} out of bounds for '{node.name}' of size {base.size}",
                    )
            val_type = self._expr(node.expr)
            if val_type not in Numeric:
                self._err(node, "container elements must be numeric")
            return
        if isinstance(node, ast.Print):
            for value in node.values:
                self._expr(value)
            return
        if isinstance(node, ast.If):
            self._expr(node.first.cond)
            self._block(node.first.body)
            for br in node.elifs:
                self._expr(br.cond)
                self._block(br.body)
            if node.else_body:
                self._block(node.else_body)
            return
        if isinstance(node, ast.While):
            self._expr(node.cond)
            self._block(node.body)
            return
        if isinstance(node, ast.For):
            start_t = self._expr(node.start)
            end_t = self._expr(node.end)
            if start_t not in Numeric or end_t not in Numeric:
                self._err(node, f"for bounds must be numeric (got {start_t}, {end_t})")
            self._push_env()
            self._env()[node.var] = TypeInfo("int")
            for s in node.body:
                self._stmt(s)
            self._pop_env()
            return
        if isinstance(node, ast.Call):
            self._check_call(node)
            return
        if isinstance(node, ast.Return):
            if self.function_depth <= 0:
                self._err(node, "'return' outside function")
            for v in node.values:
                self._expr(v)
            return
        self._err(node, f"Unhandled statement {node}")

    # --- expressions ---
    def _expr(self, node: ast.Expr) -> str:
        if isinstance(node, ast.Number):
            return "float" if self._is_float_literal(node.value) else "int"
        if isinstance(node, ast.String):
            return "string"
        if isinstance(node, ast.Var):
            t = self._lookup(node.name)
            if not t:
                self._err(node, f"undefined variable '{node.name}'")
            return t.name or "auto"
        if isinstance(node, ast.Index):
            base = self._lookup(node.name)
            if not base:
                self._err(node, f"variable '{node.name}' not declared")
            if base.name not in ContainerTypes:
                self._err(node, f"indexing requires list/array (got {base.name})")
            idx_type = self._expr(node.index)
            if idx_type not in Numeric:
                self._err(node, "index must be numeric")
            idx_literal = self._literal_int_value(node.index)
            if base.size is not None and idx_literal is not None:
                if idx_literal < 0 or idx_literal >= base.size:
                    self._err(
                        node,
                        f"index {idx_literal} out of bounds for '{node.name}' of size {base.size}",
                    )
            return "float"
        if isinstance(node, ast.Unary):
            op = node.op
            t = self._expr(node.right)
            if op in {"+", "-"}:
                if not self._is_numeric(t):
                    self._err(node, f"unary {op} requires numeric operand (got {t})")
                return t
            if op in {"!", "not"}:
                if not self._is_logic(t):
                    self._err(
                        node,
                        f"unary {op} requires numeric/bool-like operand (got {t})",
                    )
                return "bool"
            self._err(node, f"unhandled unary op {op}")
        if isinstance(node, ast.Binary):
            lt = self._expr(node.left)
            rt = self._expr(node.right)
            op = node.op
            if op in {"+", "-", "*", "/", "add", "subtract", "multiply", "divide"}:
                if not self._is_numeric(lt) or not self._is_numeric(rt):
                    self._err(
                        node,
                        f"arithmetic '{op}' requires numeric operands (got {lt}, {rt})",
                    )
                return "float" if "float" in (lt, rt) else lt or rt or "int"
            if op in {"==", "!="}:
                if lt == rt:
                    return "bool"
                if self._is_numeric(lt) and self._is_numeric(rt):
                    return "bool"
                self._err(node, f"incompatible types for equality: {lt} vs {rt}")
            if op in {">", "<", ">=", "<="}:
                if self._is_numeric(lt) and self._is_numeric(rt):
                    return "bool"
                self._err(
                    node,
                    f"ordering comparison requires numeric operands (got {lt}, {rt})",
                )
            if op in {"and", "&", "or", "|"}:
                if not self._is_logic(lt) or not self._is_logic(rt):
                    self._err(
                        node,
                        f"logical '{op}' requires numeric/bool-like operands (got {lt}, {rt})",
                    )
                return "bool"
            self._err(node, f"unhandled binary op {op}")
        if isinstance(node, ast.Power):
            bt = self._expr(node.base)
            et = self._expr(node.exponent)
            if not self._is_numeric(bt) or not self._is_numeric(et):
                self._err(node, f"power requires numeric operands (got {bt}, {et})")
            return "float" if "float" in (bt, et) else "int"
        self._err(node, f"Unhandled expr {node}")

    # --- env helpers ---
    def _env(self) -> Dict[str, TypeInfo]:
        return self.env_stack[-1]

    def _push_env(self):
        self.env_stack.append({})

    def _pop_env(self):
        if len(self.env_stack) > 1:
            self.env_stack.pop()

    def _lookup(self, name: str) -> Optional[TypeInfo]:
        for env in reversed(self.env_stack):
            if name in env:
                return env[name]
        return None

    def _ensure_assignable(self, node: ast.Node, target_type: str, expr_type: str):
        if target_type in {None, "auto"}:
            return
        if expr_type in {None, "auto"}:
            return
        if target_type == expr_type:
            return
        if target_type == "float" and expr_type in {"int", "float"}:
            return
        if target_type in Numeric and expr_type in Numeric:
            return
        self._err(node, f"cannot assign {expr_type} to {target_type}")

    # --- folding ---
    def _fold_program(self, program: ast.Program) -> None:
        program.functions = [self._fold_function(fn) for fn in program.functions]
        program.statements = [self._fold_stmt(s) for s in program.statements]

    def _fold_stmt(self, stmt: ast.Stmt) -> ast.Stmt:
        if isinstance(stmt, ast.Assign):
            stmt.expr = self._fold_expr(stmt.expr)
        elif isinstance(stmt, ast.Print):
            stmt.values = [self._fold_expr(v) for v in stmt.values]
        elif isinstance(stmt, ast.Call):
            stmt.args = [
                ast.Arg(
                    name=a.name, value=self._fold_expr(a.value), line=a.line, col=a.col
                )
                for a in stmt.args
            ]
        elif isinstance(stmt, ast.If):
            stmt.first.cond = self._fold_expr(stmt.first.cond)
            stmt.first.body = [self._fold_stmt(s) for s in stmt.first.body]
            stmt.elifs = [
                ast.IfBranch(
                    cond=self._fold_expr(br.cond),
                    body=[self._fold_stmt(s) for s in br.body],
                    line=br.line,
                    col=br.col,
                )
                for br in stmt.elifs
            ]
            if stmt.else_body:
                stmt.else_body = [self._fold_stmt(s) for s in stmt.else_body]
        elif isinstance(stmt, ast.While):
            stmt.cond = self._fold_expr(stmt.cond)
            stmt.body = [self._fold_stmt(s) for s in stmt.body]
        elif isinstance(stmt, ast.For):
            stmt.start = self._fold_expr(stmt.start)
            stmt.end = self._fold_expr(stmt.end)
            stmt.body = [self._fold_stmt(s) for s in stmt.body]
        return stmt

    def _fold_function(self, fn: ast.Function) -> ast.Function:
        fn.params = [fn_param for fn_param in fn.params]
        fn.body = [self._fold_stmt(s) for s in fn.body]
        return fn

    def _fold_expr(self, expr: ast.Expr) -> ast.Expr:
        if isinstance(expr, ast.Binary):
            expr.left = self._fold_expr(expr.left)
            expr.right = self._fold_expr(expr.right)
            if isinstance(expr.left, ast.Number) and isinstance(expr.right, ast.Number):
                try:
                    val = self._eval_binary(expr.op, expr.left.value, expr.right.value)
                    return ast.Number(val, line=expr.line, col=expr.col)
                except Exception:
                    return expr
        elif isinstance(expr, ast.Unary):
            expr.right = self._fold_expr(expr.right)
            if isinstance(expr.right, ast.Number) and expr.op in {"+", "-"}:
                try:
                    num = float(expr.right.value)
                    val = num if expr.op == "+" else -num
                    return ast.Number(
                        self._num_to_lex(val), line=expr.line, col=expr.col
                    )
                except Exception:
                    return expr
        elif isinstance(expr, ast.Power):
            expr.base = self._fold_expr(expr.base)
            expr.exponent = self._fold_expr(expr.exponent)
            if isinstance(expr.base, ast.Number) and isinstance(
                expr.exponent, ast.Number
            ):
                try:
                    val = float(expr.base.value) ** float(expr.exponent.value)
                    return ast.Number(
                        self._num_to_lex(val), line=expr.line, col=expr.col
                    )
                except Exception:
                    return expr
        return expr

    def _eval_binary(self, op: str, l: str, r: str) -> str:
        lf = float(l)
        rf = float(r)
        if op in {"+", "add"}:
            return self._num_to_lex(lf + rf)
        if op in {"-", "subtract"}:
            return self._num_to_lex(lf - rf)
        if op in {"*", "multiply"}:
            return self._num_to_lex(lf * rf)
        if op in {"/", "divide"}:
            return self._num_to_lex(lf / rf)
        raise ValueError(f"unsupported op {op}")

    def _num_to_lex(self, val: float) -> str:
        if val.is_integer():
            return str(int(val))
        return str(val)

    def _literal_int_value(self, expr: ast.Expr) -> Optional[int]:
        if isinstance(expr, ast.Number) and not self._is_float_literal(expr.value):
            try:
                return int(expr.value)
            except ValueError:
                return None
        return None

    # --- error reporting ---
    def _err(self, node: ast.Node, msg: str):
        line = getattr(node, "line", None)
        col = getattr(node, "col", None)
        if line and 1 <= line <= len(self.source_lines):
            src_line = self.source_lines[line - 1]
            caret = " " * (col - 1 if col and col > 0 else 0) + "^"
            raise SemanticError(f"{msg} at {line}:{col}\n    {src_line}\n    {caret}")
        raise SemanticError(msg)

    # --- helpers ---
    def _is_float_literal(self, lexeme: str) -> bool:
        return "." in lexeme

    def _is_numeric(self, typ: Optional[str]) -> bool:
        return typ in Numeric or typ in {"auto", None}

    def _is_logic(self, typ: Optional[str]) -> bool:
        return typ in LogicTypes or typ in {"auto", None}


__all__ = ["Analyzer", "SemanticError", "TypeInfo"]
