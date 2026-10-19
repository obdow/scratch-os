# The Whisker language

Whisker is the programming language of ScratchOS. It looks like Lua, and
most small Lua programs run with few changes, but it is a separate language
with its own rules. This file is the complete reference for the language
itself: how source text is split into tokens, the types of values, variables
and scope, expressions, statements, functions, tables and errors. It ends
with the hard limits, a list of every difference from Lua, and the known
issues. The built-in functions are described in [stdlib.md](stdlib.md) and
[system.md](system.md).

Every example in this file was run on ScratchOS. When an example has an
output block, that is exactly what the program printed (standard output
first, then standard error).

* [Lexical structure](#lexical-structure)
* [Values and types](#values-and-types)
* [Variables and scope](#variables-and-scope)
* [Expressions](#expressions)
* [Statements](#statements)
* [Functions](#functions)
* [Tables](#tables)
* [Errors](#errors)
* [Limits](#limits)
* [Differences from Lua](#differences-from-lua)
* [Known issues](#known-issues)

## Lexical structure

A Whisker program is plain text. The compiler first splits it into tokens:
names, keywords, numbers, strings and operators. Spaces, tabs, carriage
returns and newlines separate tokens and are otherwise ignored.

### Character set

ScratchOS uses code page 437 (CP437), the character set of the original IBM
PC. A string can hold any of its 256 characters, including box-drawing
characters such as `├──┤` and accented letters such as `é`. Outside strings
and comments, only ASCII letters, digits, `_`, the operator characters and
white space are allowed. Anything else is a compile error:

```lua
local function try(src) local f, err = load(src) print(err) end
try("é = 1")
```

```output
line 1: unexpected character 'é'
```

Many examples in this file show compile errors with a small helper,
`try`. It calls [`load`](stdlib.md#load), which compiles a string and
returns `nil` and the error message instead of stopping the program.

### Comments

A comment starts with `--` and runs to the end of the line. A block comment
starts with `--[[` and ends at the next `]]`, so it can span lines. Block
comments do not nest, and there are no "levels" like Lua's `--[==[`: that
form is just a line comment.

```lua
-- a line comment
--[[ a block comment
     over two lines ]] print("after the block")
--[==[ this is only a line comment
print("visible")
--[[ outer --[[ inner ]] print("not nested") -- ]]
```

```output
after the block
visible
not nested
```

A line comment that starts with `--@caps` declares the capabilities the
program needs (see [system.md](system.md)). There is no `#!` line: a file
whose first line starts with `#` does not compile.

### Names

A name (identifier) starts with an ASCII letter or `_`, followed by any
number of letters, digits and `_`. Names are case-sensitive: `count`,
`Count` and `COUNT` are three different variables. Keywords are
case-sensitive too, so `IF` and `End` are ordinary names.

```lua
IF = 1
local End = 2
local count, Count = "lower", "upper"
print(IF, End, count, Count)
```

```output
1       2       lower   upper
```

### Keywords

These 22 words are reserved and cannot be used as names:

```
and       break     continue  do        else      elseif
end       false     for       function  if        in
local     nil       not       or        repeat    return
then      true      until     while
```

`continue` is a Whisker addition. `goto` is not a keyword: it is an
ordinary name (which is why `term.goto` works), and there are no labels.

### Numbers

A number literal is a decimal number with an optional fraction and
exponent, or a hexadecimal integer.

| Form | Examples | Value |
|---|---|---|
| integer | `42`, `007` | 42, 7 |
| fraction | `3.25`, `.5`, `3.` | 3.25, 0.5, 3 |
| exponent | `1e3`, `2E2`, `5e+2`, `1.5e-2` | 1000, 200, 500, 0.015 |
| hexadecimal | `0x10`, `0xff`, `0XAbC` | 16, 255, 2748 |

Hex digits may be upper or lower case. Hex literals have no fraction or
exponent. There is no separate integer type (see [Numbers](#numbers-1)).

```lua
print(42, 3.25, .5, 3., 1e3, 2E2, 5e+2, 1.5e-2)
print(0x10, 0xff, 0XAbC)
```

```output
42      3.25    0.5     3       1000    200     500     0.015
16      255     2748
```

A number is read greedily: digits and dots are collected together. So
`1..2` is one malformed number, not `1 .. 2`. Malformed numbers (such as
`1..2`, `1.2.3` or `1e`) are not reported as errors; they silently become 0.
Put spaces around `..` after a number:

```lua
print(1 .. 2)
print(1..2)
```

```output
12
0
```

### Strings

A string literal is written between double quotes `"..."` or single quotes
`'...'`. Inside it, a backslash starts an escape sequence:

| Escape | Meaning |
|---|---|
| `\n` | newline (code 10) |
| `\t` | tab (code 9) |
| `\r` | carriage return (code 13) |
| `\e` | escape (code 27), used for [ANSI colour codes](terminal.md) |
| `\\` | backslash |
| `\"` | double quote |
| `\'` | single quote |
| `\xHH` | the character with hex code `HH` (exactly two hex digits) |
| `\ddd` | the character with decimal code `ddd` (one to three digits; the code is taken modulo 256) |
| `\` + newline | a newline (the string continues on the next line) |
| `\0` | nothing (the empty string); see [Known issues](#known-issues) |
| `\` + any other character | that character itself (`\q` is `q`, `\a` is `a`) |

Code 0 has no character in ScratchOS, so `"\0"` and `"\256"` add nothing.
A string literal cannot contain a raw newline; that is the compile error
`unfinished string`.

```lua
local function try(src) local f, err = load(src) print(err) end
print("tab:\tend", "\65\66\67", "\x41\x4a", "back\\slash", 'it\'s', "\q")
print(#"\0", #"\1", #"\255", "\1000")
print("one\
two")
try("x = 'abc\n'")
```

```output
tab:    end     ABC     AJ      back\slash      it's    q
0       1       1       d0
one
two
line 1: unfinished string
```

A *long string* is written between `[[` and `]]`. It can span lines, and
escapes are not processed in it. A newline directly after the opening `[[`
is skipped. A long string cannot contain `]]`. Only this level-0 form
exists: `[==[ ... ]==]` is a syntax error.

```lua
local s = [[
first line
C:\no\escapes]]
print(s)
print(#[[ab]])
local f, err = load("x = [==[a]==]")
print(err)
```

```output
first line
C:\no\escapes
2
line 1: unexpected symbol near '['
```

### Operators and punctuation

```
+   -   *   /   //  %   ^   #   ..
==  ~=  !=  <   <=  >   >=  =
(   )   {   }   [   ]   ;   :   ,   .   ...
```

`!=` is another spelling of `~=`. `...` is only allowed in a parameter list
(see [Parameters](#parameters-and-arguments)). There are no bitwise
operators: `&`, `|`, `~` on its own, `<<`, `>>` and `!` on its own are
compile errors.

```lua
local function try(src) local f, err = load(src) print(err) end
print(1 != 2, 1 ~= 1)
try("x = 5 & 3")
```

```output
true    false
line 1: unexpected character '&'
```

### Statements, lines and semicolons

Line breaks have no meaning: several statements can share a line, and one
statement can span several lines. A semicolon after a statement is allowed
and ignored, and so is an empty statement `;`.

```lua
local a = 1 local b = 2 print(a + b)
print(1); print(2);;
local total = a +
  b
print(total)
```

```output
3
1
2
3
```

Because line breaks are ignored, a line that starts with `(` continues the
previous expression. Here `print` and `(x)` join into the call `print(x)`,
and its result (`nil`) is then called with `"parens"`. The whole thing is
one statement, which starts on line 1:

```lua
local x = print
(x)("parens")
```

```output
nil
prog.wsk:1: attempt to call a nil value
```

## Values and types

Every value has one of these types. [`type(v)`](stdlib.md#type) returns the
type name as a string.

| Type | Values | `type()` |
|---|---|---|
| nil | `nil` | `"nil"` |
| boolean | `true`, `false` | `"boolean"` |
| number | double-precision floating point | `"number"` |
| string | text in CP437 | `"string"` |
| table | a reference to a table | `"table"` |
| function | a Whisker function or a built-in function | `"function"` |

```lua
print(type(nil), type(true), type(1), type("s"))
print(type({}), type(print), type(function() end))
```

```output
nil     boolean number  string
table   function        function
```

There are no userdata, threads (coroutines) or metatables.

### nil and booleans

`nil` means "no value". Unassigned variables, missing table fields and
missing arguments are `nil`. The booleans are `true` and `false`.

**Truthiness.** Conditions (in `if`, `while`, `repeat`, `and`, `or` and
`not`) treat `nil` and `false` as false. Every other value is true,
including `0` and the empty string `""`.

```lua
if 0 then print("0 is true") end
if "" then print("the empty string is true") end
if not nil then print("nil is false") end
```

```output
0 is true
the empty string is true
nil is false
```

### Numbers

All numbers are IEEE double-precision floats. There is no separate integer
type: `3` and `3.0` are the same value, and `7 / 2` is `3.5`. Integers are
exact up to 2^53 (9007199254740992).

`print`, `tostring` and `..` format numbers like this:

* A whole number below 10^15 in size prints without a decimal point: `3`,
  `-42`.
* Other numbers print with up to 14 significant digits: `1/3` prints as
  `0.33333333333333`, and `0.1 + 0.2` prints as `0.3`.
* Very large and very small numbers use JavaScript's exponent form:
  `1e+21`, `1e-7`.
* Infinity prints as `inf` or `-inf`.

```lua
print(7 / 2, 6 / 2, 1 / 3, 0.1 + 0.2, 100 / 7, -0.5)
print(1e15, 1e21, 1e-4, 1e-7, 1 / 0, -1 / 0)
```

```output
3.5     3       0.33333333333333        0.3     14.285714285714 -0.5
1000000000000000        1e+21   0.0001  1e-7    inf     -inf
```

Dividing by zero gives `inf` or `-inf`. `0/0`, `x % 0` and other undefined
results give NaN ("not a number"), which ScratchOS handles badly; see
[Known issues](#known-issues). `math.huge` is infinity and `math.pi` is π
(see [stdlib.md](stdlib.md)).

### Strings

A string is a sequence of CP437 characters. Strings are immutable: every
string operation makes a new string. There is no fixed maximum length;
strings are limited only by memory. `#s` is the number of characters (each
CP437 character counts as one, so `#"é"` is 1). A character outside CP437
can still be stored, but [`string.byte`](stdlib.md#stringbyte) reports it
as 63 (`?`).

```lua
print(#"é", string.byte("é"), #"├──┤")
local s = "abc"
local t = s .. "d"
print(s, t)
```

```output
1       130     4
abc     abcd
```

Strings have methods: `s:upper()` is `string.upper(s)`, and the same works
for every `string.*` function (see [Method calls](#method-calls-and-self)).

### Tables

A table is a collection of key/value pairs. It is the only data structure:
it serves as an array, a dictionary, a record and an object. Tables are
values with *reference* semantics: assigning a table to another variable
does not copy it. See [Tables](#tables).

### Functions

Functions are values: they can be stored in variables and tables, passed as
arguments and returned. There are two kinds, both with type `"function"`:
functions written in Whisker, and built-in functions such as `print` and
`string.upper`. `tostring` shows the difference: a Whisker function prints
as `function: 0x...` and a built-in as `builtin: name`.

```lua
print(tostring(print), tostring(string.upper))
local up = string.upper
print(up("works"))
```

```output
builtin: print  builtin: string.upper
WORKS
```

## Variables and scope

There are three kinds of variables: globals, locals and table fields.

### Globals

Assigning to a name that is not a local creates or changes a *global*
variable. Reading a global that was never assigned gives `nil`. Each
running program has its own globals; they are shared with code loaded by
[`load`](stdlib.md#load) and [`require`](libraries.md) in the same program,
but never with other programs. The global `arg` holds the command-line
arguments (see [getting-started.md](getting-started.md)).

```lua
Score = 10
Score = Score + 5
print(Score, score, Undefined)
```

```output
15      nil     nil
```

**Built-in names.** The names of the built-in functions (`print`,
`tostring`, ...) and modules (`string`, `math`, `table`, `os`, `io`, `fs`,
`proc`, `term`, `gui`, `gfx`, `sys`, `image`, `net`, `utf8`) are resolved
by the compiler. A module name is not a value: `local s = string` and
`pairs(string)` are compile errors, and so is an unknown function such as
`string.nope`. Built-in *functions* are values (`local up = string.upper`
works).

```lua
local function try(src) local f, err = load(src) print(err) end
try("local s = string")
try("string.nope(1)")
```

```output
line 1: module 'string' used as a value near '<eof>'
line 1: unknown function 'string.nope' near '('
```

You can replace a built-in with your own global or local of the same name.
A global replaces it only for code that comes *after* the assignment in the
source, because the compiler decides what each name means as it reads the
program from top to bottom:

```lua
print("one")
function print(x) io.write("[", x, "]\n") end
print("two")
```

```output
one
[two]
```

A local with a module's name hides the whole module, but string methods
still use the real `string` functions:

```lua
local string = {len = function() return "mine" end}
print(string.len("abc"), ("abc"):len())
```

```output
mine    3
```

### Locals and blocks

`local` declares local variables. A local is visible from the statement
after its declaration to the end of the innermost enclosing *block*. The
blocks are: the whole program (the main chunk), a function body, the body
of `do`, `while`, `for` and `repeat`, and each branch of `if`.

```lua
local x = 10
local function f()
  local x = 20
  do
    local x = 30
    print(x)
  end
  print(x)
end
f()
print(x)
do local inner = 1 end
print(inner)
```

```output
30
20
10
nil
```

`local a, b, c = ...` declares several locals at once. Without `= ...`
they all start as `nil`. The new locals become visible only after the whole
statement, so `local x = x` reads the *outer* `x`:

```lua
local x = 1
local x = x + 1
print(x)
local a, b, c = 1, 2
print(a, b, c)
local d
print(d)
```

```output
2
1       2       nil
nil
```

Shadowing (declaring a local with the same name as a visible variable) is
always allowed.

### What a function can see

Whisker has no closures. A function body can use:

1. its own parameters and locals,
2. globals,
3. *top-level locals*: locals of the main chunk that were declared before
   the function, at any depth of nesting inside the main chunk (even inside
   a `do`, `if` or loop block of the main chunk).

It can **not** use the parameters or locals of an enclosing function. The
compiler rejects that:

```lua
local function try(src) local f, err = load(src) print(err) end
try("local function outer() local n = 1; local function inner() return n end return inner end")
```

```output
line 1: cannot use local 'n' of an enclosing function (no closures: use a top-level local or global) near 'end'
```

Top-level locals work from any function, including functions nested inside
other functions:

```lua
local total = 0
local function outer()
  local function inner() total = total + 1 end
  inner()
  inner()
end
outer()
print(total)
```

```output
2
```

A function does not capture values: it reads the variable itself, when it
runs. A top-level local declared inside a block keeps its last value after
the block ends, and every function made in a loop sees the loop variable's
*current* value. After a numeric loop, that is one step past the end:

```lua
do
  local secret = 42
  function get() return secret end
end
print(get())
local fs = {}
for i = 1, 3 do fs[i] = function() return i end end
print(fs[1](), fs[2](), fs[3]())
```

```output
42
4       4       4
```

A top-level local that is declared *after* a function is not visible to
it; the name then means a global:

```lua
local function f() return x end
local x = 10
print(f())
```

```output
nil
```

Things this rule forbids, and what to do instead:

* **A local function that calls itself inside another function.** The
  inner function cannot see its own name, because that name is a local of
  the outer function. Make it a top-level local function or a global.
* **`self` in a nested function.** `self` is a parameter of the method, so
  a helper function inside the method cannot use it. Pass it as an
  argument.
* **Locals of a loaded chunk or module.** For [`load`](stdlib.md#load) and
  [`require`](libraries.md), the chunk is compiled like a function body, so
  functions inside it cannot use its locals. Libraries keep their state in
  globals (the `yarn` library uses the global `_yarn`).

```lua
local function try(src) local f, err = load(src) print(err) end
try("local function outer() local function rec(k) if k > 0 then return rec(k-1) end return 0 end return rec(3) end")
try("local M = {} function M.f() return M end return M")
try("local obj = {} function obj:get() local function h() return self end return h() end")
```

```output
line 1: cannot use local 'rec' of an enclosing function (no closures: use a top-level local or global) near '('
line 1: cannot use local 'M' of an enclosing function (no closures: use a top-level local or global) near 'end'
line 1: cannot use local 'self' of an enclosing function (no closures: use a top-level local or global) near 'end'
```

### Assignment

`target = value` assigns one value. The target is a local, a global, a
table field `t.name` or an indexed element `t[key]`.

A *multiple assignment* `a, b, c = x, y, z` assigns several. If there are
more values than targets, the extra values are evaluated and then dropped.
If there are fewer, the missing ones are `nil` (unless the last value is a
function call, see [Multiple results](#multiple-results)).

```lua
local a, b, c = 1, 2
a, b = b, a
print(a, b, c)
local d, e = 1, 2, 3
print(d, e)
```

```output
2       1       nil
1       2
```

Order of evaluation: first the table and key parts of the targets, from
left to right; then all values, from left to right; then the stores, from
right to left. So `i, t[i] = i + 1, 20` uses the *old* `i` as the key:

```lua
local function v(n) io.write("v", n, " ") return n end
local t = {}
t[v(1)], t[v(2)] = v(3), v(4)
print()
local i = 1
i, t[i] = i + 1, 20
print(i, t[1])
```

```output
v1 v2 v3 v4
2       20
```

## Expressions

### Operator precedence

From lowest to highest priority:

| Priority | Operators | Associativity |
|---|---|---|
| 1 | `or` | left |
| 2 | `and` | left |
| 3 | `<` `>` `<=` `>=` `~=` `!=` `==` | left |
| 4 | `..` | right |
| 5 | `+` `-` | left |
| 6 | `*` `/` `//` `%` | left |
| 7 | `not` `#` `-` (unary) | prefix |
| 8 | `^` | right |

Parentheses override priorities. Because `^` binds tighter than unary minus,
`-3 ^ 2` is `-(3 ^ 2)`. A unary operator is allowed right after `^`, as in
`2 ^ -1`.

```lua
print(2 + 3 * 4, (2 + 3) * 4, 2 * 3 ^ 2, -3 ^ 2, 2 ^ -1)
print(10 - 4 - 3, 64 / 4 / 2, 2 ^ 3 ^ 2, 1 .. 2 .. 3)
print("a" .. 1 + 2, not nil == true, #"abc" + 1, - - 3)
print(1 + 1 == 2 and "yes" or "no")
```

```output
14      20      18      -9      0.5
3       8       512     123
a3      true    4       3
yes
```

Comparisons are left-associative, so `1 < 2 < 3` compares `true < 3` and
fails:

```lua
print(1 < 2 < 3)
```

```output
prog.wsk:1: attempt to compare boolean with number
```

Operands are evaluated from left to right.

### Arithmetic

| Operator | Meaning |
|---|---|
| `a + b`, `a - b`, `a * b` | addition, subtraction, multiplication |
| `a / b` | division (always gives a fractional result when needed: `7 / 2` is 3.5) |
| `a // b` | floor division: `math.floor(a / b)` |
| `a % b` | modulo: `a - math.floor(a / b) * b`; the result has the sign of `b` |
| `a ^ b` | power |
| `-a` | negation |

All of them work on fractional numbers too.

```lua
print(7 // 2, -7 // 2, 7 // -2, 7.5 // 2, 1 // 0.3)
print(7 % 3, -7 % 3, 7 % -3, -7 % -3, 5.5 % 2, -5.5 % 2)
print(2 ^ 10, 2 ^ 0.5, (-2) ^ 2, 0 ^ 0)
print(1 / 0, -1 / 0, 5 // 0, -5 // 0)
```

```output
3       -4      -4      3       3
1       2       -2      -1      1.5     0.5
1024    1.4142135623731 4       1
inf     -inf    inf     -inf
```

For `^`, a whole-number exponent between -64 and 64 is computed by repeated
multiplication, so it is exact. Other exponents use `exp(b * log(a))`; a
negative base with a fractional exponent gives NaN.

### Strings in arithmetic

If an operand of an arithmetic operator (including unary `-`) is a string,
it is converted to a number when it looks like a *decimal* number after
removing surrounding spaces, tabs and newlines: digits with an optional
sign, decimal point and exponent. Hexadecimal strings such as `"0x10"` are
not converted (but [`tonumber("0x10")`](stdlib.md#tonumber) is 16). Any
other string is an error.

```lua
print("10" + 5, "3" * "4", " 7 " + 1, "1e2" + 0, -"2", ".5" + 0)
print("0x10" + 0)
```

```output
15      12      8       100     -2      0.5
prog.wsk:2: attempt to perform arithmetic on a string value
```

Arithmetic on `nil`, booleans, tables and functions is an error:
`attempt to perform arithmetic on a nil value`.

### Concatenation

`a .. b` joins two strings. Numbers are converted to strings first, using
the same format as `print`. Any other type is an error; use
[`tostring`](stdlib.md#tostring) for those.

```lua
print("x" .. 1, 10 .. 20, 1.5 .. "", (0.1 + 0.2) .. "", 1e21 .. "")
print("flag: " .. tostring(true))
print("flag: " .. true)
```

```output
x1      1020    1.5     0.3     1e+21
flag: true
prog.wsk:3: attempt to concatenate a boolean value
```

### Comparison

`==` and `~=` (or `!=`) work on any two values and never convert types:

* Values of different types are never equal, so `1 == "1"` is `false`.
* Strings are equal when they have exactly the same characters; case
  matters.
* Tables are equal only when they are the same table (identity).
* Functions are equal when they are the same function. Since there are no
  closures, every evaluation of the same `function ... end` expression
  gives the same function value.

```lua
print(1 == 1.0, 1 == "1", "abc" == "ABC", nil == false)
local t, u = {}, {}
print(t == t, t == u, print == print)
local fs = {}
for i = 1, 2 do fs[i] = function() end end
print(fs[1] == fs[2], function() end == function() end)
```

```output
true    false   false   false
true    false   true
true    false
```

`<`, `<=`, `>` and `>=` compare two numbers by value, or two strings
character by character by their CP437 codes (so case matters: all
upper-case letters come before lower-case ones, and a prefix comes before
the longer string). Any other pair of types is an error; strings are never
converted to numbers here.

```lua
print("a" < "b", "B" < "a", "abc" < "abd", "ab" < "abc", "" < "a", "10" < "9")
print(1 < "2")
```

```output
true    true    true    true    true    true
prog.wsk:2: attempt to compare number with string
```

### Length

`#s` is the number of characters in a string. `#t` is the length of a
table's array part (see [Arrays and #](#arrays-and-)). `#` on any other
type is an error.

```lua
print(#"hello", #"", #{1, 2, 3}, #{x = 1})
print(#nil)
```

```output
5       0       3       0
prog.wsk:2: attempt to get length of a nil value
```

### Logical operators

`a and b` gives `a` if `a` is false or `nil`, otherwise `b`.
`a or b` gives `a` if `a` is true (not `false` or `nil`), otherwise `b`.
Both *short-circuit*: the right side is only evaluated when needed. So
they return one of their operands, not always a boolean. `not a` always
returns a boolean.

```lua
print(nil or "default", false or nil, 0 or 1, 1 and 2, nil and 1)
print(false and error("not evaluated"), 1 or error("not evaluated"))
print(not 0, not "", not nil, not false)
local n = 5
print(n > 3 and "big" or "small")
```

```output
default nil     0       2       nil
false   1
false   false   true    true
big
```

### Table constructors

`{ ... }` makes a new table. Inside the braces, fields are separated by
`,` or `;`, and a trailing separator is allowed. There are three kinds of
field:

| Field | Meaning |
|---|---|
| `expr` | positional: appended at the next array index (1, 2, 3, ...) |
| `name = expr` | the string key `"name"` |
| `[expr] = expr` | any key |

A positional `nil` is skipped, so the next value takes its place.
Positional values are always appended after the current end of the array,
even when an `[n] = ...` field came first.

```lua
local t = {10, 20; x = 1, ["two words"] = 2, [5] = "five",}
print(#t, t[1], t[2], t.x, t["two words"], t[5])
local holes = {1, nil, 3}
print(#holes, holes[2], holes[3])
local mixed = {[1] = "a", "b"}
print(mixed[1], mixed[2])
```

```output
2       10      20      1       2       five
2       3       nil
a       b
```

A function call in a positional field contributes only its first result
(see [Multiple results](#multiple-results)).

### Function calls

A call is an expression. Its forms are described under
[Calling functions](#calling-functions).

## Statements

### if

```lua
local x = 5
if x > 10 then
  print("big")
elseif x > 3 then
  print("medium")
else
  print("small")
end
```

```output
medium
```

There can be any number of `elseif` branches; `else` is optional. The
condition can be any value (see truthiness under
[nil and booleans](#nil-and-booleans)).

### while

`while cond do ... end` repeats the body while the condition is true. The
condition is tested before each pass.

```lua
local i = 1
while i <= 3 do
  io.write(i, " ")
  i = i + 1
end
print()
```

```output
1 2 3
```

### repeat ... until

`repeat ... until cond` runs the body, then tests the condition, and stops
when it is true. The body runs at least once. Locals declared in the body
are visible in the condition.

```lua
local n = 0
repeat
  local done = n >= 3
  n = n + 1
until done
print(n)
```

```output
4
```

### Numeric for

`for v = start, limit, step do ... end` counts `v` from `start` towards
`limit` in steps of `step`. `step` defaults to 1. The three values are
evaluated once, before the loop starts, and must be numbers (strings are
not converted). The loop runs while `v <= limit` when `step` is positive,
and while `v >= limit` when `step` is zero or negative.

```lua
for i = 1, 3 do io.write(i, " ") end print()
for i = 3, 1, -1 do io.write(i, " ") end print()
for i = 0, 1, 0.25 do io.write(i, " ") end print()
for i = 1, 0 do io.write("never") end print("empty")
local n = 3
for i = 1, n do n = 10 io.write(i, " ") end print()
```

```output
1 2 3
3 2 1
0 0.25 0.5 0.75 1
empty
1 2 3
```

The loop variable is a local of the loop body; it does not exist after the
loop. Unlike Lua, it is the real counter: assigning to it changes the
following passes.

```lua
for i = 1, 10 do
  io.write(i, " ")
  i = i + 2
end
print()
local i = 99
for i = 1, 2 do end
print(i)
```

```output
1 4 7 10
99
```

Fractional steps add up rounding errors, as in any language with floats.
A step of 0 is not an error: the loop never runs when `start < limit`, and
runs forever otherwise.

```lua
for i = 1, "3" do end
```

```output
prog.wsk:1: 'for' values must be numbers
```

### Generic for

The generic `for` walks through a table. Only two forms exist, and `pairs`
and `ipairs` are part of the syntax here, not functions:

```
for k, v in pairs(t) do ... end     -- every key/value pair
for i, v in ipairs(t) do ... end    -- t[1], t[2], ... up to the first nil
```

The second variable may be left out (`for k in pairs(t) do`). Any other
form is a compile error, and the expression must be a table at run time.

```lua
local function try(src) local f, err = load(src) print(err) end
local t = {10, 20, 30, x = 1, y = 2}
for k, v in pairs(t) do io.write(k, "=", v, " ") end print()
for i, v in ipairs(t) do io.write(i, "=", v, " ") end print()
for k in pairs({a = 1}) do print(k) end
try("for k in next, t do end")
for k, v in pairs("abc") do end
```

```output
1=10 2=20 3=30 x=1 y=2
1=10 2=20 3=30
a
line 1: for-in supports pairs(t) and ipairs(t) only near ','
prog.wsk:7: bad argument to 'for' (table expected, got string)
```

`pairs` visits the array part first, in order, then the other keys in the
order they were added (see [Iteration order](#iteration-order)). There are
no custom iterators: `pairs`, `ipairs` and `next` do not exist as functions,
so `pairs(t)` outside a `for` calls the global `pairs`, which is `nil`.

```lua
print(pairs, next)
local p = pairs({})
```

```output
nil     nil
prog.wsk:2: attempt to call a nil value
```

To iterate in another way, write a `while` loop, or get the keys with
[`table.keys`](stdlib.md#tablekeys).

### break and continue

`break` leaves the innermost loop. `continue` skips the rest of the current
pass: in `while` it goes to the condition, in `for` to the next value, and
in `repeat` to the `until` test. Both are compile errors outside a loop,
and a function body inside a loop counts as outside.

```lua
local function try(src) local f, err = load(src) print(err) end
for i = 1, 6 do
  if i == 2 then continue end
  if i == 5 then break end
  io.write(i, " ")
end
print()
local k = 0
repeat
  k = k + 1
  if k < 3 then continue end
  io.write("k=", k, " ")
until k >= 4
print()
try("break")
try("while true do local f = function() break end end")
```

```output
1 3 4
k=3 k=4
line 1: break outside a loop near '<eof>'
line 1: break outside a loop near 'end'
```

### return

`return` ends the current function and gives back zero or more values
(`return`, `return x`, `return a, b`). It must be the last statement of
its block (a `;` may follow). To return from the middle of a block, wrap it
as `do return end`.

```lua
local function try(src) local f, err = load(src) print(err) end
local function first_negative(t)
  for i, v in ipairs(t) do
    if v < 0 then return i end
  end
  return nil
end
print(first_negative({3, 1, -4, 1}))
try("return 1 print(2)")
```

```output
3
line 1: 'end' expected after return near 'print'
```

A `return` in the main chunk ends the program. If the first returned value
is a number, it is the program's exit code; otherwise the exit code is 0.
See [Exit codes](#uncaught-errors-and-exit-codes).

### do ... end

`do ... end` makes a block, which limits the scope of the locals declared
in it.

```lua
local x = 1
do
  local x = 2
  print(x)
end
print(x)
```

```output
2
1
```

### Expression statements

The only expression that can stand alone as a statement is a function
call. Its results are discarded. Anything else is a `syntax error`, and
assigning to something that is not a variable or field is
`cannot assign to this expression`.

```lua
local function try(src) local f, err = load(src) print(err) end
try("x")
try("a.b")
try("f() = 1")
try("goto top")
```

```output
line 1: syntax error near '<eof>'
line 1: syntax error near '<eof>'
line 1: cannot assign to this expression near '<eof>'
line 1: syntax error near 'top'
```

## Functions

### Defining functions

A function is written `function (params) body end`. It is an expression,
so it can be assigned like any other value. The statement forms are
shorthands:

| Statement | Means |
|---|---|
| `function name(...) ... end` | `name = function(...) ... end` (a global, or a local if `name` is a visible local) |
| `local function name(...) ... end` | `local name; name = function(...) ... end`; the body can call `name` |
| `function a.b.c(...) ... end` | `a.b.c = function(...) ... end` |
| `function a.b:m(...) ... end` | `a.b.m = function(self, ...) ... end` |

```lua
function add(a, b) return a + b end
local function sub(a, b) return a - b end
local mul = function(a, b) return a * b end
local ops = {math = {}}
function ops.math.div(a, b) return a / b end
print(add(1, 2), sub(5, 3), mul(2, 4), ops.math.div(9, 3))
```

```output
3       2       8       3
```

In `function a.b.c()`, the tables `a` and `a.b` must exist already.

### Calling functions

| Form | Meaning |
|---|---|
| `f(a, b)` | ordinary call |
| `f"text"` or `f'text'` or `f[[text]]` | call with one string argument |
| `f{...}` | call with one new table as the argument |
| `obj:m(a, b)` | method call: `obj.m(obj, a, b)`, with `obj` evaluated once |
| `obj:m"text"`, `obj:m{...}` | method call with one string or table argument |

Calls can be chained: `f()()`, `f().field`, `f():method()`.

```lua
local function first(t) return t[1] end
print(first{5, 6}, type"x")
local function maker() return function() return "inner" end end
print(maker()())
```

```output
5       string
inner
```

Calling a value that is not a function is an error:

```lua
local x = 5
x()
```

```output
prog.wsk:2: attempt to call a number value
```

### Parameters and arguments

Parameters are locals of the function. Missing arguments are `nil`, and
extra arguments are evaluated and then dropped.

```lua
local function f(a, b, c) print(a, b, c) end
f(1)
f(1, 2, 3, 4)
```

```output
1       nil     nil
1       2       3
```

There are no varargs. If `...` appears in a parameter list, it declares
one ordinary parameter named `arg`, which receives one argument; `...` can
not be used in an expression. (Inside such a function, the local `arg`
hides the global `arg` with the command-line arguments.)

```lua
local function try(src) local f, err = load(src) print(err) end
local function g(a, ...) print(a, arg) end
g(1, 2, 3)
try("x = ...")
```

```output
1       2
line 1: unexpected symbol near '...'
```

### Multiple results

A function can return several values with `return a, b, c`. Unlike Lua,
these extra values survive in only one situation: when the call is the
**last** expression on the right of a `local` declaration or an
assignment, and there are more names on the left than expressions on the
right. Everywhere else a call gives exactly **one** value (its first
result, or `nil`):

* as an argument: `print(f())` prints one value;
* in `return f()`: only the first value is returned;
* in a table constructor: `{f()}` has one element;
* in parentheses: `(f())`;
* anywhere except last in a list: `local a, b = f(), 10`.

As a statement, a call's results are discarded.

```lua
local function two() return 1, 2 end
local function pass() return two() end
local a, b = two()
print(a, b)
local c, d = pass()
print(c, d)
print(two())
local t = {two(), two()}
print(#t)
local x, y, z = two(), 10
print(x, y, z)
local p, q, r = 5, two()
print(p, q, r)
local m, n = (two())
print(m, n)
```

```output
1       2
1       nil
1
2
1       10      nil
5       1       2
1       nil
```

To pass several results on, store them first: `local a, b = f() return a, b`.
The same rule applies to built-ins that return several values, such as
[`pcall`](stdlib.md#pcall) and [`unpack`](stdlib.md#unpack):
`print(pcall(f))` prints only `true` or `false`.

### Method calls and self

`obj:m(args)` calls `obj.m` with `obj` as the first argument. A function
defined with `function obj:m(params)` gets an extra first parameter named
`self`.

```lua
local counter = {n = 0}
function counter:add(k) self.n = self.n + k return self end
function counter.reset(self) self.n = 0 end
counter:add(5):add(2)
print(counter.n)
counter:reset()
print(counter.n)
```

```output
7
0
```

Strings have methods too: `s:name(...)` calls `string.name(s, ...)` for
any `string` function. Indexing a string with any other key gives `nil`.
Numbers and other types have no methods.

```lua
local s = "Hello"
print(s:upper(), s:len(), s:sub(2, 3), ("x"):rep(3), ("%d items"):format(3))
print(s[1], s.nope, s.upper)
local n = 5
print(n.x)
```

```output
HELLO   5       el      xxx     3 items
nil     nil     builtin: string.upper
prog.wsk:5: attempt to index a number value
```

### Recursion

A global function, or a `local function` in the main chunk, can call
itself. Each call uses one frame, and at most 200 frames can be active at
once (see [Limits](#limits)).

```lua
local function fact(n) if n <= 1 then return 1 end return n * fact(n - 1) end
function fib(n) if n < 2 then return n end return fib(n - 1) + fib(n - 2) end
print(fact(10), fib(15))
```

```output
3628800 610
```

A `local function` declared *inside another function* cannot call itself
(see [What a function can see](#what-a-function-can-see)). There is no tail
call optimization: `return f(x)` uses a new frame.

## Tables

### Keys

Any value except `nil` can be a key: numbers, strings, booleans, tables and
functions. Reading a missing key gives `nil`. Reading `t[nil]` gives `nil`;
writing it is an error.

`t.name` is shorthand for `t["name"]`, for keys that are valid names.

```lua
local t = {}
t.x = 1
t["key with spaces"] = 2
t[true] = "yes"
t[t] = "itself"
print(t.x, t["x"], t["key with spaces"], t[true], t[t], t.missing, t[nil])
t[nil] = 1
```

```output
1       1       2       yes     itself  nil     nil
prog.wsk:7: table index is nil
```

**String keys ignore case.** `t.Name`, `t.name` and `t["NAME"]` are the
same field, however the key is written or computed. The key keeps the
spelling it had when it was first stored, and `pairs` returns that
spelling. String *comparison* with `==` is still case-sensitive.

```lua
local t = {}
t.Name = "a"
print(t.name, t.NAME, t["nAmE"])
local k = "KEY"
t[k] = 1
print(t.key)
t.name = "b"
for key, v in pairs(t) do print(key, v) end
```

```output
a       a       a
1
Name    b
KEY     1
```

**Numbers and strings are different keys.** `t[1]` and `t["1"]` are two
fields. A number key that is a whole number is the same key however it
was computed: `t[2]`, `t[2.0]` and `t[4 / 2]` are the same field.
Fractional keys work too.

```lua
local t = {"a", "b"}
t["1"] = "string one"
t[1.5] = "one and a half"
print(t[1], t["1"], t[1.0], t[3 - 1], t[1.5], t[3 / 2])
```

```output
a       string one      a       b       one and a half  one and a half
```

Two different strings that look like the same number and have the same
length can collide as keys; see [Known issues](#known-issues).

### Arrays and #

Each table has an *array part* that holds the keys 1, 2, ..., n, and a
*hash part* for every other key. `#t` is n, the size of the array part:

* Setting `t[n + 1]` grows the array part by one, and then moves any
  following keys (`n + 2`, ...) from the hash part into it.
* Setting a key further away (`t[n + 5]`) stores it in the hash part; it
  does not change `#t`.
* Setting an element inside the array to `nil` leaves a hole; `#t` does
  not change.
* Setting the last element to `nil` shrinks the array part, also past any
  holes before it.

```lua
local t = {1, 2, 3, 4}
t[2] = nil
print(#t, t[2])
t[4] = nil
print(#t)
t[3] = nil
print(#t)
local u = {}
u[1] = "a"
u[3] = "c"
print(#u)
u[2] = "b"
print(#u)
```

```output
4       nil
3
1
1
3
```

Keys 0 and negative numbers are ordinary hash keys. Use
[`table.insert`](stdlib.md#tableinsert) and
[`table.remove`](stdlib.md#tableremove) to add and remove array elements
without leaving holes.

### Iteration order

`pairs` returns the array part first, from 1 to `#t`, skipping holes. Then
it returns the hash part in the order the keys were added. Removing a key
moves the most recently added key into its place, which changes the order.
`ipairs` returns `t[1]`, `t[2]`, ... and stops at the first `nil`.

```lua
local t = {10, 20, 30}
t[5] = 50
t.x = "x"
t[2] = nil
for k, v in pairs(t) do io.write(k, "=", v, " ") end print()
for i, v in ipairs(t) do io.write(i, "=", v, " ") end print()
```

```output
1=10 3=30 5=50 x=x
1=10
```

Changing the value of an existing key during a `pairs` loop is fine.
Removing keys during a `pairs` loop can make the loop skip other keys (see
[Known issues](#known-issues)).

### References

Variables hold references to tables. Assigning or passing a table never
copies it; use [`table.copy`](stdlib.md#tablecopy) for a copy.

```lua
local a = {1, 2}
local b = a
b[1] = 99
print(a[1], a == b)
local function push(t, v) t[#t + 1] = v end
push(a, 3)
print(#b)
local n = {inner = {v = 1}}
n.inner.v = 2
print(n.inner.v)
```

```output
99      true
3
2
```

### Objects

There are no metatables, so there is no inheritance through `__index`.
Write a constructor function that builds a table and puts the methods in
it:

```lua
local Point = {}
function Point.new(x, y)
  local p = {x = x, y = y}
  p.move = Point.move
  p.str = Point.str
  return p
end
function Point:move(dx, dy)
  self.x = self.x + dx
  self.y = self.y + dy
end
function Point:str() return "(" .. self.x .. ", " .. self.y .. ")" end

local p = Point.new(1, 2)
p:move(3, 4)
print(p:str())
```

```output
(4, 6)
```

To share methods between "classes", copy the method fields from one table
into another in the constructor (a loop over `pairs` works).

## Errors

### Runtime errors

A runtime error stops the program, unless it happens inside
[`pcall`](stdlib.md#pcall). The message is printed in red on standard
error, in the form `file:line: message`. `file` is the program's file name
without its directory, and `line` is the line where the failing statement
starts.

```lua
print("before")
local t = nil
print(t.x)
print("never")
```

```output
before
prog.wsk:3: attempt to index a nil value
```

A statement that spans several lines reports its first line:

```lua
local x = 1 +
  nil
```

```output
prog.wsk:1: attempt to perform arithmetic on a nil value
```

### error, assert and pcall

[`error(msg)`](stdlib.md#error) raises an error. The message gets the
`file:line: ` prefix of the line where `error` was called. A value that is
not a string is converted with `tostring`. A second argument (Lua's error
level) is accepted and ignored.

[`assert(v [, msg])`](stdlib.md#assert) raises `msg` (default
`assertion failed!`) when `v` is `false` or `nil`, and otherwise returns `v`.

[`pcall(f, ...)`](stdlib.md#pcall) calls the Whisker function `f` with the
other arguments. If `f` finishes, `pcall` returns `true` followed by `f`'s
results. If an error happens, `pcall` returns `false` and the message (with
its prefix). `f` must be a Whisker function, not a built-in.

```lua
local ok, e = pcall(function() error("boom") end)
print(ok, e)
local ok2, a, b = pcall(function(x, y) return x + y, x * y end, 3, 4)
print(ok2, a, b)
local ok3, e3 = pcall(function() error("level", 2) end)
print(e3)
local ok4, e4 = pcall(function() assert(nil, "custom") end)
print(e4)
local ok5, e5 = pcall(function() error() end)
print(e5)
print(assert(5, "unused"))
```

```output
false   prog.wsk:1: boom
true    7       12
prog.wsk:5: level
prog.wsk:7: custom
prog.wsk:9: nil
5
```

Raising a caught message again adds a second prefix:

```lua
local ok, e = pcall(function()
  local ok2, e2 = pcall(function() error("inner") end)
  error(e2)
end)
print(e)
```

```output
prog.wsk:3: prog.wsk:2: inner
```

A common pattern is to check arguments with `error` and handle failures
with `pcall`:

```lua
local function check(v)
  if type(v) ~= "number" then error("number expected, got " .. type(v)) end
  return v + 1
end
local ok, e = pcall(check, "x")
print(ok, e)
local ok2, v2 = pcall(check, 1)
print(ok2, v2)
```

```output
false   prog.wsk:2: number expected, got string
true    2
```

**Warning:** at present `pcall` only works reliably for errors raised by
`error`, `assert`, built-in functions and calls (`attempt to call ...`,
`stack overflow`, `'for'` errors). Errors raised by an *operator* inside
the protected function (arithmetic, `..`, comparison, `#`, indexing a
non-table, `t[nil] = v`) are caught, but `pcall`'s results come back
wrong. See [Known issues](#known-issues). Until that is fixed, check values
before using operators on them, and raise your own error with `error`.

### Compile errors

When a program does not compile, it does not start at all. The message is
printed in red, with the full path of the file, the line number, what was
wrong, and the token where the compiler noticed it:

```
/home/user/bad.wsk: line 2: unexpected symbol near '='
```

[`load`](stdlib.md#load) returns `nil` and the same message without the
path. [`proc.run`](system.md) returns `nil` and `cannot start '...'`, and
the compile error goes to the standard error of the program that called
it.

```lua
fs.write("/tmp/bad.wsk", "print('hi')\nx = = 1\n")
local out, err = proc.run("run /tmp/bad.wsk")
print(out, err)
```

```output
nil     cannot start 'run /tmp/bad.wsk'
/tmp/bad.wsk: line 2: unexpected symbol near '='
```

### Uncaught errors and exit codes

A program's exit code is:

* the number given to [`exit(n)`](stdlib.md#exit) (`exit(true)` is 0 and
  `exit(false)` is 1);
* the first value of a `return` in the main chunk, if it is a number;
* 1 after an uncaught runtime error;
* otherwise 0.

```lua
fs.write("/tmp/r.wsk", "return 7")
fs.write("/tmp/x.wsk", "exit(3)")
fs.write("/tmp/s.wsk", "return 'text'")
fs.write("/tmp/e.wsk", "print('start')\nerror('oops')\n")
local o, c1 = proc.run("run /tmp/r.wsk")
local o, c2 = proc.run("run /tmp/x.wsk")
local o, c3 = proc.run("run /tmp/s.wsk")
local out, c4 = proc.run("run /tmp/e.wsk")
print(c1, c2, c3, c4, out)
```

```output
7       3       0       1       start

e.wsk:2: oops
```

### Common error messages

Runtime errors (shown after `file:line: `):

| Message | Cause |
|---|---|
| `attempt to perform arithmetic on a X value` | `+ - * / // % ^` or unary `-` on `nil`, a boolean, a table, a function, or a string that is not a decimal number |
| `attempt to concatenate a X value` | `..` with something that is not a string or number |
| `attempt to compare X with Y` | `<`, `<=`, `>`, `>=` on two values that are not both numbers or both strings |
| `attempt to get length of a X value` | `#` on something that is not a string or table |
| `attempt to index a X value` | `v.k`, `v[k]` or `v:m()` where `v` is not a table (or a string, for reading) |
| `attempt to call a X value` | calling something that is not a function, often a misspelt or missing function name (`nil`) |
| `table index is nil` | `t[nil] = v` |
| `'for' values must be numbers` | a numeric `for` with a start, limit or step that is not a number |
| `bad argument to 'for' (table expected, got X)` | `pairs(v)` or `ipairs(v)` in a `for`, where `v` is not a table |
| `stack overflow` | too many nested calls, usually endless recursion |
| `bad argument #N to 'name' (T expected, got X)` | a built-in function got the wrong type of argument |
| `assertion failed!` | `assert` with a false value and no message |
| `permission denied (capability 'c' was refused)` | see [system.md](system.md) |

Compile errors (shown after `line N: `; most end with `near 'token'`):

| Message | Example |
|---|---|
| `unexpected symbol` | `x = = 1`, `x = 1 +` |
| `'X' expected` | `if x then` (`'end' expected`), `print('a'` (`')' expected`) |
| `name expected` | `local 1 = 2`, `function f(a, b end` |
| `syntax error` | an expression that is not a call used as a statement: `x`, `a.b` |
| `cannot assign to this expression` | `f() = 1`, `math.pi = 3` |
| `'end' expected after return` | a statement after `return` in the same block |
| `break outside a loop`, `continue outside a loop` | |
| `'}' expected` | `{1 2}` |
| `'in' expected` | `for k, v, w in pairs(t)` |
| `for-in supports pairs(t) and ipairs(t) only` | `for k in next, t do` |
| `cannot use local 'x' of an enclosing function (...)` | see [What a function can see](#what-a-function-can-see) |
| `module 'm' used as a value` | `local s = string` |
| `unknown function 'm.f'` | `string.nope()` |
| `unexpected character 'c'` | `&`, `!`, `é` outside a string |
| `unfinished string`, `unfinished long string` | a missing closing quote or `]]` |
| `'<eof>' expected` | an extra `end` |

```lua
local function try(src) local f, err = load(src) print(err) end
try("local t = {1 2}")
try("if x then")
try("function f(a, b end")
try("math.pi = 3")
try("end")
```

```output
line 1: '}' expected near '2'
line 1: 'end' expected near '<eof>'
line 1: name expected near 'end'
line 1: cannot assign to this expression near '<eof>'
line 1: '<eof>' expected near 'end'
```

## Limits

| Limit | Value | When exceeded |
|---|---|---|
| Nested calls (frames) | 200 Whisker function calls active at once, counting calls made by `pcall` | `stack overflow` |
| Value stack | 3000 cells per program: arguments, locals and temporary values of all active calls; checked at each call, with 200 cells kept in reserve | `stack overflow` |
| Code memory | 150,000 code cells shared by every program that is loaded or cached | the program does not start: `out of code memory` (from `load`: `nil, "out of code memory"`) |
| Numbers | doubles; integers are exact up to 2^53 | rounding |
| Strings, tables, globals, locals per function | no fixed limit (memory only) | |

Built-in functions do not use frames. A function with many locals uses
more stack, so it can recurse less deeply:

```lua
local depth = 0
local function down()
  depth = depth + 1
  down()
end
local ok, e = pcall(down)
print(ok, e, depth)
```

```output
false   prog.wsk:4: stack overflow      200
```

Functions that built-in functions call back (for example the comparison
function of [`table.sort`](stdlib.md#tablesort), or a module body run by
`require`) cannot wait for input or sleep (`cannot wait inside a
callback`). See [internals.md](internals.md) for how memory and scheduling
work.

## Differences from Lua

Syntax:

* `continue` statement; `!=` as another spelling of `~=`.
* No `goto` or labels, and no bitwise operators (`& | ~ << >>`).
* Long strings and block comments have no levels (`[==[ ]==]`); block
  comments do not nest.
* String escapes: `\e` is ESC; `\a`, `\b`, `\f`, `\v`, `\z` and `\u{...}`
  are not supported (`\a` is just `a`); `\0` produces nothing.
* Malformed numbers like `1..2` become 0 instead of being an error.
* No `#!` first line.
* No varargs: `...` in a parameter list is one parameter named `arg`, and
  `...` cannot be used in expressions.
* The generic `for` accepts only `pairs(t)` and `ipairs(t)`; there are no
  `next` or custom iterators, and `pairs` and `ipairs` are not functions.

Semantics:

* No closures: a function can use its own locals, globals and top-level
  locals, but not locals of an enclosing function. Functions read variables
  when they run instead of capturing values.
* Multiple results are only kept when a call is the last value of a
  `local` or assignment with more targets. `return f()`, `print(f())` and
  `{f()}` get one value.
* String keys of tables are case-insensitive (`t.Name` is `t.name`).
* A table constructor skips positional `nil` values, and positional values
  always go after the current end (`{[1] = "a", "b"}` has two elements).
* `#t` is the size of the array part; holes inside it do not change it.
* The numeric `for` variable is the real counter: assigning to it changes
  the loop. A step of 0 is not an error. `for` values must be numbers
  (no string conversion).
* Arithmetic converts only decimal strings (not `"0x10"`).
* Numbers are always floats; there is no integer subtype, `math.type` or
  integer overflow wrap-around.
* Number formatting: whole numbers below 10^15 print without `.0`; others
  use 14 significant digits.
* Function values made from the same `function` expression are equal.
* The names of built-in modules (`string`, `math`, ...) are not values, and
  calling an unknown module function is a compile error.
* `error` always adds position information and ignores the level argument;
  non-string error values become strings.
* `pcall` accepts only Whisker functions, not built-ins.
* No metatables, coroutines, `setmetatable`, `rawget`, `rawset`, `next`,
  `select` with negative indexes, `_G` or `_ENV`.
* No tail calls; the call depth limit is 200.
* Strings use CP437 characters, not bytes; `#"é"` is 1.

## Known issues

These are bugs in the current version of Whisker. Programs should not rely
on them.

### pcall and operator errors

When an operator (arithmetic, unary `-`, `..`, comparison, `#`, indexing,
`t[nil] = v`) raises an error inside a function called by `pcall`, the VM
skips part of the instruction that follows the `pcall` call. The results
`pcall` returns are then wrong (often both `nil`, so `if not ok` does not
notice the error), and the code right after it can misbehave. Errors from
`error`, `assert`, built-in functions, calls of non-functions, `stack
overflow` and `for` loops are not affected.

```lua
local ok, e = pcall(function() return nil + 1 end)
print(ok, e)     -- should print false and the message
```

### Built-in functions that report two errors

Some built-in functions keep checking arguments after the first bad one.
When they raise a second error, that error is not caught by `pcall` and
stops the program. For example `pcall(function() string.rep() end)` stops
the program with `bad argument #2 to 'rep' (number expected, got nil)`.

### Wrong line numbers

After a function returns, error messages can report a line inside that
function instead of the caller's line, until the caller reaches a new line.
In this program the error is on line 4:

```lua
local function f()
  return 1
end
local y = f() + nil
```

```output
prog.wsk:2: attempt to perform arithmetic on a nil value
```

Also, a function body written on the same line as the statement that
defines it does not record its line, so errors in it are reported at the
caller's line:

```lua
local function f() return nil + 1 end
print("x")
f()
```

```output
x
prog.wsk:3: attempt to perform arithmetic on a nil value
```

### NaN

Undefined results such as `0/0`, `x % 0` and `(-8) ^ (1/3)` print as
`inf`, compare equal to themselves, and count as 0 in further arithmetic.

```lua
local n = 0 / 0
print(n, n == n, n + 1)
```

```output
inf     true    1
```

### Large numbers print imprecisely

Whole numbers of 10^15 and more are rounded to 14 significant digits, so
`2^53` and `math.maxinteger` print as `9007199254741000`.

```lua
print(2^53, 2^63)
```

```output
9007199254741000        9223372036854798000
```

### Numeric-looking string keys can collide

Two different strings of the same length that are equal as numbers are
the same table key: `t["1.0"]` and `t["1e0"]` are one field, and so are
`t["01"]` and `t["1."]`.

```lua
local t = {["01"] = "zero one"}
print(t["1."], t["01"], t["1"])
```

```output
zero one        zero one        nil
```

### Removing keys during pairs

Removing a key moves the last key of the hash part into its place, so a
`pairs` loop that removes keys can skip some. Collect the keys first (for
example with [`table.keys`](stdlib.md#tablekeys)), then remove them.

```lua
local t = {a = 1, b = 2, c = 3}
for k, v in pairs(t) do t[k] = nil end
local left = 0
for k in pairs(t) do left = left + 1 end
print(left)
```

```output
1
```

### String escapes

* `\0` followed by digits: `"\065"` is `"65"`, not `"A"`. `\0` is read as
  an empty character and the digits stay in the string.
* `\x` followed by characters that are not hex digits produces nothing and
  swallows two characters.
* A quoted string that is still open when the source ends is accepted,
  instead of being reported as `unfinished string`.

```lua
print("\065", "[\xZZ]")
```

```output
65      []
```

### Other

* Assigning to a module function, such as `string.len = 5`, is not an
  error: it sets a global named `len`.
* Top-level locals each keep their own stack cell for the whole run, and
  their number is not checked against the 3000-cell stack.

```lua
string.len = 5
print(len, string.len("abc"))
```

```output
5       3
```

See also: [stdlib.md](stdlib.md) for the built-in functions,
[libraries.md](libraries.md) for `load` and `require`,
[internals.md](internals.md) for the compiler and VM,
[getting-started.md](getting-started.md) for running programs.
