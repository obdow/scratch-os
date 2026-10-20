# ScratchOS architecture

ScratchOS is two sprites:

* **Keyboard** has one clone per physical key. It also paces frames.
* **Kernel** runs everything else, including the desktop and the Whisker IDE.
  It is hidden and draws only by stamping its own costumes into the pen layer.

The kernel runs one `forever` loop. Each frame it calls `tick()`, a
run-without-screen-refresh custom block:

```
input_poll()      drain the keyboard queue, route keys (tty / window / dialog)
wm_tick()         mouse, menus, taskbar, window dragging, the IDE (desktop only)
sched_run(ms)     run processes for a time budget
wm_update()       recompose and redraw changed screen cells     (desktop only)
tty_render()      draw dirty terminal cells
tty_cursor_update()  blinking text cursor
```

## Graphics: the pen text engine (`src/gfx.sbs`, `src/ui.sbs`, `tools/ui_assets.py`)

* The ScratchOS screen is 1280×720 (a custom TurboWarp stage), which is a
  160×45 grid of 8×16 cells. The stand-alone IDE uses 960×544. `build.py`
  writes the size into the TurboWarp settings comment, and it reaches the SBS
  code as the constants `SCR_W`/`SCR_H`/`SCR_COLS`/`SCR_ROWS`.
* `tools/ui_assets.py` renders JetBrains Mono at 4× and box-filters it into
  glyph costumes. They are stored as 2× PNGs (16×32 px for an 8×16 cell) with
  the rotation centre at the top-left. Each build ships only the characters
  it shows: 116 for ScratchOS, 104 for the stand-alone IDE. A
  code-to-slot list (`gmap`) maps every other CP437 code to `?`. The shared
  `ord()` maps costume numbers back to codes through `glyph_code`. Box
  drawing, blocks, shades, the traffic-light dot, card suits and the cat
  logo are drawn procedurally so they meet at cell edges.
* **Arbitrary RGB colours from a few costume sets.** Scratch's *colour*
  effect rotates hue in HSV, which keeps the *chroma* (max − min channel).
  Its *brightness* effect then adds the same value to R, G and B. So one
  base set of chroma C reaches every colour with chroma C exactly:
  base `(V, V−C, V−C)`, colour effect = hue × 200, brightness = the darkest
  channel's offset. The palette's 250 entries are clustered into 8 chroma
  levels plus a white set for greys, giving 9 base sets of glyphs and 81
  rects each. Each palette entry stores its set's costume numbers, hue and
  brightness. The entries are:
  * the 16 active terminal colours;
  * 56 UI colours each for the dark and light themes;
  * the dark and light terminal colours;
  * 90 wallpaper steps, all of one chroma, so the gradient has no banding.
* Solid rectangles use 81 power-of-two rectangle costumes (1…256 px per side),
  so any fill takes at most 4 stamps. Lines use the pen.
* **True colour.** Colour numbers from 256 up are `256 + 0xRRGGBB`. The pen
  takes any RGB, so these are filled with 1 px pen strokes instead of
  costume stamps: one stroke per row, or per column for tall shapes.
  Measured in TurboWarp, a 1 px stroke covers exactly one pixel when it
  runs through whole Scratch coordinates: x = column − 640,
  y = 360 − row − 1. At half coordinates it straddles two pixels and
  blends them. A stroke also leaves a faint 2–3% tail on the neighbouring
  pixels, which builds up when a window redraws many times. So a fill side
  that lies on the clip rectangle's edge gets its last pixel row or column
  from stamps, in the nearest palette colour (`rgb_clipped`). Text in a
  true colour also uses the nearest palette entry.
* **Cells** (`ui.sbs`): a cell is a glyph and an attribute
  `fg + 256·bg + 65536·deco`. A deco is a thin pen-drawn detail over the cell:
  * 1 px borders;
  * accent underlines and the caret;
  * scrollbar thumbs, positioned to the pixel;
  * rounded corners, painted in whatever colour is behind them;
  * the wallpaper's second stripe, two per cell row.

  The Start button's cat is a glyph stamped at 200% size, which is the
  costumes' native resolution.
