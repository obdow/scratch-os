# System libraries

These libraries connect a Whisker program to ScratchOS: `io` for the standard
streams, `os` for time and the environment, `fs` for files, `proc` for other
programs, `sys` for the machine, and `net` for the ScratchOS network. This
page also explains the environment a program runs in (arguments, environment
variables, the working directory, pipes, exit codes), the in-memory file
system, and the permission system ("capabilities") that guards the sensitive
calls.

* [Conventions](#conventions)
* [The program environment](#the-program-environment)
* [io: standard streams](#io-standard-streams)
* [os: time, environment, exit](#os-time-environment-exit)
* [The file system](#the-file-system)
* [fs: files and directories](#fs-files-and-directories)
* [proc: processes](#proc-processes)
* [sys: the machine](#sys-the-machine)
* [Permissions (capabilities)](#permissions-capabilities)
* [net: the ScratchOS network](#net-the-scratchos-network)
* [Known issues](#known-issues)

## Conventions

Two kinds of failure are kept apart in every library on this page:

* **A wrong argument type raises an error.** For example `fs.read(nil)`
  stops the program with `bad argument #1 to 'fs.read' (string expected, got
  nil)`, unless you catch it with [pcall](stdlib.md#pcall). Numbers are
  accepted where a string is expected, and numeric strings where a number is
  expected.
* **An operation that fails returns `nil` and a message.** A missing file,
  a directory where a file was expected, a program that can't start: these
  return two values, `nil` and a short text such as `"no such file or
  directory"`. Assign both to see the message.

```lua
local data, err = fs.read("missing.txt")
print(data, err)
local ok, e = pcall(function() return fs.read(nil) end)
print(ok, e)
```

```output
nil	no such file or directory
false	prog.wsk:3: bad argument #1 to 'fs.read' (string expected, got nil)
```

Some error messages name the function without its library, for example
`'getenv'` for `os.getenv` and `'exit'` for `os.exit`.

`pcall` needs a Whisker function, so wrap a library call in
`function() ... end` as above; `pcall(fs.read, nil)` raises `bad argument #1
to 'pcall' (Whisker function expected)`.

Calls that wait (reading input, `sleep`, `proc.wait`, `proc.run`, permission
prompts, `net`) let other programs run meanwhile. They can't be used inside a
callback that a native calls, such as a `table.sort` comparison: there they
raise `cannot wait inside a callback`.

## The program environment

### Arguments: `arg` and os.args()

When a program starts, the global table `arg` holds its command-line
arguments. `arg[1]` to `arg[#arg]` are the arguments, always as strings.
`arg[0]` is the absolute path of the program file. `#arg` counts the
arguments, not `arg[0]`.

```lua
print(fs.name(arg[0]), arg[0] == fs.cwd() .. "/prog.wsk")
print(#arg, arg[1])
```

```output
prog.wsk	true
0	nil
```

The shell splits a command line into words like a Unix shell:

| Input | Becomes |
|---|---|
| `a  b` | two words; runs of spaces and tabs separate words |
| `'b c'` | one word, taken literally (no `$` expansion) |
| `"b c"` | one word; `$NAME`, `${NAME}`, `$?`, `$$` are expanded; `\"`, `\\`, `\$` are escapes |
| `d\ e` | a backslash makes the next character literal |
| `$HOME`, `${HOME}` | the variable's value (empty if unset); `$PWD` is the shell's current directory |
| `~` | `$HOME`, when it is a whole word or starts one (`~/x`) |
| `# ...` | a comment, when `#` starts a word (`x#y` is a plain word) |

There is no globbing: `*.txt` is passed as is. This program prints the words
it receives; the command line is passed through [proc.run](#procruncmdline)
the same way the shell passes it.

```lua
fs.write("args.wsk", "for i = 1, #arg do print(i, arg[i]) end")
local out = proc.run("args.wsk one \"two words\" three\\ four 'f $HOME' $HOME ~ *.txt x#y #gone")
io.write(out)
```

```output
1	one
2	two words
3	three four
4	f $HOME
5	/home/user
6	/home/user
7	*.txt
8	x#y
```

`os.args()` returns the table in the global `arg` (see
[os.args](#osargs)).

### Environment variables

Environment variables are name/value strings, read with
[os.getenv](#osgetenvname) and set with [os.setenv](#ossetenvname-value),
or in the shell with `NAME=value`, `export` and `unset`.

* ScratchOS has **one environment for the whole machine**, not one per
  process. A variable set by a program, a child or the shell is seen by
  every process at once, and stays after the program exits.
* Names ignore letter case: `os.getenv("home")` reads `HOME`.
* At boot the environment holds `PATH=/bin:/usr/bin`, `HOME=/home/user`,
  `USER=user`, `HOSTNAME=scratchos`, `SHELL=/bin/sh`, `TERM=scratch-pen`,
  `OS=ScratchOS` and `LANG=cp437`. `/etc/rc` adds `EDITOR=edit` and
  `PAGER=more`. The shell sets `PWD` on every `cd`.

```lua
print(os.getenv("HOME"), os.getenv("home"), os.getenv("NO_SUCH_VAR"))
fs.write("child.wsk", 'os.setenv("FROM_CHILD", "yes")')
proc.run("child.wsk")
print(os.getenv("FROM_CHILD"))
```

```output
/home/user	/home/user	nil
yes
```

### The working directory

Every process has a current directory. Relative paths in `fs` calls, in
`proc.spawn` and `proc.run` command lines, and in `require` start there. A
new program starts in the directory of the process that started it (usually
the shell's). [fs.chdir](#fschdirpath) changes it for the program only: the
shell and the parent keep theirs.

```lua
local here = fs.cwd()
fs.write("cd.wsk", 'fs.chdir("/") print(fs.cwd())')
io.write(proc.run("cd.wsk"))
print(fs.cwd() == here)
```

```output
/
true
```

### Standard input, output and error

A program has three streams, given to it by whoever started it:

* **stdin**, read with [io.read](#ioread), [io.readall](#ioreadall) and
  [io.lines](#iolines).
* **stdout**, written by `print` and [io.write](#iowrite).
* **stderr**, written by [io.error](#ioerror) and by uncaught errors.

Each stream is one of: the terminal, a pipe, a file, or nothing. The shell
sets them up:

| Shell syntax | Effect on the program |
|---|---|
| `a \| b` | `a`'s stdout feeds `b`'s stdin, a line at a time |
| `> file` | stdout goes to `file` (emptied first) |
| `>> file` | stdout is added to the end of `file` |
| `2> file`, `2>> file` | the same for stderr |
| `< file` | stdin reads `file`'s contents |
| `> /dev/null`, `2> /dev/null` | the output is thrown away |
| `< /dev/null` | stdin is empty |

Writes to a file appear in it straight away. A file used with `<` is read
when the command starts. Ending input:

* From a pipe or a file, `io.read` returns `nil` at the end. A last line
  without a newline is still returned as a line.
* From the terminal, input arrives a line at a time when the user presses
  Enter. Ctrl+D on an empty line ends the input: `io.read` returns `nil`,
  and `io.readall()` and `io.lines()` return what was typed before it.
* A program with no stdin (started from the desktop, for example) reads
  end of input at once.

A background job (`cmd &`) that reads from the terminal waits until it is
the foreground job again. [io.isatty](#ioisatty) tells whether stdout is the
terminal.

This example runs a small shell script with a pipe and a redirection.
`c.wsk` reads its input, `d.wsk` reads `c.wsk`'s output:

```lua
fs.write("in.txt", "apple\nbanana")
fs.write("c.wsk", "for _, l in ipairs(io.lines()) do print(l:upper()) end print(io.isatty())")
fs.write("d.wsk", "local l = io.read() while l do print('> ' .. l) l = io.read() end")
fs.write("q.sh", "run c.wsk < in.txt | run d.wsk")
io.write(proc.run("./q.sh"))
```

```output
> APPLE
> BANANA
> false
```

Programs started from the desktop (not from a terminal window) have their
stderr shown in a message box.

### Exit codes and `$?`

A program ends with an exit code, a number. `0` means success. The shell
puts the last command's code in `$?`, and `&&` / `||` test it.

| How the program ends | Exit code |
|---|---|
| it reaches the end of the file | `0` |
| `return n` at the top level, with a number `n` | `n` (any other value gives `0`) |
| `exit(n)` or `os.exit(n)` | `n` (default `0`) |
| an uncaught error | `1`; the message goes to stderr as `file.wsk:LINE: message` |
| Ctrl+C | `130` |
| killed (`kill`, `proc.kill`, shutdown) | `143` |

The shell itself sets `127` when a command is not found or a program has a
syntax error, and `2` for a bad redirection. Codes are not limited to
0–255: `return 300` gives `300`.

```lua
fs.write("ok.wsk", "return 4")
fs.write("bad.wsk", "local x = nil + 1")
fs.write("empty.wsk", "")
fs.write("t.sh", "run ok.wsk\necho $?\nrun bad.wsk\necho $?\nrun nope.wsk\necho $?\nrun empty.wsk && echo and\nrun bad.wsk || echo or")
local out, code = proc.run("./t.sh")
io.write(out)
```

```output
4
1
127
and
or
bad.wsk:1: attempt to perform arithmetic on a nil value
./nope.wsk: command not found
bad.wsk:1: attempt to perform arithmetic on a nil value
```

An uncaught error prints the message to stderr and ends the program:

```lua
print("before")
error("something broke")
print("after")
```

```output
before
prog.wsk:2: something broke
```

## io: standard streams

| Function | Does |
|---|---|
| `io.write(...)` | write values to stdout, no newline |
| `io.read()` | read one line from stdin |
| `io.readall()` | read the rest of stdin as one string |
| `io.lines()` | read the rest of stdin as a table of lines |
| `io.error(...)` | write values to stderr |
| `io.isatty()` | is stdout the terminal? |

### io.write(...)

Writes its arguments to stdout, converted with
[tostring](stdlib.md#tostring), with nothing between them and no newline at
the end. Any value is accepted (`nil` writes `nil`, a table writes
`table: 0x...`). Returns nothing.

```lua
io.write("a", 1, " ", 2.5, " ", nil, " ", true, "\n")
io.write("no newline")
io.write("\n")
```

```output
a1 2.5 nil true
no newline
```

### io.read()

Reads one line from stdin and returns it without the newline. Returns `nil`
at the end of input. Waits while no line is ready (on the terminal, until
the user presses Enter). It takes no arguments; there are no read formats.

```lua
-- stdin is empty here
print(io.read())
```

```output
nil
```

```lua
fs.write("in.txt", "first\nsecond\nlast")
fs.write("r.wsk", "local l = io.read() while l do print('[' .. l .. ']') l = io.read() end")
fs.write("r.sh", "run r.wsk < in.txt")
io.write(proc.run("./r.sh"))
```

```output
[first]
[second]
[last]
```

### io.readall()

Reads everything until the end of input and returns it as one string.
Every line in the result ends with `"\n"`, including a last line that had
none. Returns `""` when the input is already at its end. On the terminal it
never finishes (see [Standard input](#standard-input-output-and-error)).

```lua
print(io.readall() == "")
fs.write("in.txt", "x\ny")
fs.write("ra.wsk", "io.write('[', io.readall(), ']')")
fs.write("ra.sh", "run ra.wsk < in.txt")
print(proc.run("./ra.sh"))
```

```output
true
[x
y
]
```

### io.lines()

Reads everything until the end of input and returns a table of the lines,
without newlines. Returns an empty table when the input is at its end. It
returns a table, not an iterator: loop over it with `ipairs`.

```lua
local t = io.lines()
print(type(t), #t)
fs.write("in.txt", "one\ntwo\nthree\n")
fs.write("n.wsk", "for i, l in ipairs(io.lines()) do print(i, l) end")
fs.write("n.sh", "run n.wsk < in.txt")
io.write(proc.run("./n.sh"))
```

```output
table	0
1	one
2	two
3	three
```

### io.error(...)

Like `io.write`, but writes to stderr. Use it for error messages, so they
still reach the screen when stdout is redirected or piped. Returns nothing.

```lua
print("to stdout")
io.error("to stderr: ", 42, "\n")
```

```output
to stdout
to stderr: 42
```

(The test above shows stdout first, then stderr.)

### io.isatty()

Returns `true` when stdout is the terminal, `false` when it is a pipe, a
file or nothing. Programs use it to drop colors and screen control when
their output is redirected. It only checks stdout, not stdin.

```lua
-- stdout is a file in this test
print(io.isatty())
```

```output
false
```

## os: time, environment, exit

| Function | Returns |
|---|---|
| `os.time()` | Unix time in whole seconds |
| `os.clock()` | seconds since this program started |
| `os.millis()` | milliseconds since 2000-01-01 |
| `os.date()` | the local date and time, `"YYYY-MM-DD HH:MM:SS"` |
| `os.uptime()` | seconds since boot |
| `os.getenv(name)` | an environment variable, or `nil` |
| `os.setenv(name, value)` | nothing |
| `os.exit([code])` | does not return |
| `os.sleep([seconds])` | nothing, after the wait |
| `os.pid()` | this process's id |
| `os.args()` | the `arg` table |

### os.time()

Returns the current time as whole seconds since 1970-01-01 00:00 UTC (Unix
time). It takes no arguments: unlike Lua it can't convert a date table.

```lua
local t = os.time()
print(type(t), t > 1700000000, t == math.floor(t))
```

```output
number	true	true
```

### os.clock()

Returns the seconds since this program started, as a fractional number. It
measures wall-clock time, not CPU time, so it keeps counting while the
program sleeps or waits.

```lua
local t0 = os.clock()
sleep(0.5)
local dt = os.clock() - t0
print(dt >= 0.45 and dt < 1.5)
```

```output
true
```

### os.millis()

Returns the milliseconds since 2000-01-01 00:00 UTC, a whole number. The
starting point is 2000, not 1970 as with `os.time`. Use it to time things:
the difference between two calls is what counts.

```lua
local ms = os.millis()
print(math.abs(ms / 1000 + 946684800 - os.time()) < 2)
```

```output
true
```

### os.date()

Returns the local date and time as a string `"YYYY-MM-DD HH:MM:SS"`, always
19 characters. Any argument is ignored: there are no format strings, and it
can't format a given time. [sys.date](#sysdate) is the same function.

```lua
local d = os.date()
print(#d, d:sub(5, 5), d:sub(11, 11), d:sub(14, 14))
print(#os.date("%Y"))
```

```output
19	-	 	:
19
```

A typical value is `2026-10-18 23:49:07`. To get the parts, cut the
string:

```lua
local d = os.date()
local year, month, day = tonumber(d:sub(1, 4)), tonumber(d:sub(6, 7)), tonumber(d:sub(9, 10))
local hour, min = tonumber(d:sub(12, 13)), tonumber(d:sub(15, 16))
print(year > 2000, month >= 1 and month <= 12, hour < 24)
```

```output
true	true	true
```

### os.uptime()

Returns the seconds since ScratchOS finished booting, as a fractional
number. Same as [sys.uptime](#sysuptime).

```lua
print(os.uptime() > 0, type(os.uptime()))
```

```output
true	number
```

### os.getenv(name)

Returns the value of environment variable `name` as a string, or `nil` if it
is not set. The name ignores case. `name` must be a string or a number;
anything else raises an error. See [Environment variables](#environment-variables).

```lua
print(os.getenv("USER"), os.getenv("PATH"))
print(os.getenv("NOT_SET"))
```

```output
user	/bin:/usr/bin
nil
```

### os.setenv(name, value)

Sets environment variable `name` to `value` converted to a string, creating
it if needed. Returns nothing. The change is seen by every process on the
machine. `os.setenv(name, nil)` removes the variable, like the shell's
`unset`.

```lua
os.setenv("COLOR", 5)
print(os.getenv("COLOR"), type(os.getenv("COLOR")))
os.setenv("COLOR", nil)
print(os.getenv("COLOR"))
```

```output
5	string
nil
```

### os.exit([code])

Ends the program at once with exit code `code` (default `0`). A numeric
string works too. Code after it never runs. `exit` is the same function.
`os.exit(true)` exits with code 0 and `os.exit(false)` with code 1.

```lua
print("bye")
os.exit(3)
print("never printed")
```

```output
bye
```

```lua
fs.write("ex.wsk", "exit(7)")
local out, code = proc.run("ex.wsk")
print(code)
```

```output
7
```

### os.sleep([seconds])

Pauses the program for `seconds` (default `0`; fractions work). Other
programs run meanwhile. Zero or a negative number returns at once. A
non-number raises an error. `sleep` is the same function.

```lua
local t0 = os.millis()
os.sleep(0.3)
print(os.millis() - t0 >= 250)
```

```output
true
```

### os.pid()

Returns the process id (pid) of the running program, a whole number. Pids
count up from 1 (`init`) and are never reused until the next boot.

```lua
local me = os.pid()
print(type(me), me > 1, proc.alive(me))
```

```output
number	true	true
```

### os.args()

Returns the value of the global variable `arg`: the argument table (see
[Arguments](#arguments-arg-and-osargs)). If the program assigns a new table
to `arg`, `os.args()` returns that one.

```lua
print(os.args() == arg, os.args()[0] == arg[0], #os.args())
```

```output
true	true	0
```

## The file system

ScratchOS keeps all files in memory, inside the Scratch project.

* **Rebuilt at every boot.** The disk image is baked into the project; at
  boot it is loaded fresh. Nothing you write survives a reboot, a reload of
  the page, or a restart of the project.
* **Paths.** Names are separated by `/`. A path starting with `/` is
  absolute, otherwise it starts at the [working directory](#the-working-directory).
  `.` is the current directory and `..` the parent (`..` at `/` stays at
  `/`). Repeated slashes count as one, and a trailing slash is ignored.
  `~` is *not* expanded by `fs` functions; only the shell does that. Use
  `os.getenv("HOME")`.
* **Names** may contain any character except `/`, and can't be empty, `.`
  or `..`. Names are **case-insensitive but case-preserving**: `A.TXT` and
  `a.txt` are the same file, and the file keeps the spelling it was created
  with. Writing to `MIXED.txt` when `Mixed.TXT` exists overwrites
  `Mixed.TXT`; a rename can change the case.
* **Files** hold text (any characters). The size is the number of
  characters. Directories have size 0. There are no permissions bits,
  owners, links or hidden files.
* **Modification time.** Files and directories record when they last
  changed, shown by [fs.stat](#fsstatpath) as Unix seconds (`mtime`) and as
  `"YYYY-MM-DD HH:MM"` (`date`, in UTC). Files from the disk image have the
  boot time.
* **Protected files.** Only what is inside `/home` and `/tmp` is free for
  any program to change; the two folders themselves are protected. Changing anything else (creating,
  writing, removing or renaming in `/bin`, `/etc`, `/lib`, `/usr`, `/dev`
  or `/` itself) needs the `files` [capability](#permissions-capabilities).
  Reading is always allowed.

The tree at boot:

| Path | Holds |
|---|---|
| `/bin` | the commands, as Whisker programs (`ls.wsk`, `cat.wsk`, ...) |
| `/etc` | `rc` (the start-up script), `caps` (the permission policy), `motd`, `hostname` |
| `/lib` | Whisker libraries for [require](libraries.md) |
| `/usr/share` | manual pages (`man`), help text, wallpapers, Yarn pages |
| `/home/user` | your home: `readme.txt`, `test.wsk`, `hello.sh`, `projects/`, `examples/`, `Pictures/`, `Sites/` |
| `/tmp` | empty; scratch space for any program |
| `/dev` | empty; `/dev/null` is understood by the shell's redirections only |

```lua
print(table.concat(fs.list("/"), " "))
print(fs.stat("/etc").protected, fs.stat("/home/user").protected, fs.stat("/tmp").protected)
```

```output
bin dev etc home lib tmp usr
true	false	false
```

## fs: files and directories

All paths can be relative or absolute. Arguments that must be paths raise
an error if they are not strings (or numbers). Failures return `nil` and a
message. The messages are:

| Message | Meaning |
|---|---|
| `no such file or directory` | a name in the path does not exist |
| `not a directory` | a file was used as a directory |
| `is a directory` | a directory was used as a file |
| `file exists` | a file is in the way of a directory, or the other way round |
| `directory not empty` | `fs.remove` of a full directory without `recursive` |
| `invalid name` | the last name is empty, `.` or `..` |
| `empty path` | the path is `""` |
| `cannot remove the current directory` | the target is the working directory or holds it |
| `cannot move a directory into itself`, `cannot copy a directory into itself` | |
| `target is a directory` | `fs.rename` would replace a directory |

Changing a protected path asks for the `files` capability first; if the user
refuses, the call raises `permission denied (capability 'files' was
refused)`.

| Function | Returns |
|---|---|
| `fs.read(path)` | the file's text |
| `fs.write(path, data)` | `true` |
| `fs.append(path, data)` | `true` |
| `fs.list([dir])` | a sorted table of names |
| `fs.exists(path)` | `true` / `false` |
| `fs.isdir(path)` | `true` / `false` |
| `fs.mkdir(path)` | `true` |
| `fs.remove(path [, recursive])` | `true` |
| `fs.rename(from, to)` | `true` |
| `fs.copy(from, to)` | `true` |
| `fs.stat(path)` | a table of facts |
| `fs.cwd()` | the working directory |
| `fs.chdir(path)` | `true` |
| `fs.abs(path)` | an absolute path |
| `fs.name(path)` | the last name in a path |
| `fs.dir(path)` | the path without its last name |

### fs.read(path)

Returns the whole contents of the file at `path` as a string. Fails with
`nil` and a message if the file is missing or is a directory.

```lua
fs.write("hello.txt", "Hello!\nSecond line")
print(fs.read("hello.txt"))
print(fs.read("HELLO.TXT") == fs.read("hello.txt"))
local d, err = fs.read("nope.txt") print(d, err)
d, err = fs.read("/home") print(d, err)
```

```output
Hello!
Second line
true
nil	no such file or directory
nil	is a directory
```

### fs.write(path, data)

Replaces the contents of the file at `path` with `data`, creating the file
if needed. `data` is converted with `tostring` (a number becomes its digits,
a missing `data` writes the text `nil`). The parent directory must exist.
Returns `true`. Fails if `path` is a directory, or its directory is missing.

```lua
print(fs.write("a.txt", "one"))
print(fs.write("n.txt", 42), fs.read("n.txt"), type(fs.read("n.txt")))
local ok, err = fs.write("no/such/dir.txt", "x") print(ok, err)
ok, err = fs.write(".", "x") print(ok, err)
ok, err = fs.write("a.txt/inner", "x") print(ok, err)
```

```output
true
true	42	string
nil	no such file or directory
nil	is a directory
nil	not a directory
```

### fs.append(path, data)

Adds `data` (converted with `tostring`) to the end of the file at `path`,
creating the file if needed. Returns `true`. Fails like `fs.write`.

```lua
fs.append("log.txt", "first\n")
fs.append("log.txt", "second\n")
io.write(fs.read("log.txt"))
```

```output
first
second
```

### fs.list([dir])

Returns a table of the names in directory `dir` (default: the working
directory), sorted. Names are just names, not paths. Fails if `dir` is
missing or is a file.

Sorting ignores case, and names that are numbers sort by value (`9` before
`10`).

```lua
fs.mkdir("box")
for _, n in ipairs({"Zeta.txt", "alpha", "Beta", "10", "9", "_x"}) do fs.write("box/" .. n, "") end
fs.mkdir("box/sub")
print(table.concat(fs.list("box"), " "))
local t, err = fs.list("box/alpha") print(t, err)
t, err = fs.list("nope") print(t, err)
```

```output
9 10 _x alpha Beta sub Zeta.txt
nil	not a directory
nil	no such file or directory
```

To tell files from directories, use [fs.isdir](#fsisdirpath) on each
name, joined to the directory path:

```lua
fs.mkdir("d") fs.mkdir("d/pics") fs.write("d/notes.txt", "")
for _, n in ipairs(fs.list("d")) do
  if fs.isdir("d/" .. n) then print(n .. "/") else print(n) end
end
```

```output
notes.txt
pics/
```

### fs.exists(path)

Returns `true` if a file or directory exists at `path`, otherwise `false`.
It never fails, except that a non-string `path` raises an error.

```lua
fs.write("f.txt", "")
print(fs.exists("f.txt"), fs.exists("F.TXT"), fs.exists("./f.txt"), fs.exists("f.txt/"))
print(fs.exists("missing"), fs.exists("f.txt/x"), fs.exists("/bin"))
```

```output
true	true	true	true
false	false	true
```

### fs.isdir(path)

Returns `true` if `path` is a directory, `false` if it is a file or does
not exist.

```lua
fs.write("f.txt", "")
print(fs.isdir("."), fs.isdir("/"), fs.isdir("f.txt"), fs.isdir("missing"))
```

```output
true	true	false	false
```

### fs.mkdir(path)

Creates the directory `path`. Returns `true`, also when the directory
already exists. Only the last name is created: the parent must exist (there
is no "make parents" option). Fails if the parent is missing or a file is in
the way.

```lua
print(fs.mkdir("new"), fs.mkdir("new"), fs.isdir("new"))
local ok, err = fs.mkdir("x/y") print(ok, err)
fs.write("file", "")
ok, err = fs.mkdir("file") print(ok, err)
print(fs.mkdir("x"), fs.mkdir("x/y"))
```

```output
true	true	true
nil	no such file or directory
nil	file exists
true	true
```

### fs.remove(path [, recursive])

Deletes the file or directory at `path`. A directory must be empty unless
`recursive` is true, which deletes everything inside it as well. Returns
`true`. Fails if `path` is missing, is a full directory without
`recursive`, or is the working directory or one of its parents.

```lua
fs.mkdir("d") fs.write("d/a", "1") fs.mkdir("d/e") fs.write("d/e/b", "2")
local ok, err = fs.remove("d") print(ok, err)
print(fs.remove("d/a"), fs.exists("d/a"))
ok, err = fs.remove("d/a") print(ok, err)
print(fs.remove("d", true), fs.exists("d"))
ok, err = fs.remove("..") print(ok, err)
```

```output
nil	directory not empty
true	false
nil	no such file or directory
true	false
nil	cannot remove the current directory
```

### fs.rename(from, to)

Moves or renames a file or directory. Returns `true`.

* If `to` is an existing directory, `from` moves **into** it, keeping its
  name.
* Otherwise `from` gets the path `to`. The directory of `to` must exist. An
  existing *file* at `to` is replaced; an existing directory can't be
  replaced (it is treated as the first case).
* A directory can't move into itself.

Changing only the case of a name works (`fs.rename("c", "C")`).

```lua
fs.write("a", "A")
print(fs.rename("a", "b"), fs.exists("a"), fs.read("b"))
fs.mkdir("dir")
print(fs.rename("b", "dir"), table.concat(fs.list("dir"), ","))
fs.write("x", "new") fs.write("y", "old")
print(fs.rename("x", "y"), fs.read("y"), fs.exists("x"))
local ok, err = fs.rename("dir", "dir/inner") print(ok, err)
ok, err = fs.rename("nope", "z") print(ok, err)
```

```output
true	false	A
true	b
true	new	false
nil	cannot move a directory into itself
nil	no such file or directory
```

### fs.copy(from, to)

Copies a file, or a directory with everything in it. The destination rules
are those of `fs.rename`: an existing directory `to` receives a copy inside
it. Copying a file over an existing file replaces its contents; copying a
directory onto an existing directory of the same name merges into it.
Returns `true`. Fails if `from` is missing, a file and a directory are in
each other's way (`file exists`), or a directory would be copied into
itself. Copies get the current time as their modification time.

```lua
fs.mkdir("src") fs.write("src/one", "1") fs.write("src/two", "2")
print(fs.copy("src", "dst"), table.concat(fs.list("dst"), ","))
print(fs.copy("src/one", "single"), fs.read("single"))
fs.mkdir("into")
print(fs.copy("single", "into"), table.concat(fs.list("into"), ","))
local ok, err = fs.copy("src", "src/deeper") print(ok, err)
```

```output
true	one,two
true	1
true	single
nil	cannot copy a directory into itself
```

### fs.stat(path)

Returns a table describing the file or directory at `path`, or `nil` and a
message if it does not exist. The fields:

| Field | Value |
|---|---|
| `name` | the name, as stored (`""` for `/`) |
| `path` | the absolute path, with stored spelling |
| `type` | `"file"` or `"dir"` |
| `size` | characters in the file; `0` for a directory |
| `mtime` | last change, in Unix seconds |
| `date` | last change as `"YYYY-MM-DD HH:MM"` (UTC) |
| `inode` | the internal file number (it can be reused after a delete) |
| `protected` | `true` if changing it needs the `files` capability |

```lua
fs.write("s.txt", "12345")
local st = fs.stat("S.TXT")
print(st.name, st.path == fs.cwd() .. "/s.txt", st.type, st.size, st.protected)
print(math.abs(st.mtime - os.time()) < 5, #st.date, st.inode > 0)
local r = fs.stat("/")
print("[" .. r.name .. "]", r.path, r.type, r.size, r.protected)
local s, err = fs.stat("nope") print(s, err)
```

```output
s.txt	true	file	5	false
true	16	true
[]	/	dir	0	true
nil	no such file or directory
```

### fs.cwd()

Returns the absolute path of the working directory.

```lua
-- the tests run in /home/user/dt/<number>
print(fs.cwd():sub(1, 14))
fs.chdir("/usr/share")
print(fs.cwd())
```

```output
/home/user/dt/
/usr/share
```

### fs.chdir(path)

Makes `path` the working directory of this program. Returns `true`. Fails
if `path` is missing or is a file. It does not change the shell's directory
after the program exits.

```lua
print(fs.chdir(".."), fs.cwd())
print(fs.chdir("/HOME//User/"), fs.cwd())
print(fs.chdir("../../.."), fs.cwd())
local ok, err = fs.chdir("nope") print(ok, err)
ok, err = fs.chdir("/etc/motd") print(ok, err)
```

```output
true	/home/user/dt
true	/home/user
true	/
nil	no such file or directory
nil	not a directory
```

### fs.abs(path)

Returns the absolute, tidied form of `path` (no `.`, `..` or double
slashes), with the stored spelling of existing names. The last name does
not need to exist, but its directory must. Fails with `no such file or
directory` if the directory is missing, and with `invalid name` for `""`.

```lua
fs.chdir("/home/user")
print(fs.abs("."), fs.abs(".."), fs.abs("./new.txt"))
print(fs.abs("/etc/../BIN"), fs.abs("/not-yet"), fs.abs("//usr///share/"))
local p, err = fs.abs("a/b/c") print(p, err)
p, err = fs.abs("") print(p, err)
```

```output
/home/user	/home	/home/user/new.txt
/bin	/not-yet	/usr/share
nil	no such file or directory
nil	invalid name
```

### fs.name(path)

Returns the last name in `path`, ignoring trailing slashes. It works on the
text only; the path does not need to exist.

### fs.dir(path)

Returns `path` without its last name: the directory part. Returns `"."`
when there is no directory part, and `"/"` for a name directly under the
root. It works on the text only.

```lua
for _, p in ipairs({"/a/b/c.txt", "c.txt", "/a/b/", "/top", "/", ""}) do
  print("[" .. p .. "]", "[" .. fs.name(p) .. "]", "[" .. fs.dir(p) .. "]")
end
```

```output
[/a/b/c.txt]	[c.txt]	[/a/b]
[c.txt]	[c.txt]	[.]
[/a/b/]	[b]	[/a]
[/top]	[top]	[/]
[/]	[]	[/]
[]	[]	[.]
```

## proc: processes

A process is a running program: a Whisker program, a shell, or `init`
(pid 1). Each has a pid, a parent (the process that started it), a working
directory and three streams.

| Function | Returns |
|---|---|
| `proc.spawn(cmdline)` | the new pid |
| `proc.wait(pid)` | the exit code |
| `proc.run(cmdline)` | output and exit code |
| `proc.kill(pid)` | `true` |
| `proc.alive(pid)` | `true` / `false` |
| `proc.list()` | a table of processes |
| `proc.pid()` | the caller's pid |

**Command lines.** `proc.spawn` and `proc.run` take one string, split into
words like the shell does ([quoting](#arguments-arg-and-osargs), `$VAR`,
`~`). The first word is the program:

* a name without `/` is looked up in the directories of `$PATH`, with or
  without `.wsk` (`ls` finds `/bin/ls.wsk`); a name ending in `.wsk` is also
  found in the working directory;
* a name with `/` (`./tool.wsk`, `/home/user/x`) is a path, again with or
  without `.wsk`;
* `run file args...` runs `file` from the working directory;
* a file ending in `.sh` runs as a shell script, so a script can do what a
  command line can't (see below).

Only one simple command runs. There are no pipes, redirections or shell
builtins: `|`, `<` and `>` are passed to the program as arguments, and
`echo`, `cd` and the other builtins are not found. `;`, `&&`, `||` and `&`
end the command line; the rest is ignored. For a pipeline, write it to a
`.sh` file and run that by path (`./job.sh`):

```lua
fs.write("job.sh", "echo one two three | rev\necho done")
local out, code = proc.run("./job.sh")
io.write(out)
print(code)
```

```output
eerht owt eno
done
0
```

The new process inherits the caller's working directory, stdin and stderr.
It does not inherit the caller's granted capabilities.

### proc.spawn(cmdline)

Starts a program and returns its pid at once, without waiting. The child
writes to the caller's stdout and runs alongside it. Returns `nil` and
`cannot start '<cmdline>'` if the program is not found or does not compile
(the compiler's message goes to stderr).

The child shares the caller's process group, so Ctrl+C stops both, and the
shell waits for the child too before showing its prompt. It keeps running
if the caller ends first.

```lua
fs.write("child.wsk", "print('child says hi to ' .. arg[1])")
local pid = proc.spawn("child.wsk Ann")
print("parent goes first")
print(proc.wait(pid))
local p, err = proc.spawn("no-such-program")
print(p, err)
```

```output
parent goes first
child says hi to Ann
0
nil	cannot start 'no-such-program'
```

### proc.wait(pid)

Waits until process `pid` ends, then returns its exit code. If it has
already ended, returns the code at once (and can do so again). Returns `nil`
for a pid that never existed, or whose record is gone: ScratchOS keeps the
codes of the last 64 processes that ended. Any process can be waited for,
not only children. A non-number raises an error.

```lua
fs.write("slow.wsk", "sleep(0.3) exit(7)")
local p = proc.spawn("slow.wsk")
print(proc.alive(p))
print(proc.wait(p))
print(proc.alive(p), proc.wait(p))
print(proc.wait(99999))
```

```output
true
7
false	7
nil
```

### proc.run(cmdline)

Runs a command, waits for it to end, and returns two values: everything it
wrote to **stdout**, as a string, and its exit code. The child's stderr is
not captured; it goes to the caller's stderr. Output is collected a line at
a time, so a non-empty result always ends with `"\n"`, even if the last
line had none. Returns `nil` and `cannot start '<cmdline>'` if the program
can't start.

```lua
fs.write("tool.wsk", "io.write('out') io.error('this goes to stderr\\n') exit(3)")
local out, code = proc.run("tool.wsk")
print("[" .. out .. "]", code)
local o, err = proc.run("missing-tool") print(o, err)
o, err = proc.run("echo builtins are not found") print(o, err)
```

```output
[out
]	3
nil	cannot start 'missing-tool'
nil	cannot start 'echo builtins are not found'
this goes to stderr
```

Commands from `/bin` work as usual:

```lua
fs.write("words.txt", "pear\napple\nfig\n")
local out = proc.run("sort words.txt")
io.write(out)
local n = proc.run("wc -l words.txt")
print(#n > 0)
```

```output
apple
fig
pear
true
```

### proc.kill(pid)

Stops process `pid` with exit code `143`. Returns `true`. Fails with `nil`
and `no such process` if `pid` is not running, and `cannot kill init` for
pid 1. Killing yourself ends the program at once (code 143). Killing a
process you did not start, directly or through your children, needs the
`proc` capability; if the user refuses, the call raises an error.

```lua
fs.write("forever.wsk", "while true do sleep(1) end")
local p = proc.spawn("forever.wsk")
print(proc.kill(p))
print(proc.wait(p), proc.alive(p))
local ok, err = proc.kill(p) print(ok, err)
ok, err = proc.kill(1) print(ok, err)
```

```output
true
143	false
nil	no such process
nil	cannot kill init
```

### proc.alive(pid)

Returns `true` if process `pid` is running (or waiting), otherwise
`false`.

```lua
print(proc.alive(os.pid()), proc.alive(1), proc.alive(0), proc.alive(99999))
```

```output
true	true	false	false
```

### proc.list()

Returns a table with one entry per process, in process-table order. Each
entry is a table:

| Field | Value |
|---|---|
| `pid` | process id |
| `ppid` | parent's pid (`0` for `init`) |
| `name` | the command line that started it (for a shell, `-sh` or the script) |
| `path` | the program file (`""` for `init`) |
| `state` | `"run"` (ready), `"sleep"`, `"wait"` (for input or a child), `"prompt"` (for a permission answer), `"stop"` |
| `kind` | `"wsk"` (Whisker program), `"shell"` or `"init"` |
| `cpu` | Whisker instructions run so far, counted at the end of each time slice (0 for shells) |
| `time` | seconds since it started, to 0.1 s |
| `tty` | its terminal number (`0` for none) |
| `mem` | approximate memory: heap cells of its tables plus its stack |

[sys.procs](#sysprocs) returns the same table.

```lua
for _, e in ipairs(proc.list()) do
  if e.pid == 1 then print(e.name, e.kind, e.ppid, e.path == "") end
  if e.pid == os.pid() then print(fs.name(e.path), e.kind, e.state, type(e.cpu), type(e.mem)) end
end
```

```output
init	init	0	true
prog.wsk	wsk	run	number	number
```

### proc.pid()

Returns the caller's pid, like [os.pid](#ospid).

```lua
print(proc.pid() == os.pid())
```

```output
true
```

## sys: the machine

| Function | Returns |
|---|---|
| `sys.version()` | `"ScratchOS 1.0"` |
| `sys.hostname()` | the `HOSTNAME` variable |
| `sys.uptime()` | seconds since boot |
| `sys.date()` | same as `os.date()` |
| `sys.mem()` | a table of memory statistics |
| `sys.gc()` | tables freed by a garbage collection |
| `sys.procs()` | same as `proc.list()` |
| `sys.caps()` | this program's capabilities |
| `sys.request(cap)` | `true` / `false` |
| `sys.shutdown()`, `sys.reboot()` | nothing |

### sys.version()

Returns the name and version of the system.

```lua
print(sys.version())
```

```output
ScratchOS 1.0
```

### sys.hostname()

Returns the value of the `HOSTNAME` environment variable (`"scratchos"` at
boot), or `""` if it is unset. The file `/etc/hostname` is not used.

```lua
print(sys.hostname())
```

```output
scratchos
```

### sys.uptime()

Returns the seconds since boot, like [os.uptime](#osuptime).

```lua
local up = math.floor(sys.uptime())
print(math.floor(up / 60) .. "m " .. up % 60 .. "s")   -- for example 3m 12s
```

### sys.date()

Returns the local date and time, like [os.date](#osdate).

```lua
print(#sys.date(), sys.uptime() > 0)
```

```output
19	true
```

### sys.mem()

Returns a table of memory figures for the whole machine:

| Field | Meaning |
|---|---|
| `heap`, `heap_max` | cells used in the shared table heap, and its limit (200000) |
| `tables` | live tables |
| `code`, `code_max` | bytecode cells used by loaded programs, and the limit (150000) |
| `files` | files and directories |
| `file_bytes` | characters in all files |
| `procs` | running processes |
| `gc_runs` | garbage collections so far |
| `instructions` | Whisker instructions run since boot |

See [internals](internals.md) for what the limits mean.

```lua
local m = sys.mem()
print(m.heap_max, m.code_max, m.files > 10, m.procs >= 3)
```

```output
200000	150000	true	true
```

### sys.gc()

Runs the garbage collector now and returns the number of tables it freed.
You rarely need it: collection also runs on its own when the heap fills up.

```lua
local runs = sys.mem().gc_runs
local freed = sys.gc()
print(type(freed), sys.mem().gc_runs - runs)
```

```output
number	1
```

### sys.procs()

Returns the process table, exactly like [proc.list](#proclist).

```lua
print(#sys.procs() == #proc.list(), sys.procs()[1].name)
```

```output
true	init
```

### sys.caps()

Returns a table of the capability names this program holds, such as
`{"files", "gui"}`. A capability the user refused appears with a `!` in
front (`"!files"`). A program outside `/bin` starts with none.

```lua
print(#sys.caps())
```

```output
0
```

### sys.request(cap)

Asks for capability `cap` now and returns `true` if the program has it,
`false` if not. If the program doesn't hold it yet, the user is asked (see
[Permissions](#permissions-capabilities)) and the call waits for the answer.
A capability refused before returns `false` without asking again. An
unknown name returns `false` without asking. `cap` must be a string.

```lua
print(sys.request("no-such-capability"))
```

```output
false
```

```lua
-- asks the user once, then the real call needs no prompt
if sys.request("files") then
  fs.write("/etc/motd", "Have a nice day!\n")
else
  io.error("not allowed to change /etc/motd\n")
end
```

### sys.shutdown()

Needs the `system` capability. Stops every process (exit code 143), then
turns ScratchOS off. The program does not continue in any useful way after
the call. If the user refuses the capability, the call raises an error.

```lua
--@caps system
print("Shutting down.")
sys.shutdown()
```

### sys.reboot()

Like `sys.shutdown`, then starts ScratchOS again. Since the file system is
rebuilt at boot, every change since the last boot is lost.

```lua
--@caps system
print("Restarting...")
sys.reboot()
```

## Permissions (capabilities)

Whisker programs start with no special rights. A few calls need a
**capability**, a named permission:

| Capability | Guards |
|---|---|
| `files` | changing anything outside `/home` and `/tmp`: `fs.write`, `fs.append`, `fs.mkdir`, `fs.remove`, `fs.rename` (both ends), `fs.copy` (the destination) |
| `proc` | `proc.kill` on a process that is not your descendant |
| `gui` | `gui.window`, `gui.terminal`, `gui.ide`, `gui.launch` (see [graphics](graphics.md)) |
| `system` | `sys.shutdown`, `sys.reboot` |
| `net` | `net.ping`, `net.get`, `net.put`, `net.list` |

Reading files, listing processes, starting programs, `net.status` and
`net.id` need nothing.

### How a capability is granted

When a call needs a capability the program does not hold, ScratchOS asks
the user, and the program waits:

```
 Permission request  /home/user/c.wsk wants to
  modify system files (outside /home and /tmp) [files]
  Allow? (y)es / (n)o / (a)lways:
```

The question appears in the program's terminal, or as a dialog on the
desktop. One question is shown at a time; other programs that need one
wait their turn.

| Answer | Keys | Effect |
|---|---|---|
| yes | `y`, Enter | granted until this program ends |
| no | `n`, Esc, Ctrl+C | refused until this program ends; the call raises an error |
| always | `a` | granted, and a line `path cap` is added to `/etc/caps` |

A refused capability makes the call raise `permission denied (capability
'files' was refused)` (catch it with `pcall`). Later calls that need it
raise the same error at once, without asking. `sys.request` returns `false`
instead of raising. Capabilities belong to one run of one program: children
started with `proc.spawn` or `proc.run` ask for their own.

A refused call, caught:

```lua
local ok, err = pcall(function() return fs.write("/etc/x", "1") end)
print(ok, err)
-- if the user answers n:
-- false   c.wsk:1: permission denied (capability 'files' was refused)
```

### Declaring capabilities: `--@caps`

A comment line starting with `--@caps` lists capabilities the program
needs. They are asked for when the program starts, before its first line
runs, so the questions don't interrupt it later. Several names go on one
line, separated by spaces, and there can be several such lines. Unknown
names are skipped. The comment must start exactly `--@caps` (no space after
`--`).

```lua
--@caps files system
print(table.concat(sys.caps(), ","))   -- files,system  (if both were allowed)
```

Answering no to a declared capability does not stop the program; it runs,
and the guarded call raises the error when reached.

### The policy file: /etc/caps

`/etc/caps` grants capabilities to programs without asking. Each line is a
program path (or a prefix ending in `*`) followed by capability names.
Lines starting with `#` are comments. At boot it holds:

```
/bin/*  files proc gui system net
```

so everything in `/bin` is trusted. The shell builtin `caps` manages it:

| Command | Does |
|---|---|
| `caps` | show the policy and the capabilities of running programs |
| `caps grant PATH CAP` | add the line `PATH CAP` |
| `caps revoke PATH [CAP]` | remove `PATH`'s lines (or only those naming `CAP`) |

The policy is read at boot and again after `caps grant`, `caps revoke` or an
"always" answer; editing the file by hand takes effect only at one of
those. Like every file, `/etc/caps` returns to its original contents at the
next boot. Shell scripts (`.sh`) and the shell itself hold every
capability.

## net: the ScratchOS network

`net` reaches files on the ScratchOS server through Scratch cloud
variables. Everything except `net.status` and `net.id` needs the `net`
capability. Calls wait until the server answers. Failures return `nil` and a
message: `offline: this copy of ScratchOS has no cloud connection`, `the
ScratchOS server is not responding`, `too many requests: try again in N
seconds`, `upload limit reached: ...`, `too big: ...`, or an error from the
server (such as a missing file). The protocol, the limits and the server
are described in [NETWORK.md](../NETWORK.md).

**Names** are 1 to 100 characters from letters, digits, `_`, `-`, `.` and
`/`, without `..`. A bad name fails with `nil` and `bad name '...' (use
letters, digits, _ - . and /)` before any capability check. The server
accepts writes only under `public/` and `users/`.

### net.status()

Returns a table: `state` (`"online"`, `"no server"` or `"offline"`),
`online` (`true` when online), `id` (this computer's id), and `sent`,
`received` (packets), `requests` (requests the rate limit allows now),
`upload` (characters you may upload now). When the server has been heard:
`heartbeat` (seconds since its last one), `clients`, `packet` (the maximum
packet length). After a ping: `latency` (milliseconds). Needs no
capability.

```lua
local s = net.status()
print(s.state, s.online)
```

```output
offline	false
```

(The tests run without a cloud connection.)

### net.ping()

Asks the server to answer and returns the round trip in milliseconds.

```lua
local ms, err = net.ping()
if ms then print("server answered in " .. ms .. " ms") else print(err) end
```

### net.get(name)

Returns the text of the file `name` on the server.

```lua
local text, err = net.get("public/motd.txt")
print(text or err)
```

### net.put(name, text)

Stores `text` (up to 8192 characters) as `name` on the server. Returns
`true`. `text` is converted to a string.

```lua
local ok, err = net.put("users/" .. net.id() .. "/note.txt", "remember the milk")
if not ok then print(err) end
```

### net.list([prefix])

Returns a table of the names on the server that start with `prefix`
(default: all).

```lua
local names = net.list("public/")
if names then for _, n in ipairs(names) do print(n) end end
```

### net.id()

Returns this computer's id, a random number chosen at boot. Needs no
capability.

```lua
print(type(net.id()))
local ok, err = net.get("bad name!")
print(ok, err)
```

```output
number
nil	bad name 'bad name!' (use letters, digits, _ - . and /)
```

```lua
--@caps net
if net.status().online then
  local ok, err = net.put("public/hello.txt", "hi from " .. net.id())
  if ok then print(net.get("public/hello.txt")) else print("failed: " .. err) end
end
```

## Known issues

* `os.millis()` counts from 2000, while `os.time()` and `fs.stat().mtime`
  count from 1970.
* `os.date()` is local time; `fs.stat().date` is UTC. They differ outside
  the UTC time zone.
* Hand edits to `/etc/caps` are ignored until `caps grant`/`caps revoke`
  (or an "always" answer) reloads it.
* `sys.hostname()` reads `$HOSTNAME`; `/etc/hostname` (which says
  `ScratchOS`) is never read.

See also: [getting-started.md](getting-started.md) (running programs, the
shell), [stdlib.md](stdlib.md) (`print`, `pcall`, `error`),
[terminal.md](terminal.md) (`term`), [graphics.md](graphics.md) (`gui`
capabilities), [libraries.md](libraries.md) (`require`),
[internals.md](internals.md) (scheduling and memory),
[NETWORK.md](../NETWORK.md).
