# Write Grammar (LL-friendly)

Goal: deterministic, beginner-readable grammar suitable for an LL parser. This captures the English-like syntax, precedence/associativity, and key FIRST/FOLLOW considerations.

## Tokens (high-level)

- Keywords: `set`, `to`, `print`, `if`, `else`, `end`, `then`, `while`, `do`, `for`, `from`, `and`, `or`, `not`, `is`, `greater`, `less`, `equal`, `than`
- Symbols: `+ - * / ( ) ! & | == != > < >= <=`
- Literals: NUMBER (int or float), STRING
- Identifiers: IDENT

## Operator precedence (high to low)

1. Parentheses `( )`
2. Unary: `!` / `not`
3. Power form: `power A and B` (right-associative)
4. Multiplicative: `* /` / `multiply` `divide`
5. Additive: `+ -` / `add` `subtract`
6. Comparisons: `== != > < >= <=` and English forms
7. Logical AND: `and` `&`
8. Logical OR: `or` `|`

Associativity: binary operators are left-associative except power (right-associative by design). Logical ops are left-associative.

## Grammar (EBNF, LL-structured)

# Top-level

program        ::= stmt_list EOF

stmt_list      ::= stmt stmt_list | ε

stmt           ::= assignment
    | print_stmt
    | if_stmt
    | while_stmt
    | for_stmt

assignment     ::= "set" IDENT "to" expr

print_stmt     ::= "print" (STRING | expr)

if_stmt        ::= "if" cond "then" stmt_list elseif_tail else_tail "end" "if"

elseif_tail    ::= "else" "if" cond "then" stmt_list elseif_tail | ε

else_tail      ::= "else" stmt_list | ε

while_stmt     ::= "while" cond "do" stmt_list "end" "while"

for_stmt       ::= "for" IDENT "from" expr "to" expr "do" stmt_list "end" "for"

# Conditions factored for LL (no left recursion)

cond           ::= cond_or

cond_or        ::= cond_and (log_or cond_and)*
cond_and       ::= cond_not (log_and cond_not)*
cond_not       ::= ("!" | "not") cond_not | cond_cmp
cond_cmp       ::= expr comp_op expr | "(" cond ")"

log_or         ::= "or" | "|"
log_and        ::= "and" | "&"

comp_op        ::= "==" | "!=" | ">" | "<" | ">=" | "<="
    | "is" "equal" "to"
    | "is" "not" "equal" "to"
    | "is" "greater" "than"
    | "is" "less" "than"
    | "is" "greater" "or" "equal" "to"
    | "is" "less" "or" "equal" "to"

# Expressions factored for precedence

expr           ::= add_expr

add_expr       ::= mul_expr (("+" | "-" | "add" | "subtract") mul_expr)*
mul_expr       ::= power_expr (("*" | "/" | "multiply" | "divide") power_expr)*

# Right-associative power

power_expr     ::= unary_expr ("power" unary_expr "and" power_expr)?

unary_expr     ::= ("+" | "-") unary_expr | primary

primary        ::= NUMBER
    | IDENT
    | STRING
    | "(" expr ")"

## Optional tightening (implementation choices)

- If you want to disallow string comparisons, gate `STRING` out of `primary` and allow it only in `print_stmt`.
- To avoid ambiguity between `else if` and `elseif`, keep it lexed as two keywords and parsed via `elseif_tail` as above.
- If you prefer iterative stmt_list, you can parse statements in a loop until you see a block terminator token (`end`, `else`, `EOF`).

## FIRST/FOLLOW notes (high level)

- `stmt` FIRST: {`set`, `print`, `if`, `while`, `for`}
- `cond` FIRST: inherits from `cond_or` → from `cond_not` → from `!`, `not`, `(`, NUMBER, IDENT, STRING
- `expr` FIRST: `+ - ( NUMBER IDENT STRING`
- `stmt_list` FIRST: same as `stmt`; FOLLOW often includes block terminators (`end`, `else`, `else if`, `end while`, `end for`, EOF)
- Factoring `cond` into `or/and/not/cmp` removes left recursion and keeps disjoint FIRST sets for choice points.

## Notes

- Comparison phrases are multi-token; the lexer should emit symbolic tokens for `== != > < >= <=` and treat English forms as keyword sequences consumed by `comp_op`.
- Power is right-associative to align with math expectations.
- Blocks end explicitly with `end if`, `end while`, `end for` to avoid dangling-else ambiguity.
- Extend grammar here as features grow (e.g., functions) while preserving LL shape.
