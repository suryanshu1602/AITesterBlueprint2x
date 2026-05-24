# Chapter 11 — Python Learning

Beginner Python fundamentals for QA / test automation engineers. Each file is a standalone runnable lesson with inline comments and a quick-reference table.

## Files

| # | File | Topic | Covers |
|---|------|-------|--------|
| 01 | [01_Hello_Python.py](01_Hello_Python.py) | Hello world | First `print`, running a `.py` file |
| 02 | [02_Basic.py](02_Basic.py) | Variables & types | str, int, float, bool, None, identifier vs literal |
| 03 | [03_Basic2.py](03_Basic2.py) | More basics | Type conversions, input/output |
| 04 | [04_AIAGent_Query.py](04_AIAGent_Query.py) | AI agent query | Calling an LLM from Python |
| 05 | [05_Identifier.py](05_Identifier.py) | Identifier rules | Allowed chars, no spaces, no leading digit, no `$`/`-`/`.`, reserved keywords, unicode, PEP 8 |
| 06 | [06_Keyword.py](06_Keyword.py) | Reserved keywords | `keyword.kwlist` — 35 reserved words |
| 07 | [07_Case.py](07_Case.py) | Naming case styles | snake_case, PascalCase, camelCase, kebab-case, SCREAMING_SNAKE, dot.case, Hungarian, dunder |
| 08 | [08_Literals.py](08_Literals.py) | Literals | int/float/complex (bin/oct/hex), strings (raw/f-string/bytes), bool, None, list/tuple/set/dict/frozenset, Ellipsis, inf/nan |
| 09 | [09_Operators.py](09_Operators.py) | Operators | Arithmetic, assignment (+ walrus), comparison, logical, bitwise, identity (`is`), membership (`in`), ternary, unary, unpacking `*`/`**`, matrix `@`, precedence table |

## How to run

```bash
cd Chapter_11_Python_Learning
python3 01_Hello_Python.py
python3 05_Identifier.py
# ...etc
```

Optional virtualenv:

```bash
python3 -m venv venv
source venv/bin/activate
```

## Core concepts cheat sheet

```
name = "Pramod"
 │       │
 │       └── literal       (the value)
 └────────── identifier    (the name)
whole line  = variable assignment
```

- **Identifier** — name of variable, function, class. Rules in `05_Identifier.py`.
- **Keyword** — reserved word, cannot be used as identifier. List in `06_Keyword.py`.
- **Case style** — convention for multi-word names. Styles in `07_Case.py`.
- **Literal** — fixed value written in source. Types in `08_Literals.py`.
- **Operator** — symbol acting on operands. Categories in `09_Operators.py`.

## Recommended order

1. 01 → 04: get Python running, basic vars
2. 05 → 07: naming (identifier rules, keywords, case styles)
3. 08: values (literals)
4. 09: actions on values (operators)
