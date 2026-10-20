# Library reference

Whisker 3D adds three libraries to Whisker: `w3d` (objects, physics,
the camera, lights, the HUD and scenes), `input` and `sound`.

Conventions on this page:

- `obj` is an object table, or an object's id. Functions marked **(method)**
  can also be called on the object: `obj:pos()` is `w3d.pos(obj)`.
- Functions that return a vector return three values: `local x, y, z = obj:pos()`.
- A **colour** is `"#rrggbb"` or a number `0xRRGGBB`.
- Angles are in degrees. Distances are in units; a built-in shape is 1 unit
  across.
- Screen positions are game pixels from the top-left corner of the game
  (0..1279 x 0..719, or 0..479 x 0..359), whatever the size of the stage.
- A wrong argument raises an error such as
  `bad argument #2 to 'setpos' (number expected, got nil)`.

## Objects and scenes

| Function | Returns | Description |
|---|---|---|
| `w3d.find(name)` | obj or nil | The first live object with this name, or with this tag if `name` starts with `#` |
| `w3d.objects([filter])` | list | Every live object, or those with the name `filter`, or the tag `#filter` |
| `w3d.spawn(what [, x, y, z])` | obj | A new object: a copy of the object `what` (an object or the name of one, with its script, tag, body and looks), or a new object with the shape `what` (`"cube"`, `"models/tree.obj"`). At `x, y, z` if given. |
| `w3d.destroy(obj)` (method) | | Removes the object. Its scripts stop being called for it. Does nothing if it is already gone. |
| `w3d.alive(obj)` (method) | boolean | Whether the object still exists |
| `w3d.instances()` | list | The live objects that use the calling script |
| `w3d.frame()` | dt or nil | Waits for the next frame, and returns its `dt`; nil when the game or scene is ending. Scripts that define `update` do not need it. |
| `w3d.name(obj)` | string | The object's name (also `obj.name`) |
| `w3d.tag(obj)` (method) | string | Its tag (`""` if none) |
| `w3d.settag(obj, tag)` (method) | | Sets its tag |
| `w3d.load(scene)` | | Switches to another scene at the end of this frame. `"level2"` means `scenes/level2.scene`. |
| `w3d.scene()` | name, path | The current scene's name and file |
| `w3d.quit()` | | Ends the game (the engine returns to the editor; a player shows "The game has ended") |

## Messages and shared values

| Function | Description |
|---|---|
| `w3d.send(obj, msg [, data])` (method `obj:send(msg, data)`) | Sends a message to one object, for its script's `on_message(self, msg, data)` |
| `w3d.broadcast(msg [, data])` | Sends a message to every object that has a script |
| `w3d.message()` | The next message for an object of this script: `obj, msg, data`, or nil. The engine calls this for scripts that define `on_message`. |
| `w3d.set(key, value)` | Stores a value that every script can read, for the rest of the game |
| `w3d.get(key [, default])` | A stored value, or `default` (or nil) |

`msg`, `data` and stored values can be numbers, strings, booleans, nil or
objects.

## Position, rotation and scale

| Function | Returns | Description |
|---|---|---|
| `w3d.pos(obj)` (method) | x, y, z | Position |
| `w3d.setpos(obj, x, y, z)` (method) | | Sets the position |
| `w3d.move(obj, dx [, dy, dz])` (method) | | Moves by a vector in world axes (missing parts are 0) |
| `w3d.moverel(obj, dx [, dy, dz])` (method) | | Moves along the object's own right, up and forward axes |
| `w3d.rot(obj)` (method) | x, y, z | Rotation in degrees (pitch, yaw, roll), each in -180..180 |
| `w3d.setrot(obj, x, y [, z])` (method) | | Sets the rotation |
| `w3d.rotate(obj, dx [, dy, dz])` (method) | | Adds to the rotation |
| `w3d.scale(obj)` (method) | x, y, z | Scale |
| `w3d.setscale(obj, x [, y, z])` (method) | | Sets the scale; one number scales evenly |
| `w3d.forward(obj)` (method) | x, y, z | The unit vector the object faces (its +z axis) |
| `w3d.right(obj)` (method) | x, y, z | Its right-hand unit vector (+x) |
| `w3d.lookat(obj, x, y, z)` or `w3d.lookat(obj, other)` (method) | | Turns the object to face a point or another object (roll becomes 0) |
| `w3d.distance(a, b)` (method) | number | The distance between two objects |

Rotation is applied as yaw (around y), then pitch (around x), then roll
(around z). With rotation 0 an object faces +z. Positive yaw turns it to the
right (from +z towards +x), and positive pitch tilts its front down.

## Looks

| Function | Returns | Description |
|---|---|---|
| `w3d.color(obj)` (method) | number | Colour as `0xRRGGBB` |
| `w3d.setcolor(obj, colour)` or `w3d.setcolor(obj, r, g, b)` (method) | | Sets the colour (r, g, b are 0..255). Faces that have their own colour (models) keep it. |
| `w3d.alpha(obj)` (method) | number | Transparency, 0 (solid) to 100 (invisible) |
| `w3d.setalpha(obj, a)` (method) | | Sets the transparency |
| `w3d.visible(obj)` (method) | boolean | Whether it is drawn |
| `w3d.show(obj [, on])` (method) | | Shows it, or hides it if `on` is false. Hidden objects still collide and run scripts. |
| `w3d.mesh(obj)` (method) | string | Its shape name or model path |
| `w3d.setmesh(obj, shape)` (method) | | Changes its shape: a built-in name or a model path |

## Physics

See [Physics](physics.md) for how bodies behave.

