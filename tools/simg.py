"""
The ScratchOS image format (.simg) on the build machine, and the sample
pictures in rootfs/home/user/Pictures.

    python3 tools/simg.py            # (re)generate the sample pictures
    python3 tools/simg.py in.png     # convert a PNG to .simg (beside it)

Format (see src/image.sbs and docs/SIMG.md):

    SIMG 1
    size W H
    palette N
    #rrggbb #rrggbb - ...        N colours, "-" = transparent
    pixels
    3*1 2 ...                    one line per row: "count*index" or "index"
    end
"""

import colorsys
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICTURES = os.path.join(ROOT, 'rootfs', 'home', 'user', 'Pictures')
MAX_PIXELS = 65536


def encode(w, h, px, comment=None):
    """px: list of h rows of w values, each (r, g, b) or None (transparent)."""
    assert w * h <= MAX_PIXELS
    pal, index = [], {}
    for row in px:
        for c in row:
            if c not in index:
                index[c] = len(pal)
                pal.append(c)
    out = ['SIMG 1']
    if comment:
        out.append('# ' + comment)
    out += [f'size {w} {h}', f'palette {len(pal)}']
    toks = ['-' if c is None else '#%02x%02x%02x' % c for c in pal]
    for i in range(0, len(toks), 8):
        out.append(' '.join(toks[i:i + 8]))
    out.append('pixels')
    for row in px:
        parts, x = [], 0
        while x < w:
            n = 1
            while x + n < w and row[x + n] == row[x]:
                n += 1
            k = index[row[x]]
            parts.append(str(k) if n == 1 else f'{n}*{k}')
            x += n
        out.append(' '.join(parts))
    out.append('end')
    return '\n'.join(out) + '\n'


def decode(text):
    lines = [l.strip() for l in text.splitlines()]
    assert lines[0].startswith('SIMG')
    w = h = 0
    pal = []
    k = 1
    npal = -1
    while lines[k] != 'pixels':
        l = lines[k]
        k += 1
        if not l or (l.startswith('#') and npal < 0):
            continue
        if l.startswith('size '):
            w, h = map(int, l.split()[1:3])
        elif l.startswith('palette '):
            npal = int(l.split()[1])
        else:
            for t in l.split():
                pal.append(None if t == '-' else tuple(int(t[i:i + 2], 16) for i in (1, 3, 5)))
    rows = []
    for y in range(h):
        row = []
        for t in lines[k + 1 + y].split():
            n, _, i = t.rpartition('*')
            row += [pal[int(i)]] * (int(n) if n else 1)
        rows.append(row)
    return w, h, rows


# --- sample pictures ------------------------------------------------------------

def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sunset():
    w, h = 192, 120
    sky = [(18, 24, 82), (92, 44, 140), (214, 82, 120), (250, 160, 96), (255, 214, 140)]
    rows = []
    horizon = 78
    for y in range(h):
        row = []
        for x in range(w):
            if y < horizon:
                t = y / horizon * (len(sky) - 1)
                i = min(int(t), len(sky) - 2)
                c = lerp(sky[i], sky[i + 1], t - i)
                # the sun
                if (x - 120) ** 2 + (y - 62) ** 2 < 18 ** 2:
                    c = (255, 236, 170)
            else:
                # sea: darker reflection with stripes of sun
                t = (y - horizon) / (h - horizon)
                c = lerp((60, 34, 96), (16, 18, 48), t)
                if abs(x - 120) < 20 - (y - horizon) * 0.3 and (y - horizon) % 4 < 2:
                    c = (250, 180, 110)
            row.append(c)
        rows.append(row)
    # hills
    for x in range(w):
        top = horizon - 10 - int(9 * math.sin(x / 23) + 6 * math.sin(x / 9 + 1))
        for y in range(top, horizon):
            rows[y][x] = (34, 22, 58)
    return w, h, rows, 'sunset over the sea'


