# Whisker

Whisker is ScratchOS's programming language. It looks like Lua. The kernel
compiles it to bytecode and runs it on a preemptive virtual machine. Every
program in `/bin` is written in Whisker; read them with `cat /bin/ls.wsk`.

```
run prog.wsk args      # or just prog.wsk if it is in the current directory
whisker                # interactive REPL
edit prog.wsk          # write one (Esc -> R runs it)
```

## Language

```lua
-- line comment            --[[ block comment ]]
local x, y = 1, "two"      -- locals; assignment without `local` makes a global
local t = {10, 20, name = "x", ["key with space"] = true}
print(#t, t[1], t.name)    -- 2  10  x

if x > 0 and y ~= nil then ... elseif x == 0 then ... else ... end
while cond do ... end
repeat ... until cond
for i = 1, 10, 2 do ... end
for k, v in pairs(t) do ... end        -- array part first, then other keys
for i, v in ipairs(t) do ... end
break   continue                        -- `continue` is a Whisker addition

function add(a, b) return a + b end
local function fib(n) if n < 2 then return n end return fib(n-1) + fib(n-2) end
local q, r = divmod(7, 2)              -- multiple return values
local f = function(v) return v * 2 end

local obj = {count = 0}
function obj:inc(n) self.count = self.count + n end
obj:inc(5)

local ok, err = pcall(function() error("boom") end)   -- ok == false, err == "...: boom"
local chunk = load("return 1 + 2")                    -- compile code at run time
local util = require("util")                          -- loads /lib/util.wsk once
```

Operators, from lowest to highest precedence: `or`, `and`,
`< > <= >= ~= ==` (`!=` also works), `..`, `+ -`, `* / // %`, unary
`not # -`, `^`. Strings support escapes `\n \t \e \\ \" \xHH \ddd` and long
brackets `[[...]]`.

**Differences from Lua**

* A function can use its own locals, globals, and the program's **top-level**
  locals. It cannot use locals of another enclosing function, because there
  are no general closures. The compiler reports an error if you try.
* No metatables, coroutines or varargs (`...`). Generic `for` supports
  `pairs(t)` and `ipairs(t)`.
* String keys of tables ignore letter case (`t.Name` is `t.name`). String
  *comparison* (`==`, `<`) is case-sensitive.
* Numbers and numeric strings convert in arithmetic, like Lua.
* Character codes are code page 437 (`string.byte("é")` is 130).

## Library

**Base:** `print(...)`, `tostring(v)`, `tonumber(s [, base])`, `type(v)`,
`error(msg)`, `pcall(f, ...)`, `assert(v [, msg])`, `select(n, ...)`,
`unpack(t)`, `sleep(sec)`, `exit([code])`, `load(src)`, `require(name)`.

**string** (also callable as methods, e.g. `s:upper()`): `len sub upper lower find(s, text [, init]) rep byte char format split(s [, sep]) trim reverse startswith endswith replace(s, from, to) lines pad(s, width) contains`.
`find` and `replace` work on plain text (no patterns). `format` supports
`%d %i %s %f %x %X %c %q %%` with flags `-` and `0`, width, and precision.

**math:** `floor ceil abs sqrt sin cos tan asin acos atan atan2 exp log pow random([m [, n]]) max min fmod round tointeger`, plus `pi`, `huge` and `maxinteger`.

**table:** `insert(t, [pos,] v)`, `remove(t [, pos])`, `concat(t [, sep])`,
`sort(t [, less])`, `unpack`, `keys`, `count`, `copy`, `find(t, v)`,
`reverse`.

**io:** `write(...)`, `read()` (a line, or nil at end of input),
`readall()`, `lines()` (all remaining lines as a table), `error(...)`
(to stderr), `isatty()`.

**os:** `time()` (Unix seconds), `clock()`, `millis()`, `date()`, `getenv(k)`,
`setenv(k, v)`, `exit`, `sleep`, `pid()`, `args()`, `uptime()`.

**fs** (paths are relative to the current directory; failures return
`nil, message`):

| Function | Returns / notes |
|---|---|
| `read(p)` | file contents |
| `write(p, s)` | |
| `append(p, s)` | |
| `list([dir])` | sorted names |
| `exists(p)` | |
| `isdir(p)` | |
| `mkdir(p)` | |
| `remove(p [, recursive])` | |
| `rename(a, b)` | |
| `copy(a, b)` | |
| `stat(p)` | `{name, path, type, size, mtime, date, inode, protected}` |
| `cwd()` | current directory |
| `chdir(p)` | |
| `abs(p)` | absolute path |
| `name(p)` | last component |
| `dir(p)` | parent directory |

**proc:**

| Function | Returns / notes |
|---|---|
| `spawn(cmdline)` | pid |
| `wait(pid)` | exit code |
| `run(cmdline)` | output, code |
| `kill(pid)` | |
| `list()` | `{pid, ppid, name, path, state, cpu, time, tty, kind, mem}` |
| `alive(pid)` | |
| `pid()` | own pid |

**term** (the program's terminal): `clear()`, `color(fg [, bg])`,
`goto(x, y)` (1-based), `size()` returning `w, h`, `getpos()`, `raw(on)`
(deliver single keys), `getkey()` (a key, or nil), `waitkey()`,
`cursor(on)`, `put(x, y, text [, fg, bg])` (write without moving the
cursor), `write(s)`.
Key names: single characters, `"enter" "backspace" "delete" "escape" "up arrow" "down arrow" "left arrow" "right arrow" "home" "end" "page up" "page down" "insert"`, and `"^c"` style for Ctrl.

**gui** (needs the desktop and the `gui` capability): `window(title, w, h)`
returns a window id; `close(win)`; `event(win)` (a table or nil);
`waitevent(win)`; `size(win)`; `title(win, text)`; `active(win)`;
`terminal([cmd])`. Events are tables with `type` set to `"key"` (with
`key`), `"mousedown"`, `"drag"` or `"mouseup"` (with `x`, `y` in window
pixels), `"resize"` (with `x`, `y` = new size), or `"close"`.

**gfx** (all take a window first; colours 0–15): `clear(win, c)`,
`pixel(win, x, y, c)`, `line(win, x1, y1, x2, y2, c [, size])`,
`rect(win, x, y, w, h, c)`, `fill(win, x, y, w, h, c)`,
`circle(win, x, y, r, c)`, `disc(win, x, y, r, c)`,
`text(win, x, y, s, fg [, bg])`.

**sys:** `version()`, `uptime()`, `mem()`, `hostname()`, `caps()`,
`request(cap)`, `gc()`, `procs()`, `date()`, `shutdown()`, `reboot()`.

## Colours

| 0 black | 1 blue | 2 green | 3 cyan | 4 red | 5 magenta | 6 brown | 7 light grey |
|---|---|---|---|---|---|---|---|
| **8 dark grey** | **9 light blue** | **10 light green** | **11 light cyan** | **12 light red** | **13 light magenta** | **14 yellow** | **15 white** |

In terminal output you can also use ANSI escapes:
`print("\e[93mwarning\e[0m")`.

## Permissions

Sensitive calls need a capability:

| Capability | Calls |
|---|---|
| `files` | writing outside `/home` and `/tmp` |
| `proc` | killing processes the program did not start |
| `gui` | `gui.window`, `gui.terminal` |
| `system` | `sys.shutdown`, `sys.reboot` |

The first use asks the user: (y)es, (n)o or (a)lways. Declare needs on any
comment line to be asked when the program starts:

```lua
--@caps gui files
```

`caps` in the shell shows the policy (`/etc/caps`) and what running programs
hold. Programs in `/bin` are trusted by default.
