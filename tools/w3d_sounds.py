"""
The Whisker 3D sound effect library: small sounds synthesised at build time
(no recordings), put in the Sound sprite of the engine and the players.

    python3 tools/w3d_sounds.py out_dir     # writes the .wav files to listen to
"""

import hashlib
import io
import math
import os
import random
import struct
import sys
import wave

RATE = 22050


def _env(t, dur, attack=0.005, release=None):
    """A simple attack / decay envelope (0..1)."""
    release = release if release is not None else dur
    if t < attack:
        return t / attack
    return max(0.0, 1.0 - (t - attack) / max(0.0001, release - attack))


def _tone(freq_fn, dur, wave_fn='square', vol=0.5, noise=0.0, seed=1, attack=0.005):
    rnd = random.Random(seed)
    n = int(RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = freq_fn(t)
        phase += f / RATE
        p = phase % 1.0
        if wave_fn == 'square':
            v = 1.0 if p < 0.5 else -1.0
        elif wave_fn == 'triangle':
            v = 4 * abs(p - 0.5) - 1
        elif wave_fn == 'saw':
            v = 2 * p - 1
        else:
            v = math.sin(2 * math.pi * p)
        if noise:
            v = v * (1 - noise) + (rnd.random() * 2 - 1) * noise
        out.append(v * vol * _env(t, dur, attack))
    return out


def _noise(dur, vol=0.6, lowpass=0.3, seed=2, decay=None):
    rnd = random.Random(seed)
    n = int(RATE * dur)
    out = []
    y = 0.0
    for i in range(n):
        t = i / RATE
        x = rnd.random() * 2 - 1
        k = lowpass if decay is None else lowpass * (1 - t / dur) + 0.02
        y = y + k * (x - y)
        out.append(y * vol * _env(t, dur, 0.002) * 2)
    return out


def _cat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def _mix(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)]


def _notes(freqs, each, wave_fn='square', vol=0.4):
    return _cat(*[_tone(lambda t, f=f: f, each, wave_fn, vol) for f in freqs])


EFFECTS = {
    'jump': lambda: _tone(lambda t: 260 + 900 * t, 0.18, 'square', 0.35),
    'coin': lambda: _cat(_tone(lambda t: 988, 0.06, 'square', 0.3), _tone(lambda t: 1319, 0.22, 'square', 0.3)),
    'powerup': lambda: _notes([523, 659, 784, 1047, 1319], 0.06, 'square', 0.3),
    'hit': lambda: _mix(_noise(0.12, 0.5, 0.5), _tone(lambda t: 140 - 300 * t, 0.12, 'square', 0.3)),
    'hurt': lambda: _tone(lambda t: 420 - 900 * t, 0.25, 'saw', 0.35),
    'explosion': lambda: _noise(0.8, 0.8, 0.25, decay=True),
    'laser': lambda: _tone(lambda t: 1400 * math.exp(-t * 9) + 200, 0.22, 'square', 0.3),
    'shoot': lambda: _mix(_noise(0.1, 0.35, 0.7), _tone(lambda t: 700 - 2000 * t, 0.1, 'square', 0.25)),
    'click': lambda: _tone(lambda t: 1800, 0.025, 'sine', 0.5),
    'select': lambda: _cat(_tone(lambda t: 660, 0.05, 'sine', 0.4), _tone(lambda t: 990, 0.08, 'sine', 0.4)),
    'blip': lambda: _tone(lambda t: 880, 0.07, 'square', 0.3),
    'pop': lambda: _tone(lambda t: 300 + 1200 * math.exp(-t * 40), 0.08, 'sine', 0.6),
    'step': lambda: _noise(0.06, 0.4, 0.15),
    'whoosh': lambda: _noise(0.45, 0.5, 0.08, decay=True),
    'win': lambda: _notes([523, 659, 784, 1047, 784, 1047], 0.11, 'triangle', 0.45),
    'lose': lambda: _notes([494, 466, 440, 415], 0.18, 'triangle', 0.45),
    'bounce': lambda: _tone(lambda t: 200 + 500 * abs(math.sin(t * 40)), 0.2, 'sine', 0.5),
    'beep': lambda: _tone(lambda t: 1000, 0.15, 'sine', 0.4),
}

NAMES = list(EFFECTS)


def wav_bytes(samples):
    buf = io.BytesIO()
    w = wave.open(buf, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(b''.join(struct.pack('<h', max(-32767, min(32767, int(s * 32767)))) for s in samples))
    w.close()
    return buf.getvalue()


_cache = {}


def sounds(group):
    if group != 'w3d_sfx':
        raise KeyError(group)
    if group not in _cache:
        out = []
        for name in NAMES:
            samples = EFFECTS[name]()
            data = wav_bytes(samples)
            md5 = hashlib.md5(data).hexdigest()
            out.append({'name': name, 'assetId': md5, 'dataFormat': 'wav', 'format': '', 'rate': RATE,
                        'sampleCount': len(samples), 'md5ext': f'{md5}.wav', '_bytes': data})
        _cache[group] = out
    return [dict(s) for s in _cache[group]]


def build_data():
    return {'snd_names': list(NAMES)}


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(d, exist_ok=True)
    for s in sounds('w3d_sfx'):
        with open(os.path.join(d, s['name'] + '.wav'), 'wb') as f:
            f.write(s['_bytes'])
    print(len(NAMES), 'sounds in', d)
