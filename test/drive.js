// Boot ScratchOS headlessly, type commands, take screenshots.
//
//   node drive.js ScratchOS.sb3 outdir [--noskip] [--wait=ms] -- "cmd 1" "cmd 2" ...
//
// Each command is typed followed by Enter; a screenshot outdir/NN.png is
// taken after each.  Special commands:
//   @sleep=ms   wait        @key=Name    press a key (Playwright key name)
//   @shot       screenshot  @ctrl=c      ctrl+key
//   @click=x,y  mouse click at stage coords (0..480, 0..360)
//   @drag=x1,y1,x2,y2
const fs = require('fs');
const path = require('path');
const { launch } = require('./harness');

async function main() {
  const args = process.argv.slice(2);
  const sb3 = args[0];
  const outdir = args[1];
  const sep = args.indexOf('--');
  const opts = args.slice(2, sep < 0 ? undefined : sep);
  const cmds = sep < 0 ? [] : args.slice(sep + 1);
  const waitMs = +((opts.find((o) => o.startsWith('--wait=')) || '--wait=1500').split('=')[1]);
  fs.mkdirSync(outdir, { recursive: true });
  const h = await launch(sb3);
  const p = h.page;
  const tap = async (k) => { await p.keyboard.down(k); await h.sleep(35); await p.keyboard.up(k); await h.sleep(35); };
  // wait for the keyboard clones, skip the boot animation, wait for the kernel loop
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  if (!opts.includes('--noskip')) await tap('Escape');
  for (let i = 0; i < 400 && !((await h.read('Kernel', 'frames')) > 0); i++) await h.sleep(50);
  await h.sleep(waitMs);
  let n = 0;
  const shot = async () => { n++; await h.shot(path.join(outdir, String(n).padStart(2, '0') + '.png')); };
  await shot();
  for (const c of cmds) {
    if (c.startsWith('@sleep=')) { await h.sleep(+c.slice(7)); continue; }
    if (c === '@shot') { await shot(); continue; }
    if (c.startsWith('@key=')) { await tap(c.slice(5)); continue; }
    if (c.startsWith('@ctrl=')) {
      await p.keyboard.down('Control'); await h.sleep(30); await tap(c.slice(6)); await p.keyboard.up('Control'); await h.sleep(30);
      continue;
    }
    if (c.startsWith('@click=') || c.startsWith('@drag=')) {
      const box = await (await p.$('canvas')).boundingBox();
      const v = c.split('=')[1].split(',').map(Number);
      const sx = box.width / 480, sy = box.height / 360;
      await p.mouse.move(box.x + v[0] * sx, box.y + v[1] * sy);
      await h.sleep(60);
      await p.mouse.down();
      await h.sleep(60);
      if (v.length === 4) {
        for (let k = 1; k <= 8; k++) {
          await p.mouse.move(box.x + (v[0] + (v[2] - v[0]) * k / 8) * sx, box.y + (v[1] + (v[3] - v[1]) * k / 8) * sy);
          await h.sleep(40);
        }
      }
      await p.mouse.up();
      await h.sleep(150);
      continue;
    }
    for (const ch of c) {
      if (ch === ' ') { await tap('Space'); continue; }
      if (/[A-Z~!@#$%^&*()_+{}|:"<>?]/.test(ch)) {
        await p.keyboard.down('Shift'); await h.sleep(15);
        await p.keyboard.down(ch); await h.sleep(35); await p.keyboard.up(ch); await h.sleep(15);
        await p.keyboard.up('Shift'); await h.sleep(30);
        continue;
      }
      await tap(ch);
    }
    await tap('Enter');
    await h.sleep(+((opts.find((o) => o.startsWith('--cmdwait=')) || '--cmdwait=600').split('=')[1]));
    await shot();
  }
  const errs = h.logs.filter((l) => /error|PAGEERROR/i.test(l));
  if (errs.length) console.log(errs.join('\n'));
  console.log('frames', await h.read('Kernel', 'frames'));
  await h.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
