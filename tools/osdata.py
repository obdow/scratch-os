"""Static data tables baked into the project (keyboard map, CP437 tables)."""

import assets

# Keys the keyboard clones listen for.  Scratch reports printable keys as
# the produced character (uppercased), so shifted symbols are separate keys.
PUNCT = "`~!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?"
SPECIAL = ['space', 'enter', 'backspace', 'delete', 'left arrow', 'right arrow', 'up arrow',
           'down arrow', 'home', 'end', 'page up', 'page down', 'escape', 'insert', 'caps lock']


def keyboard_tables():
    keys, outs, kinds = [], [], []
    for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        keys.append(c)
        outs.append(c.lower())
        kinds.append(1)          # letter: shift/caps give uppercase
    for c in '0123456789' + PUNCT:
        keys.append(c)
        outs.append(c)
        kinds.append(2)          # symbol: produced char is final
    for k in SPECIAL:
        keys.append(k)
        outs.append(' ' if k == 'space' else k)
        kinds.append(3 if k != 'space' else 2)
    return keys, outs, kinds


def cp437_tables():
    chars = []
    for code in range(256):
        if code == 0:
            chars.append('')
        elif code == 32:
            chars.append(' ')
        elif code in (7, 8, 9, 10, 13, 27):
            chars.append(chr(code))   # control characters keep their ASCII meaning
        else:
            chars.append(assets.cp437_char(code))
    to_code = {ch: i for i, ch in enumerate(chars) if ch}
    upper, lower = [], []
    for code in range(256):
        ch = chars[code]
        u = ch.upper() if ch else ch
        l = ch.lower() if ch else ch
        upper.append(to_code.get(u, code) if len(u) == 1 else code)
        lower.append(to_code.get(l, code) if len(l) == 1 else code)
    # character classes for the Whisker lexer: 0 other, 1 ident start, 2 digit,
    # 3 space, 4 newline, 5 quote
    cls = []
    for code in range(256):
        ch = chars[code]
        if ch in ('\n',) or code == 10:
            cls.append(4)
        elif code in (9, 13) or ch == ' ':
            cls.append(3)
        elif ch.isdigit() and code < 128:
            cls.append(2)
        elif (ch.isalpha() and code < 128) or ch == '_':
            cls.append(1)
        elif ch in ('"', "'"):
            cls.append(5)
        else:
            cls.append(0)
    return chars, upper, lower, cls


def build_data():
    keys, outs, kinds = keyboard_tables()
    chars, upper, lower, cls = cp437_tables()
    return {
        'kb_keys': keys, 'kb_out': outs, 'kb_kind': kinds,
        'cp437': chars, 'upper': upper, 'lower': lower, 'char_class': cls,
        'glyph_code': list(range(256)),     # ScratchOS: glyph costume c+1 is code c
    }
