"""
Costume generation for ScratchOS.

All on-screen graphics are drawn with the pen: text is stamped glyph by glyph
from bitmap costumes generated here from the IBM VGA 8x16 ROM font
(assets/font/VGA8.F16, from VileR's collection, the same data as the
Px437 IBM VGA 8x16 font in "The Ultimate Oldschool PC Font Pack", CC BY-SA 4.0).

Colouring uses Scratch graphic effects instead of one costume per colour:
  * glyphs/rects drawn in pure white (#FFFFFF) give the greys via the
    brightness effect (brightness adds a constant to R, G and B);
  * glyphs/rects drawn in dark red (#AA0000) give every chromatic VGA colour
    via the colour (hue) effect, plus brightness +33.3 for the bright variants.
This reproduces the 16-colour VGA palette exactly.

Costume layout of the Kernel sprite (1-based costume numbers):
  1   .. 256   white glyph for CP437 code c is costume c+1, named by its
               Unicode character so `switch costume to (char)` + costume # gives
               a case-sensitive ord() (Scratch's costume lookup is case-sensitive)
  257 .. 512   red glyph for code c is costume c+257
  513 .. 593   white solid rect 2^i x 2^j  -> 513 + i*9 + j
  594 .. 674   red solid rect             -> 594 + i*9 + j
  675          mouse pointer (white body), 676 mouse pointer outline (black/white base)
"""

import hashlib
import io
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(ROOT, 'assets', 'font', 'VGA8.F16')

# Unicode equivalents of CP437 0x00-0x1F and 0x7F (graphic glyphs)
CP437_LOW = ['\u0000', '☺', '☻', '♥', '♦', '♣', '♠', '•', '◘', '○', '◙', '♂', '♀', '♪', '♫', '☼',
             '►', '◄', '↕', '‼', '¶', '§', '▬', '↨', '↑', '↓', '→', '←', '∟', '↔', '▲', '▼']

GLYPH_BASE = 1
RED_GLYPH_BASE = 257
RECT_W_BASE = 513
RECT_R_BASE = 594
CURSOR_COSTUME = 675
CURSOR_MASK_COSTUME = 676

WHITE = (255, 255, 255, 255)
RED = (0xAA, 0, 0, 255)


def cp437_char(code):
    if code < 32:
        return CP437_LOW[code]
    if code == 127:
        return '⌂'
    return bytes([code]).decode('cp437')


def glyph_name(code):
    if code == 0:
        return 'NUL'
    if code == 32:
        return 'SPACE'
    if code == 255:
        return 'NBSP'
    return cp437_char(code)


def unicode_to_cp437_map():
    """Map of unicode char -> cp437 code (for build-time encoding)."""
    m = {}
    for c in range(256):
        m[cp437_char(c)] = c
    m[' '] = 32
    return m


def load_font():
    with open(FONT_PATH, 'rb') as f:
        data = f.read()
    assert len(data) == 4096
    return data


def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def make_costume(name, data, fmt, rcx, rcy, res=2):
    md5 = hashlib.md5(data).hexdigest()
    c = {'name': name, 'dataFormat': fmt, 'assetId': md5, 'md5ext': f'{md5}.{fmt}',
         'rotationCenterX': rcx, 'rotationCenterY': rcy, '_bytes': data}
    if fmt != 'svg':
        c['bitmapResolution'] = res
    return c


def glyph_image(font, code, color):
    img = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
    px = img.load()
    for row in range(16):
        bits = font[code * 16 + row]
        for col in range(8):
            if bits & (0x80 >> col):
                for dy in range(2):
                    for dx in range(2):
                        px[col * 2 + dx, row * 2 + dy] = color
    return img


# Mouse pointer 8x16 ('#' body, 'o' outline)
POINTER = [
    "o.......",
    "oo......",
    "o#o.....",
    "o##o....",
    "o###o...",
    "o####o..",
    "o#####o.",
    "o######o",
    "o####ooo",
    "o#o##o..",
    "oo.o##o.",
    "o..o##o.",
    "....o##o",
    "....o##o",
    ".....oo.",
    "........",
]


def pointer_image(part):
    img = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(POINTER):
        for x, ch in enumerate(row):
            if (part == 'body' and ch == '#') or (part == 'outline' and ch == 'o'):
                for dy in range(2):
                    for dx in range(2):
                        px[x * 2 + dx, y * 2 + dy] = WHITE
    return img


_cache = {}


def costume_group(group):
    """Return list of costume dicts (with _bytes) for a named group."""
    if group in _cache:
        return [dict(c) for c in _cache[group]]
    out = []
    if group == 'glyphs':
        font = load_font()
        for code in range(256):
            out.append(make_costume(glyph_name(code), png_bytes(glyph_image(font, code, WHITE)), 'png', 0, 0))
        for code in range(256):
            out.append(make_costume(f'r{code}', png_bytes(glyph_image(font, code, RED)), 'png', 0, 0))
        for color, prefix in ((WHITE, 'w'), (RED, 'r')):
            for i in range(9):
                for j in range(9):
                    w, h = 1 << i, 1 << j
                    img = Image.new('RGBA', (w * 2, h * 2), color)
                    out.append(make_costume(f'{prefix}rect_{w}x{h}', png_bytes(img), 'png', 0, 0))
        out.append(make_costume('pointer', png_bytes(pointer_image('body')), 'png', 0, 0))
        out.append(make_costume('pointer_outline', png_bytes(pointer_image('outline')), 'png', 0, 0))
        assert len(out) == CURSOR_MASK_COSTUME
    elif group == 'ide_glyphs':
        import ide_assets
        out = ide_assets.costumes()
    elif group == 'backdrop':
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">' \
              b'<rect width="480" height="360" fill="#000000"/></svg>'
        out.append(make_costume('black', svg, 'svg', 240, 180, 1))
    elif group == 'blank':
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2" viewBox="0 0 2 2"></svg>'
        out.append(make_costume('blank', svg, 'svg', 1, 1, 1))
    else:
        raise KeyError(group)
    _cache[group] = out
    return [dict(c) for c in out]
