// End-to-end test of the relay + server with simulated ScratchOS computers
// (lib/client.js polls like a Scratch project, so lost updates are real).
//   node test/protocol-test.js
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Client } = require('../lib/client');

const PORT = 9300 + Math.floor(Math.random() * 500);
const HOST = `ws://localhost:${PORT}`;
const PROJECT = 'scratchos-test';
const DATA = fs.mkdtempSync(path.join(os.tmpdir(), 'scratchos-data-'));
fs.mkdirSync(path.join(DATA, 'pages'));
fs.writeFileSync(path.join(DATA, 'pages', 'index.yarn'), 'page "Hello"\n  title "It works"\n');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
function check(ok, what) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
  if (!ok) failures++;
}

function start(file, env) {
  const p = spawn(process.execPath, [path.join(__dirname, '..', file)], {
    env: { ...process.env, QUIET: '1', ...env }, stdio: ['ignore', 'inherit', 'inherit'],
  });
  return p;
}

async function main() {
  const relay = start('relay.js', { PORT: String(PORT), MAX_PER_IP: '100' });
  await sleep(500);
  const server = start('scratchos-server.js', { CLOUD_HOST: HOST, PROJECT_ID: PROJECT, DATA_DIR: DATA, MAX_PACKET: '256' });
  await sleep(800);
  try {
    // 1. one computer: heartbeat, ping, get, put, list, errors
    const a = new Client({ host: HOST, project: PROJECT });
    await a.connect();
    await sleep(4500);
    const hb = a.heartbeat();
    check(hb && Math.abs(hb.time - Date.now() / 1000) < 10 && hb.packet === 256, `heartbeat seen (${JSON.stringify(hb)})`);
    const ms = await a.ping();
    check(ms > 0 && ms < 3000, `ping: ${ms} ms`);
    check((await a.get('pages/index.yarn')).includes('It works'), 'get a page');
    const big = Array.from({ length: 120 }, (_, i) => `line ${i}: the quick brown fox jumps over the lazy dog`).join('\n');
    let t = Date.now();
    await a.put('public/big.txt', big);
    const upS = (Date.now() - t) / 1000;
    t = Date.now();
    const back = await a.get('public/big.txt');
    const downS = (Date.now() - t) / 1000;
    check(back === big, `put + get ${big.length} chars (up ${upS.toFixed(1)} s, down ${downS.toFixed(1)} s)`);
    check((await a.list('public/')).includes('public/big.txt'), 'list');
    await a.put('pages/hack.yarn', 'x').then(() => check(false, 'read-only area'), (e) => check(/read-only/.test(e.message), `read-only area: ${e.message}`));
    await a.get('public/nope.txt').then(() => check(false, 'missing file'), (e) => check(/not found/.test(e.message), `missing file: ${e.message}`));
    await a.put('public/huge.txt', 'x'.repeat(9000)).then(() => check(false, 'too big'), (e) => check(/too big/.test(e.message), `too big: ${e.message}`));

    // 2. many computers at once, all through the same 4 + 4 variables
    const N = 12;
    const clients = [];
    for (let i = 0; i < N; i++) { const c = new Client({ host: HOST, project: PROJECT }); await c.connect(); clients.push(c); }
    await sleep(300);
    t = Date.now();
    const results = await Promise.allSettled(clients.map(async (c, i) => {
      const text = `computer ${i} `.repeat(150);
      await c.put(`public/c${i}.txt`, text);
      const got = await c.get(`public/c${i}.txt`);
      return got === text;
    }));
    const ok = results.filter((r) => r.status === 'fulfilled' && r.value).length;
    const errs = results.filter((r) => r.status === 'rejected').map((r) => r.reason.message);
    check(ok === N, `${N} computers each put + get 2 KB at once: ${ok}/${N} correct in ${((Date.now() - t) / 1000).toFixed(1)} s ${errs.length ? JSON.stringify(errs) : ''}`);

    // 3. a computer that floods the server gets told to wait, others carry on
    const spam = new Client({ host: HOST, project: PROJECT });
    await spam.connect();
    const flood = [];
    for (let i = 0; i < 40; i++) flood.push(spam.ping().then(() => 'ok', (e) => e.message));
    await sleep(500);
    const fair = await clients[0].ping().then(() => 'ok', (e) => e.message);
    const out = await Promise.all(flood);
    const waited = [...spam.reqs.values()].length;
    const okN = out.filter((x) => x === 'ok').length;
    check(okN < 40 && out.some((x) => /busy|no answer/.test(x)), `flood of 40 pings: ${okN} answered, the rest refused (${[...new Set(out.filter((x) => x !== 'ok'))].join('; ')})`);
    check(fair === 'ok', 'another computer is still served during the flood');
    for (const c of [a, spam, ...clients]) c.close();
  } finally {
    server.kill();
    relay.kill();
  }
  console.log(failures ? `${failures} check(s) failed` : 'all checks passed');
  process.exit(failures ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
