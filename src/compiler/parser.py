"""Recursive-descent parser for the Write language."""

from __future__ import annotations

from typing import List

from . import lexer
from .ast import (
    Assign,
    Binary,
    Declaration,
    Expr,
    For,
    If,
    IfBranch,
    Input,
    Number,
    Power,
    Print,
    Program,
    Stmt,
    String,
    Unary,
    Var,
    While,
)


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[lexer.Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Program:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            stmts.append(self._statement())
        first_line = stmts[0].line if stmts else None
        first_col = stmts[0].col if stmts else None
        return Program(statements=stmts, line=first_line, col=first_col)

    # --- statements ---
    def _statement(self) -> Stmt:
        if self._match_kw("make"):
            name_tok = self._consume_ident("Expected identifier after 'make'")
            self._consume_kw("as", "Expected 'as' in declaration")
            typ = self._type_name()
            return Declaration(
                name=name_tok.lexeme, type=typ, line=name_tok.line, col=name_tok.col
            )
        if self._match_kw("input"):
            name_tok = self._consume_ident("Expected identifier after 'input'")
            typ = None
            if self._match_kw("as"):
                typ = self._type_name()
            return Input(
                name=name_tok.lexeme, type=typ, line=name_tok.line, col=name_tok.col
            )
        if self._match_kw("set"):
            name_tok = self._consume_ident("Expected identifier after 'set'")
            self._consume_kw("to", "Expected 'to' in assignment")
            expr = self._expression()
            return Assign(
                name=name_tok.lexeme, expr=expr, line=name_tok.line, col=name_tok.col
            )
        if self._match_kw("print"):
            first_expr = self._expression()
            values = [first_expr]
            while self._match_op(lexer.TokenKind.COMMA):
                values.append(self._expression())
            first_line = getattr(first_expr, "line", None)
            first_col = getattr(first_expr, "col", None)
            return Print(values=values, line=first_line, col=first_col)
        if self._match_kw("if"):
            return self._if_statement()
        if self._match_kw("while"):
            cond = self._condition()
            self._consume_kw("do", "Expected 'do' after while condition")
            body = self._block_until_end("while")
            return While(cond=cond, body=body, line=cond.line, col=cond.col)
        if self._match_kw("for"):
            var_tok = self._consume_ident("Expected loop variable after 'for'")
            self._consume_kw("from", "Expected 'from' in for loop")
            start = self._expression()
            self._consume_kw("to", "Expected 'to' in for loop")
            end = self._expression()
            self._consume_kw("do", "Expected 'do' after for header")
            body = self._block_until_end("for")
            return For(
                var=var_tok.lexeme,
                start=start,
                end=end,
                body=body,
                line=var_tok.line,
                col=var_tok.col,
            )
        tok = self._peek()
        raise ParseError(f"Unexpected token {tok.lexeme} at {tok.line}:{tok.col}")

    def _if_statement(self) -> If:
        cond = self._condition()
        self._consume_kw("then", "Expected 'then' after if condition")
        first_body = self._block_until_else_or_end()
        first_branch = IfBranch(
            cond=cond, body=first_body, line=cond.line, col=cond.col
        )

        elifs: List[IfBranch] = []
        else_body = None
        while self._match_kw("else") and self._match_kw("if"):
            cond = self._condition()
            self._consume_kw("then", "Expected 'then' after else if condition")
            body = self._block_until_else_or_end()
            elifs.append(IfBranch(cond=cond, body=body, line=cond.line, col=cond.col))

        if self._previous_two_keywords_were_else_if():
            pass
        elif self._previous_is_kw("else"):
            else_body = self._block_until_end_if()

        if else_body is None and self._match_kw("else"):
            else_body = self._block_until_end_if()

        self._consume_pair_end("if")
        return If(
            first=first_branch,
            elifs=elifs,
            else_body=else_body,
            line=first_branch.line,
            col=first_branch.col,
        )

    def _block_until_else_or_end(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            if self._check_kw("else") or self._check_pair_end("if"):
                break
            stmts.append(self._statement())
        return stmts

    def _block_until_end_if(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            if self._check_pair_end("if"):
                break
            stmts.append(self._statement())
        return stmts

    def _block_until_end(self, kind: str) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_at_end():
            if self._check_pair_end(kind):
                break
            stmts.append(self._statement())
        self._consume_pair_end(kind)
        return stmts

    # --- conditions ---
    def _condition(self) -> Expr:
        return self._cond_or()

    def _cond_or(self) -> Expr:
        expr = self._cond_and()
        while self._match_kw("or") or self._match_op(lexer.TokenKind.PIPE):
            op_tok = self._previous()
            right = self._cond_and()
            expr = Binary(expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col)
        return expr

    def _cond_and(self) -> Expr:
        expr = self._cond_not()
        while self._match_kw("and") or self._match_op(lexer.TokenKind.AMP):
            op_tok = self._previous()
            right = self._cond_not()
            expr = Binary(expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col)
        return expr

    def _cond_not(self) -> Expr:
        if self._match_kw("not") or self._match_op(lexer.TokenKind.BANG):
            op_tok = self._previous()
            right = self._cond_not()
            return Unary(op_tok.lexeme, right, line=op_tok.line, col=op_tok.col)
        return self._cond_cmp()

    def _cond_cmp(self) -> Expr:
        if self._match_op(lexer.TokenKind.LPAREN):
            expr = self._condition()
            self._consume(lexer.TokenKind.RPAREN, "Expected ')' after condition")
            return expr
        left = self._expression()
        op = self._comparison_op()
        right = self._expression()
        return Binary(left, op, right, line=left.line, col=left.col)

    def _comparison_op(self) -> str:
        if self._match_op(lexer.TokenKind.EQEQ):
            return "=="
        if self._match_op(lexer.TokenKind.NEQ):
            return "!="
        if self._match_op(lexer.TokenKind.GTE):
            return ">="
        if self._match_op(lexer.TokenKind.LTE):
            return "<="
        if self._match_op(lexer.TokenKind.GT):
            return ">"
        if self._match_op(lexer.TokenKind.LT):
            return "<"
        if self._match_kw("is"):
            if self._match_kw("equal") and self._match_kw("to"):
                return "=="
            if (
                self._match_kw("not")
                and self._match_kw("equal")
                and self._match_kw("to")
            ):
                return "!="
            if self._match_kw("greater") and self._match_kw("than"):
                return ">"
            if self._match_kw("less") and self._match_kw("than"):
                return "<"
            if (
                self._match_kw("greater")
                and self._match_kw("or")
                and self._match_kw("equal")
                and self._match_kw("to")
            ):
                return ">="
            if (
                self._match_kw("less")
                and self._match_kw("or")
                and self._match_kw("equal")
                and self._match_kw("to")
            ):
                return "<="
        tok = self._peek()
        raise ParseError(f"Expected comparison operator at {tok.line}:{tok.col}")

    # --- expressions ---
    def _expression(self) -> Expr:
        return self._add_expr()

    def _add_expr(self) -> Expr:
        expr = self._mul_expr()
        while True:
            if self._match_op(lexer.TokenKind.PLUS) or self._match_kw("add"):
                op_tok = self._previous()
                right = self._mul_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            elif self._match_op(lexer.TokenKind.MINUS) or self._match_kw("subtract"):
                op_tok = self._previous()
                right = self._mul_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            else:
                break
        return expr

    def _mul_expr(self) -> Expr:
        expr = self._power_expr()
        while True:
            if self._match_op(lexer.TokenKind.STAR) or self._match_kw("multiply"):
                op_tok = self._previous()
                right = self._power_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            elif self._match_op(lexer.TokenKind.SLASH) or self._match_kw("divide"):
                op_tok = self._previous()
                right = self._power_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            else:
                break
        return expr

    def _power_expr(self) -> Expr:
        base = self._unary_expr()
        if self._match_op(lexer.TokenKind.CARET):
            op_tok = self._previous()
            exponent = self._power_expr()
            return Power(base=base, exponent=exponent, line=op_tok.line, col=op_tok.col)
        return base

    def _unary_expr(self) -> Expr:
        if self._match_op(lexer.TokenKind.PLUS):
            op_tok = self._previous()
            return Unary("+", self._unary_expr(), line=op_tok.line, col=op_tok.col)
        if self._match_op(lexer.TokenKind.MINUS):
            op_tok = self._previous()
            return Unary("-", self._unary_expr(), line=op_tok.line, col=op_tok.col)
        return self._primary()

    def _primary(self) -> Expr:
        if self._match_kw("add"):
            op_tok = self._previous()
            left = self._unary_expr()
            self._consume_kw("and", "Expected 'and' after left operand")
            right = self._unary_expr()
            return Binary(left, "add", right, line=op_tok.line, col=op_tok.col)
        if self._match_kw("subtract"):
            op_tok = self._previous()
            left = self._unary_expr()
            self._consume_kw("and", "Expected 'and' after left operand")
            right = self._unary_expr()
            return Binary(left, "subtract", right, line=op_tok.line, col=op_tok.col)
        if self._match_kw("multiply"):
            op_tok = self._previous()
            left = self._unary_expr()
            self._consume_kw("and", "Expected 'and' after left operand")
            right = self._unary_expr()
            return Binary(left, "multiply", right, line=op_tok.line, col=op_tok.col)
        if self._match_kw("divide"):
            op_tok = self._previous()
            left = self._unary_expr()
            self._consume_kw("and", "Expected 'and' after left operand")
            right = self._unary_expr()
            return Binary(left, "divide", right, line=op_tok.line, col=op_tok.col)
        if self._match_kw("power"):
            op_tok = self._previous()
            base = self._unary_expr()
            self._consume_kw("and", "Expected 'and' after base")
            exponent = self._unary_expr()
            return Power(base=base, exponent=exponent, line=op_tok.line, col=op_tok.col)
        if self._match_kind(lexer.TokenKind.NUMBER):
            tok = self._previous()
            return Number(tok.lexeme, line=tok.line, col=tok.col)
        if self._match_kind(lexer.TokenKind.STRING):
            tok = self._previous()
            return String(tok.lexeme, line=tok.line, col=tok.col)
        if self._match_kind(lexer.TokenKind.IDENT):
            tok = self._previous()
            return Var(tok.lexeme, line=tok.line, col=tok.col)
        if self._match_op(lexer.TokenKind.LPAREN):
            expr = self._expression()
            self._consume(lexer.TokenKind.RPAREN, "Expected ')' after expression")
            return expr
        tok = self._peek()
        raise ParseError(f"Expected expression at {tok.line}:{tok.col}")

    # --- helpers ---
    def _match_kw(self, kw: str) -> bool:
        if self._check_kw(kw):
            self._advance()
            return True
        return False

    def _match_op(self, kind: lexer.TokenKind) -> bool:
        if self._check_kind(kind):
            self._advance()
            return True
        return False

    def _match_kind(self, kind: lexer.TokenKind) -> bool:
        if self._check_kind(kind):
            self._advance()
            return True
        return False

    def _consume_kw(self, kw: str, msg: str):
        if self._match_kw(kw):
            return
        raise ParseError(msg)

    def _type_name(self) -> str:
        for t in ("int", "float", "string", "bool"):
            if self._match_kw(t):
                return t
        tok = self._peek()
        raise ParseError(f"Expected type at {tok.line}:{tok.col}")

    def _consume(self, kind: lexer.TokenKind, msg: str):
        if self._check_kind(kind):
            self._advance()
            return
        raise ParseError(msg)

    def _consume_ident(self, msg: str):
        if self._check_kind(lexer.TokenKind.IDENT):
            return self._advance()
        raise ParseError(msg)

    def _check_kw(self, kw: str) -> bool:
        if self._is_at_end():
            return False
        t = self._peek()
        return t.kind == lexer.TokenKind.KEYWORD and t.lexeme == kw

    def _check_kind(self, kind: lexer.TokenKind) -> bool:
        if self._is_at_end():
            return False
        return self._peek().kind == kind

    def _check_pair_end(self, kind: str | None = None) -> bool:
        if not self._check_kw("end"):
            return False
        if kind is None:
            return True
        if self.current + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.current + 1]
        return nxt.kind == lexer.TokenKind.KEYWORD and nxt.lexeme == kind

    def _consume_pair_end(self, kind: str):
        self._consume_kw("end", f"Expected 'end' to close {kind}")
        self._consume_kw(kind, f"Expected '{kind}' after end")

    def _previous_is_kw(self, kw: str) -> bool:
        if self.current == 0:
            return False
        t = self.tokens[self.current - 1]
        return t.kind == lexer.TokenKind.KEYWORD and t.lexeme == kw

    def _previous_two_keywords_were_else_if(self) -> bool:
        if self.current < 2:
            return False
        t1 = self.tokens[self.current - 2]
        t2 = self.tokens[self.current - 1]
        return (
            t1.kind == lexer.TokenKind.KEYWORD
            and t2.kind == lexer.TokenKind.KEYWORD
            and t1.lexeme == "else"
            and t2.lexeme == "if"
        )

    def _advance(self) -> lexer.Token:
        if not self._is_at_end():
            self.current += 1
        return self.tokens[self.current - 1]

    def _peek(self) -> lexer.Token:
        return self.tokens[self.current]

    def _previous(self) -> lexer.Token:
        return self.tokens[self.current - 1]

    def _is_at_end(self) -> bool:
        return self._peek().kind == lexer.TokenKind.EOF


__all__ = ["Parser", "ParseError"]
