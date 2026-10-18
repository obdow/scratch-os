# Standard library

This file describes the built-in functions every Whisker program can use
without loading anything: the base functions (`print`, `tostring`,
`pcall` and the rest), and the `string`, `math` and `table` modules. Each
function has its own entry with its parameters, defaults, return values,
errors and examples. The examples were run on ScratchOS; the block after
each one is its exact output. Files, processes and the terminal are in
[system.md](system.md) and [terminal.md](terminal.md).

* [How built-in functions behave](#how-built-in-functions-behave)
* [Base functions](#base-functions)
* [string](#string)
* [math](#math)
* [table](#table)
* [Known issues](#known-issues)

## How built-in functions behave

A few rules hold for every function in this file.

**Arguments are converted where it makes sense.** A function that wants a
string also takes a number, which it converts the way `tostring` does. A
function that wants a number also takes a string that holds a number, such
as `"12"` or `" 2.5 "`. Any other type raises an error that names the
argument and the function by its short name:

```lua
print(string.len(12345), math.floor(" 2.5 "))
print(string.len({}))
```

```output
5       2
prog.wsk:2: bad argument #1 to 'len' (string expected, got table)
```

**Errors.** An uncaught error stops the program and prints
`file:line: message` on standard error (in red on the terminal). The
program's exit code is then 1. Catch errors with [`pcall`](#pcallf-).

**Multiple results.** Some functions return more than one value, for
example `string.find` (start and end) and `string.replace` (the new string
and a count). In Whisker you only get all of them in an assignment such as
`local a, b = f()`. Everywhere else, including as an argument to another
call and in `return f()`, only the first value is used:

```lua
local first, last = string.find("hello", "ll")
print(first, last)
print(string.find("hello", "ll"))
```

```output
3       4
3
```

**Modules are not values.** `string`, `math`, `table` and the other module
names exist only at compile time. `string.upper(s)` is compiled straight to
a call of the built-in, so you cannot store a module in a variable or loop
over it. `local s = string` is a compile error (`module 'string' used as a
value`), and so is a name that does not exist, such as `math.foo`
(`unknown function 'math.foo'`). A single function is a value, though:

```lua
local up = string.upper
print(up("abc"), type(up), up)
```

```output
ABC     function        builtin: string.upper
```

If your program defines a global with the same name as a built-in (for
example `function print(...)`), the global replaces the built-in for the
whole program.

## Base functions

| Function | Does |
|---|---|
| [`print(...)`](#print) | writes values to standard output |
| [`tostring(v)`](#tostringv) | converts any value to a string |
| [`tonumber(v [, base])`](#tonumberv--base) | converts a string to a number, or `nil` |
| [`type(v)`](#typev) | the type name of a value |
| [`error([msg])`](#errormsg) | raises an error |
| [`pcall(f, ...)`](#pcallf-) | calls a function and catches its errors |
| [`assert(v [, msg])`](#assertv--msg) | raises an error if `v` is false or `nil` |
| [`select(n, ...)`](#selectn-) | one of its arguments, or how many there are |
| [`rawequal(a, b)`](#rawequala-b) | compares two values |
| [`unpack(t)`](#unpackt) | the elements of a table as separate values |
| [`sleep([sec])`](#sleepsec) | pauses the program |
| [`exit([code])`](#exitcode) | ends the program |
| [`load(src)`](#loadsrc) | compiles code at run time |
| [`require(name)`](#requirename) | loads a module |
| [`pairs` / `ipairs`](#pairs-and-ipairs) | only in `for ... in` loops |

### print(...)

Writes its arguments to standard output, separated by tab characters and
followed by a newline. Each argument is converted with
[`tostring`](#tostringv), so any type can be printed. With no arguments it
prints an empty line. It returns nothing. To write without the tab and
newline, use [`io.write`](system.md).

```lua
print("a", 1, nil, true)
print()
print("x" .. 1 .. "y")
```

```output
a       1       nil     true

x1y
```

### tostring(v)

Returns `v` as a string. This is also how `print`, `..` and
`string.format("%s")` show values.

| Value | Result |
|---|---|
| string | itself |
| `nil`, `true`, `false` | `"nil"`, `"true"`, `"false"` |
| table | `"table: 0x"` and a six-digit handle, such as `table: 0x000004` |
| Whisker function | `"function: 0x"` and its code address |
| built-in function | `"builtin: "` and its name, such as `builtin: print` |
| number | see below |

Numbers are written like this:

* A whole number between -10^15 and 10^15 has no decimal point: `3.0`
  prints as `3`, and `-0` as `0`.
* Other numbers are rounded to 14 significant digits, then trailing zeros
  are dropped: `1/3` is `0.33333333333333`.
* Very large and very small numbers use an exponent: `1e+21`, `1e-7`.
* Infinity is `inf` or `-inf`.

```lua
print(42, 3.0, -0, 2.5, 1/3, 100/3)
print(1e15, 2^53, 1e21, 0.000001, 1e-7)
print(1/0, -1/0, 0.1 + 0.2)
```

```output
42      3       0       2.5     0.33333333333333        33.333333333333
1000000000000000        9007199254741000        1e+21   0.000001        1e-7
inf     -inf    0.3
```

```lua
print(tostring(nil), tostring(false), tostring(print))
print(tostring({}):sub(1, 9), type(tostring(12)))
```

```output
nil     false   builtin: print
table: 0x       string
```

Two different tables always give different strings, and the same table
always gives the same string, so `tostring(t)` can serve as an identity.
"Not a number" (from `0/0`) prints wrongly as `inf`; see
[Known issues](#known-issues).

### tonumber(v [, base])

Converts `v` to a number. It returns `nil` (not an error) when that is not
possible.

* A number is returned unchanged (`base` is ignored).
* A string is first trimmed of spaces, tabs, `\r` and `\n`. Without
  `base`, it may hold a decimal number with an optional sign, decimal point
  and exponent (`"-5"`, `".5"`, `"5."`, `"+5"`, `"1e3"`), or a hexadecimal
  number starting with `0x` or `0X`.
* With `base`, the string must hold only digits `0`-`9` and letters `a`-`z`
  (either case, `a` = 10 ... `z` = 35), each smaller than `base`. Signs and
  prefixes are not allowed.
* Any other type (`nil`, booleans, tables) gives `nil`.

`base` must be a number (or a numeric string); anything else raises
`bad argument #2 to 'tonumber' (number expected, got ...)`.

```lua
print(tonumber("10"), tonumber("  10  "), tonumber("-2.5e2"), tonumber(".5"))
print(tonumber("0x1F"), tonumber("abc"), tonumber(""), tonumber("1 2"))
print(tonumber(nil), tonumber(true), tonumber(7))
```

```output
10      10      -250    0.5
31      nil     nil     nil
nil     nil     7
```

```lua
print(tonumber("101", 2), tonumber("ff", 16), tonumber("FF", 16), tonumber("z", 36))
print(tonumber("8", 8), tonumber("-101", 2), tonumber("0x10", 16), tonumber("", 10))
```

```output
5       255     255     35
nil     nil     nil     nil
```

A string such as `"0x1g"` that starts with `0x` but is not valid hex gives
`0` instead of `nil`, and `"-0x10"` gives `nil`. The base is not checked:
bases above 36 behave like 36, and `tonumber("10", 2.5)` is `2.5`.

Checking input:

```lua
for _, s in ipairs({"42", "4x2", " 7 "}) do
  local n = tonumber(s)
  if n then print(s, "->", n * 2) else print(s, "is not a number") end
end
```

```output
42      ->      84
4x2     is not a number
 7      ->      14
```

### type(v)

Returns the type of `v` as a string: `"nil"`, `"number"`, `"string"`,
`"boolean"`, `"table"` or `"function"`. Built-in functions are
`"function"` too. Calling `type()` with no argument raises
`bad argument #1 to 'type' (value expected)`.

```lua
print(type(nil), type(1), type("a"), type(true))
print(type({}), type(print), type(function() end))
print(type(type(1)))
```

```output
nil     number  string  boolean
table   function        function
string
```

### error([msg])

Raises an error with the message `msg`. The message is converted with
`tostring`, so the error value is always a string (a table becomes
`table: 0x...`, no argument becomes `nil`). The current file name and line
are put in front of it. Unlike Lua, there is no level argument; a second
argument is ignored.

```lua
local ok, e = pcall(function() error("disk full") end)
print(e)
local ok2, e2 = pcall(function() error(42) end)
print(e2, type(e2))
error("stop here")
print("not reached")
```

```output
prog.wsk:1: disk full
prog.wsk:3: 42  string
prog.wsk:5: stop here
```

### pcall(f, ...)

Calls `f` with the remaining arguments in *protected mode*. If `f` finishes,
`pcall` returns `true` followed by `f`'s results. If `f` raises an error,
`pcall` returns `false` and the error message, and the program goes on.
Errors raised by `error`, `assert` and other built-in functions (such as
bad arguments), and calls of a `nil` value, are caught this way. Errors
raised by operators, such as indexing `nil` or arithmetic on `nil`, are
currently not reported correctly; see [Known issues](#known-issues).

`f` must be a function written in Whisker. A built-in such as `print` or
`string.sub` is not accepted: wrap it in a function. Passing anything else
raises `bad argument #1 to 'pcall' (Whisker function expected)`, and that
error is not caught by the `pcall` itself.

```lua
local ok, sum, prod = pcall(function(a, b) return a + b, a * b end, 3, 4)
print(ok, sum, prod)
local ok2, err = pcall(function() return string.rep("x", "y") end)
print(ok2, err)
```

```output
true    7       12
false   prog.wsk:3: bad argument #2 to 'rep' (number expected, got string)
```

```lua
local function try(f)
  local ok, e = pcall(f)
  if not ok then print("caught: " .. e) end
end
try(function()
  return string.sub("abc", "x")
end)
try(function()
  return nosuch()
end)
```

```output
caught: prog.wsk:6: bad argument #2 to 'sub' (number expected, got string)
caught: prog.wsk:9: attempt to call a nil value
```

Remember that only an assignment receives all results:
`print(pcall(f))` prints only `true` or `false`. Errors raised inside a
[`table.sort`](#tablesortt--less) comparator are not caught; see
[Known issues](#known-issues).

### assert(v [, msg])

If `v` is `false` or `nil`, raises an error with message `msg` (converted
with `tostring`), or `assertion failed!` if there is no `msg`. Otherwise
it returns `v` (only `v`; further arguments are not returned).

```lua
local f = assert(tonumber("12"), "not a number")
print(f)
local ok, e = pcall(function() assert(false) end)
print(e)
assert(tonumber("x"), "bad input")
```

```output
12
prog.wsk:3: assertion failed!
prog.wsk:5: bad input
```

### select(n, ...)

With `n` equal to `"#"`, returns the number of extra arguments. With a
number `n`, returns the `n`-th extra argument. It returns that one value
only, not every argument from `n` on as in Lua. If `n` is below 1 or past
the end, it returns `nil`. A non-numeric `n` raises
`bad argument #1 to 'select' (number expected, got string)`.

```lua
print(select("#", "a", nil, "c"), select("#"))
local x, y = select(2, "a", "b", "c")
print(x, y)
print(select(5, "a"), select(-1, "a", "b"), select("2", "a", "b"))
```

```output
3       0
b       nil
nil     nil     b
```

Since Whisker functions have no `...` parameter, `select` is mostly useful
for its argument count.

### rawequal(a, b)

Returns `true` if `a` and `b` are equal, without converting either value.
This is the same test as `==`: values of different types are never equal,
strings compare case-sensitively, and tables are equal only to themselves.

```lua
local t = {}
print(rawequal(1, 1), rawequal("a", "A"), rawequal(1, "1"))
print(rawequal(t, t), rawequal({}, {}), rawequal(nil, nil))
```

```output
true    false   false
true    false   true
```

### unpack(t)

Returns the elements `t[1]`, `t[2]`, ... `t[#t]` as separate values. It is
the same function as [`table.unpack`](#tableunpackt). Extra arguments (Lua's
`i` and `j`) are ignored: the whole array part is returned. `t` must be a
table.

```lua
local a, b, c = unpack({"x", "y", "z"})
print(a, b, c)
local p, q = unpack({1})
print(p, q)
```

```output
x       y       z
1       nil
```

### sleep([sec])

Pauses the program for `sec` seconds (default 0); fractions are allowed.
Zero or a negative value returns at once. Other programs keep running while
it waits. It returns nothing. [`os.sleep`](system.md) is the same function.
`sleep` cannot be called inside a callback such as a `table.sort`
comparator; that raises `cannot wait inside a callback`.

```lua
local t0 = os.millis()
sleep(0.2)
print(os.millis() - t0 >= 200)
```

```output
true
```

### exit([code])

Ends the program at once with exit code `code` (default 0). Nothing after
it runs. [`os.exit`](system.md) is the same function. Returning a number
from the main chunk (`return 2` at the top level) also sets the exit code.
See [getting-started.md](getting-started.md) for how the shell reports exit
codes.

```lua
print("bye")
exit(0)
print("never printed")
```

```output
bye
```

`exit(true)` and `exit(false)` are meant to mean 0 and 1, but currently
raise `bad argument #1 to 'exit' (number expected, got boolean)`; see
[Known issues](#known-issues).

### load(src)

Compiles the string `src` as a chunk of Whisker and returns it as a
function, or `nil` and an error message if it does not compile. The chunk
shares the program's globals. See
[libraries.md](libraries.md) for details.

```lua
local f = load("return 6 * 7")
print(f())
local g, err = load("return +")
print(g, err)
```

```output
42
nil     line 1: unexpected symbol near '+'
```

### require(name)

Loads the module `name` (from `/lib/name.wsk`, or `name.wsk` in the current
directory) once, and returns its result. An unknown module raises
`module 'name' not found`. See [libraries.md](libraries.md).

```lua
local ok, e = pcall(function() return require("no_such_module") end)
print(e)
```

```output
prog.wsk:1: module 'no_such_module' not found
```

### pairs and ipairs

`pairs(t)` and `ipairs(t)` are not functions in Whisker. They are part of
the generic `for` statement, and that is the only place they can appear.
Outside a `for`, `pairs` is just an undefined global (`nil`).

* `for k, v in pairs(t)` visits the array part in order (skipping `nil`
  holes), then the other keys in the order they were added.
* `for i, v in ipairs(t)` visits `t[1]`, `t[2]`, ... and stops at the first
  `nil`.

```lua
local t = {10, 20, x = "a"}
t.y = "b"
for k, v in pairs(t) do print(k, v) end
for i, v in ipairs({"p", "q"}) do print(i, v) end
print(pairs)
```

```output
1       10
2       20
x       a
y       b
1       p
2       q
nil
```

See [language.md](language.md) for the `for` statement.

## string

Strings in Whisker are sequences of characters from code page 437 (CP437),
one byte each. Positions start at 1. Where a function takes a position, a
negative number counts from the end: -1 is the last character, -2 the one
before it. All searching and comparing is case-sensitive and works on plain
text: there are no Lua patterns (`.`, `%d` and so on are ordinary
characters).

**Methods.** Every `string` function can be called as a method on a string
value: `s:upper()` is `string.upper(s)`, and `("%d"):format(5)` works too.
This works only on strings: `n:upper()` on a number raises
`attempt to index a number value`. A name that is not a `string` function
gives `nil`, so `s:nosuch()` raises `attempt to call a nil value`.

```lua
local s = "Hello"
print(s:upper(), s:len(), s:sub(2, 3), ("%03d"):format(7))
print(#s, s.nosuch)
```

```output
HELLO   5       el      007
5       nil
```

| Function | Returns |
|---|---|
| [`len(s)`](#stringlens) | number of characters |
| [`sub(s [, i [, j]])`](#stringsubs--i--j) | the part from `i` to `j` |
| [`upper(s)`](#stringuppers) / [`lower(s)`](#stringlowers) | changed case |
| [`find(s, text [, init])`](#stringfinds-text--init) | start and end of `text`, or `nil` |
| [`contains(s, text)`](#stringcontainss-text) | `true` or `false` |
| [`startswith(s, p)`](#stringstartswiths-prefix) / [`endswith(s, p)`](#stringendswiths-suffix) | `true` or `false` |
| [`replace(s, from, to)`](#stringreplaces-from-to) | new string, count |
| [`rep(s, n [, sep])`](#stringreps-n--sep) | `s` repeated |
| [`reverse(s)`](#stringreverses) | `s` backwards |
| [`trim(s)`](#stringtrims) | `s` without surrounding blanks |
| [`pad(s, width)`](#stringpads-width) | `s` padded with spaces |
| [`split(s [, sep])`](#stringsplits--sep) | table of pieces |
| [`lines(s)`](#stringliness) | table of lines |
| [`byte(s [, i])`](#stringbytes--i) | CP437 code of one character |
| [`char(...)`](#stringchar) | string from codes |
| [`format(fmt, ...)`](#stringformatfmt-) | formatted string |

### string.len(s)

Returns the number of characters in `s`. This is the same as `#s`.

```lua
print(string.len("hello"), (""):len(), #"abc", string.len(1234))
```

```output
5       0       3       4
```

### string.sub(s [, i [, j]])

Returns the characters of `s` from position `i` to position `j`, both
included. `i` defaults to 1 and `j` to -1 (the end). Negative positions
count from the end. After that, `i` below 1 becomes 1 and `j` past the end
becomes the end. If `i` is greater than `j` the result is `""`. Positions
must be numbers (or numeric strings).

```lua
local s = "hello world"
print(s:sub(1, 5), s:sub(7), s:sub(-5), s:sub(-5, -2))
print(s:sub(0), s:sub(-100, 2), s:sub(5, 100))
print("[" .. s:sub(3, 2) .. "]", "[" .. s:sub(20) .. "]")
```

```output
hello   world   world   worl
hello world     he      o world
[]      []
```

Visiting each character:

```lua
local s = "abc"
for i = 1, #s do io.write(s:sub(i, i):upper(), ".") end
print()
```

```output
A.B.C.
```

### string.upper(s)

Returns `s` with lowercase letters changed to uppercase. Letters `a`-`z`
always convert. CP437 accented letters are meant to convert too (`é` to
`É`), but most of them currently do not; see [Known issues](#known-issues).

```lua
print(string.upper("Hello, World 1"), ("é"):upper())
```

```output
HELLO, WORLD 1  É
```

### string.lower(s)

Returns `s` with uppercase letters changed to lowercase. The same notes as
for `upper` apply.

```lua
print(string.lower("Hello, WORLD"), ("ABC"):lower() == "abc")
```

```output
hello, world    true
```

### string.find(s, text [, init])

Looks for the plain text `text` in `s`, starting at position `init`
(default 1; negative counts from the end; below 1 means 1). Returns two
numbers, the start and end positions of the first match, or `nil` if there
is none. The search is case-sensitive and has no special characters. An
empty `text` matches at `init` itself and returns `init, init - 1`.

```lua
local s = "one two one"
local a, b = s:find("one")
local c, d = s:find("one", 2)
local e, f = s:find("one", -3)
print(a, b, c, d, e, f)
print(s:find("three"), s:find("ONE"), ("a.b"):find("."))
local g, h = s:find("")
print(g, h)
```

```output
1       3       9       11      9       11
nil     nil     2
1       0
```

Counting occurrences by moving `init` forward:

```lua
local function count(s, text)
  local n, pos = 0, 1
  while true do
    local a, b = string.find(s, text, pos)
    if a == nil then break end
    n = n + 1
    pos = b + 1
  end
  return n
end
print(count("banana", "an"), count("aaaa", "aa"), count("abc", "x"))
```

```output
2       2       0
```

### string.contains(s, text)

Returns `true` if the plain text `text` occurs in `s`, otherwise `false`.
Case-sensitive. An empty `text` is always found.

```lua
print(("hello"):contains("ell"), ("hello"):contains("L"), ("hello"):contains(""))
```

```output
true    false   true
```

### string.startswith(s, prefix)

Returns `true` if `s` begins with `prefix`. Case-sensitive. An empty prefix
is always `true`.

```lua
print(("hello"):startswith("he"), ("Hello"):startswith("he"), ("hi"):startswith(""))
```

```output
true    false   true
```

### string.endswith(s, suffix)

Returns `true` if `s` ends with `suffix`. Case-sensitive. An empty suffix
is always `true`; a suffix longer than `s` is `false`.

```lua
print(("photo.simg"):endswith(".simg"), ("lo"):endswith("hello"), ("x"):endswith(""))
```

```output
true    false   true
```

### string.replace(s, from, to)

Replaces every occurrence of the plain text `from` in `s` with `to`,
scanning left to right without overlaps. Returns two values: the new string
and the number of replacements. If `from` is empty, it returns `s`
unchanged and no count. Case-sensitive. `to` may be a number.

```lua
local r, n = ("a-b-c"):replace("-", " + ")
print(r, n)
local r2, n2 = ("aaa"):replace("aa", "b")
print(r2, n2)
local r3, n3 = ("Hello"):replace("hello", "bye")
print(r3, n3)
print(("50%"):replace("%", " percent"))
```

```output
a + b + c       2
ba      1
Hello   0
50 percent
```

### string.rep(s, n [, sep])

Returns `n` copies of `s` joined together, with `sep` (default `""`)
between them. If `n` is less than 1 the result is `""`. `n` should be a
whole number.

```lua
print(("ab"):rep(3), ("ab"):rep(3, ", "), "[" .. ("ab"):rep(0) .. "]", string.rep("-", 10))
```

```output
ababab  ab, ab, ab      []      ----------
```

### string.reverse(s)

Returns `s` with its characters in reverse order.

```lua
print(("stressed"):reverse(), string.reverse(123))
```

```output
desserts        321
```

### string.trim(s)

Returns `s` without the spaces, tabs, carriage returns (`\r`) and newlines
at its start and end. Blanks inside the string stay.

```lua
print("[" .. ("  two words \t\n"):trim() .. "]")
```

```output
[two words]
```

### string.pad(s, width)

Pads `s` with spaces to `width` characters. A positive `width` adds the
spaces on the right (the text is left-aligned); a negative `width` adds
them on the left (right-aligned) to a width of `-width`. A string that is
already long enough is returned unchanged; it is never cut.

```lua
print("[" .. ("ab"):pad(5) .. "]", "[" .. ("ab"):pad(-5) .. "]", "[" .. ("toolong"):pad(3) .. "]")
for _, n in ipairs({5, 120, 42}) do print(string.pad(n, -4) .. " items") end
```

```output
[ab   ] [   ab] [toolong]
   5 items
 120 items
  42 items
```

A simple bar chart with `pad` and `rep`:

```lua
local data = {{"cats", 5}, {"dogs", 3}, {"fish", 8}}
for _, d in ipairs(data) do
  print(d[1]:pad(6) .. ("#"):rep(d[2]) .. " " .. d[2])
end
```

```output
cats  ##### 5
dogs  ### 3
fish  ######## 8
```

### string.split(s [, sep])

Splits `s` into pieces and returns them in a new table (an array).

* With no `sep`, or with `sep` equal to `" "`, it splits on runs of
  whitespace (spaces, tabs, `\r`, `\n`), and ignores whitespace at the start
  and end. No piece is empty, and a blank string gives an empty table.
* With any other `sep` (which may be several characters long), it splits at
  each occurrence of `sep` exactly. Neighbouring separators give empty
  pieces, and a separator at the start or end gives an empty first or last
  piece. A string without `sep` gives one piece, so `""` gives `{""}`.
* With `sep` equal to `""`, every character becomes a piece.

The separator is plain text and case-sensitive.

```lua
local function show(t)
  local o = {}
  for i = 1, #t do o[i] = "[" .. t[i] .. "]" end
  print(#t, table.concat(o, " "))
end
show(("  a  b\tc\n d  "):split())
show(("a,b,,c,"):split(","))
show(("x::y::z"):split("::"))
show(("abc"):split(""))
show(("abc"):split(";"))
show((""):split(","))
show(("   "):split())
```

```output
4       [a] [b] [c] [d]
5       [a] [b] [] [c] []
3       [x] [y] [z]
3       [a] [b] [c]
1       [abc]
1       []
0
```

### string.lines(s)

Splits `s` at each newline (`\n`) and returns the lines in a new table. It
is `string.split(s, "\n")`: a trailing newline gives an empty last line,
`""` gives one empty line, and a `\r` before the newline stays at the end
of its line.

```lua
local t = ("first\nsecond\n\nfourth"):lines()
print(#t, t[2], "[" .. t[3] .. "]", t[4])
print(#("a\nb\n"):lines(), #("a\r\nb"):lines()[1])
```

```output
4       second  []      fourth
3       2
```

Parsing a small CSV text:

```lua
local text = "name,qty\napple,3\npear,12\n"
local total = 0
for i, line in ipairs(text:trim():lines()) do
  if i > 1 then
    local f = line:split(",")
    total = total + tonumber(f[2])
  end
end
print("total", total)
```

```output
total   15
```

### string.byte(s [, i])

Returns the CP437 code (0-255) of the character at position `i` (default
1; negative counts from the end), or `nil` if there is no character there.
It returns one code only; unlike Lua, there is no range form
`byte(s, i, j)`.

```lua
print(("ABC"):byte(), ("ABC"):byte(2), ("ABC"):byte(-1), ("ABC"):byte(4), (""):byte())
print((" "):byte(), ("\t"):byte(), ("\n"):byte(), ("é"):byte())
```

```output
65      66      67      nil     nil
32      9       10      130
```

At the moment `byte` returns 63 (the code of `?`) for many characters
outside printable ASCII, for example `É` and the box-drawing characters;
see [Known issues](#known-issues).

### string.char(...)

Returns a string made of the characters with the given CP437 codes. Codes
are rounded down and taken modulo 256. Code 0 gives an empty string. With
no arguments the result is `""`. Each argument must be a number or numeric
string.

```lua
print(string.char(72, 105, 33), string.char("65"), string.char(321), string.char(130))
print(#string.char(), #string.char(0), string.char(10) == "\n")
```

```output
Hi!     A       A       é
0       0       true
```

`byte` and `char` together, shifting letters by one:

```lua
local s, out = "HAL", ""
for i = 1, #s do out = out .. string.char(s:byte(i) + 1) end
print(out)
```

```output
IBM
```

### string.format(fmt, ...)

Returns `fmt` with each `%` specifier replaced by the next argument,
formatted. The general form of a specifier is

    %[flags][width][.precision]conversion

**Conversions**

| Spec | Output |
|---|---|
| `%d`, `%i` | the number with its fraction cut off (toward zero) |
| `%f` | the number with `precision` decimals (default 6), rounded half away from zero |
| `%x`, `%X` | the whole part in lowercase / uppercase hexadecimal |
| `%c` | the character with that CP437 code |
| `%s` | the value converted with `tostring`; `precision` keeps only that many characters |
| `%q` | the value converted with `tostring`, in double quotes (nothing is escaped) |
| `%%` | a single `%` (it uses no argument) |

**Flags**: `-` aligns left within the width (pads on the right); `0` pads
with zeros instead of spaces (after a leading minus sign). Both work with
every conversion, including `%s`. **Width** is the minimum number of
characters; longer results are not cut. **Precision** only affects `%f` and
`%s`.

```lua
local f = string.format
print(f("[%d] [%5d] [%-5d] [%05d] [%05d]", 42, 42, 42, 42, -42))
print(f("[%d] [%d] [%i] [%d]", 3.99, -3.7, "12", 1e6))
print(f("[%f] [%.2f] [%8.3f] [%-8.1f] [%08.2f]", math.pi, math.pi, math.pi, 2.5, -1.5))
print(f("[%.0f] [%.0f] [%.0f] [%.2f]", 0.5, 2.5, -2.5, 2/3))
```

```output
[42] [   42] [42   ] [00042] [-0042]
[3] [-3] [12] [1000000]
[3.141593] [3.14] [   3.142] [2.5     ] [-0001.50]
[1] [3] [-3] [0.67]
```

```lua
local f = string.format
print(f("[%x] [%X] [%04x] [%x]", 255, 255, 10, 0))
print(f("[%s] [%8s] [%-8s] [%.3s] [%s] [%s]", "hi", "hi", "hi", "hello", nil, true))
print(f("[%c%c] [%3c] [%q] [%d%%] [%5.1f%%]", 72, 105, 65, "say", 50, 12.345))
```

```output
[ff] [FF] [000a] [0]
[hi] [      hi] [hi      ] [hel] [nil] [true]
[Hi] [  A] ["say"] [50%] [ 12.3%]
```

**Arguments.** `%d`, `%i` and `%f` need a number or numeric string, and
raise `bad argument #N to 'format' (number expected)` otherwise (also when
the argument is missing). A missing argument for `%s` gives `nil`. Extra
arguments are ignored.

```lua
print(string.format("%s and %s", "one"))
print(string.format("%d items", "lots"))
```

```output
one and nil
prog.wsk:2: bad argument #2 to 'format' (number expected)
```

**Not supported.** There is no `%e`, `%g`, `%o`, `%u` or `%a`, and no `+`,
space or `#` flags. An unknown conversion letter is treated like `%s`, and
an unknown flag character is itself taken as the conversion (also like
`%s`), so the letter after it comes out as text. Negative numbers give an
empty `%x`. Check output when you port Lua code:

```lua
print(string.format("%e|%g|%u", 1.5, 2.5, 3))
print(string.format("[%+d] [% d] [%#x]", 5, 5, 255))
```

```output
1.5|2.5|3
[5d] [5d] [255x]
```

A table of aligned columns:

```lua
local items = {{"pen", 2, 1.5}, {"notebook", 1, 4.25}, {"ink", 10, 0.3}}
for _, it in ipairs(items) do
  print(string.format("%-10s %3d x %6.2f = %7.2f", it[1], it[2], it[3], it[2] * it[3]))
end
```

```output
pen          2 x   1.50 =    3.00
notebook     1 x   4.25 =    4.25
ink         10 x   0.30 =    3.00
```

## math

Angles are in radians. All functions take numbers or numeric strings, and
raise `bad argument #1 to 'NAME' (number expected, got ...)` for anything
else. Results that are not a real number (such as `math.sqrt(-1)`) print
as `inf` because of a [known issue](#known-issues).

| Name | Value or result |
|---|---|
| [`math.pi`](#mathpi-mathhuge-mathmaxinteger) | 3.141592653589793 |
| [`math.huge`](#mathpi-mathhuge-mathmaxinteger) | infinity |
| [`math.maxinteger`](#mathpi-mathhuge-mathmaxinteger) | 2^53 - 1 |
| [`floor`](#mathfloorx) [`ceil`](#mathceilx) [`round`](#mathroundx) [`abs`](#mathabsx) | rounding and sign |
| [`tointeger`](#mathtointegerx) | `x` if it is whole, else `nil` |
| [`max`](#mathmaxx-) [`min`](#mathminx-) | largest / smallest argument |
| [`fmod`](#mathfmoda-b) | remainder of a division |
| [`sqrt`](#mathsqrtx) [`pow`](#mathpowx-y) [`exp`](#mathexpx) [`log`](#mathlogx--base) | powers and logarithms |
| [`sin`](#mathsinx-mathcosx-mathtanx) [`cos`](#mathsinx-mathcosx-mathtanx) [`tan`](#mathsinx-mathcosx-mathtanx) [`asin`](#mathasinx-mathacosx) [`acos`](#mathasinx-mathacosx) [`atan`](#mathatany--x) [`atan2`](#mathatan2y-x) | trigonometry |
| [`random`](#mathrandomm--n) | random numbers |

### math.pi, math.huge, math.maxinteger

Constants. `math.pi` is π, `math.huge` is positive infinity (greater than
any number), and `math.maxinteger` is 9007199254740991 (2^53 - 1, the
largest whole number that is stored exactly). They are filled in by the
compiler, so they must be written out in full: `math.pi`, not `m.pi`.

```lua
print(math.pi, math.huge, -math.huge, math.huge > 1e308)
print(math.maxinteger == 2^53 - 1, math.maxinteger)
```

```output
3.1415926535898 inf     -inf    true
true    9007199254741000
```

`math.maxinteger` prints as `9007199254741000` because `print` rounds to 14
significant digits; the value itself is exact.

### math.floor(x)

Returns the largest whole number less than or equal to `x`.

```lua
print(math.floor(3.7), math.floor(-3.2), math.floor(5), math.floor("2.5"))
```

```output
3       -4      5       2
```

Rounding to two decimals, and integer division:

```lua
local x = 3.14159
print(math.floor(x * 100 + 0.5) / 100, math.floor(17 / 5), 17 // 5)
```

```output
3.14    3       3
```

### math.ceil(x)

Returns the smallest whole number greater than or equal to `x`.

```lua
print(math.ceil(3.2), math.ceil(-3.7), math.ceil(5))
```

```output
4       -3      5
```

### math.round(x)

Rounds `x` to the nearest whole number. Halves round up, toward positive
infinity: 2.5 becomes 3, but -2.5 becomes -2.

```lua
print(math.round(2.4), math.round(2.5), math.round(3.5), math.round(-2.5), math.round(-2.6))
```

```output
2       3       4       -2      -3
```

### math.abs(x)

Returns the absolute value of `x`.

```lua
print(math.abs(-4), math.abs(4), math.abs(-0.5), math.abs("-2"))
```

```output
4       4       0.5     2
```

### math.tointeger(x)

Returns `x` as a number if it is a whole number, otherwise `nil`. A
numeric string is converted (`"8"` gives the number 8); a string that is not
numeric raises an error.

```lua
print(math.tointeger(3), math.tointeger(3.0), math.tointeger(3.5))
print(math.tointeger("8"), type(math.tointeger("8")), math.tointeger("8.5"))
```

```output
3       3       nil
8       number  nil
```

### math.max(x, ...)

Returns the largest of its arguments, as a number. It takes any number of
arguments, but at least one. With none it raises
`bad argument #1 to 'max' (number expected, got nil)`.

```lua
print(math.max(3, 1, 4, 1, 5), math.max(-1, -5), math.max(7), math.max("10", 9))
```

```output
5       -1      7       10
```

### math.min(x, ...)

Returns the smallest of its arguments. The same rules as `math.max`
apply (its error messages also say `'max'`).

```lua
print(math.min(3, 1, 4, 1, 5), math.min(2.5, 2.4), math.min(0))
```

```output
1       2.4     0
```

### math.fmod(a, b)

Returns the remainder of `a / b`, with the quotient rounded toward zero, so
the result has the sign of `a`. This differs from the `%` operator, whose
result has the sign of `b`. `math.fmod(a, 0)` returns `a`.

```lua
print(math.fmod(7, 3), math.fmod(-7, 3), math.fmod(7, -3), math.fmod(5.5, 2))
print(-7 % 3, 7 % -3, math.fmod(1, 0))
```

```output
1       -1      1       1.5
2       -2      1
```

### math.sqrt(x)

Returns the square root of `x`.

```lua
print(math.sqrt(16), math.sqrt(2), math.sqrt(0))
```

```output
4       1.4142135623731 0
```

### math.pow(x, y)

Returns `x` raised to the power `y`, the same as `x ^ y`. Whole exponents
up to 64 are computed by repeated multiplication, so they are exact where
possible.

```lua
print(math.pow(2, 10), math.pow(2, -1), math.pow(2, 0.5), math.pow(0, 0), 3 ^ 2)
```

```output
1024    0.5     1.4142135623731 1       9
```

### math.exp(x)

Returns *e* raised to the power `x`.

```lua
print(math.exp(0), math.exp(1))
```

```output
1       2.718281828459
```

### math.log(x [, base])

Returns the logarithm of `x`: the natural logarithm, or the logarithm to
`base` if it is given. `math.log(0)` is `-inf`.

```lua
print(math.log(1), math.log(math.exp(2)), math.log(8, 2), math.log(1000, 10), math.log(0))
```

```output
0       2       3       3       -inf
```

### math.sin(x), math.cos(x), math.tan(x)

Return the sine, cosine and tangent of the angle `x`, in radians.

```lua
print(math.sin(0), math.cos(0), math.sin(math.pi / 2), math.tan(math.pi / 4))
print(math.floor(math.cos(math.pi) + 0.5))
```

```output
0       1       1       1
-1
```

### math.asin(x), math.acos(x)

Return the arc sine and arc cosine of `x`, in radians.

```lua
print(math.asin(1), math.acos(1), math.acos(0) == math.pi / 2)
```

```output
1.5707963267949 0       true
```

### math.atan(y [, x])

With one argument, returns the arc tangent of `y` in radians. With two,
it is [`math.atan2(y, x)`](#mathatan2y-x).

```lua
print(math.atan(1), math.atan(1) == math.pi / 4, math.atan(1, -1))
```

```output
0.78539816339745        true    2.3561944901923
```

### math.atan2(y, x)

Returns the angle, in radians from -π to π, of the point (`x`, `y`) seen
from the origin. It uses the signs of both arguments to find the quadrant.

```lua
print(math.atan2(1, 0), math.atan2(0, -1), math.atan2(-1, 0), math.atan2(0, 1))
```

```output
1.5707963267949 3.1415926535898 -1.5707963267949        0
```

### math.random([m [, n]])

Returns a random number.

* `math.random()` returns a number from 0 up to but not including 1, in
  steps of 0.000001.
* `math.random(m)` returns a whole number from 1 to `m`, inclusive.
* `math.random(m, n)` returns a whole number from `m` to `n`, inclusive.

`m` and `n` are rounded down first. If the range is backwards
(`math.random(5, 1)`, or `math.random(0)`, which is the range 1 to 0) the
result is still a whole number between the two ends. There is no
`math.randomseed`.

```lua
local d = math.random(6)          -- a die: 1 to 6
local c = math.random(-1, 1)      -- -1, 0 or 1
local x = math.random()           -- 0 <= x < 1
local pick = ({"rock", "paper", "scissors"})[math.random(3)]
```

The ranges can be checked:

```lua
local ok = true
for i = 1, 300 do
  local a, b, c = math.random(), math.random(6), math.random(-2, 2)
  if a < 0 or a >= 1 or b < 1 or b > 6 or b ~= math.floor(b) or c < -2 or c > 2 then ok = false end
end
print(ok, math.random(4, 4))
```

```output
true    4
```

## table

These functions work on a table's *array part*: the values at keys 1, 2,
3 ... that `#t` counts. Only `table.keys`, `table.count` and `table.copy`
also look at the other keys. The table argument must be a table; anything
else raises `bad argument #1 to 'NAME' (table expected, got ...)`.

Two facts about Whisker tables matter here (see
[language.md](language.md)): a `nil` in a table constructor is skipped,
so `{1, nil, 3}` is the same as `{1, 3}`; and setting `t[i] = nil` inside
the array leaves a hole that `#t` still counts.

| Function | Does |
|---|---|
| [`insert(t, [pos,] v)`](#tableinsertt-pos-v) | adds a value |
| [`remove(t [, pos])`](#tableremovet--pos) | removes and returns a value |
| [`concat(t [, sep])`](#tableconcatt--sep) | joins values into a string |
| [`sort(t [, less])`](#tablesortt--less) | sorts in place |
| [`unpack(t)`](#tableunpackt) | values as separate results |
| [`keys(t)`](#tablekeyst) | a table of all keys |
| [`count(t)`](#tablecountt) | number of entries |
| [`copy(t)`](#tablecopyt) | a shallow copy |
| [`find(t, v)`](#tablefindt-v) | index of a value |
| [`reverse(t)`](#tablereverset) | reverses in place |

### table.insert(t, [pos,] v)

With two arguments, appends `v` at the end of `t`. With three, inserts `v`
at position `pos` and moves the elements from `pos` on up by one. A `pos`
greater than `#t` appends. `pos` must be at least 1 (see
[Known issues](#known-issues)). Returns nothing. Appending `nil` does
nothing.

```lua
local t = {"b", "d"}
table.insert(t, "e")
table.insert(t, 1, "a")
table.insert(t, 3, "c")
table.insert(t, 99, "f")
print(#t, table.concat(t, " "))
table.insert(t, nil)
print(#t)
```

```output
6       a b c d e f
6
```

### table.remove(t [, pos])

Removes the element at position `pos` (default `#t`, the last one), moves
the following elements down by one, and returns the removed value. If `t`
is empty or `pos` is outside 1 to `#t`, it returns `nil` and changes
nothing.

```lua
local t = {"a", "b", "c", "d"}
print(table.remove(t), table.remove(t, 1), table.concat(t, " "))
print(table.remove(t, 5), table.remove({}), #t)
```

```output
d       a       b c
nil     nil     2
```

A stack and a queue:

```lua
local stack = {}
table.insert(stack, 1) table.insert(stack, 2) table.insert(stack, 3)
print(table.remove(stack), table.remove(stack))
local queue = {"first", "second"}
print(table.remove(queue, 1), #queue)
```

```output
3       2
first   1
```

### table.concat(t [, sep])

Joins the elements of the array part into one string, with `sep` (default
`""`) between them. Elements may be strings or numbers (numbers are
written as by `tostring`). Any other element raises
`invalid value (at index N) in table for 'concat'`. Lua's `i` and `j`
arguments are ignored. `sep` may be a number.

```lua
print(table.concat({1, 2.5, "x"}), table.concat({"a", "b", "c"}, ", "))
print("[" .. table.concat({}) .. "]", table.concat({1, 2}, 0))
print(table.concat({"a", true}))
```

```output
12.5x   a, b, c
[]      102
prog.wsk:3: invalid value (at index 2) in table for 'concat'
```

### table.sort(t [, less])

Sorts the array part of `t` in place and returns nothing. The sort is
stable: equal elements keep their order.

Without `less`, numbers sort from smallest to largest and strings sort by
CP437 code, which is case-sensitive (all uppercase letters before
lowercase). A table that mixes numbers and strings, or holds other types,
raises `attempt to compare number with string` (or similar).

With `less`, `table.sort` calls `less(a, b)`, which should return `true`
when `a` must come before `b`. Any value other than `false` or `nil` counts
as true, so return a comparison, not a number. The comparator cannot wait
(`sleep`, `io.read`...), and an error inside it ends the program even
inside `pcall` (see [Known issues](#known-issues)).

```lua
local n = {10, 9, 100, 1.5, -2}
table.sort(n)
print(table.concat(n, " "))
table.sort(n, function(a, b) return a > b end)
print(table.concat(n, " "))
local s = {"banana", "Apple", "cherry", "apple"}
table.sort(s)
print(table.concat(s, " "))
table.sort(s, function(a, b) return a:lower() < b:lower() end)
print(table.concat(s, " "))
```

```output
-2 1.5 9 10 100
100 10 9 1.5 -2
Apple apple banana cherry
Apple apple banana cherry
```

Sorting records by a field, stably:

```lua
local people = {
  {name = "Ann", age = 30}, {name = "Bob", age = 25},
  {name = "Cat", age = 30}, {name = "Dan", age = 25},
}
table.sort(people, function(a, b) return a.age < b.age end)
for _, p in ipairs(people) do print(p.age, p.name) end
```

```output
25      Bob
25      Dan
30      Ann
30      Cat
```

```lua
local ok, e = pcall(function() table.sort({3, "x", 1}) end)
print(e)
```

```output
prog.wsk:1: attempt to compare string with number
```

### table.unpack(t)

The same function as [`unpack`](#unpackt): returns `t[1]` ... `t[#t]` as
separate values. Extra arguments are ignored.

```lua
local a, b, c, d = table.unpack({1, 2, 3}, 2, 3)
print(a, b, c, d)
```

```output
1       2       3       nil
```

### table.keys(t)

Returns a new array of all keys of `t` that have a value. Array indices
come first, in order, then the other keys in the order they were added.
Removing a key moves the most recently added key into its place, so the
order changes. String keys keep the case they were first written with.

```lua
local t = {"a", "b", x = 1}
t.y = 2
t.Z = 3
local k = table.keys(t)
for i = 1, #k do io.write(tostring(k[i]), " ") end
print()
t.x = nil
k = table.keys(t)
for i = 1, #k do io.write(tostring(k[i]), " ") end
print()
```

```output
1 2 x y Z
1 2 Z y
```

Visiting keys in sorted order:

```lua
local stock = {pears = 4, apples = 7, figs = 1}
local names = table.keys(stock)
table.sort(names)
for _, k in ipairs(names) do print(k, stock[k]) end
```

```output
apples  7
figs    1
pears   4
```

### table.count(t)

Returns the number of entries in `t` with a non-`nil` value, counting the
array part and all other keys. Compare `#t`, which is the length of the
array part only and also counts holes.

```lua
local t = {10, 20, 30, name = "x", size = 2}
print(#t, table.count(t))
t[2] = nil
print(#t, table.count(t))
print(#{a = 1, b = 2}, table.count({a = 1, b = 2}), table.count({}))
```

```output
3       5
3       4
0       2       0
```

Holes and `#`: a key just past the end of the array joins it, a key
further out does not until the gap is filled.

```lua
local u = {}
u[1] = "a" u[2] = "b" u[4] = "d"
print(#u, table.count(u))
u[3] = "c"
print(#u, table.count(u))
```

```output
2       3
4       4
```

### table.copy(t)

Returns a new table with the same keys and values as `t`. The copy is
shallow: a table stored inside `t` is shared, not copied.

```lua
local inner = {1}
local t = {inner, 2, k = "v"}
local c = table.copy(t)
c[2] = 99
print(c == t, t[2], c[2], c.k, c[1] == inner)
```

```output
false   2       99      v       true
```

### table.find(t, v)

Returns the first index `i` in the array part where `t[i] == v`, or `nil`.
The comparison is `==`: no conversion between numbers and strings, and
strings are case-sensitive. Keys outside the array part are not searched.

```lua
local t = {"a", "b", "c", "b"}
print(table.find(t, "b"), table.find(t, "B"), table.find({1, 2, 3}, "2"), table.find({x = 5}, 5))
```

```output
2       nil     nil     nil
```

Removing a value by searching for it:

```lua
local t = {"red", "green", "blue"}
local i = table.find(t, "green")
if i then table.remove(t, i) end
print(table.concat(t, ","))
```

```output
red,blue
```

### table.reverse(t)

Reverses the order of the array part of `t` in place. It returns nothing
(not the table). Other keys are not changed.

```lua
local t = {1, 2, 3, 4, k = "v"}
print(table.reverse(t))
print(table.concat(t, " "), t.k)
```

```output
nil
4 3 2 1 v
```

To get a reversed copy and keep the original, copy first:

```lua
local t = {1, 2, 3}
local r = table.copy(t)
table.reverse(r)
print(table.concat(t, " "), table.concat(r, " "))
```

```output
1 2 3   3 2 1
```

## Known issues

These behaviours look like bugs. Avoid relying on them.

* **Not-a-number prints as `inf`.** `0/0`, `math.sqrt(-1)` and
  `math.log(-1)` produce NaN, but `tostring` shows `inf`, and `nan == nan`
  is `true`. Numbers smaller than about 1e-295 (such as `5e-324`) print as
  `NaN`.
* **`string.byte` returns 63 for many characters.** Only printable ASCII,
  tab, newline, carriage return, escape and the few CP437 characters the
  system draws (such as `é`) get their real code. Others, such as `É`, `ß`
  and most box-drawing characters, give 63. For the same reason
  `string.upper` and `string.lower` leave most accented letters unchanged,
  sorting treats those characters as `?`, and `==` may treat two of them as
  equal.
* **`pcall` and errors from operators.** When the error inside `pcall`
  comes from an operator rather than a function call, `pcall` returns the
  wrong values. Indexing `nil` (`t.x` with `t` = `nil`) gives the message
  and `nil` instead of `false` and the message; arithmetic on `nil` gives
  `nil, nil`; calling a method on a number (`n:upper()`) gives `true`.
  Outside `pcall` these errors are reported correctly. Until this is
  fixed, check values before using them, or raise the error yourself with
  `error`.
* **Line numbers in errors from one-line functions.** An error inside a
  function written on a single line, such as
  `pcall(function() return string.sub(s, "x") end)` passed on to another
  function, can report the line that was running before the call.
* **Errors in a `table.sort` comparator** are not caught by `pcall`; the
  program ends.
* **`exit(true)` and `exit(false)`** raise an error instead of exiting with
  code 0 or 1.
* **`table.insert(t, pos, v)` with `pos` below 1** writes outside the
  table instead of raising an error. The value is lost and other data may
  be damaged.
* **`tonumber`** returns `0` for strings like `"0x1g"` (starting with `0x`
  but not valid hex), and accepts bases outside 2 to 36.
* **`string.format("%x", n)`** gives an empty string for negative `n`, and
  `%d` of a number between -1 and 0 gives `-0`.
* **`string.find(s, "", init)`** returns `init` even when `init` is past
  the end of `s`.
* **`math.min`** reports its argument errors as `'max'`.

See also: [language.md](language.md) for the syntax these functions are used
with, [system.md](system.md) for `io`, `os`, `fs` and `proc`,
[terminal.md](terminal.md), [libraries.md](libraries.md) for `load` and
`require`, and the [README](README.md).
