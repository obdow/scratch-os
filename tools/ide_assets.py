"""
Costumes and palette for the Whisker IDE (WhiskerIDE.sb3 only).

ScratchOS draws text with the IBM VGA font in the 16 VGA colours.  The IDE
uses JetBrains Mono and a modern palette instead, so it needs arbitrary RGB
colours.  Colours are still produced from a few base costume sets with the
colour (hue) and brightness effects:

  * Scratch's colour effect rotates the hue in HSV space, which keeps the
    *chroma* (max - min channel) of the base colour; the brightness effect
    then adds the same value to R, G and B.  So one base set of chroma C can
    reach every colour whose chroma is C, exactly:
        target T, mn = min(T)
        base   B = (V, V - C, V - C)          (hue 0, value V = max(C, 14))
        colour effect     = hue(T) * 200
        brightness effect = (mn - (V - C)) / 255 * 100
  * near-neutral colours (chroma <= GREY_MAX) come from the white set with
    brightness alone, as in ScratchOS.

The palette's chromas are clustered into a handful of levels (log-scale
k-means); each colour is nudged to its level's chroma, which keeps the hue
and the darkest channel.  One base set = 256 glyphs + 81 power-of-two rects.

Only the characters the IDE actually shows get a glyph (GLYPHS: printable
ASCII, the UI symbols and the few non-ASCII characters in the bundled
files); any other code is drawn as '?'.  Glyphs are rendered from
JetBrains Mono at 4x and box-filtered to the costume's 2x resolution
(16x32 pixels for an 8x16 cell); stamped at 1x with linear filtering
(see src/ide/gfx.sbs) each 2x2 block is averaged, so text is anti-aliased.  The UI symbols (triangles, dot, stop
square, close cross, separator line) are drawn procedurally.

Palette indices (pal_* lists, 1-based in Scratch):
  0..15    active ANSI colours (copied from 80.. or 96.. on theme change)
  16..47   dark theme UI colours  (UI_NAMES order)
  48..79   light theme UI colours
  80..95   ANSI colours, dark theme
  96..111  ANSI colours, light theme
"""

import colorsys
import math
import os

from PIL import Image, ImageDraw, ImageFont

import assets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JBM_PATH = os.path.join(ROOT, 'assets', 'font', 'JetBrainsMono-Regular.ttf')

# CP437 codes that get a glyph costume
GLYPHS = sorted(set(range(32, 127)) | {
    7,     # dot: modified tab, tree files, run status
    16,    # right triangle: Run button, collapsed folder, "run" lines
    30,    # up triangle: output panel button
    31,    # down triangle: output panel button, expanded folder
    130,   # e acute (used in the language reference)
    158,   # close cross (drawn in the peseta slot)
    175,   # >> : truncated tree names
    196,   # horizontal line: menu separators
    254,   # stop square: Stop button, "stopped" / "exit code" lines
})
QMARK = GLYPHS.index(63)

GREY_MAX = 8          # chroma at or below this is drawn as a neutral grey
LEVELS = 8            # number of chromatic base sets
SET_SIZE = len(GLYPHS) + 81   # glyphs + rects per base set

UI_NAMES = [
    'EDBG', 'PANEL', 'BORDER', 'TEXT', 'DIM', 'EDFG', 'GUT', 'GUTCUR',
    'CURLINE', 'SEL', 'ACCENT', 'ACTIVE', 'RUN', 'STOP', 'ERRBG', 'ERRFG',
    'SCROLL', 'BUTTON', 'KW', 'STR', 'NUM', 'COM', 'LIB', 'POPUP',
    'ONACC', 'WARN', 'POPBD', 'HEADER', 'PTROUT', 'FOLDER', 'WSK', 'HOVER',
]

