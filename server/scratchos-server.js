#!/usr/bin/env node
// scratchos-server.js - the ScratchOS network's data server.
//
// It joins the project's cloud variables as one more client, and answers the
// packets ScratchOS computers write to "☁ up1".."☁ up4" (see src/net.sbs and
// lib/protocol.js):  ping, get <key>, put <key> <text>, list <prefix>.
// Files live in DATA_DIR; "pages/" holds the pages the Browser shows at
// net://, written by you; computers may write under "public/" and "users/".
//
//   CLOUD_HOST=ws://localhost:9080 PROJECT_ID=scratchos node scratchos-server.js
//
// Settings (environment variables, defaults in brackets):
//   CLOUD_HOST     the cloud server                         [ws://localhost:9080]
//   PROJECT_ID     the project's id on it                   [scratchos]
//   USERNAME       the name it joins as                     [scratchos-server]
//   DATA_DIR       where files are kept                     [./data]
//   MAX_PACKET     longest value the cloud server accepts   [256; Scratch's limit]
//   PACE_MS        gap between writes to one down variable  [120]
//   SEND_PER_SEC   writes per second, all variables         [16]
//   WRITABLE       key prefixes computers may write         [public/,users/]
//   USER_AGENT     sent when connecting; public cloud servers ask for contact
//                  details here                             [ScratchOS-server/1.0]
//   ... and the limits below (LIMITS).

const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const P = require('./lib/protocol');

const env = (k, d) => (process.env[k] !== undefined ? process.env[k] : d);
const num = (k, d) => Number(env(k, d));

const CLOUD_HOST = env('CLOUD_HOST', 'ws://localhost:9080');
const PROJECT_ID = env('PROJECT_ID', 'scratchos');
const USERNAME = env('USERNAME', 'scratchos-server');
const DATA_DIR = path.resolve(env('DATA_DIR', path.join(__dirname, 'data')));
const MAX_PACKET = num('MAX_PACKET', 256);
const PACE_MS = num('PACE_MS', 120);
const SEND_PER_SEC = num('SEND_PER_SEC', 16);
const WRITABLE = env('WRITABLE', 'public/,users/').split(',').filter(Boolean);
const USER_AGENT = env('USER_AGENT', 'ScratchOS-server/1.0');
const VERSION = 1;
const QUIET = !!process.env.QUIET;

const LIMITS = {
  reqPerMin: num('REQ_PER_MIN', 30),        // requests a minute per computer ...
  reqBurst: num('REQ_BURST', 8),            // ... with bursts of this many
  upPerMin: num('UP_PER_MIN', 32768),       // characters uploaded a minute per computer
  downPerMin: num('DOWN_PER_MIN', 262144),  // characters downloaded a minute per computer
  maxUpload: num('MAX_UPLOAD', 8192),
  maxDownload: num('MAX_DOWNLOAD', 65536),
  inflight: num('MAX_INFLIGHT', 3),         // unfinished requests per computer
  quota: num('QUOTA', 262144),              // characters a computer may store
  storage: num('MAX_STORAGE', 50 * 1024 * 1024),
  sessions: num('MAX_SESSIONS', 200),       // computers served at once
  globalPerSec: num('GLOBAL_PER_SEC', 25),  // new requests a second, everyone together
  strikes: num('STRIKES', 5),               // limit breaches before a time-out ...
  banSeconds: num('BAN_SECONDS', 120),      // ... of this long
};

const WINDOW = 4;          // download chunks in flight
const RETX_MS = 2500;      // resend unacknowledged chunks after this
const MAX_RETX = 6;
const KEEP_DONE_MS = 60000;
const SESSION_IDLE_MS = 300000;
const DOWN_VARS = ['☁ down1', '☁ down2', '☁ down3', '☁ down4'];
const UP_VARS = new Set(['☁ up1', '☁ up2', '☁ up3', '☁ up4']);
const PAYLOAD = MAX_PACKET - P.HEAD;   // digits per chunk

const log = (...a) => { if (!QUIET) console.log(new Date().toISOString().slice(11, 19), '[server]', ...a); };

// --- storage -----------------------------------------------------------------------------

const KEY_RE = /^[A-Za-z0-9_\-./]{1,100}$/;
function keyOk(k) { return KEY_RE.test(k) && !k.includes('..') && !k.startsWith('/') && !k.endsWith('/'); }
function keyPath(k) { return path.join(DATA_DIR, ...k.split('/')); }
function canWrite(k) { return WRITABLE.some((p) => k.startsWith(p)); }

