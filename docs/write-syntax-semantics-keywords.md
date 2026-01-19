# Write Language: Syntax Examples, Semantics, and Keywords

## Examples (Write source)

### Variables and arithmetic

```
set x to 10
set y to 5
set sum to add x and y
set scaled to multiply sum and 3
set powered to power x and 2
```

### Printing

```
print sum
print "Hello World"
```

### Conditionals

```
if x is greater than y then
    print "x is greater"
else if x is equal to y then
    print "x equals y"
else
    print "y is greater"
end if
```

### While loop

```
while x is less than 10 do
    set x to add x and 1
    print x
end while
```

### For loop

```
for i from 1 to 5 do
    print i
end for
```

### Logical expressions

```
if !(x == 0 | y == 0) then
    print "none is zero"
end if

if x > 0 and y > 0 then
    print "both positive"
end if
```

## Semantics (concise)

- Variables: declared on first assignment via `set name to expr`; reassignment allowed; implementation may treat undeclared reads as errors.
- Types: int by default; allow float literals (e.g., `3.14`) if enabled; numeric operations coerce to the wider type; string literals remain strings; no implicit string-number mixing.
- Power: `power a and b` maps to `pow(a, b)` (C/C++); result follows numeric promotion (int->double unless you constrain to int-only).
- Blocks: `if/else`, `while`, `for` introduce new statement blocks; scopes can be global-only or block-scoped per implementation choice (recommend block scope for loop indices).
- Conditions: comparisons produce booleans; `and/or/!/&/|` use short-circuit semantics if supported; precedence: `!` highest, then comparison, then `and/&`, then `or/|`.
- For loop semantics: `for i from a to b do ... end for` initializes `i = a`, executes body while `i <= b`, incrementing `i` by 1 each iteration.
- Print: outputs expression or string literal with newline (maps to `std::cout << value << std::endl`).
- Errors: undefined identifier, type mismatch (if typing enforced), malformed syntax, or division by zero (runtime guard optional).

## Keywords and operators

- Control: `if`, `else if`, `else`, `end if`, `while`, `end while`, `for`, `end for`, `from`, `do`, `then`
- Assignment: `set`, `to`
- Arithmetic: `add`, `subtract`, `multiply`, `divide`, `power`, `+`, `-`, `*`, `/`
- Comparison (English forms map to symbols): `is equal to (==)`, `is not equal to (!=)`, `is greater than (>)`, `is less than (<)`, `is greater or equal to (>=)`, `is less or equal to (<=)`, plus symbolic `== != > < >= <=`
- Logical: `and`, `or`, `not`, `!`, `&`, `|`
- Other: parentheses `(` `)`, identifiers, numeric literals (int/float), string literals
