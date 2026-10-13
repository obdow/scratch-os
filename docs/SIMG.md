# The ScratchOS image format (.simg)

`.simg` is ScratchOS's picture format. Paint saves it, Preview shows it, and
programs read and write it with the `image` library (see `WHISKER.md`). It is
plain text, so `cat` can show it and a text editor can change it. It is
small for the flat-colour pictures ScratchOS draws, because each row is
run-length encoded against a palette.

```
SIMG 1
# the ScratchOS cat
size 48 48
palette 3
- #3575f0 #ffffff
pixels
48*0
...
17*0 5*1 4*2 ...
end
```

| Line | Meaning |
|---|---|
| `SIMG 1` | magic and version; always the first line |
| `# text` | a comment (allowed before `palette`) |
| `size W H` | width and height in pixels; `W * H` is at most 65,536 |
| `palette N` | the number of palette entries that follow |
| entries | `N` colours over one or more lines, separated by spaces: `#rrggbb`, `#rgb`, or `-` for transparent. Entries are numbered from 0 |
| `pixels` | the start of the pixel rows |
| rows | `H` lines, top to bottom. Each is a list of palette indices, left to right; `count*index` repeats an index `count` times |
| `end` | optional terminator |

Blank lines in the header are ignored. A row that is short is padded with
transparent pixels, and extra pixels are dropped.

## Tools

* `python3 tools/simg.py` regenerates the sample pictures in
  `rootfs/home/user/Pictures`.
* `python3 tools/simg.py picture.png` converts a PNG (scaled down to fit
  65,536 pixels; alpha below 50% becomes transparent).

## In ScratchOS

Pixels are stored in a Whisker table: `w`, `h`, and an array part of raw
`0xRRGGBB` values (-1 for transparent). `gfx.image` draws it with the pen.
The pen takes any RGB, so pictures are not limited to the system palette.
Each row is drawn as one stroke per run of equal pixels.
