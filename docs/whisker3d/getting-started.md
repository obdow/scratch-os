# Getting started

## Open the engine

Open `Whisker3D.sb3` in [TurboWarp](https://turbowarp.org) and click the
green flag. The project sets TurboWarp's stage to 1280x720 at 60 FPS. Use
fullscreen or a large player so that the text is sharp.

The start screen lists **Your projects** on the left and the **Examples** on
the right. Click an example to open a copy of it (the original stays as it
was). Then press **Play** in the title bar, or Ctrl+Enter, to try it.

## Make a project

Click **+ New project**. The form asks three things:

| Field | Choices |
|---|---|
| Name | Click it and type a name. The project is the folder `/projects/<name>`. |
| Screen | **1280 x 720**: for TurboWarp, sharper and faster. **480 x 360**: standard Scratch, so the game can be shared on scratch.mit.edu. |
| Start with | **Starter**: a player you can walk with, a camera that follows it, coins to collect and a HUD. **Empty**: ground, a light and a camera. |

Click **Create**. The project opens in the scene editor.

The screen size decides which player plays the exported game (see
[Publishing](publishing.md)). The editor and the play view always show the
game at its own aspect ratio, so 480x360 games are letterboxed in the
engine's 16:9 stage. You can change the size later in the project settings
(Game > Project settings).

## The editor

```
+--------------------------------------------------------------------------+
| File Edit Scene Game View Help                     [Play]   title bar     |
| [Select][Move][Rotate][Scale] [Snap]   [+ Cube][+ Sphere][+ Light]  tools |
|---------+-------------------------------------------------+--------------|
| Objects |                                                 | Inspector    |
| Project |                                                 |  Name        |
| Scene   |               3D viewport                       |  Position    |
| Ground  |                                                 |  Rotation    |
| Player  |                                                 |  ...         |
| ...     |                                                 |              |
|---------+-------------------------------------------------+--------------|
| output                                                                   |
+--------------------------------------------------------------------------+
```

- **Objects** (left) lists the objects in the scene. The first two rows
  select the **Project** settings and the **Scene** settings instead.
- **The viewport** (middle) shows the scene. Drag to orbit, Shift+drag to
  pan, use the wheel to zoom, and click an object to select it.
- **The inspector** (right) shows the settings of what is selected. Click a
  row to change it. On/off rows flip; the others ask for a new value on the
  status line.
- **The tools**: Select (Q), Move (W), Rotate (E), Scale (R). With Move,
  Rotate or Scale chosen, dragging the selected object changes it. G turns
  snapping on and off.

Ctrl+1 shows the scene editor and Ctrl+2 shows the code, which is the
Whisker IDE with its file tree, tabs, syntax colouring and error markers.
Ctrl+S saves the scene and every open file.

[The editor](editor.md) lists every menu item, key and inspector setting.

## Play

Press **Play** (Ctrl+Enter). The editor saves the scene and the open file, compiles the
scripts and runs the game in the whole stage. Esc stops it and returns to
the editor. The scene is reloaded as it was saved, so nothing the game did
while it ran is kept. What scripts `print` and any error appear in the output
panel. A script error also opens the script at the failing line.

Game > Check scripts compiles every script without playing, to find mistakes
quickly.

## A first script

Select an object, for example a cube (Scene > Add cube). In the inspector,
click **> New script** and accept the name `scripts/cube.wsk`. The script
opens in the code view:

```lua
-- scripts/cube.wsk
function start(self)
  print("hello from " .. self.name)
end

function update(self, dt)
  self:rotate(0, 90 * dt, 0)          -- 90 degrees a second around y
  if input.pressed("space") then
    self:push(0, 8, 0)                -- needs a dynamic body
    sound.play("jump")
  end
end
```

Give the cube a **Body** of `dynamic` and a **Collider** of `box` in the
inspector, so that it falls onto the ground and can jump. Then press Play.

`start(self)` runs once for every object that uses the script, before its
first `update`. `update(self, dt)` runs every frame, and `dt` is the time
since the last frame in seconds. `self` is the object. [Scripting](scripting.md)
explains all of it, and the [reference](reference.md) lists every function.

## Save and share

Projects live in the engine's file system. Save the `.sb3` (File > Save to
your computer in TurboWarp) to keep them.

To share a game, use File > Export project (.txt). The game is compiled and
put in the list `w3d_export` on the stage. Right-click the list, choose
**export**, and give the file to players. They import it into the list
`game` of the player project for its screen size. [Publishing](publishing.md)
goes through it step by step.

## Help inside the engine

The Help menu opens these pages inside the engine:

| Item | Opens |
|---|---|
| Getting started | `/docs/getting-started.txt`, a short version of this page |
| Whisker 3D reference | `/docs/w3d-library.txt`, every `w3d`, `input` and `sound` function |
| Whisker language | `/docs/whisker/reference.txt`, the Whisker quick reference |
| Keyboard and mouse | the editor's keys and mouse actions |
