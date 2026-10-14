// The ScratchOS cloud-variable protocol (the other half is src/net.sbs).
//
// A packet is a string of digits:
//   "1" type(2) id(6) msg(4) seq(3) total(3) payload
// Text is 2 digits a character: printable ASCII 32..126 -> 01..95, newline
// -> 96, anything else -> "98" + its code page 437 code (3 digits).

const HEAD = 19;

const T = {
  PING: 10, PONG: 11,
  GET: 20, PUT: 21, LIST: 22,
  DATA: 30, ACK: 31, DONE: 32,
  ERROR: 40, WAIT: 41,
};

// CP437 for the codes the kernel can send outside printable ASCII
const CP437_HIGH = 'ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ ';
const CP437_LOW = ['', '☺', '☻', '♥', '♦', '♣', '♠', '•', '◘', '○', '\n', '♂', '♀', '♪', '♫', '☼',
  '►', '◄', '↕', '‼', '¶', '§', '▬', '↨', '↑', '↓', '→', '←', '∟', '↔', '▲', '▼'];

function charToCode(ch) {
  const c = ch.codePointAt(0);
  if (c >= 32 && c <= 126) return c;
  if (ch === '\n') return 10;
  const lo = CP437_LOW.indexOf(ch);
  if (lo > 0) return lo;
  if (ch === '⌂') return 127;
  const hi = CP437_HIGH.indexOf(ch);
  if (hi >= 0) return 128 + hi;
  return 63; // '?'
}

function codeToChar(c) {
  if (c >= 32 && c <= 126) return String.fromCharCode(c);
  if (c === 10) return '\n';
  if (c < 32) return CP437_LOW[c] || '?';
  if (c === 127) return '⌂';
  return CP437_HIGH[c - 128] || '?';
}

function encode(text) {
  let out = '';
  for (const ch of String(text).replace(/\r/g, '')) {
    const c = charToCode(ch);
    if (c >= 32 && c <= 126) out += String(c - 31).padStart(2, '0');
    else if (c === 10) out += '96';
    else out += '98' + String(c).padStart(3, '0');
  }
  return out;
}

function decode(digits) {
  let out = '';
  let i = 0;
  while (i + 1 < digits.length) {
    const c = Number(digits.slice(i, i + 2));
    if (c >= 1 && c <= 95) { out += String.fromCharCode(c + 31); i += 2; }
    else if (c === 96) { out += '\n'; i += 2; }
    else if (c === 98) { out += codeToChar(Number(digits.slice(i + 2, i + 5))); i += 5; }
    else i += 2;
  }
  return out;
}

const pad = (n, w) => String(n).padStart(w, '0');

function packet(type, id, msg, seq, total, payload = '') {
  return '1' + pad(type, 2) + pad(id, 6) + pad(msg, 4) + pad(seq, 3) + pad(total, 3) + payload;
}

// null if it is not a well-formed packet
function parse(value) {
  const v = String(value);
  if (v.length < HEAD || v[0] !== '1' || !/^\d+$/.test(v)) return null;
  return {
    type: Number(v.slice(1, 3)),
    id: Number(v.slice(3, 9)),
    msg: Number(v.slice(9, 13)),
    seq: Number(v.slice(13, 16)),
    total: Number(v.slice(16, 19)),
    payload: v.slice(HEAD),
  };
}

// split encoded digits into chunks of `size` digits (at least one, maybe empty)
function chunks(digits, size) {
  const out = [];
  for (let i = 0; i < digits.length; i += size) out.push(digits.slice(i, i + size));
  if (out.length === 0) out.push('');
  return out;
}

// the heartbeat: "1" unix-time(10) max-packet(5) clients(3) version(2)
function heartbeat(maxPacket, clients, version = 1) {
  return '1' + pad(Math.floor(Date.now() / 1000), 10) + pad(maxPacket, 5) + pad(Math.min(999, clients), 3) + pad(version, 2);
}

module.exports = { HEAD, T, encode, decode, packet, parse, chunks, heartbeat };
