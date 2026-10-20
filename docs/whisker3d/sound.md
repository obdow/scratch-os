# Sound

Whisker 3D has two kinds of sound: **effects**, a built-in library of short
sounds, and **music**, notes and drums played by the Scratch Music extension.

## Effects

```lua
sound.play("jump")
sound.play("coin", 60)          -- at 60% volume
sound.play("laser", 100, -30)   -- three semitones lower
for _, name in ipairs(sound.list()) do print(name) end
```

| Name | Sound |
|---|---|
| `jump` | A rising chirp |
| `coin` | Two quick high notes |
| `powerup` | A rising run of notes |
| `hit` | A short noisy thud |
| `hurt` | A falling buzz |
| `explosion` | A burst of noise that fades |
| `laser` | A falling zap |
| `shoot` | A short noisy zap |
| `click` | A tiny tick, for buttons |
| `select` | Two rising notes |
| `blip` | A short square-wave beep |
| `pop` | A bubble pop |
| `step` | A soft tick of noise |
| `whoosh` | A rush of air |
| `win` | A rising fanfare |
| `lose` | Four falling notes |
| `bounce` | A springy boing |
| `beep` | A plain sine beep |

The effects are made by `tools/w3d_sounds.py` when the engine is built, so
they need no sound files. Effects take turns on four channels, so several
can play at once. `pitch` is Scratch's pitch effect: 10 is
one semitone, so 120 is an octave up and -120 an octave down. Varying it a
little each time (`sound.play("step", 50, math.random(-20, 20))`) makes
repeated sounds less tiring.

## Music

The Music extension plays notes on four **voices**. Each voice plays its
queue of notes, drums and rests one after another, while the game runs.
`beats` are at the current tempo (`sound.tempo(bpm)`, 120 by default).

```lua
sound.tempo(100)
-- a C major arpeggio on the piano (instrument 1), voice 1
for _, n in ipairs({60, 64, 67, 72}) do sound.note(n, 0.5, 1) end
-- a chord: the same moment on three voices
sound.note(60, 2, 1, 1)
sound.note(64, 2, 1, 2)
sound.note(67, 2, 1, 3)
-- drums go to voice 4 unless you say otherwise
sound.drum(2, 1)  sound.drum(1, 1)
sound.rest(1)
```

The queues are filled by your scripts, so queue a phrase and then wait until
it has had time to play before you queue the next one:

```lua
-- scripts/music.wsk: a bass line on voice 1 and a beat on voice 4
local BASS = {45, 45, 52, 48, 45, 45, 55, 52}
local next_time = 0

function start(self) sound.tempo(132) end

function update(self, dt)
  if w3d.time() >= next_time then
    for i, n in ipairs(BASS) do
      sound.note(n, 0.5, 6, 1)                       -- bass (6), voice 1
      if i % 2 == 1 then sound.drum(1, 0.5) else sound.drum(3, 0.5) end
    end
    next_time = w3d.time() + 4 * 60 / 132            -- 8 half beats
  end
end
```

`sound.stop()` stops everything and empties the queues.
`sound.volume(v)` sets the volume of everything, 0..100.

**Instruments** (`sound.note`'s third argument): 1 Piano, 2 Electric Piano,
3 Organ, 4 Guitar, 5 Electric Guitar, 6 Bass, 7 Pizzicato, 8 Cello,
9 Trombone, 10 Clarinet, 11 Saxophone, 12 Flute, 13 Wooden Flute,
14 Bassoon, 15 Choir, 16 Vibraphone, 17 Music Box, 18 Steel Drum,
19 Marimba, 20 Synth Lead, 21 Synth Pad. 0 or no argument keeps the voice's
instrument (piano at first).

**Drums** (`sound.drum`'s first argument): 1 Snare Drum, 2 Bass Drum,
3 Side Stick, 4 Crash Cymbal, 5 Open Hi-Hat, 6 Closed Hi-Hat, 7 Tambourine,
8 Hand Clap, 9 Claves, 10 Wood Block, 11 Cowbell, 12 Triangle, 13 Bongo,
14 Conga, 15 Cabasa, 16 Guiro, 17 Vibraslap, 18 Cuica.

**Notes** are MIDI numbers: 60 is middle C, 61 C#, 62 D, and each octave is
12 more (72 is the C above middle C).

## How it works

The engine's scripts never play sounds directly. The library adds requests
to a queue (global Scratch lists), and a separate sprite, **Sound**, plays
them. It has eight clones: four effect channels, each with its own volume
and pitch effect, and the four music voices, which use the Music
extension's blocks and wait for each note. Because the Music extension is
part of the project, the players ask for it when they load.
