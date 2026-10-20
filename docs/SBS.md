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
    sounds "w3d_sfx";            // sound groups (tools/assets.py: sound_group)
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
| pen | `stamp()` `pen_down()` `pen_up()` `pen_clear()` `pen_color(rgb)` `pen_size(n)` `pen_alpha(t)` (transparency 0..100) |
| sound | `sound_start(name)` `sound_stop_all()` `sound_volume(v)` `sound_pitch(v)` `sound_pan(v)` |
| music | `music_note(note, beats)` `music_drum(drum, beats)` `music_rest(beats)` `music_instrument(i)` `music_tempo(bpm)` (the Music extension is added to the project when one is used) |
| control | `wait(s)` `wait_until(c)` `broadcast("m")` `broadcast_wait("m")` `clone_self()` `delete_clone()` `stop_all()` `stop_others()` `stop_script()` |

## Constant folding

Expressions made only of constants are computed by the compiler, including
comparisons and `&&` / `||`. An `if` whose condition folds to a constant
compiles to just the branch that runs, so build constants switch whole
features off:

```c
const HAS_NET = 0;               // build.py sets these per target
if (HAS_NET == 1) { net_init(); }    // no blocks at all in this build
```

Pruning then drops the procedures that only the removed branch called.

## Safety rewrite

Scratch considers `"0"` equal to `" "` and `""`, and TurboWarp treats
constant whitespace strings as the number 0. So `x == "<whitespace>"` is
compiled as `len(x) == len(W) && contains(W, x)`, and `x == ""` as
`len(x) == 0`.

## Pruning

After compiling, `prune_unused` (called by `build.py`) removes what a build
cannot use:

1. **Custom blocks** that no hat script reaches, following call chains.
   Code shared by ScratchOS and the stand-alone IDE (such as the IDE's
   boot, or the shell) is dropped from the build that never runs it.
2. **Writes** to variables and lists that nothing reads. A Scratch reporter
   has no side effects, so such a `set` / `change` / list write can be
   deleted. This repeats until nothing changes.
3. **Variables and lists** that no remaining block mentions.

`build.py` keeps `kb_ready` and `frames`, which the test harness reads. Set
`SBC_PRUNED=file` to get the list of what was removed.
