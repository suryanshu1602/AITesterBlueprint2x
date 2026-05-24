# Naming case conventions / "case styles" used in code.
# Python (PEP 8) prefers some over others. Other languages prefer different ones.
# Below: name -> example -> where used.


# 1. lowercase  (flatcase)
# All lowercase, no separator. Hard to read for multi-word.
# Used for: Python module/package names, HTML tags.
name = "pramod"
username = "pramod"
print(name, username)


# 2. UPPERCASE
# All caps, no separator. Hard to read for multi-word.
# Used for: single-word constants in some old code.
PI = 3.14
DEBUG = True
print(PI, DEBUG)


# 3. snake_case
# Lowercase words joined by underscore. Python default for vars + functions.
# Used for: Python variables, functions, methods, modules, DB columns.
first_name = "Pramod"
retry_count = 3
def get_user_name():
    return "Pramod"
print(first_name, retry_count, get_user_name())


# 4. SCREAMING_SNAKE_CASE  (a.k.a. UPPER_SNAKE_CASE / MACRO_CASE)
# Uppercase words joined by underscore. Python convention for constants.
# Used for: Python constants, env vars, C/C++ macros.
MAX_RETRY = 3
BASE_URL = "https://api.thetestingacademy.com"
DATABASE_URL = "postgres://localhost:5432"
print(MAX_RETRY, BASE_URL, DATABASE_URL)


# 5. camelCase  (a.k.a. lowerCamelCase / dromedaryCase)
# First word lowercase, subsequent words capitalized. No separator.
# Used for: JavaScript, Java, C# vars/methods. NOT idiomatic in Python.
firstName = "Pramod"          # works in Python but breaks PEP 8
retryCount = 3
def getUserName():            # also works but non-Pythonic
    return "Pramod"
print(firstName, retryCount, getUserName())


# 6. PascalCase  (a.k.a. UpperCamelCase / StudlyCase)
# Every word capitalized including first. No separator.
# Used for: class names (Python, Java, C#), C# methods, React components, types.
class LoginPage:
    pass
class UserService:
    pass
class APIClient:              # acronyms: PEP 8 keeps them all-caps
    pass
print(LoginPage(), UserService(), APIClient())


# 7. kebab-case  (a.k.a. dash-case / lisp-case / spinal-case)
# Lowercase words joined by hyphen. INVALID as Python identifier (- = minus).
# Used for: URLs, CSS classes, HTML attributes, CLI flags, npm packages.
# user-name = "bad"           # SyntaxError in Python
url_slug = "my-blog-post"     # store the value, not as identifier
css_class = "btn-primary"
print(url_slug, css_class)


# 8. SCREAMING-KEBAB-CASE  (a.k.a. TRAIN-CASE / COBOL-CASE)
# Uppercase words joined by hyphen. INVALID in Python.
# Used for: HTTP headers (Content-Type, X-Request-Id).
http_header = "Content-Type"
print(http_header)


# 9. Title Case
# Each word capitalized, separated by spaces. Not a code identifier — text style.
# Used for: book titles, headings, UI labels.
heading = "The Testing Academy Blueprint"
print(heading)


# 10. Sentence case
# First word capitalized, rest lowercase. Text style, not code.
# Used for: UI sentences, error messages.
error = "Invalid email address"
print(error)


# 11. dot.case
# Lowercase words joined by dot. Used for config keys, namespaces.
# In Python, dot means attribute access, so not a single identifier.
config_key = "database.connection.timeout"
print(config_key)


# 12. path/case  (a.k.a. slash case)
# Words joined by slash. File paths, URL paths.
file_path = "src/utils/string_helpers.py"
print(file_path)


# 13. Hungarian notation
# Prefix indicates type. Old Microsoft / VB / C style. Discouraged in Python.
# strName, iCount, bIsValid, arrUsers
strName = "Pramod"            # don't do this in Python
iCount = 3
bIsValid = True
print(strName, iCount, bIsValid)


# 14. _leading_underscore   -> "private/internal" by convention (Python).
# 15. trailing_underscore_  -> avoid clash with keyword: class_, type_, id_.
# 16. __double_leading      -> name-mangled inside a class.
# 17. __dunder__            -> reserved for Python (__init__, __name__). Don't invent.
_private = "internal use"
class_ = "Selenium"
class Demo:
    def __init__(self):
        self.__mangled = "renamed to _Demo__mangled"
print(_private, class_, Demo().__dict__)


# Quick reference table:
# style                    example                used for
# -----------------------  ---------------------  ---------------------------
# lowercase                username               Python modules, HTML tags
# UPPERCASE                PI                     single-word constants
# snake_case               first_name             Python vars/functions
# SCREAMING_SNAKE_CASE     MAX_RETRY              Python constants, env vars
# camelCase                firstName              JS/Java vars (not Python)
# PascalCase               LoginPage              classes, React components
# kebab-case               my-blog-post           URLs, CSS, CLI flags
# SCREAMING-KEBAB-CASE     Content-Type           HTTP headers
# Title Case               Hello World            headings (text only)
# Sentence case            Hello world            UI text (text only)
# dot.case                 db.conn.timeout        config keys
# path/case                src/utils/file.py      file paths
# Hungarian                strName, iCount        legacy MS code, avoid