* **Filtering.** The pen layer has a fixed size (no high-quality pen, which
  would blur already-drawn content when the window is resized). So the 2×
  glyphs must be linearly filtered to average down cleanly. At exactly 100%
  size and 90° Scratch samples raster costumes nearest-neighbour, so the
  drawing sprite points at 90.001°.
* **Warp mode matters at boot.** The keyboard sprite requests a redraw every
  frame, so any loop that runs outside warp mode (a `nowarp` proc) yields
  once per iteration. The IDE once spent ~22 s at start-up filling its
  1,320-cell screen buffer that way; its boot now runs in warp mode after a
  one-frame splash.

The system cursor is used; nothing draws a pointer. Measured in headless
Chromium with software GL, a stamp costs about 11 µs, and the 160×45 screen
has 7,200 cells. So everything redraws incrementally: terminals track dirty
cells, and the window manager diffs whole screens. The desktop runs at about
60 fps there, including while typing in the IDE.

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
| `net` | use the ScratchOS network |

`/etc/caps` grants capabilities by path (prefix `*` allowed). Otherwise the
first use blocks the process and asks the user, in the terminal or as a
desktop dialog. Programs can request capabilities at start with `--@caps`.

## Desktop (`src/wm.sbs`)

A desktop on the cell grid:
- **Menu bar** (row 0): the logo menu, the focused app's menus.
- **Wallpaper**: two gradient stripes per cell row, or a `.simg` picture
  (`gui.wallpaper`). A picture is scaled to cover the screen and thinned
  to about 20,000 pixels, because it stays pinned in the shared heap.
  Picture cells are marked `-5`. The redraw gathers consecutive dirty ones
  along a row into a span (`wall_span`). Each picture row's run of equal
  pixels inside the span is then one pen stroke per screen row, however
  many cells it crosses, so a full repaint costs strokes per run, not per
  cell.
- **Windows**: a title row with the traffic lights and rounded top corners,
  over content that runs edge to edge.
- **Taskbar** (the bottom two rows): Start, pinned apps (`task_pins`), then
  running apps and other windows, the clock, and show desktop. Its cells
  are marked `-3`, with an attribute that is a signature of what the cell
  shows (button, app, hover / front / running state, the minute). When any
  of them changes, the whole bar is repainted in one pass at pixel level
  (`wm_draw_taskbar`), so the icon tiles and accent lines need not fit the
  cell grid. Start is a menu (`TB_STARTMENU`) that opens upwards from the
  taskbar.

`wm_compose()` builds:

