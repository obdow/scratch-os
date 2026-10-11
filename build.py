#!/usr/bin/env python3
"""
Build ScratchOS.sb3 from source.

    python3 build.py              # writes ScratchOS.sb3
    python3 build.py -o out.sb3   # custom output path
    python3 build.py --main src/test_text.sbs   # build an alternative entry file

Inputs:
    src/*.sbs      kernel source (SBS build language, compiled by tools/sbc.py)
    rootfs/        files baked into the in-memory file system at boot
    assets/font/   IBM VGA 8x16 font (ScratchOS), JetBrains Mono (Whisker IDE)
"""

import argparse
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import assets  # noqa: E402
import ide_assets  # noqa: E402
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
    'width': 480,
    'height': 360,
}


def build(main, out, rootfs_dir=None, ide=False):
    data = rootfs.build_data(rootfs_dir or os.path.join(ROOT, 'rootfs'))
    data.update(osdata.build_data())
    data.update(natives.build_data())
    if ide:
        data.update(ide_assets.build_data())
    prog = sbc.Program(data)
    # Constants made available to SBS source
    if ide:
        prog.consts.update(ide_assets.layout())
        prog.consts.update(ide_assets.ui_consts())
    else:
        prog.consts.update({
            'GLYPH_BASE': assets.GLYPH_BASE,
            'RED_GLYPH_BASE': assets.RED_GLYPH_BASE,
            'RECT_W_BASE': assets.RECT_W_BASE,
            'RECT_R_BASE': assets.RECT_R_BASE,
            'CURSOR_COSTUME': assets.CURSOR_COSTUME,
            'CURSOR_MASK_COSTUME': assets.CURSOR_MASK_COSTUME,
            'ORD_SENTINEL': assets.GLYPH_BASE + ord('?'),
        })
    prog.consts.update(data.get('_consts', {}))
    prog.consts.update(data['_native_consts'])
    prog.load(main)
    targets, asset_bytes = prog.build_targets(assets.costume_group)
    stage = targets[0]
    cfg_text = ("Configuration for https://turbowarp.org/\n"
                "You can move, resize, and minimize this comment, but don't edit it by hand. "
                "This comment can be deleted to remove the stored settings.\n"
                + json.dumps(dict(TW_CONFIG, hq=True) if ide else TW_CONFIG) + " // _twconfig_")
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
    print(f"wrote {out}: {nblocks} blocks, {len(asset_bytes)} assets, project.json {len(pj)//1024} KiB")
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
                  a.rootfs or os.path.join(ROOT, 'ide', 'rootfs'), ide=True)
        else:
            build(a.main, a.out, a.rootfs)
    except sbc.CompileError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
