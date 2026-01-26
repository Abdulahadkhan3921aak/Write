# IDE Diagnostics Plan

This compiler surfaces diagnostics that an IDE can display alongside type hints:

- Variable type info: the semantic pass records the declared or inferred type of each variable. Containers track a literal size when declared with an integer `of size N`.
- Function checks: undefined function names, duplicate definitions, wrong arity, missing named args, duplicate args, and type-mismatched arguments are reported.
- Assignment checks: type mismatches against declarations, container element type enforcement, and re-declarations in the same scope.
- Control flow checks: non-numeric loop bounds, return outside a function.
- Container bounds: literal `list/array` sizes are recorded; literal indices are rejected when `index < 0` or `index >= size` for both reads and writes.
- Input rules: `input` requires a prior declaration unless typed inline.

Suggested IDE surfaces:

- Hover: show variable type (and size for containers) from the semantic table.
- Squiggles: highlight mismatched types, unknown identifiers, missing/extra function arguments, and out-of-bounds literal indices.
- Quick-fixes: suggest existing function names when an unknown call is detected; suggest available parameters when a named argument is wrong.

Sample files demonstrating these behaviors are in `spec/examples/`:

- `containers_sized.write` — valid sized lists and indexing.
- `functions_and_calls.write` — typed functions and calls.
- `diagnostics_showcase.write` — examples that should raise diagnostics (unknown function, wrong arity, out-of-bounds index).
- `full_language_tour.write` — broad coverage: types, loops, functions, containers, conditionals, arithmetic.
- `named_args_and_defaults.write` — default parameters and named arguments.
- `io_and_conditions.write` — input, booleans, comparisons, and conditional flow.