# JetBrains "New UI" inspired themes
DARK = {
    'EDBG': '1E1F22', 'PANEL': '2B2D30', 'BORDER': '393B40', 'TEXT': 'DFE1E5',
    'DIM': '868A91', 'EDFG': 'BCBEC4', 'GUT': '4B5059', 'GUTCUR': 'A1A3AB',
    'CURLINE': '26282E', 'SEL': '214283', 'ACCENT': '3574F0', 'ACTIVE': '2E436E',
    'RUN': '5FB865', 'STOP': 'DB5C5C', 'ERRBG': '4A2B2E', 'ERRFG': 'F75464',
    'SCROLL': '4E5157', 'BUTTON': '393B40', 'KW': 'CF8E6D', 'STR': '6AAB73',
    'NUM': '2AACB8', 'COM': '7A7E85', 'LIB': '56A8F5', 'POPUP': '2B2D30',
    'ONACC': 'FFFFFF', 'WARN': 'F2C55C', 'POPBD': '4E5157', 'HEADER': 'DFE1E5',
    'PTROUT': '000000', 'FOLDER': 'C7A65D', 'WSK': '6AAB73', 'HOVER': '35373B',
}
LIGHT = {
    'EDBG': 'FFFFFF', 'PANEL': 'F7F8FA', 'BORDER': 'EBECF0', 'TEXT': '000000',
    'DIM': '6C707E', 'EDFG': '080808', 'GUT': 'AEB3C2', 'GUTCUR': '767A8A',
    'CURLINE': 'F5F8FE', 'SEL': 'A6D2FF', 'ACCENT': '3574F0', 'ACTIVE': 'D5E1FF',
    'RUN': '208A3C', 'STOP': 'E55765', 'ERRBG': 'FAE3E3', 'ERRFG': 'E55765',
    'SCROLL': 'C9CCD6', 'BUTTON': 'DFE1E5', 'KW': '0033B3', 'STR': '067D17',
    'NUM': '1750EB', 'COM': '8C8C8C', 'LIB': '00627A', 'POPUP': 'FFFFFF',
    'ONACC': 'FFFFFF', 'WARN': 'B97C00', 'POPBD': 'C9CCD6', 'HEADER': '000000',
    'PTROUT': '000000', 'FOLDER': 'A3832F', 'WSK': '067D17', 'HOVER': 'EBECF0',
}
# 16 terminal / graphics colours (VGA order) per theme
ANSI_DARK = ['1E1F22', '3B7DD8', '5FA35F', '3CA8B4', 'D9534F', 'A770D0', 'C9913A', 'BCBEC4',
             '6B7280', '6CA6F7', '8BD17C', '6ED3DD', 'F07178', 'D29BF0', 'F2CC60', 'EDEFF2']
ANSI_LIGHT = ['FFFFFF', '4078F2', '50A14F', '0184BC', 'E45649', 'A626A4', 'C18401', '383A42',
              'A0A1A7', '526FFF', '3E953A', '0997B3', 'CA1243', 'B751B6', '986801', '000000']


def _rgb(h):
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def palette_hex():
    out = list(ANSI_DARK)
    out += [DARK[n] for n in UI_NAMES]
    out += [LIGHT[n] for n in UI_NAMES]
    out += ANSI_DARK + ANSI_LIGHT
    assert len(out) == 112
    return out


def _levels(chromas):
    """Log-scale 1-D k-means over the chromatic palette entries."""
    lv = sorted(math.log(c) for c in chromas)
    k = min(LEVELS, len(set(lv)))
    cent = [lv[int(i * (len(lv) - 1) / max(1, k - 1))] for i in range(k)]
    for _ in range(100):
        groups = [[] for _ in cent]
        for v in lv:
            groups[min(range(k), key=lambda i: abs(v - cent[i]))].append(v)
        cent = [sum(g) / len(g) if g else cent[i] for i, g in enumerate(groups)]
    return sorted(set(max(2, round(math.exp(c))) for c in cent))


