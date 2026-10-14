// End-to-end test of the ScratchOS network with the real ScratchOS project:
// starts a cloud relay and the data server, boots several copies of
// ScratchOS at once and has each upload and download through cloud
// variables, then checks the "no server" and "offline" states.
//
//   node net-e2e.js ../ScratchOS.sb3
//
// Exit code 0 when every check passes.
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { launch } = require('./harness');

const SERVER = path.join(__dirname, '..', 'server');
const PORT = 9800 + Math.floor(Math.random() * 100);
const HOST = `ws://localhost:${PORT}`;
const PROJECT = 'scratchos-e2e';
const DATA = fs.mkdtempSync(path.join(os.tmpdir(), 'scratchos-e2e-'));
fs.cpSync(path.join(SERVER, 'data'), DATA, { recursive: true });
const N = +(process.env.COPIES || 3);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let fails = 0;
function check(ok, what, screen) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
  if (!ok) { fails++; if (screen) console.log('--- screen ---\n' + screen + '\n--------------'); }
}
function start(file, env) {
  return spawn(process.execPath, [path.join(SERVER, file)], {
    env: { ...process.env, QUIET: '1', ...env }, stdio: ['ignore', 'inherit', 'inherit'],
  });
}

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
        line += code === 0 || code === 32 ? ' ' : (cp[code] || '?');
      }
      rows.push(line.replace(/\s+$/, ''));
    }
    return rows.join('\n');
  });
}

async function boot(cloud) {
  const h = await launch(path.resolve(process.argv[2] || '../ScratchOS.sb3'), { cloud });
  const p = h.page;
  h.tap = async (k) => { await p.keyboard.down(k); await h.sleep(60); await p.keyboard.up(k); await h.sleep(30); };
  h.type = async (cmd) => {
    for (const ch of cmd) {
      if (ch === ' ') { await h.tap('Space'); continue; }
      if (/[A-Z~!@#$%^&*()_+{}|:"<>?]/.test(ch)) {
        await p.keyboard.down('Shift'); await h.sleep(15);
        await p.keyboard.down(ch); await h.sleep(50); await p.keyboard.up(ch); await h.sleep(15);
        await p.keyboard.up('Shift'); await h.sleep(30);
        continue;
      }
      await h.tap(ch);
    }
    await h.tap('Enter');
  };
  // run a command and wait until the screen shows `want` (or time runs out)
  h.run = async (cmd, want, ms = 30000) => {
    await h.type('clear');
    await h.sleep(500);
    await h.type(cmd);
    const t = Date.now();
    let s = '';
    while (Date.now() - t < ms) {
      s = await screenText(p);
      if (s.includes(want)) return { ok: true, s, secs: (Date.now() - t) / 1000 };
      await h.sleep(300);
    }
    return { ok: false, s };
  };
  for (let i = 0; i < 200 && (await h.read('Stage', 'kb_ready')) != 1; i++) await h.sleep(50);
  await h.tap('Escape');
  for (let i = 0; i < 400 && !((await h.read('Kernel', 'frames')) > 0); i++) await h.sleep(50);
  await h.sleep(1500);
  return h;
}

(async () => {
  const relay = start('relay.js', { PORT: String(PORT) });
  await sleep(500);
  let server = start('scratchos-server.js', { CLOUD_HOST: HOST, PROJECT_ID: PROJECT, DATA_DIR: DATA });
  const copies = [];
  try {
    for (let i = 0; i < N; i++) copies.push(await boot({ host: HOST, project: PROJECT }));
    await sleep(5000); // a heartbeat or two

    let r = await copies[0].run('net status', 'state     online');
    check(r.ok, 'net status: online', r.s);
    r = await copies[0].run('net ping', 'reply from the server');
    check(r.ok, `net ping (${(r.s.match(/in (\d+) ms/) || [])[1]} ms)`, r.s);

    // every copy uploads its own file and downloads its neighbour's, all at once
    const outs = await Promise.all(copies.map((h, i) => h.run(
      `echo message from computer ${i} > /tmp/m.txt; net put public/e2e${i}.txt /tmp/m.txt`, 'uploaded', 60000)));
    outs.forEach((o, i) => check(o.ok, `copy ${i}: net put at the same time as ${N - 1} others`, o.s));
    const gets = await Promise.all(copies.map((h, i) => h.run(
      `net get public/e2e${(i + 1) % N}.txt`, `message from computer ${(i + 1) % N}`, 60000)));
    gets.forEach((o, i) => check(o.ok, `copy ${i}: net get the file copy ${(i + 1) % N} uploaded`, o.s));
    r = await copies[0].run('net ls public/', `public/e2e${N - 1}.txt`);
    check(r.ok, 'net ls public/', r.s);
    r = await copies[0].run('net put pages/x.yarn /etc/hostname', 'read-only');
    check(r.ok, 'uploading to pages/ is refused', r.s);

    // the kernel's own rate limit: a burst of requests runs out of tokens
    r = await copies[1].run(Array(9).fill('net ping').join('; '), 'too many requests', 60000);
    check(r.ok, 'a burst of 9 pings is cut short by the rate limit', r.s);

    // stop the server: the relay still runs, so the state becomes "no server"
    server.kill();
    await sleep(15000);
    r = await copies[2 % N].run('net status', 'state     no server');
    check(r.ok, 'server stopped: net status says no server', r.s);
    r = await copies[2 % N].run('net ping', 'net:', 40000);
    check(r.ok && !r.s.includes('reply from'), 'server stopped: net ping fails', r.s);
    server = start('scratchos-server.js', { CLOUD_HOST: HOST, PROJECT_ID: PROJECT, DATA_DIR: DATA });
    await sleep(6000);
    r = await copies[2 % N].run('net status', 'state     online');
    check(r.ok, 'server back: online again', r.s);
  } finally {
    for (const h of copies) {
      const errs = h.logs.filter((l) => /PAGEERROR/.test(l));
      if (errs.length) { console.log(errs.join('\n')); fails++; }
      await h.close();
    }
    server.kill();
    relay.kill();
  }

  // no cloud provider at all: offline
  const off = await boot(null);
  const r = await off.run('net status', 'state     offline');
  check(r.ok, 'no cloud connection: net status says offline', r.s);
  await off.close();

  console.log(fails ? `${fails} check(s) failed` : 'all checks passed');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
