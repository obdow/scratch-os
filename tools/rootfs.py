"""
Bake the rootfs/ directory into list data for the kernel.

At boot the kernel walks these lists and creates the in-memory file system
(directories first, then files), so the disk image is rebuilt every boot.
"""

import os


def _walk(root, prefix, exclude, paths, types, contents):
    """Add the tree under directory `root` at virtual path `prefix`."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel = os.path.relpath(dirpath, root)
        vpath = prefix if rel == '.' else prefix.rstrip('/') + '/' + rel.replace(os.sep, '/')
        if vpath != '/' and vpath not in paths:
            # parent directories first
            parts = vpath.strip('/').split('/')
            for k in range(1, len(parts)):
                d = '/' + '/'.join(parts[:k])
                if d not in paths:
                    paths.append(d); types.append('d'); contents.append('')
            paths.append(vpath)
            types.append('d')
            contents.append('')
        for fn in sorted(filenames):
            if fn.startswith('.') and fn != '.profile':
                continue
            vp = vpath.rstrip('/') + '/' + fn
            if vp in exclude:
                continue
            with open(os.path.join(dirpath, fn), encoding='utf-8') as f:
                text = f.read()
            paths.append(vp)
            types.append('f')
            contents.append(text)


def build_data(root, mounts=()):
    """root: directory baked in at /.  mounts: (directory, virtual path,
    excluded virtual paths) triples added on top (e.g. the IDE's examples
    inside ScratchOS)."""
    paths, types, contents = [], [], []
    if os.path.isdir(root):
        _walk(root, '/', set(), paths, types, contents)
    for d, prefix, exclude in mounts:
        _walk(d, prefix, set(exclude), paths, types, contents)
    # directories that must exist even when empty (git does not store them)
    for d in ('/tmp', '/dev', '/home/user', '/home/user/projects'):
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
