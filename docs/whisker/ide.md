# The Whisker IDE

The Whisker IDE is an editor and runner for Whisker programs. It has a file
tree, tabs, syntax highlighting for Whisker and Yarn, autocomplete, find and
replace, undo, an output panel that works as the program's terminal, error
markers, a formatted preview for text files, and a pane that shows a
program's graphics window. It comes in two forms: an app inside ScratchOS,
and a stand-alone Scratch project, `WhiskerIDE.sb3`, that runs Whisker
without the rest of the operating system. Both are built from the same
source (`src/ide/`) and use the same compiler and virtual machine.

* [Two forms](#two-forms)
* [The window](#the-window)
* [Files and tabs](#files-and-tabs)
* [Editing](#editing)
* [Syntax highlighting](#syntax-highlighting)
* [Autocomplete](#autocomplete)
* [Running and stopping programs](#running-and-stopping-programs)
* [The output panel and input](#the-output-panel-and-input)
* [Errors](#errors)
* [Find, replace and go to line](#find-replace-and-go-to-line)
* [Text files and the preview](#text-files-and-the-preview)
* [Graphics programs](#graphics-programs)
* [Menus](#menus)
* [Keyboard shortcuts](#keyboard-shortcuts)
* [Mouse](#mouse)
* [Themes](#themes)
* [Exporting and importing files](#exporting-and-importing-files)
* [The examples](#the-examples)
* [Known issues](#known-issues)

## Two forms

**Inside ScratchOS** the IDE is a desktop window. Open it from
**Start > Whisker IDE**, from the menu bar (**File > Whisker IDE**, or
**Help > Whisker Reference** and **Help > Whisker Quick Start**, which open
those documents in it), by double-clicking a `.wsk` file in Finder, with the
shell command `ide [file]`, or from a program with
[`gui.ide([path])`](graphics.md#guiidepath). The `ide` command creates the
file if it does not exist. It needs the desktop: in the text console it
says `ide: the desktop is not running (start it with 'startx')`.

**Stand-alone**, the IDE is its own Scratch project. Build it with:

```text
python3 build.py --ide            # writes WhiskerIDE.sb3
python3 build.py --ide -o my.sb3  # or another file name
```

and open the `.sb3` in TurboWarp. It fills the whole stage and starts with
`/projects/main.wsk` open.

| | In ScratchOS | Stand-alone `WhiskerIDE.sb3` |
|---|---|---|
| Size | a window, 122×36 cells at first; resize it down to 72×18 | the whole 960×544 stage: 120×34 cells of 8×16 pixels |
| Folder shown in the tree | `/home/user` (your home folder) | `/` (without `/tmp`, `/dev` and `/home`) |
| Projects folder (new files, Save as, Import) | `/home/user/projects` | `/projects` |
| Examples | `/home/user/examples` (all but `sorting.wsk`) | `/examples` |
| Documents (read-only) | `/usr/share/doc/whisker`: `quickstart.txt`, `reference.txt` | `/docs`: `quickstart.txt`, `reference.txt`, `sort.txt` |
| Libraries | `/lib/yarn.wsk` | `/lib/sort.wsk` ([the sort library](libraries.md#the-sort-library)) |
| Other programs | all of ScratchOS: `/bin`, the shell, the desktop | none: only the IDE's files |
| Graphics windows | ordinary desktop windows | a preview pane inside the IDE |
| `.yarn` pages | Run opens them in the Browser | can be edited, but not shown |
| Theme at start | the desktop's appearance | dark |

In both forms the files live in memory and are reset when the project
restarts. See [Exporting and importing files](#exporting-and-importing-files).

Closing the IDE window in ScratchOS keeps the IDE's state: the open tabs,
unsaved text and output are still there when you open it again, at the same
place and size. A program that is running keeps running.

## The window

From top to bottom:

| Row | Contents |
|---|---|
| Menu bar | the **W** badge, the menus **File Edit Run View Help**, the current file's name, and the **Run** button (**Stop** while a program runs) |
| Tab bar | one tab per open file: its name, then **×** to close it, or **●** if it has unsaved changes. A text file's tab bar also has a **Preview / Edit** switch on the right. |
| File tree | 24 columns on the left, headed **Project** with a **+** (new file). Folders come first, then files; `▸`/`▾` show closed and open folders, and `.wsk` files have a coloured dot. The open file is highlighted. |
| Editor | line numbers, the text, and a scrollbar on the right when the file is taller than the view. The cursor's line is shaded. |
| Output panel | a header (**Output**, a green dot and `running` while a program runs, or the last error in red, then **Clear ▲ ▼ ×**), and below it the program's terminal |
| Status bar | the file's path (with `(read-only)` and a dot for unsaved changes), then `line:column` and the file type (`Whisker`, `Yarn` or `Text`). It shows messages for 3 seconds, the number of selected characters, and the one-line prompts for file names, find and go to line. |

Menus, dialogs and the autocomplete list are drawn over the window.

## Files and tabs

**Opening.** Click a file in the tree to open it in a new tab (or switch to
its tab). Click a folder to open or close it. With the tree focused (click
it first), Up and Down move the selection, Enter opens it, and Left or Right
go back to the editor.

**Switching.** Click a tab. Each tab keeps its own cursor, scroll position
and unsaved text. Tabs that do not fit in the tab bar are not shown, but
stay open; close others to see them.

**New file** (File > New file..., the tree's **+**, or Ctrl+N when no file
is open) asks for a name on the status line:

* A name without `/` is created in the folder selected in the tree (or the
  folder of the selected file), otherwise in the projects folder. A name
  starting with `/` is a full path.
* A name without a `.` gets `.wsk` added.
* A new `.wsk` file starts with a comment holding its name. A new `.yarn`
  file starts with a small example page. Other files start empty.
* If the file exists already, it is opened instead.

**Save** (Ctrl+S) writes the tab's text to its file, with a newline at the
end. Running a program saves it first.

**Save as...** asks for a new path. A name without `/` goes into the
projects folder. The tab then belongs to the new file; the old file is left
as it was. This is the way to edit a copy of a read-only document.

**Rename...** moves the file to a new path (relative names are in the
projects folder). Read-only files cannot be renamed.

**Delete file** asks for confirmation, then deletes the file and closes its
tab. A read-only file is not deleted; only its tab closes.

**Close tab** (or the tab's **×**) closes it. If it has unsaved changes a
dialog asks **Yes** (save, then close), **No** (close without saving) or
**Cancel**.

The documents in the docs folder are **read-only**: you can read, select,
copy and run them, but not change them (the status bar says
`Read-only file`).

## Editing

* Type to insert text. **Enter** starts a new line with the same
  indentation; after a line that opens a block (ending in `then`, `do`,
  `else`, `repeat`, `{` or `(`, or a `function (...)` header without `end`)
  it indents two more spaces. In a `.yarn` file the same happens after
  elements that hold others (`page`, `box`, `row`, `column`, `center`,
  `list`, `item`, `script`, `code`).
* Typing `end`, `else`, `elseif`, `until` or `}` alone on a line moves it
  back to match the block it closes.
* **Backspace** in the leading spaces of a line removes two spaces at once.
  There is no Tab key in the browser: indent with spaces, or with
  **Edit > Indent** (Ctrl+]) and **Edit > Unindent** (Ctrl+\[), which move
  the current line or every selected line by two spaces.
* **Arrows** move; **Ctrl+Left/Right** jump by words; **Home** goes to the
  first non-blank character, and again to column 1; **End** goes to the end
  of the line; **Ctrl+Home/End** go to the start and end of the file;
  **Page Up/Down** move a screen.
* **Selecting:** hold Shift with any movement key, drag with the mouse,
  double-click a word, or click a line number to select that line.
  **Ctrl+A** selects everything. Typing replaces the selection.
* **Clipboard:** Ctrl+X, Ctrl+C and Ctrl+V. Without a selection, Cut and
  Copy take the whole current line. The clipboard belongs to ScratchOS (or
  to the stand-alone IDE). It is shared with
  [`gui.clipboard`](graphics.md#guiclipboardtext) and TextEdit, but not with
  the rest of your computer.
* **Undo and redo:** Ctrl+Z and Ctrl+Y. Typing on one line counts as one
  step. Each tab has its own history; the IDE keeps the last 80 steps
  across all tabs, and a closed tab's history is forgotten.
* **Toggle comment** (Ctrl+/) adds `-- ` to the start of the current or
  selected lines, or removes it if every non-blank line already has it.
* **Duplicate line** (Ctrl+D) copies the current line below itself.
  **Delete line** removes it.

## Syntax highlighting

`.wsk` files are coloured as Whisker:

| Colour group | What |
|---|---|
| keywords | `and break do else elseif end false for function if in local nil not or repeat return then true until while continue` |
| built-ins | built-in functions such as `print` and `tonumber`, the library names (`string`, `math`, `table`, `os`, `io`, `fs`, `proc`, `term`, `gui`, `gfx`, `sys`, `utf8`, `image`, `net`), anything after `library.`, and `pairs`, `ipairs`, `self`, `arg` |
| strings | `"..."` and `'...'` (with `\` escapes) and `[[...]]` long strings |
| comments | `-- ...` and `--[[ ... ]]` block comments |
| numbers | decimal and hexadecimal numbers |
| operators | punctuation and operators |

Long strings and block comments continue across lines.

`.yarn` files ([Yarn pages](libraries.md#the-yarn-library)) are coloured as
Yarn: element names (`page`, `box`, `text`, `button` ...) as keywords,
quoted strings as strings, `key=value` attributes and switches such as
`bold` or `center` as built-ins, `#id` and `.style` names as numbers, and
`--` comment lines as comments. The Whisker code after `->` and the lines of
a `script` block are coloured as Whisker, and the lines of `code` blocks as
strings.

Other files (text files) are not coloured.

## Autocomplete

The autocomplete list suggests the names of built-in functions, keywords
and library names that start with the word before the cursor.

* It opens by itself when you type a `.` after a name, such as `string.`,
  and narrows as you type.
* **Ctrl+Space** opens it at any point. If nothing matches, the status bar
  says `No completions for '...'`.
* Up and Down choose, **Enter** or a click inserts, Esc closes it. Any other
  special key also closes it.
* A function is inserted with `()` and the cursor between the brackets. A
  library name is inserted with its `.` and the list opens again with that
  library's functions.
* It shows at most 8 entries, and it knows only the built-ins, not the
  names in your program. Matching is case-sensitive.
* It is off in text files.

## Running and stopping programs

**Run** with Ctrl+Enter, the **Run** button or **Run > Run**. The IDE:

1. saves the file (a read-only document runs from a copy in
   `/tmp/run.wsk`);
2. writes `► run <path>` in the output panel;
3. compiles and starts the program. A compile error is reported instead
   (see [Errors](#errors)).

The program runs with:

* its folder as the working directory;
* `arg[0]` set to its path, and no arguments (the IDE has no way to pass
  them; to test a program that reads `arg`, set defaults in the program or
  run it from a terminal);
* the output panel as its input, output and error streams;
* every capability (`files`, `proc`, `gui`, `system`, `net`) already
  granted, so it is never asked for permission and `--@caps` lines have no
  effect.

When it ends, the panel shows `■ exit code N (T s)` with the exit code and
the time it ran, or `■ error after T s` after an uncaught error.

**Stop** with Esc, the **Stop** button, **Run > Stop**, or Ctrl+C while the
output panel has focus. The panel shows `■ stopped`. Stopping ends the
program and every process it started. Running again while a program runs
stops the old one first.

Only `.wsk` files run. For a text file the status bar says `... is a text
file - only .wsk programs run`. In ScratchOS, Run on a `.yarn` page opens it
in the Browser (`/bin/browser.wsk`), and **Check syntax** runs the
Browser's checker on it (`browser --check`). The stand-alone IDE has no
Browser and says `Open .yarn pages in the ScratchOS Browser`.

**Check syntax** (Run menu) saves and compiles the file without running it.
It reports `No syntax errors in name.wsk (N instructions)`, where N counts
code cells (instructions and their operands), or marks the error.

## The output panel and input

The output panel is the program's terminal. Everything the program prints
appears there, ANSI colours and `term` calls included, and
[`term.size()`](terminal.md#termsize) gives the panel's size.

When a program starts, the panel gets the keyboard focus. Then:

* typed text goes to the program. A program that calls `io.read()` gets
  the line when you press Enter, with the usual line editing (Backspace,
  arrows, Home/End, history with Up/Down);
* a program in raw mode ([`term.raw`](terminal.md#termrawon)) gets single
  keys from `term.getkey` / `term.waitkey`;
* Ctrl and Shift are dropped from keys before they reach the program, so
  Ctrl+S arrives as `s`. Esc never reaches the program: it stops it.

Click the editor to give it the keyboard back while the program keeps
running; click the panel to return to the program.

**Clear** (or **Run > Clear output**) empties the panel. **▲** and **▼**
make it 3 rows taller or shorter (between 4 and 16 rows), and **×** hides
it. **View > Output** sets it to small (4 rows), medium (8, the default),
large (16) or hidden. When it is hidden, click the status bar to bring it
back.

## Errors

When a program has a compile error, or stops with a runtime error that
nobody caught, the IDE:

* shows the message in red in the output panel header, and in the status
  bar for a compile error;
* opens the file if needed and puts the cursor on the error's line;
* marks that line with a red background and a red line number.

Click the message in the output header, or choose **Run > Go to error**, to
jump back to the line later. Editing the file, or running it again, clears
the mark. Errors caught with `pcall` are not marked.

```lua
-- errors.wsk (from the examples): the first error is caught,
-- the second stops the program and is marked on line 9
local ok, err = pcall(function()
  error("something went wrong")
end)
print("caught:", ok, err)

local function divide(a, b)
  if b == 0 then error("division by zero") end
  return a / b
end
print(divide(10, 2))
print(divide(1, 0))
```

```output
caught: false   prog.wsk:4: something went wrong
5
prog.wsk:9: division by zero
```

(The example file in the IDE has one comment line fewer, so its lines are
one less.) See [language.md](language.md#errors) for the messages.

## Find, replace and go to line

* **Find** (Ctrl+F or Edit > Find...) asks for text on the status line and
  selects the next match after the cursor, wrapping round to the start of
  the file. The search is case-sensitive and matches plain text.
  **Find next** repeats the last search. The status bar says on which line
  it was found, or that it was not found.
* **Replace...** asks for the text to find, then the replacement, and
  replaces every match in the file at once. It reports how many it
  replaced; Ctrl+Z undoes it in one step.
* **Go to line** (Ctrl+G) asks for a line number.

In a prompt, Enter accepts, Esc cancels and Backspace deletes. Clicking
elsewhere also cancels it.

## Text files and the preview

A file that is not a `.wsk` program or a `.yarn` page is a text file. Text
files open in the **Preview**, a formatted, read-only view with word wrap
(at most 100 columns wide). An empty text file opens in the editor. The
Preview understands a little Markdown:

| Source | Shown as |
|---|---|
| `# Heading`, `## Heading`, `### Heading` | headings; the first level is underlined |
| `* item`, `- item`, `+ item`, `1. item` | list items with a hanging indent |
| `> text` | a quote with a bar on the left |
| `---`, `***` or `___` | a horizontal rule |
| lines between ```` ``` ```` fences | a code block with Whisker colours, not wrapped |
| `` `code` ``, `**bold**`, `*emphasis*` | inline styles (the markers are hidden) |

Other lines are paragraphs that keep their indentation.

**Ctrl+E**, **View > Text preview / edit**, or the **Preview / Edit**
switch in the tab bar change between the Preview and the plain-text editor.
Double-clicking a line in the Preview opens the editor at that line. In the
Preview, Up/Down, Page Up/Down, Space, Home/End and the mouse wheel scroll,
and Ctrl+F and Ctrl+G work. The Preview is only for text files: `.wsk` and
`.yarn` files are always edited.

## Graphics programs

**In ScratchOS**, a program run from the IDE opens ordinary desktop
windows, which you can move, resize and close as usual.

**In the stand-alone IDE** there is no desktop, so the newest window a
program opens appears in a **preview pane** over the editor: a frame with
the window's title and a **×** button. It is centred, and if the window is
larger than the space above the output panel it is made smaller and the
program gets a `resize` event with the new size. Click inside it to give it
the focus, then:

* mouse presses, drags and releases reach the program as `mousedown`,
  `drag` and `mouseup` events;
* keys reach it as `key` events (without the Ctrl/Shift modifier);
* **×** sends a `close` event (or removes the pane if the program has
  ended).

The mouse wheel does not reach the program. Esc stops a running program,
which also closes its window; after the program has ended, Esc closes the
pane. Only one window is shown at a time. See [graphics.md](graphics.md).

## Menus

Click a menu title, or press **Esc** to open the File menu (when there is
nothing else for Esc to do: stop a program, close the preview pane or clear
a selection). In an open menu, Left/Right change menus, Up/Down choose an
item, Enter runs it, Esc closes it, and typing the first letter of a menu
title (`f`, `e`, `r`, `v`, `h`) opens that menu. The mouse also highlights
and clicks items.

**File**

| Item | Key | Does |
|---|---|---|
| New file... | (Ctrl+N with no file open) | create a file and open it |
| Save | Ctrl+S | save the current tab |
| Save as... | | save under a new path |
| Rename... | | move the file |
| Delete file | | delete it (asks first) |
| Close tab | | close the tab (asks about unsaved changes) |
| Export (list) | | copy the file into the stage list `ide_export` |
| Import (list) | | create a file from the stage list `ide_export` |

**Edit**

| Item | Key | Does |
|---|---|---|
| Undo / Redo | Ctrl+Z / Ctrl+Y | |
| Cut / Copy / Paste | Ctrl+X / Ctrl+C / Ctrl+V | |
| Select all | Ctrl+A | |
| Find... | Ctrl+F | |
| Find next | | repeat the last search |
| Replace... | | replace every match |
| Go to line... | Ctrl+G | |
| Toggle comment | Ctrl+/ | |
| Duplicate line | Ctrl+D | |
| Delete line | | |
| Indent / Unindent | (Ctrl+] / Ctrl+\[) | two spaces, current or selected lines |

**Run**

| Item | Key | Does |
|---|---|---|
| Run | Ctrl+Enter | save and run |
| Stop | Esc | stop the program |
| Check syntax | | compile without running |
| Go to error | | jump to the last error |
| Clear output | | empty the output panel |

**View**

| Item | Key | Does |
|---|---|---|
| File tree | | show or hide the tree |
| Text preview / edit | Ctrl+E | switch a text file's view |
| Output: small / medium / large / hidden | | 4, 8 or 16 rows, or no panel |
| Theme: dark / light | | |

**Help**

| Item | Does |
|---|---|
| Quick start | opens `quickstart.txt` from the docs folder |
| Language reference | opens `reference.txt`, a short Whisker reference |
| Keyboard shortcuts | a dialog listing the main keys |
| About | the version and credits |

Dialogs: in a Yes / No / Cancel dialog press `y` or Enter for Yes, `n` for
No, Esc or `c` for Cancel, or click a button. A message dialog closes with
Enter, Esc or Space.

## Keyboard shortcuts

| Keys | Action |
|---|---|
| Ctrl+Enter | run (restart if running) |
| Esc | close an open menu, dialog, prompt or autocomplete list; else stop the program; else close the graphics pane; else clear the selection; else open the menus |
| Ctrl+S | save |
| Ctrl+N | new file (only when no file is open) |
| Ctrl+Z / Ctrl+Y | undo / redo |
| Ctrl+X / Ctrl+C / Ctrl+V | cut / copy / paste (the whole line if nothing is selected) |
| Ctrl+A | select all |
| Ctrl+F | find |
| Ctrl+G | go to line |
| Ctrl+Space | autocomplete |
| Ctrl+/ | toggle comment |
| Ctrl+D | duplicate line |
| Ctrl+] / Ctrl+\[ | indent / unindent |
| Ctrl+E | text files: Preview / Edit |
| Shift+movement | select |
| Ctrl+Left / Ctrl+Right | word left / right |
| Ctrl+Home / Ctrl+End | start / end of file |
| Home / End | first non-blank (then column 1) / end of line |
| Page Up / Page Down | one screen |
| Ctrl+C (output panel focused) | stop the program |

## Mouse

* Click in the text to place the cursor; drag to select; double-click to
  select a word; click a line number to select the line.
* The mouse wheel scrolls the tree, the editor or the Preview by 3 lines.
* Drag a scrollbar's thumb, or click the track to jump there.
* Click a tab to switch, its **×** to close it.
* Click **Run** / **Stop** in the menu bar.
* In the output header: **Clear**, **▲**, **▼**, **×**, and the error
  message (go to the error). Click the panel to type into the program.

## Themes

**View > Theme: dark** and **Theme: light** change the IDE's colours,
including the editor's syntax colours and the 16 terminal colours of the
output panel. The stand-alone IDE starts dark. In ScratchOS the IDE takes
the desktop's appearance when it is first opened and follows it when you
change it in System Settings (or with
[`gui.appearance`](graphics.md#guiappearancemode)).

## Exporting and importing files

Files live in memory, so they are lost when the project restarts. The IDE
can move a file between its memory and your computer through a Scratch list
called `ide_export`, which TurboWarp (and Scratch) can save and load as a
text file.

To **export** (save to your computer):

1. Open the file and choose **File > Export (list)**. The current text,
   saved or not, is copied into the list, one line per item, and the list
   appears on the stage.
2. Right-click the list and choose **export**. The browser downloads it as
   a `.txt` file.

To **import** (load from your computer):

1. Choose **File > Import (list)**. If the list is empty, it appears with
   instructions.
2. Right-click the list, choose **import**, and pick a text file.
3. Choose **File > Import (list)** again. Enter a name (a name without `/`
   goes into the projects folder; the default is `imported.wsk`). The file
   is created, or **overwritten without asking** if it exists, and opened.
   The list is hidden again.

This works the same in both forms of the IDE.

## The examples

The examples folder holds short programs to read and run. In ScratchOS
they are in `~/examples`.

| File | Shows |
|---|---|
| `bounce.wsk` | bouncing balls in a window; click to add a ball (events, `gfx.disc`) |
| `clock.wsk` | an analog clock drawn with lines and discs (`os.date`, trigonometry) |
| `cube.wsk` | a shaded 3D cube you can orbit with the mouse (drag, arrows, `+`/`-`, Space) |
| `errors.wsk` | `pcall`, `error`, and an uncaught error the IDE marks |
| `fibonacci.wsk` | recursion against a loop, with timing |
| `fizzbuzz.wsk` | the classic exercise: `if` / `elseif` and `%` |
| `guess.wsk` | guess the number: input with `io.read` |
| `input.wsk` | reading a name and a number from the output panel |
| `mandelbrot.wsk` | an ASCII Mandelbrot set sized to the output panel with `term.size` |
| `objects.wsk` | object-style tables with methods (`:` and `self`) |
| `primes.wsk` | the sieve of Eratosthenes (reads an optional limit from `arg[1]`) |
| `sorting.wsk` | every method of the sort library, compared (stand-alone IDE only) |
| `sortvis.wsk` | bubble sort and insertion sort animated in a window |
| `strings.wsk` | a tour of the string library |

The examples are ordinary files, so you can change them; they are reset
when the project restarts.

## Known issues

* In ScratchOS, **View > Theme** changes the colours of the whole desktop,
  not only the IDE, and only partly: the menu bar changes at once, other
  parts when they are next redrawn, and System Settings still shows the old
  appearance. Use System Settings to change the appearance instead.
* Esc and the Ctrl/Shift modifiers never reach a program running in the
  output panel (see [above](#the-output-panel-and-input)), so a program
  that waits for Esc or a Ctrl key cannot be used from the IDE.
* Tabs that do not fit in the tab bar are not drawn, and there is no way to
  scroll the tab bar.
* There is no way to pass command-line arguments to a program.
* **Check syntax** reports code cells as "instructions".

See also: [getting-started.md](getting-started.md),
[graphics.md](graphics.md), [terminal.md](terminal.md),
[libraries.md](libraries.md).
