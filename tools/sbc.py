"""
sbc - Scratch Build Compiler.

Compiles SBS ("Scratch Build Source"), a small C-like language, into
Scratch 3 block JSON.  The OS kernel is written in SBS because hand-placing
tens of thousands of blocks is not practical; the output is still ordinary,
editable Scratch blocks.

Language summary (see docs/SBS.md for the full reference):

    const NAME = 42;
    global counter = 0;            // stage variable
    global list queue;             // stage list
    sprite Kernel {
        costumes "os_glyphs";      // costume groups supplied by build.py
        var x = 0;                 // sprite variable
        list buf = data("key");    // list initialised from build data
        proc add2(a, b) { return a + b; }        // warp custom block
        proc fib(n) recursive { if (n < 2) { return n; } return fib(n-1) + fib(n-2); }
        on flag { forever { tick(); } }
    }

Procedures return values through a hidden `_r` variable; calls used inside
expressions are hoisted into statements automatically.  `local` variables in
`recursive` procedures are saved/restored on a stack list so recursion works.
"""

import json
import os
import re


class CompileError(Exception):
    pass


# --------------------------------------------------------------------------
# Lexer
# --------------------------------------------------------------------------

TOKEN_RE = re.compile(r"""
    (?P<ws>[ \t\r\n]+)
  | (?P<lc>//[^\n]*)
  | (?P<bc>/\*.*?\*/)
  | (?P<num>0x[0-9a-fA-F]+|\d+\.\d*|\.\d+|\d+(?:[eE][-+]?\d+)?)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\.\.=|\+\+|--|\+=|-=|\*=|/=|%=|==|!=|<=|>=|&&|\|\||\.\.|[-+*/%<>=!(){}\[\],;:?.])
""", re.S | re.X)


def unescape(s, fname, line):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c != '\\':
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= len(s):
            raise CompileError(f"{fname}:{line}: bad escape")
        c = s[i]
        simple = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'", '0': '\0', 'e': '\x1b'}
        if c in simple:
            out.append(simple[c])
            i += 1
        elif c == 'x':
            out.append(chr(int(s[i + 1:i + 3], 16)))
            i += 3
        elif c == 'u':
            if s[i + 1] == '{':
                j = s.index('}', i)
                out.append(chr(int(s[i + 2:j], 16)))
                i = j + 1
            else:
                out.append(chr(int(s[i + 1:i + 5], 16)))
                i += 5
        else:
            raise CompileError(f"{fname}:{line}: unknown escape \\{c}")
    return ''.join(out)


class Tok:
    __slots__ = ('kind', 'val', 'line', 'file')

    def __init__(self, kind, val, line, file):
        self.kind, self.val, self.line, self.file = kind, val, line, file

    def __repr__(self):
        return f"Tok({self.kind},{self.val!r},{self.file}:{self.line})"


def lex(src, fname):
    toks = []
    pos = 0
    line = 1
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise CompileError(f"{fname}:{line}: unexpected character {src[pos]!r}")
        kind = m.lastgroup
        text = m.group(kind)
        if kind == 'num':
            if text.startswith('0x'):
                v = int(text, 16)
            elif re.fullmatch(r'\d+', text):
                v = int(text)
            else:
                v = float(text)
            toks.append(Tok('num', v, line, fname))
        elif kind == 'str':
            toks.append(Tok('str', unescape(text[1:-1], fname, line), line, fname))
        elif kind == 'id':
            toks.append(Tok('id', text, line, fname))
        elif kind == 'op':
            toks.append(Tok('op', text, line, fname))
        line += text.count('\n')
        pos = m.end()
    toks.append(Tok('eof', None, line, fname))
    return toks


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------

class Node:
    def __init__(self, kind, *args, line=None):
        self.kind = kind
        self.a = list(args)
        self.line = line

    def __repr__(self):
        return f"{self.kind}{self.a}"


def N(kind, *args, tok=None):
    n = Node(kind, *args)
    if tok is not None:
        n.line = f"{tok.file}:{tok.line}"
    return n


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

BINOP_PREC = [
    ['||'],
    ['&&'],
    ['==', '!='],
    ['<', '>', '<=', '>='],
    ['..'],
    ['+', '-'],
    ['*', '/', '%'],
]


