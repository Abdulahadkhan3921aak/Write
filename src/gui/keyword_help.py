"""Keyword help system for the Write IDE."""

from __future__ import annotations


class KeywordDatabase:
    """Database of keyword descriptions and help text."""

    KEYWORDS = {
        # Control flow
        "if": "Conditional statement: if <condition> then ... end if",
        "else": "Else clause for if statements",
        "end": "Marks end of block (if/while/for/function)",
        "then": "Keyword after condition in if statements",
        "while": "Loop while condition is true: while <condition> do ... end while",
        "do": "Keyword that starts the loop body",
        "for": "For loop: for <var> from <start> to <end> do ... end for",
        "from": "Part of for loop: for i from 1 to 10",
        # Variables
        "set": "Assignment: set <variable> to <value>",
        "make": "Create/initialize: make <numbers> as list of size 10",
        "input": "Read input: input <variable>",
        "to": "Assignment: set x to 5",
        "as": "Type declaration: make list as list of size 5",
        "of": "List declaration: list of size 5",
        "size": "List parameter: list of size 10",
        # Functions
        "function": 'Define function: function "name" arguments:(a:int, b:float) ... end_function',
        "func": "Short form of function",
        "end_function": "End of function block",
        "end_func": "Short form of end_function",
        "return": "Return value from function",
        "call": 'Call function: call "name" with arguments:(val1, val2)',
        "arguments": "Function parameters: arguments:(a:int, b:float)",
        "arg": "Function parameter",
        "args": "Function parameters",
        "with": "Call syntax: call name with arguments:(...)",
        # Data types
        "int": "Integer type",
        "float": "Floating point type",
        "string": "String/text type",
        "bool": "Boolean type (true/false)",
        "list": "List/array type",
        "array": "Alias for list type",
        # I/O
        "print": 'Print output: print "Hello" or print variable',
        # Logic
        "and": "Logical AND operator",
        "or": "Logical OR operator",
        "not": "Logical NOT (negation)",
        "is": "Comparison: x is equal to 5",
        "equal": "Equality check: x is equal to 5",
        "greater": "Greater than: x is greater than 5",
        "less": "Less than: x is less than 5",
        "than": "Comparison keyword: greater than, less than",
        # Arithmetic
        "add": "Addition: add x and y",
        "subtract": "Subtraction: subtract x from y",
        "sub": "Short form of subtract",
        "multiply": "Multiplication: multiply x and y",
        "divide": "Division: divide x by y",
        "power": "Exponentiation: power x by y",
    }

    @classmethod
    def get_help(cls, keyword: str) -> str:
        """Get help text for a keyword."""
        return cls.KEYWORDS.get(keyword.lower(), "")

    @classmethod
    def get_all_keywords(cls) -> list[str]:
        """Get all available keywords."""
        return sorted(cls.KEYWORDS.keys())

    @classmethod
    def is_keyword(cls, word: str) -> bool:
        """Check if word is a keyword."""
        return word.lower() in cls.KEYWORDS
