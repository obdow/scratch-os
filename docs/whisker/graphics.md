# Graphics and windows

Whisker programs can open windows on the ScratchOS desktop, draw shapes,
text and pictures in them, and react to the mouse and keyboard. Three
libraries do this: `gui` opens and manages windows and delivers events,
`gfx` draws, and `image` builds pictures in memory and reads and writes
them as `.simg` files. This chapter explains the model (coordinates,
colours, events, the display list) and then lists every function. A
worked tutorial builds a small program with a button.

* [Quick start](#quick-start)
* [The desktop and the gui capability](#the-desktop-and-the-gui-capability)
* [Windows and coordinates](#windows-and-coordinates)
* [Colours](#colours)
* [Events](#events)
* [Event loops and frame pacing](#event-loops-and-frame-pacing)
* [Flicker-free drawing with batches](#flicker-free-drawing-with-batches)
* [Performance](#performance)
* [Tutorial: a counter with a button](#tutorial-a-counter-with-a-button)
* [The gui library](#the-gui-library)
* [The gfx library](#the-gfx-library)
* [The image library](#the-image-library)
* [Known issues](#known-issues)

## Quick start

```lua
--@caps gui
local win = gui.window("Hello", 240, 120)     -- title, width, height in pixels
local W, H = gui.size(win)

gfx.clear(win, gui.color("window"))
gfx.disc(win, W // 2, H // 2, 30, gfx.hex("#ff8800"))
gfx.text(win, 8, 8, "Hello, desktop!", gui.color("text"))

while true do
  local e = gui.waitevent(win)                 -- sleep until something happens
  if e.type == "close" then break end          -- the red button was clicked
  if e.type == "key" and e.key == "q" then break end
end
gui.close(win)
```

Save it as `hello.wsk` and run it from a terminal window on the desktop
(`run hello.wsk`). The `--@caps gui` line asks for permission to open
windows when the program starts (see below).

## The desktop and the gui capability

Windows exist only while the desktop is running. ScratchOS boots to the
desktop; the logo menu's **Text Console** item leaves it, and the shell
command `startx` starts it again.

**Without the desktop** (in the text console, or in a doctest-style run),
the calls that need a window fail with an error:

| Call | Error |
|---|---|
| `gui.window` | `the desktop is not running (start it with 'startx')` |
| `gui.terminal`, `gui.ide`, `gui.launch` | `the desktop is not running` |
| every call that takes a window (`gui.close`, `gui.event`, `gfx.text`, ...) | `bad argument #1 to '...' (not one of your windows)` |

Everything else works without the desktop: `gui.color`, `gui.appearance`,
`gui.wallpaper`, `gui.apps`, `gui.pinned`, `gui.clipboard`, `gfx.rgb`,
`gfx.hex`, `gfx.torgb`, `gfx.batch`, `gfx.flush` and the whole `image`
library. A program can test for the desktop by calling `gui.window` inside
[`pcall`](stdlib.md#pcallf-). The desktop check happens before the permission
check, so this never shows a prompt in the text console:

```lua
local ok, err = pcall(function() return gui.window("Test", 100, 100) end)
print(ok, err)
```

```output
false   prog.wsk:1: the desktop is not running (start it with 'startx')
```

**The `gui` capability.** Four calls need the `gui`
[capability](system.md#permissions-capabilities): `gui.window`,
`gui.terminal`, `gui.ide` and `gui.launch`. The first time a program uses
one, ScratchOS asks the user in a dialog (Don't Allow / Always Allow /
Allow Once; the keys `n` or Escape, `a`, and `y` or Enter also answer it). The program
waits until the user answers. If the user refuses, the call raises
`permission denied (capability 'gui' was refused)`. Put `--@caps gui` on a
comment line to ask when the program starts instead. Programs in `/bin`
have the capability through `/etc/caps`.

Every other `gui` and `gfx` call needs no capability. Drawing needs none
because a program can only draw in its own windows. `gui.appearance`,
`gui.wallpaper`, `gui.pinned` and `gui.clipboard` also need none, although
they change desktop-wide settings (see [Known issues](#known-issues)).

**In the stand-alone Whisker IDE** a program's window is shown as a preview
inside the IDE. See [ide.md](ide.md).

## Windows and coordinates

The ScratchOS screen is 1280 x 720 pixels, a grid of 160 x 45 text cells of
8 x 16 pixels. The desktop places every window on this cell grid. A window
has a title row (16 pixels, with the close, minimise and zoom buttons) and,
below it, the **drawing area**. All `gfx` coordinates and all event
coordinates are in pixels of the drawing area:

* (0, 0) is the top-left pixel of the drawing area, just below the title
  row.
* x grows to the right and y grows **down**.
* `gui.size(win)` returns the drawing area's width and height.

`gui.window(title, w, h)` asks for a drawing area of `w` x `h` pixels.
The desktop rounds the width up to a multiple of 8 and the height up to a
multiple of 16. The drawing area is at least 128 x 32 and at most
1280 x 656 pixels (the whole screen between the menu bar and the
taskbar). So always read the real size back:

```lua
local win = gui.window("Demo", 250, 100)
local W, H = gui.size(win)        -- 256, 112
```

You can't choose where a window appears. New windows cascade from the
upper left. The user can move a window by its title row, resize it by
dragging its bottom-right cell (down to 160 x 48 pixels), and zoom it with
the green button or a double click on the title row. Moving a window sends
no event. Resizing and zooming send `"resize"` events.

**Clipping.** Drawing is clipped to the drawing area and to the parts of it
that other windows, menus and dialogs don't cover. Nothing a program draws
can reach the title row, another window or the taskbar. Coordinates
outside the drawing area are allowed: the shape is simply cut off. Two
cases are special:

* **Text** is drawn a whole character at a time. A character that would
  cross an edge of the drawing area, or a covered part of it, is left out
  completely. `gfx.text(win, W - 20, 0, "EDGE")` shows only `ED`.
* **Thick lines** are clipped so that the pen stays inside: a line of size
  `s` ends about `s / 2` pixels before the edge.

**The display list.** Each window remembers everything drawn in it since
the last `gfx.clear`. When part of a window is uncovered, or the window is
moved or zoomed, the desktop repaints it from this list; the program does
nothing. This is also why `gfx.clear` matters: it empties the list (see
[Performance](#performance)). A minimised window still records what is
drawn and shows it when it is restored.

**Owners.** A window belongs to the process that opened it. Other
processes, even the program's own children, get `not one of your windows`
if they try to use it. When the process ends, for any reason, its windows
close. Choosing **Text Console** stops every program that has a window
(exit code 143).

## Colours

Every colour argument in `gfx` and `image` is a number of one of three
kinds:

| Numbers | Kind | Follows the appearance? |
|---|---|---|
| 0–15 | the 16 terminal colours | yes |
| 16–71 | system UI colours, from `gui.color(name)` | yes |
| 256 and up | true colours, from `gfx.rgb` or `gfx.hex` | no |

The `gfx` functions round the number down. Any other number (negative, or
72–255) is taken modulo 16, so `-1` is colour 15 and `100` is colour 4.

### Terminal colours

These are the same 16 colours as in the terminal (VGA order):

| 0 black | 1 blue | 2 green | 3 cyan | 4 red | 5 magenta | 6 brown | 7 light grey |
|---|---|---|---|---|---|---|---|
| **8 dark grey** | **9 light blue** | **10 light green** | **11 light cyan** | **12 light red** | **13 light magenta** | **14 yellow** | **15 white** |

They depend on the appearance. In the light appearance, 0 "black" becomes
white and 15 "white" becomes black, so that text in colour 15 on colour 0
stays readable. When the user switches appearance, every window is
repainted with the new colours. The colours drawn are close to, but not
exactly, the theme's design colours, because they are made with Scratch
costume effects. `gfx.torgb` reports what is really drawn:

```lua
local function hex(c) local r, g, b, h = gfx.torgb(c) return h end
print("dark", hex(0), hex(1), hex(15))
gui.appearance("light")
print("light", hex(0), hex(1), hex(15))
gui.appearance("dark")
```

```output
dark    #202020 #3b81e1 #efefef
light   #ffffff #4074e6 #000000
```

### System colours

`gui.color(name)` returns the number of a colour of the desktop's own
interface. Like the terminal colours, these follow the appearance, so a
program drawn in them matches the rest of the desktop in both themes:

| Name | Use |
|---|---|
| `"window"` (or `"background"`) | window background |
| `"sidebar"` (or `"panel"`) | side panels, toolbars |
| `"text"` | normal text |
| `"dim"` (or `"secondary"`) | secondary text |
| `"accent"` | the accent colour (selection, primary buttons) |
| `"ontext"` | text on the accent colour |
| `"selection"` | a selected item's background |
| `"hover"` | an item under the pointer |
| `"border"` | lines and borders |
| `"button"` | button background |
| `"folder"` | folder icons |
| `"red"`, `"yellow"`, `"green"` | the title row's button colours |
| `"error"` | error text |
| `"paper"` | near white, the same in both appearances |
| `"ink"` | near black, the same in both appearances |

Names ignore case. An unknown name raises `gui.color: unknown colour '...'`.

```lua
print(gui.color("window"), gui.color("Accent"), gui.color("ink"))
local r, g, b, h = gfx.torgb(gui.color("accent"))
print(h)
```

```output
16      26      65
#3579fe
```

### True colours

`gfx.rgb(r, g, b)` and `gfx.hex("#rrggbb")` return a *true colour*, the
number `256 + 0xRRGGBB`. Shapes and pictures draw true colours exactly.
They never change with the appearance.

**Text in a true colour is approximated.** Characters are stamped from
pre-coloured costumes, so `gfx.text` draws them in the nearest of the
system's built-in colours (about 250: the terminal and UI colours of both
appearances and the wallpaper gradient). The text's background colour
(`bg`) is a filled rectangle and is drawn exactly.

## Events

A window collects events in a queue. `gui.event(win)` takes the oldest one
and returns it (or `nil` if there is none); `gui.waitevent(win)` waits for
one. An event is a table. Its `type` field says what happened, and `x` and
`y` are always present (0 when they don't apply):

| `type` | When | Fields |
|---|---|---|
| `"mousedown"` | a mouse button goes down in the drawing area | `x`, `y` |
| `"drag"` | the pointer moves while the button is held, after a `"mousedown"` in this window | `x`, `y` |
| `"mouseup"` | the button is released, after a `"mousedown"` in this window | `x`, `y` |
| `"move"` | the pointer moves with no button held, only after [`gui.track`](#guitrackwin--on) | `x`, `y` |
| `"wheel"` | the mouse wheel turns over the window | `y` = notches, positive = down; `x` = 0 |
| `"key"` | a key is pressed while the window is in front | `key`, and `mod` for some keys |
| `"resize"` | the drawing area changed size | `x`, `y` = the new width and height |
| `"close"` | the user asked to close the window | |

**Mouse.** `x` and `y` are drawing-area pixels. A click on a window that is
not in front brings it to the front *and* sends the `"mousedown"`. Clicks
on the title row and on the bottom-right cell (the resize handle) send
nothing. After a `"mousedown"`, `"drag"` and `"mouseup"` go to the same
window even when the pointer leaves it, so their coordinates can be
negative or larger than the window. `"drag"` is sent once per display
frame in which the pointer moved.

**Keys.** Key events go only to the front window, and only when no menu or
dialog is open. `e.key` is:

* a character: `"a"`, `"A"` (Shift or Caps Lock), `"7"`, `"!"`, `" "` for
  the space bar;
* the name of a special key: `"enter"`, `"backspace"`, `"delete"`,
  `"escape"`, `"insert"`, `"home"`, `"end"`, `"page up"`, `"page down"`,
  `"up arrow"`, `"down arrow"`, `"left arrow"`, `"right arrow"`;
* Ctrl with a character: `"^"` and the character, such as `"^c"` or
  `"^s"` (always lower case). In a window, Ctrl+C is an ordinary key
  event; it doesn't stop the program.

When Shift or Ctrl is held with a special key, `e.key` is the plain name
and `e.mod` is `"shift"` or `"ctrl"` (Ctrl wins if both are held). For
other keys `mod` is absent. Tab and the function keys produce no events.
Caps Lock only toggles capitals. Ctrl+Space is taken by the desktop (it
opens the logo menu).

**Resize.** The desktop sends `"resize"` each time the size changes while
the user drags the handle (so several arrive during one drag), and when the
window is zoomed or unzoomed. The new size is in `e.x` and `e.y`, the same
values `gui.size` now returns. The old drawing stays in the display list
and is repainted, but anything that depends on the size should be drawn
again.

**Close.** Clicking the red button, choosing **File > Close Window** or
**Quit** in the app menu sends `"close"`. **The window does not close by
itself.** The program decides: it can save its work, ask, or ignore the
event. If it ignores it, the window stays open and the next click sends
another `"close"`. The window closes when the program calls `gui.close` or
exits. (If the process that owned the window is already gone, the red
button closes it at once.) A program that never reads its events can still
be stopped from Activity Monitor, or with Ctrl+C in the terminal it was
started from.

**Focus.** `gui.active(win)` is `true` when the window is the front window
and no menu or dialog is open, that is, when it would receive keys. A
window that is not in front still receives mouse clicks (they bring it to
the front), wheel events (they go to the window under the pointer) and
`"close"`.

The desktop keeps at most about 200 undelivered events across all windows;
when there are more, the oldest are dropped. Closing a window drops its
pending events.

## Event loops and frame pacing

ScratchOS runs one *display frame* 60 times per second (the project's
frame rate in TurboWarp). In each frame it reads the mouse and keyboard,
delivers events, runs the programs for a few milliseconds, and shows the
result. A program has two good ways to structure its main loop.

**Event-driven** (Paint, Finder, Preview, System Settings). Draw, then
sleep in `gui.waitevent` until something happens, and redraw only what
changed. A waiting program uses no CPU time. `gui.waitevent` has no
time-out; if the program must also do something on a timer, use the
polling loop instead.

```lua
draw()
while true do
  local e = gui.waitevent(win)
  if e.type == "close" then break end
  handle(e)          -- update the state and redraw what changed
end
gui.close(win)
```

**Polling** (animations, clocks, games: `cube`, `clock`, Activity
Monitor). Each time round the loop, take *all* waiting events with
`gui.event` until it returns `nil`, update the state, draw a frame, and
`sleep` a little:

```lua
local running = true
while running do
  local e = gui.event(win)
  while e do                         -- empty the queue
    if e.type == "close" then running = false end
    e = gui.event(win)
  end
  step()                             -- move things
  draw()                             -- one frame, inside gfx.batch / gfx.flush
  sleep(0.03)                        -- about 30 frames per second
end
gui.close(win)
```

`sleep(sec)` wakes at the first display frame after the time has passed,
so a frame can't be shorter than 1/60 s. The bundled programs use
`sleep(0.02)` to `sleep(0.03)` for animation and `sleep(0.1)` to
`sleep(0.2)` for displays that change slowly. A loop that never sleeps or
waits still works (programs are preemptively scheduled), but it takes CPU
time from every other program.

## Flicker-free drawing with batches

Drawing goes straight to the screen. Each display frame a program gets a
short time slice (about 4,000 VM instructions); if a frame's drawing takes
longer, the user sees it half drawn: the cleared background, then the
shapes appearing. Wrap a frame in `gfx.batch()` and `gfx.flush()`:

```lua
gfx.batch()
gfx.clear(win, 0)
-- ... draw the whole frame ...
gfx.flush()
```

While a batch is open the program's time slices are 15 times longer
(about 60,000 instructions), so most frames are drawn completely before
the screen is shown. Nothing is buffered: a frame larger than that can
still show in pieces, and while a long batch runs the rest of the desktop
waits. Don't `sleep` or `gui.waitevent` inside a batch. Only one process
can hold the batch at a time (the last one to call `gfx.batch`); a batch
ends at `gfx.flush` or when the program exits.

## Performance

Drawing is done with the Scratch pen: costume stamps for palette colours
and text, pen strokes for true colours. Rough costs, from cheapest:

* **`gfx.clear`** is a few stamps, and also empties the display list.
* **Rectangles in a terminal or system colour** take at most 4 stamps for
  each 256 x 256 block, whatever their size.
* **`gfx.line`** is one pen stroke; **`gfx.circle`** is 12 to 48 strokes.
* **Rectangles in a true colour** take one pen stroke per row (or per
  column, whichever is fewer), about twice the time of a palette fill.
* **`gfx.disc`** is one fill per row: `2r + 1` fills.
* **`gfx.text`** is one stamp per character, plus a fill when `bg` is
  given.
* **`gfx.pixel`** is one fill per call. Avoid drawing pictures pixel by
  pixel; build an [image](#the-image-library) instead.
* **`gfx.image`** draws one stroke per run of equal pixels in each row (per
  screen row when scaled up). A flat picture is cheap; a 64 x 64 picture
  where every pixel differs is about 4,000 strokes, ten times slower.

Tips:

* **Call `gfx.clear` at the start of every full redraw.** Without it the
  display list keeps growing, every repaint (when the window is uncovered
  or moved) replays all of it, and after about 12,800 primitives new
  drawing is still shown but no longer recorded, so it disappears at the
  next repaint.
* **Redraw only when something changed.** `clock.wsk` redraws once a
  second; `cube.wsk` redraws only while the cube moves.
* For large areas, prefer terminal and system colours to true colours.
* Draw static parts of a picture once into an image and show it with
  `gfx.image`.

## Tutorial: a counter with a button

This program shows a number and an "Add one" button. Clicking the button or
pressing Space adds one, `r` resets, `q` or Escape quits. The button lights
up under the pointer, and the layout follows the window when it is
resized. It uses only system colours, so it looks right in both
appearances.

```lua
-- counter.wsk - a window with one button
--@caps gui

local win = gui.window("Counter", 240, 160)
local W, H = gui.size(win)
gui.track(win, true)            -- also send "move" events, for the hover effect

local count = 0
local hover = false
local button = {w = 120, h = 32}    -- x and y are set by layout()

-- place the button in the middle of the window
local function layout()
  button.x = (W - button.w) // 2
  button.y = (H - button.h) // 2 + 16
end

-- is the point (x, y) inside the button?
local function inside(x, y)
  return x >= button.x and x < button.x + button.w
     and y >= button.y and y < button.y + button.h
end

local function draw()
  gfx.batch()
  gfx.clear(win, gui.color("window"))
  local label = "Count: " .. count
  gfx.text(win, (W - #label * 16) // 2, 16, label, gui.color("text"), nil, 2)
  local bg = gui.color("button")
  if hover then bg = gui.color("accent") end
  gfx.fill(win, button.x, button.y, button.w, button.h, bg)
  gfx.rect(win, button.x, button.y, button.w, button.h, gui.color("border"))
  local text = "Add one"
  gfx.text(win, button.x + (button.w - #text * 8) // 2, button.y + 8, text, gui.color("text"))
  gfx.text(win, 4, H - 16, "space: add  r: reset  q: quit", gui.color("dim"))
  gfx.flush()
end

layout()
draw()
local running = true
while running do
  local e = gui.waitevent(win)          -- sleeps until something happens
  if e.type == "close" then
    running = false
  elseif e.type == "mousedown" then
    if inside(e.x, e.y) then count = count + 1 draw() end
  elseif e.type == "move" then
    local h = inside(e.x, e.y)
    if h ~= hover then hover = h draw() end
  elseif e.type == "key" then
    if e.key == " " or e.key == "enter" then count = count + 1 draw()
    elseif e.key == "r" then count = 0 draw()
    elseif e.key == "q" or e.key == "escape" then running = false
    end
  elseif e.type == "resize" then
    W, H = e.x, e.y
    layout()
    draw()
  end
end
gui.close(win)
```

How it works:

1. **Setup.** `gui.window` asks for 240 x 160 pixels; `gui.size` returns
   what we got. `gui.track` turns on `"move"` events.
2. **State.** `count`, `hover` and the `button` table describe what is on
   screen. `draw` paints all of it from this state, so any change is just
   "update the state, call `draw`".
3. **Hit test.** `inside` compares the event's coordinates with the
   button's rectangle. Event coordinates and drawing coordinates are the
   same pixels, so no conversion is needed.
4. **Drawing.** `draw` starts with `gfx.clear` (which also empties the
   display list) and wraps everything in `gfx.batch` / `gfx.flush`. The big
   label uses scale 2, so each character is 16 pixels wide; that is why it
   is centred with `#label * 16`.
5. **Events.** `gui.waitevent` sleeps until the user does something, so
   the program uses no CPU time while idle. The `"move"` handler redraws
   only when the hover state changes, not on every pointer move.
6. **Resize.** The new size arrives in `e.x` and `e.y`; `layout` moves the
   button to the new middle and `draw` paints everything again.
7. **Quitting.** A `"close"` event or `q` ends the loop; `gui.close`
   removes the window. (Exiting would close it too.)

Note that `layout`, `inside` and `draw` use the top-level locals `W`, `H`,
`button`, `count` and `hover`. A Whisker function can use the program's
top-level locals, but not the locals of another function (see
[What a function can see](language.md#what-a-function-can-see)).

## The gui library

| Function | Summary |
|---|---|
| [`gui.window(title [, w, h])`](#guiwindowtitle--w-h) | open a window, return its id |
| [`gui.close(win)`](#guiclosewin) | close a window |
| [`gui.event(win)`](#guieventwin) | the next event, or `nil` |
| [`gui.waitevent(win)`](#guiwaiteventwin) | wait for the next event |
| [`gui.size(win)`](#guisizewin) | drawing area width, height |
| [`gui.title(win, text)`](#guititlewin-text) | change the title |
| [`gui.active(win)`](#guiactivewin) | is the window in front? |
| [`gui.track(win [, on])`](#guitrackwin--on) | turn `"move"` events on or off |
| [`gui.color(name)`](#guicolorname) | a system colour |
| [`gui.terminal([cmd])`](#guiterminalcmd) | open a terminal window |
| [`gui.ide([path])`](#guiidepath) | open the Whisker IDE |
| [`gui.launch(cmdline)`](#guilaunchcmdline) | start a desktop app |
| [`gui.appearance([mode])`](#guiappearancemode) | get or set light / dark |
| [`gui.wallpaper([path])`](#guiwallpaperpath) | get or set the desktop picture |
| [`gui.apps()`](#guiapps) | the desktop's apps |
| [`gui.pinned(app [, on])`](#guipinnedapp--on) | get or set a taskbar pin |
| [`gui.clipboard([text])`](#guiclipboardtext) | get or set the clipboard |

### gui.window(title [, w, h])

Opens a window and returns its id, a small number used by every other
`gui` and `gfx` call.

* `title`: the text in the title row.
* `w`, `h`: the size of the drawing area in pixels; default 240 x 160.
  The width is rounded up to a multiple of 8 and the height to a multiple
  of 16, then limited to 128..1280 and 32..656.

The drawing area starts filled with colour 0. If the title (or the
program's command name) is one of the desktop's app names, the window
joins that app's taskbar button.

Returns `nil, "too many windows"` when the desktop already has 16 windows
(of all kinds). Raises an error without the desktop, and needs the `gui`
capability (see [above](#the-desktop-and-the-gui-capability)).

```lua
--@caps gui
local win = gui.window("Sketch", 320, 200)
if not win then print("no window") exit(1) end
```

### gui.close(win)

Closes one of the program's windows and drops its pending events. Returns
nothing. Windows also close when the program exits.

```lua
gui.close(win)
```

### gui.event(win)

Returns the window's oldest pending [event](#events) as a table, and
removes it from the queue. Returns `nil` at once if there is none.

```lua
local e = gui.event(win)
while e do
  if e.type == "key" then print("key", e.key) end
  e = gui.event(win)
end
```

### gui.waitevent(win)

Like `gui.event`, but if there is no event it waits until one arrives. It
always returns an event table. There is no time-out.

```lua
local e = gui.waitevent(win)
if e.type == "mousedown" then gfx.disc(win, e.x, e.y, 4, 14) end
```

### gui.size(win)

Returns two values: the width and height of the drawing area in pixels.
They change when the user resizes or zooms the window (a `"resize"` event
announces it).

```lua
local W, H = gui.size(win)
gfx.line(win, 0, 0, W - 1, H - 1, 15)
```

### gui.title(win, text)

Sets the window's title. Returns nothing.

```lua
gui.title(win, "Paint - " .. fs.name(path))
```

### gui.active(win)

Returns `true` when the window is the front window and no menu or dialog
is open (so it receives keys), otherwise `false`.

```lua
if gui.active(win) then gfx.rect(win, 0, 0, W, H, gui.color("accent")) end
```

### gui.track(win [, on])

Turns `"move"` events on (`on` is `true` or left out) or off (`false` or
`nil`). With tracking on, the window gets a `"move"` event with `x` and `y`
whenever the pointer moves over its drawing area with no button held,
while it is the front window. Use it for hover effects, as in the
[tutorial](#tutorial-a-counter-with-a-button). Returns nothing.

```lua
gui.track(win, true)
```

### gui.color(name)

Returns the colour number of a system colour (see
[System colours](#system-colours) for the names). The number stays the same
when the appearance changes; what it draws follows the appearance.

```lua
local bg, fg = gui.color("window"), gui.color("text")
print(bg, fg)
```

```output
16      19
```

### gui.terminal([cmd])

Opens a terminal window (100 x 30 characters) and returns its id. With no
argument it runs an interactive shell in `/home/user`; with `cmd` it runs
that shell command line, and the title is the command. The window closes
when the programs in it have exited, so a short command flashes by; Finder
uses `gui.terminal("run " .. path)` to run a program in its own terminal.

The id can't be used with `gfx` or `gui.event` (those need a window the
program drew itself). Returns `nil, "too many windows"` if the desktop is
full. Needs the desktop and the `gui` capability.

```lua
gui.terminal("run /home/user/test.wsk")
```

### gui.ide([path])

Opens the Whisker IDE, or brings it to the front, and opens `path` in it
if it is given and exists (relative to the current directory). Returns
nothing. Needs the desktop and the `gui` capability.

```lua
gui.ide("notes.txt")
```

### gui.launch(cmdline)

Starts a desktop program, as the Start menu does: `cmdline` is a command
and its arguments, such as `"preview /home/user/Pictures/cat.simg"`. The
program runs with no terminal: its input is empty, and what it writes to
stdout or stderr is shown in a message box. Returns nothing; if the command
doesn't exist, a "Cannot start" message box appears. Needs the desktop and
the `gui` capability.

```lua
gui.launch("textedit " .. fs.abs("notes.txt"))
```

### gui.appearance([mode])

Returns the current appearance, `"light"` or `"dark"`. With `mode`
(`"light"` or `"dark"`, any case) it switches first: the desktop, the
terminals and every window are redrawn in the new colours. Any other
string raises `gui.appearance: "light" or "dark"`. It works without the
desktop too, and then switches the text console's colours.

```lua
local before = gui.appearance()
print(before, gui.appearance("light"), gui.appearance())
gui.appearance(before)
```

```output
dark    light   light
```

### gui.wallpaper([path])

Returns the path of the desktop picture, or `""` for the default gradient.
With `path` it sets the picture first: a `.simg` file, or `""` for the
gradient. The picture is scaled to cover the screen; large pictures are
thinned to about 20,000 pixels. On failure it returns `nil` and a message
(`cannot open ...`, or why the file isn't a valid image).

A relative `path` is looked up from the program's current directory, and
the wallpaper is remembered by its absolute path.

```lua
print("[" .. gui.wallpaper() .. "]")
local ok, err = gui.wallpaper("/no/such.simg")
print(ok, err)
```

```output
[]
nil     cannot open /no/such.simg
```

### gui.apps()

Returns a new table with the names of the desktop's apps, in the order of
the Start menu.

```lua
local apps = gui.apps()
print(#apps, apps[1], apps[13])
```

```output
13      Finder  System Settings
```

### gui.pinned(app [, on])

Returns whether the app called `app` (a name from `gui.apps()`) is pinned
to the taskbar. With `on` (`true` or `false`) it pins or unpins it first.
For an unknown name it returns `nil, "no app called ..."`. Finder and
Activity Monitor are pinned when the desktop starts.

```lua
print(gui.pinned("Finder"), gui.pinned("Paint"))
print(gui.pinned("Paint", true))
gui.pinned("Paint", false)
local ok, err = gui.pinned("Nope")
print(ok, err)
```

```output
true    false
true
nil     no app called Nope
```

### gui.clipboard([text])

Returns the clipboard's text. With an argument it sets the clipboard first
(numbers are converted to strings). The clipboard is shared with the
Whisker IDE and TextEdit.

```lua
gui.clipboard("copied text")
print(gui.clipboard())
```

```output
copied text
```

## The gfx library

All drawing functions take a window id first. Coordinates are drawing-area
pixels (see [Windows and coordinates](#windows-and-coordinates)); colours
are as in [Colours](#colours). Drawing functions return nothing, and
raise `bad argument #1 to '...' (not one of your windows)` for a window
that isn't the program's own.

| Function | Draws |
|---|---|
| [`gfx.clear(win [, c])`](#gfxclearwin--c) | the whole drawing area (and empties the display list) |
| [`gfx.pixel(win, x, y [, c])`](#gfxpixelwin-x-y--c) | one pixel |
| [`gfx.line(win, x1, y1, x2, y2 [, c [, size]])`](#gfxlinewin-x1-y1-x2-y2--c--size) | a line |
| [`gfx.rect(win, x, y, w, h [, c])`](#gfxrectwin-x-y-w-h--c) | a rectangle outline |
| [`gfx.fill(win, x, y, w, h [, c])`](#gfxfillwin-x-y-w-h--c) | a filled rectangle |
| [`gfx.circle(win, x, y, r [, c])`](#gfxcirclewin-x-y-r--c) | a circle outline |
| [`gfx.disc(win, x, y, r [, c])`](#gfxdiscwin-x-y-r--c) | a filled circle |
| [`gfx.poly(win, points [, c])`](#gfxpolywin-points--c) | a filled polygon |
| [`gfx.text(win, x, y, s [, fg [, bg [, scale]]])`](#gfxtextwin-x-y-s--fg--bg--scale) | text |
| [`gfx.image(win, img [, x, y [, scale]])`](#gfximagewin-img--x-y--scale) | a picture |
| [`gfx.batch()`](#gfxbatch) / [`gfx.flush()`](#gfxflush) | start / end a frame |
| [`gfx.rgb(r, g, b)`](#gfxrgbr-g-b) | a true colour from components |
| [`gfx.hex(s)`](#gfxhexs) | a true colour from `"#rrggbb"` |
| [`gfx.torgb(c)`](#gfxtorgbc) | the components of any colour |

### gfx.clear(win [, c])

Fills the whole drawing area with colour `c` (default 0) and empties the
window's display list, so it becomes the background for later repaints.
Call it at the start of every full redraw.

```lua
gfx.clear(win, gui.color("window"))
```

### gfx.pixel(win, x, y [, c])

Sets the pixel at (`x`, `y`) (rounded down) to colour `c` (default 15).

```lua
for i = 0, 99 do gfx.pixel(win, i, 50 + 20 * math.sin(i / 10), 10) end
```

### gfx.line(win, x1, y1, x2, y2 [, c [, size]])

Draws a line from (`x1`, `y1`) to (`x2`, `y2`) in colour `c` (default 15),
`size` pixels thick (default 1), with round ends. The coordinates may be
fractions.

```lua
gfx.line(win, 10, 10, 200, 80, 12, 3)
```

### gfx.rect(win, x, y, w, h [, c])

Draws the 1-pixel outline of the rectangle with its top-left corner at
(`x`, `y`), `w` pixels wide and `h` high, inside those bounds. The numbers
are rounded down; nothing is drawn if `w` or `h` is less than 1. The
default colour is 15.

```lua
gfx.rect(win, 20, 20, 100, 40, gui.color("border"))
```

### gfx.fill(win, x, y, w, h [, c])

Fills the rectangle with its top-left corner at (`x`, `y`), `w` x `h`
pixels, in colour `c` (default 15). Arguments as for `gfx.rect`.

```lua
gfx.fill(win, 20, 20, 100, 40, gui.color("accent"))
```

### gfx.circle(win, x, y, r [, c])

Draws a 1-pixel circle outline centred on (`x`, `y`) with radius `r`
(rounded down; nothing for a negative radius), in colour `c` (default 15).
It is drawn as 12 to 48 straight segments.

```lua
gfx.circle(win, 100, 80, 30, 13)
```

### gfx.disc(win, x, y, r [, c])

Draws a filled circle centred on (`x`, `y`) with radius `r`, in colour `c`
(default 15). A radius of 0 draws one pixel.

```lua
gfx.disc(win, 100, 80, 30, 14)
```

### gfx.poly(win, points [, c])

Fills a polygon in colour `c` (default 15). `points` is a flat table of
coordinates `{x1, y1, x2, y2, x3, y3, ...}`, rounded to whole pixels.
Fewer than three points draw nothing. The polygon is filled row by row
from its leftmost to its rightmost edge, so it should be convex (or at
least have a single span in every row); `cube.wsk` draws its faces this
way.

```lua
gfx.poly(win, {100, 20, 160, 120, 40, 120}, 3)       -- a triangle
```

### gfx.text(win, x, y, s [, fg [, bg [, scale]]])

Draws `s` (converted with `tostring`) with the top-left corner of its first
character at (`x`, `y`).

* `fg`: the text colour, default 15. A true colour is drawn as the nearest
  built-in colour (see [True colours](#true-colours)).
* `bg`: a background colour filled behind each character, or `nil`
  (default) for none.
* `scale`: 2 or more draws characters 16 x 32 pixels; otherwise they are
  8 x 16.

Characters are 8 (or 16) pixels apart; there is no wrapping, and tabs and
newlines are not interpreted. Only the characters the system uses have
glyphs: printable ASCII, a few accented letters such as `é`, a few symbols
(`•`, `►`, `▼`, `■`, `☺` shows the ScratchOS cat, some box-drawing lines and
blocks). Any other character, including tab and newline, is drawn as `?`.
A character that would cross the edge of the visible drawing area is left
out (see [Clipping](#windows-and-coordinates)).

```lua
gfx.text(win, 8, 8, "Score: " .. score, 15)
gfx.text(win, 8, 30, "GAME OVER", 14, 4, 2)    -- yellow on red, double size
```

### gfx.image(win, img [, x, y [, scale]])

Draws the [image](#the-image-library) `img` with its top-left corner at
(`x`, `y`) (default 0, 0). Each image pixel becomes a `scale` x `scale`
square (default 1; fractions such as 2.5 work; 0 or less means 1).
Transparent pixels are skipped, so whatever is underneath shows through.
Colours are exact.

The window keeps a *reference* to the image, not a copy: if the program
changes the image afterwards, the next repaint of the window shows the
changed picture. Draw a copy (`image.copy`) if that matters.

```lua
local sun = image.new(16, 16)                 -- transparent
image.disc(sun, 8, 8, 6, gfx.hex("#ffcc00"))
gfx.image(win, sun, 10, 10, 4)                -- 64 x 64 on screen
```

### gfx.batch()

Starts a frame: until `gfx.flush`, the program runs with much longer time
slices, so the frame appears at once instead of being seen half drawn.
See [Flicker-free drawing with batches](#flicker-free-drawing-with-batches).
Takes no window and returns nothing; works without the desktop.

```lua
gfx.batch()
gfx.clear(win, 0)
draw_everything()
gfx.flush()
```

### gfx.flush()

Ends the frame started by `gfx.batch`. It does nothing if this program
doesn't hold the batch. Returns nothing.

### gfx.rgb(r, g, b)

Returns the true colour with red, green and blue components `r`, `g`, `b`
(0–255 each). The numbers are rounded down and limited to 0–255. The
result is `256 + r * 65536 + g * 256 + b`.

```lua
print(gfx.rgb(255, 136, 0), gfx.rgb(300, -5, 1.7) == gfx.hex("#ff0001"))
```

```output
16746752        true
```

### gfx.hex(s)

Returns the true colour written as `"#rrggbb"`, `"rrggbb"`, `"#rgb"` or
`"rgb"` (upper or lower case), or `nil` if `s` is not one of these.

```lua
print(gfx.hex("#ff8800"), gfx.hex("F80"), gfx.hex("#ff880"), gfx.hex("#gg0000"))
```

```output
16746752        16746752        nil     nil
```

### gfx.torgb(c)

Returns four values for any colour number: red, green, blue (0–255) and
the `"#rrggbb"` string. For a terminal or system colour this is what it
draws in the current appearance. Other numbers are first treated as the
`gfx` functions treat them (so `-1` gives colour 15).

```lua
local r, g, b, h = gfx.torgb(gfx.hex("#123456"))
print(r, g, b, h)
local r2, g2, b2, h2 = gfx.torgb(gui.color("red"))
print(h2)
```

```output
18      52      86      #123456
#fd5f57
```

Remember that only an assignment keeps all four results:
`print(gfx.torgb(c))` prints just the red value (see
[Multiple results](language.md#multiple-results)).

## The image library

An image is a picture in memory that a program can draw into, save as a
`.simg` file, and show in a window with [`gfx.image`](#gfximagewin-img--x-y--scale).
Paint, Preview and the wallpaper use it.

**The image table.** An image is an ordinary Whisker table with two fields,
`w` and `h`, and `w * h` pixels in its array part, row by row from the top
left: pixel (x, y) is element `y * w + x + 1`. Each element is a raw RGB
number `0xRRGGBB`, or -1 for a transparent pixel. Any table of this shape
counts as an image, including one a program builds itself.

**Pixel coordinates are 0-based**: x from 0 to `w - 1`, y from 0 to
`h - 1`. Coordinates are rounded down. Drawing outside the image is
ignored; reading outside returns `nil`.

**Colours.** The `image` functions take and return the same colour numbers
as `gfx` (terminal, system and true colours), plus -1 for transparent. A
terminal or system colour is converted to RGB when it is stored, using the
current appearance, so an image never changes with the appearance. Note
the difference between the functions and the raw table: `image.get`
returns a true colour (`256 + 0xRRGGBB`), while the table element holds
`0xRRGGBB`. Pass colours to `image.set` from `gfx.rgb` or `gfx.hex`, not
as raw `0xRRGGBB` numbers.

**Limits.** An image has at most 65,536 pixels (for example 256 x 256).
Images are tables, so they use memory from the program's heap; see
[internals.md](internals.md).

```lua
local img = image.new(3, 2, gfx.hex("#ff0000"))
print(img.w, img.h, #img, img[1] == 0xff0000)
print(image.get(img, 0, 0) == gfx.hex("#ff0000"), image.get(img, 3, 0))
img[2] = 0x00ff00                      -- writing the table directly
local r, g, b, h = gfx.torgb(image.get(img, 1, 0))
print(h)
```

```output
3       2       6       true
true    nil
#00ff00
```

The examples below print images as text with this helper, which shows `#`
for white, `.` for transparent and `o` for any other colour:

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(6, 3)
image.fill(img, 1, 1, 4, 1, WHITE)
image.set(img, 0, 0, 1)
show(img)
```

```output
o.....
.####.
......
```

| Function | Returns |
|---|---|
| [`image.new(w, h [, c])`](#imageneww-h--c) | a new image |
| [`image.load(path)`](#imageloadpath) | an image, or `nil` and a message |
| [`image.save(path, img)`](#imagesavepath-img) | `true`, or `nil` and a message |
| [`image.decode(text)`](#imagedecodetext) | an image from `.simg` text |
| [`image.encode(img)`](#imageencodeimg) | `.simg` text |
| [`image.size(img)`](#imagesizeimg) | width, height |
| [`image.get(img, x, y)`](#imagegetimg-x-y) | a pixel's colour |
| [`image.set(img, x, y, c)`](#imagesetimg-x-y-c) | |
| [`image.fill(img, x, y, w, h, c)`](#imagefillimg-x-y-w-h-c) | |
| [`image.rect(img, x, y, w, h, c)`](#imagerectimg-x-y-w-h-c) | |
| [`image.line(img, x1, y1, x2, y2, c [, width])`](#imagelineimg-x1-y1-x2-y2-c--width) | |
| [`image.circle(img, x, y, r, c)`](#imagecircleimg-x-y-r-c) | |
| [`image.disc(img, x, y, r, c)`](#imagediscimg-x-y-r-c) | |
| [`image.copy(img)`](#imagecopyimg) | a new image |
| [`image.rotate(img)`](#imagerotateimg) | a new image |
| [`image.flip(img [, dir])`](#imageflipimg--dir) | |
| [`image.colors(img)`](#imagecolorsimg) | colour count, transparent? |

Functions that take an image raise `bad argument #1 to '...' (not an
image)` when the argument is not a table with numeric `w` and `h` and at
least `w * h` array elements.

### image.new(w, h [, c])

Returns a new `w` x `h` image (sizes rounded down) filled with colour `c`,
or transparent if `c` is left out. Raises
`image.new: size must be 1..65536 pixels` if `w` or `h` is less than 1 or
the image would have more than 65,536 pixels.

```lua
local img = image.new(4, 4)
print(img[1], image.get(img, 0, 0))
local ok, err = pcall(function() return image.new(257, 256) end)
print(ok, err)
```

```output
-1      -1
false   prog.wsk:3: image.new: size must be 1..65536 pixels
```

### image.load(path)

Reads a `.simg` file (path relative to the current directory) and returns
a new image. On failure returns `nil` and a message: a file system error
such as `no such file or directory` or `is a directory`, or one of the
[decode](#imagedecodetext) errors.

```lua
local img, err = image.load("/home/user/Pictures/cat.simg")
if img then print(image.size(img)) else print(err) end
local x, e = image.load("/nope.simg")
print(x, e)
local y, e2 = image.load("/etc/caps")
print(y, e2)
```

```output
48
nil     no such file or directory
nil     not a .simg image
```

### image.save(path, img)

Writes `img` to `path` in the `.simg` format, replacing any existing file.
Returns `true`, or `nil` and a message (for example
`no such file or directory` when the folder doesn't exist, or
`is a directory`). Saving outside `/home` and `/tmp` needs the `files`
capability.

```lua
local img = image.new(2, 1, gfx.hex("#336699"))
print(image.save("tiny.simg", img))
print(fs.read("tiny.simg"))
local ok, err = image.save("no/such/dir.simg", img)
print(ok, err)
```

```output
true
SIMG 1
size 2 1
palette 1
#336699
pixels
2*0
end

nil     no such file or directory
```

### image.decode(text)

Like `image.load`, but takes the `.simg` text itself. Returns a new image,
or `nil` and one of these messages:

| Message | Cause |
|---|---|
| `not a .simg image` | the first line doesn't start with `SIMG` |
| `missing size` | no `size W H` line |
| `image too large (WxH)` | more than 65,536 pixels |
| `palette has N colours, expected M` | wrong number of palette entries |
| `bad colour X` | a palette entry that isn't `#rgb`, `#rrggbb` or `-` |

Missing rows and short rows are filled with transparent pixels; extra
pixels in a row are dropped.

```lua
local text = "SIMG 1\nsize 3 2\npalette 2\n#fff -\npixels\n0 1 0\n3*0\n"
local img = image.decode(text)
local w, h = image.size(img)
print(w, h, image.get(img, 1, 0), image.get(img, 1, 1) == gfx.hex("#fff"))
local x, err = image.decode("SIMG 1\nsize 2 1\npalette 2\n#fff\npixels\n0 0\n")
print(x, err)
```

```output
3       2       -1      true
nil     palette has 1 colours, expected 2
```

### image.encode(img)

Returns the image as `.simg` text, the same text `image.save` writes. The
palette lists the colours in the order they are first used (8 per line);
each row is run-length encoded.

```lua
local img = image.new(3, 2, gfx.hex("#ff0000"))
image.set(img, 1, 1, -1)
print(image.encode(img))
```

```output
SIMG 1
size 3 2
palette 2
#ff0000 -
pixels
3*0
0 1 0
end
```

**The .simg format, briefly.** It is plain text: a `SIMG 1` line, optional
`#` comments, `size W H`, `palette N` followed by `N` colours (`#rrggbb`,
`#rgb` or `-` for transparent), `pixels`, then one line per row of palette
indices, where `count*index` repeats an index. See [SIMG.md](../SIMG.md)
for the full description.

### image.size(img)

Returns two values: the width and the height.

```lua
local w, h = image.size(image.new(20, 10))
print(w, h)
```

```output
20      10
```

### image.get(img, x, y)

Returns the colour of pixel (`x`, `y`) as a true colour, -1 if it is
transparent, or `nil` if the position is outside the image.

```lua
local img = image.new(2, 2, gfx.rgb(10, 20, 30))
print(image.get(img, 1, 1) == gfx.rgb(10, 20, 30), image.get(img, 2, 0), image.get(img, -1, 0))
```

```output
true    nil     nil
```

### image.set(img, x, y, c)

Sets pixel (`x`, `y`) to colour `c` (-1 for transparent). Positions outside
the image are ignored. Returns nothing.

```lua
local img = image.new(2, 2, gfx.hex("#000"))
image.set(img, 1, 0, -1)
image.set(img, 5, 5, -1)         -- ignored
print(image.get(img, 0, 0) == gfx.hex("#000"), image.get(img, 1, 0))
```

```output
true    -1
```

### image.fill(img, x, y, w, h, c)

Fills the rectangle with its top-left corner at (`x`, `y`), `w` x `h`
pixels, with colour `c`. The part outside the image is ignored. Use -1 to
erase to transparent.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(5, 3)
image.fill(img, -1, 1, 3, 5, WHITE)
show(img)
```

```output
.....
##...
##...
```

### image.rect(img, x, y, w, h, c)

Draws the 1-pixel outline of the rectangle, inside its bounds.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(5, 4)
image.rect(img, 0, 0, 5, 4, WHITE)
show(img)
```

```output
#####
#...#
#...#
#####
```

### image.line(img, x1, y1, x2, y2, c [, width])

Draws a line from (`x1`, `y1`) to (`x2`, `y2`). With `width` greater than 1
(default 1) it is drawn with a round brush of that diameter, as Paint's
pencil does.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local a = image.new(7, 4)
image.line(a, 0, 0, 6, 3, WHITE)
show(a)
print()
local b = image.new(7, 5)
image.line(b, 1, 2, 5, 2, WHITE, 3)
show(b)
```

```output
#......
.##....
...##..
.....##

.......
.#####.
#######
.#####.
.......
```

### image.circle(img, x, y, r, c)

Draws a circle outline centred on (`x`, `y`) with radius `r`.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(9, 9)
image.circle(img, 4, 4, 3, WHITE)
show(img)
```

```output
.........
...###...
..#...#..
.#.....#.
.#.....#.
.#.....#.
..#...#..
...###...
.........
```

### image.disc(img, x, y, r, c)

Draws a filled circle centred on (`x`, `y`) with radius `r`.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(9, 9)
image.disc(img, 4, 4, 3, WHITE)
show(img)
```

```output
.........
....#....
..#####..
.#######.
.#######.
.#######.
..#####..
....#....
.........
```

### image.copy(img)

Returns a new image with the same size and pixels. Changing one doesn't
change the other.

```lua
local a = image.new(2, 1, gfx.hex("#fff"))
local b = image.copy(a)
image.set(b, 0, 0, -1)
print(image.get(a, 0, 0) == gfx.hex("#fff"), image.get(b, 0, 0))
```

```output
true    -1
```

### image.rotate(img)

Returns a new image, turned 90 degrees clockwise (its width and height
are swapped). The original is unchanged.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(3, 2)
image.fill(img, 0, 0, 3, 1, WHITE)
image.set(img, 0, 1, 1)
show(img)
print()
show(image.rotate(img))
```

```output
###
o..

o#
.#
.#
```

### image.flip(img [, dir])

Mirrors the image **in place**: left to right, or top to bottom when `dir`
is `"v"` or `"vertical"`. Any other string, or `nil`, flips left to right.
Returns nothing.

```lua
local WHITE = gfx.hex("#fff")
local function show(img)
  local w, h = image.size(img)
  for y = 0, h - 1 do
    local s = ""
    for x = 0, w - 1 do
      local c = image.get(img, x, y)
      if c == WHITE then s = s .. "#" elseif c == -1 then s = s .. "." else s = s .. "o" end
    end
    print(s)
  end
end
local img = image.new(3, 2)
image.set(img, 0, 0, WHITE)
image.flip(img)
show(img)
print()
image.flip(img, "v")
show(img)
```

```output
..#
...

...
..#
```

### image.colors(img)

Returns two values: the number of different pixel values in the image
(transparent counts as one), and whether any pixel is transparent. Preview
shows these in its status line.

```lua
local img = image.new(4, 4, gfx.hex("#fff"))
image.set(img, 0, 0, gfx.hex("#000"))
local n, transparent = image.colors(img)
print(n, transparent)
image.set(img, 1, 0, -1)
n, transparent = image.colors(img)
print(n, transparent)
```

```output
2       false
3       true
```

## Known issues

* **`gui.appearance`, `gui.wallpaper`, `gui.pinned` and `gui.clipboard`
  need no capability**, although they change desktop-wide settings or read
  the shared clipboard. Any program can call them.
* **A `.simg` palette index that is out of range** is not reported; the
  pixel gets an invalid value instead of an error.
* **`image.set(img, x, y, 0xff0000)` doesn't store red.** Colour arguments
  are colour numbers, so a raw RGB value above 255 is read as a true colour
  minus 256 (here `#feff00`). Use `gfx.hex` or `gfx.rgb`, or write the raw
  value into the table directly.

See also: [system.md](system.md) (capabilities, processes),
[terminal.md](terminal.md) (text-mode programs and keys),
[language.md](language.md), [ide.md](ide.md) (the graphics preview),
[SIMG.md](../SIMG.md), and the programs `/bin/paint.wsk`, `/bin/cube.wsk`,
`/bin/clock.wsk` and `/bin/files.wsk`.
