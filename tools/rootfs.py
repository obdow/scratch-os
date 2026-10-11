"""
Bake the rootfs/ directory into list data for the kernel.

At boot the kernel walks these lists and creates the in-memory file system
(directories first, then files), so the disk image is rebuilt every boot.
"""

import os


def build_data(root):
    paths, types, contents = [], [], []
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            rel = os.path.relpath(dirpath, root)
            vpath = '/' if rel == '.' else '/' + rel.replace(os.sep, '/')
            if vpath != '/':
                paths.append(vpath)
                types.append('d')
                contents.append('')
            for fn in sorted(filenames):
                if fn.startswith('.') and fn != '.profile':
                    continue
                full = os.path.join(dirpath, fn)
                with open(full, encoding='utf-8') as f:
                    text = f.read()
                paths.append((vpath.rstrip('/') + '/' + fn))
                types.append('f')
                contents.append(text)
    # directories that must exist even when empty (git does not store them)
    for d in ('/tmp', '/home/user', '/home/user/projects'):
        if d not in paths:
            paths.insert(0 if d == '/tmp' else len(paths), d)
            types.insert(0 if d == '/tmp' else len(types), 'd')
            contents.insert(0 if d == '/tmp' else len(contents), '')
    return {
        'rootfs_paths': paths,
        'rootfs_types': types,
        'rootfs_data': contents,
        '_consts': {},
    }
