// Runs the Whisker 3D library checks (test/w3d/apitest): the project is
// imported into the engine, exported compiled, and played in a player; its
// test script prints PASS / FAIL lines.
//
//   node w3d-api.js [engine.sb3] [player.sb3] [--vanilla]
const { execFileSync } = require('child_process');
const path = require('path');
const { launch } = require('./harness');

const ROOT = path.join(__dirname, '..');
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const engine = args[0] || path.join(ROOT, 'Whisker3D.sb3');
const player = args[1] || path.join(ROOT, 'Whisker3D-Player-480x360.sb3');
const vanilla = process.argv.includes('--vanilla');

const setKernel = (h, name, v) => h.page.evaluate(([n, v]) => {
  const t = vm.runtime.getSpriteTargetByName('Kernel');
  Object.values(t.variables).find((x) => x.name === n).value = v;
}, [name, v]);
const stageList = (h, name) => h.page.evaluate((n) => {
  const st = vm.runtime.getTargetForStage();
  return Object.values(st.variables).find((v) => v.name === n && v.type === 'list').value.slice();
}, name);

async function compileWithEngine(dir) {
  const bundle = execFileSync('python3', [path.join(ROOT, 'tools', 'w3d_bundle.py'), 'pack', dir], { encoding: 'utf8' })
    .replace(/\n$/, '').split('\n');
  const h = await launch(engine, { lists: { w3d_import: bundle } });
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await h.sleep(3000);
  await setKernel(h, 'w3e_testcmd', 'prompt:importproj:apitest'); await h.sleep(2500);
  await setKernel(h, 'w3e_testcmd', 'exportproj'); await h.sleep(3000);
  const out = await stageList(h, 'w3d_export');
  if (out.length < 10) {
    console.log('engine state:', await h.read('Kernel', 'w3e_mode'), '|', await h.read('Kernel', 'xs_err'), '|',
      await h.read('Kernel', 'pj_err'), '|', await h.read('Kernel', 'idlg_title'), JSON.stringify(await h.read('Kernel', 'idlg_lines')));
  }
  await h.close();
  return out;
}

(async () => {
  const lines = await compileWithEngine(path.join(__dirname, 'w3d', 'apitest'));
  if (lines.length < 10) { console.log('FAIL  the engine did not export the project'); process.exit(1); }
  const h = await launch(player, { lists: { game: lines }, vanilla });
  await h.page.keyboard.down('w');
  let log = '';
  for (let i = 0; i < 40 && !/DONE/.test(log); i++) {
    await h.sleep(500);
    log = await h.page.evaluate(() => {
      const t = vm.runtime.getSpriteTargetByName('Kernel');
      const L = (n) => Object.values(t.variables).find((l) => l.name === n && l.type === 'list').value;
      const names = L('fs_name'), data = L('fs_data'), parent = L('fs_parent'), used = L('fs_used');
      for (let i = 0; i < names.length; i++) if (used[i] == 1 && names[i] === 'log.txt' && parent[i] == 1) return String(data[i]);
      return '';
    });
  }
  const err = await h.read('Kernel', 'g_err');
  const queued = await h.page.evaluate(() => {
    const st = vm.runtime.getTargetForStage();
    return Object.values(st.variables).find((v) => v.name === 'snd_k' && v.type === 'list').value.length;
  });
  log += (queued === 0 ? 'PASS' : 'FAIL') + ' the Sound sprite played everything queued (' + queued + ' left)\n';
  await h.close();
  process.stdout.write(log.split('\n').map((l) => l.replace(/^(PASS|FAIL) /, '$1  ')).join('\n'));
  if (err) console.log('game stopped: ' + err);
  const failed = (log.match(/^FAIL/mg) || []).length;
  const ok = /DONE/.test(log) && failed === 0 && !err;
  console.log(ok ? 'all checks passed' : `${failed} check(s) failed`);
  process.exit(ok ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
