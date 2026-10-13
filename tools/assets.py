"""
Costume helpers for ScratchOS and the Whisker IDE.

The glyph and colour costumes themselves come from tools/ui_assets.py
(JetBrains Mono, modern palette); this module holds the CP437 tables, PNG /
costume helpers and the small fixed costume groups.
"""

import hashlib
import io
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Unicode equivalents of CP437 0x00-0x1F and 0x7F (graphic glyphs)
CP437_LOW = ['\u0000', '☺', '☻', '♥', '♦', '♣', '♠', '•', '◘', '○', '◙', '♂', '♀', '♪', '♫', '☼',
             '►', '◄', '↕', '‼', '¶', '§', '▬', '↨', '↑', '↓', '→', '←', '∟', '↔', '▲', '▼']

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


_cache = {}


def costume_group(group):
    """Return list of costume dicts (with _bytes) for a named group."""
    if group in _cache:
        return [dict(c) for c in _cache[group]]
    out = []
    if group in ('ide_glyphs', 'os_glyphs'):
        import ui_assets
        out = ui_assets.costumes(group[:-7])
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
