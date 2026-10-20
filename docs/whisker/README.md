# The Whisker manual

Whisker is the programming language of ScratchOS. It looks like Lua: small
and dynamic, with tables as its one data structure. Every program in `/bin`
is written in it, including the shell tools, Finder, Paint and the Browser.
The kernel compiles Whisker to bytecode and runs it on a preemptive virtual
machine inside the Scratch project. This manual describes all of it.

```lua
-- hello.wsk
local name = arg[1] or "world"
print("Hello, " .. name .. "!")
for i = 1, 3 do
  print(i, string.rep("*", i))
end
```

```
user@scratchos:~$ run hello.wsk Whisker
Hello, Whisker!
1       *
2       **
3       ***
```

## Chapters

| Chapter | What it covers |
|---|---|
| [Getting started](getting-started.md) | Running programs, the interactive interpreter, `edit`, input, arguments, exit codes, a first game, saving your work |
| [The language](language.md) | Syntax, values and types, variables and scope, operators, statements, functions, tables, errors, limits, and every difference from Lua |
| [Standard library](stdlib.md) | Base functions (`print`, `pcall`, `tostring`, ...), `string`, `math`, `table` |
| [System libraries](system.md) | `io`, `os`, `fs`, `proc`, `sys`, `net`; arguments, environment, pipes and exit codes; permissions |
| [Terminal programs](terminal.md) | `term`, colours and ANSI escapes, keys, raw mode, the CP437 character set, full-screen text programs |
| [Graphics and windows](graphics.md) | `gui` windows and events, `gfx` drawing, colours, `image` pictures (`.simg`), and a worked example |
| [Modules and libraries](libraries.md) | `require`, `load`, writing modules, and the bundled `yarn` and `sort` libraries |
| [The Whisker IDE](ide.md) | The editor in ScratchOS and the stand-alone `WhiskerIDE.sb3`: running, errors, menus, shortcuts |
| [Internals](internals.md) | The compiler, bytecode, VM, scheduling, memory, limits and performance |
| [Whisker 3D](whisker3d.md) | The 3D game engine: scripts on objects, and the `w3d`, `input` and `sound` libraries (full manual in [docs/whisker3d](../whisker3d/README.md)) |

New to programming in Whisker? Read [Getting started](getting-started.md),
then the first half of [The language](language.md). If you already know
Lua, go straight to
[Differences from Lua](language.md#differences-from-lua).

## Quick reference

[../WHISKER.md](../WHISKER.md) is a two-page summary of the language and
library. Inside ScratchOS, `man whisker` and `man lib` have short versions,
and the IDE has the same reference under **Help**.

## About the examples

Examples followed by an `output` block are tested: `test/doctest.js` runs
each one in a real ScratchOS and checks that it prints exactly what is
shown. Run it from the `test` directory:

```
cd test && npm install
node doctest.js                         # every chapter
node doctest.js ../docs/whisker/stdlib.md
```

Examples without an output block need a window, a key press or the network.
They were checked by hand on the desktop.

## Related documents

* [YARN.md](../YARN.md): the Yarn web page language, used by the Browser.
* [SIMG.md](../SIMG.md): the `.simg` picture format.
* [NETWORK.md](../NETWORK.md): the ScratchOS network behind `net`.
* [ARCHITECTURE.md](../ARCHITECTURE.md): how the whole system is built.
* [SBS.md](../SBS.md): the language the kernel itself is written in.
* [whisker3d/](../whisker3d/README.md): the Whisker 3D game engine manual.
