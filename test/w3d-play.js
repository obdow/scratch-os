// Play a Whisker 3D game folder in a player build, headlessly.
//
//   node w3d-play.js PLAYER.sb3 GAME_DIR [seconds] [out.png]
//
// Prints what the game's scripts printed (/log.txt) and why it stopped, if
// it did.  Exit code 1 if the game stopped with an error.
const { execFileSync } = require('child_process');
const path = require('path');
const { launch } = require('./harness');

async function play(sb3, dir, secs, png, keys) {
  const bundle = execFileSync('python3', [path.join(__dirname, '..', 'tools', 'w3d_bundle.py'), 'pack', dir], { encoding: 'utf8' })
    .replace(/\n$/, '').split('\n');
  const h = await launch(sb3, { lists: { game: bundle } });
  const t0 = Date.now();
  for (const k of keys || []) {
    await h.sleep(k.at - (Date.now() - t0) > 0 ? k.at - (Date.now() - t0) : 0);
    if (k.down) await h.page.keyboard.down(k.key); else await h.page.keyboard.up(k.key);
  }
  const left = secs * 1000 - (Date.now() - t0);
  if (left > 0) await h.sleep(left);
  const res = await h.page.evaluate(() => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const V = (n) => { const v = Object.values(t.variables).find((x) => x.name === n && x.type !== 'list'); return v ? v.value : undefined; };
    const L = (n) => Object.values(t.variables).find((l) => l.name === n && l.type === 'list').value;
    const names = L('fs_name'), data = L('fs_data'), parent = L('fs_parent'), used = L('fs_used');
    let log = '';
    for (let i = 0; i < names.length; i++) if (used[i] == 1 && names[i] === 'log.txt' && parent[i] == 1) log = String(data[i]);
    return { log, err: V('g_err'), on: V('g_on'), stats: V('w3_stats'), frames: V('frames') };
  });
  if (png) await h.shot(png);
  const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
  await h.close();
  return { ...res, pageErrors: errs };
}

module.exports = { play };

if (require.main === module) {
  (async () => {
    const [sb3, dir, secs, png] = process.argv.slice(2);
    const r = await play(sb3, dir, +(secs || 5), png);
    console.log('--- log ---\n' + r.log + '-----------');
    console.log('running:', r.on, ' frames:', r.frames, ' ', r.stats);
    if (r.err) console.log('stopped:', r.err);
    if (r.pageErrors.length) console.log(r.pageErrors.join('\n'));
    process.exit(r.err || r.pageErrors.length ? 1 : 0);
  })().catch((e) => { console.error(e); process.exit(1); });
}
