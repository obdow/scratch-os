"""
Costumes and palette for the modern look of ScratchOS and the Whisker IDE.

Both builds draw text in JetBrains Mono and use a palette of arbitrary RGB
colours.  Colours are produced from a few base costume sets with Scratch's
colour (hue) and brightness effects:

  * the colour effect rotates the hue in HSV space, which keeps the *chroma*
    (max - min channel) of the base colour; the brightness effect then adds
    the same value to R, G and B.  So one base set of chroma C reaches every
    colour whose chroma is C, exactly:
        target T, mn = min(T)
        base   B = (V, V - C, V - C)          (hue 0, value V = max(C, 14))
        colour effect     = hue(T) * 200
        brightness effect = (mn - (V - C)) / 255 * 100
  * near-neutral colours (chroma <= GREY_MAX) come from a white set with
    brightness alone.

The palette's chromas are clustered into a handful of levels (log-scale
k-means); each colour is nudged to its level's chroma, which keeps the hue
and the darkest channel.  One base set = the build's glyphs + 81
power-of-two rects.

Each build ships only the characters it shows (GLYPHS[kind]); any other
code is drawn as '?'.  Glyphs are rendered from JetBrains Mono at 4x and
box-filtered to the costume's 2x resolution (16x32 pixels for an 8x16 cell);
stamped at 1x with linear filtering (see src/gfx.sbs) each 2x2 block is
averaged, so text is anti-aliased.  UI symbols, box drawing, blocks and
shades are drawn procedurally so they meet exactly at cell edges.

Palette indices (pal_* lists, 1-based in Scratch):
  0..15      active terminal / graphics colours (copied from ANSI_SRC.. on a
             theme change)
  16..71     dark theme UI colours  (UI_NAMES order, UI_SLOTS of them)
  72..127    light theme UI colours
  128..143   ANSI colours, dark theme      (ANSI_SRC)
  144..159   ANSI colours, light theme
  160..249   desktop wallpaper gradient    (WALL_BASE, WALL_N steps)
"""

import colorsys
import math
import os

from PIL import Image, ImageDraw, ImageFont

import assets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JBM_PATH = os.path.join(ROOT, 'assets', 'font', 'JetBrainsMono-Regular.ttf')

# CP437 codes that get a glyph costume, per build
_IDE = set(range(32, 127)) | {
    7,     # dot: modified tab, tree files, run status
    16,    # right triangle: Run button, collapsed folder, "run" lines
    30,    # up triangle: output panel button
    31,    # down triangle: output panel button, expanded folder
    130,   # e acute (used in the language reference)
    158,   # close cross (drawn in the peseta slot)
    175,   # >> : truncated tree names
    196,   # horizontal line: menu separators
    254,   # stop square: Stop button, "stopped" / "exit code" lines
}
_OS = _IDE | {
    1,     # the ScratchOS logo (menu bar), drawn in the smiley slot
    3, 4, 5, 6,              # card suits (about, snake)
    15,    # large dot: window traffic lights
    17, 18, 24, 25, 26, 27,  # arrows
    240,   # menu / hamburger
    0xB0, 0xB1, 0xB2,        # shades
    0xDB, 0xDC, 0xDD, 0xDE, 0xDF,   # blocks
} | set(range(0xB3, 0xDB))   # box drawing
GLYPHS = {'ide': sorted(_IDE), 'os': sorted(_OS)}

GREY_MAX = 8          # chroma at or below this is drawn as a neutral grey
LEVELS = 8            # number of chromatic base sets