def cat():
    w = h = 48
    rows = [[None] * w for _ in range(h)]
    cx, cy, r = 24, 28, 15
    blue, eye = (53, 117, 240), (255, 255, 255)

    def inside_tri(px, py, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s((px, py), a, b), s((px, py), b, c), s((px, py), c, a)
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)
    for y in range(h):
        for x in range(w):
            px_, py_ = x + 0.5, y + 0.5
            on = (px_ - cx) ** 2 + (py_ - cy) ** 2 <= r * r
            for sgn in (-1, 1):
                if inside_tri(px_, py_, (cx + sgn * r * 0.92, cy - r * 0.38), (cx + sgn * r * 0.78, cy - r * 1.55),
                              (cx + sgn * r * 0.12, cy - r * 0.9)):
                    on = True
            if on:
                rows[y][x] = blue
            for ex in (-r * 0.38, r * 0.38):
                if (px_ - (cx + ex)) ** 2 + (py_ - (cy - r * 0.08)) ** 2 <= (r * 0.14) ** 2:
                    rows[y][x] = eye
    return w, h, rows, 'the ScratchOS cat (transparent background)'


def heart():
    art = [
        "..XXX...XXX..",
        ".XXXXX.XXXXX.",
        "XXXXXXXXXXXXX",
        "XXXXXXXXXXXXX",
        "XXXXXXXXXXXXX",
        ".XXXXXXXXXXX.",
        "..XXXXXXXXX..",
        "...XXXXXXX...",
        "....XXXXX....",
        ".....XXX.....",
        "......X......",
    ]
    red, shine = (240, 71, 62), (255, 160, 150)
    rows = [[(red if ch == 'X' else None) for ch in line] for line in art]
    rows[2][2] = rows[2][3] = rows[3][2] = shine
    return len(art[0]), len(art), rows, 'pixel heart'


def mountains():
    w, h = 160, 96
    rows = []
    for y in range(h):
        rows.append([lerp((120, 190, 240), (220, 238, 250), y / h)] * w)
    # far to near: each range sits lower and darker than the one behind it
    layers = [(46, (120, 136, 180), 0.035, 18), (64, (74, 92, 140), 0.05, 14), (80, (40, 56, 96), 0.08, 9)]
    for base, colour, f, amp in layers:
        for x in range(w):
            top = int(base - amp * abs(math.sin(x * f * 3.1 + base)) - amp * 0.6 * math.sin(x * f * 7.3))
            for y in range(max(0, top), h):
                c = colour
                if y < top + 5 and base == 46:
                    c = (245, 248, 252)        # snow caps on the far range
                rows[y][x] = c
    for x in range(w):
        for y in range(84, h):
            rows[y][x] = (46, 120, 70) if (x + y) % 7 else (60, 140, 84)
    return w, h, rows, 'flat mountains'


def spectrum():
    w, h = 96, 48
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            hue = x / w
            v = 1 - max(0, (y - h / 2) / (h / 2))
            s = min(1, y / (h / 2))
            r, g, b = colorsys.hsv_to_rgb(hue, s, v)
            row.append((round(r * 255), round(g * 255), round(b * 255)))
        rows.append(row)
    return w, h, rows, 'hue / saturation / value spectrum'


SAMPLES = {'sunset.simg': sunset, 'cat.simg': cat, 'heart.simg': heart,
           'mountains.simg': mountains, 'spectrum.simg': spectrum}


def from_png(path):
    from PIL import Image
    im = Image.open(path).convert('RGBA')
    if im.width * im.height > MAX_PIXELS:
        f = math.sqrt(MAX_PIXELS / (im.width * im.height))
        im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
    px = im.load()
    rows = [[(px[x, y][:3] if px[x, y][3] >= 128 else None) for x in range(im.width)] for y in range(im.height)]
    return im.width, im.height, rows


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            w, h, rows = from_png(p)
            out = os.path.splitext(p)[0] + '.simg'
            open(out, 'w').write(encode(w, h, rows, 'converted from ' + os.path.basename(p)))
            print('wrote', out, f'{w}x{h}')
        sys.exit(0)
    os.makedirs(PICTURES, exist_ok=True)
    for name, fn in SAMPLES.items():
        w, h, rows, note = fn()
        text = encode(w, h, rows, note)
        assert decode(text) == (w, h, rows)
        open(os.path.join(PICTURES, name), 'w').write(text)
        print(f'{name}: {w}x{h}, {len(text) // 1024} KiB')
