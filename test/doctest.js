// Checks the examples in the documentation against the real Whisker runtime.
//
//   node doctest.js [files.md ...]          (default: ../docs/whisker/*.md)
//   node doctest.js --keep ...              keep the generated files
//
// A ```lua block followed by an ```output block is a test: the program is run
// in ScratchOS (`run prog.wsk > o 2> e < empty` from a shell script) and
// what it writes to stdout, then stderr, must equal the output block.  In
// the output block a line holding only `...` matches any number of lines.
// Tabs count as spaces to the next multiple of 8, colour escapes are
// dropped, and trailing spaces and trailing blank lines are ignored.
//
// The examples are baked into a copy of the root file system under
// /home/user/dt, so the build takes a few seconds before the browser starts.
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { launch } = require('./harness');

const ROOT = path.join(__dirname, '..');

function collect(files) {
  const tests = [];
  for (const file of files) {
    const lines = fs.readFileSync(file, 'utf8').split('\n');
    let i = 0;
    while (i < lines.length) {
      if (/^```lua\s*$/.test(lines[i])) {
        const start = i + 1;
        let j = start;
        while (j < lines.length && !/^```\s*$/.test(lines[j])) j++;
        const code = lines.slice(start, j).join('\n');
        let k = j + 1;
        while (k < lines.length && lines[k].trim() === '') k++;
        if (k < lines.length && /^```output\s*$/.test(lines[k])) {
          let m = k + 1;
          while (m < lines.length && !/^```\s*$/.test(lines[m])) m++;
          tests.push({ file: path.relative(ROOT, file), line: start, code, want: lines.slice(k + 1, m).join('\n') });
          i = m + 1;
          continue;
        }
        i = j + 1;
        continue;
      }
      i++;
    }
  }
  return tests;
}

// tabs become spaces (stops every 8 columns, as on screen); colour escapes go
function expand(line) {
  let out = '';
  for (const ch of line) out += ch === '\t' ? ' '.repeat(8 - (out.length % 8)) : ch;
  return out;
}
const norm = (s) => s.replace(/\r/g, '').replace(/\x1b\[[0-9;]*m/g, '').split('\n')
  .map((l) => expand(l).replace(/\s+$/, '')).join('\n').replace(/\n+$/, '');

function matches(got, want) {
  const g = norm(got).split('\n');
  const w = norm(want).split('\n');
  const go = (gi, wi) => {
    if (wi === w.length) return gi === g.length || (gi === g.length - 1 && g[gi] === '');
    if (w[wi] === '...') {
      for (let k = gi; k <= g.length; k++) if (go(k, wi + 1)) return true;
      return false;
    }
    return gi < g.length && g[gi] === w[wi] && go(gi + 1, wi + 1);
  };
  return go(0, 0);
}

async function main() {
  const args = process.argv.slice(2);
  const keep = args.includes('--keep');
  let files = args.filter((a) => !a.startsWith('--'));
  if (!files.length) {
    const dir = path.join(ROOT, 'docs', 'whisker');
    files = fs.readdirSync(dir).filter((f) => f.endsWith('.md')).sort().map((f) => path.join(dir, f));
  }
  const tests = collect(files);
  if (!tests.length) { console.log('no tests found'); return; }

  // a copy of the root file system with the examples and a script that runs them
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'whisker-doctest-'));
  const rfs = path.join(work, 'rootfs');
  fs.cpSync(path.join(ROOT, 'rootfs'), rfs, { recursive: true });
  const dt = path.join(rfs, 'home', 'user', 'dt');
  fs.mkdirSync(dt);
  fs.writeFileSync(path.join(dt, 'empty'), '');
  const script = [];
  // each example is /home/user/dt/<n>/prog.wsk, so errors read "prog.wsk:3: ..."
  tests.forEach((t, n) => {
    fs.mkdirSync(path.join(dt, String(n + 1)));
    fs.writeFileSync(path.join(dt, String(n + 1), 'prog.wsk'), t.code + '\n');
    script.push(`cd /home/user/dt/${n + 1}`);
    script.push('run prog.wsk > o 2> e < ../empty');
    script.push('touch d');
  });
  fs.writeFileSync(path.join(dt, 'all.sh'), script.join('\n') + '\n');
  const sb3 = path.join(work, 'doctest.sb3');
  execFileSync('python3', [path.join(ROOT, 'build.py'), '--rootfs', rfs, '-o', sb3], { stdio: 'ignore' });

  const h = await launch(sb3);
  const p = h.page;
  const tap = async (k) => { await p.keyboard.down(k); await h.sleep(60); await p.keyboard.up(k); await h.sleep(30); };
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await tap('Escape');
  for (let i = 0; i < 400 && !((await h.read('Kernel', 'frames')) > 0); i++) await h.sleep(50);
  await h.sleep(1500);
  for (const ch of 'cd dt; sh all.sh') await tap(ch === ' ' ? 'Space' : ch);
  await tap('Enter');

  // read /home/user/dt/<dir>/<name> from the kernel's file system (null if missing)
  const readFile = (dir, name) => p.evaluate(([dir, name]) => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const L = (n) => Object.values(t.variables).find((l) => l.name === n && l.type === 'list').value;
    const used = L('fs_used'), names = L('fs_name'), parent = L('fs_parent'), data = L('fs_data');
    for (let i = 0; i < names.length; i++) {
      const up = +parent[i] - 1;
      if (used[i] == 1 && String(names[i]) === name && String(names[up]) === dir && String(names[+parent[up] - 1]) === 'dt') return String(data[i]);
    }
    return null;
  }, [String(dir), name]);

  let fails = 0;
  for (let n = 1; n <= tests.length; n++) {
    const t = tests[n - 1];
    const where = `${t.file}:${t.line}`;
    let done = false;
    for (let w = 0; w < 600 && !done; w++) {     // 60 s per example
      done = (await readFile(n, 'd')) !== null;
      if (!done) await h.sleep(100);
    }
    if (!done) {
      console.log(`FAIL  ${where}  (no result after 60 s; later examples were not run)`);
      fails += tests.length - n + 1;
      break;
    }
    const got = ((await readFile(n, 'o')) || '') + ((await readFile(n, 'e')) || '');
    if (matches(got, t.want)) {
      console.log(`PASS  ${where}`);
    } else {
      fails++;
      console.log(`FAIL  ${where}\n--- expected ---\n${norm(t.want)}\n--- got ---\n${norm(got)}\n----------------`);
    }
  }
  const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
  if (errs.length) { console.log(errs.join('\n')); fails++; }
  await h.close();
  if (keep) console.log(`files kept in ${work}`); else fs.rmSync(work, { recursive: true, force: true });
  console.log(`${tests.length - fails}/${tests.length} examples passed`);
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
