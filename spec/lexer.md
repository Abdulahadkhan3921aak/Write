Next options: add more token examples (e.g., for/while blocks), wire a Python lexer skeleton under src/compiler, or extend error-handling notes.# Write Lexer Specification

## Token categories

- Keywords: set, to, print, if, else, end, then, while, do, for, from, and, or, not, is, greater, less, equal, than
- Operators/symbols: +, -, *, /, (, ), !, &, |, ==, !=, >, <, >=, <=
- Literals: NUMBER (int/float), STRING
- Identifier: IDENT
- Punctuation: none beyond parentheses

## Regex suggestions (PCRE-style)

- WHITESPACE: `[\t\r\n ]+` (skip)
- COMMENT (optional): `#.*` to end of line (skip)
- STRING: `"([^"\\]|\\.)*"`
- NUMBER: `(\d+\.\d+|\d+)`
- IDENT/KEYWORD: `[A-Za-z_][A-Za-z0-9_]*`
- OPERATORS (longest match first): `==|!=|>=|<=|\+|-|\*|/|\(|\)|!|&|\|>|<`

After scanning IDENT/KEYWORD, if lexeme is in the keyword set, emit the keyword token; otherwise emit IDENT.

## Operator/keyword mapping notes

- Logical: `and`/`&`, `or`/`|`, unary `not`/`!`
- Comparison: allow both symbolic (`== != > < >= <=`) and English sequences consumed in parser (`is equal to`, etc.). Lex them as separate tokens so the parser can match the sequences.

## Token emission examples

Input:

``` write
set x to add y and 3
```

Tokens:

- KEYWORD(set)
- IDENT(x)
- KEYWORD(to)
- IDENT(add) or KEYWORD(add) if you treat add as keyword (recommended: treat arithmetic words as keywords)
- IDENT(y)
- KEYWORD(and)
- NUMBER(3)

Input:

``` write
if x is greater than 2 and y <= 5 then
    print "ok"
end if
```

Tokens:

- KEYWORD(if)
- IDENT(x)
- KEYWORD(is)
- KEYWORD(greater)
- KEYWORD(than)
- NUMBER(2)
- KEYWORD(and)
- IDENT(y)
- OP(<=)
- NUMBER(5)
- KEYWORD(then)
- NEWLINE/WHITESPACE (skipped)
- KEYWORD(print)
- STRING("ok")
- KEYWORD(end)
- KEYWORD(if)

Input:

``` write
while !(a == 0 | b == 0) do
    print "none is zero"
end while
```

Tokens:

- KEYWORD(while)
- OP(!)
- OP(()
- IDENT(a)
- OP(==)
- NUMBER(0)
- OP(|)
- IDENT(b)
- OP(==)
- NUMBER(0)
- OP())
- KEYWORD(do)
- KEYWORD(print)
- STRING("none is zero")
- KEYWORD(end)
- KEYWORD(while)

Input:

``` write
for i from 1 to 3 do
    print i
end for
```

Tokens:

- KEYWORD(for)
- IDENT(i)
- KEYWORD(from)
- NUMBER(1)
- KEYWORD(to)
- NUMBER(3)
- KEYWORD(do)
- KEYWORD(print)
- IDENT(i)
- KEYWORD(end)
- KEYWORD(for)

Input:

``` write
while x is less than 10 do
    set x to add x and 1
end while
```

Tokens:

- KEYWORD(while)
- IDENT(x)
- KEYWORD(is)
- KEYWORD(less)
- KEYWORD(than)
- NUMBER(10)
- KEYWORD(do)
- KEYWORD(set)
- IDENT(x)
- KEYWORD(to)
- KEYWORD(add)
- IDENT(x)
- KEYWORD(and)
- NUMBER(1)
- KEYWORD(end)
- KEYWORD(while)

## Error handling

- Unknown characters: report with line/column and skip or halt.
- Unterminated string: report with line/column; halt.
- Invalid number: malformed float (e.g., `12.`) or overflow; report with position.
- Unexpected character after operator: surface the lexeme and position to aid debugging.

## Implementation tips

- Use longest-match scanning; test multi-char operators before single-char.
- Preserve line/column for diagnostics to feed parser and GUI error display.
- Keep a token kind for EOF.
