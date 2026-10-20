# Scenes and projects

## The project folder

A project is a folder in `/projects` in the engine's file system:

```
/projects/My Game/
  game.w3d              project settings
  scenes/main.scene     scenes (text files)
  scripts/player.wsk    scripts (Whisker)
  models/tree.obj       models (and their .mtl files)
  .build/               compiled scripts, made by File > Export (do not edit)
```

Everything is plain text, and the editor writes the same files you could
write by hand. Files can be opened in the code view and edited there; a
scene edited as text is reloaded when you go back to the scene editor or
press Play.

## game.w3d

```
-- Whisker 3D project settings
name My Game
resolution 1280x720
scene scenes/main.scene
budget 600
distance 120
fill 2
```

| Setting | Meaning |
|---|---|
| `name` | The game's name, shown by the players |
| `resolution` | `1280x720` (TurboWarp) or `480x360` (Scratch) |
| `scene` | The scene the game starts in |
| `budget` | The most triangles drawn in a frame (at least 20); the nearest are kept |
| `distance` | How far the camera sees, in units (at least 5) |
| `fill` | Fill coarseness: the pen size of the finest strokes that fill a triangle (at least 1). Higher is faster and blockier. |

[Graphics](graphics.md#quality) explains the quality settings.

## The scene file

A scene is a list of settings, one per line. `--` starts a comment, and
words with spaces are written in double quotes. The world settings come
first, then each object starts with an `object` line and is followed by its
settings, indented by convention.

```
-- Whisker 3D scene
scene "Main"
sky #5d86e6 #d9ebff
ambient 0.35
sun -0.4 -1 0.6 0.8
fog 25 60 #d9ebff
gravity -22

object "Ground" mesh
  mesh plane
  scale 30 1 30
  color #5aa864
  body static
  collider box

object "Player" mesh
  mesh capsule
  pos 0 1 0
  scale 1 1.6 1
  color #ff8a3d
  tag player
  script scripts/player.wsk
  body dynamic
  collider box

object "Lamp" light
  pos 0 3 0
  range 8
  power 1

object "Camera" camera
  pos 0 6 -10
  rot 25 0 0
  fov 60
  script scripts/camera.wsk
```

**World settings**

| Line | Meaning | Default |
|---|---|---|
| `scene NAME` | The scene's name | `Scene` |
| `sky TOP [HORIZON]` | Sky colours, top and at the horizon | `#7580ee #ddeeff` |
| `ambient A` | Light everywhere, 0..1 | `0.35` |
| `sun X Y Z [STRENGTH]` | The direction sunlight travels, and its strength | `-0.4 -1 0.5 0.8` |
| `fog NEAR FAR [COLOUR]`, `fog off` | Fog | off (`30 80 #ddeeff`) |
| `gravity G` | The y acceleration of dynamic bodies | `-20` |

**Object lines**

| Line | Meaning |
|---|---|
| `object NAME [KIND]` | Starts an object. `KIND` is `mesh` (default), `light`, `camera` or `empty` (an invisible point, for scripts and markers). |
| `mesh SHAPE` | A built-in shape or a model path |
| `pos X Y Z` | Position |
| `rot X Y Z` | Rotation in degrees (pitch, yaw, roll) |
| `scale X [Y Z]` | Scale; one number scales evenly |
| `color #RRGGBB` | Colour |
| `alpha A` | Transparency, 0..100 |
| `hidden` | Not drawn |
| `unlit` | Not lit: drawn in its own colour |
| `twosided` | Back faces are drawn too |
| `tag WORD` | Its tag |
| `script PATH` | The script it runs (project-relative) |
| `body KIND` | `static`, `dynamic` or `kinematic` |
| `collider KIND` | `box` or `sphere` |
| `trigger` | The collider reports touches but does not block |
| `bounce B` | 0 (no bounce) to 1 (full bounce) |
| `range R`, `power P` | A light's range (default 8) and strength (default 1) |
| `fov DEG` | A camera's view angle (default 60) |

An unknown word is an error with its line number. Objects spawned while the
game runs are never written to the scene.

## Built-in shapes

Every shape fits in a 1 x 1 x 1 box around the object's position, except the
plane, which is flat.

| Name | Shape | Faces |
|---|---|---|
| `cube` | A cube | 12 |
| `plane` | A flat square at y = 0, facing up, made of 8 x 8 tiles (so it sorts well against objects on it, and fog and lights vary across it) | 128 |
| `quad` | An upright square facing -z, for signs and billboards | 2 |
| `sphere` | A sphere | 168 |
| `cylinder` | A cylinder, upright | 64 |
| `cone` | A cone, point up | 32 |
| `pyramid` | A square pyramid | 6 |
| `wedge` | A ramp: full height at +z, zero at -z | 8 |
| `torus` | A ring around y | 256 |
| `capsule` | A pill: 1 tall, 0.5 wide | 192 |

Scale them to make other shapes: a `cube` scaled `10 0.5 2` is a platform,
and a `cylinder` scaled `0.7 0.12 0.7` and turned 90 degrees is a coin.

## .obj models

Whisker 3D reads Wavefront `.obj` files, the format most 3D tools export:

| Line | Read as |
|---|---|
| `v x y z` | A vertex |
| `v x y z r g b` | A vertex with a colour (0..1); faces take the colour of their first corner |
| `f a b c ...` | A face with 3 or more corners: `7`, `7/2`, `7/2/3` or `7//3`. Negative numbers count back from the last vertex. Faces with more corners are split into triangles. |
| `usemtl NAME` | The colour of the faces that follow: a name from the `.mtl` file (its `Kd` line), or a colour written as `#rrggbb` |
| `mtllib FILE` | The `.mtl` file with the colours, next to the model |

Other lines (`vt`, `vn`, `o`, `g`, `s`, ...) are ignored. Faces are flat
shaded, in one colour each. `.obj` files are right-handed, so Whisker 3D
mirrors z when it reads them, and faces keep the usual counter-clockwise
winding of `.obj`. A model drawn inside out was exported with the opposite
winding; turn on **Two-sided** for it, or flip its normals in the 3D tool.

Faces without a material use the object's colour. A model is loaded once and
shared by every object using it, and it is reloaded when its file changes.

Keep models small: every triangle costs time each frame. A few hundred
triangles per model is a good size. In Blender, use **Decimate** to reduce a
model, and export with "Triangulated mesh" and "Write materials" on.

Models are imported with File > Import model (see [The editor](editor.md#importing-a-model)).
