# Publishing

A finished game is exported from the engine as **one `.txt` file**. A player
project loads that file through a Scratch list, so the game can be shared
without the engine.

```
Whisker3D.sb3                     game.txt                    Whisker3D-Player-720p.sb3
File > Export project  ──list w3d_export──▶  (export)  ──list game──▶  or -480x360.sb3
```

## Export

1. Open the project and choose **File > Export project (.txt)**.
2. The engine checks and compiles every script. If one does not compile,
   it says which and where, and nothing is exported.
3. The list **`w3d_export`** appears on the stage, holding the whole
   project: one line of the file per item.
4. Right-click the list and choose **export**. The browser saves it as a
   `.txt` file (named after the list; rename it to your game's name).

The same file is also a backup of the project: it can be imported back into
the engine (see [Import](#import-into-the-engine)).

## Play it in a player

There are two players, one for each screen size. Use the one that matches
the project's resolution:

| Player | Use for | Where |
|---|---|---|
| `Whisker3D-Player-720p.sb3` | Games made at 1280 x 720 | TurboWarp |
| `Whisker3D-Player-480x360.sb3` | Games made at 480 x 360 | TurboWarp, or scratch.mit.edu |

1. Open the player and click the green flag. With no game loaded, it shows
   the steps and the list **`game`**.
2. Right-click the list `game`, choose **import**, and pick the `.txt` file.
3. Click the green flag again. The game starts.
4. Save the player project (File > Save to your computer). The game is now
   inside it, and the `.sb3` can be shared or uploaded like any project.

If a game stops with an error, the player shows the error and the last
lines the scripts printed. A game that ends with `w3d.quit()` shows "The game
has ended"; the green flag starts it again.

The players contain no Whisker compiler (it would not fit in a Scratch
project), so the export carries every script already compiled. After
changing a script, export again.

## Sharing on scratch.mit.edu

Only the 480 x 360 player is made for vanilla Scratch:

- Its stage is Scratch's standard 480 x 360.
- Its `project.json` is under Scratch's 5 MB limit, with the game loaded
  (the exported examples are about 15 KB each, so there is plenty of room).
- It draws inside the stage with sprite fencing on. While drawing it wears a
  blank costume, so the pen can reach the edges.
- It keeps working at Scratch's 30 frames a second. The game's `dt` follows
  the real time, so things move at the same speed at any frame rate.

Upload the saved player `.sb3` with the game in it. Players on the website
just click the green flag. Vanilla Scratch is much slower than TurboWarp, so
test the game there before sharing it, and lower the triangle budget or
raise the fill coarseness if needed (see [Graphics](graphics.md#quality)).

The 720p player uses TurboWarp features (a 1280 x 720 stage and no fencing),
so share it as a `.sb3` for TurboWarp, or package it with the
[TurboWarp Packager](https://packager.turbowarp.org).

## Import into the engine

**File > Import project (.txt)** (also on the start screen) makes a new
project from an exported file:

1. Choose File > Import project. The list **`w3d_import`** appears.
2. Right-click it, choose **import**, and pick the `.txt` file.
3. Choose File > Import project again and give the project a name (the name
   in the file is suggested). The project opens.

## The bundle format

The `.txt` file is plain text, one line per list item:

```
WHISKER3D 1
name Coin Run
@file game.w3d 7
-- Whisker 3D project settings
name Coin Run
resolution 1280x720
...
@file scenes/level1.scene 120
...
@file scripts/player.wsk 41
...
@file .build/scripts/player.wsk 230
WBC 1 ...
@end
```

- `WHISKER3D 1` is the format and version.
- `name` is the project's name.
- `@file PATH N` is followed by the `N` lines of the file at `PATH` in the
  project. Files are text: settings, scenes, scripts, models.
- `.build/` holds the compiled scripts for the players: each object script
  together with the loop that runs it, and each module it requires
  (`.build/req/1`, `.build/req/2`, ...), as Whisker bytecode in text form
  (WBC). The engine itself does not use `.build` (it compiles the scripts
  as it plays them), and makes it again on every export.
- `@end` ends the bundle.

Scratch's list import reads the file as CSV when lines contain commas (it
offers to pick a column), which would cut lines apart. So every line that
contains a special character is escaped:

| Written | Means |
|---|---|
| `~~` | `~` |
| `~c` | `,` |
| `~s` | `;` |
| `~p` | `\|` |
| `~t` | a tab |
| `~q` | `"` |
| `~0` (the whole line) | an empty line |

Lines without any of these characters are written as they are, so most of
a bundle stays readable.

`tools/w3d_bundle.py` packs a project folder into a bundle and unpacks one,
outside Scratch:

```
python3 tools/w3d_bundle.py pack "w3d/rootfs/examples/Coin Run" coinrun.txt
python3 tools/w3d_bundle.py unpack coinrun.txt out/
```

A bundle packed this way has no `.build` folder: it can be imported into the
engine, but a player needs one exported by the engine.
