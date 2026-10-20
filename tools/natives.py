"""
Native functions (system calls) available to Whisker programs.

The order defines the native id (1-based).  build.py exports:
  * list data "nat_names"  - names looked up by the compiler
  * const N_<NAME>          - ids used by the kernel's dispatch switch
    (dots become underscores: "fs.read" -> N_FS_READ)
"""

NATIVES = [
    # base library
    'print', 'tostring', 'tonumber', 'type', 'error', 'pcall', 'assert', 'select', 'rawequal',
    'unpack', 'sleep', 'exit', 'load', 'require',
    # string
    'string.len', 'string.sub', 'string.upper', 'string.lower', 'string.find', 'string.rep',
    'string.byte', 'string.char', 'string.format', 'string.split', 'string.trim', 'string.reverse',
    'string.startswith', 'string.endswith', 'string.replace', 'string.lines', 'string.pad',
    'string.contains',
    # math
    'math.floor', 'math.ceil', 'math.abs', 'math.sqrt', 'math.sin', 'math.cos', 'math.tan',
    'math.atan', 'math.atan2', 'math.exp', 'math.log', 'math.random', 'math.max', 'math.min',
    'math.fmod', 'math.round', 'math.tointeger', 'math.asin', 'math.acos', 'math.pow',
    # table
    'table.insert', 'table.remove', 'table.concat', 'table.sort', 'table.unpack', 'table.keys',
    'table.count', 'table.copy', 'table.find', 'table.reverse',
    # io (standard streams)
    'io.write', 'io.read', 'io.readall', 'io.lines', 'io.error', 'io.isatty',
    # os
    'os.time', 'os.clock', 'os.date', 'os.getenv', 'os.setenv', 'os.exit', 'os.sleep', 'os.pid',
    'os.args', 'os.uptime', 'os.millis',
    # file system
    'fs.read', 'fs.write', 'fs.append', 'fs.list', 'fs.exists', 'fs.isdir', 'fs.mkdir', 'fs.remove',
    'fs.rename', 'fs.copy', 'fs.stat', 'fs.cwd', 'fs.chdir', 'fs.abs', 'fs.name', 'fs.dir',
    # processes
    'proc.spawn', 'proc.wait', 'proc.kill', 'proc.list', 'proc.pid', 'proc.alive', 'proc.run',
    # terminal
    'term.clear', 'term.color', 'term.goto', 'term.size', 'term.raw', 'term.getkey',
    'term.waitkey', 'term.cursor', 'term.put', 'term.write', 'term.getpos',
    # windows / graphics
    'gui.window', 'gui.close', 'gui.event', 'gui.waitevent', 'gui.size', 'gui.title',
    'gui.active', 'gui.terminal', 'gui.color', 'gui.ide', 'gui.launch', 'gui.track', 'gui.appearance', 'gui.wallpaper',
    'gui.apps', 'gui.pinned', 'gui.clipboard',
    'gfx.clear', 'gfx.pixel', 'gfx.line', 'gfx.rect', 'gfx.fill', 'gfx.circle', 'gfx.text',
    'gfx.batch', 'gfx.flush', 'gfx.disc', 'gfx.poly', 'gfx.rgb', 'gfx.hex', 'gfx.torgb', 'gfx.image',
    # images and the .simg format (image.sbs)
    'image.new', 'image.load', 'image.save', 'image.decode', 'image.encode', 'image.size',
    'image.get', 'image.set', 'image.fill', 'image.rect', 'image.line', 'image.circle',
    'image.disc', 'image.copy', 'image.rotate', 'image.flip', 'image.colors',
    # system
    'sys.version', 'sys.uptime', 'sys.mem', 'sys.shutdown', 'sys.reboot', 'sys.caps',
    'sys.hostname', 'sys.gc', 'sys.request', 'sys.procs', 'sys.date',
    # the network, over cloud variables (net.sbs)
    'net.status', 'net.ping', 'net.get', 'net.put', 'net.list', 'net.id',
    # Whisker 3D (src/w3d/natives3d.sbs); keep these last: everything from
    # 'w3d.find' on is dispatched to nat_w3d (a stub outside Whisker 3D)
    # -- objects and scenes
    'w3d.find', 'w3d.objects', 'w3d.spawn', 'w3d.destroy', 'w3d.alive', 'w3d.instances',
    'w3d.frame', 'w3d.message', 'w3d.broadcast', 'w3d.send', 'w3d.contacts',
    'w3d.pos', 'w3d.setpos', 'w3d.move', 'w3d.moverel', 'w3d.rot', 'w3d.setrot', 'w3d.rotate',
    'w3d.scale', 'w3d.setscale', 'w3d.color', 'w3d.setcolor', 'w3d.alpha', 'w3d.setalpha',
    'w3d.visible', 'w3d.show', 'w3d.name', 'w3d.tag', 'w3d.settag', 'w3d.forward', 'w3d.right',
    'w3d.lookat', 'w3d.distance', 'w3d.setmesh', 'w3d.mesh',
    # -- physics
    'w3d.velocity', 'w3d.setvelocity', 'w3d.push', 'w3d.grounded', 'w3d.touching',
    'w3d.body', 'w3d.setbody', 'w3d.gravity', 'w3d.raycast',
    # -- camera, lights, environment
    'w3d.camera', 'w3d.fov', 'w3d.sky', 'w3d.fog', 'w3d.ambient', 'w3d.sun', 'w3d.light',
    # -- screen, HUD, time, scenes, shared values
    'w3d.screen', 'w3d.text', 'w3d.rect', 'w3d.line', 'w3d.project',
    'w3d.time', 'w3d.fps', 'w3d.load', 'w3d.scene', 'w3d.quit', 'w3d.set', 'w3d.get',
    # -- input
    'input.key', 'input.pressed', 'input.released', 'input.mouse', 'input.mousedown',
    'input.clicked', 'input.axis',
    # -- sound
    'sound.play', 'sound.stop', 'sound.list', 'sound.note', 'sound.drum', 'sound.rest',
    'sound.tempo', 'sound.volume',
    # -- added later (keep appending here)
    'w3d.screenray',
]


def const_name(n):
    return 'N_' + n.replace('.', '_').upper()


def build_data():
    return {
        'nat_names': list(NATIVES),
        '_native_consts': {const_name(n): i + 1 for i, n in enumerate(NATIVES)},
    }