class Parser:
    def __init__(self, toks, consts, loader):
        self.t = toks
        self.i = 0
        self.consts = consts
        self.loader = loader

    # token helpers
    @property
    def cur(self):
        return self.t[self.i]

    def peek(self, k=1):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def err(self, msg, tok=None):
        tok = tok or self.cur
        raise CompileError(f"{tok.file}:{tok.line}: {msg} (at {tok.val!r})")

    def is_op(self, v):
        return self.cur.kind == 'op' and self.cur.val == v

    def is_kw(self, v):
        return self.cur.kind == 'id' and self.cur.val == v

    def eat_op(self, v):
        if not self.is_op(v):
            self.err(f"expected '{v}'")
        self.i += 1

    def eat_kw(self, v):
        if not self.is_kw(v):
            self.err(f"expected '{v}'")
        self.i += 1

    def ident(self):
        if self.cur.kind != 'id':
            self.err("expected identifier")
        v = self.cur.val
        self.i += 1
        return v

    # top level ---------------------------------------------------------
    def parse_program(self, prog):
        while self.cur.kind != 'eof':
            self.parse_top(prog)

    def parse_top(self, prog):
        tok = self.cur
        if self.is_kw('const'):
            self.parse_const()
        elif self.is_kw('include'):
            self.i += 1
            path = self.cur.val
            self.i += 1
            self.eat_op(';')
            self.loader(path, tok.file, prog, members=False)
        elif self.is_kw('global'):
            self.i += 1
            # `global cloud NAME;` declares a cloud variable (shown as "☁ NAME")
            cloud = self.cur.kind == 'id' and self.cur.val == 'cloud' and self.peek().kind == 'id'
            if cloud:
                self.i += 1
            d = self.parse_vardecl(tok)
            d['cloud'] = cloud
            prog['globals'].append(d)
        elif self.is_kw('sprite') or self.is_kw('stage'):
            is_stage = self.cur.val == 'stage'
            self.i += 1
            name = 'Stage' if is_stage else self.ident()
            spr = prog['sprites'].setdefault(name, {
                'name': name, 'stage': is_stage, 'vars': [], 'procs': [],
                'hats': [], 'costumes': [], 'props': {}})
            self.eat_op('{')
            while not self.is_op('}'):
                self.parse_member(spr)
            self.eat_op('}')
        else:
            self.err("expected top-level declaration")

    def parse_const(self):
        self.eat_kw('const')
        name = self.ident()
        self.eat_op('=')
        e = self.parse_expr()
        v = self.fold(e)
        if v is None:
            self.err(f"const {name} must be a constant expression")
        self.consts[name] = v
        self.eat_op(';')

    def fold(self, e):
        """Return python value of constant expression or None."""
        if e.kind == 'num':
            return e.a[0]
        if e.kind == 'str':
            return e.a[0]
        if e.kind == 'un' and e.a[0] == '-':
            v = self.fold(e.a[1])
            return -v if isinstance(v, (int, float)) else None
        if e.kind == 'bin':
            a, b = self.fold(e.a[1]), self.fold(e.a[2])
            if a is None or b is None:
                return None
            op = e.a[0]
            if op == '..':
                return fmt_lit(a) + fmt_lit(b)
            if isinstance(a, str) or isinstance(b, str):
                return None
            if op == '+': return a + b
            if op == '-': return a - b
            if op == '*': return a * b
            if op == '/' and b != 0:
                r = a / b
                return int(r) if r == int(r) else r
            if op == '%' and b != 0: return a % b
            if op == '==': return 1 if a == b else 0
            if op == '!=': return 1 if a != b else 0
            if op == '<': return 1 if a < b else 0
            if op == '>': return 1 if a > b else 0
            if op == '<=': return 1 if a <= b else 0
            if op == '>=': return 1 if a >= b else 0
            if op == '&&': return 1 if (a and b) else 0
            if op == '||': return 1 if (a or b) else 0
        return None

    def parse_vardecl(self, tok):
        is_list = False
        if self.is_kw('list'):
            is_list = True
            self.i += 1
        name = self.ident()
        init = None
        if self.is_op('='):
            self.i += 1
            if is_list:
                if self.is_op('['):
                    self.i += 1
                    init = []
                    while not self.is_op(']'):
                        e = self.parse_expr()
                        v = self.fold(e)
                        if v is None:
                            self.err("list initialiser must be constant")
                        init.append(v)
                        if self.is_op(','):
                            self.i += 1
                    self.eat_op(']')
                elif self.is_kw('data'):
                    self.i += 1
                    self.eat_op('(')
                    key = self.cur.val
                    self.i += 1
                    self.eat_op(')')
                    init = ('data', key)
                else:
                    self.err("expected list initialiser")
            else:
                e = self.parse_expr()
                init = self.fold(e)
                if init is None:
                    self.err("variable initialiser must be constant")
        self.eat_op(';')
        return {'name': name, 'list': is_list, 'init': init, 'line': f"{tok.file}:{tok.line}"}

    def parse_member(self, spr):
        tok = self.cur
        if self.is_kw('include'):
            self.i += 1
            path = self.cur.val
            self.i += 1
            self.eat_op(';')
            self.loader(path, tok.file, spr, members=True)
        elif self.is_kw('const'):
            self.parse_const()
        elif self.is_kw('var'):
            self.i += 1
            spr['vars'].append(self.parse_vardecl(tok))
        elif self.is_kw('list'):
            spr['vars'].append(self.parse_vardecl(tok))
        elif self.is_kw('sounds'):
            self.i += 1
            while True:
                spr.setdefault('sounds', []).append(self.cur.val)
                self.i += 1
                if self.is_op(','):
                    self.i += 1
                    continue
                break
            self.eat_op(';')
        elif self.is_kw('costumes'):
            self.i += 1
            while True:
                spr['costumes'].append(self.cur.val)
                self.i += 1
                if self.is_op(','):
                    self.i += 1
                    continue
                break
            self.eat_op(';')
        elif self.is_kw('prop'):
            self.i += 1
            k = self.ident()
            self.eat_op('=')
            v = self.fold(self.parse_expr())
            spr['props'][k] = v
            self.eat_op(';')
        elif self.is_kw('proc'):
            self.i += 1
            name = self.ident()
            self.eat_op('(')
            params = []
            while not self.is_op(')'):
                params.append(self.ident())
                if self.is_op(','):
                    self.i += 1
            self.eat_op(')')
            mods = set()
            while self.cur.kind == 'id' and self.cur.val in ('nowarp', 'recursive', 'warp'):
                mods.add(self.cur.val)
                self.i += 1
            body = self.parse_block()
            spr['procs'].append({'name': name, 'params': params, 'mods': mods, 'body': body,
                                 'line': f"{tok.file}:{tok.line}"})
        elif self.is_kw('on'):
            self.i += 1
            ev = self.ident()
            arg = None
            if ev in ('msg', 'key'):
                arg = self.cur.val
                self.i += 1
            body = self.parse_block()
            spr['hats'].append({'event': ev, 'arg': arg, 'body': body, 'line': f"{tok.file}:{tok.line}"})
        else:
            self.err("expected sprite member")

    # statements -----------------------------------------------------------
    def parse_block(self):
        self.eat_op('{')
        stmts = []
        while not self.is_op('}'):
            stmts.append(self.parse_stmt())
        self.eat_op('}')
        return stmts

    def parse_stmt(self):
        tok = self.cur
        if self.is_op('{'):
            return N('block', self.parse_block(), tok=tok)
        if self.cur.kind == 'id':
            kw = self.cur.val
            if kw == 'local':
                self.i += 1
                names = []
                while True:
                    name = self.ident()
                    init = None
                    if self.is_op('='):
                        self.i += 1
                        init = self.parse_expr()
                    names.append((name, init))
                    if self.is_op(','):
                        self.i += 1
                        continue
                    break
                self.eat_op(';')
                return N('local', names, tok=tok)
            if kw == 'if':
                self.i += 1
                self.eat_op('(')
                c = self.parse_expr()
                self.eat_op(')')
                then = self.parse_block()
                els = None
                if self.is_kw('else'):
                    self.i += 1
                    if self.is_kw('if'):
                        els = [self.parse_stmt()]
                    else:
                        els = self.parse_block()
                # a constant condition (build settings) keeps only one branch
                cv = self.fold(c)
                if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                    return N('block', then if cv else (els or []), tok=tok)
                return N('if', c, then, els, tok=tok)
            if kw in ('while', 'until'):
                self.i += 1
                self.eat_op('(')
                c = self.parse_expr()
                self.eat_op(')')
                body = self.parse_block()
                if kw == 'until':
                    c = N('un', '!', c, tok=tok)
                return N('while', c, body, tok=tok)
            if kw == 'repeat':
                self.i += 1
                self.eat_op('(')
                c = self.parse_expr()
                self.eat_op(')')
                return N('repeat', c, self.parse_block(), tok=tok)
            if kw == 'forever':
                self.i += 1
                return N('forever', self.parse_block(), tok=tok)
            if kw == 'for':
                self.i += 1
                if self.is_op('('):
                    self.i += 1
                    init = None if self.is_op(';') else self.parse_simple()
                    self.eat_op(';')
                    cond = None if self.is_op(';') else self.parse_expr()
                    self.eat_op(';')
                    step = None if self.is_op(')') else self.parse_simple()
                    self.eat_op(')')
                    body = self.parse_block()
                    return N('for', init, cond, step, body, tok=tok)
                var = self.ident()
                self.eat_op('=')
                a = self.parse_expr()
                self.eat_kw('to')
                b = self.parse_expr()
                step = N('num', 1)
                if self.is_kw('step'):
                    self.i += 1
                    step = self.parse_expr()
                sv = self.fold(step)
                if sv is None:
                    self.err("for-to step must be constant")
                body = self.parse_block()
                cmp = '<=' if sv > 0 else '>='
                init = N('local', [(var, a)], tok=tok)
                cond = N('bin', cmp, N('name', var, tok=tok), b, tok=tok)
                stp = N('assign', var, '+=', N('num', sv), tok=tok)
                return N('for', init, cond, stp, body, tok=tok)
            if kw == 'switch':
                self.i += 1
                self.eat_op('(')
                e = self.parse_expr()
                self.eat_op(')')
                self.eat_op('{')
                cases = []
                default = None
                while not self.is_op('}'):
                    if self.is_kw('case'):
                        self.i += 1
                        vals = []
                        while True:
                            v = self.fold(self.parse_expr())
                            if not isinstance(v, (int, float)):
                                self.err("case value must be numeric constant")
                            vals.append(v)
                            if self.is_op(','):
                                self.i += 1
                                continue
                            break
                        self.eat_op(':')
                        body = self.parse_block()
                        cases.append((vals, body))
                    elif self.is_kw('default'):
                        self.i += 1
                        self.eat_op(':')
                        default = self.parse_block()
                    else:
                        self.err("expected case/default")
                self.eat_op('}')
                return N('switch', e, cases, default, tok=tok)
            if kw == 'break':
                self.i += 1
                self.eat_op(';')
                return N('break', tok=tok)
            if kw == 'continue':
                self.i += 1
                self.eat_op(';')
                return N('continue', tok=tok)
            if kw == 'return':
                self.i += 1
                e = None
                if not self.is_op(';'):
                    e = self.parse_expr()
                self.eat_op(';')
                return N('return', e, tok=tok)
        s = self.parse_simple()
        self.eat_op(';')
        return s

    def parse_simple(self):
        tok = self.cur
        if self.cur.kind == 'id' and self.peek().kind == 'op':
            op = self.peek().val
            if op in ('=', '+=', '-=', '*=', '/=', '%=', '..='):
                name = self.ident()
                self.i += 1
                e = self.parse_expr()
                return N('assign', name, op, e, tok=tok)
            if op in ('++', '--'):
                name = self.ident()
                self.i += 1
                return N('assign', name, '+=' if op == '++' else '-=', N('num', 1), tok=tok)
            if op == '[':
                # possible list item assignment
                save = self.i
                name = self.ident()
                self.eat_op('[')
                idx = self.parse_expr()
                self.eat_op(']')
                if self.is_op('='):
                    self.i += 1
                    e = self.parse_expr()
                    return N('setitem', name, idx, e, tok=tok)
                if self.cur.kind == 'op' and self.cur.val in ('+=', '-=', '..='):
                    op = self.cur.val[:-1]
                    self.i += 1
                    e = self.parse_expr()
                    return N('setitem', name, idx, N('bin', op, N('index', name, idx, tok=tok), e, tok=tok), tok=tok)
                self.i = save
        e = self.parse_expr()
        if e.kind != 'call':
            self.err("expression statement must be a call", tok)
        return N('exprstmt', e, tok=tok)

    # expressions ----------------------------------------------------------
    def parse_expr(self):
        c = self.parse_bin(0)
        if self.is_op('?'):
            tok = self.cur
            self.i += 1
            a = self.parse_expr()
            self.eat_op(':')
            b = self.parse_expr()
            return N('cond', c, a, b, tok=tok)
        return c

    def parse_bin(self, lvl):
        if lvl >= len(BINOP_PREC):
            return self.parse_unary()
        lhs = self.parse_bin(lvl + 1)
        while self.cur.kind == 'op' and self.cur.val in BINOP_PREC[lvl]:
            tok = self.cur
            op = self.cur.val
            self.i += 1
            rhs = self.parse_bin(lvl + 1)
            lhs = N('bin', op, lhs, rhs, tok=tok)
            v = self.fold(lhs)
            if v is not None and op not in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
                lhs = N('str' if isinstance(v, str) else 'num', v, tok=tok)
        return lhs

    def parse_unary(self):
        tok = self.cur
        if self.is_op('!'):
            self.i += 1
            return N('un', '!', self.parse_unary(), tok=tok)
        if self.is_op('-'):
            self.i += 1
            e = self.parse_unary()
            if e.kind == 'num':
                return N('num', -e.a[0], tok=tok)
            return N('un', '-', e, tok=tok)
        return self.parse_postfix()

    def parse_postfix(self):
        tok = self.cur
        if self.cur.kind == 'num':
            self.i += 1
            return N('num', tok.val, tok=tok)
        if self.cur.kind == 'str':
            self.i += 1
            return N('str', tok.val, tok=tok)
        if self.is_op('('):
            self.i += 1
            e = self.parse_expr()
            self.eat_op(')')
            return e
        if self.cur.kind == 'id':
            name = self.ident()
            if name == 'true':
                return N('bool', True, tok=tok)
            if name == 'false':
                return N('bool', False, tok=tok)
            if self.is_op('('):
                self.i += 1
                args = []
                while not self.is_op(')'):
                    args.append(self.parse_expr())
                    if self.is_op(','):
                        self.i += 1
                self.eat_op(')')
                return N('call', name, args, tok=tok)
            if self.is_op('['):
                self.i += 1
                idx = self.parse_expr()
                self.eat_op(']')
                return N('index', name, idx, tok=tok)
            if name in self.consts:
                v = self.consts[name]
                return N('str' if isinstance(v, str) else 'num', v, tok=tok)
            return N('name', name, tok=tok)
        self.err("expected expression")