UI_NAMES = [
    'EDBG', 'PANEL', 'BORDER', 'TEXT', 'DIM', 'EDFG', 'GUT', 'GUTCUR',
    'CURLINE', 'SEL', 'ACCENT', 'ACTIVE', 'RUN', 'STOP', 'ERRBG', 'ERRFG',
    'SCROLL', 'BUTTON', 'KW', 'STR', 'NUM', 'COM', 'LIB', 'POPUP',
    'ONACC', 'WARN', 'POPBD', 'HEADER', 'PTROUT', 'FOLDER', 'WSK', 'HOVER',
    # desktop (ScratchOS)
    'MENUBAR', 'MENUTXT', 'DOCK', 'DOCKBD', 'DOCKTXT', 'TLRED', 'TLYEL', 'TLGRN',
    'TLOFF', 'TITLE', 'TITLEIN', 'TITLETXT', 'TITLEDIM', 'DESKTXT', 'WINBD', 'SHADOW',
    # dock icon tiles (the same in both themes)
    'ICBLUE', 'ICDARK', 'ICPURP', 'ICWHITE', 'ICORANGE', 'ICGREEN', 'ICGREY', 'ICRED',
]
UI_SLOTS = len(UI_NAMES)

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
    'MENUBAR': '232329', 'MENUTXT': 'ECECF0', 'DOCK': '2A2A31', 'DOCKBD': '4A4A54',
    'DOCKTXT': 'F2F2F5', 'TLRED': 'FF5F57', 'TLYEL': 'FEBC2E', 'TLGRN': '28C840',
    'TLOFF': '55555C', 'TITLE': '323238', 'TITLEIN': '27272C', 'TITLETXT': 'E8E8EC',
    'TITLEDIM': '8A8A92', 'DESKTXT': 'FFFFFF', 'WINBD': '101014', 'SHADOW': '18181E',
    'ICBLUE': '1E7CF2', 'ICDARK': '1C1C21', 'ICPURP': '7A4CF0', 'ICWHITE': 'F4F4F6',
    'ICORANGE': 'FF8A1E', 'ICGREEN': '2FBF57', 'ICGREY': '8E8E96', 'ICRED': 'F0473E',
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
    'MENUBAR': 'EDEDF0', 'MENUTXT': '1D1D1F', 'DOCK': 'E9E9ED', 'DOCKBD': 'C6C6CC',
    'DOCKTXT': '1D1D1F', 'TLRED': 'FF5F57', 'TLYEL': 'FEBC2E', 'TLGRN': '28C840',
    'TLOFF': 'CACACE', 'TITLE': 'E6E6E9', 'TITLEIN': 'F3F3F5', 'TITLETXT': '1D1D1F',
    'TITLEDIM': '9C9CA2', 'DESKTXT': 'FFFFFF', 'WINBD': 'AEAEB6', 'SHADOW': '6E6E80',
    'ICBLUE': '1E7CF2', 'ICDARK': '1C1C21', 'ICPURP': '7A4CF0', 'ICWHITE': 'F4F4F6',
    'ICORANGE': 'FF8A1E', 'ICGREEN': '2FBF57', 'ICGREY': '8E8E96', 'ICRED': 'F0473E',
}
# 16 terminal / graphics colours (VGA order) per theme
ANSI_DARK = ['1E1F22', '3B7DD8', '5FA35F', '3CA8B4', 'D9534F', 'A770D0', 'C9913A', 'BCBEC4',
             '6B7280', '6CA6F7', '8BD17C', '6ED3DD', 'F07178', 'D29BF0', 'F2CC60', 'EDEFF2']
ANSI_LIGHT = ['FFFFFF', '4078F2', '50A14F', '0184BC', 'E45649', 'A626A4', 'C18401', '383A42',
              'A0A1A7', '526FFF', '3E953A', '0997B3', 'CA1243', 'B751B6', '986801', '000000']


# desktop wallpaper: a vertical gradient from deep blue through violet to a
# warm coral.  Every step has the same chroma, so all of them come from one
# base set exactly (no banding from chroma quantisation).
WALL_N = 90                  # one colour per half-cell stripe at 720p
WALL_CHROMA = 120


def _wall(i):
    t = i / (WALL_N - 1)
    hue = (228 + 150 * t) % 360          # degrees: blue -> violet -> magenta -> coral
    mn = 18 + 92 * t                     # darker at the top
    # an RGB triple with this hue, max - min = WALL_CHROMA and min = mn
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 1, 1)
    return '%02X%02X%02X' % tuple(round(mn + x * WALL_CHROMA) for x in (r, g, b))


WALL = [_wall(i) for i in range(WALL_N)]
ANSI_SRC = 16 + 2 * UI_SLOTS
WALL_BASE = ANSI_SRC + 32


def _rgb(h):
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def palette_hex():
    out = list(ANSI_DARK)
    out += [DARK[n] for n in UI_NAMES]
    out += [LIGHT[n] for n in UI_NAMES]
    out += ANSI_DARK + ANSI_LIGHT
    out += WALL
    assert len(out) == WALL_BASE + WALL_N
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
    """Return (base set colours, per-entry dicts) for the palette."""
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


def set_size(kind):
    return len(GLYPHS[kind]) + 81       # glyphs + rects per base set


