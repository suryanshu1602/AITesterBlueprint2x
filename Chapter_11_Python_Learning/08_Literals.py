# Literal = raw fixed value written directly in source code.
# Example: in `age = 25`, the `25` is an integer literal.
# Python literal types below.


# ============================================================
# 1. Numeric Literals
# ============================================================

# 1a. int — whole numbers, unlimited size
count = 25
negative = -100
big = 10_000_000           # underscore = visual separator, ignored by Python
print(count, negative, big, type(count))

# int in other bases:
binary = 0b1010            # binary,      prefix 0b -> 10
octal = 0o17               # octal,       prefix 0o -> 15
hexa = 0xFF                # hexadecimal, prefix 0x -> 255
print(binary, octal, hexa)

# 1b. float — decimal / scientific notation
price = 99.99
pi = 3.14
scientific = 1.5e3         # 1.5 x 10^3 = 1500.0
tiny = 2.5e-4              # 0.00025
print(price, pi, scientific, tiny, type(price))

# 1c. complex — real + imaginary (j = sqrt(-1))
c = 3 + 4j
print(c, c.real, c.imag, type(c))


# ============================================================
# 2. String Literals
# ============================================================

# 2a. Single, double, triple quotes
s1 = 'single'
s2 = "double"
s3 = '''triple single
spans multiple lines'''
s4 = """triple double
also multi-line"""
print(s1, s2)
print(s3)
print(s4)

# 2b. Escape sequences
escapes = "line1\nline2\tindented\\backslash\"quote"
print(escapes)

# 2c. Raw string — backslashes treated literally (regex, Windows paths)
raw = r"C:\Users\Pramod\new"
regex = r"\d+\.\d+"
print(raw, regex)

# 2d. f-string — formatted string literal (Python 3.6+)
name = "Pramod"
age = 25
msg = f"Hello {name}, age {age}, in 5 yrs = {age + 5}"
print(msg)



# ============================================================
# 3. Boolean Literals
# ============================================================
is_passing = True
is_failing = False
print(is_passing, is_failing, type(is_passing))
# Note: True == 1, False == 0 internally
print(True + True)         # 2


# ============================================================
# 4. None Literal (Special)
# ============================================================
result = None              # absence of value, NOT 0 or ""
print(result, type(result))


# ============================================================
# 5. Collection Literals
# ============================================================

# 5a. list — ordered, mutable
# nums = [1, 2, 3]
# mixed = [1, "two", 3.0, True]
# empty_list = []
# print(nums, mixed, empty_list)

# # 5b. tuple — ordered, immutable
# point = (10, 20)
# single = (5,)              # trailing comma needed for 1-element tuple
# empty_tuple = ()
# print(point, single, empty_tuple)

# # 5c. set — unordered, unique, mutable
# colors = {"red", "green", "blue"}
# empty_set = set()          # {} is dict, not set
# print(colors, empty_set)

# # 5d. frozenset — immutable set (built via constructor, no literal form)
# frozen = frozenset([1, 2, 3])
# print(frozen)

# # 5e. dict — key-value pairs
# user = {"name": "Pramod", "age": 25}
# empty_dict = {}
# print(user, empty_dict)


# ============================================================
# 6. Ellipsis Literal
# ============================================================
# `...` placeholder, also used in type hints, numpy slicing
def stub():
    ...                    # equivalent to `pass`
print(Ellipsis, ...)


# ============================================================
# 7. Special Numeric Floats
# ============================================================
inf = float("inf")
ninf = float("-inf")
nan = float("nan")
print(inf, ninf, nan)


# ============================================================
# Literal vs Identifier vs Variable
# ============================================================
# name = "Pramod"
#  |       |
#  |       +---- literal  (the value "Pramod")
#  +------------ identifier (the name)
#  whole line  = variable assignment


# ============================================================
# Quick reference table
# ============================================================
# category      type           example
# ----------    -----------    ----------------------
# numeric       int            25, 0b1010, 0xFF, 1_000
#               float          3.14, 1.5e3
#               complex        3+4j
# string        str            "hi", 'hi', """hi"""
#               raw            r"C:\path"
#               f-string       f"hi {name}"
#               bytes          b"hi"
# boolean       bool           True, False
# none          NoneType       None
# collection    list           [1, 2, 3]
#               tuple          (1, 2, 3)
#               set            {1, 2, 3}
#               dict           {"k": "v"}
#               frozenset      frozenset([1,2])
# special       Ellipsis       ...
#               float inf/nan  float("inf"), float("nan")
