# The editor

The engine is the [Whisker IDE](../whisker/ide.md) with a scene editor added.
It has four modes: the start screen, the scene editor (Ctrl+1), the code view
(Ctrl+2) and play (Ctrl+Enter, Esc to stop).

## Mouse and keys in the scene editor

| Action | Does |
|---|---|
| Click an object | Selects it. Click empty space to select the scene. |
| Drag (Select tool, or nothing selected) | Orbits the view around its centre. |
| Shift + drag | Pans the view. |
| Wheel | Zooms. |
| Drag (Move tool) | Moves the selection across the ground plane. Shift + drag moves it up and down. |
| Drag (Rotate tool) | Turns the selection around y. Shift + drag turns it around x. |
| Drag (Scale tool) | Drag up to grow and down to shrink, evenly. Shift + drag scales only the height. |
| Q, W, E, R | Select, Move, Rotate and Scale tools |
| G | Snap on or off: positions snap to 0.25 and rotations to 15 degrees |
| F | Focus the view on the selection |
| Arrow keys, Page Up / Page Down | Nudge the selection along x, z and y, by 0.25 (0.05 with snap off) |
| Delete, Backspace | Delete the selection |
| Ctrl+D | Duplicate the selection |
| Ctrl+Z | Undo the last scene change |
| Ctrl+S | Save the scene and the open files |
| Ctrl+1, Ctrl+2 | Scene editor, code |
| Ctrl+Enter | Play |
| Esc | Stop the game |

The viewport draws a grid on the ground, the selection's outline, and a
small marker for each light and camera. Lights and cameras are invisible in
the game.

## The inspector

Click a row to change it. Rows that are on/off flip when clicked. The others
ask for a value on the status line: type it and press Enter, or press Esc to
cancel. Vectors are typed as three numbers (`0 1.5 -2`), and colours as
`#rrggbb`.

**Object rows**

| Row | For | Meaning |
|---|---|---|
| Name | all | The object's name, used by `w3d.find` and `touching` |
| Shape | meshes | A built-in shape (`cube`, `sphere`, ...) or a model path (`models/tree.obj`) |
| Position, Rotation, Scale | all (scale: meshes and empties) | x y z. Rotation is in degrees, applied as yaw (y), then pitch (x), then roll (z). |
| Colour | meshes | The colour of faces that have none of their own |
| Transparency | meshes | 0 (solid) to 100 (invisible) |
| Visible | meshes | Hidden objects still collide and run scripts |
| Unlit | meshes | Drawn in its own colour, ignoring lights (signs, coins, stars) |
| Two-sided | meshes | Back faces are drawn too (flat leaves, glass panes) |
| Range, Strength | lights | How far the light reaches, and how bright it is |
| View angle | cameras | The vertical field of view, in degrees |
| Tag | all | A group name: `w3d.objects("#coin")`, `touching("#enemy")` |
| Script | all | The script this object runs. **> Edit the script** opens it; **> New script** makes one. |
| Body, Collider, Trigger, Bounce | all | See [Physics](physics.md) |

**Scene rows** (click **Scene** in the object list): name, sky top and
horizon colours, ambient light, sun direction and strength, fog on/off with
near / far distances and colour, gravity, and the view angle.

**Project rows** (click **Project**): name, resolution, first scene, and the
quality settings described in [Graphics](graphics.md#quality).

## Menus

| Menu | Items |
|---|---|
| File | Projects... (back to the start screen), New project..., Save, Export project (.txt), Import project (.txt), Import model (.obj), New script..., New scene..., Open scene..., New file..., Close tab |
| Edit | Undo, Redo, Cut, Copy, Paste, Select all (code), Duplicate object, Delete object, Find..., Replace..., Go to line..., Toggle comment |
| Scene | Add cube, sphere, plane, cylinder, cone, pyramid, wedge (ramp), torus, capsule, quad; Add model...; Add empty; Add point light; Add camera; Focus on selection; Scene settings |
| Game | Play, Stop, Check scripts, Project settings |
| View | Scene editor, Code, the four tools, snap, Reset the view, output panel size, dark and light themes |
| Help | Getting started, Whisker 3D reference, Whisker language, Keyboard and mouse, About |

New objects appear at the centre of the view, standing on the ground. The
game looks through the scene's first camera; further cameras are only
objects (a script can copy their position to the real camera). If a scene
has no camera, one is made at (0, 3, -8), looking slightly down. Point
lights are white; up to 8 visible ones light the scene at a time.

## Importing a model

1. File > Import model (.obj). The engine shows the list `w3d_import` on the
   stage.
2. Right-click the list, choose **import**, and pick the `.obj` file.
3. Choose File > Import model (.obj) again and give the file a name, such as
   `models/house.obj`.
4. Scene > Add model..., or set an object's **Shape** to that path.

Colours come from `usemtl` lines. A `.mtl` file can be imported the same way
next to the model (`models/house.mtl`), and the model then uses its `Kd`
colours. See [Scenes and projects](scenes.md#obj-models).

## Code view

The code view is the Whisker IDE: a file tree of the project, tabs, syntax
colouring, find and replace, and error markers. Errors from Check scripts and
from playing open the script at the line. The [IDE chapter](../whisker/ide.md)
of the Whisker manual describes it. Whisker 3D scripts can use everything in
Whisker except the ScratchOS-only libraries (`gui`, windows, `net`). See
[Scripting](scripting.md#what-scripts-can-use).
