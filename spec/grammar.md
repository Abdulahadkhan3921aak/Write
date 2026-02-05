# Write Grammar (parser-aligned, LL-friendly)

Deterministic, readable grammar that matches the current recursive-descent parser in
`src/compiler/parser.py`. Uses explicit block terminators and English-like phrases.

## Tokens (high level)

- Keywords: `set`, `make`, `input`, `as`, `of`, `size`, `to`, `print`, `return`,
    `if`, `else`, `then`, `while`, `do`, `for`, `from`, `and`, `or`, `not`, `is`,
    `greater`, `less`, `equal`, `than`, `add`, `subtract`, `sub`, `multiply`,
    `divide`, `power`, `int`, `float`, `string`, `bool`, `list`, `array`,
    `function`, `func`, `end_function`, `end_func`, `arguments`, `aguments`,
    `with`, `call`.
- Symbols: `+ - * / ^ ( ) [ ] , : ! & | == != > < >= <= =`.
- Literals: NUMBER (int/float), STRING.
- Identifiers: IDENT.
- EOF sentinel.

## Operator precedence (high → low)

1. Parentheses `( )`
2. Unary `+ -` and logical `!` / `not`
3. Power: `a ^ b` or phrase `power a and b` (right-associative)
4. Multiplicative: `* /` or phrases `multiply/divide ... and ...`
5. Additive: `+ -` or phrases `add/subtract ... and ...`
6. Comparisons: `== != > < >= <=` and English forms (`is greater than`, etc.)
7. Logical AND: `and` / `&`
8. Logical OR: `or` / `|`

All binary operators are left-associative except power (right-associative).

## Grammar (EBNF)

### Top-level

program        ::= (function_def | stmt)* EOF

function_def   ::= ("function" | "func") func_name ("arguments" | "aguments")? ":"? "(" param_list? ")" stmt* function_end
function_end   ::= "end_function" | "end_func" | "end" ("function" | "func")
func_name      ::= STRING | IDENT

param_list     ::= param ("," param)*
param          ::= IDENT (":" type_name)? ("=" expr)?
type_name      ::= "int" | "float" | "string" | "bool" | "list" | "array"

### Statements

stmt           ::= assignment
                                | declaration
                                | input_stmt
                                | print_stmt
                                | call_stmt
                                | return_stmt
                                | if_stmt
                                | while_stmt
                                | for_stmt
                                | add_stmt
                                | sub_stmt

declaration    ::= "make" IDENT ("as" type_name ("of" "size" expr)? )?

assignment     ::= "set" IDENT (index_suffix)? (":" type_name)? "to" assignment_rhs
index_suffix   ::= "[" expr "]"
assignment_rhs ::= expr | add_phrase | sub_phrase

# convenience in-place updates

add_stmt       ::= add_phrase
sub_stmt       ::= sub_phrase
add_phrase     ::= "add" expr "to" IDENT
sub_phrase     ::= ("sub" | "subtract") expr "from" IDENT

# input and return

input_stmt     ::= "input" STRING? IDENT ("as" type_name)?
return_stmt    ::= "return" return_values?
return_values  ::= expr ("," expr | expr)*

# alias: "set return to ..."

assignment     ::= "set" "return" "to" return_values

print_stmt     ::= "print" print_values
print_values   ::= expr ("," expr | expr)*

call_stmt      ::= "call" func_name "with" ("arguments" | "aguments") ":"? "(" arg_list? ")"
arg_list       ::= arg ("," arg)*
arg            ::= IDENT "=" expr | expr

if_stmt        ::= "if" cond "then" stmt*elif_tail else_tail "end" "if"
elif_tail      ::= ("else" "if" cond "then" stmt*)*
else_tail      ::= ("else" stmt*)?

while_stmt     ::= "while" cond "do" stmt* "end" "while"

for_stmt       ::= "for" IDENT "from" expr "to" expr "do" stmt* "end" "for"

### Conditions (LL factored)

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
                                | "is" "greater" "than" "or" "equal" "to"
                                | "is" "less" "than" "or" "equal" "to"

### Expressions (precedence-factored)

expr           ::= add_expr
add_expr       ::= mul_expr (("+" | "-") mul_expr)*
mul_expr       ::= power_expr (("*" | "/") power_expr)*
power_expr     ::= unary_expr ("^" unary_expr | "power" unary_expr "and" power_expr)?
unary_expr     ::= ("+" | "-") unary_expr | primary

primary        ::= NUMBER
                                | STRING
                                | IDENT index_suffix?
                                | "(" expr ")"
                                | phrase_binary

phrase_binary  ::= ("add" | "subtract" | "multiply" | "divide") unary_expr "and" unary_expr
                                 | "power" unary_expr "and" unary_expr

### Notes

- Comparison phrases are multi-token sequences; the lexer emits individual keyword
    tokens, and the parser recognizes the sequences.
- `print` and `return` accept multiple expressions separated by commas or simply
    juxtaposed expressions on the same line (parser keeps consuming expression starts).
- Lists/arrays may declare a size with `make my_list as list of size 10` and are
    indexed with `name[expr]` in both expressions and assignments.
- Functions accept string or identifier names, support default parameter values,
    and allow both positional and named call arguments.
- Blocks end explicitly with `end if`, `end while`, `end for`, `end function` to
    avoid dangling-else ambiguity.
