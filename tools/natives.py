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
    'gui.active', 'gui.terminal', 'gui.color', 'gui.ide',
    'gfx.clear', 'gfx.pixel', 'gfx.line', 'gfx.rect', 'gfx.fill', 'gfx.circle', 'gfx.text',
    'gfx.batch', 'gfx.flush', 'gfx.disc', 'gfx.poly',
    # system
    'sys.version', 'sys.uptime', 'sys.mem', 'sys.shutdown', 'sys.reboot', 'sys.caps',
    'sys.hostname', 'sys.gc', 'sys.request', 'sys.procs', 'sys.date',
]


def const_name(n):
    return 'N_' + n.replace('.', '_').upper()


def build_data():
    return {
        'nat_names': list(NATIVES),
        '_native_consts': {const_name(n): i + 1 for i, n in enumerate(NATIVES)},
    }