def fmt_lit(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float):
        if v != v:
            return 'NaN'
        if v in (float('inf'), float('-inf')):
            return 'Infinity' if v > 0 else '-Infinity'
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    return str(v)


# --------------------------------------------------------------------------
# Code generation
# --------------------------------------------------------------------------

_B62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


class IdGen:
    def __init__(self, prefix):
        self.n = 0
        self.prefix = prefix

    def __call__(self):
        self.n += 1
        n = self.n
        s = ''
        while n:
            s = _B62[n % 62] + s
            n //= 62
        return self.prefix + s


MATHOPS = {'abs', 'floor', 'ceiling', 'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'e ^', '10 ^'}
MATH_ALIASES = {'abs': 'abs', 'floor': 'floor', 'ceil': 'ceiling', 'sqrt': 'sqrt', 'sin': 'sin', 'cos': 'cos',
                'tan': 'tan', 'asin': 'asin', 'acos': 'acos', 'atan': 'atan', 'ln': 'ln', 'log10': 'log',
                'exp': 'e ^', 'pow10': '10 ^'}
CURRENT_MENU = {'year': 'YEAR', 'month': 'MONTH', 'date': 'DATE', 'dayofweek': 'DAYOFWEEK',
                'hour': 'HOUR', 'minute': 'MINUTE', 'second': 'SECOND'}

# value kinds: ('lit', python value)  ('blk', id, is_bool)  ('var', name, id)  ('none',)


class ProcInfo:
    def __init__(self, name, params, mods, sprite):
        self.name = name
        self.params = params
        self.mods = mods
        self.proccode = name + ''.join(' %s' for _ in params)
        self.argids = [f"{sprite}_{name}_a{i}" for i in range(len(params))]
        self.warp = 'nowarp' not in mods
        self.recursive = 'recursive' in mods


class Ctx:
    """Per-script compile context."""

    def __init__(self, name, proc=None):
        self.name = name
        self.proc = proc
        self.locals = {}          # local name -> var key
        self.saved = []           # var keys saved for recursion
        self.tmp_n = 0
        self.tmp_max = 0
        self.loops = []           # stack of loop info dicts
        self.sw_n = 0


class SpriteGen:
    def __init__(self, prog, spr, gen, var_ids, stage_vars):
        self.prog = prog
        self.spr = spr
        self.gen = gen
        self.blocks = {}
        self.newid = IdGen(spr['name'][:2] + '_')
        self.vars = {}            # name -> (id, display_name)
        self.lists = {}
        self.var_values = {}
        self.list_values = {}
        self.stage_vars = stage_vars
        self.procs = {}
        self.pre = None
        self.ctx = None
        self.top_y = 0
        sname = spr['name']
        seen = {}
        for v in spr['vars']:
            key = (v['name'], v['list'])
            if key in seen:
                kind = 'list' if v['list'] else 'var'
                raise CompileError(f"{v['line']}: duplicate {kind} {v['name']} (first declared at {seen[key]})")
            seen[key] = v['line']
            self.declare(v['name'], v['list'], v['init'])
        for p in spr['procs']:
            if p['name'] in self.procs:
                raise CompileError(f"{p['line']}: duplicate proc {p['name']}")
            self.procs[p['name']] = ProcInfo(p['name'], p['params'], p['mods'], sname)
        self.declare('_r', False, 0)
        self.declare('_save', True, [])

    # --- symbols -----------------------------------------------------------
    def declare(self, name, is_list, init):
        tbl = self.lists if is_list else self.vars
        if name in tbl:
            return tbl[name]
        vid = f"{self.spr['name']}.{'L' if is_list else 'V'}.{name}"
        tbl[name] = (vid, name)
        if is_list:
            if isinstance(init, tuple) and init[0] == 'data':
                vals = self.gen.data[init[1]]
            else:
                vals = init or []
            self.list_values[name] = vals
        else:
            self.var_values[name] = 0 if init is None else init
        return tbl[name]

    def lookup_var(self, name):
        if self.ctx and name in self.ctx.locals:
            return self.vars[self.ctx.locals[name]]
        if name in self.vars:
            return self.vars[name]
        if name in self.stage_vars['vars']:
            return self.stage_vars['vars'][name]
        return None

    def lookup_list(self, name):
        if name in self.lists:
            return self.lists[name]
        if name in self.stage_vars['lists']:
            return self.stage_vars['lists'][name]
        return None

    def is_param(self, name):
        return self.ctx and self.ctx.proc and name in self.ctx.proc.params

    def err(self, node, msg):
        raise CompileError(f"{getattr(node, 'line', '?')}: {msg}")

    # --- block helpers -----------------------------------------------------
    def mk(self, opcode, inputs=None, fields=None, shadow=False, mutation=None, top=False):
        bid = self.newid()
        b = {'opcode': opcode, 'next': None, 'parent': None, 'inputs': {}, 'fields': fields or {},
             'shadow': shadow, 'topLevel': top}
        if mutation is not None:
            b['mutation'] = mutation
        if top:
            b['x'] = 0
            b['y'] = self.top_y
            self.top_y += 400
        self.blocks[bid] = b
        for k, (slot, val) in (inputs or {}).items():
            inp = self.make_input(slot, val, bid)
            if inp is not None:
                b['inputs'][k] = inp
        return bid

    def make_input(self, slot, val, parent):
        """slot: 'num' | 'str' | 'bool' | 'color' | ('menu', opcode, field, default)"""
        if slot == 'bool':
            bid = self.as_bool_block(val)
            if bid is None:
                return None
            self.blocks[bid]['parent'] = parent
            return [2, bid]
        if isinstance(slot, tuple) and slot[0] == 'menu':
            _, mop, mfield, default = slot
            if val[0] == 'lit':
                sid = self.mk(mop, fields={mfield: [fmt_lit(val[1]), None]}, shadow=True)
                self.blocks[sid]['parent'] = parent
                return [1, sid]
            sid = self.mk(mop, fields={mfield: [default, None]}, shadow=True)
            self.blocks[sid]['parent'] = parent
            return [3, self.reporter(val, parent), sid]
        prim = {'num': 4, 'str': 10, 'color': 9, 'int': 7, 'posnum': 5}[slot]
        empty = '#000000' if slot == 'color' else ''
        if val[0] == 'lit':
            v = val[1]
            if slot == 'color' and isinstance(v, (int, float)):
                v = '#%06x' % int(v)
            return [1, [prim, fmt_lit(v)]]
        if val[0] == 'none':
            return [1, [prim, empty]]
        return [3, self.reporter(val, parent), [prim, empty]]

    def reporter(self, val, parent):
        if val[0] == 'var':
            return [12, val[1], val[2]]
        if val[0] == 'blk':
            self.blocks[val[1]]['parent'] = parent
            return val[1]
        raise CompileError(f"bad reporter {val}")

    def as_bool_block(self, val):
        """Return a boolean block id (or None for constant false)."""
        if val[0] == 'blk' and val[2]:
            return val[1]
        if val[0] == 'lit':
            v = val[1]
            truthy = v is True or (isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0) \
                or (isinstance(v, str) and v not in ('', '0', 'false'))
            if truthy:
                return self.mk('operator_not', {})  # not <empty> == true
            return None
        if val[0] == 'none':
            return None
        # generic value: compare with 1 (true == 1 in Scratch casting)
        return self.mk('operator_equals', {'OPERAND1': ('str', val), 'OPERAND2': ('str', ('lit', 1))})

    def link(self, ids):
        ids = [i for i in ids if i is not None]
        for a, b in zip(ids, ids[1:]):
            self.blocks[a]['next'] = b
            self.blocks[b]['parent'] = a
        return ids[0] if ids else None

    def substack(self, ids, parent):
        first = self.link(ids)
        if first is None:
            return None
        self.blocks[first]['parent'] = parent
        return [2, first]

    def set_sub(self, bid, name, ids):
        s = self.substack(ids, bid)
        if s:
            self.blocks[bid]['inputs'][name] = s

    # --- temps / locals ----------------------------------------------------
    def tmp(self):
        self.ctx.tmp_n += 1
        n = self.ctx.tmp_n
        self.ctx.tmp_max = max(self.ctx.tmp_max, n)
        key = f"{self.ctx.name}._t{n}"
        self.declare(key, False, 0)
        if self.ctx.proc and self.ctx.proc.recursive and key not in self.ctx.saved:
            self.ctx.saved.append(key)
        return key

    def flag_var(self, kind):
        key = f"{self.ctx.name}._{kind}{len(self.ctx.loops)}"
        self.declare(key, False, 0)
        if self.ctx.proc and self.ctx.proc.recursive and key not in self.ctx.saved:
            self.ctx.saved.append(key)
        return key

    def var_val(self, key):
        vid, disp = self.vars[key]
        return ('var', disp, vid)

    def set_var_stmt(self, key_or_tuple, val):
        vid, disp = key_or_tuple
        return self.mk('data_setvariableto', {'VALUE': ('str', val)}, {'VARIABLE': [disp, vid]})

    # --- expressions -------------------------------------------------------
    def expr(self, e):
        k = e.kind
        if k == 'num':
            return ('lit', e.a[0])
        if k == 'str':
            return ('lit', e.a[0])
        if k == 'bool':
            if e.a[0]:
                return ('blk', self.mk('operator_not', {}), True)
            return ('blk', self.mk('operator_not', {'OPERAND': ('bool', ('lit', 1))}), True)
        if k == 'name':
            name = e.a[0]
            if self.is_param(name):
                return ('blk', self.mk('argument_reporter_string_number', fields={'VALUE': [name, None]}), False)
            v = self.lookup_var(name)
            if v:
                return ('var', v[1], v[0])
            if self.lookup_list(name):
                self.err(e, f"list '{name}' used as value")
            self.err(e, f"unknown name '{name}'")
        if k == 'index':
            name, idx = e.a
            lst = self.lookup_list(name)
            iv = self.expr(idx)
            if lst:
                return ('blk', self.mk('data_itemoflist', {'INDEX': ('int', iv)}, {'LIST': [lst[1], lst[0]]}), False)
            sv = self.expr(N('name', name)) if not self.is_param(name) else self.expr(N('name', name))
            return ('blk', self.mk('operator_letter_of', {'LETTER': ('posnum', iv), 'STRING': ('str', sv)}), False)
        if k == 'un':
            op, x = e.a
            if op == '!':
                xv = self.expr(x)
                return ('blk', self.mk('operator_not', {'OPERAND': ('bool', xv)}), True)
            if op == '-':
                xv = self.expr(x)
                return ('blk', self.mk('operator_subtract', {'NUM1': ('num', ('lit', 0)), 'NUM2': ('num', xv)}), False)
        if k == 'bin':
            return self.binop(e)
        if k == 'cond':
            c, a, b = e.a
            t = self.tmp()
            cv = self.expr(c)
            saved = self.pre
            self.pre = []
            av = self.expr(a)
            self.pre.append(self.set_var_stmt(self.vars[t], av))
            then_ids = self.pre
            self.pre = []
            bv = self.expr(b)
            self.pre.append(self.set_var_stmt(self.vars[t], bv))
            else_ids = self.pre
            self.pre = saved
            bid = self.mk('control_if_else', {'CONDITION': ('bool', cv)})
            self.set_sub(bid, 'SUBSTACK', then_ids)
            self.set_sub(bid, 'SUBSTACK2', else_ids)
            self.pre.append(bid)
            return self.var_val(t)
        if k == 'call':
            return self.call_expr(e)
        self.err(e, f"bad expression {k}")

    def binop(self, e):
        op, a, b = e.a
        if op in ('&&', '||'):
            av = self.expr(a)
            saved = self.pre
            self.pre = []
            bv = self.expr(b)
            rhs_pre = self.pre
            self.pre = saved
            if not rhs_pre:
                opc = 'operator_and' if op == '&&' else 'operator_or'
                return ('blk', self.mk(opc, {'OPERAND1': ('bool', av), 'OPERAND2': ('bool', bv)}), True)
            # short-circuit with hoisted rhs
            t = self.tmp()
            tv = self.vars[t]
            ab = self.as_bool_block(av)
            self.pre.append(self.set_var_stmt(tv, ('blk', ab, True) if ab else ('lit', 0)))
            cond = self.var_val(t)
            if op == '||':
                cond = ('blk', self.mk('operator_not', {'OPERAND': ('bool', cond)}), True)
            bid = self.mk('control_if', {'CONDITION': ('bool', cond)})
            bb = self.as_bool_block(bv)
            rhs_pre.append(self.set_var_stmt(tv, ('blk', bb, True) if bb else ('lit', 0)))
            self.set_sub(bid, 'SUBSTACK', rhs_pre)
            self.pre.append(bid)
            return self.var_val(t)
        # Scratch/TurboWarp quirk: a numerically-zero value ("0", 0) compares equal to a
        # whitespace-only string, and TurboWarp even treats a constant "\t" or " " as 0.
        # So `x == W` (W whitespace) is compiled as  len(x) == len(W) && contains(W, x),
        # which only uses string operations; `x == ""` becomes len(x) == 0.
        if op in ('==', '!=') and (self.is_ws_lit(a) or self.is_ws_lit(b)):
            x, lit = (b, a) if self.is_ws_lit(a) else (a, b)
            w = lit.a[0]
            xv = self.expr(x)
            if xv[0] == 'blk':
                t = self.tmp()
                self.pre.append(self.set_var_stmt(self.vars[t], xv))
                xv = self.var_val(t)
            lb = self.mk('operator_length', {'STRING': ('str', xv)})
            eq = self.mk('operator_equals', {'OPERAND1': ('str', ('blk', lb, False)), 'OPERAND2': ('str', ('lit', len(w)))})
            if w != '':
                cb = self.mk('operator_contains', {'STRING1': ('str', ('lit', w)), 'STRING2': ('str', xv)})
                eq = self.mk('operator_and', {'OPERAND1': ('bool', ('blk', eq, True)), 'OPERAND2': ('bool', ('blk', cb, True))})
            if op == '==':
                return ('blk', eq, True)
            return ('blk', self.mk('operator_not', {'OPERAND': ('bool', ('blk', eq, True))}), True)
        av = self.expr(a)
        bv = self.expr(b)
        if op == '+':
            return ('blk', self.mk('operator_add', {'NUM1': ('num', av), 'NUM2': ('num', bv)}), False)
        if op == '-':
            return ('blk', self.mk('operator_subtract', {'NUM1': ('num', av), 'NUM2': ('num', bv)}), False)
        if op == '*':
            return ('blk', self.mk('operator_multiply', {'NUM1': ('num', av), 'NUM2': ('num', bv)}), False)
        if op == '/':
            return ('blk', self.mk('operator_divide', {'NUM1': ('num', av), 'NUM2': ('num', bv)}), False)
        if op == '%':
            return ('blk', self.mk('operator_mod', {'NUM1': ('num', av), 'NUM2': ('num', bv)}), False)
        if op == '..':
            return ('blk', self.mk('operator_join', {'STRING1': ('str', av), 'STRING2': ('str', bv)}), False)
        if op == '==':
            return ('blk', self.mk('operator_equals', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)}), True)
        if op == '!=':
            eq = self.mk('operator_equals', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)})
            return ('blk', self.mk('operator_not', {'OPERAND': ('bool', ('blk', eq, True))}), True)
        if op == '<':
            return ('blk', self.mk('operator_lt', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)}), True)
        if op == '>':
            return ('blk', self.mk('operator_gt', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)}), True)
        if op == '<=':
            g = self.mk('operator_gt', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)})
            return ('blk', self.mk('operator_not', {'OPERAND': ('bool', ('blk', g, True))}), True)
        if op == '>=':
            g = self.mk('operator_lt', {'OPERAND1': ('str', av), 'OPERAND2': ('str', bv)})
            return ('blk', self.mk('operator_not', {'OPERAND': ('bool', ('blk', g, True))}), True)
        self.err(e, f"bad operator {op}")

    @staticmethod
    def is_ws_lit(e):
        return e.kind == 'str' and e.a[0].strip(' \t\n\r') == ''

    def list_arg(self, e, node):
        if e.kind != 'name' or not self.lookup_list(e.a[0]):
            self.err(node, "expected list name")
        l = self.lookup_list(e.a[0])
        return {'LIST': [l[1], l[0]]}

    def call_expr(self, e):
        name, args = e.a
        n = len(args)
        if name in self.procs:
            self.emit_call(e)
            t = self.tmp()
            r = self.vars['_r']
            self.pre.append(self.set_var_stmt(self.vars[t], ('var', r[1], r[0])))
            return self.var_val(t)
        X = lambda i: self.expr(args[i])
        if name == 'len':
            if args[0].kind == 'name' and self.lookup_list(args[0].a[0]) and not self.lookup_var(args[0].a[0]):
                return ('blk', self.mk('data_lengthoflist', fields=self.list_arg(args[0], e)), False)
            return ('blk', self.mk('operator_length', {'STRING': ('str', X(0))}), False)
        if name == 'index':
            f = self.list_arg(args[0], e)
            return ('blk', self.mk('data_itemnumoflist', {'ITEM': ('str', X(1))}, f), False)
        if name == 'has':
            f = self.list_arg(args[0], e)
            return ('blk', self.mk('data_listcontainsitem', {'ITEM': ('str', X(1))}, f), True)
        if name == 'contains':
            return ('blk', self.mk('operator_contains', {'STRING1': ('str', X(0)), 'STRING2': ('str', X(1))}), True)
        if name == 'join':
            vals = [X(i) for i in range(n)]
            acc = vals[0]
            for v in vals[1:]:
                acc = ('blk', self.mk('operator_join', {'STRING1': ('str', acc), 'STRING2': ('str', v)}), False)
            return acc
        if name == 'letter':
            return ('blk', self.mk('operator_letter_of', {'LETTER': ('posnum', X(1)), 'STRING': ('str', X(0))}), False)
        if name == 'round':
            return ('blk', self.mk('operator_round', {'NUM': ('num', X(0))}), False)
        if name in MATH_ALIASES:
            return ('blk', self.mk('operator_mathop', {'NUM': ('num', X(0))},
                                   {'OPERATOR': [MATH_ALIASES[name], None]}), False)
        if name == 'random':
            return ('blk', self.mk('operator_random', {'FROM': ('num', X(0)), 'TO': ('num', X(1))}), False)
        if name == 'num':  # force numeric
            return ('blk', self.mk('operator_add', {'NUM1': ('num', X(0)), 'NUM2': ('num', ('lit', 0))}), False)
        if name == 'mouse_x':
            return ('blk', self.mk('sensing_mousex'), False)
        if name == 'mouse_y':
            return ('blk', self.mk('sensing_mousey'), False)
        if name == 'mouse_down':
            return ('blk', self.mk('sensing_mousedown'), True)
        if name == 'key':
            return ('blk', self.mk('sensing_keypressed',
                                   {'KEY_OPTION': (('menu', 'sensing_keyoptions', 'KEY_OPTION', 'space'), X(0))}), True)
        if name == 'timer':
            return ('blk', self.mk('sensing_timer'), False)
        if name == 'days2000':
            return ('blk', self.mk('sensing_dayssince2000'), False)
        if name == 'now':
            what = self.fold_str(args[0], e)
            return ('blk', self.mk('sensing_current', fields={'CURRENTMENU': [CURRENT_MENU[what], None]}), False)
        if name == 'username':
            return ('blk', self.mk('sensing_username'), False)
        if name == 'costume_num':
            return ('blk', self.mk('looks_costumenumbername', fields={'NUMBER_NAME': ['number', None]}), False)
        if name == 'costume_name':
            return ('blk', self.mk('looks_costumenumbername', fields={'NUMBER_NAME': ['name', None]}), False)
        if name == 'x_pos':
            return ('blk', self.mk('motion_xposition'), False)
        if name == 'y_pos':
            return ('blk', self.mk('motion_yposition'), False)
        self.err(e, f"unknown function '{name}'")

    def fold_str(self, node, e):
        if node.kind != 'str':
            self.err(e, "expected string literal")
        return node.a[0]

    def emit_call(self, e):
        name, args = e.a
        p = self.procs[name]
        if len(args) != len(p.params):
            self.err(e, f"{name} expects {len(p.params)} args, got {len(args)}")
        vals = [self.expr(a) for a in args]
        inputs = {aid: ('str', v) for aid, v in zip(p.argids, vals)}
        mut = {'tagName': 'mutation', 'children': [], 'proccode': p.proccode,
               'argumentids': json.dumps(p.argids), 'warp': 'true' if p.warp else 'false'}
        bid = self.mk('procedures_call', inputs, mutation=mut)
        self.pre.append(bid)

    # --- statements --------------------------------------------------------
    def stmts(self, lst):
        """Compile list of statements -> list of block ids. Handles break/continue wrapping."""
        out = []
        i = 0
        while i < len(lst):
            s = lst[i]
            out.extend(self.stmt(s))
            if self.ctx.loops and s.kind in ('break', 'continue'):
                return out  # rest is dead code
            if self.ctx.loops and s.kind not in ('break', 'continue') and self.may_jump(s):
                rest = lst[i + 1:]
                if rest:
                    loop = self.ctx.loops[-1]
                    cond = self.not_jumped(loop)
                    bid = self.mk('control_if', {'CONDITION': ('bool', cond)})
                    self.set_sub(bid, 'SUBSTACK', self.stmts(rest))
                    out.append(bid)
                return out
            i += 1
        return out

    def may_jump(self, s, depth=0):
        """True if statement contains break/continue for the current loop."""
        k = s.kind
        if k in ('break', 'continue'):
            return depth == 0
        if k in ('while', 'repeat', 'forever', 'for'):
            body = s.a[-1] if k != 'for' else s.a[3]
            return any(self.may_jump(x, depth + 1) for x in body)
        if k == 'if':
            return any(self.may_jump(x, depth) for x in s.a[1]) or \
                any(self.may_jump(x, depth) for x in (s.a[2] or []))
        if k == 'block':
            return any(self.may_jump(x, depth) for x in s.a[0])
        if k == 'switch':
            return any(any(self.may_jump(x, depth) for x in b) for _, b in s.a[1]) or \
                any(self.may_jump(x, depth) for x in (s.a[2] or []))
        return False

    def body_has(self, body, kind, depth=0):
        for s in body:
            k = s.kind
            if k == kind and depth == 0:
                return True
            if k in ('while', 'repeat', 'forever'):
                if self.body_has(s.a[-1], kind, depth + 1):
                    return True
            elif k == 'for':
                if self.body_has(s.a[3], kind, depth + 1):
                    return True
            elif k == 'if':
                if self.body_has(s.a[1], kind, depth) or self.body_has(s.a[2] or [], kind, depth):
                    return True
            elif k == 'block':
                if self.body_has(s.a[0], kind, depth):
                    return True
            elif k == 'switch':
                for _, b in s.a[1]:
                    if self.body_has(b, kind, depth):
                        return True
                if self.body_has(s.a[2] or [], kind, depth):
                    return True
        return False

    def not_jumped(self, loop):
        parts = []
        if loop['brk']:
            parts.append(self.vars[loop['brk']])
        if loop['cnt']:
            parts.append(self.vars[loop['cnt']])
        conds = [('blk', self.mk('operator_equals', {'OPERAND1': ('str', ('var', p[1], p[0])),
                                                      'OPERAND2': ('str', ('lit', 0))}), True) for p in parts]
        c = conds[0]
        for d in conds[1:]:
            c = ('blk', self.mk('operator_and', {'OPERAND1': ('bool', c), 'OPERAND2': ('bool', d)}), True)
        return c

    def with_pre(self, fn):
        """Run fn() collecting hoisted statements; return (pre_ids, result)."""
        saved = self.pre
        self.pre = []
        r = fn()
        p = self.pre
        self.pre = saved
        return p, r

    def stmt(self, s):
        self.ctx.tmp_n = 0
        k = s.kind
        if k == 'block':
            return self.stmts(s.a[0])
        if k == 'local':
            out = []
            for name, init in s.a[0]:
                key = f"{self.ctx.name}.{name}"
                self.declare(key, False, 0)
                self.ctx.locals[name] = key
                if self.ctx.proc and self.ctx.proc.recursive and key not in self.ctx.saved:
                    self.ctx.saved.append(key)
                if init is not None:
                    out.extend(self.assign(s, name, '=', init))
            return out
        if k == 'assign':
            return self.assign(s, *s.a)
        if k == 'setitem':
            name, idx, val = s.a
            lst = self.lookup_list(name)
            if not lst:
                self.err(s, f"'{name}' is not a list")
            pre, (iv, vv) = self.with_pre(lambda: (self.expr(idx), self.expr(val)))
            return pre + [self.mk('data_replaceitemoflist', {'INDEX': ('int', iv), 'ITEM': ('str', vv)},
                                  {'LIST': [lst[1], lst[0]]})]
        if k == 'if':
            c, then, els = s.a
            pre, cv = self.with_pre(lambda: self.expr(c))
            if els:
                bid = self.mk('control_if_else', {'CONDITION': ('bool', cv)})
                self.set_sub(bid, 'SUBSTACK', self.stmts(then))
                self.set_sub(bid, 'SUBSTACK2', self.stmts(els))
            else:
                bid = self.mk('control_if', {'CONDITION': ('bool', cv)})
                self.set_sub(bid, 'SUBSTACK', self.stmts(then))
            return pre + [bid]
        if k in ('while', 'for', 'repeat', 'forever'):
            return self.loop(s)
        if k == 'switch':
            return self.switch(s)
        if k == 'break':
            if not self.ctx.loops:
                self.err(s, "break outside loop")
            return [self.set_var_stmt(self.vars[self.ctx.loops[-1]['brk']], ('lit', 1))]
        if k == 'continue':
            if not self.ctx.loops:
                self.err(s, "continue outside loop")
            return [self.set_var_stmt(self.vars[self.ctx.loops[-1]['cnt']], ('lit', 1))]
        if k == 'return':
            out = []
            if s.a[0] is not None:
                e = s.a[0]
                if e.kind == 'call' and e.a[0] in self.procs:
                    self.pre = out
                    self.emit_call(e)
                    self.pre = None
                else:
                    pre, v = self.with_pre(lambda: self.expr(e))
                    out.extend(pre)
                    out.append(self.set_var_stmt(self.vars['_r'], v))
            out.extend(self.restore_locals())
            out.append(self.mk('control_stop', fields={'STOP_OPTION': ['this script', None]},
                               mutation={'tagName': 'mutation', 'children': [], 'hasnext': 'false'}))
            return out
        if k == 'exprstmt':
            return self.call_stmt(s.a[0])
        self.err(s, f"bad statement {k}")

    def restore_locals(self):
        if not self.ctx.proc or not self.ctx.proc.recursive:
            return []
        return [('RESTORE',)]  # placeholder, patched after body compile

    def assign(self, s, name, op, e):
        if self.is_param(name):
            self.err(s, f"cannot assign to parameter '{name}'")
        v = self.lookup_var(name)
        if not v:
            self.err(s, f"unknown variable '{name}'")
        if op == '=' and e.kind == 'call' and e.a[0] in self.procs:
            out = []
            self.pre = out
            self.emit_call(e)
            self.pre = None
            r = self.vars['_r']
            out.append(self.set_var_stmt(v, ('var', r[1], r[0])))
            return out
        pre, val = self.with_pre(lambda: self.expr(e))
        if op == '=':
            return pre + [self.set_var_stmt(v, val)]
        if op == '+=':
            return pre + [self.mk('data_changevariableby', {'VALUE': ('num', val)}, {'VARIABLE': [v[1], v[0]]})]
        if op == '-=':
            if val[0] == 'lit' and isinstance(val[1], (int, float)):
                neg = ('lit', -val[1])
            else:
                neg = ('blk', self.mk('operator_subtract', {'NUM1': ('num', ('lit', 0)), 'NUM2': ('num', val)}), False)
            return pre + [self.mk('data_changevariableby', {'VALUE': ('num', neg)}, {'VARIABLE': [v[1], v[0]]})]
        opmap = {'*=': 'operator_multiply', '/=': 'operator_divide', '%=': 'operator_mod', '..=': 'operator_join'}
        cur = ('var', v[1], v[0])
        if op == '..=':
            nb = self.mk('operator_join', {'STRING1': ('str', cur), 'STRING2': ('str', val)})
        else:
            nb = self.mk(opmap[op], {'NUM1': ('num', cur), 'NUM2': ('num', val)})
        return pre + [self.set_var_stmt(v, ('blk', nb, False))]

    def loop(self, s):
        k = s.kind
        if k == 'for':
            init, cond, step, body = s.a
        elif k == 'while':
            init, step = None, None
            cond, body = s.a
        elif k == 'forever':
            init, cond, step = None, None, None
            body = s.a[0]
        else:  # repeat
            init, cond, step = None, None, None
            body = s.a[1]
        has_brk = self.body_has(body, 'break')
        has_cnt = self.body_has(body, 'continue')
        self.ctx.loops.append({'brk': None, 'cnt': None})
        loop = self.ctx.loops[-1]
        if has_brk:
            loop['brk'] = self.flag_var('bk')
        if has_cnt:
            loop['cnt'] = self.flag_var('ct')
        out = []
        if init is not None:
            out.extend(self.stmt(init))
        if has_brk:
            out.append(self.set_var_stmt(self.vars[loop['brk']], ('lit', 0)))
        body_ids = []
        if has_cnt:
            body_ids.append(self.set_var_stmt(self.vars[loop['cnt']], ('lit', 0)))
        body_ids.extend(self.stmts(body))
        if k == 'repeat' and not has_brk:
            self.ctx.loops.pop()
            self.ctx.tmp_n = 0
            pre, nv = self.with_pre(lambda: self.expr(s.a[0]))
            bid = self.mk('control_repeat', {'TIMES': ('posnum', nv)})
            self.set_sub(bid, 'SUBSTACK', body_ids)
            return out + pre + [bid]
        if k == 'repeat':
            # counted loop with break -> while
            cnt = self.tmp()
            pre, nv = self.with_pre(lambda: self.expr(s.a[0]))
            out.extend(pre)
            out.append(self.set_var_stmt(self.vars[cnt], nv))
            cond_v = ('blk', self.mk('operator_gt', {'OPERAND1': ('str', self.var_val(cnt)),
                                                     'OPERAND2': ('str', ('lit', 0))}), True)
            body_ids.append(self.mk('data_changevariableby', {'VALUE': ('num', ('lit', -1))},
                                    {'VARIABLE': [self.vars[cnt][1], self.vars[cnt][0]]}))
            cond_pre = []
        elif cond is None:
            cond_v = None
            cond_pre = []
        else:
            self.ctx.tmp_n = 0
            cond_pre, cond_v = self.with_pre(lambda: self.expr(cond))
        if step is not None:
            step_ids = self.stmt(step)
            if has_brk:
                g = self.mk('control_if', {'CONDITION': ('bool', ('blk', self.mk('operator_equals', {
                    'OPERAND1': ('str', self.var_val(loop['brk'])), 'OPERAND2': ('str', ('lit', 0))}), True))})
                self.set_sub(g, 'SUBSTACK', step_ids)
                step_ids = [g]
            body_ids.extend(step_ids)
        if cond_pre:
            # recompute condition at end of each iteration
            self.ctx.tmp_n = 0
            cond_pre2, cond_v2 = self.with_pre(lambda: self.expr(cond))
            # we need the same variable to hold the condition: store into temp
            ct = self.tmp()
            out.extend(cond_pre)
            out.append(self.set_var_stmt(self.vars[ct], cond_v if cond_v[0] != 'blk' or not cond_v[2] else cond_v))
            body_ids.extend(cond_pre2)
            body_ids.append(self.set_var_stmt(self.vars[ct], cond_v2))
            cond_v = self.var_val(ct)
        if has_brk:
            nb = ('blk', self.mk('operator_equals', {'OPERAND1': ('str', self.var_val(loop['brk'])),
                                                     'OPERAND2': ('str', ('lit', 0))}), True)
            if cond_v is None:
                cond_v = nb
            else:
                cond_v = ('blk', self.mk('operator_and', {'OPERAND1': ('bool', nb), 'OPERAND2': ('bool', cond_v)}), True)
        self.ctx.loops.pop()
        if cond_v is None:
            bid = self.mk('control_forever')
        else:
            bid = self.mk('control_while', {'CONDITION': ('bool', cond_v)})
        self.set_sub(bid, 'SUBSTACK', body_ids)
        return out + [bid]

    def switch(self, s):
        e, cases, default = s.a
        pre, v = self.with_pre(lambda: self.expr(e))
        self.ctx.sw_n += 1
        key = f"{self.ctx.name}._sw{self.ctx.sw_n}"
        self.declare(key, False, 0)
        if self.ctx.proc and self.ctx.proc.recursive:
            self.ctx.saved.append(key)
        out = pre
        if v[0] == 'var':
            sv = v
        else:
            out.append(self.set_var_stmt(self.vars[key], v))
            sv = self.var_val(key)
        flat = []
        for vals, body in cases:
            for x in vals:
                flat.append((x, body))
        flat.sort(key=lambda t: t[0])
        dflag = None
        if default:
            dflag = f"{self.ctx.name}._swd{self.ctx.sw_n}"
            self.declare(dflag, False, 0)
            if self.ctx.proc and self.ctx.proc.recursive:
                self.ctx.saved.append(dflag)
            out.append(self.set_var_stmt(self.vars[dflag], ('lit', 0)))
        compiled = {}

        def body_ids(body):
            # Each case body compiled separately each time it's used (blocks can't be shared)
            return self.stmts(body)

        def miss():
            if dflag:
                return [self.set_var_stmt(self.vars[dflag], ('lit', 1))]
            return []

        def tree(items):
            if len(items) == 1:
                x, body = items[0]
                bid = self.mk('control_if_else' if dflag else 'control_if', {'CONDITION': ('bool', (
                    'blk', self.mk('operator_equals', {'OPERAND1': ('str', sv), 'OPERAND2': ('str', ('lit', x))}), True))})
                self.set_sub(bid, 'SUBSTACK', body_ids(body))
                if dflag:
                    self.set_sub(bid, 'SUBSTACK2', miss())
                return [bid]
            mid = len(items) // 2
            pivot = items[mid][0]
            bid = self.mk('control_if_else', {'CONDITION': ('bool', (
                'blk', self.mk('operator_lt', {'OPERAND1': ('str', sv), 'OPERAND2': ('str', ('lit', pivot))}), True))})
            self.set_sub(bid, 'SUBSTACK', tree(items[:mid]))
            self.set_sub(bid, 'SUBSTACK2', tree(items[mid:]))
            return [bid]

        if flat:
            out.extend(tree(flat))
        elif dflag:
            out.extend(miss())
        if default:
            bid = self.mk('control_if', {'CONDITION': ('bool', (
                'blk', self.mk('operator_equals', {'OPERAND1': ('str', self.var_val(dflag)),
                                                   'OPERAND2': ('str', ('lit', 1))}), True))})
            self.set_sub(bid, 'SUBSTACK', self.stmts(default))
            out.append(bid)
        return out

    def call_stmt(self, e):
        name, args = e.a
        if name in self.procs:
            out = []
            self.pre = out
            self.emit_call(e)
            self.pre = None
            return out
        self.pre = []
        out = self.pre
        X = lambda i: self.expr(args[i])
        L = lambda i: self.list_arg(args[i], e)
        mk = self.mk
        b = None
        if name == 'add':
            f = L(0)
            b = mk('data_addtolist', {'ITEM': ('str', X(1))}, f)
        elif name == 'del':
            f = L(0)
            b = mk('data_deleteoflist', {'INDEX': ('int', X(1))}, f)
        elif name == 'clear':
            b = mk('data_deletealloflist', fields=L(0))
        elif name == 'insert':
            f = L(0)
            b = mk('data_insertatlist', {'INDEX': ('int', X(1)), 'ITEM': ('str', X(2))}, f)
        elif name == 'show_list':
            b = mk('data_showlist', fields=L(0))
        elif name == 'hide_list':
            b = mk('data_hidelist', fields=L(0))
        elif name == 'goto':
            b = mk('motion_gotoxy', {'X': ('num', X(0)), 'Y': ('num', X(1))})
        elif name == 'set_x':
            b = mk('motion_setx', {'X': ('num', X(0))})
        elif name == 'set_y':
            b = mk('motion_sety', {'Y': ('num', X(0))})
        elif name == 'change_x':
            b = mk('motion_changexby', {'DX': ('num', X(0))})
        elif name == 'change_y':
            b = mk('motion_changeyby', {'DY': ('num', X(0))})
        elif name == 'costume':
            b = mk('looks_switchcostumeto', {'COSTUME': (('menu', 'looks_costume', 'COSTUME', 'c1'), X(0))})
        elif name == 'effect':
            eff = self.fold_str(args[0], e).upper()
            b = mk('looks_seteffectto', {'VALUE': ('num', X(1))}, {'EFFECT': [eff, None]})
        elif name == 'clear_effects':
            b = mk('looks_cleargraphiceffects')
        elif name == 'show':
            b = mk('looks_show')
        elif name == 'hide':
            b = mk('looks_hide')
        elif name == 'size':
            b = mk('looks_setsizeto', {'SIZE': ('num', X(0))})
        elif name == 'point':
            b = mk('motion_pointindirection', {'DIRECTION': ('num', X(0))})
        elif name == 'front':
            b = mk('looks_gotofrontback', fields={'FRONT_BACK': ['front', None]})
        elif name == 'stamp':
            b = mk('pen_stamp')
        elif name == 'pen_down':
            b = mk('pen_penDown')
        elif name == 'pen_up':
            b = mk('pen_penUp')
        elif name == 'pen_clear':
            b = mk('pen_clear')
        elif name == 'pen_color':
            b = mk('pen_setPenColorToColor', {'COLOR': ('color', X(0))})
        elif name == 'pen_size':
            b = mk('pen_setPenSizeTo', {'SIZE': ('num', X(0))})
        elif name == 'pen_alpha':
            # pen transparency 0 (opaque) .. 100 (invisible)
            b = mk('pen_setPenColorParamTo', {'COLOR_PARAM': (('menu', 'pen_menu_colorParam', 'colorParam', 'transparency'), ('lit', 'transparency')),
                                               'VALUE': ('num', X(0))})
        elif name == 'sound_start':
            b = mk('sound_play', {'SOUND_MENU': (('menu', 'sound_sounds_menu', 'SOUND_MENU', ''), X(0))})
        elif name == 'sound_stop_all':
            b = mk('sound_stopallsounds')
        elif name == 'sound_volume':
            b = mk('sound_setvolumeto', {'VOLUME': ('num', X(0))})
        elif name in ('sound_pitch', 'sound_pan'):
            b = mk('sound_seteffectto', {'VALUE': ('num', X(0))}, {'EFFECT': ['PITCH' if name == 'sound_pitch' else 'PAN', None]})
        elif name == 'music_note':
            b = mk('music_playNoteForBeats', {'NOTE': (('menu', 'note', 'NOTE', '60'), X(0)), 'BEATS': ('num', X(1))})
        elif name == 'music_drum':
            b = mk('music_playDrumForBeats', {'DRUM': (('menu', 'music_menu_DRUM', 'DRUM', '1'), X(0)), 'BEATS': ('num', X(1))})
        elif name == 'music_rest':
            b = mk('music_restForBeats', {'BEATS': ('num', X(0))})
        elif name == 'music_instrument':
            b = mk('music_setInstrument', {'INSTRUMENT': (('menu', 'music_menu_INSTRUMENT', 'INSTRUMENT', '1'), X(0))})
        elif name == 'music_tempo':
            b = mk('music_setTempo', {'TEMPO': ('num', X(0))})
        elif name == 'wait':
            b = mk('control_wait', {'DURATION': ('posnum', X(0))})
        elif name == 'wait_until':
            b = mk('control_wait_until', {'CONDITION': ('bool', X(0))})
        elif name in ('broadcast', 'broadcast_wait'):
            msg = self.fold_str(args[0], e)
            bid = self.gen.broadcast_id(msg)
            b = mk('event_broadcast' if name == 'broadcast' else 'event_broadcastandwait')
            self.blocks[b]['inputs']['BROADCAST_INPUT'] = [1, [11, msg, bid]]
        elif name == 'clone_self':
            sid = mk('control_create_clone_of_menu', fields={'CLONE_OPTION': ['_myself_', None]}, shadow=True)
            b = mk('control_create_clone_of')
            self.blocks[b]['inputs']['CLONE_OPTION'] = [1, sid]
            self.blocks[sid]['parent'] = b
        elif name == 'delete_clone':
            b = mk('control_delete_this_clone')
        elif name == 'stop_all':
            b = mk('control_stop', fields={'STOP_OPTION': ['all', None]},
                   mutation={'tagName': 'mutation', 'children': [], 'hasnext': 'false'})
        elif name == 'stop_others':
            b = mk('control_stop', fields={'STOP_OPTION': ['other scripts in sprite', None]},
                   mutation={'tagName': 'mutation', 'children': [], 'hasnext': 'true'})
        elif name == 'stop_script':
            b = mk('control_stop', fields={'STOP_OPTION': ['this script', None]},
                   mutation={'tagName': 'mutation', 'children': [], 'hasnext': 'false'})
        elif name == 'reset_timer':
            b = mk('sensing_resettimer')
        else:
            self.err(e, f"unknown statement function '{name}'")
        self.pre = None
        out.append(b)
        return out

    # --- scripts -----------------------------------------------------------
    def restore_ids(self):
        out = []
        sv = self.lists['_save']
        for key in reversed(self.ctx.saved):
            v = self.vars[key]
            item = self.mk('data_itemoflist', {'INDEX': ('int', ('lit', 'last'))}, {'LIST': [sv[1], sv[0]]})
            out.append(self.set_var_stmt(v, ('blk', item, False)))
            out.append(self.mk('data_deleteoflist', {'INDEX': ('int', ('lit', 'last'))}, {'LIST': [sv[1], sv[0]]}))
        return out

    def save_ids(self):
        out = []
        sv = self.lists['_save']
        for key in self.ctx.saved:
            v = self.vars[key]
            out.append(self.mk('data_addtolist', {'ITEM': ('str', ('var', v[1], v[0]))}, {'LIST': [sv[1], sv[0]]}))
        return out

    def compile_proc(self, p):
        info = self.procs[p['name']]
        ctx = Ctx(p['name'], info)
        self.ctx = ctx
        if info.recursive:
            # pre-scan locals so return statements know what to restore
            self.prescan_locals(p['body'], ctx)
        body_ids = self.stmts(p['body'])
        # function-level restore at end
        if info.recursive:
            # A second pass is required: temps/flags discovered during compile were added to
            # ctx.saved after some returns were compiled.  To keep it simple we recompile the
            # body with the now-complete saved list.
            saved_final = list(ctx.saved)
            # discard old blocks generated for this proc
            new_ids = set(self._collect_new)
            self.blocks = {k: v for k, v in self.blocks.items() if k not in new_ids}
            ctx2 = Ctx(p['name'], info)
            ctx2.saved = saved_final
            ctx2.fixed_saved = True
            self.ctx = ctx2
            self.prescan_locals(p['body'], ctx2)
            body_ids = self.stmts(p['body'])
            body_ids = self.save_ids() + body_ids + self.restore_ids()
        # prototype
        proto = self.newid()
        defn = self.newid()
        arg_shadows = {}
        for aid, pname in zip(info.argids, info.params):
            sid = self.newid()
            self.blocks[sid] = {'opcode': 'argument_reporter_string_number', 'next': None, 'parent': proto,
                                'inputs': {}, 'fields': {'VALUE': [pname, None]}, 'shadow': True, 'topLevel': False}
            arg_shadows[aid] = [1, sid]
        self.blocks[proto] = {
            'opcode': 'procedures_prototype', 'next': None, 'parent': defn, 'inputs': arg_shadows, 'fields': {},
            'shadow': True, 'topLevel': False,
            'mutation': {'tagName': 'mutation', 'children': [], 'proccode': info.proccode,
                         'argumentids': json.dumps(info.argids), 'argumentnames': json.dumps(info.params),
                         'argumentdefaults': json.dumps([''] * len(info.params)),
                         'warp': 'true' if info.warp else 'false'}}
        self.blocks[defn] = {'opcode': 'procedures_definition', 'next': None, 'parent': None,
                             'inputs': {'custom_block': [1, proto]}, 'fields': {}, 'shadow': False,
                             'topLevel': True, 'x': 0, 'y': self.top_y}
        self.top_y += 400
        first = self.link(body_ids)
        if first:
            self.blocks[defn]['next'] = first
            self.blocks[first]['parent'] = defn

    def prescan_locals(self, body, ctx):
        for s in body:
            if s.kind == 'local':
                for name, _ in s.a[0]:
                    key = f"{ctx.name}.{name}"
                    self.declare(key, False, 0)
                    if key not in ctx.saved:
                        ctx.saved.append(key)
            for sub in self.substatements(s):
                self.prescan_locals(sub, ctx)

    def substatements(self, s):
        k = s.kind
        if k == 'if':
            return [s.a[1], s.a[2] or []]
        if k in ('while', 'repeat', 'forever'):
            return [s.a[-1]]
        if k == 'for':
            return [s.a[3]]
        if k == 'block':
            return [s.a[0]]
        if k == 'switch':
            return [b for _, b in s.a[1]] + [s.a[2] or []]
        return []

    def compile_hat(self, h, idx):
        ctx = Ctx(f"on{idx}")
        self.ctx = ctx
        ev = h['event']
        if ev == 'flag':
            hat = self.mk('event_whenflagclicked', top=True)
        elif ev == 'clone':
            hat = self.mk('control_start_as_clone', top=True)
        elif ev == 'msg':
            bid = self.gen.broadcast_id(h['arg'])
            hat = self.mk('event_whenbroadcastreceived', fields={'BROADCAST_OPTION': [h['arg'], bid]}, top=True)
        elif ev == 'key':
            hat = self.mk('event_whenkeypressed', fields={'KEY_OPTION': [h['arg'], None]}, top=True)
        else:
            raise CompileError(f"{h['line']}: unknown event {ev}")
        ids = self.stmts(h['body'])
        first = self.link(ids)
        if first:
            self.blocks[hat]['next'] = first
            self.blocks[first]['parent'] = hat

    def compile(self):
        for p in self.spr['procs']:
            before = set(self.blocks)
            self._collect_new = _NewTracker(self, before)
            self.compile_proc(p)
        for i, h in enumerate(self.spr['hats']):
            self.compile_hat(h, i)
        # strip RESTORE placeholders (unused path)
        return self.blocks


