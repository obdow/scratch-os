// Regression test: boots ScratchOS headlessly in TurboWarp and checks the
// console output of a series of commands.
//
//   node regress.js ../ScratchOS.sb3
//
// Exit code 0 when every check passes.
const { launch } = require('./harness');

const CHECKS = [
  // [command, substring expected on screen afterwards, wait ms]
  ['clear', 'user@scratchos', 800],
  ['test.wsk', '30 passed, 0 failed', 6000],
  ['clear', 'user@scratchos', 800],
  ['echo hello $USER | rev', 'resu olleh', 2500],
  ['ls /bin | grep edit', 'edit.wsk', 2500],
  ['seq 4 | sort -r -n | head -n 1', '\n4', 2500],
  ['projects/primes.wsk 30', '10 primes up to 30', 2500],
  ['false || echo fallback', 'fallback', 1200],
  ['X=7; echo x=$X', 'x=7', 1200],
  ['cd /tmp && mkdir -p d/e && cd d && pwd', '/tmp/d', 3000],
  ['cd; touch /tmp/f1 && ls /tmp', 'f1', 3000],
  ['cat /etc/hostname', 'ScratchOS', 1500],
  ['calc 6*7', '42', 2500],
  ['clear', 'user@scratchos', 800],
  ['echo \'print(string.format("%05.1f|%x", 3.14159, 255))\' > /tmp/f.wsk; run /tmp/f.wsk', '003.1|ff', 3000],
  ['echo \'local t = {} for i = 1, 300 do t[i] = {i} end print(#t, t[300][1])\' > /tmp/g.wsk; run /tmp/g.wsk', '300     300', 3000],
];

function screenText(page) {
  return page.evaluate(() => {
    const t = vm.runtime.getSpriteTargetByName('Kernel');
    const L = (name) => Object.values(t.variables).find((l) => l.name === name && l.type === 'list').value;
    const V = (name) => Object.values(t.variables).find((v) => v.name === name && v.type !== 'list').value;
    const tty = V('con');
    const ch = L('cell_ch'), cp = L('cp437');
    const base = +L('tty_base')[tty - 1], top = +L('tty_top')[tty - 1];
    const w = +L('tty_w')[tty - 1], h = +L('tty_h')[tty - 1];
    const rows = [];
    for (let r = 0; r < h; r++) {
      let line = '';
      for (let c = 0; c < w; c++) {
        const code = +ch[base + ((r + top) % h) * w + c];
        line += code === 0 || code === 32 ? ' ' : code === 9 ? '\t' : (cp[code] || '?');
      }
      rows.push(line.replace(/\s+$/, ''));
    }
    return rows.join('\n');
  });
}

(async () => {
  const h = await launch(process.argv[2] || '../ScratchOS.sb3');
  const p = h.page;
  const tap = async (k) => { await p.keyboard.down(k); await h.sleep(60); await p.keyboard.up(k); await h.sleep(30); };
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await tap('Escape');
  for (let i = 0; i < 400 && !((await h.read('Kernel', 'frames')) > 0); i++) await h.sleep(50);
  await h.sleep(1500);
  let fails = 0;
  for (const [cmd, want, wait] of CHECKS) {
    for (const ch of cmd) {
      if (ch === ' ') { await tap('Space'); continue; }
      if (/[A-Z~!@#$%^&*()_+{}|:"<>?]/.test(ch)) {
        await p.keyboard.down('Shift'); await h.sleep(15);
        await p.keyboard.down(ch); await h.sleep(50); await p.keyboard.up(ch); await h.sleep(15);
        await p.keyboard.up('Shift'); await h.sleep(30);
        continue;
      }
      await tap(ch);
    }
    await tap('Enter');
    await h.sleep(wait);
    const screen = await screenText(p);
    const ok = screen.includes(want);
    if (!ok) fails++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${cmd}`);
    if (!ok) console.log('--- screen ---\n' + screen + '\n--------------');
  }
  const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
  if (errs.length) { console.log(errs.join('\n')); fails++; }
  console.log(`${CHECKS.length - fails}/${CHECKS.length} checks passed`);
  await h.close();
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
