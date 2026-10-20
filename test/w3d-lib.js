// Helpers for the Whisker 3D tests: compile a project folder with the
// engine (import + File > Export project) and play a bundle in a player.
const { execFileSync } = require('child_process');
const path = require('path');
const { launch } = require('./harness');

const ROOT = path.join(__dirname, '..');

const setKernel = (h, name, v) => h.page.evaluate(([n, v]) => {
  const t = vm.runtime.getSpriteTargetByName('Kernel');
  Object.values(t.variables).find((x) => x.name === n).value = v;
}, [name, v]);

const stageList = (h, name) => h.page.evaluate((n) => {
  const st = vm.runtime.getTargetForStage();
  return Object.values(st.variables).find((v) => v.name === n && v.type === 'list').value.slice();
}, name);

function pack(dir) {
  return execFileSync('python3', [path.join(ROOT, 'tools', 'w3d_bundle.py'), 'pack', dir], { encoding: 'utf8' })
    .replace(/\n$/, '').split('\n');
}

// returns {lines, error}
async function compileWithEngine(engine, dir, name) {
  const h = await launch(engine, { lists: { w3d_import: pack(dir) } });
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await h.sleep(3000);
  await setKernel(h, 'w3e_testcmd', 'prompt:importproj:' + (name || 'test')); await h.sleep(2500);
  await setKernel(h, 'w3e_testcmd', 'exportproj'); await h.sleep(3000);
  const lines = await stageList(h, 'w3d_export');
  let error = '';
  if (lines.length < 10) error = (await h.read('Kernel', 'xs_err')) || (await h.read('Kernel', 'pj_err')) || 'no export';
  await h.close();
  return { lines, error };
}

async function readLog(h) {
  return h.page.evaluate(() => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const L = (n) => Object.values(t.variables).find((l) => l.name === n && l.type === 'list').value;
    const names = L('fs_name'), data = L('fs_data'), parent = L('fs_parent'), used = L('fs_used');
    for (let i = 0; i < names.length; i++) if (used[i] == 1 && names[i] === 'log.txt' && parent[i] == 1) return String(data[i]);
    return '';
  });
}

module.exports = { ROOT, setKernel, stageList, pack, compileWithEngine, readLog };
