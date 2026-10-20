# Scripting

Games are written in [Whisker](../whisker/language.md). A script is a
`.wsk` file, usually in `scripts/`, that an object names in its **Script**
setting. Any number of objects can use the same script, and each of them
runs it as its own `self`.

## The script functions

A script defines any of these global functions. All of them are optional.

| Function | Called |
|---|---|
| `start(self)` | Once for each object, on the first frame it exists, before its first `update`. Objects made later with `w3d.spawn` get `start` on their first frame. |
| `update(self, dt)` | Every frame, for each object. `dt` is the time since the last frame in seconds (never 0). |
| `on_collide(self, other)` | Every frame, once for each object `self` is touching (see [Physics](physics.md)). It keeps being called while they touch. |
| `on_message(self, msg, data)` | For each message sent to the object with `w3d.send` or `w3d.broadcast`, before `update`. |

Within a frame, `start` calls come first, then messages, collisions, and
updates, in that order. Objects are visited in scene order.

```lua
-- scripts/door.wsk: opens when it gets the message "open"
local opening = {}

function on_message(self, msg, data)
  if msg == "open" then opening[self.id] = true end
end

function update(self, dt)
  if opening[self.id] then
    local x, y, z = self:pos()
    if y < 4 then self:move(0, 2 * dt, 0) end
  end
end
```

### How it runs

The engine runs each distinct script as one Whisker process. The top of the
file runs once, when the scene starts, so `local` variables there are shared
by every object using the script (store per-object values in a table keyed
by `self.id`, as above, or as fields of `self`). After the top of the file,
a loop added by the engine waits for each frame and calls the functions:

```lua
-- (added after every script; simplified)
while true do
  local dt = w3d.frame()            -- wait for the next frame
  if dt == nil then break end       -- the game or scene ended
  for _, o in ipairs(w3d.instances()) do
    -- start(o) the first time, then on_message, on_collide, update
  end
end
```

Each frame goes:

1. **Input**: keys and the mouse are read.
2. **Scripts**: every script runs its frame, until all of them are waiting in
   `w3d.frame()` again (or 40 ms have passed; a script that is still busy
   carries on in the next frame).
3. **Physics**: bodies move and collide.
4. **Render**: the 3D view is drawn.
5. **HUD**: the text, rectangles and lines that scripts asked for this frame
   are drawn on top.

A script can also write its own loop with `w3d.frame()` instead of defining
`update`. This is useful for sequences:

```lua
-- scripts/intro.wsk: a camera fly-in, then normal play
local cam = w3d.camera()
for i = 1, 120 do
  cam:setpos(0, 10 - i / 20, -20 + i / 10)
  cam:lookat(0, 0, 0)
  w3d.frame()
end
w3d.broadcast("go")
```

## Objects

Objects are tables. `self` and the results of `w3d.find`, `w3d.objects`,
`w3d.spawn`, `w3d.camera` and `w3d.raycast` are these tables:

```lua
self.id          -- a number, unique while the scene runs
self.name        -- the name from the scene ("Player")
self:pos()       -- methods: the same as w3d.pos(self)
```

The methods are the `w3d` functions of the same name, so `self:move(1, 0, 0)`
is `w3d.move(self, 1, 0, 0)`. Every function that takes an object also
accepts its id. There is one table per object, shared by every script, so a
field one script sets is seen by the others:

```lua
-- in enemy.wsk
function on_collide(self, other)
  if other.name == "Player" then
    other.health = (other.health or 3) - 1
  end
end
```

The methods are `pos setpos move moverel rot setrot rotate scale setscale
color setcolor alpha setalpha visible show tag settag forward right lookat
distance setmesh mesh velocity setvelocity push grounded touching body
setbody destroy alive contacts send light`. The [reference](reference.md)
describes each one.

A destroyed object's table stays valid as a value, but the methods raise an
error if they are called on it. Use `obj:alive()` (or `w3d.alive(obj)`)
when an object may have been destroyed.

## Finding objects

```lua
local player = w3d.find("Player")       -- by name: the first, or nil
local boss   = w3d.find("#boss")        -- by tag
for _, c in ipairs(w3d.objects("#coin")) do c:setcolor("#ffffff") end
local all = w3d.objects()               -- every live object
```

## Spawning and destroying

```lua
-- a template object can be hidden in the scene and copied
local b = w3d.spawn("Bullet", x, y, z)  -- copies the object "Bullet", script included
b:show()
b:setvelocity(fx * 30, fy * 30, fz * 30)

local rock = w3d.spawn("sphere", 0, 5, 0)   -- a new object with a built-in shape
rock:setbody("dynamic", "sphere")
local tree = w3d.spawn("models/tree.obj")   -- or a model

w3d.destroy(b)
```

Spawned objects are not saved into the scene.

## Messages

```lua
w3d.send(door, "open")                  -- to one object
w3d.send(door, "open", 2.5)             -- with a value
w3d.broadcast("game over")              -- to every object that has a script
w3d.broadcast("score", 100)
```

The message and its data can be numbers, strings, booleans, nil or objects.
They arrive in the receiving object's `on_message` in the same frame, if its
script has not run yet, or else in the next one.

## Shared values

`w3d.set(key, value)` and `w3d.get(key [, default])` keep values that every
script can read. They last for the whole game, across scene changes, so they
suit scores, lives and the level number:

```lua
w3d.set("coins", w3d.get("coins", 0) + 1)
```

Values can be numbers, strings, booleans, nil or objects. Script variables
do not survive a scene change, because the scripts are started again.

## Scenes

```lua
w3d.load("level2")          -- scenes/level2.scene, at the end of this frame
local name, path = w3d.scene()
w3d.quit()                  -- end the game
```

Loading a scene stops every script, replaces all the objects, and starts the
scripts of the new scene. Shared values are kept.

## Modules

`require("name")` loads `/lib/name.wsk`, or `name.wsk` next to the script, as
in [Whisker](../whisker/libraries.md):

```lua
-- scripts/util.wsk
local M = {}
function M.clamp(v, a, b) return math.max(a, math.min(b, v)) end
return M
```

```lua
-- scripts/player.wsk
local util = require("util")
```

Exporting compiles the modules into the game too. `load(src)` works in the
engine, but not in the players, which have no compiler: there it returns
nil and an error message.

## What scripts can use

Scripts have the whole Whisker language and standard library (`string`,
`math`, `table`, `pcall`, `error`, ...), plus `w3d`, `input` and `sound`.
`print` writes to the output panel in the engine, and to a log in the players
(the log is shown if the game stops with an error). `io` and `fs` work on the
game's own files. The ScratchOS libraries for windows, the terminal and the
network (`gui`, `term`, `net`) do nothing useful in a game.

In ScratchOS and the Whisker IDE, the `w3d`, `input` and `sound` libraries
exist, but calling them raises an error such as "w3d.find is only available
in Whisker 3D".

## Errors

A compile error or a runtime error stops the game. In the engine, the error
appears in the output panel and the script opens at the line; in a player,
an error screen shows it with the end of the log. Errors name the script and
line (`player.wsk:12: attempt to index a nil value`).

Common mistakes:

- Calling a method with `.` instead of `:` (`self.pos()` instead of
  `self:pos()`): the error says the argument is not an object.
- Using an object after `w3d.destroy`: check `obj:alive()` first.
- Forgetting a body: `setvelocity` and `push` only move `dynamic` bodies.
  Move other objects with `setpos` or `move`.
