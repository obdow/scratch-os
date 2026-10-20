#!/usr/bin/env python3
"""
Build ScratchOS.sb3 (and WhiskerIDE.sb3) from source.

    python3 build.py              # writes ScratchOS.sb3
    python3 build.py --ide        # writes WhiskerIDE.sb3 (the stand-alone IDE)
    python3 build.py -o out.sb3   # custom output path
    python3 build.py --w3d w3d          # writes Whisker3D.sb3 (the 3D game engine)
    python3 build.py --w3d player720    # writes Whisker3D-Player-720p.sb3
    python3 build.py --w3d player480    # writes Whisker3D-Player-480x360.sb3

Inputs:
    src/*.sbs      kernel source (SBS build language, compiled by tools/sbc.py)
    src/ide/       the Whisker IDE (an app in ScratchOS, or a project of its own)
    rootfs/        files baked into the ScratchOS file system at boot
    ide/rootfs/    the IDE's files (/projects, /examples, /docs, /lib)
    assets/font/   JetBrains Mono
"""

import argparse
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import assets  # noqa: E402
import ui_assets  # noqa: E402
import natives  # noqa: E402
import osdata  # noqa: E402
import rootfs  # noqa: E402
import sbc  # noqa: E402

TW_CONFIG = {
    'framerate': 60,
    'runtimeOptions': {'maxClones': 300, 'miscLimits': False, 'fencing': False},
    'interpolation': False,
    'turbo': False,
    'hq': False,
}


# custom TurboWarp stage sizes, a whole number of 8x16 text cells each
OS_STAGE = (1280, 720)        # 720p: 160 x 45 cells
IDE_STAGE = (960, 544)        # 120 x 34 cells

# the IDE's files inside ScratchOS (the sort library stays IDE-only)
IDE_FILES = os.path.join(ROOT, 'ide', 'rootfs')
OS_MOUNTS = [
    (os.path.join(IDE_FILES, 'examples'), '/home/user/examples', ['/home/user/examples/sorting.wsk']),
    (os.path.join(IDE_FILES, 'projects'), '/home/user/projects', []),
    (os.path.join(IDE_FILES, 'docs'), '/usr/share/doc/whisker', ['/usr/share/doc/whisker/sort.txt']),
]


def compact_ids(project):
    """Replace the long variable / list / broadcast ids ("Kernel.V.gn_theme")
    by short ones everywhere they appear: the ids are repeated in every
    block that uses them, and Scratch limits project.json to 5 MB."""
    ids = {}

    def short(old):
        if old not in ids:
            n = len(ids)
            out = ''
            while True:
                out = '0123456789abcdefghijklmnopqrstuvwxyz'[n % 36] + out
                n //= 36
                if n == 0:
                    break
            ids[old] = '`' + out
        return ids[old]

    for t in project['targets']:
        for key in ('variables', 'lists', 'broadcasts'):
            t[key] = {short(k): v for k, v in t[key].items()}
    for t in project['targets']:
        for b in t['blocks'].values():
            if isinstance(b, list):          # a top-level reporter: [12, name, id, x, y]
                if len(b) >= 3 and b[0] in (11, 12, 13) and b[2] in ids:
                    b[2] = ids[b[2]]
                continue
            for inp in b.get('inputs', {}).values():
                for x in inp[1:]:
                    if isinstance(x, list) and len(x) >= 3 and x[0] in (11, 12, 13) and x[2] in ids:
                        x[2] = ids[x[2]]
            for f in b.get('fields', {}).values():
                if isinstance(f, list) and len(f) >= 2 and f[1] in ids:
                    f[1] = ids[f[1]]
    for m in project['monitors']:
        if m['id'] in ids:
            m['id'] = ids[m['id']]


def monitors_for(targets, sw, sh):
    """Visible list monitors: stage lists whose name starts with a capital
    letter and that SBS marks with `global list ... = [] ` + a monitor
    request in build data (see W3D_MONITORS)."""
    out = []
    stage = targets[0]
    for vid, (name, _items) in stage['lists'].items():
        if name in W3D_MONITORS:
            x, y, w, h, visible = W3D_MONITORS[name](sw, sh)
            out.append({'id': vid, 'mode': 'list', 'opcode': 'data_listcontents',
                        'params': {'LIST': name}, 'spriteName': None, 'value': [],
                        'width': w, 'height': h, 'x': x, 'y': y, 'visible': visible})
    return out


