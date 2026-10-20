# Physics

Physics in Whisker 3D is simple and predictable: bodies are boxes or
spheres that never rotate from collisions, gravity pulls dynamic bodies
down, and overlapping bodies are pushed apart. It suits platformers,
shooters, and anything with things that roll, fall and bounce.

## Bodies and colliders

An object takes part in physics when it has a **collider**. Its **body**
says how it moves.

| Body | Moves | Collides |
|---|---|---|
| `none` | Only by scripts | Like `static`, if it has a collider |
| `static` | Never (scripts can still move it) | Blocks dynamic bodies |
| `dynamic` | By gravity and its velocity | Is pushed out of everything it hits |
| `kinematic` | Only by scripts (`setpos`, `move`) | Pushes dynamic bodies like a static one, and reports touches with other non-dynamic colliders |

| Collider | Shape |
|---|---|
| `none` | No collisions |
| `box` | The axis-aligned box around the object's shape, after rotation and scale |
| `sphere` | A sphere around the object's centre, as wide as the largest scale |

Flat shapes (`plane`, `quad`) are solid for one unit below their face, so
fast objects do not fall through the ground.

A **trigger** collider records touches but does not block. Use triggers for
coins, goals, checkpoints and damage zones:

```lua
-- scripts/goal.wsk (the object has: collider box, trigger)
function on_collide(self, other)
  if other.name == "Player" then w3d.load("level2") end
end
```

**Bounce** (0..1) is how much speed a dynamic body keeps when it hits
something: 0 stops it, and 1 bounces it back at the same speed. Hits
slower than 1.5 units a second never bounce, so bodies come to rest.

## Moving bodies

```lua
self:setvelocity(vx, vy, vz)      -- dynamic bodies only
self:push(0, 8, 0)                -- add to the velocity: a jump
if self:grounded() then ... end   -- standing on something
self:setbody("dynamic", "sphere") -- change the body while playing
w3d.gravity(-9.8)                 -- slower falling
```

`setpos` and `move` move any object, including dynamic ones, but they
teleport it: it is pushed out of whatever it lands in on the next step.

For a character, set the horizontal velocity from the input every frame, and
keep the vertical velocity so that gravity works:

```lua
function update(self, dt)
  local _, vy, _ = self:velocity()
  if self:grounded() and input.pressed("space") then vy = 9 end
  self:setvelocity(input.axis("horizontal") * 6, vy, input.axis("vertical") * 6)
end
```

## Touches

| Function | Answers |
|---|---|
| `self:touching()` | Is it touching anything? |
| `self:touching(other)`, `self:touching("Player")`, `self:touching("#coin")` | Is it touching that object, an object with that name, or with that tag? |
| `self:contacts()` | Which objects is it touching? |
| `on_collide(self, other)` | Called each frame for each object it touches |

Touches are found during the physics step, so they describe the last frame.
Pairs of objects that cannot move (static, kinematic, no body) are only
checked when one of them is a trigger or kinematic, which keeps scenes with
many static objects fast.

## Raycasts

`w3d.raycast` finds the first collider along a line. Triggers are skipped.

```lua
-- shoot along the ship's nose, ignoring the ship itself
local x, y, z = self:pos()
local fx, fy, fz = self:forward()
local hit, dist, hx, hy, hz = w3d.raycast(x, y, z, fx, fy, fz, 80, self)
if hit and hit:tag() == "rock" then
  sound.play("explosion")
  hit:destroy()
end

-- is there ground under me (within 1.1 units)?
local below = w3d.raycast(x, y, z, 0, -1, 0, 1.1, self)
```

With `w3d.screenray` a raycast picks the object under the mouse; see the
[reference](reference.md#screen-and-hud).

## The physics step

Each frame, after the scripts:

1. The step is split into up to 8 substeps, so that no dynamic body moves
   more than 0.2 units at a time; fast bodies do not pass through thin
   walls. A frame longer than 0.1 s is simulated as 0.1 s.
2. In each substep, gravity is added to the velocity of every dynamic body,
   and the body moves.
3. Twice per substep, every dynamic collider that overlaps another collider
   is pushed out the shortest way. Two dynamic bodies share the push. The
   body loses the part of its velocity that goes into the surface, or keeps
   `bounce` of it, reversed. Being pushed up by a surface that is not
   steeper than about 45 degrees counts as standing on it (`grounded`).
4. Every touching pair is recorded for `touching`, `contacts` and
   `on_collide`.

Collisions do not make bodies spin, and boxes stay axis-aligned: a rotated
cube collides as the box around it. Use a `sphere` collider for round
objects, and several boxes for complicated shapes (hidden cubes with
colliders around a model work well).
