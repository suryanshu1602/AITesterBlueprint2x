# Operator = symbol that performs operation on operands.
# Example: in `a + b`, the `+` is operator, `a` and `b` are operands.
# All Python operator categories below.


# ============================================================
# 1. Arithmetic Operators — math
# ============================================================
a, b = 10, 3
print("a + b  =", a + b)     # 13   addition
print("a - b  =", a - b)     # 7    subtraction
print("a * b  =", a * b)     # 30   multiplication
print("a / b  =", a / b)     # 3.33 true division -> float
print("a // b =", a // b)    # 3    floor division -> int (rounds down)
print("a % b  =", a % b)     # 1    modulus (remainder)
print("a ** b =", a ** b)    # 1000 exponent (power)


# ============================================================
# 2. Assignment Operators — assign + shorthand math
# ============================================================
x = 10
x += 5    # x = x + 5  -> 15
x -= 2    # 13
x *= 2    # 26
x /= 4    # 6.5
x //= 2   # 3.0
x **= 2   # 9.0
x %= 4    # 1.0
print("after compound assign x =", x)



# ============================================================
# 3. Comparison / Relational Operators — return bool
# ============================================================
a, b = 10, 20
print(a == b)    # False  equal
print(a != b)    # True   not equal
print(a > b)     # False  greater
print(a < b)     # True   less
print(a >= b)    # False  greater or equal
print(a <= b)    # True   less or equal

# Chained comparison (Pythonic):
age = 25
print(18 <= age < 60)        # True


# ============================================================
# 4. Logical Operators — combine boolean expressions
# ============================================================
t, f = True, False
print(t and f)    # False  both must be True
print(t or f)     # True   either True
print(not t)      # False  invert

# Short-circuit + non-bool return:
print(0 or "default")        # "default"  (0 is falsy)
print("hi" and "bye")        # "bye"      (returns last truthy)


# # ============================================================
# # 5. Bitwise Operators — operate bit-by-bit
# # ============================================================
# a, b = 0b1100, 0b1010   # 12, 10
# print(bin(a & b))       # 0b1000   AND
# print(bin(a | b))       # 0b1110   OR
# print(bin(a ^ b))       # 0b0110   XOR
# print(bin(~a))          # -0b1101  NOT (inverts all bits)
# print(bin(a << 2))      # 0b110000 left shift
# print(bin(a >> 1))      # 0b110    right shift


# ============================================================
# 6. Identity Operators — same object in memory?
# ============================================================
a = [1, 2, 3]
b = a
c = [1, 2, 3]
print(a is b)        # True   same object
print(a is c)        # False  same value, different object
print(a is not c)    # True
print(a == c)        # True   == checks value, not identity


# ============================================================
# 7. Membership Operators — value present in collection?
# ============================================================
nums = [1, 2, 3]
print(2 in nums)         # True
print(5 not in nums)     # True
print("a" in "banana")   # True
print("x" in {"x": 1})   # True (checks dict keys)


# ============================================================
# 8. Ternary / Conditional Operator — inline if-else
# ============================================================
age = 20
status = "adult" if age >= 18 else "minor"
print(status)


# ============================================================
# 9. Unary Operators — single operand
# ============================================================
x = 5
print(-x)     # -5    unary minus
print(+x)     # 5     unary plus
print(~x)     # -6    bitwise not
print(not x)  # False logical not



# ============================================================
# 12. Matrix Multiplication Operator @  (Python 3.5+, numpy)
# ============================================================
# import numpy as np
# a = np.array([[1, 2], [3, 4]])
# print(a @ a)      # matrix product, NOT element-wise


# ============================================================
# Operator Precedence (high -> low, abbreviated)
# ============================================================
# 1.  ()                          parentheses
# 2.  **                          exponent
# 3.  +x  -x  ~x                  unary
# 4.  *  /  //  %  @              multiplicative
# 5.  +  -                        additive
# 6.  <<  >>                      bit shift
# 7.  &                           bitwise AND
# 8.  ^                           bitwise XOR
# 9.  |                           bitwise OR
# 10. ==  !=  <  >  <=  >=  is  in   comparison + identity + membership
# 11. not
# 12. and
# 13. or
# 14. if-else (ternary)
# 15. :=                          walrus
# 16. =  +=  -= ...               assignment


# ============================================================
# Quick reference
# ============================================================
# category        operators
# --------------  -----------------------------------------
# arithmetic      +  -  *  /  //  %  **
# assignment      =  +=  -=  *=  /=  //=  %=  **=  &=  |=  ^=  <<=  >>=  :=
# comparison      ==  !=  >  <  >=  <=
# logical         and  or  not
# bitwise         &  |  ^  ~  <<  >>
# identity        is  is not
# membership      in  not in
# ternary         x if cond else y
# unpacking       *  **
# matrix          @
