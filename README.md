# ScratchOS

An operating system built in Scratch, with a macOS-style desktop at 720p.
It has:
- a boot screen;
- a menu bar, a Windows-style taskbar with a Start menu, and windows with
  traffic-light buttons;
- Finder, Terminal and the **Whisker IDE**;
- a Unix-like shell, preemptive multitasking, an in-memory file system and a
  capability-based permission system;
- its own programming language, **Whisker**, compiled to bytecode and run on
  a virtual machine;
- its own web page language, **Yarn**, and a **Browser** to read the pages.

All of it runs inside one Scratch project.

Every pixel is drawn with the **pen**. Text is stamped glyph by glyph in
**JetBrains Mono** (anti-aliased costumes). Colours come from a modern palette
with dark and light appearances. Keyboard input uses **one clone per key**
instead of `ask` blocks.

**Run it:** open `ScratchOS.sb3` in [TurboWarp](https://turbowarp.org/)
(File → Load from your computer) and click the green flag.

> TurboWarp is required. Its compiler makes the VM fast enough, and it can
> detect Backspace, Shift, Ctrl, Escape, Home/End and Page Up/Down, which
> vanilla Scratch cannot. The project sets a 1280×720 stage and 60 FPS, and
> turns off sprite fencing, through TurboWarp's project settings. Fullscreen
> gives the best view.

## The desktop

ScratchOS boots to the desktop: a cat logo, a progress bar, then the menu
bar, the wallpaper and the taskbar. (Hold Esc while it boots for the text
console; `startx` starts the desktop from there.)

- **Menu bar.**
  - The cat menu: About, System Settings, Light/Dark appearance, Activity
    Monitor, Text Console, Restart, Shut Down.
  - The focused app's menus: About, Pin to / Unpin from Taskbar, Hide,
    Quit, plus File, Window and Help.
- **Taskbar.** A full-width bar along the bottom, like Windows 10:
  - **Start** (the cat, bottom left) lists every app: Finder, Terminal,
    Whisker IDE, TextEdit, Paint, Preview, Browser, Clock, 3D Cube, Snake,
    Matrix, Activity Monitor and System Settings. It also has Text Console,
    Restart and Shut Down.
  - **Pinned apps** come first. Finder and Activity Monitor are pinned at
    first. Click **Pin** / **Unpin** next to an app in Start, or use the
    app's menu in the menu bar.
  - **Running apps** follow, and so does any other window. An accent line
    marks a running app, and a wider one the window in front. Click a button
    to bring its window forward; click the front window's button to
    minimise it.
  - The time and date are on the right. The thin strip at the far right
    shows the desktop (click again to bring the windows back). Hover over
    anything for its name.
- **Windows.**
  - Red closes, yellow minimises, green zooms.
  - Double-click the title bar to zoom.
  - Drag the title to move, and the bottom-right corner to resize.
  - The mouse wheel scrolls.
- **Finder.**
  - A sidebar (Home, Projects, Pictures, Sites, Examples, Applications,
    Documents…).
  - Back/forward, and Name/Size/Kind columns.
  - Double-click a `.wsk` or `.txt` file to open it in the Whisker IDE, or
    a `.simg` picture to open it in Preview, or a `.yarn` page to open it
    in the Browser.
- **Paint.** Pen, line, box, fill, circle and disc tools, and the 16 system
  colours plus your recent custom colours. **Colors…** (or `k`) opens a
  colour picker with a hex field, R/G/B sliders and a hue strip; any
  24-bit colour works. Save writes a `.simg` picture to `~/Pictures`, and
  Open loads one to paint over.
- **Preview.** The picture viewer, for ScratchOS's own image format
  `.simg` (see [docs/SIMG.md](docs/SIMG.md)). It has previous / next
  through the folder, zoom (fit, buttons, wheel), drag to pan, rotate,
  flip, save, and Edit in Paint. A checkerboard shows through transparent
  pixels. `~/Pictures` comes with a few samples.
- **Browser.** Reads web pages written in **Yarn** (see
  [docs/YARN.md](docs/YARN.md)). It has back / forward / reload / home, an
  address bar, link hover, scrolling, forms, and Source (open the page in
  the IDE). For now it opens local files and folders. Other sources, such
  as a future ScratchOS network, plug in as handlers for `name://`
  addresses. `~/Sites` holds a sample site, and `about:help` is the Yarn
  guide.
- **Yarn.** One element per line, indented to nest:
  `title "Hi"`, `text "**bold** and [links](about.yarn)"`, `row`, `box`,
  `image cat.simg`, `button "Go" -> say("Hi!")`. It has five themes,
  named styles, and Whisker `script` blocks that change the page through
  `page.get/set/show/hide/add`. The IDE highlights `.yarn` files, Run
  (Ctrl+Enter) shows the page in the Browser, and Check syntax lists the
  page's problems.
- **Whisker IDE.** The full IDE in a resizable window, with its editor,
  output panel, tree of your home folder, examples and docs. Programs it runs
  open their windows on the desktop. Open it from Start, from Finder, or
  with `ide [file]` in a terminal.
- **System Settings.** Dark and light appearance. This recolours the menu
  bar, taskbar, windows, terminals, the IDE and apps that use system colours.

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
user@scratchos:~$ ide projects/primes.wsk    # open a file in the Whisker IDE
user@scratchos:~$ startx                     # the desktop (from the text console)
```

| Area | Features |
|---|---|
| Boot | logo and progress bar while the kernel starts (fs, scheduler, VM, capabilities, window manager), `init` (pid 1) running `/etc/rc`; Esc during boot gives the text console with the kernel log and motd |
| Shell | pipes `\|`, redirection `> >> < 2>`, `;` `&&` `\|\|` `&`, quoting, `$VAR` `$?` `$$` `~`, history (↑/↓), line editing, Ctrl+C, job control (`jobs`, `fg`, `kill %n`), scripts (`sh file.sh`, `source`) |
| Programs | `ls cat cp mv rm mkdir rmdir touch tree find grep wc head tail sort uniq rev tee seq yes basename dirname sleep date cal ps top kill free uname whoami hostname man more edit whisker calc cowsay fortune bench matrix snake hello cube` |
| Desktop | menu bar with app menus, a Windows-style taskbar (Start menu, pinned and running apps, clock, show desktop), gradient wallpaper, windows with traffic lights (close, minimise, zoom), drag / resize / double-click zoom, permission and message dialogs, dark and light appearance |
| GUI apps | Finder, Whisker IDE, Paint (with a hex / RGB colour picker), Preview (`.simg` pictures), Browser (Yarn web pages), Activity Monitor, Clock, 3D Cube (orbit it with the mouse), About, System Settings, plus terminal apps like TextEdit, Snake and Matrix |
| Language | Whisker: Lua-like syntax, tables, functions, methods, `pcall`/`error`, multiple returns, `load`/`require`, 140+ built-in functions |
| Permissions | programs ask before using `files`, `proc`, `gui` or `system` capabilities: (y)es / (n)o / (a)lways; policy in `/etc/caps` |

Type `help`, `man scratchos`, `man whisker`, `man lib` or `man sh` inside the OS.

### Keys

Up/Down history · Left/Right/Home/End/Backspace/Delete editing ·
Ctrl+C interrupt · Esc during boot gives the text console, and opens the
editor's and the IDE's menus · Ctrl+Space opens the cat menu on the desktop
(arrows and Enter move through the menu bar). The browser has no Tab key
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

`WhiskerIDE.sb3` is also a separate project: a standalone development environment
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

Inside ScratchOS the same IDE runs as a desktop app (see above), sharing the
system's font, palette and appearance.

- **Editor with tabs**: syntax highlighting (keywords, strings, numbers,
  comments, library names, and multi-line `--[[ ]]` / `[[ ]]`), line numbers,
  a scrollbar, mouse and shift+arrow selection, cut/copy/paste, multi-level
  undo/redo, auto-indent and auto-dedent, toggle comment, duplicate or delete
  line, indent/unindent, find, find next, replace, and go to line.
- **Native text files**: any file that isn't a `.wsk` program opens in a
  rendered **Preview**.
  - Word wrap with hanging indents.
  - Markdown-style headings, bullet and numbered lists, quotes and rules.
  - `code`, **bold** and *emphasis*.
  - Fenced code blocks shown with Whisker syntax highlighting.

  Ctrl+E, or the Preview / Edit switch in the tab bar, flips to a
  plain-text editor without Whisker colours, autocomplete or block
  indent. Double-clicking a preview line opens the editor at that line.
  Find and go-to-line follow into the preview, and Run explains that
  text files don't run.
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
- **Examples and docs**: 14 example programs, a quick-start guide and the
  full language reference.
- **Sort library** (`/lib/sort.wsk`, IDE only and not part of the core
  language): `local sort = require("sort")` gives 12 sorting methods.
  - bubble, cocktail, gnome, insertion, selection
  - shell, comb
  - merge, quick, heap
  - counting, radix

  Each sorts in place, with an optional comparator or record field. There
  are also helpers: sorted copies, `is_sorted`, binary `search`, and `count`
  of comparisons. See `/docs/sort.txt` and `/examples/sorting.wsk`.
- Dark and light themes (View menu), which also restyle the output panel
  and the 16 program colours, and adjustable output panel sizes.
- **Export / import**: the IDE file system lives in memory. File > Export
  copies the current file into the stage list `ide_export`; right-click the
  list to save it as a `.txt` file. File > Import reads one back the same way.

Shortcuts: Ctrl+Enter run, Esc stop (or open the menu), Ctrl+S save, Ctrl+Z/Y
undo/redo, Ctrl+X/C/V, Ctrl+A, Ctrl+F find, Ctrl+G go to line, Ctrl+D
duplicate line, Ctrl+/ comment, Ctrl+] / Ctrl+[ indent, Ctrl+Space complete,
Ctrl+E text preview / edit,
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
src/ui.sbs          the shared modern look: cell attributes, decorations, themes
src/wm.sbs          the desktop (menu bar, taskbar, Start, windows, dialogs)
src/ide/            the Whisker IDE (an app in ScratchOS, or a project of its own)
ide/rootfs/         the IDE's files (/projects, /examples, /docs, /lib); inside
                    ScratchOS they appear in ~/examples, ~/projects and
                    /usr/share/doc/whisker
rootfs/             files baked into the file system image (/bin, /etc, /home, /usr)
tools/sbc.py        SBS -> Scratch 3 compiler
tools/assets.py     CP437 tables and costume helpers
tools/ui_assets.py  JetBrains Mono glyph costumes and the colour palette
tools/natives.py    the Whisker system-call table
tools/simg.py       the .simg picture format: sample pictures, PNG converter
rootfs/lib/yarn.wsk the Yarn page engine (parse, lay out, draw); /bin/browser.wsk uses it
assets/font/        JetBrains Mono (OFL 1.1)
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

* Font: [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono),
  SIL Open Font License 1.1 (see `assets/font/JetBrainsMono-OFL.txt`).
* Runs on [TurboWarp](https://turbowarp.org/). Testing uses the
  [TurboWarp packager](https://github.com/TurboWarp/packager)'s scaffolding.
