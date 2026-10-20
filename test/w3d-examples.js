// Plays every Whisker 3D example (w3d/rootfs/examples) for a few seconds in
// the player for its resolution, after compiling it with the engine.
//
//   node w3d-examples.js [engine.sb3] [player720.sb3] [player480.sb3] [outdir]
const fs = require('fs');
const path = require('path');
const { launch } = require('./harness');
const { ROOT, compileWithEngine, readLog } = require('./w3d-lib');

const [engine, p720, p480, outdir] = [
  process.argv[2] || path.join(ROOT, 'Whisker3D.sb3'),
  process.argv[3] || path.join(ROOT, 'Whisker3D-Player-720p.sb3'),
  process.argv[4] || path.join(ROOT, 'Whisker3D-Player-480x360.sb3'),
  process.argv[5] || path.join(__dirname, 'out', 'w3d'),
];
fs.mkdirSync(outdir, { recursive: true });

(async () => {
  let fails = 0;
  const dir = path.join(ROOT, 'w3d', 'rootfs', 'examples');
  for (const ex of fs.readdirSync(dir).sort()) {
    const settings = fs.readFileSync(path.join(dir, ex, 'game.w3d'), 'utf8');
    const is480 = /resolution\s+480/.test(settings);
    const { lines, error } = await compileWithEngine(engine, path.join(dir, ex), ex.replace(/ /g, ''));
    if (error) { console.log(`FAIL  ${ex}: export: ${error}`); fails++; continue; }
    const h = await launch(is480 ? p480 : p720, { lists: { game: lines } });
    await h.sleep(3000);
    await h.page.keyboard.down('w');
    await h.sleep(1200);
    await h.page.keyboard.up('w');
    await h.page.mouse.click(is480 ? 240 : 640, is480 ? 230 : 450);
    await h.sleep(1500);
    const err = await h.read('Kernel', 'g_err');
    const stats = await h.read('Kernel', 'w3_stats');
    const log = await readLog(h);
    await h.shot(path.join(outdir, ex.replace(/ /g, '-') + '.png'));
    const pageErrs = h.logs.filter((l) => /PAGEERROR/.test(l));
    await h.close();
    const ok = !err && pageErrs.length === 0;
    if (!ok) fails++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${ex} (${is480 ? '480x360' : '1280x720'}): ${stats} ${err || ''} ${pageErrs.join(' ')}`);
    if (log.trim()) console.log('      printed: ' + log.trim().split('\n').slice(-3).join(' | '));
  }
  console.log(fails ? `${fails} example(s) failed` : 'all examples run');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
