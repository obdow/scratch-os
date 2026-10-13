# Yarn

Yarn is the ScratchOS language for web pages. Pages are `.yarn` text files.
You write them in the Whisker IDE and read them in the **Browser**. The
design goals:

* **Easy to type.** One element per line. Indentation does the nesting, so
  there are no closing tags.
* **Readable as text.** A Yarn file looks like an outline of the page.
* **Programmable.** Pages can run Whisker code, so buttons and forms do
  real work.

```
page "My Site" theme=light
  title "Welcome"
  text "Hello, **world**! Read [about me](about.yarn)."
  row
    box
      text "Left"
    box
      image cat.simg
  button "Click" -> say("Hi!")
```

## Lines

Each line is an **element**, then its arguments, then optionally `->` and an
action:

```
kind  "quoted text" bare-word  key=value  key="value with spaces"  #id  .style  switch  -> action
```

* A line that **starts with a quote** is a `text` element: `"Hello"`.
* A line indented more than the one above it goes **inside** that element.
* `--` starts a comment line. Blank lines are ignored.
* Inside quotes, `\"` is a quote, `\\` a backslash and `\n` a line break.
* Element names and attribute names ignore case. Ids also ignore case,
  because Whisker table keys do.

## Elements

| Element | Arguments | Notes |
|---|---|---|
| `page` | title | the page: `theme=`, `bg=`, `color=`, `accent=`. Optional: elements can also sit at the top level |
| `title` / `heading` / `subheading` | text | large; bold with a rule under it; bold |
| `text` | text | a paragraph (word-wrapped). With no text, the indented lines below form the paragraph; a blank line starts a new one |
| `quote` | text | dim, with a bar on the left |
| `code` | | the indented lines below, shown exactly (or `code "one line"`) |
| `list` | | holds `item`s; `numbered` for 1. 2. 3. |
| `item` | text | an item; may hold more elements (for example a nested list) |
| `box` | | a card: padding, a background (`card`) and a border |
| `row` | | its children side by side; `gap=` sets the space between them |
| `column` | | a group with no look of its own (for example a stack inside a `row`) |
| `center` | | centres its contents |
| `link` | label | `-> target`: a page path, `#id`, `about:...` or a folder |
| `button` | label | `-> code`: Whisker code run on click |
| `input` | id, placeholder | a text field; `value=`, `width=`; `-> code` runs on Enter |
| `check` | id, label | a checkbox; `checked`; `-> code` runs when it changes |
| `image` | file | a `.simg` picture; `scale=`, `width=` |
| `divider` | | a horizontal line |
| `space` | lines | empty space (default 1 line) |
| `style` | name | a named set of attributes (below) |
| `script` | | Whisker code: the indented lines below |

## Inline text

Text arguments understand `**bold**`, `` `code` `` and `[label](target)`
links.

## Attributes

| Attribute | Values |
|---|---|
| `color`, `bg`, `border` | a colour (below) |
| `align` | `left`, `center`, `right` (or the switches `center` / `right` / `left`) |
| `width` | pixels (`200`) or a share of the space (`40%`): narrower blocks, row columns, fields, pictures |
| `pad` | padding in pixels (boxes default to 14) |
| `scale` | picture scale (`2`, `0.5`); otherwise small pictures are enlarged by whole steps |
| `style` | a style name (same as `.name`) |
| `id` | (same as `#name`) |
| switches | `bold`, `big` (double-size text), `dim`, `hidden`, `numbered`, `checked` |

`color` and alignment are inherited: a `box color=white` makes all the
text inside it white.

**Colours** can be:

* `#rgb` or `#rrggbb`;
* a name: black, white, gray, silver, red, orange, yellow, gold, green, lime,
  teal, cyan, blue, navy, purple, pink, brown, maroon;
* or one of the theme's colours: `text`, `dim`, `head`, `accent`, `card`,
  `border`, `codebg`, `code`, `button`, `ontext`, `field`, `bg`.

Text is drawn in the nearest of the system's 250 colours. Backgrounds,
boxes and pictures get the exact colour.

