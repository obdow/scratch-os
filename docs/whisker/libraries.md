# Modules and libraries

A Whisker program can be split into several files, and can use code that
other people wrote. This chapter explains `require`, which loads a module
file once, and `load`, which compiles a string of Whisker code while the
program runs. It shows how to write a module of your own, and it describes
the two libraries that come with the system: **yarn**, the page engine of
the Browser, and **sort**, a collection of sorting algorithms that ships
with the Whisker IDE.

* [require](#requirename)
* [load](#loadsrc)
* [Writing a module](#writing-a-module)
* [The yarn library](#the-yarn-library)
* [The sort library](#the-sort-library)
* [Known issues](#known-issues)

## require(name)

Loads the module `name`, runs it, and returns the value that the module
returns. A module is an ordinary `.wsk` file.

```lua
local yarn = require("yarn")
print(type(yarn), type(yarn.parse))
```

```output
table	function
```

### Where require looks

`require` tries these files, in this order, and uses the first one that
exists:

1. `/lib/` *name* `.wsk`
2. *name* `.wsk`, relative to the current directory
3. *name* exactly as given, relative to the current directory

So a file in `/lib` wins over a file of the same name in the current
directory. There is no search path to configure (no `package.path`, no `?`
patterns). *name* may contain `/`: `require("game/board")` loads
`/lib/game/board.wsk` or `game/board.wsk`, and an absolute name such as
`require("/home/user/proj/util")` works through step 2.

The *current directory* is the directory of the process (`fs.cwd()`),
normally the directory the user was in when the program started. It is
**not** the directory of the program file. To load a module that sits next
to your program wherever it is started from, build the name from `arg[0]`,
which holds the program's absolute path:

```lua
-- write a module next to this program, then load it from there
local here = fs.dir(arg[0])
fs.write(here .. "/helper.wsk", "return 'helper loaded'")
fs.chdir("/tmp")                          -- the current directory changes...
print(require(here .. "/helper"))         -- ...but this name still works
```

```output
helper loaded
```

(The examples in this chapter create their module files first, so that
each one runs on its own. Normally you write the module with `edit`.)

ScratchOS's `/lib` holds `yarn.wsk`. The stand-alone Whisker IDE has
`/lib/sort.wsk` instead. You can put your own modules in `/lib`, but
writing there needs the `files` capability (see [system.md](system.md)).
Modules in your home directory need nothing.

### What require returns

`require` runs the module's code as a function and returns the module's
`return` value: usually a table of functions, but any value works. If the
module returns nothing (or `nil`), `require` returns `true`.

```lua
fs.write("hello.wsk", "print('module running')")
print(require("hello"))
```

```output
module running
true
```

### Loading once

A program loads each module once. The second `require` with the same name
does not run the file again, it returns the same value:

```lua
fs.write("counter.wsk", "print('loading counter')\nreturn {n = 0}")
local a = require("counter")
local b = require("counter")
a.n = a.n + 1
print(a == b, b.n)
```

```output
loading counter
true	1
```

The cache is kept per program: another program, or a second run of the
same program, loads the file again. The cache key is the name string
exactly as written, so `require("counter")`, `require("./counter")` and
`require("Counter")` load the file three times.

The result is stored in a global variable named `__mod_` followed by the
name. Setting it to `nil` makes the next `require` load the file again:

```lua
fs.write("m.wsk", "print('loading m')\nreturn {}")
local first = require("m")
__mod_m = nil
local second = require("m")
print(first == second)
```

```output
loading m
loading m
false
```

### Errors

`require` raises an error when the module cannot be found, or when it does
not compile. Catch it with `pcall` if the module is optional. `pcall`
takes a Whisker function, so wrap the call:

```lua
local ok, err = pcall(function() return require("nosuch") end)
print(ok, err)
fs.write("broken.wsk", "local x = = 1")
ok, err = pcall(function() return require("broken") end)
print(ok, err)
```

```output
false	prog.wsk:1: module 'nosuch' not found
false	prog.wsk:4: error loading module 'broken': line 1: unexpected symbol near '='
```

A directory with the module's name counts as "not found".

An error while the module's code runs (for example a call to `error` at its
top level) is passed on to the code that called `require`, like any error.
Its line number is the line in the module file, but the message names the
main program file (see [Known issues](#known-issues)). A module that failed
is not stored, so the next `require` runs it again.

```lua
fs.write("fails.wsk", "print('starting')\nerror('cannot start')")
local ok, err = pcall(function() return require("fails") end)
print(ok, err)
ok, err = pcall(function() return require("fails") end)
print(ok)
require("fails")
print("not reached")
```

```output
starting
false	prog.wsk:2: cannot start
starting
false
starting
prog.wsk:2: cannot start
```

Modules may require other modules, but two modules can't require each other
(a cycle). `require` notices the cycle and raises
`loop while loading module 'name'`.

```lua
fs.write("a.wsk", "local b = require('b')\nreturn 'A'")
fs.write("b.wsk", "local a = require('a')\nreturn 'B'")
local ok, err = pcall(function() return require("a") end)
print(ok, err)
```

```output
false	prog.wsk:1: loop while loading module 'a'
```

### What a module can see

A module shares the program's global variables, and the program sees the
globals the module creates. The module cannot see the program's `local`
variables, and the program cannot see the module's.

```lua
fs.write("greet.wsk", "function greet(n) return greeting .. ', ' .. n end")
greeting = "Hello"
require("greet")
print(greet("Ann"))
```

```output
Hello, Ann
```

The module's code is compiled like the body of a function. So a function
*inside* the module cannot use a `local` of the module's top level (the
rule that a function cannot use another function's locals, see
[language.md](language.md)). The compiler rejects it:

```lua
fs.write("bad.wsk", "local secret = 42\nfunction get() return secret end")
local ok, err = pcall(function() return require("bad") end)
print(err)
```

```output
prog.wsk:2: error loading module 'bad': line 2: cannot use local 'secret' of an enclosing function (no closures: use a top-level local or global) near 'end'
```

This is why modules keep their state in a global table. See
[Writing a module](#writing-a-module).

## load(src)

Compiles the string `src` as Whisker code and returns it as a function. If
the code does not compile, `load` returns `nil` and an error message. It
does not raise an error.

* `src`: the code. A number is turned into a string. Other arguments are
  ignored (there is no chunk name or environment argument).
* Returns: a function, or `nil` and a message of the form
  `line N: message`.

```lua
local f = load("return 6 * 7")
print(f())
local g, err = load("return 6 *")
print(g, err)
```

```output
42
nil	line 1: unexpected symbol near '<eof>'
```

Calling the function runs the code. Each call runs it again. A `return`
in the code gives the function's results, also several of them:

```lua
local f = load("local a, b = 3, 4\nreturn a + b, a * b")
local sum, product = f()
print(sum, product)
```

```output
7	12
```

The function takes no parameters: arguments passed to it are ignored, and
`...` does not exist in Whisker. Pass values in global variables instead.

### What loaded code can see

Loaded code shares the program's globals, as a module does. It can read
and change them, and define new global functions. It cannot see the
`local` variables of the code that called `load`.

```lua
local secret = "local"
shown = "global"
local f = load("return shown, secret")
local a, b = f()
print(a, b)
load("function double(x) return x * 2 end")()
print(double(21))
```

```output
global	nil
42
```

Like a module, loaded code is compiled as a function body, so functions
defined in it cannot use its own top-level locals.

### Errors in loaded code

Compile errors come back from `load` as a message. An error raised while the
function runs behaves like any error: it stops the program, or `pcall`
catches it. Its message names the main program and the line *inside the
loaded string*:

```lua
local f = load("local x = 1\nerror('bad value')")
local ok, err = pcall(f)
print(ok, err)
```

```output
false	prog.wsk:2: bad value
```

### A small calculator

`load` lets a program evaluate expressions that the user types. Put
`return` in front to get the value:

```lua
local function eval(expr)
  local f, err = load("return " .. expr)
  if f == nil then return "error: " .. err end
  local ok, v = pcall(f)
  if not ok then return "error" end
  return v
end
print(eval("1 + 2 * 3"))
print(eval("math.sqrt(16)"))
print(eval("2 +"))
```

```output
7
4
error: line 1: unexpected symbol near '<eof>'
```

Each `load` takes a little code memory, which is freed when the program
ends. A program that calls `load` thousands of times can run out of code
memory (`load` then returns `nil, "out of code memory"`).

The Browser uses `load` to run the scripts and button actions of Yarn
pages (see [The yarn library](#the-yarn-library)).

## Writing a module

Because a module's functions cannot see its top-level locals, a module
keeps everything in one global table, and returns that table. Choose a
global name that other code will not use, such as the module's name with
an underscore in front.

A module `/home/user/vec.wsk`:

```lua
-- vec.wsk - 2D vectors
_vec = {}

_vec.zero = {x = 0, y = 0}

function _vec.new(x, y) return {x = x, y = y} end

function _vec.add(a, b) return _vec.new(a.x + b.x, a.y + b.y) end

function _vec.len(a) return math.sqrt(a.x * a.x + a.y * a.y) end

function _vec.str(a) return "(" .. a.x .. ", " .. a.y .. ")" end

return _vec
```

A program that uses it:

```lua
local vec = require("vec")
local p = vec.add(vec.new(1, 2), vec.new(2, 2))
print(vec.str(p), vec.len(p))
```

Here both are in one tested example (the program writes the module first):

```lua
fs.write("vec.wsk", [[
_vec = {}
_vec.zero = {x = 0, y = 0}
function _vec.new(x, y) return {x = x, y = y} end
function _vec.add(a, b) return _vec.new(a.x + b.x, a.y + b.y) end
function _vec.len(a) return math.sqrt(a.x * a.x + a.y * a.y) end
function _vec.str(a) return "(" .. a.x .. ", " .. a.y .. ")" end
return _vec
]])
local vec = require("vec")
local p = vec.add(vec.new(1, 2), vec.new(2, 2))
print(vec.str(p), vec.len(p))
print(vec == _vec)
```

```output
(3, 4)	5
true
```

Tips:

* Functions in the module call each other through the table
  (`_vec.new`), never through locals.
* Settings and state also go in the table: `_vec.count = 0`.
* Callers should use the value `require` returns (`local vec = ...`),
  not the global name, so the module can be renamed later.
* A module runs when it is first required. Keep its top level to
  definitions; do not print or ask for input there.
* `yarn.wsk` and `sort.wsk` follow this pattern; read them for larger
  examples.

## The yarn library

`/lib/yarn.wsk` is the engine behind the Browser: it reads pages written
in Yarn, the ScratchOS page language, lays them out, and draws them in a
window. Any program can use it to show formatted text, help screens or
simple forms. The page language is described in [YARN.md](../YARN.md).

```lua
local yarn = require("yarn")
```

The library returns its table, which is also the global `_yarn`. Do not
use that name for anything else.

| Function | Does |
|---|---|
| [`yarn.parse(src [, doc [, into]])`](#yarnparsesrc--doc--into) | page text to a document |
| [`yarn.layout(doc, width)`](#yarnlayoutdoc-width) | a document to a view (what to draw where) |
| [`yarn.draw(win, view, x, y, w, h, scroll, hover, focus)`](#yarndrawwin-view-x-y-w-h-scroll-hover-focus) | draw a view in a window |
| [`yarn.hit(view, x, y)`](#yarnhitview-x-y) | the link, button or field at a point |
| [`yarn.text_of(node)`](#yarntext_ofnode) | the text of an element |
| [`yarn.hidden(doc, node)`](#yarnhiddendoc-node) | whether an element is hidden |
| [`yarn.fixcall(code)`](#yarnfixcallcode) | `say "hi"` to `say("hi")` |
| [`yarn.theme(name [, over])`](#yarnthemename--over) | the colours of a theme |
| [`yarn.colour(value, theme)`](#yarncolourvalue-theme) | a colour attribute to a colour number |

`parse`, `layout` and `hit` work without the desktop. `draw` needs a
window, so it needs the desktop and the `gui` capability.

### yarn.parse(src [, doc [, into]])

Parses Yarn source text and returns a *document*. It never raises an error
for a bad page: problems are collected in `doc.errors`.

* `src`: the page text. `nil` counts as an empty page.
* `doc`, `into`: leave them out to make a new document. To add elements to
  an existing document, pass the document and the node that should receive
  the new top-level elements (the Browser's `page.add` does this). A
  `page` line in the added text is then not used.
* Returns: the document (the same `doc` if one was given).

The document is a table:

| Field | Holds |
|---|---|
| `root` | the root node; the page's elements are its `kids` |
| `title` | the page title (from `page "Title"`), or `""` |
| `theme` | the theme name: `"light"`, `"dark"`, `"paper"`, `"ocean"` or `"forest"` |
| `pattrs` | the attributes of the `page` line |
| `styles` | named styles: style name (lowercase) → table of attributes |
| `scripts` | the `script` blocks: a list of `{line = first line, src = code}` |
| `ids` | the elements that have an id: id → node |
| `errors` | a list of `{line = n, msg = text}` |
| `base` | not set by `parse`. Set it to a directory, and `layout` loads relative image names from there |

```lua
local yarn = require("yarn")
local doc = yarn.parse([[
page "Demo" theme=dark
  title "Welcome"
  text "Hello, **world**!"
  blink "?"
  button "Go"
]])
print(doc.title, doc.theme)
for _, e in ipairs(doc.errors) do print(e.line, e.msg) end
```

```output
Demo	dark
4	unknown element 'blink'
5	button "Go" has no action (add -> code)
```

Each element is a *node*, a table with these fields:

| Field | Holds |
|---|---|
| `kind` | the element name in lowercase: `"text"`, `"box"`, `"button"`, ... A line that starts with a quoted string is `"text"`. An unknown element becomes `"box"` with `bad = true` |
| `args` | the quoted strings and plain words after the name |
| `attrs` | `name=value` attributes (names in lowercase); flags such as `bold` are stored as `"true"`; `#name` is stored as `attrs.id` |
| `styles` | the `.name` style names |
| `kids` | the child nodes (indented lines below) |
| `line` | the line number in the source |
| `action` | the code after `->`, for buttons |
| `uid` | a number unique to this node |

Some kinds have extra fields: `label` (link, button, check), `target`
(link), `value` and `hint` (input), `checked` (check), `src` (image), and
`raw` (code: a list of lines). The `page` line is itself a node: the first
kid of `root`, with the page's elements below it.

```lua
local yarn = require("yarn")
local doc = yarn.parse([[
style note color=dim
page "Notes"
  text "First" .note #intro bold
  input name "Your name"
  code
    print("hi")
]])
local page = doc.root.kids[1]
print(page.kind, #page.kids)
local t = doc.ids.intro
print(t.kind, t.args[1], t.styles[1], t.attrs.bold)
print(doc.ids.name.kind, doc.ids.name.hint)
print(page.kids[3].raw[1])
print(doc.styles.note.color)
```

```output
page	3
text	First	note	true
input	Your name
print("hi")
dim
```

The `style` line makes no node: it goes into `doc.styles`. The lines
indented under `code` are its text, not child elements.

### yarn.layout(doc, width)

Lays the document out for a page `width` pixels wide and returns a *view*.
Layout works in page coordinates: (0, 0) is the top left of the page, and
`y` grows down the whole page, not just the visible part. The page has a
margin of 28 pixels at each side (12 if `width` is less than 480) and 20 at
the top. Images are loaded here (with `image.load`, relative to
`doc.base`).

The view is a table:

| Field | Holds |
|---|---|
| `ops` | the drawing operations, in order. Each has `op` (`"text"`, `"fill"`, `"box"`, `"button"`, `"input"`, `"check"` or `"image"`), a position `x`, `y`, and its own fields (`s` for text, `w`, `h`, colours) |
| `hits` | the areas that react to the mouse: `{x, y, w, h, kind, ...}` with `kind` `"link"` (and `target`), `"button"`, `"input"` or `"check"` (and `n`, the node) |
| `height` | the height of the whole page in pixels |
| `th` | the theme colours used (see [yarn.theme](#yarnthemename--over)) |
| `doc`, `width` | the arguments |

Lay the page out again after the window width changes, and after the
document changes.

```lua
local yarn = require("yarn")
local doc = yarn.parse('text "Read [the guide](help.yarn)."\nbutton "OK" -> done()')
local view = yarn.layout(doc, 400)
print(#view.ops, #view.hits, view.height)
for _, o in ipairs(view.ops) do print(o.op, o.x, o.y, o.s) end
for _, h in ipairs(view.hits) do print(h.kind, h.x, h.y, h.w, h.h) end
```

```output
4	2	94
text	12	20	Read
text	52	20	the guide
text	124	20	.
button	12	48	OK
link	52	20	72	18
button	12	48	44	26
```

### yarn.draw(win, view, x, y, w, h, scroll, hover, focus)

Draws part of a view into the window `win`.

* `x`, `y`, `w`, `h`: the rectangle of the window to draw in. It is first
  filled with the page background.
* `scroll`: the page `y` shown at the top of the rectangle (0 = the top of
  the page).
* `hover`: the `key` of the hit under the mouse pointer, or `nil`. That
  link is underlined, that button or field gets an outline.
* `focus`: the input node that has the keyboard focus, or `nil`. It is drawn
  with a text cursor.
* Returns nothing.

Operations that are partly inside the rectangle are drawn whole, so draw
the page last, or redraw what is around it. Wrap the call in `gfx.batch()`
and `gfx.flush()` to avoid flicker.

This program shows a page in a window. The mouse wheel scrolls it, a link
shows its target in the title bar, and the button closes the window. It
needs the desktop.

```lua
--@caps gui
-- yview.wsk - show a Yarn page in a window
local yarn = require("yarn")
local src = [[
page "Help" theme=paper
  title "Hello"
  text "This page is drawn by **yarn**. See [the guide](about:help)."
  row
    box
      text "Left"
    box
      text "Right"
  button "Close" -> close
]]
local doc = yarn.parse(src)
local win = gui.window(doc.title, 400, 300)
local w, h = gui.size(win)
local view = yarn.layout(doc, w)
local scroll = 0

local function redraw()
  gfx.batch()
  yarn.draw(win, view, 0, 0, w, h, scroll, nil, nil)
  gfx.flush()
end

redraw()
while true do
  local e = gui.waitevent(win)
  if e.type == "close" then break
  elseif e.type == "resize" then
    w, h = gui.size(win)
    view = yarn.layout(doc, w)
    redraw()
  elseif e.type == "wheel" then
    scroll = math.max(0, math.min(view.height - h, scroll + e.y * 30))
    redraw()
  elseif e.type == "mousedown" then
    local hit = yarn.hit(view, e.x, e.y + scroll)
    if hit and hit.kind == "button" and hit.n.action == "close" then break end
    if hit and hit.kind == "link" then gui.title(win, "link: " .. hit.target) end
  end
end
gui.close(win)
```

### yarn.hit(view, x, y)

Returns the entry of `view.hits` at page point (`x`, `y`), or `nil`. Add
the scroll position to a window `y` first. When areas overlap, the one
added last wins. The entry's fields: `kind` (`"link"`, `"button"`,
`"input"` or `"check"`), `x`, `y`, `w`, `h`, `key` (the value `draw`
takes as `hover`), `target` for links and `n` (the node) for the others.

```lua
local yarn = require("yarn")
local view = yarn.layout(yarn.parse('button "Save" -> save()'), 400)
local hit = yarn.hit(view, 20, 30)
print(hit.kind, hit.n.label, hit.n.action)
print(yarn.hit(view, 300, 300))
```

```output
button	Save	save()
nil
```

### yarn.text_of(node)

Returns the text of an element: the label of a link, button or check box,
the lines of a code block joined with newlines, or else its strings joined
with spaces. Markup such as `**` is kept.

```lua
local yarn = require("yarn")
local doc = yarn.parse('text "Hello" "there"\nlink "Home" -> index.yarn')
print(yarn.text_of(doc.root.kids[1]))
print(yarn.text_of(doc.root.kids[2]), doc.root.kids[2].target)
```

```output
Hello there
Home	index.yarn
```

### yarn.hidden(doc, node)

Returns `true` when the element is hidden: by the `hidden` flag (also
through a style), or by `node.hide`, which overrides the flag when it is
not `nil`. Hidden elements take no space in the layout. The Browser's
`page.show` and `page.hide` set `node.hide` and lay the page out again.

```lua
local yarn = require("yarn")
local doc = yarn.parse('text "a" hidden\ntext "b"')
local a, b = doc.root.kids[1], doc.root.kids[2]
print(yarn.hidden(doc, a), yarn.hidden(doc, b))
a.hide = false
print(yarn.hidden(doc, a))
```

```output
true	false
false
```

### yarn.fixcall(code)

Turns the short call form `name "text"` into `name("text")`, so that page
actions like `say "Hi!"` compile. Other code is returned unchanged. The
Browser runs every action as `load(yarn.fixcall(code))`.

```lua
local yarn = require("yarn")
print(yarn.fixcall('say "Hi!"'))
print(yarn.fixcall('page.set("x", 1)'))
```

```output
say("Hi!")
page.set("x", 1)
```

### yarn.theme(name [, over])

Returns the colours of a theme as a table of colour numbers (as `gfx`
uses), with these keys: `bg`, `text`, `dim`, `head`, `accent`, `card`,
`border`, `codebg`, `code`, `button`, `ontext`, `field`, and `name`.
An unknown `name` gives the light theme. `over` is a table of attributes
(such as `doc.pattrs`) whose keys replace those colours.

```lua
local yarn = require("yarn")
local th = yarn.theme("dark")
local r, g, b, hex = gfx.torgb(th.bg)
print(hex)
th = yarn.theme("light", {bg = "#ff0000"})
r, g, b, hex = gfx.torgb(th.bg)
print(hex)
```

```output
#0d1117
#ff0000
```

The tables `yarn.themes` (theme name → colour strings) and `yarn.names`
(colour names such as `red`, `navy` → `"#rrggbb"`) hold the data.

### yarn.colour(value, theme)

Turns a colour attribute into a colour number: a number stays as it is,
`"#rrggbb"` is converted, a theme key (`"accent"`, `"dim"`, ...) gives that
colour of `theme`, and a colour name gives its `yarn.names` value. Returns
`nil` for `nil`, `""` or an unknown name.

```lua
local yarn = require("yarn")
local th = yarn.theme("light")
print(yarn.colour("accent", th) == th.accent, yarn.colour("nosuch", th))
local r, g, b, hex = gfx.torgb(yarn.colour("navy", th))
print(hex)
```

```output
true	nil
#1f3a6e
```

### Other fields

The library's other functions are its internal steps. They are public
because everything lives in one table, but they may change:
`yarn.eff(doc, node)` (the attributes after styles are applied),
`yarn.size(v, avail)` (`"50%"` or `"200"` to pixels), `yarn.parse_line`,
`yarn.qstring`, `yarn.indent`, `yarn.setup`, `yarn.err`, `yarn.lay`,
`yarn.lay_kids`, `yarn.lay_inner`, `yarn.lay_row`, `yarn.lay_list`,
`yarn.lay_image`, `yarn.gap`, `yarn.alignx`, `yarn.inline`, `yarn.flow`,
`yarn.flush`, `yarn.op`. The tables `yarn.kinds` (element names; `true`
for those that can hold other elements) and `yarn.flags` (the bare words
that are flags) describe the language.

## The sort library

`sort.wsk` is a library of twelve sorting algorithms, for learning and
comparing them. It ships with the **stand-alone Whisker IDE**
(`WhiskerIDE.sb3`), where it is `/lib/sort.wsk`, together with the example
`/examples/sorting.wsk` and the guide `/docs/sort.txt`. It is not part of
ScratchOS: the IDE's files that ScratchOS includes leave it out, so
`require("sort")` fails there with `module 'sort' not found`. (The file
is `ide/rootfs/lib/sort.wsk` in the ScratchOS sources; a copy placed in
`/lib` or in the current directory works in ScratchOS too.)

The examples below were run in the IDE. Their results are shown in
comments.

```lua
local sort = require("sort")
local t = {5, 2, 9, 1, 7}
sort.quick(t)
print(table.concat(t, " "))                  -- 1 2 5 7 9
```

The library returns the global table `_sort`. Do not use that name for
anything else.

### Sorting functions

Every sort function has the form `sort.NAME(t [, less])`. It sorts
`t[1]` to `t[#t]` in place and returns `t`. The optional `less` says what
"in order" means:

* `nil`: ascending, using `<` (numbers, or strings).
* a string: the name of a field. Elements are tables, ordered by
  `a[field] < b[field]`.
* a function: `less(a, b)` returns `true` when `a` must come before `b`.
  `sort.asc` and `sort.desc` are ready-made.

```lua
local sort = require("sort")
print(table.concat(sort.heap({5, 2, 9, 1, 7}, sort.desc), " "))    -- 9 7 5 2 1
local people = {{name = "Ann", age = 31}, {name = "Bob", age = 25},
                {name = "Cy", age = 31}, {name = "Di", age = 19}}
sort.merge(people, "age")
for _, p in ipairs(people) do io.write(p.name, " ") end            -- Di Bob Ann Cy
print()
local words = {"pear", "fig", "banana", "kiwi"}
sort.insertion(words, function(a, b) return #a < #b end)
print(table.concat(words, " "))                                    -- fig pear kiwi banana
```

A *stable* sort keeps equal elements in their old order (Ann stays before
Cy above). The methods:

| Function | Time | Stable | How it works |
|---|---|---|---|
| `sort.bubble(t [, less])` | O(n²) | yes | swaps neighbours until nothing moves |
| `sort.cocktail(t [, less])` | O(n²) | yes | bubble sort in both directions |
| `sort.gnome(t [, less])` | O(n²) | yes | steps back after every swap |
| `sort.insertion(t [, less])` | O(n²) | yes | fast on small or nearly sorted data |
| `sort.selection(t [, less])` | O(n²) | no | fewest swaps (at most n − 1) |
| `sort.shell(t [, less])` | about O(n^1.3) | no | insertion sort over shrinking gaps (701, 301, 132, 57, 23, 10, 4, 1) |
| `sort.comb(t [, less])` | about O(n log n) | no | bubble sort over gaps that shrink by 1.3 |
| `sort.merge(t [, less])` | O(n log n) | yes | bottom-up merging; uses a second table |
| `sort.quick(t [, less])` | O(n log n) on average | no | median-of-three pivot, no deep recursion; ranges under 8 finish with insertion sort |
| `sort.heap(t [, less])` | O(n log n) | no | in place, no extra memory |
| `sort.counting(t [, less])` | O(n + range) | yes | integers only |
| `sort.radix(t [, less])` | O(n × digits) | yes | non-negative integers only (base 10) |

`sort.counting` and `sort.radix` make no comparisons. Their `less` may
only be `nil` (ascending) or `sort.desc` (descending); any other value is
ignored and the result is ascending. They raise an error for other values:

```lua
local sort = require("sort")
print(table.concat(sort.counting({3, -1, 2, -1}), " "))             -- -1 -1 2 3
print(table.concat(sort.radix({170, 45, 802, 2, 66}), " "))         -- 2 45 66 170 802
print(table.concat(sort.radix({3, 1, 2}, sort.desc), " "))          -- 3 2 1
local ok, err = pcall(function() return sort.counting({1, 2.5}) end)
print(err)                         -- ...: sort.counting: needs integers (item 2)
ok, err = pcall(function() return sort.radix({1, -2}) end)
print(err)                         -- ...: sort.radix: needs non-negative integers (item 2)
```

The other sorts call `less` (or `<`) on the elements, so mixing numbers
and strings raises the usual comparison error.

### sort.methods and sort.info

`sort.methods` is the list of the twelve method names, in the order of the
table above. `sort.info` maps each name to a one-line description.

```lua
local sort = require("sort")
print(#sort.methods, sort.methods[1])      -- 12  bubble
print(sort.info.quick)   -- O(n log n) average, unstable - median-of-three partitioning
```

### sort.sorted(t [, method [, less]])

Returns a sorted copy of `t` and leaves `t` unchanged. `method` is a name
from `sort.methods` (default `"merge"`). An unknown name raises
`sort: unknown method '...'`.

```lua
local sort = require("sort")
local t = {3, 1, 2}
local s = sort.sorted(t, "insertion")
print(table.concat(t, " "), table.concat(s, " "))     -- 3 1 2   1 2 3
```

### sort.is_sorted(t [, less])

Returns `true` when no element is less than the one before it.

```lua
local sort = require("sort")
print(sort.is_sorted({1, 2, 2, 3}), sort.is_sorted({3, 1}))   -- true  false
print(sort.is_sorted({3, 1}, sort.desc))                       -- true
```

### sort.search(t, x [, less])

Binary search in a table sorted with the same `less`. Returns the index of
an element equal to `x` (neither less nor greater), or `nil`. With a field
name as `less`, `x` must be a table with that field.

```lua
local sort = require("sort")
print(sort.search({10, 20, 30, 40}, 30))       -- 3
print(sort.search({10, 20, 30, 40}, 25))       -- nil
local recs = sort.quick({{n = 3}, {n = 1}}, "n")
print(sort.search(recs, {n = 3}, "n"))         -- 2
```

### sort.count(method, t [, less])

Sorts a copy of `t` with the named method and returns the number of
comparisons it made. Use it to compare the methods. An unknown name raises
`sort: unknown method '...'`. For `counting` and `radix` the count is 0.

```lua
local sort = require("sort")
local t = {5, 4, 3, 2, 1}
print(sort.count("bubble", t), sort.count("merge", t))   -- 10  5
print(sort.count("insertion", {1, 2, 3, 4, 5}))          -- 4
```

### Helpers

| Function | Does |
|---|---|
| `sort.copy(t)` | a new table with `t[1]` … `t[#t]` |
| `sort.reverse(t)` | reverses `t` in place and returns it |
| `sort.shuffle(t)` | puts `t` in random order in place (Fisher–Yates) and returns it |
| `sort.asc(a, b)` | `a < b` |
| `sort.desc(a, b)` | `a > b` |

```lua
local sort = require("sort")
print(table.concat(sort.reverse(sort.copy({1, 2, 3})), " "))   -- 3 2 1
print(sort.asc(1, 2), sort.desc(1, 2))                         -- true  false
local deck = sort.shuffle({1, 2, 3, 4, 5})                     -- random order
```

The library also has internal fields: `sort.prep`, `sort.key`,
`sort.bykey`, `sort.sift`, `sort.check_ints`, `sort.shell_gaps`,
`sort.compares`, `sort.inner` and `sort.counted`. Sorting by a field name
stores the name in `sort.key`, so a comparison function given to one sort
must not start another sort by a different field.

## Known issues

* Error messages from code in a module or in a `load`ed string name the
  main program file, with the line number inside the module or string
  (`prog.wsk:302: sort: unknown method 'x'` for a line of `sort.wsk`).
* The cache key is the exact name, so one file loaded under two names (for
  example `"m"` and `"./m"`) runs twice and gives two different tables.

See also: [language.md](language.md) (functions, scope and globals),
[stdlib.md](stdlib.md) (`pcall`, `error`), [system.md](system.md) (`fs`,
capabilities), [graphics.md](graphics.md) (windows and `gfx`),
[ide.md](ide.md), [YARN.md](../YARN.md).
