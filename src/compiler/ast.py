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


# Statements
@dataclass
class Stmt(Node):
    pass


@dataclass
class Program(Node):
    statements: List[Stmt]


@dataclass
class Assign(Stmt):
    name: str
    expr: Expr


@dataclass
class Declaration(Stmt):
    name: str
    type: str


@dataclass
class Input(Stmt):
    name: str
    type: Optional[str] = None


@dataclass
class Print(Stmt):
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
    "Assign",
    "Print",
    "Declaration",
    "Input",
    "If",
    "IfBranch",
    "While",
    "For",
]