# list monitors the players show so a game .txt can be imported into them
W3D_MONITORS = {
    'game': lambda sw, sh: (sw // 2 - 150, 40, 300, sh - 120, True),
}


def backdrop_svg(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" fill="#000000"/></svg>').encode()


# Whisker 3D: the engine (an IDE + scene editor, 1280x720) and the two game
# players (1280x720 for TurboWarp, 480x360 for scratch.mit.edu)
W3D_FILES = os.path.join(ROOT, 'w3d', 'rootfs')
W3D_PLAYER_FILES = os.path.join(ROOT, 'w3d', 'player_rootfs')
W3D_TARGETS = {
    'w3d': ('Whisker3D.sb3', (1280, 720), 0),
    'player720': ('Whisker3D-Player-720p.sb3', (1280, 720), 1),
    'player480': ('Whisker3D-Player-480x360.sb3', (480, 360), 1),
}


def build(main, out, rootfs_dir=None, ide=False, target=None):
    kind = 'ide' if (ide or target) else 'os'
    if target:
        data = rootfs.build_data(rootfs_dir or (W3D_FILES if target == 'w3d' else W3D_PLAYER_FILES))
    elif ide:
        data = rootfs.build_data(rootfs_dir or IDE_FILES)
    else:
        data = rootfs.build_data(rootfs_dir or os.path.join(ROOT, 'rootfs'), OS_MOUNTS)
    data.update(osdata.build_data())
    data.update(natives.build_data())
    data.update(ui_assets.build_data(kind))
    import w3d_sounds
    data.update(w3d_sounds.build_data())
    prog = sbc.Program(data)
    # Constants made available to SBS source
    prog.consts.update(ui_assets.layout(kind))
    prog.consts.update(ui_assets.ui_consts())
    prog.consts.update({'IDE_HOSTED': 0 if (ide or target) else 1})
    sw, sh = IDE_STAGE if ide else OS_STAGE
    player = 1 if (target and W3D_TARGETS[target][2]) else 0
    prog.consts.update({'HAS_WM': 1 - player, 'HAS_NET': 1 - player, 'HAS_COMPILER': 1 - player,
                        'W3D_PLAYER': player, 'W3D_ENGINE': 1 if target == 'w3d' else 0})
    if target:
        sw, sh = W3D_TARGETS[target][1]
    prog.consts.update({'SCR_W': sw, 'SCR_H': sh, 'SCR_COLS': sw // 8, 'SCR_ROWS': sh // 16})
    prog.consts.update(data.get('_consts', {}))
    prog.consts.update(data['_native_consts'])
    prog.load(main)
    def costume_group(group):
        if group == 'backdrop':
            return [assets.make_costume('black', backdrop_svg(sw, sh), 'svg', sw // 2, sh // 2, 1)]
        return assets.costume_group(group)
    targets, asset_bytes = prog.build_targets(costume_group, assets.sound_group)
    # drop custom blocks this build never runs, and variables / lists nothing
    # uses (the test harness reads kb_ready and frames)
    pruned = sbc.prune_unused(targets, keep={'kb_ready', 'frames', 'w3_stats', 'g_trace', 'w3e_testcmd'})
    if os.environ.get('SBC_PRUNED'):
        with open(os.environ['SBC_PRUNED'], 'w') as f:
            f.write('\n'.join(sorted(pruned['names'])) + '\n')
    stage = targets[0]
    cfg_text = ("Configuration for https://turbowarp.org/\n"
                "You can move, resize, and minimize this comment, but don't edit it by hand. "
                "This comment can be deleted to remove the stored settings.\n"
                + json.dumps(dict(TW_CONFIG, width=sw, height=sh)) + " // _twconfig_")
    stage['comments']['twconfig'] = {'blockId': None, 'x': 0, 'y': 0, 'width': 350, 'height': 170,
                                     'minimized': False, 'text': cfg_text}
    exts = ['pen']
    if '"music_' in json.dumps(targets):
        exts.append('music')
    project = {
        'targets': targets,
        'monitors': monitors_for(targets, sw, sh),
        'extensions': exts,
        'meta': {'semver': '3.0.0', 'vm': '0.2.0', 'agent': 'ScratchOS build.py',
                 'platform': {'name': 'TurboWarp', 'url': 'https://turbowarp.org/'}},
    }
    compact_ids(project)
    pj = json.dumps(project, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('project.json', pj)
        for name, b in sorted(asset_bytes.items()):
            z.writestr(name, b)
    nblocks = sbc.count_blocks(targets)
    print(f"wrote {out}: {nblocks} blocks, {len(asset_bytes)} assets, project.json {len(pj)//1024} KiB"
          f" (pruned {pruned['procs']} unused procs, {pruned['vars']} variables, {pruned['lists']} lists)")
    return project


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--main', default=os.path.join(ROOT, 'src', 'main.sbs'))
    ap.add_argument('-o', '--out', default=os.path.join(ROOT, 'ScratchOS.sb3'))
    ap.add_argument('--rootfs', default=None, help='directory baked into the file system')
    ap.add_argument('--ide', action='store_true', help='build the Whisker IDE (WhiskerIDE.sb3)')
    ap.add_argument('--w3d', choices=sorted(W3D_TARGETS),
                    help='build Whisker 3D: the engine (w3d) or a game player (player720, player480)')
    a = ap.parse_args()
    try:
        if a.w3d:
            entry = 'main.sbs' if a.w3d == 'w3d' else 'player.sbs'
            out = a.out if a.out != os.path.join(ROOT, 'ScratchOS.sb3') else os.path.join(ROOT, W3D_TARGETS[a.w3d][0])
            build(os.path.join(ROOT, 'src', 'w3d', entry), out, a.rootfs, target=a.w3d)
        elif a.ide:
            build(os.path.join(ROOT, 'src', 'ide', 'main.sbs'),
                  a.out if a.out != os.path.join(ROOT, 'ScratchOS.sb3') else os.path.join(ROOT, 'WhiskerIDE.sb3'),
                  a.rootfs, ide=True)
        else:
            build(a.main, a.out, a.rootfs)
    except sbc.CompileError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