def layout(kind):
    bases, _ = build_palette()
    return {
        'GLYPH_BASE': 1,
        # no drawn pointer (the system cursor is used); kept for old code
        'CURSOR_COSTUME': 1,
        'CURSOR_MASK_COSTUME': 1,
        'UI_SETS': len(bases),
        'ORD_SENTINEL': 1 + GLYPHS[kind].index(63),
        'UI_SLOTS': UI_SLOTS,
        'ANSI_SRC': ANSI_SRC,
        'WALL_BASE': WALL_BASE,
        'WALL_N': WALL_N,
    }


def build_data(kind):
    """Data lists for src/gfx.sbs."""
    _, entries = build_palette()
    glyphs = GLYPHS[kind]
    size = set_size(kind)
    qmark = glyphs.index(63)
    gb, rb, hue, bri, rgb = [], [], [], [], []
    for e in entries:
        gb.append(1 + e['set'] * size)
        rb.append(1 + len(glyphs) + e['set'] * size)
        hue.append(e['hue'])
        bri.append(e['bri'])
        r, g, b = e['rgb']
        rgb.append(r * 65536 + g * 256 + b)
    # code -> glyph slot in a set (unsupported codes show '?'), and
    # costume number -> code for ord() (costume lookup by name, set 0)
    gmap = [glyphs.index(c) if c in glyphs else qmark for c in range(256)]
    return {'ui_pal_gb': gb, 'ui_pal_rb': rb, 'ui_pal_hue': hue, 'ui_pal_bri': bri, 'ui_pal_rgb': rgb,
            'ui_gmap': gmap, 'glyph_code': list(glyphs)}


def ui_consts():
    """U_<NAME> = palette index of the dark-theme slot (light = + UI_SLOTS)."""
    return {'U_' + n: 16 + i for i, n in enumerate(UI_NAMES)}


# ---------------------------------------------------------------------------
# glyph masks (alpha, 16x32 = 2x of an 8x16 cell)
# ---------------------------------------------------------------------------

SS = 4                 # drawing scale: 4 canvas px per stage px (2x the costume)
W4, H4 = 8 * SS, 16 * SS
CX4, CY4 = W4 // 2, H4 // 2

BOX = {  # code: (up, down, left, right), 1 = single, 2 = double
    0xB3: (1, 1, 0, 0), 0xB4: (1, 1, 1, 0), 0xB5: (1, 1, 2, 0), 0xB6: (2, 2, 1, 0),
    0xB7: (0, 2, 1, 0), 0xB8: (0, 1, 2, 0), 0xB9: (2, 2, 2, 0), 0xBA: (2, 2, 0, 0),
    0xBB: (0, 2, 2, 0), 0xBC: (2, 0, 2, 0), 0xBD: (2, 0, 1, 0), 0xBE: (1, 0, 2, 0),
    0xBF: (0, 1, 1, 0), 0xC0: (1, 0, 0, 1), 0xC1: (1, 0, 1, 1), 0xC2: (0, 1, 1, 1),
    0xC3: (1, 1, 0, 1), 0xC4: (0, 0, 1, 1), 0xC5: (1, 1, 1, 1), 0xC6: (1, 1, 0, 2),
    0xC7: (2, 2, 0, 1), 0xC8: (2, 0, 0, 2), 0xC9: (0, 2, 0, 2), 0xCA: (2, 0, 2, 2),
    0xCB: (0, 2, 2, 2), 0xCC: (2, 2, 0, 2), 0xCD: (0, 0, 2, 2), 0xCE: (2, 2, 2, 2),
    0xCF: (1, 0, 2, 2), 0xD0: (2, 0, 1, 1), 0xD1: (0, 1, 2, 2), 0xD2: (0, 2, 1, 1),
    0xD3: (2, 0, 0, 1), 0xD4: (1, 0, 0, 2), 0xD5: (0, 1, 0, 2), 0xD6: (0, 2, 0, 1),
    0xD7: (2, 2, 1, 1), 0xD8: (1, 1, 2, 2), 0xD9: (1, 0, 1, 0), 0xDA: (0, 1, 0, 1),
}
ROUNDED = {0xDA: 'tl', 0xBF: 'tr', 0xC0: 'bl', 0xD9: 'br'}


