# How Whisker works inside

This chapter explains what happens to a Whisker program between `run prog.wsk` and its last
instruction. It covers the compiler, the bytecode, the virtual machine, scheduling, memory and
the hard limits. You don't need any of it to write programs, but it explains the rules that can
seem odd, such as why functions can't see each other's locals, and it helps with performance.
Everything lives in the Kernel sprite as SBS code (see [../SBS.md](../SBS.md)). SBS compiles to
ordinary Scratch blocks.

* [The pipeline](#the-pipeline)
* [The compiler](#the-compiler)
* [Bytecode](#bytecode)
* [The virtual machine](#the-virtual-machine)
* [Built-in functions](#built-in-functions)
* [Errors and pcall](#errors-and-pcall)
* [Scheduling](#scheduling)
* [Memory and garbage collection](#memory-and-garbage-collection)
* [Limits](#limits)
* [Performance](#performance)

## The pipeline

```
prog.wsk ──lexer──▶ tokens ──parser + code generator──▶ bytecode in CODE ──VM──▶ results
            (wcomp.sbs)            (one pass, wcomp.sbs)        (cached)        (vm.sbs)
```

1. **Lookup.** The shell finds the file, and `vm_spawn` (in `src/vm.sbs`) checks the code cache.
   Compiled code is kept per file, keyed by inode and modification time, so starting a program
   again skips compiling until the file changes. Several running copies share one code segment.
2. **Compile.** `src/wcomp.sbs` turns the source into bytecode in one pass. A compile error stops
   here. The shell prints `path: line N: message` and `$?` is 127.
3. **Start.** The VM gives the new process a value stack, a call stack and a globals table, and
   runs any `--@caps` requests first (see [system.md](system.md)).
4. **Run.** The scheduler runs the process a slice at a time until it returns from the main chunk,
   calls `exit`, fails with an uncaught error, or is killed.

`load(src)` and `require(name)` use the same compiler at run time. Their chunks share the
program's globals (see [libraries.md](libraries.md)).

## The compiler

**Lexer.** It reads the whole source into parallel token lists: kind, value and line. Strings
come out fully decoded, with escapes applied. Numbers are converted to values. Comments vanish.
Lexical errors include `unfinished string`, `unfinished long string`, `malformed number '1..2'`
and `unexpected character`.

**Parser and code generator.** This is a single-pass recursive-descent parser. Expressions use
Lua's *expression descriptor* technique: a parsed expression is described first (a constant, a
local slot, a global, an indexed value, a call...) and turned into code only when its use is
known. That is how `a.b.c = v` becomes one store, and how `x and y or z` jumps without extra
temporaries. The compiler emits code straight into a buffer. There is no syntax tree and no
optimisation pass.

**Scopes.** Each function has its own numbered local slots. Blocks reuse slots after they end.
The compiler resolves a name in this order:

1. a local of the current function;
2. a local of the **main chunk** (only when the function was written at the top level of the
   file), reached with `GETM`/`SETM`;
3. a built-in module name, such as `string` or `math`, which becomes a native reference at compile
   time;
4. otherwise, a global.

A function can't reach the locals of *another enclosing function*, because Whisker has no general
closures; the compiler reports this as an error. Main-chunk locals work because the main
chunk's frame lives as long as the program does. See
[language.md](language.md#what-a-function-can-see).

**Lines.** The compiler emits `LINE n` whenever the source line changes, and at the start of
each function body. The VM keeps the current line, and each call frame saves the caller's line,
so error messages name the right line after a call returns.

**Position-independent code.** Jumps and function addresses are relative to the instruction, so
a compiled segment can be loaded anywhere in `CODE`.

## Bytecode

`CODE` is one big list. An instruction is an opcode cell, followed by 0–2 operand cells. The VM
is a stack machine: operands are pushed, and operators pop them and push the result. There are
55 opcodes, listed at the top of `src/wcomp.sbs`.

| Group | Opcodes |
|---|---|
| constants | `PUSHNIL` `PUSHTRUE` `PUSHFALSE` `PUSHN n` `PUSHS s` `PUSHNAT id` `FUNC off` |
| variables | `GETL slot` `SETL slot` (locals), `GETM` `SETM` (main-chunk locals), `GETG slot` `SETG slot` (globals) |
| stack | `POP` `DUP` |
| arithmetic | `ADD` `SUB` `MUL` `DIV` `MOD` `POW` `IDIV` `NEG` |
| strings and length | `CONCAT` `LEN` |
| logic and comparison | `NOT` `EQ` `NE` `LT` `LE` `GT` `GE` |
| jumps | `JMP off`; `JF`/`JT` (pop the value, jump if false/true); `JFK`/`JTK` (keep the value when jumping, for `and`/`or`) |
| tables | `NEWTABLE` `GETINDEX` `SETINDEX` `GETFIELD k` `SETFIELD k` `SETFIELDK` `APPEND` `SELF k` |
| calls | `CALL n w` (n arguments, w results wanted), `CALLN id n w` (a built-in known at compile time, such as `math.abs`, called directly), `RET n`, `RETNIL` |
| loops | `FORCHK` `FORINC` (numeric `for`), `ITERP` `ITERI` (`pairs`/`ipairs`) |
| other | `LINE n`, `HALT` |

`pairs` and `ipairs` aren't functions: the compiler recognises them in a generic `for` and emits
`ITERP` or `ITERI`. That is why they can't be stored in variables or passed around.

Every call site states how many results it wants (`w`). The callee's results are adjusted to
that count, padded with `nil` or cut short. This is why only an assignment with several targets
receives several values (see [language.md](language.md#multiple-results)).

## The virtual machine

**Values.** Every value is a pair: a *value* cell and a *tag* cell, held in two parallel lists
(`STK`/`STT` on the stack, `HV`/`HT` in the heap).

| Tag | Type | Value cell holds |
|---|---|---|
| 0 | nil | `""` |
| 1 | number | the number |
| 2 | string | the string itself (strings are Scratch values, not heap objects) |
| 3 | boolean | 1 or 0 |
| 4 | table | a table handle |
| 5 | function | the absolute code address |
| 6 | native | a built-in function id |

**Registers.** These are kept in kernel variables while a process runs and saved into the
process table when it is switched out:
* `vm_pc` (the instruction);
* `vm_sp` (the stack top);
* `vm_fp` (the frame's first local);
* `vm_csp` (the call stack top);
* `vm_line`;
* the bases of the process's stack, call stack, code segment and globals.

**Frames.** A call pushes 5 cells on the call stack:
1. the return pc;
2. the caller's frame pointer;
3. where the results go;
4. how many results are wanted;
5. flags, which hold `pcall` = 1 plus twice the caller's line.

Arguments become the first locals of the new frame. Missing ones are set to `nil` and extra ones
are dropped.

**The dispatch loop.** `vm_exec` reads an opcode and runs it. SBS compiles the `switch` into a
binary tree of `if` blocks, so finding an opcode takes about six comparisons. The common cases
are written inline: for example, `ADD` of two numbers doesn't call a helper. In headless,
software-rendered Chromium the loop runs a few million simple instructions per second.

## Built-in functions

A built-in is a value tagged *native* with an id from `tools/natives.py`. Its position in that
list is the id, and `build.py` exports constants such as `N_STRING_SUB`. `CALL` on a native goes
to `native_call`. That dispatches to:
* `nat_core` for the base library, `string`, `math`, `table`, `io` and `os`;
* `nat_sys` for the rest (`fs`, `proc`, `term`, `gui`, `gfx`, `image`, `sys` and `net`).

Results go through a small list (`nr_v`/`nr_t`) and are adjusted to the count the call site
wants.

**Blocking.** A native that has to wait, for input, `sleep`, a permission prompt or a network
answer, calls `nat_block(reason)` and returns without a result. The process is marked blocked,
and its pc stays on the `CALL`. When the scheduler wakes the process, the same instruction runs
again. This time the native finds its input ready and returns normally. There is no
continuation or saved native state, just a retry. So blocking natives keep their progress in
kernel lists (for example `p_wake` for `sleep`, or the request table for `net`).

**Callbacks.** `table.sort` comparators and `require`d module bodies run *synchronously*:
1. the native pushes a call;
2. it runs a nested `vm_exec` until the call returns;
3. it carries on.

A callback can't block. `cannot wait inside a callback` is raised instead, because the native
underneath it can't be suspended. For the same reason, `table.sort` can't be called again from
inside its own comparator; you get an error.

## Errors and pcall

`error()`, and every runtime error, go through `vm_raise(msg)`. It prefixes the message with the
program's file name and the current line, then looks down the call stack for a frame flagged as
a `pcall`.

* **Not found:** the message is written to the program's stderr (in red on a terminal, or in a
  message box for desktop programs). The process ends with exit code 1.
* **Found:** the error is *pending*. The instruction that raised it still finishes, and later
  raises from the same instruction are ignored. Then the loop unwinds to the pcall frame and
  places `false, message` there as pcall's results. If the pcall belongs to code outside a
  running callback, the callback's loop stops first, and the outer loop does the unwinding.

`pcall` itself is compiled as a call with the pcall flag. That is why it accepts only Whisker
functions: wrap a built-in as `pcall(function() return fs.read(p) end)`.

## Scheduling

ScratchOS runs one Scratch `forever` loop. Each frame (60 per second):

1. **Input.** The kernel handles keyboard and mouse input.
2. **Processes.** It calls `sched_run` with a budget of about 8–10 ms. The scheduler goes round
   the process table, round robin. Each ready Whisker process runs up to **4,000 instructions**
   per turn, and the scheduler keeps going round until the budget is spent.
3. **Screen.** It redraws the screen.

Scheduling is **preemptive**: a program in an endless loop still gives up the processor after
each slice, so the desktop and other programs keep running.

* **Blocked processes** are retried once a frame. Sleepers wake when their time comes.
* **Batched frames:** a process between `gfx.batch()` and `gfx.flush()` gets slices of 60,000
  instructions, so its frame is drawn in one go.
* **Busy programs** get a share of each frame, not all of it, and the scheduler stops for the
  frame when the budget is spent. A tight loop of simple instructions gets through a few hundred
  thousand instructions per second.

## Memory and garbage collection

**Tables.** All tables live in two shared heap lists (`HV`/`HT`). A table is a *handle* into a
registry of parallel `tb_*` lists. Each table records:
* an **array part**: the values for keys 1..n, stored one after another, with a capacity that
  grows by doubling;
* a **hash part**: key/value pairs found by linear search, using Scratch's equality. That is why
  string keys ignore case.

Reading `t[i]` from the array part costs the same whatever the table's size. A lookup in the
hash part slows down as the table gets more non-array keys. Use arrays for big collections,
and keep string-keyed tables small (objects and records).

**Strings** are plain Scratch values held in the stack or heap cells. They are not heap objects
and need no collection.

**Garbage collection** is mark-compact and stop-the-world. It runs at the start of a slice when
the heap has passed 120,000 cells.

1. **Mark.** Everything reachable is marked, starting from these roots:
   * every running program's stack and globals table;
   * tables the kernel pins, such as window display lists.
2. **Sweep.** Unmarked tables are freed.
3. **Compact.** The heap is compacted.

`sys.gc()` runs a collection on demand. `sys.mem()` reports heap use (see [system.md](system.md)).
The heap is shared by all programs. A table's owner pid is recorded, and when a process ends
its tables become garbage.

## Limits

| What | Limit | When you exceed it |
|---|---|---|
| processes at once | 32 (`MAX_PROC`) | `cannot fork: process table full` |
| value stack per process | 3,000 cells (`STACK_SIZE`) | `stack overflow` |
| call stack per process | 1,000 cells, so about 200 nested calls (`CS_SIZE` / 5) | `stack overflow` |
| compiled code, all programs together | 150,000 cells (`CODE_LIMIT`) | the program can't be loaded; unused segments are freed and reused first |
| heap | not fixed; a collection runs at 120,000 cells | Scratch lists hold up to 200,000 items each |
| one callback (sort comparator, module body) | 5,000,000 instructions | the callback stops early; longer callbacks aren't supported |
| `image` pictures | 65,536 pixels | see [graphics.md](graphics.md) |
| numbers | IEEE double; integers are exact up to 2^53, but output shows 14 significant digits | |

## Performance

These figures come from runs in headless Chromium, timed with `os.millis()` around loops of
20,000 iterations. Absolute times vary with the machine and with what else is running, so treat
them as rough ratios.

* **Instruction count is what matters.** Each Whisker operation is several Scratch blocks.
  Anything that removes instructions from a hot loop helps.
* **Function calls are the expensive part.** `x = inc(x)` with a one-line Whisker function took
  about twice as long as `x = x + 1`: the frame push, argument adjustment and return cost
  several instructions. A built-in such as `math.abs(x)` is called directly (`CALLN`) and is
  cheaper. Inline tiny helpers inside hot loops.
* **`t[#t + 1] = v` is faster than `table.insert(t, v)`**: about 1.5× in our measurements.
* **Locals, top-level locals and globals are all fast.** Globals are numbered slots, not looked
  up by name, so the differences are small. Prefer locals for clarity, not speed.
* **Field access (`p.x`) searches the table's hash part.** It is about as fast as a local for a
  small object, but slows down as the object gets more fields. Copy a field into a local before
  a long loop if it doesn't change.
* **String building is fine at small sizes.** Building a 2,000-character string with `..` took
  about the same time as filling a table and calling `table.concat`. For much longer text,
  collect pieces in a table and join them once, because each `..` copies the whole string.
* **Drawing:** use `gfx.batch()` / `gfx.flush()` around each frame, and see the performance notes
  in [graphics.md](graphics.md).
* **Don't busy-wait.** The scheduler preempts long computations, so the desktop stays usable, but
  a loop that polls for something burns its whole share. Use `gui.waitevent`, `term.waitkey`,
  or `sleep(seconds)` with a real delay. `sleep(0)` returns at once and doesn't yield.

See also: [language.md](language.md), [stdlib.md](stdlib.md), [system.md](system.md),
[../ARCHITECTURE.md](../ARCHITECTURE.md).
