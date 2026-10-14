// A ScratchOS network client in Node, behaving like the kernel (src/net.sbs):
// it only looks at the cloud variables every frame (so, like a Scratch
// project, it misses values that are overwritten in between), writes at most
// one packet every 110 ms, and resends with the same rules.  Used by the
// tests, and handy for scripts that talk to the server the way ScratchOS does.

const WebSocket = require('ws');
const P = require('./protocol');

const GAP = 110;
const WINDOW = 4;
const TIMEOUT = 2500;
const TRIES = 6;
const FRAME = 16;

class Client {
  constructor({ host, project, user = 'player' + Math.floor(Math.random() * 1e6), maxPacket = 256 } = {}) {
    this.host = host;
    this.project = project;
    this.user = user;
    this.id = 100000 + Math.floor(Math.random() * 900000);
    this.msgc = Math.floor(Math.random() * 10000);
    this.vars = {};          // what the cloud says (latest values)
    this.seen = {};          // what we last looked at
    this.queue = [];
    this.lastTx = 0;
    this.reqs = new Map();
    this.maxPacket = maxPacket;
    this.sent = 0;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.host);
      this.ws.on('open', () => {
        this.ws.send(JSON.stringify({ method: 'handshake', project_id: this.project, user: this.user }));
        this.timer = setInterval(() => this.frame(), FRAME);
        resolve();
      });
      this.ws.on('error', reject);
      this.ws.on('message', (d) => {
        for (const line of String(d).split('\n')) {
          if (!line) continue;
          const m = JSON.parse(line);
          if (m.method === 'set') this.vars[m.name] = String(m.value);
        }
      });
    });
  }

  close() { clearInterval(this.timer); this.ws.close(); }

  heartbeat() {
    const v = this.vars['☁ heartbeat'];
    if (!v || v.length < 19) return null;
    return { time: Number(v.slice(1, 11)), packet: Number(v.slice(11, 16)), clients: Number(v.slice(16, 19)) };
  }

  // one Scratch frame: look at the down variables, step requests, write one packet
  frame() {
    const hb = this.heartbeat();
    if (hb) this.maxPacket = Math.min(Math.max(64, hb.packet), 10000);
    for (let k = 1; k <= 4; k++) {
      const name = '☁ down' + k;
      const v = this.vars[name];
      if (v !== undefined && v !== this.seen[name]) { this.seen[name] = v; this.receive(v); }
    }
    const now = Date.now();
    for (const r of this.reqs.values()) if (!r.finished && now >= r.t) this.step(r, now);
    if (this.queue.length && now - this.lastTx >= GAP) {
      const { pkt } = this.queue.shift();
      const slot = (this.id + this.sent) % 4 + 1;
      this.ws.send(JSON.stringify({ method: 'set', name: '☁ up' + slot, value: pkt, project_id: this.project, user: this.user }));
      this.lastTx = now;
      this.sent++;
    }
  }

  enqueue(r, pkt) { if (this.queue.length < 12) this.queue.push({ r, pkt }); }
  unqueue(r) { this.queue = this.queue.filter((q) => q.r !== r); }
  ack(r) { this.enqueue(r, P.packet(P.T.ACK, this.id, r.msg, r.got, r.total, '')); r.ackt = Date.now(); }

  receive(v) {
    const p = P.parse(v);
    if (!p || p.id !== this.id) return;
    const r = this.reqs.get(p.msg);
    if (!r || r.finished) return;
    const now = Date.now();
    r.t = now;
    r.wait = TIMEOUT;
    if (p.type === P.T.ACK) {
      r.base = Math.max(r.base, p.seq);
      if (r.next <= r.base) r.next = r.base + 1;
      if (r.base >= r.chunks.length) r.state = 'wait';
    } else if (p.type === P.T.PONG || p.type === P.T.DONE) {
      this.finish(r, null, P.decode(p.payload));
    } else if (p.type === P.T.DATA) {
      r.state = 'wait';
      r.base = r.chunks.length;
      if (p.seq === r.got + 1) {
        r.down += p.payload;
        r.got = p.seq;
        r.total = p.total;
        if (r.got >= p.total) { this.ack(r); this.finish(r, null, P.decode(r.down)); }
        else if (r.got % 2 === 0) this.ack(r);
      } else if (now - r.ackt > 400) this.ack(r);
    } else if (p.type === P.T.ERROR) {
      this.finish(r, new Error(P.decode(p.payload)));
    } else if (p.type === P.T.WAIT) {
      const secs = Number(P.decode(p.payload)) || 1;
      r.waits = (r.waits || 0) + 1;
      if (secs > 20) return this.finish(r, new Error(`busy: try again in ${secs} s`));
      this.unqueue(r);
      r.next = r.base + 1;
      r.t = now + secs * 1000;
      r.state = 'send';
    }
  }

  step(r, now) {
    if (r.state === 'send') {
      while (r.next <= r.chunks.length && r.next <= r.base + WINDOW && this.queue.length < 8) {
        this.enqueue(r, P.packet(r.type, this.id, r.msg, r.next, r.chunks.length, r.chunks[r.next - 1]));
        r.next++;
      }
    }
    if (now - r.t > r.wait) {
      if (++r.tries > TRIES) return this.finish(r, new Error('no answer from the server'));
      this.unqueue(r);
      r.resends = (r.resends || 0) + 1;
      if (r.state === 'send' || r.got === 0) {
        r.state = 'send';
        r.next = r.base + 1;
        if (r.chunks.length === 1 || r.base >= r.chunks.length) r.next = r.chunks.length;
      } else this.ack(r);
      r.t = now;
      r.wait = Math.min(12000, r.wait * 2 + Math.random() * 1000);
    }
  }

  finish(r, err, value) {
    r.finished = true;
    this.unqueue(r);
    this.reqs.delete(r.msg);
    if (err) r.reject(err); else r.resolve(value);
  }

  request(type, text) {
    return new Promise((resolve, reject) => {
      this.msgc = (this.msgc + 1) % 10000;
      const r = {
        type, msg: this.msgc, chunks: P.chunks(P.encode(text), this.maxPacket - P.HEAD), base: 0, next: 1,
        got: 0, total: 0, down: '', state: 'send', t: Date.now(), t0: Date.now(), wait: TIMEOUT, tries: 0, ackt: 0,
        resolve, reject,
      };
      this.reqs.set(r.msg, r);
      this.step(r, Date.now());
    });
  }

  async ping() { const t = Date.now(); await this.request(P.T.PING, ''); return Date.now() - t; }
  get(key) { return this.request(P.T.GET, key); }
  put(key, text) { return this.request(P.T.PUT, key + '\n' + text); }
  async list(prefix = '') { const t = await this.request(P.T.LIST, prefix); return t ? t.split('\n') : []; }
}

module.exports = { Client };