def build_palette():
    """Return (base set colours, per-entry dicts) for the IDE palette."""
    cols = [_rgb(h) for h in palette_hex()]
    chromas = [max(c) - min(c) for c in cols if max(c) - min(c) > GREY_MAX]
    levels = _levels(chromas)
    bases = [(255, 255, 255)]
    for c in levels:
        v = max(c, 14)
        bases.append((v, v - c, v - c))
    entries = []
    for t in cols:
        mn, mx = min(t), max(t)
        c = mx - mn
        if c <= GREY_MAX:
            g = round((t[0] + t[1] + t[2]) / 3)
            entries.append({'set': 0, 'hue': 0, 'bri': (g - 255) / 255 * 100, 'rgb': (g, g, g)})
            continue
        k = min(range(len(levels)), key=lambda i: abs(math.log(levels[i]) - math.log(c)))
        cq = levels[k]
        q = [mn + (x - mn) * cq / c for x in t]
        if max(q) > 255:
            q = [x - (max(q) - 255) for x in q]
        q = tuple(round(x) for x in q)
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in q))
        b = bases[k + 1]
        bri = (min(q) - b[1]) / 255 * 100
        entries.append({'set': k + 1, 'hue': round(h * 200, 4), 'bri': round(bri, 4), 'rgb': q})
    return bases, entries


def layout():
    bases, _ = build_palette()
    n = len(bases)
    return {
        'GLYPH_BASE': 1,
        # no drawn pointer in the IDE (the system cursor is used); the
        # shared window manager code still names these costumes
        'CURSOR_COSTUME': 1,
        'CURSOR_MASK_COSTUME': 1,
        'IDE_SETS': n,
        'ORD_SENTINEL': 1 + QMARK,
    }


def build_data():
    """Data lists for src/ide/gfx.sbs."""
    _, entries = build_palette()
    gb, rb, hue, bri, rgb = [], [], [], [], []
    for e in entries:
        gb.append(1 + e['set'] * SET_SIZE)
        rb.append(1 + len(GLYPHS) + e['set'] * SET_SIZE)
        hue.append(e['hue'])
        bri.append(e['bri'])
        r, g, b = e['rgb']
        rgb.append(r * 65536 + g * 256 + b)
    # code -> glyph slot in a set (unsupported codes show '?'), and
    # costume number -> code for ord() (costume lookup by name, set 0)
    gmap = [GLYPHS.index(c) if c in GLYPHS else QMARK for c in range(256)]
    return {'ide_pal_gb': gb, 'ide_pal_rb': rb, 'ide_pal_hue': hue, 'ide_pal_bri': bri, 'ide_pal_rgb': rgb,
            'ide_gmap': gmap, 'glyph_code': list(GLYPHS)}


def ui_consts():
    """U_<NAME> = palette index of the dark-theme slot (light = +32)."""
    return {'U_' + n: 16 + i for i, n in enumerate(UI_NAMES)}


# ---------------------------------------------------------------------------
# glyph masks (alpha, 16x32 = 2x of an 8x16 cell)
# ---------------------------------------------------------------------------

SS = 4                 # drawing scale: 4 canvas px per stage px (2x the costume)
W4, H4 = 8 * SS, 16 * SS
CX4, CY4 = W4 // 2, H4 // 2

