# Internals

Whisker 3D is written in SBS ([docs/SBS.md](../SBS.md)) and compiled by
`build.py` into ordinary Scratch blocks, like ScratchOS and the Whisker IDE.
The engine is the IDE's kernel (file system, processes, the Whisker compiler
and VM) with a renderer, physics, sound, a game runtime and a scene editor
added. The players are the same game runtime without the compiler, the
editor, the window manager or networking.

## Source files

| File | What it does |
|---|---|
| `src/w3d/main.sbs` | The engine's entry point: the IDE plus the Whisker 3D modules |
| `src/w3d/player.sbs` | The players' entry point: loads the list `game` into `/game` and plays it; help and error screens |
| `src/w3d/mesh.sbs` | Mesh storage, the built-in shapes, the `.obj` / `.mtl` reader, the model cache |
| `src/w3d/objects.sbs` | Scene objects (`ob_*` lists), the world settings, rotation matrices |
| `src/w3d/r3d.sbs` | The renderer: camera, culling, lighting, clipping, depth buckets, the triangle filler, sky, HUD rectangles, editor lines and picking |
| `src/w3d/phys.sbs` | Physics and raycasts |
| `src/w3d/project.sbs` | `game.w3d`, scene files, bundles (export / import) |
| `src/w3d/game.sbs` | The game runtime: starting scripts, the frame loop, the HUD queue, scene changes |
| `src/w3d/natives3d.sbs` | The Whisker libraries `w3d`, `input` and `sound` |
| `src/w3d/sound.sbs` | The sound queue and the Sound sprite |
| `src/w3d/export.sbs` | Compiling a project's scripts and modules for the players |
| `src/w3d/editor.sbs` | The start screen and the scene editor, as hooks into the IDE |
| `src/wcore.sbs` | Shared by the compiler and the VM: opcodes, the native name table, compiled-code text (WBC) |
| `src/shell_lite.sbs` | The few shell helpers the kernel needs, for builds without the shell |
| `src/w3d_stub.sbs` | `w3d`, `input` and `sound` outside Whisker 3D: each raises "only available in Whisker 3D" |
| `w3d/rootfs/` | The engine's files: `templates/` (Starter, Empty), `examples/` and `docs/` |
| `w3d/player_rootfs/` | The players' files |
| `tools/w3d_sounds.py` | Synthesizes the sound effects as WAV files at build time |
| `tools/w3d_bundle.py` | Packs and unpacks bundles outside Scratch |

## The frame loop

`game_tick` runs one frame:

1. **Input**: the keys that scripts asked about and the mouse button are
   sampled, so that `pressed` / `released` / `clicked` are edges between two
   frames.
2. **Scripts**: every script process waiting in `w3d.frame()` is released,
   and the scheduler runs the processes until they are all waiting again, or
   for at most 40 ms (a busy script carries on in the next frame).
3. **Physics**: `phys_step(dt)`.
4. **Scene change**: a `w3d.load` takes effect here (and `w3d.quit` just
   before physics).
5. **Render**: `r3_render` draws the sky and the scene.
6. **HUD**: the queue that scripts filled with `w3d.text` / `rect` / `line` is
   drawn and emptied.

Each distinct script is one Whisker process, made by compiling the script
with a loop appended (`GAME_FOOTER` in `game.sbs`). The loop calls
`w3d.frame()`, which blocks the process until the next frame, and then calls
`start`, `on_message`, `on_collide` and `update` for each object in
`w3d.instances()`. So the scripts are ordinary Whisker programs, scheduled
preemptively like any other, and a script stuck in a long loop slows the
game down but does not freeze the engine.

Object tables are made once per object and *pinned*, so the garbage
collector never frees them and every script shares them. Their method fields
hold native function values (`TNAT`), so `obj:pos()` calls the native
`w3d.pos` with `obj` as its first argument.

## The renderer

Coordinates are left-handed (x right, y up, z forward). A rotation is
`Ry(yaw) * Rx(pitch) * Rz(roll)`, and its columns are the object's right, up
and forward axes. Built-in faces wind clockwise when seen from the front, and
a face's normal is `cross(b - a, c - a)`. `.obj` files are mirrored in z as
they load, which turns their counter-clockwise faces clockwise.

For each object, the renderer:

1. culls it against the view with its bounding sphere and the draw distance;
2. moves its vertices into camera space (one combined matrix per object);
3. for each face, skips it if it faces away (unless two-sided), computes its
   flat brightness (ambient + sun + up to 8 point lights with quadratic
   falloff) and fog, clips it against the near plane (Sutherland-Hodgman),
   projects it, and clips it to the viewport in 2D;