## Styles and themes

```
style note color=dim bg=card pad=8
style heading color=accent        -- named after an element: applies to every heading
text "Remember" .note
text "Also" style=note bold
```

Attributes apply in this order, each overriding the one before:

1. the element's own kind's style;
2. its named styles;
3. its own attributes.

Themes are `light` (the default), `dark`, `paper`, `ocean` and `forest`.
The `page` line can override single theme colours:
`page "Mine" theme=dark accent=#ffb703`.

## Scripts

Whisker code in a `script` block runs when the page loads. Button and field
actions run Whisker code when used. A global function called `onload` runs
once the page has been laid out.

```
input name "Your name" -> greet()
button "Greet" -> greet()
text "" #out
script
  count = 0                        -- page state lives in globals
  function greet()
    count = count + 1
    page.set("out", "Hello, " .. page.get("name") .. " (" .. count .. ")")
  end
```

An action can also use the short call form `say "Hi!"`.

| Call | Does |
|---|---|
| `page.get(id)` | the text of an element, a field's value, or whether a checkbox is ticked |
| `page.set(id, value)` | set the text / label / value / ticked state / picture file |
| `page.show(id)`, `page.hide(id)`, `page.toggle(id)`, `page.visible(id)` | |
| `page.attr(id, key, value)` | set an attribute (`nil` removes it) |
| `page.style(id, name)` | replace the element's styles |
| `page.add(id, yarn)` | parse Yarn text and append the elements to a container (`box`, `list`, ...) |
| `page.clear(id)` | remove a container's children |
| `page.go(url)`, `page.back()`, `page.reload()` | navigate, after the script finishes |
| `page.url()`, `page.title([text])` | |
| `say(message)` | a message banner at the top of the page |

Scripts are ordinary Whisker. They share the browser's global variables:
`page`, `say` and the functions of the last pages opened. Locals declared
at a script's top level cannot be used by its functions (the compiler
says so: Whisker has no closures), so keep shared state in globals. A script has the browser's permissions, which is fine while
pages are local files. Pages from a network will need a sandbox.

## The browser

`browser [address]` (also in Start and in Finder) opens:

* `about:home` (the start page) and `about:help` (the guide). These are
  Yarn files in `/usr/share/yarn`.
* Local files: `.yarn` pages, `.simg` pictures and any other file shown as
  text.
* Folders: their `index.yarn` if they have one, otherwise a listing.

Relative paths and links start from the current page's folder; `~` is your
home folder.

* **Toolbar:** back, forward, reload, home, the address bar (click it or
  press Ctrl+L, type, Enter) and **Source**, which opens the page in the IDE.
* **Keys:** the arrows, space and page up / down scroll; left / right
  arrows go back / forward; Ctrl+R reloads.
* **Problems:** the status bar shows the page's problems (unknown
  elements, script errors).

`browser --check page.yarn ...` prints the problems instead, including
links and pictures that point to missing files. **Check syntax** in the
IDE runs it.

### Where pages come from

`fetch` in `/bin/browser.wsk` takes an address, picks a handler from the
`schemes` table by its scheme, and gets back the page's Yarn text, the
folder its links start from, and the file Source opens. `about:` and local
files are the two handlers today. Any other `name://` address shows a page
saying the ScratchOS network is not available yet. A page server or
database is one more handler in `schemes`. Everything after fetching
(parsing, layout, scripts, history) works the same for every source.

## The engine (`/lib/yarn.wsk`)

```lua
local yarn = require("yarn")
local doc = yarn.parse(src)            -- doc.root, doc.ids, doc.styles, doc.scripts, doc.errors
local view = yarn.layout(doc, width)   -- view.ops (drawing), view.hits (links, buttons, fields)
yarn.draw(win, view, x, y, w, h, scroll, hover, focus)
local hit = yarn.hit(view, x, y)       -- {kind = "link" / "button" / "input" / "check", ...}
```

Any program can show Yarn: help screens, dialogs, documents.
