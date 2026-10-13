#!/usr/bin/env python3
"""
Build ScratchOS.sb3 (and WhiskerIDE.sb3) from source.

    python3 build.py              # writes ScratchOS.sb3
    python3 build.py --ide        # writes WhiskerIDE.sb3 (the stand-alone IDE)
    python3 build.py -o out.sb3   # custom output path

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


def backdrop_svg(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" fill="#000000"/></svg>').encode()


def build(main, out, rootfs_dir=None, ide=False):
    kind = 'ide' if ide else 'os'
    if ide:
        data = rootfs.build_data(rootfs_dir or IDE_FILES)
    else:
        data = rootfs.build_data(rootfs_dir or os.path.join(ROOT, 'rootfs'), OS_MOUNTS)
    data.update(osdata.build_data())
    data.update(natives.build_data())
    data.update(ui_assets.build_data(kind))
    prog = sbc.Program(data)
    # Constants made available to SBS source
    prog.consts.update(ui_assets.layout(kind))
    prog.consts.update(ui_assets.ui_consts())
    prog.consts.update({'IDE_HOSTED': 0 if ide else 1})
    sw, sh = IDE_STAGE if ide else OS_STAGE
    prog.consts.update({'SCR_W': sw, 'SCR_H': sh, 'SCR_COLS': sw // 8, 'SCR_ROWS': sh // 16})
    prog.consts.update(data.get('_consts', {}))
    prog.consts.update(data['_native_consts'])
    prog.load(main)
    def costume_group(group):
        if group == 'backdrop':
            return [assets.make_costume('black', backdrop_svg(sw, sh), 'svg', sw // 2, sh // 2, 1)]
        return assets.costume_group(group)
    targets, asset_bytes = prog.build_targets(costume_group)
    # drop custom blocks this build never runs, and variables / lists nothing
    # uses (the test harness reads kb_ready and frames)
    pruned = sbc.prune_unused(targets, keep={'kb_ready', 'frames'})
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
    project = {
        'targets': targets,
        'monitors': [],
        'extensions': ['pen'],
        'meta': {'semver': '3.0.0', 'vm': '0.2.0', 'agent': 'ScratchOS build.py',
                 'platform': {'name': 'TurboWarp', 'url': 'https://turbowarp.org/'}},
    }
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
    a = ap.parse_args()
    try:
        if a.ide:
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
