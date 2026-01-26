"""Recursive-descent parser for the Write language."""

from __future__ import annotations

from typing import List

from . import lexer
from .ast import (
    Arg,
    Assign,
    Binary,
    Call,
    Declaration,
    Expr,
    Index,
    IndexAssign,
    For,
    Function,
    If,
    IfBranch,
    Input,
    Number,
    Param,
    Power,
    Print,
    Program,
    Return,
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
        functions: List[Function] = []
        stmts: List[Stmt] = []
        while not self._is_at_end():
            if self._check_kw("function") or self._check_kw("func"):
                functions.append(self._function_def())
                continue
            stmts.append(self._statement())
        first_node = None
        if functions:
            first_node = functions[0]
        if stmts:
            first_node = first_node or stmts[0]
        first_line = getattr(first_node, "line", None) if first_node else None
        first_col = getattr(first_node, "col", None) if first_node else None
        return Program(
            functions=functions, statements=stmts, line=first_line, col=first_col
        )

    # --- statements ---
    def _statement(self) -> Stmt:
        if self._match_kw("add"):
            return self._inplace_update("add")
        if self._match_kw("sub") or self._match_kw("subtract"):
            return self._inplace_update("sub")
        if self._match_kw("make"):
            name_tok = self._consume_ident("Expected identifier after 'make'")
            typ = None
            size_expr = None
            if self._match_kw("as"):
                typ = self._type_name()
                if typ in {"list", "array"} and self._match_kw("of"):
                    self._consume_kw("size", "Expected 'size' after 'of'")
                    size_expr = self._expression()
            return Declaration(
                name=name_tok.lexeme,
                type=typ,
                size=size_expr,
                line=name_tok.line,
                col=name_tok.col,
            )
        if self._match_kw("call"):
            return self._call_statement()
        if self._match_kw("return"):
            return self._return_statement()
        if self._match_kw("input"):
            prompt = None
            if self._check_kind(lexer.TokenKind.STRING):
                prompt_tok = self._advance()
                prompt = prompt_tok.lexeme
            name_tok = self._consume_ident("Expected identifier after 'input'")
            typ = None
            if self._match_kw("as"):
                typ = self._type_name()
            return Input(
                name=name_tok.lexeme,
                type=typ,
                prompt=prompt,
                line=name_tok.line,
                col=name_tok.col,
            )
        if self._match_kw("set"):
            if self._check_kw("return"):
                ret_kw = self._advance()
                self._consume_kw("to", "Expected 'to' after 'set return'")
                return self._return_statement(ret_kw)
            name_tok = self._consume_ident("Expected identifier after 'set'")
            idx_expr = None
            if self._match_op(lexer.TokenKind.LBRACKET):
                idx_expr = self._expression()
                self._consume(lexer.TokenKind.RBRACKET, "Expected ']' after index")
            var_type = None
            if idx_expr is None and self._match_op(lexer.TokenKind.COLON):
                var_type = self._type_name()
            self._consume_kw("to", "Expected 'to' in assignment")
            expr = self._assignment_rhs(name_tok)
            if idx_expr is not None:
                return IndexAssign(
                    name=name_tok.lexeme,
                    index=idx_expr,
                    expr=expr,
                    line=name_tok.line,
                    col=name_tok.col,
                )
            return Assign(
                name=name_tok.lexeme,
                expr=expr,
                type=var_type,
                line=name_tok.line,
                col=name_tok.col,
            )
        if self._match_kw("print"):
            first_expr = self._expression()
            values = [first_expr]
            while True:
                if self._match_op(lexer.TokenKind.COMMA):
                    values.append(self._expression())
                    continue
                if self._is_expr_start():
                    values.append(self._expression())
                    continue
                break
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

    def _function_def(self) -> Function:
        start_kw = "function" if self._match_kw("function") else "func"
        name_tok = self._consume_function_name()
        # Support both legacy "arguments:" and simplified signature directly.
        if self._match_kw("arguments") or self._match_kw("aguments"):
            self._match_op(lexer.TokenKind.COLON)
        self._consume(lexer.TokenKind.LPAREN, "Expected '(' after function name")
        params: List[Param] = []
        if not self._check_kind(lexer.TokenKind.RPAREN):
            while True:
                params.append(self._param_decl())
                if self._match_op(lexer.TokenKind.COMMA):
                    continue
                break
        self._consume(lexer.TokenKind.RPAREN, "Expected ')' after parameters")

        body: List[Stmt] = []
        while not self._is_at_end():
            if self._check_kw("end_function") or self._check_kw("end_func"):
                break
            if self._check_kw("end") and self._next_kw_in({"function", "func"}):
                break
            body.append(self._statement())

        if self._match_kw("end_function") or self._match_kw("end_func"):
            pass
        elif self._match_kw("end"):
            # allow "end function" or "end func"
            if self._match_kw("function") or self._match_kw("func"):
                pass
            else:
                end_name = "function" if start_kw == "function" else "func"
                self._consume_kw(end_name, f"Expected '{end_name}' after end")
        else:
            tok = self._peek()
            raise ParseError(f"Expected function terminator at {tok.line}:{tok.col}")

        return Function(
            name=name_tok.lexeme,
            params=params,
            body=body,
            line=name_tok.line,
            col=name_tok.col,
        )

    def _param_decl(self) -> Param:
        name_tok = self._consume_ident("Expected parameter name")
        param_type = None
        default = None
        if self._match_op(lexer.TokenKind.COLON):
            param_type = self._type_name()
        if self._match_op(lexer.TokenKind.EQ):
            default = self._expression()
        return Param(
            name=name_tok.lexeme,
            type=param_type,
            default=default,
            line=name_tok.line,
            col=name_tok.col,
        )

    def _call_statement(self) -> Call:
        name_tok = self._consume_function_name()
        self._consume_kw("with", "Expected 'with' after function name")
        self._consume_any_kw(
            ["arguments", "aguments"], "Expected 'arguments' after 'with'"
        )
        self._match_op(lexer.TokenKind.COLON)
        self._consume(lexer.TokenKind.LPAREN, "Expected '(' after arguments:")
        args: List[Arg] = []
        if not self._check_kind(lexer.TokenKind.RPAREN):
            while True:
                if self._check_kind(lexer.TokenKind.IDENT) and self._peek_next_is(
                    lexer.TokenKind.EQ
                ):
                    arg_name_tok = self._advance()
                    self._consume(lexer.TokenKind.EQ, "Expected '=' after arg name")
                    value = self._expression()
                    args.append(
                        Arg(
                            name=arg_name_tok.lexeme,
                            value=value,
                            line=arg_name_tok.line,
                            col=arg_name_tok.col,
                        )
                    )
                else:
                    value = self._expression()
                    args.append(
                        Arg(name=None, value=value, line=value.line, col=value.col)
                    )

                if self._match_op(lexer.TokenKind.COMMA):
                    continue
                break
        self._consume(lexer.TokenKind.RPAREN, "Expected ')' after call arguments")
        return Call(
            name=name_tok.lexeme, args=args, line=name_tok.line, col=name_tok.col
        )

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
            seqs = [
                (["greater", "than", "or", "equal", "to"], ">="),
                (["less", "than", "or", "equal", "to"], "<="),
                (["greater", "or", "equal", "to"], ">="),
                (["less", "or", "equal", "to"], "<="),
                (["greater", "than"], ">"),
                (["less", "than"], "<"),
                (["equal", "to"], "=="),
                (["not", "equal", "to"], "!="),
            ]
            for seq, op in seqs:
                if self._try_keywords(seq):
                    return op
        tok = self._peek()
        raise ParseError(f"Expected comparison operator at {tok.line}:{tok.col}")

    # --- expressions ---
    def _expression(self) -> Expr:
        return self._add_expr()

    def _add_expr(self) -> Expr:
        expr = self._mul_expr()
        while True:
            if self._match_op(lexer.TokenKind.PLUS):
                op_tok = self._previous()
                right = self._mul_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            elif self._match_op(lexer.TokenKind.MINUS):
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
            if self._match_op(lexer.TokenKind.STAR):
                op_tok = self._previous()
                right = self._power_expr()
                expr = Binary(
                    expr, op_tok.lexeme, right, line=op_tok.line, col=op_tok.col
                )
            elif self._match_op(lexer.TokenKind.SLASH):
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
            if self._match_op(lexer.TokenKind.LBRACKET):
                idx = self._expression()
                self._consume(lexer.TokenKind.RBRACKET, "Expected ']' after index")
                return Index(tok.lexeme, idx, line=tok.line, col=tok.col)
            return Var(tok.lexeme, line=tok.line, col=tok.col)
        if self._match_op(lexer.TokenKind.LPAREN):
            expr = self._expression()
            self._consume(lexer.TokenKind.RPAREN, "Expected ')' after expression")
            return expr
        tok = self._peek()
        raise ParseError(f"Expected expression at {tok.line}:{tok.col}")

    def _inplace_update(self, kind: str) -> Assign:
        value = self._expression()
        if kind == "add":
            self._consume_kw("to", "Expected 'to' after add expression")
            target_tok = self._consume_ident("Expected target variable after 'to'")
            expr = Binary(
                left=Var(
                    name=target_tok.lexeme, line=target_tok.line, col=target_tok.col
                ),
                op="+",
                right=value,
                line=target_tok.line,
                col=target_tok.col,
            )
        else:
            self._consume_kw("from", "Expected 'from' after sub expression")
            target_tok = self._consume_ident("Expected target variable after 'from'")
            expr = Binary(
                left=Var(
                    name=target_tok.lexeme, line=target_tok.line, col=target_tok.col
                ),
                op="-",
                right=value,
                line=target_tok.line,
                col=target_tok.col,
            )
        return Assign(
            name=target_tok.lexeme,
            expr=expr,
            line=target_tok.line,
            col=target_tok.col,
        )

    def _assignment_rhs(self, lhs_tok: lexer.Token) -> Expr:
        # Support phrase forms like "add 6 to x" / "sub 2 from x" while
        # leaving regular expressions like "add 1 and 2" untouched.
        if self._check_kw("add"):
            save = self.current
            self._advance()  # consume 'add'
            value = self._expression()
            if self._match_kw("to"):
                target_tok = self._consume_ident("Expected target variable after 'to'")
                return Binary(
                    left=Var(
                        name=target_tok.lexeme,
                        line=target_tok.line,
                        col=target_tok.col,
                    ),
                    op="+",
                    right=value,
                    line=lhs_tok.line,
                    col=lhs_tok.col,
                )
            self.current = save
        if self._check_kw("sub") or self._check_kw("subtract"):
            save = self.current
            self._advance()  # consume 'sub'/'subtract'
            value = self._expression()
            if self._match_kw("from"):
                target_tok = self._consume_ident(
                    "Expected target variable after 'from'"
                )
                return Binary(
                    left=Var(
                        name=target_tok.lexeme,
                        line=target_tok.line,
                        col=target_tok.col,
                    ),
                    op="-",
                    right=value,
                    line=lhs_tok.line,
                    col=lhs_tok.col,
                )
            self.current = save
        return self._expression()

    def _return_statement(self, start_tok: lexer.Token | None = None) -> Return:
        values: List[Expr] = []
        if self._is_expr_start():
            first = self._expression()
            values.append(first)
            while True:
                if self._match_op(lexer.TokenKind.COMMA):
                    values.append(self._expression())
                    continue
                if self._is_expr_start():
                    values.append(self._expression())
                    continue
                break
        tok = start_tok or self._previous()
        return Return(values=values, line=tok.line, col=tok.col)

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
        for t in ("int", "float", "string", "bool", "list", "array"):
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

    def _consume_function_name(self):
        if self._check_kind(lexer.TokenKind.STRING):
            return self._advance()
        if self._check_kind(lexer.TokenKind.IDENT):
            return self._advance()
        raise ParseError("Expected function name")

    def _consume_any_kw(self, kws: List[str], msg: str):
        for kw in kws:
            if self._match_kw(kw):
                return
        raise ParseError(msg)

    def _peek_next_is(self, kind: lexer.TokenKind) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].kind == kind

    def _next_kw_in(self, kws: set[str]) -> bool:
        if self.current + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.current + 1]
        return nxt.kind == lexer.TokenKind.KEYWORD and nxt.lexeme in kws

    def _check_kind(self, kind: lexer.TokenKind) -> bool:
        if self._is_at_end():
            return False
        return self._peek().kind == kind

    def _is_expr_start(self) -> bool:
        if self._is_at_end():
            return False
        t = self._peek()
        if t.kind in {
            lexer.TokenKind.NUMBER,
            lexer.TokenKind.STRING,
            lexer.TokenKind.IDENT,
            lexer.TokenKind.LPAREN,
            lexer.TokenKind.PLUS,
            lexer.TokenKind.MINUS,
        }:
            return True
        if t.kind == lexer.TokenKind.KEYWORD and t.lexeme in {
            "add",
            "subtract",
            "multiply",
            "divide",
            "power",
            "not",
        }:
            return True
        return False

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

    def _try_keywords(self, seq: List[str]) -> bool:
        save = self.current
        for kw in seq:
            if not self._match_kw(kw):
                self.current = save
                return False
        return True

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