let storageUsed = 0;
function scan(dir) {
  let n = 0;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    n += e.isDirectory() ? scan(p) : fs.statSync(p).size;
  }
  return n;
}

function listKeys(prefix) {
  const out = [];
  const walk = (dir, rel) => {
    if (!fs.existsSync(dir)) return;
    for (const e of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const k = rel ? rel + '/' + e.name : e.name;
      if (e.isDirectory()) walk(path.join(dir, e.name), k);
      else if (k.startsWith(prefix) && !k.endsWith('.meta.json')) out.push(k);
      if (out.length >= 200) return;
    }
  };
  walk(DATA_DIR, '');
  return out;
}

// --- rate limiting -----------------------------------------------------------------------

class Bucket {
  constructor(perMin, burst) { this.rate = perMin / 60000; this.cap = burst; this.v = burst; this.t = Date.now(); }
  refill() { const now = Date.now(); this.v = Math.min(this.cap, this.v + (now - this.t) * this.rate); this.t = now; }
  take(n = 1) { this.refill(); if (this.v >= n) { this.v -= n; return 0; } return Math.ceil((n - this.v) / this.rate / 1000); }
}

const globalBucket = new Bucket(LIMITS.globalPerSec * 60, LIMITS.globalPerSec);
const sessions = new Map();     // computer id -> session

function session(id) {
  let s = sessions.get(id);
  if (!s) {
    if (sessions.size >= LIMITS.sessions) return null;
    s = {
      id, last: Date.now(), reqs: new Map(), outbox: [], strikes: 0, banUntil: 0, stored: 0,
      reqBucket: new Bucket(LIMITS.reqPerMin, LIMITS.reqBurst),
      upBucket: new Bucket(LIMITS.upPerMin, LIMITS.upPerMin),
      downBucket: new Bucket(LIMITS.downPerMin, LIMITS.downPerMin),
    };
    sessions.set(id, s);
  }
  s.last = Date.now();
  return s;
}

function strike(s, why) {
  s.strikes++;
  log(`computer ${s.id}: limit (${why}), strike ${s.strikes}`);
  if (s.strikes >= LIMITS.strikes) {
    s.banUntil = Date.now() + LIMITS.banSeconds * 1000;
    s.strikes = 0;
    log(`computer ${s.id}: timed out for ${LIMITS.banSeconds}s`);
  }
}

// --- the cloud connection -----------------------------------------------------------------

let ws = null;
let connected = false;
let attempts = 0;

function connect() {
  ws = new WebSocket(CLOUD_HOST, { headers: { 'user-agent': USER_AGENT } });
  ws.on('open', () => {
    connected = true;
    attempts = 0;
    ws.send(JSON.stringify({ method: 'handshake', project_id: PROJECT_ID, user: USERNAME }));
    log(`connected to ${CLOUD_HOST}, project ${PROJECT_ID}`);
    beat();
  });
  ws.on('message', (data) => {
    for (const line of String(data).split('\n')) {
      if (!line) continue;
      let m;
      try { m = JSON.parse(line); } catch { continue; }
      if (m.method === 'set' && UP_VARS.has(m.name)) onPacket(String(m.value));
    }
  });
  ws.on('close', (code) => {
    connected = false;
    const wait = Math.min(30000, 1000 * 2 ** attempts++) * (0.5 + Math.random());
    log(`disconnected (${code}); reconnecting in ${Math.round(wait / 1000)}s`);
    setTimeout(connect, wait);
  });
  ws.on('error', (e) => log('connection error:', e.message));
}

function setVar(name, value) {
  if (!connected) return false;
  // values go as strings: as JSON numbers, long ones would lose digits
  ws.send(JSON.stringify({ method: 'set', name, value: String(value), project_id: PROJECT_ID, user: USERNAME }));
  return true;
}

function beat() {
  const active = [...sessions.values()].filter((s) => Date.now() - s.last < 60000).length;
  setVar('☁ heartbeat', P.heartbeat(MAX_PACKET, active, VERSION));
}

// --- requests ------------------------------------------------------------------------------

// queue a packet for computer s (sent fairly by the scheduler)
function out(s, type, req, seq, total, payload) {
  s.outbox.push({ pkt: P.packet(type, s.id, req ? req.msg : 0, seq, total, payload), req, seq });
}

