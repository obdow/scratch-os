// Whisker 3D end to end: make a project in the engine, export it, and play
// the exported .txt in both players.
//
//   node w3d-e2e.js [engine.sb3] [player720.sb3] [player480.sb3] [outdir]
//
// The 480 x 360 player runs like scratch.mit.edu would (no compiler,
// fencing on, 30 fps).  Exit code 0 when every check passes.
const fs = require('fs');
const path = require('path');
const { launch } = require('./harness');

const ROOT = path.join(__dirname, '..');
const [engine, p720, p480, outdir] = [
  process.argv[2] || path.join(ROOT, 'Whisker3D.sb3'),
  process.argv[3] || path.join(ROOT, 'Whisker3D-Player-720p.sb3'),
  process.argv[4] || path.join(ROOT, 'Whisker3D-Player-480x360.sb3'),
  process.argv[5] || path.join(__dirname, 'out', 'w3d'),
];
fs.mkdirSync(outdir, { recursive: true });
let fails = 0;
const check = (ok, what) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`); if (!ok) fails++; };

const kernel = (h, name) => h.read('Kernel', name);
async function cmd(h, c, wait = 800) {
  await h.page.evaluate((c) => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    Object.values(t.variables).find((v) => v.name === 'w3e_testcmd').value = c;
  }, c);
  await h.sleep(wait);
}
const stageList = (h, name) => h.page.evaluate((n) => {
  const st = vm.runtime.getTargetForStage();
  return Object.values(st.variables).find((v) => v.name === n && v.type === 'list').value.slice();
}, name);

const kernelList = (h, name) => h.page.evaluate((n) => {
  const t = vm.runtime.getSpriteTargetByName('Kernel');
  return Object.values(t.variables).find((v) => v.name === n && v.type === 'list').value.slice();
}, name);

// the Help pages open, and a scene edited as text is not overwritten
async function editorChecks(h) {
  for (const [c, file] of [['w3help', '/docs/getting-started.txt'], ['w3ref', '/docs/w3d-library.txt'],
    ['ref', '/docs/whisker/reference.txt']]) {
    await cmd(h, c);
    check((await kernelList(h, 'tab_path')).includes(file), `engine: Help opens ${file}`);
  }
  const added = await h.page.evaluate(() => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const L = (n) => Object.values(t.variables).find((v) => v.name === n && v.type === 'list').value;
    const name = L('fs_name');
    const parent = L('fs_parent');
    const data = L('fs_data');
    for (let i = 0; i < name.length; i++) {
      const p = parent[i] - 1;
      if (name[i] === 'main.scene' && name[p] === 'scenes' && name[parent[p] - 1] === 'E2E 720') {
        data[i] = data[i] + '\nobject "Typed" mesh\n  mesh cube\n  pos 1 2 3\n';
        return true;
      }
    }
    return false;
  });
  await cmd(h, 'vscene');
  check(added && (await kernelList(h, 'ob_name')).includes('Typed'), 'engine: a scene edited as text is reloaded');
  await cmd(h, 'save');
  const text = await h.page.evaluate(() => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const L = (n) => Object.values(t.variables).find((v) => v.name === n && v.type === 'list').value;
    return L('fs_data').find((d) => typeof d === 'string' && /object "?Typed"? mesh/.test(d)) || '';
  });
  check(text.includes('pos 1 2 3'), 'engine: saving keeps the text edit');
}

async function exportProject(res) {
  const h = await launch(engine);
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await h.sleep(3000);
  await cmd(h, 'prompt:newproj:E2E ' + res);
  await cmd(h, res === 480 ? 'button:np480' : 'button:np720');
  await cmd(h, 'button:create', 3000);
  check((await kernel(h, 'w3e_mode')) == 1, `engine: a ${res} project opens in the scene editor`);
  await h.shot(path.join(outdir, `editor-${res}.png`));
  if (res === 720) await editorChecks(h);
  await cmd(h, 'exportproj', 3000);
  const lines = await stageList(h, 'w3d_export');
  check(lines.length > 20 && lines[0] === 'WHISKER3D 1', `engine: export gives a bundle (${lines.length} lines)`);
  check(lines.some((l) => l.startsWith('@file .build/scripts/player.wsk')), 'engine: the bundle has the compiled scripts');
  check(!lines.some((l) => /[,;|"\t]/.test(l)) && !lines.includes(''), 'engine: no line has characters CSV import would split on');
  const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
  check(errs.length === 0, 'engine: no page errors ' + errs.join(' '));
  await h.close();
  return lines;
}

async function play(sb3, lines, name, opts) {
  const h = await launch(sb3, { lists: { game: lines }, ...opts });
  await h.sleep(4000);
  // walk forward for a moment
  await h.page.keyboard.down('w');
  await h.sleep(1500);
  await h.page.keyboard.up('w');
  await h.sleep(500);
  const err = await kernel(h, 'g_err');
  const on = await kernel(h, 'g_on');
  const stats = await kernel(h, 'w3_stats');
  await h.shot(path.join(outdir, `${name}.png`));
  check(on == 1 && !err, `${name}: the game runs (${stats}) ${err || ''}`);
  const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
  check(errs.length === 0, `${name}: no page errors ${errs.join(' ')}`);
  await h.close();
}

(async () => {
  const l720 = await exportProject(720);
  await play(p720, l720, 'player-720p', {});
  const l480 = await exportProject(480);
  await play(p480, l480, 'player-480x360', { vanilla: true });
  console.log(fails ? `${fails} check(s) failed` : 'all checks passed');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
