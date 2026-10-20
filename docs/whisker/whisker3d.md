# Whisker 3D

[Whisker 3D](../whisker3d/README.md) is a 3D game engine for Scratch and
TurboWarp whose games are written in Whisker. It is a separate project,
`Whisker3D.sb3`, built from the same kernel as ScratchOS and the Whisker IDE,
with a scene editor, a renderer, physics and sound added. This chapter
summarises what it adds to Whisker. The [Whisker 3D manual](../whisker3d/README.md)
covers everything in full.

## Scripts on objects

A Whisker 3D script is a Whisker program attached to objects in a scene. It
defines functions that the engine calls:

```lua
-- scripts/spinner.wsk
local SPEED = 90                    -- shared by every object using this script

function start(self)                -- once per object
  self.turns = 0
end

function update(self, dt)           -- every frame; dt in seconds
  self:rotate(0, SPEED * dt, 0)
end

function on_collide(self, other)    -- each frame, for each object it touches
  if other.name == "Player" then w3d.send(other, "spun") end
end

function on_message(self, msg, data) end   -- from w3d.send / w3d.broadcast
```

Each script runs as one Whisker process. Its top level runs once, then a loop
added by the engine waits for each frame with `w3d.frame()` and calls the
functions above for every object that uses the script. See
[Scripting](../whisker3d/scripting.md).

## The libraries

| Library | What it has |
|---|---|
| `w3d` | Objects (`find`, `objects`, `spawn`, `destroy`), transforms (`pos`, `setpos`, `move`, `rotate`, `lookat`, `forward`, ...), looks (`setcolor`, `setalpha`, `show`, `setmesh`), physics (`setvelocity`, `push`, `grounded`, `touching`, `contacts`, `setbody`, `raycast`, `gravity`), the camera and lights (`camera`, `fov`, `sky`, `fog`, `ambient`, `sun`, `light`), the HUD (`text`, `rect`, `line`, `project`, `screenray`, `screen`), messages and shared values (`send`, `broadcast`, `set`, `get`), scenes (`load`, `scene`, `quit`) and time (`time`, `fps`, `frame`) |
| `input` | `key`, `pressed`, `released`, `axis`, `mouse`, `mousedown`, `clicked` |
| `sound` | `play`, `stop`, `list` (built-in effects); `note`, `drum`, `rest`, `tempo`, `volume` (music, through the Scratch Music extension) |

Objects are tables whose method fields are the `w3d` functions, so
`self:pos()` is `w3d.pos(self)`. Each object has one table, shared by every
script. The [library reference](../whisker3d/reference.md) describes every
function.

These libraries exist in ScratchOS and the Whisker IDE too, so programs that
mention them still compile there, but every call raises an error such as
`w3d.find is only available in Whisker 3D`.

## Precompiled programs

The Whisker 3D players have no compiler, so the engine exports games with
their scripts already compiled to bytecode, stored as text (WBC). The
kernel's loader (`vm_load`) accepts this text as well as source, and in a
kernel without a compiler, `require` finds precompiled modules by name. This
is described in [Whisker 3D internals](../whisker3d/internals.md#the-players).
Nothing changes for ScratchOS programs, which are still compiled from
source when they run.
