# ScratchOS

An operating system built in Scratch. It has a BIOS and boot sequence, a
Unix-like shell, preemptive multitasking, an in-memory file system, a
capability-based permission system, a mouse-driven window manager, and
its own programming language, **Whisker**. Whisker is compiled to bytecode
and run on a virtual machine, all inside one Scratch project.

Every pixel is drawn with the **pen**. Text is stamped glyph by glyph from
the IBM VGA 8×16 font (code page 437) in the 16-colour VGA palette. Keyboard
input uses **one clone per key** instead of `ask` blocks.

**Run it:** open `ScratchOS.sb3` in [TurboWarp](https://turbowarp.org/)
(File → Load from your computer) and click the green flag.

> TurboWarp is required. Its compiler makes the VM fast enough, and it can
> detect Backspace, Shift, Ctrl, Escape, Home/End and Page Up/Down, which
> vanilla Scratch cannot. The project sets 60 FPS and turns off sprite
> fencing through TurboWarp's project settings.

## What you can do

```
user@scratchos:~$ ls -l /bin                 # the programs, written in Whisker
user@scratchos:~$ cat /bin/hello.wsk         # read their source
user@scratchos:~$ find / -name *.txt | sort -r | head -n 3
user@scratchos:~$ edit hello2.wsk            # full-screen editor (Esc for the menu)
user@scratchos:~$ hello2.wsk                 # run your program
user@scratchos:~$ whisker                    # interactive Whisker REPL
user@scratchos:~$ yes > /dev/null &          # background job; `jobs`, `kill %1`
user@scratchos:~$ top                        # live process monitor
user@scratchos:~$ startx                     # the desktop
```

| Area | Features |
|---|---|
| Boot | BIOS POST with memory test, boot manager, kernel log, `init` (pid 1) running `/etc/rc`, motd. Press Esc to skip the animations. |
| Shell | pipes `\|`, redirection `> >> < 2>`, `;` `&&` `\|\|` `&`, quoting, `$VAR` `$?` `$$` `~`, history (↑/↓), line editing, Ctrl+C, job control (`jobs`, `fg`, `kill %n`), scripts (`sh file.sh`, `source`) |
| Programs | `ls cat cp mv rm mkdir rmdir touch tree find grep wc head tail sort uniq rev tee seq yes basename dirname sleep date cal ps top kill free uname whoami hostname man more edit whisker calc cowsay fortune bench matrix snake hello cube` |
| Desktop | overlapping windows (drag, resize, minimise, maximise, close), taskbar with clock, Start menu, desktop icons, terminal windows, permission dialogs, error dialogs |
| GUI apps | Files (file manager), Paint, Task Manager, Clock, 3D Cube (orbit it with the mouse), About, plus terminal apps like Text Editor and Snake |
| Language | Whisker: Lua-like syntax, tables, functions, methods, `pcall`/`error`, multiple returns, `load`/`require`, 140+ built-in functions |
| Permissions | programs ask before using `files`, `proc`, `gui` or `system` capabilities: (y)es / (n)o / (a)lways; policy in `/etc/caps` |

Type `help`, `man scratchos`, `man whisker`, `man lib` or `man sh` inside the OS.

### Keys

Up/Down history · Left/Right/Home/End/Backspace/Delete editing ·
Ctrl+C interrupt · Esc skips the boot animations and opens the editor menu ·
Ctrl+Space opens the Start menu on the desktop. The browser has no Tab key
for the page, so there is no tab completion, and the editor auto-indents
instead.

## Whisker in 30 seconds

```lua
-- shapes.wsk
local Shape = {}
function Shape.new(kind, size)
  local s = {kind = kind, size = size}
  function s:area()
    if self.kind == "square" then return self.size ^ 2 end
    return math.pi * self.size ^ 2
  end
  return s
end

local list = {Shape.new("square", 3), Shape.new("circle", 2)}
table.sort(list, function(a, b) return a:area() < b:area() end)
for _, s in ipairs(list) do
  print(string.format("%-7s area %6.2f", s.kind, s:area()))
end
```

Graphics on the desktop:

```lua
--@caps gui
local win = gui.window("Hello", 200, 100)
gfx.clear(win, 1)
gfx.disc(win, 100, 50, 30, 14)
gfx.text(win, 60, 80, "Hello!", 15)
repeat local e = gui.waitevent(win) until e.type == "close"
```

See [docs/WHISKER.md](docs/WHISKER.md) for the full language and library reference.

## Whisker IDE

`WhiskerIDE.sb3` is a separate project: a standalone development environment
for Whisker. It reuses the ScratchOS runtime (compiler, VM, heap, natives,
file system, text engine and canvas code) but has its own full-screen UI,
so there is no shell or desktop. Open it in TurboWarp and click the flag.

The IDE has its own look, separate from ScratchOS:

- **A larger custom stage**: 960×544, or 120×34 text cells, set through
  TurboWarp's project settings. Use fullscreen or a large player for the
  best view.
- **Text in JetBrains Mono**: anti-aliased glyph costumes.
- **Flat dark and light themes** modelled on modern desktop IDEs, with a
  title bar holding a Run/Stop button, tabs with accent underlines, a
  project tree, thin 1px borders, and popup menus and dialogs.
- **Pixel-smooth scrollbars** on the editor and the project tree: drag the
  thumb or click the track. The mouse wheel scrolls whichever one the
  pointer is over.
- **The normal system mouse cursor**.

ScratchOS itself keeps the 480×360 stage, VGA font and palette.

- **Editor with tabs**: syntax highlighting (keywords, strings, numbers,
  comments, library names, and multi-line `--[[ ]]` / `[[ ]]`), line numbers,
  a scrollbar, mouse and shift+arrow selection, cut/copy/paste, multi-level
  undo/redo, auto-indent and auto-dedent, toggle comment, duplicate or delete
  line, indent/unindent, find, find next, replace, and go to line.
- **Autocomplete** for keywords, library modules and their functions
  (`string.u` offers `string.upper`), and for identifiers in the file.
  It opens as you type, or on Ctrl+Space.
- **File tree** for `/projects`, `/examples` and `/docs`, with menu items to
  create, rename, delete and save files.
- **Run / Stop** (Ctrl+Enter / Esc). Output goes to a resizable output panel,
  which also takes keyboard input for `io.read()`. Compile and runtime errors
  are shown in the output header and the status bar. The line is marked in
  the gutter, and Run > Go to error jumps to it. Run > Check syntax compiles
  without running.
- **Graphics preview**: programs that call `gui.window` / `gfx.*` draw into
  a floating preview window with full mouse and keyboard events. Try
  `examples/bounce.wsk`, `clock.wsk` and `cube.wsk`.
- **Examples and docs**: 13 example programs, a quick-start guide and the
  full language reference.
- Dark and light themes (View menu), which also restyle the output panel
  and the 16 program colours, and adjustable output panel sizes.
- **Export / import**: the IDE file system lives in memory. File > Export
  copies the current file into the stage list `ide_export`; right-click the
  list to save it as a `.txt` file. File > Import reads one back the same way.

Shortcuts: Ctrl+Enter run, Esc stop (or open the menu), Ctrl+S save, Ctrl+Z/Y
undo/redo, Ctrl+X/C/V, Ctrl+A, Ctrl+F find, Ctrl+G go to line, Ctrl+D
duplicate line, Ctrl+/ comment, Ctrl+] / Ctrl+[ indent, Ctrl+Space complete,
Esc opens the menu bar; arrows or a menu's first letter move through it. The browser may
intercept a few Ctrl shortcuts; the same commands are all in the menus.

## How it is built

Hand-placing tens of thousands of blocks is not practical, so the kernel is
written in **SBS**, a small C-like language. `tools/sbc.py` compiles it into
ordinary Scratch blocks. The output is a normal project you can open and edit
in the Scratch/TurboWarp editor, about 23,000 blocks in total.

```
build.py            build entry point -> ScratchOS.sb3 (--ide -> WhiskerIDE.sb3)
src/*.sbs           the kernel (Kernel sprite) and keyboard (Keyboard sprite)
src/ide/            the Whisker IDE front end (shares the kernel sources)
ide/rootfs/         files baked into the IDE (/projects, /examples, /docs)
rootfs/             files baked into the file system image (/bin, /etc, /home, /usr)
tools/sbc.py        SBS -> Scratch 3 compiler
tools/assets.py     glyph / rectangle costumes from the VGA font
tools/ide_assets.py the IDE's JetBrains Mono costumes and colour palette
tools/natives.py    the Whisker system-call table
assets/font/        IBM VGA 8x16 font (VileR, CC BY-SA 4.0), JetBrains Mono (OFL 1.1)
test/               headless TurboWarp harness (Playwright) and regression test
docs/               architecture, SBS and Whisker documentation
```

Requirements: Python 3 with Pillow. To build:

```
python3 build.py                 # writes ScratchOS.sb3
python3 build.py --ide           # writes WhiskerIDE.sb3
```

To test (Node 18+ and a Chromium for Playwright):

```
cd test && npm install
node regress.js ../ScratchOS.sb3                          # boots the OS, runs commands, checks output
node drive.js ../ScratchOS.sb3 out --text -- "ls" "ps"    # type commands, dump the screen
```

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit:
the stamp text engine, clone keyboard, scheduler, VM, heap/GC, the window
manager's cell compositor, and the Scratch quirks that had to be worked around.

## Credits

* Font: IBM VGA 8×16 from VileR's
  [VGA text mode fonts](https://github.com/viler-int10h/vga-text-mode-fonts)
  collection (the same data as *Px437 IBM VGA 8x16* in
  [The Ultimate Oldschool PC Font Pack](https://int10h.org/oldschool-pc-fonts/),
  CC BY-SA 4.0).
* Whisker IDE font: [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono),
  SIL Open Font License 1.1 (see `assets/font/JetBrainsMono-OFL.txt`).
* Runs on [TurboWarp](https://turbowarp.org/). Testing uses the
  [TurboWarp packager](https://github.com/TurboWarp/packager)'s scaffolding.