// a one-packet answer, remembered so a repeated request gets it again
function reply(s, req, type, text) {
  req.done = true;
  req.answer = { type, payload: P.encode(text) };
  req.doneAt = Date.now();
  out(s, type, req, 1, 1, req.answer.payload);
}

function wait(s, req, seconds) {
  // not remembered: the computer waits and asks again
  out(s, P.T.WAIT, req, 1, 1, P.encode(String(Math.max(1, seconds))));
}

function onPacket(value) {
  const p = P.parse(value);
  if (!p || p.id < 100000) return;
  const s = session(p.id);
  if (!s) return;            // too many computers: ignore (they see "no answer")
  if (Date.now() < s.banUntil) {
    if (p.type !== P.T.ACK) wait(s, { msg: p.msg }, Math.ceil((s.banUntil - Date.now()) / 1000));
    return;
  }
  if (p.type === P.T.ACK) return onAck(s, p);
  if (![P.T.PING, P.T.GET, P.T.PUT, P.T.LIST].includes(p.type)) return strike(s, 'unknown packet');
  if (p.total < 1 || p.seq < 1 || p.seq > p.total) return strike(s, 'bad chunk');

  let req = s.reqs.get(p.msg);
  if (req && req.type !== p.type) { s.reqs.delete(p.msg); req = null; }
  if (!req) {
    // a new request: the limits
    let open = 0;
    for (const r of s.reqs.values()) if (!r.done) open++;
    if (open >= LIMITS.inflight) { strike(s, 'too many at once'); return wait(s, { msg: p.msg }, 2); }
    const g = globalBucket.take();
    if (g) return wait(s, { msg: p.msg }, Math.max(2, g));
    const w = s.reqBucket.take();
    if (w) { strike(s, 'requests'); return wait(s, { msg: p.msg }, w); }
    if (p.type === P.T.PUT && p.total * PAYLOAD > LIMITS.maxUpload * 2 + 400) {
      req = { msg: p.msg, type: p.type };
      s.reqs.set(p.msg, req);
      return reply(s, req, P.T.ERROR, `too big: uploads are at most ${LIMITS.maxUpload} characters`);
    }
    req = { msg: p.msg, type: p.type, total: p.total, got: 0, parts: [], done: false, t: Date.now() };
    s.reqs.set(p.msg, req);
  }

  if (req.done) {
    // the computer missed the answer: send it again
    if (req.answer) out(s, req.answer.type, req, 1, 1, req.answer.payload);
    else if (req.data) resendFrom(s, req, req.acked);
    return;
  }
  if (p.seq === req.got + 1) {
    req.parts.push(p.payload);
    req.got++;
  }
  if (req.got < req.total) {
    // acknowledge uploads every other chunk, and whenever one is out of order
    if (req.got % 2 === 0 || p.seq !== req.got) out(s, P.T.ACK, req, req.got, req.total, '');
    return;
  }
  handle(s, req, P.decode(req.parts.join('')));
}