def _box_mask(code):
    up, down, left, right = BOX[code]
    lw = SS                     # line width: 1 stage pixel
    d = 3 * SS // 2 + SS // 2   # double-line offset from the centre (2 px)
    img = Image.new('L', (W4, H4), 0)
    dr = ImageDraw.Draw(img)

    def hline(y, x0, x1):
        x0, x1 = sorted((x0, x1))
        dr.rectangle([x0, y - lw // 2, x1 - 1, y + lw // 2 - 1], fill=255)

    def vline(x, y0, y1):
        y0, y1 = sorted((y0, y1))
        dr.rectangle([x - lw // 2, y0, x + lw // 2 - 1, y1 - 1], fill=255)

    if code in ROUNDED:
        # rounded single corner
        r = 3 * SS
        corner = ROUNDED[code]
        sx = 1 if corner in ('tl', 'bl') else -1    # direction of the horizontal arm
        sy = 1 if corner in ('tl', 'tr') else -1    # direction of the vertical arm
        ex = W4 if sx > 0 else 0
        ey = H4 if sy > 0 else 0
        hline(CY4, CX4 + sx * r, ex)
        vline(CX4, CY4 + sy * r, ey)
        # quarter circle centred at (CX4 + sx*r, CY4 + sy*r)
        ccx, ccy = CX4 + sx * r, CY4 + sy * r
        box = [ccx - r - lw // 2, ccy - r - lw // 2, ccx + r + lw // 2 - 1, ccy + r + lw // 2 - 1]
        start = {'tl': 180, 'tr': 270, 'br': 0, 'bl': 90}[corner]
        dr.arc(box, start, start + 90, fill=255, width=lw)
        return img

    st = {'u': up, 'd': down, 'l': left, 'r': right}

    def ext_single(perp):
        return d + lw // 2 if max(st[p] for p in perp) == 2 else lw // 2

    def ext_double(side, opp):
        # how far past the centre the line on `side` of a double arm runs
        if st[side] == 2:
            return -d
        if st[side] == 1:
            return 0
        return d

    for arm, sty in st.items():
        if sty == 0:
            continue
        if arm in 'ud':
            edge = 0 if arm == 'u' else H4
            sgn = 1 if arm == 'u' else -1        # direction from the edge toward the centre
            if sty == 1:
                vline(CX4, edge, CY4 + sgn * ext_single('lr'))
            else:
                for side, off in (('l', -d), ('r', d)):
                    e = ext_double(side, None)
                    vline(CX4 + off, edge, CY4 + sgn * e + (sgn * lw // 2))
        else:
            edge = 0 if arm == 'l' else W4
            sgn = 1 if arm == 'l' else -1
            if sty == 1:
                hline(CY4, edge, CX4 + sgn * ext_single('ud'))
            else:
                for side, off in (('u', -d), ('d', d)):
                    e = ext_double(side, None)
                    hline(CY4 + off, edge, CX4 + sgn * e + (sgn * lw // 2))
    return img


def _shape_mask(code):
    """UI symbols, blocks and shades drawn procedurally (None if not one)."""
    img = Image.new('L', (W4, H4), 0)
    dr = ImageDraw.Draw(img)
    cy = CY4 + SS // 2
    if code == 0xDB:
        dr.rectangle([0, 0, W4, H4], fill=255)
    elif code == 0xDC:
        dr.rectangle([0, H4 // 2, W4, H4], fill=255)
    elif code == 0xDF:
        dr.rectangle([0, 0, W4, H4 // 2 - 1], fill=255)
    elif code == 0xDD:
        dr.rectangle([0, 0, W4 // 2 - 1, H4], fill=255)
    elif code == 0xDE:
        dr.rectangle([W4 // 2, 0, W4, H4], fill=255)
    elif code in (0xB0, 0xB1, 0xB2):
        dr.rectangle([0, 0, W4, H4], fill={0xB0: 64, 0xB1: 128, 0xB2: 192}[code])
    elif code == 15:
        # large dot (window traffic lights): 7 px across
        r = 3.5 * SS
        dr.ellipse([CX4 - r, cy - r, CX4 + r, cy + r], fill=255)
    elif code == 1:
        # ScratchOS logo: a cat's head
        r = 3.3 * SS
        hy = cy + SS
        dr.ellipse([CX4 - r, hy - r, CX4 + r, hy + r], fill=255)
        dr.polygon([(CX4 - r, hy - 0.2 * r), (CX4 - 0.9 * r, hy - 2.0 * r), (CX4 - 0.1 * r, hy - 0.9 * r)], fill=255)
        dr.polygon([(CX4 + r, hy - 0.2 * r), (CX4 + 0.9 * r, hy - 2.0 * r), (CX4 + 0.1 * r, hy - 0.9 * r)], fill=255)
        e = 0.55 * SS
        for ex in (-1.3 * SS, 1.3 * SS):
            dr.ellipse([CX4 + ex - e, hy - 0.3 * SS - e, CX4 + ex + e, hy - 0.3 * SS + e], fill=0)
    elif code in (3, 4, 5, 6):
        s = 3 * SS
        if code == 3:      # heart
            dr.ellipse([CX4 - s, cy - s, CX4, cy], fill=255)
            dr.ellipse([CX4, cy - s, CX4 + s, cy], fill=255)
            dr.polygon([(CX4 - s, cy - s / 2), (CX4 + s, cy - s / 2), (CX4, cy + s)], fill=255)
        elif code == 4:    # diamond
            dr.polygon([(CX4, cy - s), (CX4 + s * 0.8, cy), (CX4, cy + s), (CX4 - s * 0.8, cy)], fill=255)
        elif code == 5:    # club
            q = s * 0.55
            for dx, dy in ((0, -q), (-q, q * 0.4), (q, q * 0.4)):
                dr.ellipse([CX4 + dx - q, cy + dy - q, CX4 + dx + q, cy + dy + q], fill=255)
            dr.polygon([(CX4, cy), (CX4 - q, cy + s), (CX4 + q, cy + s)], fill=255)
        else:              # spade
            dr.ellipse([CX4 - s, cy - s * 0.3, CX4, cy + s * 0.5], fill=255)
            dr.ellipse([CX4, cy - s * 0.3, CX4 + s, cy + s * 0.5], fill=255)
            dr.polygon([(CX4 - s, cy + s * 0.1), (CX4 + s, cy + s * 0.1), (CX4, cy - s)], fill=255)
            dr.polygon([(CX4, cy), (CX4 - s * 0.5, cy + s), (CX4 + s * 0.5, cy + s)], fill=255)
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
    if m is None and code in BOX:
        m = _box_mask(code)
    if m is None:
        m = _font_mask(code)
    if m is None:
        raise ValueError(f'no glyph for CP437 code {code} in JetBrains Mono')
    return m.resize((16, 32), Image.BOX)


def _coloured(mask, rgb):
    img = Image.new('RGBA', mask.size, rgb + (255,))
    img.putalpha(mask)
    return img


def costumes(kind):
    bases, _ = build_palette()
    glyphs = GLYPHS[kind]
    masks = {code: glyph_mask(code) for code in glyphs}
    out = []
    for k, base in enumerate(bases):
        for code in glyphs:
            name = assets.glyph_name(code) if k == 0 else f's{k}g{code}'
            out.append(assets.make_costume(name, assets.png_bytes(_coloured(masks[code], base)), 'png', 0, 0))
        for i in range(9):
            for j in range(9):
                w, h = 1 << i, 1 << j
                img = Image.new('RGBA', (w * 2, h * 2), base + (255,))
                out.append(assets.make_costume(f's{k}rect_{w}x{h}', assets.png_bytes(img), 'png', 0, 0))
    assert len(out) == len(bases) * set_size(kind)
    return out


if __name__ == '__main__':
    b, e = build_palette()
    print(len(b), 'base sets', b)
    names = (['ansi%d' % i for i in range(16)] + ['d_' + n for n in UI_NAMES] + ['l_' + n for n in UI_NAMES]
             + ['ansid%d' % i for i in range(16)] + ['ansil%d' % i for i in range(16)] + ['wall%d' % i for i in range(WALL_N)])
    for i, (h, ent) in enumerate(zip(palette_hex(), e)):
        print(f"{i:3} {names[i]:10} {h} -> {'%02X%02X%02X' % ent['rgb']} set {ent['set']}")
    for kind in ('ide', 'os'):
        print(kind, len(GLYPHS[kind]), 'glyphs,', len(b) * set_size(kind), 'costumes')
    g = GLYPHS['os']
    sheet = Image.new('RGBA', (16 * 32, 32 * ((len(g) + 31) // 32)), (30, 31, 34, 255))
    for k, code in enumerate(g):
        sheet.alpha_composite(_coloured(glyph_mask(code), (223, 225, 229)), ((k % 32) * 16, (k // 32) * 32))
    sheet.save(os.environ.get('SHEET', '/tmp/ui_glyphs.png'))
