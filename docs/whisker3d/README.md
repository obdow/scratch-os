# Whisker 3D

Whisker 3D is a 3D game engine that runs inside Scratch. It is a stand-alone
project, `Whisker3D.sb3`, made from the same kernel as ScratchOS and the
Whisker IDE. It has a scene editor and a code editor, and you write the games
in [Whisker](../whisker/README.md), the Lua-like language of ScratchOS.
Finished games are exported as a `.txt` file and played in one of two player
projects:

| File | Stage | For |
|---|---|---|
| `Whisker3D.sb3` | 1280 x 720 | The engine: make, edit, test and export games. Open it in [TurboWarp](https://turbowarp.org); the project sets its 1280x720 stage, 60 FPS and no fencing through TurboWarp's project settings. |
| `Whisker3D-Player-720p.sb3` | 1280 x 720 | Plays games made at 1280x720, in TurboWarp. |
| `Whisker3D-Player-480x360.sb3` | 480 x 360 | Plays games made at 480x360, in TurboWarp or on scratch.mit.edu (no compiler, fenced pen, 30 fps safe). |

```lua
-- scripts/coin.wsk: a coin spins, and is collected when the player touches it
function update(self, dt)
  self:rotate(0, 150 * dt, 0)
  if self:touching("#player") then
    sound.play("coin")
    w3d.set("coins", w3d.get("coins", 0) + 1)
    w3d.destroy(self)
  end
end
```

## What it has

- **A renderer** of flat-shaded triangles: painter's-order depth sorting,
  back-face culling, near-plane clipping, a sun, up to 8 point lights, fog, a
  gradient sky and transparency. Triangles are filled with the incircle
  method from `Triangle Filler.sb3`. Its quality is adjustable per project
  (triangle budget, draw distance, fill resolution).
- **A scene editor**: orbit, pan and zoom the view; select objects by
  clicking; move, rotate and scale them with snapping; an inspector for every
  setting; undo; built-in shapes, `.obj` models, lights and cameras.
- **Scripts on objects**, like Unity: a script defines `start(self)`,
  `update(self, dt)`, `on_collide(self, other)` and `on_message(self, msg,
  data)`, and every object that uses the script runs it.
- **Physics**: static, dynamic and kinematic bodies; box and sphere
  colliders; triggers; bounce; gravity; "grounded"; raycasts.
- **Input**: keys, edges (pressed / released), axes, the mouse and clicks.
- **Sound**: 18 built-in effects, and music notes and drums through the
  Scratch Music extension on four voices.
- **A HUD**: text, rectangles (optionally translucent) and lines on top of
  the 3D view.
- **Projects** as folders, exported and imported as one `.txt` file through
  a Scratch list.
- **Three examples**: Coin Run (a platformer with two levels), Space Flyer
  (a shooter with music) and Shape Garden (every shape, a model, lights,
  glass and mouse picking, at 480x360).

## Chapters

| Chapter | What it covers |
|---|---|
| [Getting started](getting-started.md) | Opening the engine, the start screen, making a project, the editor, playing, a first script |
| [The editor](editor.md) | Every menu, tool, key and mouse action; the inspector; project and scene settings |
| [Scripting](scripting.md) | How scripts run, the object functions, messages, shared values, scenes, modules, errors |
| [Library reference](reference.md) | Every function in `w3d`, `input` and `sound` |
| [Scenes and projects](scenes.md) | The project folder, `game.w3d`, the scene file format, built-in shapes, `.obj` models |
| [Physics](physics.md) | Bodies, colliders, triggers, the simulation step, raycasts |
| [Graphics](graphics.md) | Coordinates, the camera, lighting, fog, transparency, the HUD, quality and performance |
| [Sound](sound.md) | Effects, music voices, the list of sounds |
| [Publishing](publishing.md) | Exporting to `.txt`, the two players, importing, the bundle format, scratch.mit.edu |
| [Internals](internals.md) | How the engine is built: the frame loop, the renderer, the players, and what was added to Whisker and the toolchain |

## Building

```
python3 build.py --w3d w3d          # Whisker3D.sb3
python3 build.py --w3d player720    # Whisker3D-Player-720p.sb3
python3 build.py --w3d player480    # Whisker3D-Player-480x360.sb3
```

The sources are in `src/w3d/`, the engine's files (templates, examples) in
`w3d/rootfs/`, and the tests in `test/w3d-*.js` (see [Internals](internals.md#tests)).
