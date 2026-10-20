#!/usr/bin/env python3
"""
Whisker 3D project bundles (the .txt a project is exported to).

    python3 tools/w3d_bundle.py pack DIR [OUT.txt]     # a project folder -> bundle
    python3 tools/w3d_bundle.py unpack IN.txt DIR      # bundle -> folder

Format (one list item per line):
    WHISKER3D 1
    name <project name>
    @file <path> <number of lines>
    ...that many lines...
    @end

Scratch imports a list file as CSV, so each line is escaped: "~" ~~, "," ~c,
";" ~s, "|" ~p, tab ~t, '"' ~q, and an empty line is "~0".
"""

import os
import sys


ESC = {'~': '~~', ',': '~c', ';': '~s', '|': '~p', '\t': '~t', '"': '~q'}
UNESC = {'~': '~', 'c': ',', 's': ';', 'p': '|', 't': '\t', 'q': '"', '0': ''}


def esc(line):
    if line == '':
        return '~0'
    return ''.join(ESC.get(ch, ch) for ch in line)


def unesc(line):
    if line == '~0':
        return ''
    out = []
    i = 0
    while i < len(line):
        if line[i] == '~' and i + 1 < len(line):
            out.append(UNESC.get(line[i + 1], line[i + 1]))
            i += 2
        else:
            out.append(line[i])
            i += 1
    return ''.join(out)


def project_name(d):
    try:
        for line in open(os.path.join(d, 'game.w3d'), encoding='utf-8'):
            if line.startswith('name '):
                return line[5:].strip()
    except OSError:
        pass
    return os.path.basename(os.path.abspath(d))


def pack(d):
    lines = ['WHISKER3D 1', esc('name ' + project_name(d))]
    for root, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if not x.startswith('.'))
        for f in sorted(files):
            if f.startswith('.'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, d).replace(os.sep, '/')
            text = open(path, encoding='utf-8').read()
            if text.endswith('\n'):
                text = text[:-1]
            body = text.split('\n') if text else []
            lines.append(f'@file {rel} {len(body)}')
            lines.extend(esc(x) for x in body)
    lines.append('@end')
    return lines


def unpack(lines, d):
    if not lines or not lines[0].startswith('WHISKER3D'):
        raise ValueError('not a Whisker 3D bundle')
    lines = [unesc(x) for x in lines]
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.startswith('@file '):
            _, path, n = line.split(' ')
            n = int(n)
            out = os.path.join(d, *path.split('/'))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'w', encoding='utf-8') as f:
                f.write(''.join(x + '\n' for x in lines[i + 1:i + 1 + n]))
            i += n + 1
        else:
            i += 1


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'pack':
        out = '\n'.join(pack(sys.argv[2])) + '\n'
        if len(sys.argv) > 3:
            open(sys.argv[3], 'w', encoding='utf-8').write(out)
        else:
            sys.stdout.write(out)
    elif len(sys.argv) == 4 and sys.argv[1] == 'unpack':
        unpack(open(sys.argv[2], encoding='utf-8').read().rstrip('\n').split('\n'), sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
