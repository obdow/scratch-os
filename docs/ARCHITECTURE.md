# ScratchOS architecture

ScratchOS is two sprites:

* **Keyboard** has one clone per physical key. It also paces frames.
* **Kernel** runs everything else. It is hidden and draws only by stamping
  its own costumes into the pen layer.

The kernel runs one `forever` loop. Each frame it calls `tick()`, a
run-without-screen-refresh custom block:

```
input_poll()      drain the keyboard queue, route keys (tty / window / dialog)
wm_tick()         mouse, window dragging, recomposition       (desktop only)
sched_run(ms)     run processes for a time budget
wm_update()       redraw changed screen cells                 (desktop only)
tty_render()      draw dirty terminal cells
tty_cursor_update()  blinking text cursor
wm_pointer()      mouse pointer                               (desktop only)
```

## Graphics: the pen text engine (`src/gfx.sbs`, `tools/assets.py`)

* The screen is 480×360, which is a 60×22 grid of 8×16 cells.
* `tools/assets.py` turns the VGA ROM font into 256 glyph costumes, stored as
  2× PNGs with the rotation centre at the top-left. Stamping at integer
  positions is pixel exact.
* **Colours without 4096 costumes.** Each glyph exists twice, in white and in
  dark red `#AA0000`. Scratch's *brightness* effect adds a constant to R, G
  and B. Its *colour* effect rotates hue. So:
  * greys = white glyph + brightness (0, −33.3, −66.7, −100)
  * the six VGA hues and brown (hue 30°) = red glyph + colour effect
  * bright colours = the same + brightness +33.3 (because `0x55 = 0xFF − 0xAA`)

  This reproduces all 16 VGA colours exactly. The smoke test checks this
  pixel by pixel.
* Solid rectangles use 81 power-of-two rectangle costumes (1…256 px per side),
  so any fill takes at most 4 stamps.
* Lines use the pen. The mouse pointer is two stamped glyphs (outline + body).
* **The Whisker IDE's palette** (`src/ide/gfx.sbs`, `tools/ide_assets.py`)
  extends the same trick to arbitrary RGB. The colour effect rotates hue in
  HSV and keeps the *chroma* (max − min channel); brightness then shifts all
  three channels. So one base set of chroma C reaches every colour with
  chroma C exactly. The IDE's 112 palette entries (16 terminal colours for
  each theme, 32 UI colours for each theme) are clustered into 8 chroma
  levels plus grey, giving 9 base sets of glyphs and 81 rects each.
  Each palette entry stores its set's costume numbers, hue and brightness.
  The IDE ships only the 104 characters it actually shows: printable ASCII,
  its UI symbols (drawn procedurally) and the non-ASCII characters in its
  bundled files. A code-to-slot list (`gmap`) maps every other CP437 code to
  `?`. Because glyph costumes are no longer numbered by code, the shared
  `ord()` maps costume numbers back to codes through `glyph_code` (the
  identity in ScratchOS). Thin borders, accent underlines
  and the scrollbar are extra 1–2 px rect stamps ("decos") carried in the
  cell attribute.

Measured in headless Chromium with software GL, a stamp costs about 11 µs and
a full 60×22 redraw about 29 ms. So everything redraws incrementally:
terminals track dirty cells, and the window manager diffs whole screens.

## Keyboard (`src/kbd.sbs`)

Every key (A–Z, digits, punctuation, and Enter/Backspace/arrows/…) gets a
clone. Each clone loops `wait until <key (k) pressed?>`, pushes an event
string into the global list `kb_queue`, and auto-repeats after 0.42 s.
Letters use the Shift and Caps Lock state. Ctrl+key produces `"^c"`.
TurboWarp reports shifted symbols (`!`, `@`, …) as their own keys.

Polling cannot see a press shorter than one frame. Real keypresses are much
longer, but a very slow frame can lose a keystroke.

The parent Keyboard sprite stays visible with a blank costume and moves to
the same spot every frame. That requests a redraw, so the Scratch sequencer
runs each thread once per frame instead of spinning idle loops.

## Terminals (`src/tty.sbs`)

A tty is a grid of CP437 codes and attributes (`fg + 16·bg`) stored in shared
lists. Rows form a ring buffer, so scrolling is O(width). Output understands
ANSI SGR colours, `ESC[2J`, `ESC[H`, `ESC[K` and cursor moves. Cooked mode
does line editing and history. Raw mode hands every key to the foreground
process (`term.raw(true)`).

`ord()` uses the **costume trick**. Glyph costumes are named by their Unicode
character, and costume lookup by name is case-sensitive, so
`switch costume to (ch)` followed by `costume #` gives a case-sensitive
character code. Scratch has no other way to tell "a" from "A".

## File system (`src/fs.sbs`, `tools/rootfs.py`)