* `own[]`, the owner of every cell (desktop, menu bar, menu, dialog, taskbar, a
  window, or `OUT_WIN` for the IDE's Output panel)
* `ui_ch[]`/`ui_at[]`, the glyph and attribute of every non-content cell
  (`-1` marks content drawn by a tty or a canvas, `-3` a taskbar cell)

`wm_diff()` compares these with the previous frame and redraws only changed
cells. Content cells encode their window-relative position in the attribute,
so moving a window marks all its content dirty.

* **Terminal windows** are ttys whose visibility is checked against `own[]`.
* **Canvas windows** (graphics programs) keep a retained display list of
  primitives in a pinned heap table. New primitives draw immediately, clipped
  to the window's visible rectangles, which are the content rectangle minus
  every rectangle above it, the menu bar and the taskbar. Uncovered regions are
  repainted by replaying the list with the same clipping (Liang–Barsky lines,
  rectangle intersection, whole-glyph text). A glyph cannot be stamped in
  part, so it is stamped only when every cell it touches is visible.
  Another window's edge cuts the visible area into bands, so the test is
  against all of the window's visible rectangles: a glyph straddling a
  band boundary must still be drawn. Canvases that call `gui.track` also
  get `move` events. Colours `16…` are system UI
  colours (`gui.color`), resolved for the current appearance when drawn.
* **Images** (`src/image.sbs`) are heap tables (`w`, `h`, and pixels as raw
  RGB, -1 transparent). They are read and written in the `.simg` text format
  (`docs/SIMG.md`). `gfx.image` adds display-list op 10, which pins the
  image table until the window is cleared or closed. Replay draws each
  row's runs of equal pixels as single pen strokes, clipped like any fill.
* **The Whisker IDE** (`src/ide/`) is one window kind. The IDE has a
  variable size and screen origin (`IC`/`IR`, `ide_ox`/`ide_oy`). Hosted, it
  only *composes* its cells into its own buffer. `wm_compose()` copies them
  into the window, so the window manager's diff draws them, with clipping and
  overlap for free. Output-panel cells are owned by `OUT_WIN` so its tty
  draws only where the panel is visible. The window manager routes mouse
  presses (`ide_grab`), the wheel and raw key events (with their `^` / `+`
  modifier prefixes) to the IDE. Programs the IDE runs open ordinary desktop
  windows. The same `ide.sbs` builds the stand-alone `WhiskerIDE.sb3`
  (`IDE_HOSTED = 0`), where the IDE owns the whole stage.

## Yarn and the Browser (`rootfs/lib/yarn.wsk`, `rootfs/bin/browser.wsk`)

Both are Whisker programs; the kernel knows nothing about web pages.

* `yarn.parse` turns a page into a tree of element tables. It reads one
  line at a time: an indentation stack finds each line's parent, and a
  tokenizer splits the line into strings, `key=value`, `#id`, `.style`,
  switches and the `-> action`. `script` / `code` / paragraph blocks take
  the more-indented lines below them as raw text.
* `yarn.layout` walks the tree with a width and produces a flat list of
  drawing operations (text runs, fills, boxes, pictures, form controls) and
  hit rectangles. Text is word-wrapped on the fixed 8 px grid. Bold is
  drawn twice, one pixel apart. Titles use the costumes at 200% (16×32).
* `yarn.draw` replays the operations that intersect the viewport through
  `gfx`. The browser draws its toolbar and status bar last, so they cover
  anything that reaches past the page area.
* Page scripts are compiled with `load()`, so they share the browser's
  globals. The `page` API is made of browser functions working on its
  top-level locals. An action that changes the page only marks it dirty;
  the page is laid out again once the action returns.
* `fetch` picks a handler by address scheme (`about:`, `net://`, files).
  `net://` fetches through `net.get` / `net.list`. Scripts run only on local
  pages and the server's own `net://` pages, and are off for uploaded ones.

## Network (`src/net.sbs`, `src/cloud.sbs`, `server/`)

The full protocol is in [NETWORK.md](NETWORK.md). Inside the kernel:

* `global cloud NAME;` in SBS declares a Stage variable `☁ NAME` with the
  cloud flag. The pruner never removes cloud variables or writes to them.
  There are nine: `heartbeat`, `up1`–`up4` and `down1`–`down4`.
* `net_tick()` runs every frame, in `tick()` and in the IDE loop:
  * reads the heartbeat;
  * looks at each `down` variable for a changed value (compared as
    `"p" .. v`, because `=` compares long digit strings as numbers);
  * steps each request: queue chunks, resend on time-out, obey "wait";
  * writes at most one queued packet every 0.11 s, rotating through `up1`–`up4`.
* Up to 3 requests are kept in parallel lists (`rq_*`), one per blocked
  process. `nat_net` starts a request, blocks the process with `BLK_IO`, and
  returns the result when the process is resumed after the request
  finishes, the same way `io.read` waits for input.
* When `net_state()` changes, the taskbar is marked for redraw. Its
  indicator is three cells in front of the clock.

## Whisker 3D (`src/w3d/`)

The 3D game engine and its two players are further builds of the same kernel
(`build.py --w3d w3d|player720|player480`). The engine adds a renderer, physics,
sound, a game runtime and a scene editor to the Whisker IDE. The players
leave out the compiler, the shell, the window manager and networking. That
is done with build constants that `sbc` folds away (`HAS_COMPILER`, `HAS_WM`,
`HAS_NET`), so the players run scripts that the engine compiled ahead of
time (WBC, in `src/wcore.sbs`). The scripts are ordinary Whisker processes
that block in `w3d.frame()` between frames. See
[whisker3d/internals.md](whisker3d/internals.md).

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