| Function | Returns | Description |
|---|---|---|
| `w3d.velocity(obj)` (method) | x, y, z | Velocity in units a second |
| `w3d.setvelocity(obj, x, y, z)` (method) | | Sets the velocity (used by dynamic bodies) |
| `w3d.push(obj, dx [, dy, dz])` (method) | | Adds to the velocity (an impulse) |
| `w3d.grounded(obj)` (method) | boolean | Whether it stood on something in the last physics step |
| `w3d.touching(obj [, what])` (method) | boolean | Whether it touches anything, or `what`: an object, a name, or `"#tag"` |
| `w3d.contacts(obj)` (method) | list | The objects it touches |
| `w3d.body(obj)` (method) | body, collider | `"none"`, `"static"`, `"dynamic"` or `"kinematic"`, and `"none"`, `"box"` or `"sphere"` |
| `w3d.setbody(obj, body [, collider])` (method) | | Sets the body and, optionally, the collider. A body without a collider gets a box. |
| `w3d.gravity([g])` | number | Gets or sets gravity (the y acceleration; the default is -20) |
| `w3d.raycast(x, y, z, dx, dy, dz [, max [, ignore]])` | obj, dist, hx, hy, hz, nx, ny, nz | The first collider along the ray from `x, y, z` in direction `dx, dy, dz` (need not be unit length), up to `max` units (default 1000), skipping the object `ignore`. Returns the object, the distance, the hit point and the surface normal, or nil. Triggers are skipped. |

## Camera, lights and the world

| Function | Returns | Description |
|---|---|---|
| `w3d.camera()` | obj | The scene's camera object. Move and turn it like any object. |
| `w3d.fov([deg])` | number | Gets or sets the vertical view angle (10..150; default 60) |
| `w3d.sky(top [, horizon])` | | Sets the sky colours (one colour: a plain sky) |
| `w3d.fog(near, far [, colour])` | | Fades faces to `colour` from `near` to `far` units from the camera |
| `w3d.fog(false)` | | Turns fog off |
| `w3d.ambient([a])` | number | Gets or sets the ambient light (0..1; default 0.35) |
| `w3d.sun([x, y, z [, strength]])` | x, y, z, strength | Gets or sets the direction the sunlight travels and its strength (default `-0.4, -1, 0.5, 0.8`) |
| `w3d.light(obj [, range [, power]])` (method) | range, power | Gets or sets a point light's range in units and its strength |

## Screen and HUD

HUD drawing lasts one frame: call these in `update` every frame to keep them
on screen. They are drawn after the 3D view, in the order they were called.

| Function | Returns | Description |
|---|---|---|
| `w3d.screen()` | w, h | The game's size: 1280, 720 or 480, 360 |
| `w3d.text(x, y, text [, colour [, size]])` | | Text with its top-left corner at `x, y`. `size` 1 (default) or 2 for large text. `"\n"` starts a new line. The default colour is white. |
| `w3d.rect(x, y, w, h, colour [, transparency])` | | A filled rectangle; transparency 0 (solid, the default) to 100 |
| `w3d.line(x1, y1, x2, y2, colour [, width])` | | A line, `width` pixels wide (default 2) |
| `w3d.project(x, y, z)` | sx, sy, depth | The screen position of a world point (for labels over objects), or nil if it is behind the camera |
| `w3d.screenray(sx, sy)` | x, y, z, dx, dy, dz | The ray from the camera through a screen position, for `w3d.raycast` (mouse picking) |

```lua
-- click an object to select it
if input.clicked() then
  local x, y, z, dx, dy, dz = w3d.screenray(input.mouse())
  local hit = w3d.raycast(x, y, z, dx, dy, dz)
  if hit then print("clicked " .. hit.name) end
end
```

## Time

| Function | Returns | Description |
|---|---|---|
| `w3d.time()` | number | Seconds since the game started |
| `w3d.fps()` | number | Frames drawn in the last second |

## input

Key names are Scratch's (`"a"`, `"1"`, `"space"`, `"enter"`, `"up arrow"`, ...),
any case. `"up"`, `"down"`, `"left"`, `"right"` and `"return"` also work.

| Function | Returns | Description |
|---|---|---|
| `input.key(name)` | boolean | Whether the key is held down |
| `input.pressed(name)` | boolean | Whether it went down since the last frame |
| `input.released(name)` | boolean | Whether it went up since the last frame |
| `input.axis("horizontal")` | -1, 0 or 1 | Right arrow or D minus left arrow or A |
| `input.axis("vertical")` | -1, 0 or 1 | Up arrow or W minus down arrow or S |
| `input.mouse()` | x, y | The mouse position in game pixels |
| `input.mousedown()` | boolean | Whether the mouse button is held |
| `input.clicked()` | boolean | Whether the button went down since the last frame |

`input.pressed` and `input.released` compare this frame with the last. They
are true for exactly one frame per press, so call them every frame (in
`update`), not only now and then. A key that is already held when the game
starts does not count as pressed.

## sound

See [Sound](sound.md).

| Function | Description |
|---|---|
| `sound.play(name [, volume [, pitch]])` | Plays a built-in effect. `volume` 0..100 (default 100); `pitch` in Scratch's pitch effect units, 10 per semitone (default 0). |
| `sound.stop()` | Stops every sound and clears the music queues |
| `sound.list()` | The names of the built-in effects |
| `sound.note(note, beats [, instrument [, voice]])` | Queues a note on a music voice (1-4, default 1). `note` is a MIDI number (60 = middle C); `instrument` is a Scratch Music instrument (1-21; 0 or none keeps the voice's current one). |
| `sound.drum(drum, beats [, voice])` | Queues a drum (1-18, Scratch Music's drums) on a voice (default 4) |
| `sound.rest(beats [, voice])` | Queues a rest (default voice 1) |
| `sound.tempo(bpm)` | Sets the music tempo (default 120) |
| `sound.volume(v)` | Sets the master volume, 0..100 |