4. puts each resulting triangle in one of 1024 depth buckets, keyed by the
   square root of the depth of its farthest corner (more buckets near the
   camera, where order matters most).

Then the buckets are drawn from far to near. If there are more triangles
than the budget, the farthest are dropped. Each triangle is filled by
`tri_fill`, the incircle method of `Triangle Filler.sb3`: the outline with a
thin pen, a dot as wide as the incircle, then shrinking copies of the
triangle traced with ever thinner pens. The outline pen is one pixel wider
than the finest fill stroke, so neighbouring faces overlap and no sky shows
between them.

Transparent faces set the pen's transparency. Translucent HUD rectangles are
stamped from power-of-two-sized rectangle costumes with the ghost effect,
because pen strokes that overlap would make stripes.

In the 480 x 360 player, sprite fencing is on (as on scratch.mit.edu), which
would stop the pen sprite at the stage edges. While drawing, the sprite wears
a blank costume ("pen"), which fencing lets go anywhere.

## The players

The engine's `project.json` is about 10 MB, well over scratch.mit.edu's
5 MB limit, and the Whisker compiler is a large part of it. So
the players leave out the compiler, the shell, the window manager and the
networking. These are switched off by build constants that the SBS compiler
folds away (`if (HAS_COMPILER == 1) { ... }` produces no blocks when the
constant is 0):

| Constant | Engine | Players |
|---|---|---|
| `HAS_COMPILER` | 1 | 0 |
| `HAS_WM` | 1 | 0 |
| `HAS_NET` | 1 | 0 |
| `W3D_ENGINE` | 1 | 0 |
| `W3D_PLAYER` | 0 | 1 |

`build.py` also shortens the variable ids in `project.json`
(`compact_ids`), because each block repeats the ids it uses. The 480 x 360
player's `project.json` is about 4.4 MB.

Without a compiler, a player runs code compiled by the engine. Exporting
compiles each object script with its loop into `.build/<script path>`, and
each module the script requires into `.build/req/<n>`. A module's code
refers to globals by number, in the order the program first names them, so
modules are compiled as they will run: depth first, in the order of the
`require` calls, with the names the requirer already has. The compiled code
is stored as WBC text:

```
WBC 1
module <name>
base <global names the code was compiled against>
names <global names after compiling>
caps <capabilities>
code <n>
<one instruction word per line>
```

`vm_load` accepts WBC as well as source, and `require` in a player looks up
the precompiled module by name (`wbc_find_module`).

## What was added to Whisker

For Whisker 3D, these were added to the shared kernel and documented here
and in the [Whisker manual](../whisker/whisker3d.md):

- **Libraries** `w3d`, `input` and `sound` ([reference](reference.md)). Their
  natives are at the end of the native table (`tools/natives.py`), so the
  ids of the older natives did not change. In ScratchOS and the Whisker IDE
  they are stubs that raise an error.
- **Precompiled code (WBC)**: `wbc_text` / `wbc_parse` in `src/wcore.sbs`,
  loading it in `vm_load`, and module lookup by name in `require` when there
  is no compiler.
- **`src/wcore.sbs`**: the opcodes, the native name table and the error and
  capability helpers moved out of the compiler, so that a kernel without the
  compiler can still run code.
- **Build constants** (`HAS_WM`, `HAS_NET`, `HAS_COMPILER`) around the parts
  of the kernel a player does not need.

And to the toolchain ([docs/SBS.md](../SBS.md)):

- `sounds "group"` in sprites, and the `pen_alpha`, `sound_*` and `music_*`
  built-ins (the Music extension is added to a project that uses it).
- Constant folding of comparisons and `&&` / `||`, and of `if` with a
  constant condition.
- `build.py --w3d {w3d,player720,player480}`, `compact_ids`, and list
  monitors for the `game`, `w3d_export` and `w3d_import` lists.

## Tests

The tests run the built `.sb3` files headlessly in TurboWarp (Playwright),
like the ScratchOS tests:

| Test | Checks |
|---|---|
| `node test/w3d-e2e.js` | Makes a project in the engine through its UI, edits the scene, plays it, exports it, and plays the export in both players (the 480 x 360 one as on scratch.mit.edu: no compiler, fencing, 30 fps) |
| `node test/w3d-api.js [--vanilla]` | The library checks in `test/w3d/apitest` (objects, messages, physics, raycasts, input, HUD, sound queue), exported and run in a player |
| `node test/w3d-examples.js` | Compiles each example with the engine and plays it in the player for its resolution |
| `node test/w3d-play.js PLAYER GAME_DIR` | Plays a game folder and prints its log |

The Whisker manual's doctests (`node test/doctest.js`) and the ScratchOS
regression test (`node test/regress.js`) cover the shared kernel.
