# Terminal programs

This chapter is about programs that work in a text terminal. It covers the
`term` library, the ANSI escape sequences that the terminal understands, the
16 colours, the characters that the screen can show, the key names that a
program receives, line input, and what happens when output goes to a file.
It ends with two complete full-screen programs: a menu and a small game.

* [The terminal](#the-terminal)
* [Printing and escape sequences](#printing-and-escape-sequences)
* [Colours](#colours)
* [Characters](#characters)
* [The term library](#the-term-library)
* [Keys](#keys)
* [Line input and cooked mode](#line-input-and-cooked-mode)
* [Redirected output and programs without a terminal](#redirected-output-and-programs-without-a-terminal)
* [Ctrl+C](#ctrlc)
* [Tutorial: a full-screen menu](#tutorial-a-full-screen-menu)
* [Tutorial: a game loop](#tutorial-a-game-loop)
* [Known issues](#known-issues)

## The terminal

A terminal is a grid of character cells. Each cell holds one character and
one colour attribute (a foreground colour and a background colour). Every
program started from a shell has a *controlling terminal*: the screen of the
shell that started it.

| Where the program runs | Terminal size (columns × rows) |
|---|---|
| The text console (before `startx`) | 160 × 45 |
| A new Terminal window on the desktop | 100 × 29 (the window is 100 × 30 cells, one row is the title bar) |
| A maximized Terminal window | 160 × 41 |
| The Output panel of the Whisker IDE | the panel's size (see [ide.md](ide.md)) |

The size of a Terminal window changes when the user resizes or zooms it.
Always ask for it with [`term.size()`](#termsize) and do not assume a
size.

There is no scrollback. When text reaches the last row, the whole screen
moves up one row and the top row is lost. Text that reaches the right edge
continues on the next row (a soft wrap). When a Terminal window is resized,
the text of programs in [cooked mode](#line-input-and-cooked-mode) is
wrapped again at the new width. A program in raw mode keeps its cells as
they are and gets a `"resize"` key so it can draw again.

The text cursor is a blinking underline at the current output position. It
is shown in the focused terminal only.

## Printing and escape sequences

`print` and `io.write` send text to standard output. When standard output
is the terminal, the text is drawn at the cursor, and the cursor moves on.
These control characters have a special meaning:

| Character | Effect |
|---|---|
| `"\n"` (10) | go to the start of the next row (scroll if this is the last row) |
| `"\r"` (13) | go to the start of the current row |
| `"\t"` (9) | go to the next column that is a multiple of 8 (at most the last column) |
| `"\e"` (27) | start an escape sequence (see below) |
| code 7 (bell) | ignored |
| code 8 (backspace) | move one column left. Whisker cannot make this character (see [Known issues](#known-issues)), so use `"\e[D"` |

Whisker writes the escape character as `"\e"` (or `"\27"`, `"\x1B"`).

```lua
print(string.byte("\e"), #"\e[2J", "\27" == "\e")
```

```output
27	4	true
```

### Escape sequences

An escape sequence is `ESC [`, then parameters, then one letter. The
parameters are digits separated by `;`. The terminal understands these:

| Sequence | Effect |
|---|---|
| `\e[` *n* `m` | set colours or attributes (SGR, see the next table). Several codes can be given: `\e[97;44m` |
| `\e[m` | the same as `\e[0m`: reset the colours |
| `\e[2J` or `\e[J` | clear the whole screen with the current background colour, and move the cursor to the top left |
| `\e[H` | move the cursor to row 1, column 1 |
| `\e[` *row* `;` *col* `H` | move the cursor to *row*, *col* (both 1-based). `\e[` *row* `H` uses column 1. `f` works the same as `H` |
| `\e[K` | erase from the cursor to the end of the row (with the current colours). The cursor does not move |
| `\e[` *n* `A` | move the cursor up *n* rows (default 1) |
| `\e[` *n* `B` | move down *n* rows |
| `\e[` *n* `C` | move right *n* columns |
| `\e[` *n* `D` | move left *n* columns |

Cursor movements stop at the edges of the screen. They never scroll.

The SGR (colour) codes:

| Code | Effect |
|---|---|
| 0 | reset: light grey on black (colour 7 on colour 0) |
| 1 | "bold": makes the *current* foreground colour bright (colour + 8) |
| 7 | reverse: swap the foreground and background colours |
| 30–37 | foreground: black, red, green, yellow, blue, magenta, cyan, white |
| 90–97 | bright foreground: dark grey, light red, light green, yellow, light blue, light magenta, light cyan, white |
| 40–47 | background, same colours as 30–37 |
| 100–107 | bright background, same colours as 90–97 |
| 39 | default foreground (colour 7) |
| 49 | default background (colour 0) |

Any other code, such as 4 (underline) or 22, is ignored. Because code 1
changes the colour that is set *at that moment*, write it after the colour:
`"\e[31;1m"` is bright red, but `"\e[1;31m"` is plain red.

Other escape sequences are consumed and ignored. For example `\e[s`,
`\e[u` and `\e[0J` do nothing. An `ESC` that is not followed by `[` is
dropped together with the next character. A sequence whose parameters hold
anything except digits and `;` ends at that character. So the common
`"\e[?25l"` (hide the cursor) prints `25l`. Use
[`term.cursor(false)`](#termcursoron) instead.

The terminal remembers a half-finished sequence, so a sequence may be split
over two `io.write` calls.

Here is a status line that uses escapes. When the output is captured in a
file, the colour codes stay in the file (the doctest tool removes them
here), and `cat` shows the colours later.

```lua
local function ok(msg) print("\e[92m[ OK ]\e[0m " .. msg) end
local function fail(msg) print("\e[91m[FAIL]\e[0m " .. msg) end
ok("disk checked")
fail("no network")
```

```output
[ OK ] disk checked
[FAIL] no network
```

This program redraws a progress bar on one row. `"\r"` goes back to the
start of the row, and `"\e[K"` erases what is left of an older, longer
text:

```lua
for i = 0, 20 do
  io.write("\rCopying [" .. string.rep("#", i) .. string.rep(".", 20 - i) .. "] " .. i * 5 .. "%\e[K")
  sleep(0.05)
end
print(" done")
```

## Colours

The terminal has 16 colours, numbered 0 to 15. `term.color`, `term.put`
and the `gfx` functions use these numbers. The ANSI codes map onto them as
the table shows.

| No. | Name | ANSI fg / bg | Dark appearance | Light appearance |
|---|---|---|---|---|
| 0 | black | 30 / 40 | `#1E1F22` | `#FFFFFF` |
| 1 | blue | 34 / 44 | `#3B7DD8` | `#4078F2` |
| 2 | green | 32 / 42 | `#5FA35F` | `#50A14F` |
| 3 | cyan | 36 / 46 | `#3CA8B4` | `#0184BC` |
| 4 | red | 31 / 41 | `#D9534F` | `#E45649` |
| 5 | magenta | 35 / 45 | `#A770D0` | `#A626A4` |
| 6 | brown | 33 / 43 | `#C9913A` | `#C18401` |
| 7 | light grey | 37 / 47 | `#BCBEC4` | `#383A42` |
| 8 | dark grey | 90 / 100 | `#6B7280` | `#A0A1A7` |
| 9 | light blue | 94 / 104 | `#6CA6F7` | `#526FFF` |
| 10 | light green | 92 / 102 | `#8BD17C` | `#3E953A` |
| 11 | light cyan | 96 / 106 | `#6ED3DD` | `#0997B3` |
| 12 | light red | 91 / 101 | `#F07178` | `#CA1243` |
| 13 | light magenta | 95 / 105 | `#D29BF0` | `#B751B6` |
| 14 | yellow | 93 / 103 | `#F2CC60` | `#986801` |
| 15 | white | 97 / 107 | `#EDEFF2` | `#000000` |

The text console always uses the dark colours. On the desktop, the
appearance setting (`gui.appearance`, see [graphics.md](graphics.md))
switches every terminal to the other set, and redraws them. In the light
appearance colour 0 is white and 15 is black. So "light grey on black" (7
on 0) is still the normal text, but dark on white. Choose colours by their
role (0 = background, 7 = text, 15 = bright text) and both appearances work.

The colour attribute belongs to the terminal, not to the program. It stays
after a program ends, so set it back with `term.color(7, 0)` or `"\e[0m"`
before you exit.

## Characters

Whisker strings use code page 437 (CP437): each character is one code from
0 to 255. The screen, however, has pictures (glyphs) for only some of them.
In ScratchOS these characters can be shown:

* the printable ASCII characters, codes 32–126
* these extra characters:

| Code | Char | Code | Char | Code | Char |
|---|---|---|---|---|---|
| 1 | ☺ (drawn as the ScratchOS logo) | 30 | ▲ | 195 | ├ |
| 3 | ♥ | 31 | ▼ | 196 | ─ |
| 4 | ♦ | 130 | é | 219 | █ |
| 7 | • (only with `term.put`) | 158 | ₧ (drawn as a close cross) | 220 | ▄ |
| 15 | ☼ (drawn as a large dot) | 175 | » | 223 | ▀ |
| 16 | ► | 179 | │ | 240 | ≡ |
| 17 | ◄ | 192 | └ | 254 | ■ |

Every other character is drawn as `?`. This includes the corners `┌ ┐ ┘`,
the double lines `═ ║ ╔`, and the shades `░ ▒ ▓`. (The Whisker IDE has
fewer still: ASCII plus `• ► ▲ ▼ é ₧ » ─ ■`.)

The keyboard types only ASCII. To put another character in a string, use
an escape with its code: `"\196"` (decimal) or `"\xC4"` (hex) is `─`.
`string.char(196)` gives the same string.

```lua
print("\196\196\196", "\xDB\xDF\xDC", string.char(16, 32, 17))
print(string.byte("─"), string.byte("█"))
```

```output
───	█▀▄	► ◄
196	219
```

A character without a glyph is still an ordinary character: `string.byte`
gives its code, and files and pipes keep it. Only the screen shows it as
`?`.

```lua
print(string.byte("╔"), #"╔═╗")
```

```output
201	3
```

The line characters suit trees and rules:

```lua
local dirs = {"bin", "home", "lib", "tmp"}
print("/")
for i, d in ipairs(dirs) do
  if i < #dirs then print("├── " .. d) else print("└── " .. d) end
end
print(string.rep("─", 12))
```

```output
/
├── bin
├── home
├── lib
└── tmp
────────────
```

The blocks suit bars:

```lua
local sales = {{"mon", 3}, {"tue", 7}, {"wed", 5}}
for _, d in ipairs(sales) do print(d[1] .. " " .. string.rep("█", d[2]) .. " " .. d[2]) end
```

```output
mon ███ 3
tue ███████ 7
wed █████ 5
```

There are no corner characters for the top of a box. Draw boxes with the
block characters `█ ▀ ▄`, as `/bin/snake.wsk` does, or with `+`, `-` and
`|`, which also work in the IDE.

## The term library

The `term` functions act on the program's controlling terminal. They work
even when standard output is redirected (see
[below](#redirected-output-and-programs-without-a-terminal)). Positions are
1-based: column 1, row 1 is the top-left cell.

| Function | Does |
|---|---|
| [`term.clear()`](#termclear) | clear the screen, cursor to the top left |
| [`term.color(fg [, bg])`](#termcolorfg--bg) | set the colours for later output |
| [`term.goto(x, y)`](#termgotox-y) | move the cursor |
| [`term.getpos()`](#termgetpos) | the cursor position |
| [`term.size()`](#termsize) | the terminal size |
| [`term.write(s)`](#termwrites) | write to the terminal |
| [`term.put(x, y, s [, fg [, bg]])`](#termputx-y-s--fg--bg) | write at a position, without moving the cursor |
| [`term.cursor(on)`](#termcursoron) | show or hide the cursor |
| [`term.raw([on])`](#termrawon) | switch between raw and cooked mode |
| [`term.getkey()`](#termgetkey) | the next key, or `nil` |
| [`term.waitkey()`](#termwaitkey) | wait for the next key |

All of them return nothing, except `size`, `getpos`, `getkey` and
`waitkey`. When an argument has the wrong type they raise an error such as
`bad argument #1 to 'term.color' (number expected, got string)`:

```lua
term.color("red")
```

```output
prog.wsk:1: bad argument #1 to 'term.color' (number expected, got string)
```

### term.clear()

Clears the whole screen and moves the cursor to column 1, row 1. The cells
get the current background colour, so `term.color(15, 1)` and then
`term.clear()` gives a blue screen. It is the same as writing `"\e[2J\e[H"`
with `term.write`.

```lua
term.color(15, 1)
term.clear()
print("white on blue")
```

### term.color(fg [, bg])

Sets the colours that later output to this terminal uses: `print`,
`io.write` and `term.write` text (when it goes to the terminal),
`term.clear`, and `term.put` without colours.

* `fg`: the text colour, 0–15. If it is `nil`, colour 7 is used.
* `bg`: the background colour, 0–15. If it is left out, the background does
  not change.

Numbers are taken modulo 16. An escape such as `"\e[31m"` later in the
output changes the colours again. The colour stays set after the program
ends. See [Colours](#colours).

```lua
term.color(14)          -- yellow text, background unchanged
print("warning")
term.color(0, 7)        -- black on light grey
print(" selected ")
term.color(7, 0)        -- back to normal
```

### term.goto(x, y)

Moves the cursor to column `x`, row `y`. Both are required. Values outside
the screen are clamped to the nearest edge. The next output starts there.

```lua
term.clear()
term.goto(10, 5)
io.write("this starts at column 10 of row 5")
term.goto(1, 7)
```

### term.getpos()

Returns two numbers: the cursor's column and row (1-based). Right after a
character was written in the last column, the column is the width plus 1:
the cursor waits there, and the next character goes to the next row.

```lua
local w = term.size()
io.write(string.rep("x", w))
local x, y = term.getpos()
print()
print(x == w + 1)       -- true
```

### term.size()

Returns two numbers: the number of columns and the number of rows. See
[The terminal](#the-terminal) for typical sizes. Use a multiple assignment;
`print(term.size())` shows only the first value.

When the doctests run (from the text console), it prints:

```lua
local w, h = term.size()
print(w, h)
```

```output
160	45
```

### term.write(s)

Writes `s` (converted with `tostring`) to the terminal at the cursor, like
`io.write`, with control characters and escape sequences. The difference:
`term.write` always goes to the terminal, even when standard output is
redirected to a file or a pipe. Use it for things that belong on the
screen only, such as a prompt or a progress display.

```lua
term.write("Working...\r")
```

### term.put(x, y, s [, fg [, bg]])

Writes `s` at column `x`, row `y` without moving the cursor. This is the
main tool of full-screen programs.

* `x`, `y`: the position of the first character. Parts of `s` that fall
  outside the screen are skipped (`x` may be 0 or negative), and a `y` off
  the screen draws nothing.
* `s`: converted with `tostring`. It is drawn as it is, one character per
  cell, on one row: newlines, tabs and escapes are not interpreted, and the
  screen never scrolls. Control characters show as `?` (code 7 shows `•`).
* `fg`, `bg`: colours, 0–15. If they are left out, the terminal's current
  colours are used. To set only `bg`, give `fg` as well; `nil` is an error.

Only the cells that really change are redrawn, so you can redraw a whole
row every frame cheaply.

```lua
term.put(1, 1, " Status: ready ", 0, 7)
term.put(70, 1, "12:00", 14)
```

### term.cursor(on)

Shows the text cursor when `on` is true, hides it when `on` is `false` or
`nil`. Note that `term.cursor()` with no argument hides it. When a program
in raw mode ends, the cursor is shown again. A program that hides the
cursor in cooked mode must show it again before it ends.

```lua
term.cursor(false)
-- ... draw ...
term.cursor(true)
```

### term.raw([on])

Switches the terminal to raw mode when `on` is true or left out, and back
to cooked mode when `on` is `false` or `nil`.

* In **cooked mode** (the normal mode) the terminal edits a line as the
  user types, echoes it, and hands the finished line to
  [`io.read`](#line-input-and-cooked-mode). `term.getkey` gets nothing.
* In **raw mode** the terminal does not echo or edit. Each key goes to the
  program and is read with `term.getkey` or `term.waitkey`. `io.read` from
  the terminal waits until the program goes back to cooked mode.

The mode belongs to the terminal. When the program ends (also with Ctrl+C
or an error), the terminal goes back to cooked mode and the cursor is shown.
Keys that the program did not read are thrown away.

```lua
term.raw(true)
print("press a key")
local k = term.waitkey()
term.raw(false)
print("you pressed " .. k)
```

### term.getkey()

Returns the next key from the program's key queue as a string (see
[Keys](#keys)), or `nil` when there is none. It never waits. Keys reach the
queue only while the terminal is in raw mode and the program is the
terminal's foreground program.

```lua
print(term.getkey())    -- nil: cooked mode, no keys
```

```output
nil
```

### term.waitkey()

Like `term.getkey`, but waits until a key arrives. Other programs run
meanwhile. It waits forever if the terminal is not in raw mode, or if the
program has no terminal.

```lua
term.raw(true)
io.write("Continue? (y/n) ")
local k = term.waitkey()
while k ~= "y" and k ~= "n" do k = term.waitkey() end
term.raw(false)
print(k)
```

## Keys

In raw mode, `term.getkey` and `term.waitkey` return these strings:

| Key | String |
|---|---|
| a letter | `"a"` … `"z"`, or `"A"` … `"Z"` with Shift or Caps Lock (not both) |
| a digit or symbol | the character typed: `"1"`, `"!"`, `"~"`, `"?"`, ... |
| Space | `" "` |
| Enter | `"enter"` |
| Backspace | `"backspace"` |
| Delete | `"delete"` |
| Insert | `"insert"` |
| Escape | `"escape"` |
| arrows | `"up arrow"`, `"down arrow"`, `"left arrow"`, `"right arrow"` |
| Home, End | `"home"`, `"end"` |
| Page Up, Page Down | `"page up"`, `"page down"` |
| Ctrl + a character key | `"^"` and the unshifted character: `"^a"`, `"^s"`, `"^1"`, `"^ "` (Ctrl+Space). Ctrl+Shift+B is also `"^b"` |
| the terminal was resized | `"resize"` (not a key: see [The terminal](#the-terminal)) |

Key names are lowercase words, and a single character is always one
character long, so `#k == 1` tells a typed character from a special key.

Some keys give nothing:

* Tab, the function keys F1–F12, and Shift, Ctrl and Alt on their own.
* Caps Lock only switches the case of letters.
* Ctrl+C never reaches the program: it stops it (see [Ctrl+C](#ctrlc)).
  Ctrl+D does reach a program in raw mode, as `"^d"`.

Shift and Ctrl are dropped from special keys: Shift+Left arrow and
Ctrl+Enter arrive as `"left arrow"` and `"enter"`. (Desktop windows made
with `gui.window` do get them, as the event's `mod`; see
[graphics.md](graphics.md).)

Holding a key down repeats it: the first repeat comes after about 0.4
seconds, then about 28 per second.

When a [capability prompt](system.md) is waiting on the terminal, the keys
answer the prompt.

## Line input and cooked mode

In cooked mode `io.read()` reads one line that the user types. It returns
the line without the newline. While typing, the user can edit the line:

| Key | Effect |
|---|---|
| Left / Right arrow | move in the line |
| Home / End | go to the start / end of the line |
| Backspace / Delete | delete the character before / under the cursor |
| Up / Down arrow | go through the history |
| Enter | finish the line |
| Ctrl+D, on an empty line | end of input: `io.read()` returns `nil` |
| Ctrl+C | stop the program |

Other control keys are ignored. The terminal always echoes what is typed;
there is no way to turn the echo off (so there is no password input).

The history is one list for the whole system: the shell and all programs
share it. Each non-empty line read from a terminal is added to it (at most
100 lines are kept, and a line equal to the one before is not added
again).

Keys typed before the program asks for a line are kept: they appear when
`io.read` is called, or at the next shell prompt.

Ctrl+D on an empty line ends the input: the waiting `io.read()` returns
`nil`, and `io.readall()` or `io.lines()` returns what was typed before.
Each Ctrl+D ends the input once; the program may read more lines
afterwards. (At the shell prompt Ctrl+D does nothing.) When standard input
is a file or a pipe (`prog < file`, `cat file | prog`), the input ends at
the end of the file. There is no test for "standard input is a terminal"
(`io.isatty()` looks at standard output).

This loop reads lines until the end of the input:

```lua
local n = 0
while true do
  local line = io.read()
  if line == nil then break end
  n = n + 1
end
print(n .. " lines")
```

```output
0 lines
```

(The doctest tool gives each example an empty file as standard input, so
it counts 0 lines. Run from a terminal, it counts lines until Ctrl+D.)

```lua
io.write("Your name: ")
local name = io.read()
print("Hello, " .. name .. "!")
```

## Redirected output and programs without a terminal

`print`, `io.write` and `io.error` follow redirection: with
`prog > file`, `print` writes to the file. The `term` functions do not:
they always act on the terminal. Escape sequences in redirected text are
stored in the file as they are.

`io.isatty()` returns `true` when standard output is a terminal. Use it to
leave out colours and screen tricks when the output goes to a file:

```lua
term.write("this goes to the screen only\n")
print("this goes to standard output")
print(io.isatty())
```

```output
this goes to standard output
false
```

(The doctest tool runs each example as `run prog.wsk > o`, so here
`io.isatty()` is `false` and the `term.write` text is not in the file.)

Mixing `term.color` with `print` does not colour redirected output, because
`term.color` changes the terminal and `print` writes to the file. Escapes
in the text are the portable choice. A careful program does both checks:

```lua
local tty = io.isatty()
local function red(s)
  if tty then return "\e[91m" .. s .. "\e[0m" end
  return s
end
print(red("error:") .. " file not found")
```

```output
error: file not found
```

A program started from the desktop (the Start menu, Finder, or
`gui.launch`) has no terminal. Then `term.size()` returns 60, 22,
`term.getpos()` returns 1, 1, `term.getkey()` returns `nil`,
`term.waitkey()` waits forever, and the other `term` functions do nothing.
What it prints, and its errors, appear in a message box.
Such a program should use a window (see [graphics.md](graphics.md)).

## Ctrl+C

Ctrl+C stops the foreground program of the terminal at once, together with
the other processes in its process group (the programs it started with
`proc.spawn`, and the other programs of a pipeline). It
works in raw mode too. The program cannot catch it: no `pcall` sees it, and
code after the current line does not run. The exit code is 130, which the
shell shows with `echo $?`. The terminal goes back to cooked mode and the
cursor is shown, but the colours stay as the program left them.

At a shell prompt, Ctrl+C prints `^C` and starts a new line.

If your program must save something when it is stopped, read keys in raw
mode and offer its own quit key (`q` or Escape) instead.

## Tutorial: a full-screen menu

This program shows a menu in the middle of the screen. The arrow keys move
the highlight and Enter chooses. It shows the usual structure of a
full-screen program:

1. Set up: raw mode, hide the cursor, draw everything.
2. Loop: wait for a key, change the state, redraw only what changed.
3. Handle `"resize"` by reading the size again and redrawing everything.
4. Clean up: cooked mode, cursor on, normal colours, clear the screen.

Save it as `menu.wsk` and run it with `menu.wsk`.

```lua
-- menu.wsk - choose an item with the arrow keys
local items = {"New game", "Load game", "Options", "Quit"}
local sel = 1
local W, H = term.size()

-- draw one menu line; the selected one is white on blue
local function item(i)
  local text = string.format(" %-16s ", items[i])
  local x = (W - #text) // 2
  local y = (H - #items) // 2 + i
  if i == sel then term.put(x, y, text, 15, 1) else term.put(x, y, text, 7, 0) end
end

-- draw everything: after start-up and when the window changes size
local function screen()
  term.color(7, 0)
  term.clear()
  term.put(1, 1, string.format(" %-" .. (W - 1) .. "s", "MENU   up/down: move   Enter: choose   q: quit"), 0, 7)
  for i = 1, #items do item(i) end
end

term.raw(true)
term.cursor(false)
screen()
local choice = nil
while choice == nil do
  local k = term.waitkey()
  local old = sel
  if k == "up arrow" then
    sel = sel - 1
    if sel < 1 then sel = #items end
  elseif k == "down arrow" then
    sel = sel % #items + 1
  elseif k == "enter" then
    choice = items[sel]
  elseif k == "q" or k == "escape" then
    choice = "Quit"
  elseif k == "resize" then
    W, H = term.size()
    screen()
  end
  if sel ~= old then
    item(old)
    item(sel)
  end
end
-- put the terminal back the way we found it
term.raw(false)
term.cursor(true)
term.color(7, 0)
term.clear()
print("You chose: " .. choice)
```

Some points to notice:

* `item` and `screen` use `W`, `H`, `items` and `sel`. A function can use
  the program's top-level locals, so this works. (It cannot use the locals
  of another function: see [language.md](language.md).)
* `term.waitkey()` lets other programs run while the menu waits, so the
  menu uses no CPU time while nobody types.
* Only the two changed lines are drawn after an arrow key. A full
  `term.clear()` redraws the whole screen and is much slower.
* `string.format(" %-16s ", ...)` pads every line to the same width, so the
  highlight bar has the same length on each line.

## Tutorial: a game loop

A game cannot wait for keys, because things must move when nobody types.
It runs a loop of frames. Each frame reads all waiting keys with
`term.getkey()` (which never waits), updates the game, draws, and sleeps a
little. `/bin/snake.wsk` and `/bin/matrix.wsk` work this way.

In this game stars fall from the top, and you catch them with a paddle at
the bottom.

```lua
-- catch.wsk - catch the falling stars.  left/right: move, q: quit
local W, H = term.size()
local px = W // 2                          -- paddle centre
local sx, sy = math.random(2, W - 1), 2    -- the star
local score, lives = 0, 3

local function status()
  local s = string.format(" score %d   lives %d   left/right: move   q: quit", score, lives)
  term.put(1, 1, s .. string.rep(" ", W - #s), 0, 7)
end

term.raw(true)
term.cursor(false)
term.color(7, 0)
term.clear()
status()
local running = true
while running and lives > 0 do
  -- 1. input: handle every key that arrived since the last frame
  local k = term.getkey()
  while k do
    if k == "left arrow" and px > 3 then px = px - 2
    elseif k == "right arrow" and px < W - 2 then px = px + 2
    elseif k == "q" or k == "escape" then running = false
    elseif k == "resize" then
      W, H = term.size()
      term.clear()
      status()
    end
    k = term.getkey()
  end
  -- 2. update: the star falls one row per frame
  term.put(sx, sy, " ")
  sy = sy + 1
  if sy >= H then
    if math.abs(sx - px) <= 2 then score = score + 1 else lives = lives - 1 end
    sx, sy = math.random(2, W - 1), 2
    status()
  end
  -- 3. draw
  term.put(sx, sy, "*", 14)
  term.put(1, H, string.rep(" ", W))
  term.put(px - 2, H, "▀▀▀▀▀", 11)
  sleep(0.05)
end
term.raw(false)
term.cursor(true)
term.clear()
print("Final score: " .. score)
```

Some points to notice:

* The inner `while k do ... end` loop reads *all* waiting keys. If you read
  one key per frame, keys pile up when the user holds a key down, and the
  paddle goes on moving after the key is released.
* The star is erased by drawing a space over it, and the paddle row is
  cleared and drawn again every frame. `term.put` redraws only cells that
  change, so this costs little.
* `sleep(0.05)` sets the speed, and lets other programs run. Without it the
  game would run as fast as the system allows, which depends on the load.
  Measure time with `os.millis()` if the speed must be exact.
* The paddle is drawn with `▀` (code 223), one of the block characters the
  screen can show (see [Characters](#characters)).

## Known issues

* Only the characters listed in [Characters](#characters) can be shown. All
  others, including most CP437 box-drawing characters, appear as `?`.
* `"\e[1;31m"` gives plain red: code 1 brightens the colour that is set
  when it is read, so it must come after the colour (`"\e[31;1m"`).
* `\e[J` with no parameter clears the whole screen (in other terminals it
  clears from the cursor down), and `\e[2J` also moves the cursor to the top
  left. `\e[0J`, `\e[1J`, `\e[1K` and `\e[2K` work like other
  terminals only partly: the J forms do nothing, and the K forms always
  erase from the cursor to the end of the row.
* Sequences with `?` (such as `\e[?25l`) are not understood, and their
  remaining characters are printed.
* `string.char(8)` and `"\8"` give an empty string, so a program cannot
  write a backspace character. Use `"\e[D"` to move left.
* When a program ends, the cursor is shown again only if the terminal was in
  raw mode, and the colours are never reset.

See also: [system.md](system.md) (io, processes, capabilities),
[graphics.md](graphics.md) (windows and `gfx`),
[stdlib.md](stdlib.md) (`string.format`, `string.rep`),
[getting-started.md](getting-started.md).
