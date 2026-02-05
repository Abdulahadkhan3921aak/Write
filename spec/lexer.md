# Write Lexer Specification (parser-aligned)

Token kinds and keyword set match `src/compiler/lexer.py`. Longest-match rules apply.

## Token categories

- Keywords: `set`, `make`, `input`, `as`, `of`, `size`, `to`, `print`, `return`,
    `if`, `else`, `end`, `then`, `while`, `do`, `for`, `from`, `and`, `or`, `not`,
    `is`, `greater`, `less`, `equal`, `than`, `add`, `subtract`, `sub`, `multiply`,
    `divide`, `power`, `int`, `float`, `string`, `bool`, `list`, `array`,
    `function`, `func`, `end_function`, `end_func`, `arguments`, `aguments`, `arg`,
    `args`, `with`, `call`.
- Operators / symbols: `+`, `-`, `*`, `/`, `^`, `(`, `)`, `[`, `]`, `,`, `:`,
    `!`, `&`, `|`, `==`, `!=`, `>=`, `<=`, `>`, `<`, `=`.
- Literals: NUMBER (int/float), STRING (double-quoted with escapes).
- IDENT: `[A-Za-z_][A-Za-z0-9_]*` not in the keyword set.
- EOF sentinel.

## Regex sketches (PCRE-ish)

- WHITESPACE: `[\t\r ]+` (skip)
- NEWLINE: `\n` (advance line/col, otherwise skip)
- COMMENT: `#.*` (skip)
- STRING: `"([^"\\]|\\.)*"` (report unterminated)
- NUMBER: `(\d+\.\d+|\d+)`
- IDENT/KEYWORD: `[A-Za-z_][A-Za-z0-9_]*` (classify via keyword set)
- OPERATORS (order matters): `==|!=|>=|<=|\^|\+|-|\*|/|\(|\)|\[|\]|,|:|!|&|\||>|<|=`

## Mapping notes

- Logical: `and`/`&`, `or`/`|`, unary `not`/`!`.
- Comparison: emit individual tokens (`is`, `greater`, `than`, …); the parser
    assembles sequences like `is greater than` or `is less than or equal to`.
- Arithmetic words (`add`, `subtract`, `multiply`, `divide`, `power`) are
    keywords so the parser can accept phrase-style expressions.
- Arrays/lists: use `[` `]` for indexing; `of size` appears in declarations but is
    tokenized as separate keywords.

## Token walkthrough examples

````write
make numbers as list of size 5
set numbers[0] to 10
````

- KEYWORD(make)
- IDENT(numbers)
- KEYWORD(as)
- KEYWORD(list)
- KEYWORD(of)
- KEYWORD(size)
- NUMBER(5)
- KEYWORD(set)
- IDENT(numbers)
- OP([)
- NUMBER(0)
- OP(])
- KEYWORD(to)
- NUMBER(10)

````write
call "sum" with arguments:(a=1, b=2)
````

- KEYWORD(call)
- STRING("sum")
- KEYWORD(with)
- KEYWORD(arguments)
- OP(:) [optional]
- OP(()
- IDENT(a)
- OP(=)
- NUMBER(1)
- OP(,)
- IDENT(b)
- OP(=)
- NUMBER(2)
- OP())

````write
if x is less than 10 and not done then
        print x, "ok"
end if
````

- KEYWORD(if)
- IDENT(x)
- KEYWORD(is)
- KEYWORD(less)
- KEYWORD(than)
- NUMBER(10)
- KEYWORD(and)
- KEYWORD(not)
- IDENT(done)
- KEYWORD(then)
- KEYWORD(print)
- IDENT(x)
- OP(,)
- STRING("ok")
- KEYWORD(end)
- KEYWORD(if)

## Error handling

- Unknown character → raise with line/col.
- Unterminated string → raise with line/col.
- Invalid number (e.g., trailing dot) → raise with position.
- Still emit EOF even after an error if you choose to recover.

## Implementation tips

- Apply longest-match for multi-char operators before single-char ones.
- Maintain line/col on every advance; newline resets column to 1.
- Keep `KEYWORD` kind with original lexeme; the parser disambiguates phrases.
