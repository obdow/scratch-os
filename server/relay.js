#!/usr/bin/env node
// relay.js - a small cloud-variable server speaking the TurboWarp / Scratch
// cloud protocol, for running the ScratchOS network yourself.
//
//   PORT=9080 MAX_VALUE=10000 node relay.js
//
// Projects connect to ws://host:PORT (TurboWarp: ?cloud_host=ws://host:PORT,
// or the Packager's "custom cloud host").  Messages are lines of JSON:
//   {"method":"handshake","project_id":"...","user":"..."}
//   {"method":"set","name":"☁ x","value":"123"}
// After a handshake the client gets every variable of its project; each
// "set" is stored and passed on to everyone else in the project.
//
// Limits (environment variables):
//   MAX_VALUE        longest value, in digits          (10000; Scratch's own is 256)
//   MAX_VARS         variables per project             (10, like Scratch)
//   MAX_PER_ROOM     connections per project           (200)
//   MAX_PER_IP       connections per address           (8)
//   SETS_PER_SECOND  writes per connection per second  (30; more are dropped)
//   TRUST_PROXY      1 behind a reverse proxy (nginx, Caddy, Fly...): take the
//                    client's address from X-Forwarded-For   (0)
// For a public deployment you may prefer TurboWarp's own server
// (github.com/TurboWarp/cloud-server); ScratchOS works with either.

const http = require('http');
const { WebSocketServer } = require('ws');

const env = (k, d) => (process.env[k] !== undefined ? Number(process.env[k]) : d);
const PORT = env('PORT', 9080);
const MAX_VALUE = env('MAX_VALUE', 10000);
const MAX_VARS = env('MAX_VARS', 10);
const MAX_PER_ROOM = env('MAX_PER_ROOM', 200);
const MAX_PER_IP = env('MAX_PER_IP', 8);
const SETS_PER_SECOND = env('SETS_PER_SECOND', 30);
const TRUST_PROXY = env('TRUST_PROXY', 0) === 1;
const QUIET = !!process.env.QUIET;

const rooms = new Map();       // project id -> {vars: Map, clients: Set}
const perIp = new Map();

const log = (...a) => { if (!QUIET) console.log(new Date().toISOString().slice(11, 19), '[relay]', ...a); };

function validValue(v) {
  if (typeof v === 'number') v = String(v);
  return typeof v === 'string' && v.length <= MAX_VALUE && /^-?\d+(\.\d+)?$/.test(v);
}

function room(id) {
  if (!rooms.has(id)) rooms.set(id, { vars: new Map(), clients: new Set() });
  return rooms.get(id);
}

function send(ws, msgs) {
  if (ws.readyState === ws.OPEN && msgs.length) ws.send(msgs.map((m) => JSON.stringify(m)).join('\n'));
}

const server = http.createServer((req, res) => {
  // a status page, handy for uptime monitors
  res.writeHead(200, { 'content-type': 'text/plain' });
  let n = 0;
  for (const r of rooms.values()) n += r.clients.size;
  res.end(`ScratchOS cloud relay: ${rooms.size} project(s), ${n} connection(s)\n`);
});
const wss = new WebSocketServer({ server, maxPayload: MAX_VALUE * 2 + 1024 });

wss.on('connection', (ws, req) => {
  // the header is only honest when our own proxy set it
  const fwd = TRUST_PROXY ? req.headers['x-forwarded-for'] : '';
  const ip = (fwd || req.socket.remoteAddress || '').split(',')[0].trim();
  perIp.set(ip, (perIp.get(ip) || 0) + 1);
  if (perIp.get(ip) > MAX_PER_IP) { ws.close(4003, 'too many connections'); }
  let r = null;
  let user = '';
  let windowStart = Date.now();
  let sets = 0;
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  ws.on('message', (data) => {
    for (const line of String(data).split('\n')) {
      if (!line.trim()) continue;
      let m;
      try { m = JSON.parse(line); } catch { ws.close(4000, 'bad message'); return; }
      if (m.method === 'handshake') {
        if (r) continue;
        const pid = String(m.project_id || '');
        user = String(m.user || 'player');
        if (!pid || pid.length > 100 || user.length > 40) { ws.close(4002, 'bad handshake'); return; }
        r = room(pid);
        if (r.clients.size >= MAX_PER_ROOM) { ws.close(4003, 'project is full'); r = null; return; }
        r.clients.add(ws);
        send(ws, [...r.vars].map(([name, value]) => ({ method: 'set', name, value })));
        log(`${user} joined ${pid} (${r.clients.size} connected)`);
      } else if (m.method === 'set') {
        if (!r) continue;
        // rate limit: excess writes are dropped (the ScratchOS protocol resends)
        const now = Date.now();
        if (now - windowStart >= 1000) { windowStart = now; sets = 0; }
        if (++sets > SETS_PER_SECOND) continue;
        const name = String(m.name || '');
        if (!name.startsWith('☁ ') || name.length > 64 || !validValue(m.value)) continue;
        if (!r.vars.has(name) && r.vars.size >= MAX_VARS) continue;
        const value = String(m.value);
        r.vars.set(name, value);
        const out = JSON.stringify({ method: 'set', name, value });
        for (const c of r.clients) if (c !== ws && c.readyState === c.OPEN) c.send(out);
      }
      // create / rename / delete are not needed by ScratchOS
    }
  });

  ws.on('close', () => {
    perIp.set(ip, perIp.get(ip) - 1);
    if (perIp.get(ip) <= 0) perIp.delete(ip);
    if (r) {
      r.clients.delete(ws);
      log(`${user} left (${r.clients.size} connected)`);
    }
  });
});

// drop dead connections
setInterval(() => {
  for (const ws of wss.clients) {
    if (!ws.isAlive) { ws.terminate(); continue; }
    ws.isAlive = false;
    ws.ping();
  }
}, 30000).unref();

server.listen(PORT, () => log(`listening on ws://localhost:${PORT} (values up to ${MAX_VALUE} digits)`));
