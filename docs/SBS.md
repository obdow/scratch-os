# SBS, the Scratch Build Source language

`tools/sbc.py` compiles SBS files into Scratch 3 blocks. Every construct maps
to ordinary blocks, so the output can be opened and edited in Scratch or
TurboWarp.

## Top level

```c
const NAME = 42;                 // compile-time constant (numbers, strings, folded expressions)
global score = 0;                // stage (global) variable
global list queue;               // stage list
include "other.sbs";             // textual include (also allowed inside a sprite)

sprite Kernel {
    costumes "os_glyphs";        // costume groups provided by tools/assets.py
    prop visible = 1;
    var x = 0;                   // sprite variable
    list cells = [1, 2, 3];      // list with initial contents
    list rootfs = data("rootfs_paths");   // contents supplied by build.py
    proc name(a, b) { ... }      // custom block, "run without screen refresh"
    proc slow() nowarp { ... }   // normal (screen-refreshing) custom block
    proc fact(n) recursive { ... }        // locals saved/restored -> recursion works
    on flag { ... }              // when green flag clicked
    on clone { ... }             // when I start as a clone
    on msg "name" { ... }        // when I receive
}
```

## Statements

```c
x = expr;   x += 1;   x -= 1;   x *= 2;   x /= 2;   x %= 3;   x ..= "s";   x++;   x--;
local y = expr;                          // proc-local (a mangled sprite variable)
list[i] = v;   list[i] += 1;             // replace item
if (c) { } else if (c) { } else { }
while (c) { }   until (c) { }   repeat (n) { }   forever { }
for (init; cond; step) { }   for i = a to b step s { }
switch (e) { case 1, 2: { } case 3: { } default: { } }   // binary-search tree of ifs
break;  continue;  return expr;
proc_call(args);   builtin(args);
```

`break` and `continue` are implemented with flag variables. `switch` cases
must be numeric constants. It is used for VM opcode dispatch.

## Expressions

`+ - * / %`, `..` (join), `== != < > <= >=`, `&& || !`, and `c ? a : b`.

A list name followed by `[i]` gives an item. Any other name followed by
`[i]` gives a letter.

A call to a user `proc` inside an expression is hoisted into statements, and
its result is read from the hidden variable `_r`. The `&&`, `||` and `?:`
operators keep short-circuit behaviour when the right side contains a call.

## Built-ins

| Kind | Functions |
|---|---|
| lists | `add(l, v)` `del(l, i)` `clear(l)` `insert(l, i, v)` `len(l)` `index(l, v)` `has(l, v)` |
| strings | `len(s)` `letter(s, i)` `contains(a, b)` `join(a, b, ...)` |
| math | `round floor ceil abs sqrt sin cos tan asin acos atan ln log10 exp pow10 random(a, b) num(x)` |
| sensing | `key(k)` `mouse_x()` `mouse_y()` `mouse_down()` `timer()` `days2000()` `now("hour")` `username()` |
| looks | `costume(c)` `costume_num()` `costume_name()` `effect("color", v)` `clear_effects()` `show()` `hide()` `size(s)` `front()` |
| motion | `goto(x, y)` `set_x` `set_y` `change_x` `change_y` `x_pos()` `y_pos()` |
| pen | `stamp()` `pen_down()` `pen_up()` `pen_clear()` `pen_color(rgb)` `pen_size(n)` |
| control | `wait(s)` `wait_until(c)` `broadcast("m")` `broadcast_wait("m")` `clone_self()` `delete_clone()` `stop_all()` `stop_others()` `stop_script()` |

## Safety rewrite

Scratch considers `"0"` equal to `" "` and `""`, and TurboWarp treats
constant whitespace strings as the number 0. So `x == "<whitespace>"` is
compiled as `len(x) == len(W) && contains(W, x)`, and `x == ""` as
`len(x) == 0`.