function handle(s, req, text) {
  req.parts = null;
  if (req.type === P.T.PING) {
    let online = 0;
    for (const x of sessions.values()) if (Date.now() - x.last < 60000) online++;
    return reply(s, req, P.T.PONG, `ScratchOS server ${VERSION}; ${online} online`);
  }
  if (req.type === P.T.PUT) {
    const nl = text.indexOf('\n');
    const key = nl < 0 ? text : text.slice(0, nl);
    const data = nl < 0 ? '' : text.slice(nl + 1);
    if (!keyOk(key)) return reply(s, req, P.T.ERROR, `bad name: ${key}`);
    if (!canWrite(key)) return reply(s, req, P.T.ERROR, `${key} is read-only (write under ${WRITABLE.join(' or ')})`);
    if (data.length > LIMITS.maxUpload) return reply(s, req, P.T.ERROR, `too big: uploads are at most ${LIMITS.maxUpload} characters`);
    const w = s.upBucket.take(data.length);
    if (w) { strike(s, 'upload'); req.done = false; s.reqs.delete(req.msg); return wait(s, req, w); }
    if (s.stored + data.length > LIMITS.quota) return reply(s, req, P.T.ERROR, 'storage quota used up');
    if (storageUsed + data.length > LIMITS.storage) return reply(s, req, P.T.ERROR, 'the server is full');
    const file = keyPath(key);
    let before = 0;
    try { before = fs.statSync(file).size; } catch {}
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, data);
    fs.writeFileSync(file + '.meta.json', JSON.stringify({ by: s.id, at: new Date().toISOString() }));
    storageUsed += data.length - before;
    s.stored += data.length;
    log(`computer ${s.id}: put ${key} (${data.length} chars)`);
    return reply(s, req, P.T.DONE, `saved ${key}`);
  }
  // get and list send data
  let body;
  if (req.type === P.T.GET) {
    const key = text;
    if (!keyOk(key)) return reply(s, req, P.T.ERROR, `bad name: ${key}`);
    try { body = fs.readFileSync(keyPath(key), 'utf8'); } catch { return reply(s, req, P.T.ERROR, `not found: ${key}`); }
    if (body.length > LIMITS.maxDownload) return reply(s, req, P.T.ERROR, `${key} is too big to download`);
    log(`computer ${s.id}: get ${key} (${body.length} chars)`);
  } else {
    if (text && !/^[A-Za-z0-9_\-./]{0,100}$/.test(text)) return reply(s, req, P.T.ERROR, `bad prefix: ${text}`);
    body = listKeys(text).join('\n');
  }
  const w = s.downBucket.take(body.length);
  if (w) { strike(s, 'download'); s.reqs.delete(req.msg); return wait(s, req, w); }
  req.done = true;
  req.doneAt = Date.now();
  req.data = P.chunks(P.encode(body), PAYLOAD);
  req.acked = 0;
  req.sent = 0;
  req.retx = 0;
  sendWindow(s, req);
}

function sendWindow(s, req) {
  while (req.sent < req.data.length && req.sent < req.acked + WINDOW) {
    req.sent++;
    out(s, P.T.DATA, req, req.sent, req.data.length, req.data[req.sent - 1]);
  }
  req.t = Date.now();
}

function resendFrom(s, req, acked) {
  s.outbox = s.outbox.filter((o) => o.req !== req);
  req.sent = acked;
  sendWindow(s, req);
}

function onAck(s, p) {
  const req = s.reqs.get(p.msg);
  if (!req || !req.data) return;
  if (p.seq > req.acked) {
    req.acked = Math.min(p.seq, req.data.length);
    req.retx = 0;
    sendWindow(s, req);
  } else if (p.seq === req.acked && req.acked < req.data.length) {
    // a repeated ack: a chunk went missing
    resendFrom(s, req, req.acked);
  }
}

// --- sending: fair, paced -------------------------------------------------------------------

const slotFree = DOWN_VARS.map(() => 0);
const sendBucket = new Bucket(SEND_PER_SEC * 60, SEND_PER_SEC);
let rr = 0;

function pump() {
  const now = Date.now();
  // one packet per free variable, taking computers in turn
  for (let v = 0; v < DOWN_VARS.length; v++) {
    if (now < slotFree[v]) continue;
    const ids = [...sessions.keys()].filter((id) => sessions.get(id).outbox.length);
    if (!ids.length) return;
    if (sendBucket.take()) return;
    const s = sessions.get(ids[rr++ % ids.length]);
    const o = s.outbox.shift();
    if (!setVar(DOWN_VARS[v], o.pkt)) { s.outbox.unshift(o); return; }
    slotFree[v] = now + PACE_MS;
  }
}

function housekeeping() {
  const now = Date.now();
  for (const [id, s] of sessions) {
    for (const [msg, req] of s.reqs) {
      if (req.data && req.acked < req.data.length && now - req.t > RETX_MS) {
        if (++req.retx > MAX_RETX) { s.reqs.delete(msg); continue; }
        resendFrom(s, req, req.acked);
      }
      if (req.done && now - (req.doneAt || 0) > KEEP_DONE_MS) s.reqs.delete(msg);
      if (!req.done && now - req.t > KEEP_DONE_MS) s.reqs.delete(msg);
    }
    if (now - s.last > SESSION_IDLE_MS && !s.outbox.length) sessions.delete(id);
  }
}

// --- start --------------------------------------------------------------------------------

fs.mkdirSync(DATA_DIR, { recursive: true });
storageUsed = scan(DATA_DIR);
log(`data in ${DATA_DIR} (${storageUsed} bytes); packets up to ${MAX_PACKET} digits`);
setInterval(pump, 20);
setInterval(housekeeping, 500);
setInterval(beat, 4000);
connect();

module.exports = { LIMITS };
