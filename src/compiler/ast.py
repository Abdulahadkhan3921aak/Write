"""AST node definitions for the Write language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union


# Base node for location info
@dataclass(kw_only=True)
class Node:
    line: Optional[int] = None
    col: Optional[int] = None


# Expressions
@dataclass
class Expr(Node):
    pass


@dataclass
class Number(Expr):
    value: str  # keep raw lexeme; convert later if needed


@dataclass
class String(Expr):
    value: str


@dataclass
class Var(Expr):
    name: str


@dataclass
class Unary(Expr):
    op: str
    right: Expr


@dataclass
class Binary(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass
class Power(Expr):
    base: Expr
    exponent: Expr


@dataclass
class Index(Expr):
    name: str
    index: Expr


@dataclass
class Stmt(Node):
    pass


@dataclass
class Program(Node):
    functions: List["Function"]
    statements: List[Stmt]


@dataclass
class Assign(Stmt):
    name: str
    expr: Expr
    type: Optional[str] = None


@dataclass
class IndexAssign(Stmt):
    name: str
    index: Expr
    expr: Expr


@dataclass
class Declaration(Stmt):
    name: str
    type: Optional[str] = None
    size: Optional[Expr] = None


@dataclass
class Input(Stmt):
    name: str
    type: Optional[str] = None
    prompt: Optional[str] = None


@dataclass
class Print(Stmt):
    values: List[Expr]


@dataclass
class Return(Stmt):
    values: List[Expr]


@dataclass
class IfBranch(Node):
    cond: Expr
    body: List[Stmt]


@dataclass
class If(Stmt):
    first: IfBranch
    elifs: List[IfBranch]
    else_body: Optional[List[Stmt]]


@dataclass
class While(Stmt):
    cond: Expr
    body: List[Stmt]


@dataclass
class For(Stmt):
    var: str
    start: Expr
    end: Expr
    body: List[Stmt]


# Functions
@dataclass
class Param(Node):
    name: str
    type: Optional[str] = None
    default: Optional[Expr] = None


@dataclass
class Arg(Node):
    name: Optional[str]
    value: Expr


@dataclass
class Call(Stmt):
    name: str
    args: List[Arg]


@dataclass
class Function(Node):
    name: str
    params: List[Param]
    body: List[Stmt]


__all__ = [
    "Expr",
    "Stmt",
    "Program",
    "Number",
    "String",
    "Var",
    "Unary",
    "Binary",
    "Power",
    "Index",
    "Assign",
    "IndexAssign",
    "Print",
    "Declaration",
    "Input",
    "If",
    "IfBranch",
    "While",
    "For",
    "Param",
    "Arg",
    "Call",
    "Function",
    "Return",
]