Inodes are parallel lists. Directory lookup searches the list
`fs_key = "<parent>/<name>"` with `item # of`, so names are case-insensitive
but case-preserving. The `rootfs/` directory is baked into list data and
loaded at every boot. Nothing persists between runs.

## Processes (`src/proc.sbs`)

32 process slots. Kinds: native shell, Whisker VM program, init. File
descriptors are (kind, id) pairs: tty, pipe, file (append to an inode), null,
or message box. Pipes queue complete lines.

Scheduling is **preemptive**. Each frame the kernel runs ready processes
round-robin until the time budget (8–10 ms) is used. A VM process runs at most
4000 instructions per turn, so an infinite loop cannot freeze the OS.
Blocking calls (read, sleep, wait, permission prompts) leave the program
counter on the same instruction and retry it on a later frame.

TurboWarp's `timer` is frozen within a frame, so time budgets use
`days since 2000`, which has millisecond resolution.

## The shell (`src/shell.sbs`)

The shell is a state machine (PROMPT → READ → RUN → WAIT) run as a native
process. Each command line is executed one *and-or element* at a time, so
`a && b` can wait for `a`. Builtins run inside the shell. Other commands are
looked up on `$PATH` and started as Whisker programs. Files ending in `.sh`
run in a child shell.

## Whisker (`src/wcomp.sbs`, `src/vm.sbs`, `src/natives*.sbs`, `src/heap.sbs`)

* **Compiler.** Lexer, then a single-pass recursive-descent parser with Lua's
  expression-descriptor technique, emitting stack bytecode. Jumps and function
  addresses are relative to their own instruction, so code is position
  independent. Programs are cached by inode and modification time.
* **VM.** Each value is a (value, tag) pair in two parallel stacks. Tags are
  nil, number, string, boolean, table, function and native. Frames live on a
  separate call stack with 5 cells per frame. The dispatch loop is a
  compile-time binary `switch` tree over 55 opcodes. In software-rendered
  Chromium it runs about 2–5 million instructions per second.
* **Top-level locals.** The main chunk's frame lives for the whole run, so
  functions reach its locals directly with `GETM`/`SETM`. That covers the
  common Lua idiom of functions using file-level locals, including recursive
  `local function`s, without general closures.
* **Errors.** `pcall` frames are marked, and `error()` unwinds to the nearest
  one. `load()` compiles a chunk that shares the program's global slots.
  `require()` runs a module synchronously by re-entering the interpreter loop.
  `table.sort` comparators do the same.
* **Heap.** A table has an array part plus a hash part with linear search,
  stored in shared lists through a handle registry. Collection is
  mark-compact, run between instructions when the heap passes 120,000 cells.
  The roots are process stacks, globals, and kernel-pinned display lists.

## Capabilities (`src/caps.sbs`)

| Capability | Allows |
|---|---|
| `files` | modify outside `/home` and `/tmp` |
| `proc` | kill processes the program did not start |
| `gui` | open windows |
| `system` | power off or reboot |

`/etc/caps` grants capabilities by path (prefix `*` allowed). Otherwise the
first use blocks the process and asks the user, in the terminal or as a
desktop dialog. Programs can request capabilities at start with `--@caps`.

## Window manager (`src/wm.sbs`)

Windows are aligned to the cell grid. `wm_compose()` builds:

* `own[]`, the owner of every cell (desktop, taskbar, menu, dialog, or a
  window)
* `ui_ch[]`/`ui_at[]`, the glyph of every non-content cell

`wm_diff()` compares these with the previous frame and redraws only changed
cells. Content cells encode their window-relative position in the attribute,
so moving a window marks all its content dirty.

* **Terminal windows** are ttys whose visibility is checked against `own[]`.
* **Canvas windows** (graphics programs) keep a retained display list of
  primitives in a pinned heap table. New primitives draw immediately, clipped
  to the window's visible rectangles, which are the content rectangle minus
  every rectangle above it. Uncovered regions are repainted by replaying the
  list with the same clipping (Liang–Barsky lines, rectangle intersection,
  whole-glyph text).

## Scratch / TurboWarp quirks worked around

* `"0" = " "` and `"0" = ""` are **true** in Scratch's comparison (an
  `else if` skips the whitespace check). TurboWarp's compiler even treats a
  *constant* `"\t"` or `" "` as the number 0. The SBS compiler therefore
  compiles comparisons with whitespace literals as
  `length(x) = length(W) and W contains x`, and `x == ""` as `length(x) = 0`.
* String comparison and `item # of` ignore case. Case-sensitive equality goes
  through `ord()`, and table keys are documented as case-insensitive.
* `timer` is frozen inside a frame, so the kernel uses `days since 2000`.
* `switch costume to (x)` treats number-like *strings* as costume names first,
  so glyph numbers are always passed as computed numbers.