class _NewTracker:
    """Iterable of block ids created since construction (used to discard a first-pass compile)."""

    def __init__(self, gen, before):
        self.gen = gen
        self.before = before

    def __iter__(self):
        return iter([k for k in self.gen.blocks if k not in self.before])


# Patch: restore_locals produces real blocks (needs saved list complete -> second pass handles it)
def _restore_locals(self):
    if not self.ctx.proc or not self.ctx.proc.recursive:
        return []
    return self.restore_ids()


SpriteGen.restore_locals = _restore_locals


# --------------------------------------------------------------------------
# Program / project assembly
# --------------------------------------------------------------------------

class Program:
    def __init__(self, data=None):
        self.data = data or {}
        self.consts = {}
        self.prog = {'globals': [], 'sprites': {}}
        self.loaded = set()
        self.broadcasts = {}

    def broadcast_id(self, name):
        if name not in self.broadcasts:
            self.broadcasts[name] = 'bc_' + re.sub(r'[^A-Za-z0-9]', '_', name)
        return self.broadcasts[name]

    def load(self, path, relto=None, target=None, members=False):
        if relto:
            path = os.path.join(os.path.dirname(relto), path)
        path = os.path.normpath(path)
        if path in self.loaded:
            return
        self.loaded.add(path)
        with open(path, encoding='utf-8') as f:
            src = f.read()
        toks = lex(src, os.path.relpath(path))
        p = Parser(toks, self.consts, lambda pth, rel, tg, members: self.load(pth, rel, tg, members))
        if members:
            while p.cur.kind != 'eof':
                p.parse_member(target)
        else:
            p.parse_program(self.prog)

    def build_targets(self, costume_provider, sound_provider=None):
        """Returns list of target dicts (without asset bytes) and asset map."""
        stage_vars = {'vars': {}, 'lists': {}}
        stage_var_values = {}
        stage_list_values = {}
        for g in self.prog['globals']:
            vid = f"G.{'L' if g['list'] else 'V'}.{g['name']}"
            if g['list']:
                stage_vars['lists'][g['name']] = (vid, g['name'])
                init = g['init']
                if isinstance(init, tuple) and init[0] == 'data':
                    init = self.data[init[1]]
                stage_list_values[g['name']] = init or []
            else:
                disp = ('☁ ' + g['name']) if g.get('cloud') else g['name']
                stage_vars['vars'][g['name']] = (vid, disp)
                stage_var_values[g['name']] = 0 if g['init'] is None else g['init']
        sprites = self.prog['sprites']
        if 'Stage' not in sprites:
            sprites['Stage'] = {'name': 'Stage', 'stage': True, 'vars': [], 'procs': [], 'hats': [],
                                'costumes': ['backdrop'], 'props': {}}
        targets = []
        assets = {}
        order = ['Stage'] + [n for n in sprites if n != 'Stage']
        layer = 0
        for name in order:
            spr = sprites[name]
            sg = SpriteGen(self, spr, self, None, stage_vars)
            blocks = sg.compile()
            costumes = []
            for group in spr['costumes'] or (['backdrop'] if spr['stage'] else []):
                for c in costume_provider(group):
                    assets[c['md5ext']] = c.pop('_bytes')
                    costumes.append(c)
            sounds = []
            for group in spr.get('sounds', []):
                for snd in sound_provider(group):
                    assets[snd['md5ext']] = snd.pop('_bytes')
                    sounds.append(snd)
            variables = {}
            lists = {}
            if spr['stage']:
                for n, (vid, disp) in stage_vars['vars'].items():
                    variables[vid] = [disp, stage_var_values[n]]
                    if disp.startswith('☁ '):
                        variables[vid].append(True)
                for n, (vid, disp) in stage_vars['lists'].items():
                    lists[vid] = [disp, stage_list_values[n]]
            for n, (vid, disp) in sg.vars.items():
                variables[vid] = [disp, sg.var_values[n]]
            for n, (vid, disp) in sg.lists.items():
                lists[vid] = [disp, sg.list_values[n]]
            t = {
                'isStage': spr['stage'], 'name': name, 'variables': variables, 'lists': lists,
                'broadcasts': {}, 'blocks': blocks, 'comments': {}, 'currentCostume': 0,
                'costumes': costumes, 'sounds': sounds, 'volume': 100, 'layerOrder': layer,
            }
            if spr['stage']:
                t.update({'tempo': 60, 'videoTransparency': 50, 'videoState': 'off', 'textToSpeechLanguage': None})
            else:
                props = spr['props']
                t.update({'visible': bool(props.get('visible', 0)), 'x': 0, 'y': 0, 'size': 100, 'direction': 90,
                          'draggable': False, 'rotationStyle': 'don\'t rotate'})
            targets.append(t)
            layer += 1
        stage = targets[0]
        stage['broadcasts'] = {bid: n for n, bid in self.broadcasts.items()}
        return targets, assets