def _shape_mask(code):
    """UI symbols drawn procedurally (None if `code` is not one)."""
    img = Image.new('L', (W4, H4), 0)
    dr = ImageDraw.Draw(img)
    if code == 196:
        # separator line, 1 stage pixel, edge to edge
        dr.rectangle([0, CY4 - SS // 2, W4 - 1, CY4 + SS // 2 - 1], fill=255)
    elif code in (16, 30, 31):
        # small solid triangles: right, up, down
        s = 3 * SS
        cx, cy = CX4, CY4 + SS // 2
        pts = {16: [(cx - s * 0.6, cy - s), (cx - s * 0.6, cy + s), (cx + s * 0.9, cy)],
               30: [(cx - s, cy + s * 0.6), (cx + s, cy + s * 0.6), (cx, cy - s * 0.9)],
               31: [(cx - s, cy - s * 0.6), (cx + s, cy - s * 0.6), (cx, cy + s * 0.9)]}[code]
        dr.polygon(pts, fill=255)
    elif code == 158:
        # '₧' slot holds a close cross (x) for tabs and windows
        s = int(2.5 * SS)
        cy = CY4 + SS // 2
        dr.line([(CX4 - s, cy - s), (CX4 + s, cy + s)], fill=255, width=int(SS * 1.1))
        dr.line([(CX4 - s, cy + s), (CX4 + s, cy - s)], fill=255, width=int(SS * 1.1))
    elif code == 0xFE:
        s = 3 * SS
        cy = CY4 + SS // 2
        dr.rounded_rectangle([CX4 - s, cy - s, CX4 + s, cy + s], radius=SS, fill=255)
    elif code == 7:
        r = int(2.2 * SS)
        cy = CY4 + SS // 2
        dr.ellipse([CX4 - r, cy - r, CX4 + r, cy + r], fill=255)
    else:
        return None
    return img


_font = None
_notdef = None


def _jbm():
    global _font, _notdef
    if _font is None:
        _font = ImageFont.truetype(JBM_PATH, 25 * SS // 2)
        k = _font.getmask('\U000F0000')
        _notdef = (k.size, bytes(k))
    return _font


def _font_mask(code):
    f = _jbm()
    ch = assets.cp437_char(code)
    k = f.getmask(ch)
    if (k.size, bytes(k)) == _notdef:
        return None
    img = Image.new('L', (W4, H4), 0)
    dr = ImageDraw.Draw(img)
    adv = f.getlength(ch)
    dr.text(((W4 - adv) / 2, -SS), ch, font=f, fill=255)
    return img



def glyph_mask(code):
    """16x32 alpha mask of glyph `code`."""
    if code == 32:
        return Image.new('L', (16, 32), 0)
    m = _shape_mask(code)
    if m is None:
        m = _font_mask(code)
    if m is None:
        raise ValueError(f'no glyph for CP437 code {code} in JetBrains Mono')
    return m.resize((16, 32), Image.BOX)


def _coloured(mask, rgb):
    img = Image.new('RGBA', mask.size, rgb + (255,))
    img.putalpha(mask)
    return img


def costumes():
    bases, _ = build_palette()
    masks = {code: glyph_mask(code) for code in GLYPHS}
    out = []
    for k, base in enumerate(bases):
        for code in GLYPHS:
            name = assets.glyph_name(code) if k == 0 else f's{k}g{code}'
            out.append(assets.make_costume(name, assets.png_bytes(_coloured(masks[code], base)), 'png', 0, 0))
        for i in range(9):
            for j in range(9):
                w, h = 1 << i, 1 << j
                img = Image.new('RGBA', (w * 2, h * 2), base + (255,))
                out.append(assets.make_costume(f's{k}rect_{w}x{h}', assets.png_bytes(img), 'png', 0, 0))
    assert len(out) == len(bases) * SET_SIZE
    return out


if __name__ == '__main__':
    b, e = build_palette()
    print(len(b), 'base sets', b)
    names = ['ansi%d' % i for i in range(16)] + ['d_' + n for n in UI_NAMES] + ['l_' + n for n in UI_NAMES]
    for i, (h, ent) in enumerate(zip(palette_hex(), e)):
        if i < 80:
            print(f"{i:3} {names[i]:10} {h} -> {'%02X%02X%02X' % ent['rgb']} set {ent['set']}")
    print(len(GLYPHS), 'glyphs,', len(b) * SET_SIZE, 'costumes')
    sheet = Image.new('RGBA', (16 * 32, 32 * 4), (30, 31, 34, 255))
    for k, code in enumerate(GLYPHS):
        sheet.alpha_composite(_coloured(glyph_mask(code), (223, 225, 229)), ((k % 32) * 16, (k // 32) * 32))
    sheet.save(os.environ.get('SHEET', '/tmp/ide_glyphs.png'))
