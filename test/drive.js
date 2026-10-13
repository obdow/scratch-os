// Boot ScratchOS headlessly, type commands, take screenshots.
//
//   node drive.js ScratchOS.sb3 outdir [--noskip] [--wait=ms] -- "cmd 1" "cmd 2" ...
//
// Each command is typed followed by Enter; a screenshot outdir/NN.png is
// taken after each.  Special commands:
//   @sleep=ms   wait        @key=Name    press a key (Playwright key name)
//   @shot       screenshot  @ctrl=c      ctrl+key
//   @click=x,y  mouse click at stage coords (0..stage width, 0..stage height)
//   @drag=x1,y1,x2,y2   @move=x1,y1,x2,y2   @wheel=x,y,dy
//   @var=Sprite:name    print a variable or list
// Options: --scale=N renders the stage N times larger, --hq uses the
// high-quality pen (as the Whisker IDE's TurboWarp settings request).
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
  const scale = +((opts.find((o) => o.startsWith('--scale=')) || '--scale=1').split('=')[1]);
  const h = await launch(sb3, { scale, hq: opts.includes('--hq') });
  const p = h.page;
  const tap = async (k) => { await p.keyboard.down(k); await h.sleep(60); await p.keyboard.up(k); await h.sleep(30); };
  // wait for the keyboard clones, skip the boot animation, wait for the kernel loop
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  if (!opts.includes('--noskip')) await tap('Escape');
  for (let i = 0; i < 400 && !((await h.read('Kernel', 'frames')) > 0); i++) await h.sleep(50);
  await h.sleep(waitMs);
  let n = 0;
  const textMode = opts.includes('--text');
  const dump = async () => {
    const rows = await p.evaluate(() => {
      const t = vm.runtime.getSpriteTargetByName('Kernel');
      const L = (name) => Object.values(t.variables).find((l) => l.name === name && l.type === 'list').value;
      const V = (name) => Object.values(t.variables).find((v) => v.name === name && v.type !== 'list').value;
      const tty = (V('gui') == 1) ? (L('tty_win').findIndex((w, i) => L('tty_used')[i] == 1 && w > 0) + 1 || 1) : V('con');
      const ch = L('cell_ch'), base = +L('tty_base')[tty - 1], top = +L('tty_top')[tty - 1];
      const w = +L('tty_w')[tty - 1], h = +L('tty_h')[tty - 1];
      const cp = L('cp437');
      const out = [];
      for (let r = 0; r < h; r++) {
        let line = '';
        for (let c = 0; c < w; c++) {
          const code = +ch[base + ((r + top) % h) * w + c];
          line += code === 0 || code === 32 ? ' ' : (cp[code] || '?');
        }
        out.push(line.replace(/\s+$/, ''));
      }
      return out;
    });
    console.log(rows.join('\n').replace(/\n+$/, ''));
    console.log('-'.repeat(60));
  };
  const shot = async () => {
    n++;
    if (textMode) { await dump(); if (!opts.includes('--png')) return; }
    await h.shot(path.join(outdir, String(n).padStart(2, '0') + '.png'));
  };
  await shot();
  for (const c of cmds) {
    if (c.startsWith('@sleep=')) { await h.sleep(+c.slice(7)); continue; }
    if (c.startsWith('@var=')) {
      const [spr, name] = c.slice(5).split(':');
      console.log(`${spr}:${name} =`, JSON.stringify(await h.read(spr, name)));
      continue;
    }
    if (c === '@shot') { await shot(); continue; }
    if (c.startsWith('@key=')) { await tap(c.slice(5)); continue; }
    if (c.startsWith('@ctrl=')) {
      await p.keyboard.down('Control'); await h.sleep(30); await tap(c.slice(6)); await p.keyboard.up('Control'); await h.sleep(30);
      continue;
    }
    if (c.startsWith('@wheel=')) {
      // @wheel=x,y,dy  scroll the mouse wheel over a stage point
      const box = await (await p.$('canvas')).boundingBox();
      const v = c.split('=')[1].split(',').map(Number);
      await p.mouse.move(box.x + v[0] * box.width / h.stage.w, box.y + v[1] * box.height / h.stage.h);
      await h.sleep(60);
      await p.mouse.wheel(0, v[2]);
      await h.sleep(250);
      continue;
    }
    if (c.startsWith('@move=')) {
      const box = await (await p.$('canvas')).boundingBox();
      const v = c.split('=')[1].split(',').map(Number);
      const sx = box.width / h.stage.w, sy = box.height / h.stage.h;
      for (let k = 0; k <= 24; k++) {
        await p.mouse.move(box.x + (v[0] + (v[2] - v[0]) * k / 24) * sx, box.y + (v[1] + (v[3] - v[1]) * k / 24) * sy);
        await h.sleep(35);
      }
      continue;
    }
    if (c.startsWith('@click=') || c.startsWith('@drag=')) {
      const box = await (await p.$('canvas')).boundingBox();
      const v = c.split('=')[1].split(',').map(Number);
      const sx = box.width / h.stage.w, sy = box.height / h.stage.h;
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