def prune_unused(targets, keep=()):
    """Remove what the project cannot use: custom block definitions that no
    script reaches (directly or through other blocks), then variables and
    lists that no remaining block refers to.  `keep` names variables / lists
    that outside tools read (the test harness).  Returns removal counts."""
    removed = {'procs': 0, 'blocks': 0, 'vars': 0, 'lists': 0, 'names': []}
    for t in targets:
        blocks = t['blocks']

        def root(bid):
            while True:
                b = blocks[bid]
                if isinstance(b, list) or b.get('topLevel') or b.get('parent') is None:
                    return bid
                bid = b['parent']
        roots = {}
        for bid, b in blocks.items():
            roots.setdefault(root(bid), []).append(bid)
        # each definition script: its proccode; every script: the procs it calls
        defs = {}
        calls = {}
        for r, members in roots.items():
            rb = blocks[r]
            if isinstance(rb, dict) and rb['opcode'] == 'procedures_definition':
                proto = blocks[rb['inputs']['custom_block'][1]]
                defs[proto['mutation']['proccode']] = r
            calls[r] = {blocks[m]['mutation']['proccode'] for m in members
                        if isinstance(blocks[m], dict) and blocks[m]['opcode'] == 'procedures_call'}
        live = set()
        todo = [r for r in roots if not (isinstance(blocks[r], dict) and blocks[r]['opcode'] == 'procedures_definition')
                and isinstance(blocks[r], dict) and blocks[r]['opcode'].startswith(('event_', 'control_start_as_clone'))]
        live.update(todo)
        while todo:
            r = todo.pop()
            for pc in calls.get(r, ()):
                d = defs.get(pc)
                if d is not None and d not in live:
                    live.add(d)
                    todo.append(d)
        for pc, r in defs.items():
            if r not in live:
                for m in roots[r]:
                    del blocks[m]
                removed['procs'] += 1
                removed['blocks'] += len(roots[r])
                removed['names'].append('proc ' + pc.split(' ')[0])
    # writes to variables / lists that nothing reads: a Scratch reporter has
    # no side effects, so the statement can go (repeat: a removed write may
    # have been the last reader of another variable)
    WRITES = {'data_setvariableto', 'data_changevariableby', 'data_addtolist', 'data_deleteoflist',
              'data_deletealloflist', 'data_insertatlist', 'data_replaceitemoflist'}
    READS = {'data_variable', 'data_itemoflist', 'data_lengthoflist', 'data_listcontainsitem',
             'data_itemnumoflist', 'data_listcontents'}
    keep_ids = set()
    for t in targets:
        for kind in ('variables', 'lists'):
            for vid, v in t[kind].items():
                if v[0] in keep or str(v[0]).startswith('☁'):
                    keep_ids.add(vid)
    while True:
        read = set()
        for t in targets:
            for b in t['blocks'].values():
                if isinstance(b, list):
                    read.add(b[2])
                    continue
                for v in b.get('inputs', {}).values():
                    for x in v[1:]:
                        if isinstance(x, list) and x and x[0] in (12, 13):
                            read.add(x[2])
                if b['opcode'] in READS:
                    for k in ('VARIABLE', 'LIST'):
                        if k in b.get('fields', {}):
                            read.add(b['fields'][k][1])
        dead = 0
        for t in targets:
            blocks = t['blocks']
            for bid in list(blocks):
                b = blocks.get(bid)
                if not isinstance(b, dict) or b['opcode'] not in WRITES:
                    continue
                f = b['fields'].get('VARIABLE') or b['fields'].get('LIST')
                if f[1] in read or f[1] in keep_ids:
                    continue
                _splice_out(blocks, bid)
                dead += 1
        removed['writes'] = removed.get('writes', 0) + dead
        if dead == 0:
            break
    used = set()
    for t in targets:
        for b in t['blocks'].values():
            if isinstance(b, list):
                used.add(b[2])
                continue
            for v in b.get('inputs', {}).values():
                for x in v[1:]:
                    if isinstance(x, list) and x and x[0] in (12, 13):
                        used.add(x[2])
            for k, v in b.get('fields', {}).items():
                if k in ('VARIABLE', 'LIST') and len(v) > 1:
                    used.add(v[1])
    for t in targets:
        for kind, key in (('variables', 'vars'), ('lists', 'lists')):
            for vid in list(t[kind]):
                if vid not in used and t[kind][vid][0] not in keep and not str(t[kind][vid][0]).startswith('☁'):
                    removed['names'].append(key[:-1] + ' ' + t[kind][vid][0])
                    del t[kind][vid]
                    removed[key] += 1
    return removed


def _splice_out(blocks, bid):
    """Remove statement bid (and its input blocks) from its script."""
    b = blocks[bid]
    parent, nxt = b.get('parent'), b.get('next')
    if parent is not None:
        p = blocks[parent]
        if p.get('next') == bid:
            p['next'] = nxt
        for k, v in p.get('inputs', {}).items():
            if len(v) > 1 and v[1] == bid:
                if nxt is None:
                    del p['inputs'][k]
                else:
                    v[1] = nxt
                break
    if nxt is not None:
        blocks[nxt]['parent'] = parent
        if b.get('topLevel'):
            blocks[nxt].update(topLevel=True, x=b.get('x', 0), y=b.get('y', 0))
    todo = [bid]
    while todo:
        x = todo.pop()
        xb = blocks.pop(x, None)
        if isinstance(xb, dict):
            for v in xb.get('inputs', {}).values():
                for y in v[1:]:
                    if isinstance(y, str) and y in blocks and y != nxt:
                        todo.append(y)


def count_blocks(targets):
    return sum(len(t['blocks']) for t in targets)
