# Identifier = name of variable, function, class, module.
# Python identifier rules below. Invalid examples kept commented so file still runs.


# Rule 1: Allowed chars = letters (a-z, A-Z), digits (0-9), underscore (_).
name = "pramod"
user_name = "Pramod"
userName2 = "Dutta"
print(name, user_name, userName2)


# Rule 2: No spaces allowed.
# first name = "Pramod"        # SyntaxError: invalid syntax
first_name = "Pramod"           # use underscore instead
print(first_name)


# Rule 3: Cannot start with digit. Can contain digits after first char.
# 1name = "bad"                 # SyntaxError
# 123 = 123                     # SyntaxError: cannot assign to literal
name1 = "ok"
test_42 = "ok"
print(name1, test_42)


# Rule 4: Can start with underscore. Often means "private/internal" by convention.
_internal = "private-ish"
__dunder__ = "reserved style, avoid for own vars"
print(_internal, __dunder__)


# Rule 5: Case-sensitive. name, Name, NAME are 3 different identifiers.
age = 10
Age = 20
AGE = 30
print(age, Age, AGE)


# Rule 6: NO special chars allowed: $ @ # % ! - . / \ ? + * & space etc.
# Unlike JavaScript/PHP, $ is NOT valid in Python.
# $price = 100                  # SyntaxError
# user-name = "bad"             # SyntaxError (minus = subtraction)
# user@id = "bad"               # SyntaxError
# user.name = "bad"             # treated as attribute access, not identifier
price_usd = 100
print(price_usd)


# Rule 7: Cannot use Python reserved keywords (35 keywords).
# Examples: if, else, for, while, def, class, return, True, False, None,
#           import, from, as, try, except, finally, with, lambda, yield,
#           global, nonlocal, pass, break, continue, in, is, not, and, or,
#           assert, del, raise, async, await
# class = "bad"                 # SyntaxError
# for = 5                       # SyntaxError
class_name = "Selenium"         # workaround: rename or trailing underscore
type_ = "str"
print(class_name, type_)

# See all keywords:
import keyword
print("Reserved keywords:", keyword.kwlist)


# Rule 8: No length limit, but keep readable.
this_is_a_very_long_but_valid_identifier_name = "ok"
print(this_is_a_very_long_but_valid_identifier_name)


# Rule 9: Unicode letters allowed (Python 3), but stick to ASCII for team code.
naïve = "works but avoid"
π = 3.14
print(naïve, π)


# Rule 10: PEP 8 naming convention (style, not syntax):
#   variables, functions  -> snake_case        (retry_count, get_user)
#   constants             -> UPPER_SNAKE_CASE  (MAX_RETRY, BASE_URL)
#   classes               -> PascalCase        (LoginPage, UserService)
#   private               -> _leading_underscore
#   dunder / magic        -> __name__          (don't invent your own)
MAX_RETRY = 3
BASE_URL = "https://api.thetestingacademy.com"
