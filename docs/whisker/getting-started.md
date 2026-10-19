# Getting started

This is a hands-on tour for someone who has never used Whisker. You will
run a program, try the interactive interpreter, write and edit your own
programs, read input and command-line arguments, build a small word
counter, open a window, and learn how to keep your work, because ScratchOS
forgets every file when it restarts. Each section links to the full
reference when you want the details.

* [Where programs live](#where-programs-live)
* [Running a program](#running-a-program)
* [The interactive interpreter](#the-interactive-interpreter)
* [Your first program](#your-first-program)
* [Writing programs with edit](#writing-programs-with-edit)
* [Reading input](#reading-input)
* [Command-line arguments](#command-line-arguments)
* [Exit codes](#exit-codes)
* [When something goes wrong](#when-something-goes-wrong)
* [A bigger program: a word counter](#a-bigger-program-a-word-counter)
* [A game: guess the number](#a-game-guess-the-number)
* [Using a window](#using-a-window)
* [The Whisker IDE and Finder](#the-whisker-ide-and-finder)
* [Saving your work](#saving-your-work)
* [Next steps](#next-steps)

## Where programs live

A Whisker program is a text file whose name ends in `.wsk`. ScratchOS keeps
all files in memory, in a Unix-like tree:

| Folder | What is there |
|---|---|
| `/bin` | the system's programs: `ls`, `cat`, `edit`, `whisker`, the desktop apps. All of them are Whisker programs, so `cat /bin/hello.wsk` shows real code. |
| `/lib` | libraries for [`require`](libraries.md), such as `yarn.wsk` |
| `/home/user` | your home folder (`~`), where the shell starts. Put your programs here. |
| `~/projects` | a few sample programs (`guess.wsk`, `primes.wsk`, `shapes.wsk`, `main.wsk`) |
| `~/examples` | the Whisker IDE's example programs |
| `/usr/share/doc/whisker` | the IDE's quick start and language reference |
| `/tmp` | scratch space |

You may create and change files anywhere under `/home` and `/tmp`. Changing
files elsewhere needs the `files` permission (see
[system.md](system.md)).

## Running a program

ScratchOS boots to the desktop. Open a terminal from the Start menu
(**Start > Terminal**), or press Esc while ScratchOS boots to get the
full-screen text console instead. Either way you get a shell prompt:

```text
user@scratchos:~$
```

There are three ways to start a program.

**`run` with a file name.** `run` takes a path to a program and its
arguments. The `.wsk` ending may be left out:

```text
user@scratchos:~$ run projects/primes.wsk 30
user@scratchos:~$ cd projects
user@scratchos:~/projects$ run primes 30
```

**The file name itself.** A name that ends in `.wsk` runs a program from the
current folder, without `run`:

```text
user@scratchos:~/projects$ primes.wsk 30
```

**A command name.** A plain name such as `ls` or `hello` is looked up in the
folders listed in the `PATH` variable (`/bin:/usr/bin`). In each folder the
shell tries the name itself, then the name with `.wsk` added. That is why
`hello` runs `/bin/hello.wsk`.

The rules, in order:

1. A name that contains `/` (such as `./guess`, `projects/guess.wsk` or
   `/home/user/projects/guess`) is a path. The shell tries it as given, then
   with `.wsk` added.
2. Any other name is searched for on `PATH`, as above.
3. If that fails and the name ends in `.wsk`, the shell looks in the current
   folder.
4. Otherwise you get `name: command not found` (exit code 127).

So in your home folder `guess` alone is *not* found, but `run guess`,
`./guess` and `guess.wsk` (from inside `projects`) all work. Use `which`
to see what a name means:

```text
user@scratchos:~$ which hello ls cd
hello is /bin/hello.wsk
ls is /bin/ls.wsk
cd is a shell builtin
```

To make your own commands available everywhere, put them in a folder and
add it to `PATH`, for example `export PATH=/bin:/usr/bin:/home/user/bin`.
Files ending in `.sh` are shell scripts: `run` and the rules above start
them in a new shell instead of the Whisker interpreter.

While a program runs it owns the terminal. **Ctrl+C** stops it. The shell
also has pipes, redirection and background jobs, so Whisker programs combine
like Unix tools:

```text
user@scratchos:~$ ls /bin | wc -l
user@scratchos:~$ run projects/primes.wsk 1000 > primes.txt
user@scratchos:~$ run long.wsk &
```

`help` lists the shell's commands, and `man sh` describes the shell.

## The interactive interpreter

`whisker` starts a REPL (read-eval-print loop). Type an expression and it
prints the value. Type a statement and it runs it:

```text
user@scratchos:~$ whisker
ScratchOS 1.0 - Whisker interactive
Type expressions or statements.  'exit' quits.
wsk> 1 + 2
3
wsk> x = 10
wsk> x * 2
20
wsk> function sq(n) return n * n end
wsk> sq(9)
81
wsk> print(1, 2)
1       2
wsk> exit
```

How it works: each line is compiled on its own, first as `return <line>`
(so an expression shows its value), and if that does not compile, as a
statement. That has some consequences:

* **One line at a time.** There is no multi-line input. A loop or function
  must fit on one line: `for i = 1, 3 do print(i) end`. A line that is not
  complete is an error (`line 1: 'end' expected near '<eof>'`).
* **Use globals, not locals.** `local y = 5` works, but `y` is gone on the
  next line, because each line is a separate chunk. Globals (`y = 5`) and
  global functions stay for the whole session.
* **Only the first value is shown.** `1, 2` prints `1`. A value of `nil`
  prints nothing. Strings are printed without quotes.
* **Errors don't end the session.** They are printed in red, and you can go
  on typing.

`exit` or `quit` leaves the REPL. The up and down arrows bring back earlier
lines.

## Your first program

Create a file and run it. The quickest way is the editor, described in the
next section: `edit hello.wsk`, type the program, press Esc, then `X` and
Enter to save and quit. Then `run hello.wsk`.

```lua
print("Hello, world!")
```

```output
Hello, world!
```

`print` writes its arguments and a newline. Here is something with a little
more in it: a local variable, a loop and string concatenation (`..`):

```lua
-- squares.wsk - the first few square numbers
local count = 5
for i = 1, count do
  print(i .. " squared is " .. i * i)
end
print("done")
```

```output
1 squared is 1
2 squared is 4
3 squared is 9
4 squared is 16
5 squared is 25
done
```

Lines that start with `--` are comments. Whisker looks like Lua: blocks end
with `end`, `local` makes a variable that belongs to the block, and
variables without `local` are globals. [language.md](language.md) is the
full reference. Functions and tables work as you would expect:

```lua
local function greet(name, punctuation)
  punctuation = punctuation or "!"
  return "Hello, " .. name .. punctuation
end

local friends = {"Ann", "Bo", "Cy"}
for i, name in ipairs(friends) do
  print(i, greet(name))
end
print(#friends .. " friends, last one: " .. friends[#friends])
```

```output
1       Hello, Ann!
2       Hello, Bo!
3       Hello, Cy!
3 friends, last one: Cy
```

When `print` gets several values it separates them with a tab.

## Writing programs with edit

`edit` is a full-screen text editor for the terminal:

```text
user@scratchos:~$ edit hello.wsk
```

If the file does not exist, it is created when you save. Move with the arrow
keys, Home/End and Page Up/Page Down. Enter starts a new line with the same
indentation as the one above. (There is no Tab key in the browser, so indent
with spaces.)

| Key | Does |
|---|---|
| Esc | opens the menu on the bottom line: type a letter, then Enter |
| Esc, `S` | save |
| Esc, `X` | save and quit |
| Esc, `Q` | quit (asks first if there are unsaved changes) |
| Esc, `O` | open another file |
| Esc, `F` | find text (searches forward from the cursor and wraps around) |
| Esc, `G` | go to a line number |
| Esc, `R` | save and run the program, then press any key to come back |
| Ctrl+S | save |
| Ctrl+X | save and quit |

`Esc, R` is the quickest edit-run loop in the text console. On the desktop
you can also open any file from Finder in TextEdit or, for `.wsk` files, the
Whisker IDE (see [below](#the-whisker-ide-and-finder)).

## Reading input

`io.read()` reads one line from the program's input, without the newline.
At the end of the input it returns `nil`. `io.write` writes text without
adding a newline, which suits prompts:

```lua
io.write("What is your name? ")
local name = io.read()
if name == nil or name == "" then
  name = "stranger"
end
print("Hello, " .. name .. "!")
```

```output
What is your name? Hello, stranger!
```

Run in a terminal, this waits for you to type a line and press Enter. (The
output above is what you get when there is no input at all.) Use
[`tonumber`](stdlib.md#tonumberv--base) to turn typed text into a number. It
returns `nil` if the text is not a number:

```lua
local answers = {"42", "  7 ", "seven", "0x1F"}
for _, text in ipairs(answers) do
  local n = tonumber(text)
  if n then
    print(text .. " -> " .. n * 2)
  else
    print(text .. " -> not a number")
  end
end
```

```output
42 -> 84
  7  -> 14
seven -> not a number
0x1F -> 62
```

To read all the input, use `io.lines()`. It returns a *table* of lines (not
an iterator, as in Lua), so loop over it with `ipairs`:

```lua
local lines = io.lines()
for i, line in ipairs(lines) do
  print(i .. ": " .. line)
end
print(#lines .. " lines")
```

```output
0 lines
```

```text
user@scratchos:~$ ls /bin | run number.wsk
1: about.wsk
2: basename.wsk
...
```

Input from a pipe or a file (`run number.wsk < notes.txt`) ends at the end of
the data. At the keyboard, press Ctrl+D on an empty line to end the input.
Interactive programs are friendlier when they also stop on a word such as
`quit` or an empty line. [system.md](system.md#io-standard-streams) describes `io` in full,
and [terminal.md](terminal.md) covers single keys and full-screen text
programs.

## Command-line arguments

The words after the program name arrive in the global table `arg`.
`arg[1]` is the first argument, `#arg` is how many there are, and `arg[0]`
is the program's full path. Arguments are always strings. Quotes group
words: `run greet.wsk "Ann Lee"` has one argument.

```lua
-- greet.wsk - greet everyone named on the command line
if #arg == 0 then
  print("usage: " .. fs.name(arg[0]) .. " name...")
  exit(2)
end
for i = 1, #arg do
  print("Hello, " .. arg[i] .. "!")
end
```

```output
usage: prog.wsk name...
```

```text
user@scratchos:~$ run greet.wsk Ann "Bo Diddley"
Hello, Ann!
Hello, Bo Diddley!
```

(The tested output says `prog.wsk` because the examples in this manual are
run under that name.) `os.args()` returns the same table. See
[system.md](system.md#arguments-arg-and-osargs).

## Exit codes

Every program ends with an exit code, a number the shell keeps in `$?`. Zero
means success.

| How the program ends | Code |
|---|---|
| it reaches the end of the file | 0 |
| `exit(n)` or `os.exit(n)` | `n` (`exit()` is 0) |
| `return n` at the top level of the file | `n` (a non-number gives 0) |
| an error nobody catches | 1 |
| Ctrl+C | 130 |
| `kill` | 143 |
| the shell could not find or compile it | 127 |

```text
user@scratchos:~$ run greet.wsk
usage: greet.wsk name...
user@scratchos:~$ echo $?
2
user@scratchos:~$ run greet.wsk Ann && echo worked
Hello, Ann!
worked
```

`&&` runs the next command only if the first one succeeded, and `||` only
if it failed. See [system.md](system.md#exit-codes-and-).

## When something goes wrong

There are two kinds of error.

A **compile error** means the program is not valid Whisker. The shell
reports it before anything runs, with the file's full path and the line,
and the exit code is 127. Here `oops.wsk` is missing the `end` of its `if`:

```text
user@scratchos:~$ cat oops.wsk
local x = 1
if x then
  print(x)
user@scratchos:~$ run oops.wsk
/home/user/oops.wsk: line 4: 'end' expected near '<eof>'
```

The line is where the compiler noticed the problem, which here is the end
of the file, one line after the last one.

A **runtime error** happens while the program runs, for example when you do
arithmetic on `nil`. The program stops, the message shows the file name and
line, and the exit code is 1:

```lua
local scores = {10, 20}
print("total: " .. scores[1] + scores[2])
print("third: " .. scores[3] + 0)
```

```output
total: 30
prog.wsk:3: attempt to perform arithmetic on a nil value
```

Call `error("message")` to raise your own error, and use `pcall` to catch
errors instead of stopping:

```lua
local function divide(a, b)
  if b == 0 then error("division by zero") end
  return a / b
end
local ok, result = pcall(divide, 10, 2)
print(ok, result)
ok, result = pcall(divide, 1, 0)
print(ok, result)
```

```output
true    5
false   prog.wsk:2: division by zero
```

Messages in the console are red; [language.md](language.md#errors) lists the
common ones. When the message is not enough, the simplest tool is `print`:
print the values you are unsure of. The [Whisker IDE](ide.md) also moves the
cursor to the line of an error.

## A bigger program: a word counter

This program counts how often each word appears in a file and prints the
most common ones. It shows tables used as dictionaries, a list of keys,
sorting with your own comparison function, reading a file, and reporting an
error properly. Without an argument it counts a built-in sample text, which
is what the tested output shows.

```lua
-- wordcount.wsk - the most common words in a file
--   usage: wordcount.wsk [file] [how-many]
local text = "The cat sat on the mat. The dog sat on the log, and the cat ran."
if arg[1] then
  local data, err = fs.read(arg[1])
  if data == nil then
    io.error("wordcount: " .. arg[1] .. ": " .. err .. "\n")
    exit(1)
  end
  text = data
end
local top = tonumber(arg[2] or "") or 5

-- turn punctuation into spaces, then split into words
local clean = ""
for i = 1, #text do
  local c = text:sub(i, i):lower()
  if c >= "a" and c <= "z" or c == "'" then
    clean = clean .. c
  else
    clean = clean .. " "
  end
end

local counts = {}      -- word -> how many times
local words = {}       -- each different word once
for _, w in ipairs(clean:split()) do
  if counts[w] == nil then
    counts[w] = 0
    words[#words + 1] = w
  end
  counts[w] = counts[w] + 1
end

-- most frequent first; equal counts in alphabetical order
table.sort(words, function(a, b)
  if counts[a] ~= counts[b] then return counts[a] > counts[b] end
  return a < b
end)

print(#words .. " different words")
for i = 1, math.min(top, #words) do
  local w = words[i]
  print(string.format("%-5s %s %d", w, string.rep("#", counts[w]), counts[w]))
end
```

```output
9 different words
the   ##### 5
cat   ## 2
on    ## 2
sat   ## 2
and   # 1
```

Things to notice:

* `text:sub(i, i)` is the same as `string.sub(text, i, i)`. Every
  [string function](stdlib.md#string) can be called this way.
* `clean:split()` with no separator splits at runs of spaces, tabs and
  newlines, and returns a table.
* `counts[w] == nil` tells a new word from one seen before. String keys in
  Whisker tables ignore letter case (`counts.The` is `counts.the`), so the
  `lower()` call is not strictly needed here. See
  [language.md](language.md#keys).
* `table.sort` takes a function that says whether `a` comes before `b`.
* `io.error` writes to the error stream, so the message still shows when the
  output is redirected to a file.

Try it on a real file: `run wordcount.wsk /home/user/readme.txt 3`.

## A game: guess the number

A classic first game. It uses `math.random`, so the output is different every
time, and it needs you to type, so this example is not tested
automatically. A copy is in `~/projects/guess.wsk`.

```lua
-- guess.wsk - guess the number
local secret = math.random(1, 100)
local tries = 0
print("I'm thinking of a number between 1 and 100.")
while true do
  io.write("Your guess: ")
  local line = io.read()
  if line == nil or line == "quit" then
    print("The number was " .. secret .. ".")
    break
  end
  local guess = tonumber(line)
  if guess == nil then
    print("Please type a number (or quit).")
  else
    tries = tries + 1
    if guess < secret then
      print("Too low.")
    elseif guess > secret then
      print("Too high.")
    else
      print("Yes! You needed " .. tries .. " tries.")
      break
    end
  end
end
```

`math.random(1, 100)` returns a whole number from 1 to 100. Each run picks a
new number. `break` leaves the `while true` loop.

## Using a window

On the desktop, programs can open windows and draw in them with the `gui`
and `gfx` libraries. Opening a window needs the `gui` permission. The
`--@caps gui` comment asks for it when the program starts. Programs in
`/bin` have it already, and so do programs run from the Whisker IDE. Run
this from a desktop terminal (not the text console):

```lua
--@caps gui
-- window.wsk - a window with a moving dot; close it to quit
local win = gui.window("Hello", 240, 120)
local x = 0
while true do
  local e = gui.event(win)
  if e and e.type == "close" then break end
  gfx.batch()
  gfx.clear(win, gui.color("window"))
  gfx.text(win, 8, 8, "Hello from Whisker!", gui.color("text"))
  gfx.disc(win, 20 + x, 70, 10, gui.color("accent"))
  gfx.flush()
  x = (x + 4) % 200
  sleep(0.05)
end
gui.close(win)
```

The first time, ScratchOS asks whether the program may open windows:
choose **Allow Once**, **Always Allow** or **Don't Allow** (or press `y`, `a`
or `n`). The loop checks for events (the
close button here), draws a frame between `gfx.batch()` and `gfx.flush()` so
that it appears all at once, and sleeps a little. When the program ends its
windows close. [graphics.md](graphics.md) explains windows, events, colours
and images.

## The Whisker IDE and Finder

The Whisker IDE is an editor and runner in one window, with a file tree,
tabs, syntax highlighting, autocomplete and an output panel. Open it from
the Start menu, the menu bar's **File > Whisker IDE**, or from a desktop
terminal:

```text
user@scratchos:~$ ide hello.wsk
```

`ide` opens the file, creating it if needed. In the IDE, **Ctrl+Enter**
saves and runs the current file, and its output and input go to the Output
panel. Errors put the cursor on the line that caused them. The IDE also
exists as a stand-alone Scratch project, `WhiskerIDE.sb3`.
[ide.md](ide.md) describes both.

In **Finder**, double-clicking a `.wsk` file opens it in the IDE. The **Run**
button starts it in a new terminal window. That window closes as soon as the
program ends, so a program that only prints something disappears at once.
Run such programs from a terminal or the IDE instead, or end them with
`io.read()` so they wait for Enter.

## Saving your work

**ScratchOS keeps files only in memory.** Every boot rebuilds the file
system from the copy built into the project, so everything you created or
changed is gone after a restart (Start > Restart, `reboot`, or reloading
the page). Saving the Scratch project does not save your files either.

To keep a program:

* **Export it from the Whisker IDE.** Open the file, then choose
  **File > Export (list)**. The file appears, one line per item, in a list
  called `ide_export` on the Scratch stage. Right-click the list and choose
  **export** to download it as a `.txt` file. To bring it back later, choose
  **File > Import (list)**, right-click the list, choose **import**, pick the
  file, then choose **File > Import (list)** again and give it a name. See
  [ide.md](ide.md#exporting-and-importing-files).
* **Use the ScratchOS network**, if a server is running: `net.put` stores
  text on the server and `net.get` reads it back after a restart. See
  [system.md](system.md).
* **Build it in.** If you work on ScratchOS itself, files placed in the
  `rootfs/` folder of the source are baked into the project by
  `python3 build.py`.

## Next steps

* [README.md](README.md): the overview and index of this manual.
* [language.md](language.md): the language, including how Whisker differs
  from Lua (no closures over a function's locals, no metatables, case-blind
  table keys).
* [stdlib.md](stdlib.md): `print`, `string`, `math` and `table`.
* [system.md](system.md): input and output, files, processes, permissions
  and the network.
* [terminal.md](terminal.md): colours, keys and full-screen text programs.
* [graphics.md](graphics.md): windows, drawing, events and images.
* [libraries.md](libraries.md): `require`, `load` and the libraries in `/lib`.
* [ide.md](ide.md): the Whisker IDE.
* [internals.md](internals.md): how the compiler and virtual machine work, the
  limits, and how to make programs fast.

The programs in `/bin` are good reading: `cat /bin/wc.wsk`, `/bin/edit.wsk`
or `/bin/snake.wsk`.

See also: [language.md](language.md), [ide.md](ide.md),
[system.md](system.md).
