# Graphics

## Coordinates

Whisker 3D is left-handed with y up: **x** points right, **y** up, and **z**
forward, away from a camera that has no rotation. One unit is the size of a
built-in shape, so think of it as a metre.

Rotations are in degrees: yaw around y, then pitch around x, then roll
around z. Positive yaw turns an object's front from +z towards +x (to the
right, seen from above), and positive pitch tilts its front down. The
camera works the same way: rotation `25 0 0` looks forward and 25 degrees
down.

`obj:forward()` and `obj:right()` give an object's axes in world space, and
`obj:moverel(x, y, z)` moves along them.

## The camera

The scene's camera object is `w3d.camera()`. Move and turn it like any
object; `w3d.fov` sets its vertical view angle. A camera that follows the
player:

```lua
-- scripts/camera.wsk (on the camera)
local player
local DIST, HEIGHT = 9, 4

function start(self)
  player = w3d.find("Player")
end

function update(self, dt)
  if not player or not player:alive() then return end
  local px, py, pz = player:pos()
  local x, y, z = self:pos()
  -- ease towards a point behind and above the player
  local k = math.min(1, 5 * dt)
  self:setpos(x + (px - x) * k, y + (py + HEIGHT - y) * k, z + (pz - DIST - z) * k)
  self:lookat(px, py + 1, pz)
end
```

The view is cut at 0.1 units in front of the camera and at the project's draw
distance.

## Lighting and colour

Faces are flat: each triangle has one colour. A face's brightness is

```
ambient + sun strength * (how directly it faces the sun)
        + for each point light in range: power * (1 - distance / range)^2 * (how directly it faces the light)
```

and the colour is multiplied by it, so values above 1 brighten towards
white. Up to 8 visible point lights count, and they are white.

| Setting | Where | Default |
|---|---|---|
| Ambient | `ambient` in the scene, `w3d.ambient(a)` | 0.35 |
| Sun | `sun x y z strength`, `w3d.sun(x, y, z, s)`: the direction the light travels | `-0.4 -1 0.5`, 0.8 |
| Point lights | `light` objects: `range`, `power`; `obj:light(range, power)` | 8, 1 |
| Unlit | `unlit` on an object: its own colour, no light and no fog | off |

Colours with lighting look best in the middle of the range: very dark
colours stay dark, and pure white cannot get brighter.

## Sky and fog

The sky is a vertical gradient from the top colour to the horizon colour,
drawn behind everything: `sky #5d86e6 #d9ebff` or `w3d.sky(top, horizon)`.

Fog fades lit faces towards the fog colour between `near` and `far` units of
depth from the camera. Make the fog colour the same as the sky's horizon
colour, and set the draw distance a little beyond `far`, so that distant
objects fade out instead of popping out of view.

## Transparency

`alpha` (0 solid .. 100 invisible) makes an object see-through, using
Scratch's pen transparency. Transparent faces are sorted with the rest, so
they work best for simple, convex shapes such as panes of glass, water, and
ghosts. Turn on **Two-sided** for a flat pane so that it can be seen from
both sides.

## How faces are drawn

Each frame the renderer:

1. fills the sky;
2. skips objects whose bounding sphere is outside the view;
3. moves the vertices into camera space, and skips faces that point away
   (back-face culling) unless the object is two-sided;
4. lights and fogs each face;
5. clips faces to the near plane, projects them, and clips them to the
   screen;
6. sorts them into 1024 depth buckets by their farthest corner, and draws
   them from far to near (the painter's algorithm);
7. fills each triangle with the incircle method of `Triangle Filler.sb3`:
   the outline with a thin pen, then a pen dot as wide as the incircle, then
   ever smaller copies of the triangle shrunk towards its corners, each
   traced with a pen as wide as the gap it covers, until the gap is smaller
   than the fill coarseness.

The painter's algorithm is fast, but it is not exact: a large face can be
drawn over a smaller one that is in front of it. Split big faces (the
built-in `plane` is already made of 8 x 8 tiles), and avoid long thin
triangles that cross other objects.

## The HUD

`w3d.text`, `w3d.rect` and `w3d.line` draw on top of the 3D view for one
frame, in game pixels from the top-left corner. Text uses the same
monospaced font as the Whisker IDE and ScratchOS: size 1 is 8 x 16 pixels
per character, and size 2 is 16 x 32. Text colours are rounded to the
nearest of the font's 256 colours. A rectangle with transparency is a good
backing for text:

```lua
function update(self, dt)
  local w, h = w3d.screen()
  w3d.rect(12, 12, 220, 34, "#000000", 55)
  w3d.text(24, 21, "Score: " .. w3d.get("score", 0), "#ffd54f")
  -- a label over an object
  local sx, sy = w3d.project(self:pos())
  if sx then w3d.text(sx - 16, sy - 40, "Ally", "#ffffff") end
end
```

A 480x360 game played in the engine is scaled up by 2 and letterboxed; the
HUD scales with it.

## Quality

Each project has three quality settings, in the project settings (click
**Project** in the object list) and in `game.w3d`:

| Setting | Default | Lower | Higher |
|---|---|---|---|
| Triangle budget (`budget`) | 600 | Faster: the farthest faces are left out first | More detail in big scenes |
| Draw distance (`distance`) | 120 | Faster: less to draw | You see farther |
| Fill coarseness (`fill`) | 2 | Sharper edges, slower | Faster, rougher edges |

Speed depends mostly on how many triangles are drawn and how large they are
on the screen. When you stop a game, the output panel shows how many
triangles the last frame drew and the frame rate. Some guidelines:

- Keep scenes to a few hundred visible triangles. A cube is 12, a sphere 168,
  and the ground plane 128.
- Use fog and a shorter draw distance in large outdoor scenes.
- Use the simplest shape that works: a pyramid or a cone for a tree crown, a
  low-polygon model rather than a detailed one.
- In TurboWarp, keep the game at 1280x720 with fill coarseness 2. A 480x360
  game draws a quarter as many pixels and runs faster on slow computers.
- Vanilla Scratch (scratch.mit.edu) runs projects much more slowly than
  TurboWarp. Keep games meant for it small, at 480x360, and raise the fill
  coarseness to 3 if they are slow.
