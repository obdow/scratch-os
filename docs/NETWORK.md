# The ScratchOS network

ScratchOS can upload and download files through **cloud variables**, the only
way a Scratch project can talk to the outside world. A small Node program, the
**ScratchOS server**, joins the same cloud variables as one more player and
answers requests. On top of that ScratchOS has:

* `net` in the terminal: `net status`, `net ping`, `net get`, `net put`, `net ls`
* the Whisker `net` library (`net.get`, `net.put`, ...), behind the `net` capability
* `net://` pages in the Browser, served from the server's `pages/` folder
* a network indicator in the taskbar, and a Network page in System Settings

```
 ScratchOS (player 1) ─┐                     ┌─ scratchos-server.js
 ScratchOS (player 2) ─┼── cloud server ─────┤   (files in DATA_DIR)
 ScratchOS (player n) ─┘   (relay.js, or      └─
                            TurboWarp's / Scratch's)
```

## Running it locally

```
cd server && npm install
node relay.js                                    # a cloud server on ws://localhost:9080
CLOUD_HOST=ws://localhost:9080 PROJECT_ID=scratchos node scratchos-server.js
```

Then open ScratchOS with that cloud server. In the headless test tools:

```
cd test
node drive.js ../ScratchOS.sb3 out --text --cloud=ws://localhost:9080,scratchos -- "net status" "net ping"
node net-e2e.js ../ScratchOS.sb3       # 3 copies at once, rate limits, no server, offline
cd ../server && npm test               # the protocol, 12 computers at once, a flood
```

## How it works

### The variables

Cloud variables hold only digits, at most 256 of them on Scratch, and a project
may have 10. ScratchOS uses nine (`src/cloud.sbs`):

| Variable | Written by | Holds |
|---|---|---|
| `☁ heartbeat` | server, every 4 s | `1` + unix time (10) + max packet (5) + computers (3) + version (2) |
| `☁ up1` .. `☁ up4` | computers | packets to the server |
| `☁ down1` .. `☁ down4` | server | packets to computers |

### Packets

Every value written is one packet, all digits:

```
1  TT  IIIIII  MMMM  SSS  NNN  payload...
   │   │       │     │    └ chunks in this message
   │   │       │     └ this chunk (1..NNN)
   │   │       └ message number (each request gets a new one)
   │   └ the computer's id (random, chosen at boot)
   └ type
```

The leading `1` keeps leading zeros. Text in the payload takes 2 digits a
character: printable ASCII 32–126 is `01`–`95`, a newline is `96`, and any other
character is `98` followed by its 3-digit code. With 256 digits, a packet
carries up to 118 characters.

| Type | From | Meaning |
|---|---|---|
| 10 / 11 | computer / server | ping / pong |
| 20 | computer | get: payload is the name |
| 21 | computer | put: payload is the name, a newline, then the data |
| 22 | computer | list: payload is a prefix |
| 30 | server | data: one chunk of an answer |
| 31 | both | ack: "I have every chunk up to SSS" |
| 32 | server | done: the put is stored |
| 40 | server | error: payload is the message |
| 41 | server | wait: payload is the number of seconds to wait |

### Many computers at once

Everyone writes to the same nine variables, so the design assumes values will
be overwritten:

* **Computer → server never loses anything.** A cloud server sends the bot
  every write as its own message, even two to the same variable in the same
  instant. Computers also spread their writes over `up1`–`up4`.
* **Server → computer can lose values.** A Scratch project only sees a
  variable's *latest* value each frame. The server therefore waits 120 ms
  between writes to the same `down` variable, rotates through all four, sends
  at most 16 packets a second in total, and takes turns between computers
  (round robin) so one big download cannot starve the rest.
* **Every packet carries its computer id and message number.** A computer
  ignores packets that are not for it, so `down` variables can be shared.
* **Anything lost is sent again.**
  * Requests are repeated until answered.
  * Uploads keep 4 chunks in flight and go back to the last acknowledged
    chunk (go-back-N).
  * Downloads keep 4 chunks in flight; the computer acknowledges every
    second chunk and the last one.
  * Waits start at 2.5 s and double, plus a random part so that computers
    don't retry in step, for up to 6 tries.
* **Repeats are safe.** The server remembers finished answers for a minute,
  so a repeated request gets the same reply and is not run twice.

Measured with the default 256-digit packets: about 1 KB/s up and 2 KB/s down for
one computer; 12 computers each uploading and downloading 2 KB at once all
finish correctly in about 18 s.

### Rate limits

Cloud variables are shared by everyone, so one player spamming them would
slow down everyone else. There are limits on both sides.

**In ScratchOS** (`src/net.sbs`), which a normal program cannot get around:

| Limit | Value |
|---|---|
| cloud writes | one every 0.11 s (Scratch itself allows about 10 a second) |
| requests | 6 at once, then one more every 4 s (15 a minute) |
| upload | 8192 characters per file, 16384 a minute |
| download | 65536 characters per file |
| in flight | 3 requests (more wait their turn) |
| server says "wait" | the request pauses for that long |

**In the server** (`scratchos-server.js`, per computer id), for modified or
hostile clients:

| Limit | Default | Setting |
|---|---|---|
| requests | 30 a minute, bursts of 8 | `REQ_PER_MIN`, `REQ_BURST` |
| uploaded | 32 KB a minute | `UP_PER_MIN` |
| downloaded | 256 KB a minute | `DOWN_PER_MIN` |
| unfinished requests | 3 | `MAX_INFLIGHT` |
| stored per computer | 256 KB | `QUOTA` |
| total storage | 50 MB | `MAX_STORAGE` |
| computers at once | 200 | `MAX_SESSIONS` |
| new requests, everyone | 25 a second | `GLOBAL_PER_SEC` |
| time-out | 5 breaches → ignored for 120 s | `STRIKES`, `BAN_SECONDS` |

A computer over a limit gets a `41 wait` packet, and keeps getting it while it
is timed out. The flood test sends 40 pings at once: 8 are answered, the rest
are refused, the sender is timed out, and other computers are served normally
the whole time.

**In the cloud server** (`relay.js`): 30 writes a second per connection,
8 connections per address, values of digits only.

### Connected or not

The kernel watches `☁ heartbeat`. `net_state()` gives:

| State | When | Taskbar |
|---|---|---|
| **online** | a heartbeat arrived in the last 12 s, and it has changed while we watched or its time is within 2 minutes of ours (an old value left in the variable doesn't count) | three bars |
| **no server** | cloud variables work, but no fresh heartbeat | one yellow bar |
| **offline** | no cloud connection at all (opened from a file, cloud off, not logged in on Scratch) | dim bars with a cross |

Hover the indicator for the state and latency; click it for
**System Settings → Network**, with a **Test connection** button. In the
terminal: `net status`. From Whisker: `net.status().state`.

### Names and storage

Names use letters, digits, `_ - . /`, up to 100 characters, and no `..`.
Computers may write only under `public/` and `users/` (`WRITABLE`). The
server owner puts the Browser's `net://` pages in `pages/`, which computers
can only read. Files are stored in `DATA_DIR`, each with a `.meta.json` that
records who wrote it and when.

### `net://` in the Browser

* `net://` opens `pages/index.yarn`, and `net://about.yarn` opens `pages/about.yarn`.
* `net://public/` (ending in `/`) lists the files there.
* `.yarn` files are shown as pages, and any other file as text.

Scripts in `net://` pages run only for `pages/` (written by the server owner).
For uploaded pages, such as `net://public/...`, scripts are switched off.

## Security

Cloud variables are **anonymous and can be forged**. Anyone can write any
value, including another computer's id, and anyone can read every packet.
So:

* Don't send anything private. There are no passwords and no encryption.
* Treat the per-computer limits as best effort. Someone who changes their id
  for every request gets past the per-computer limits; the global limit,
  the quotas and the relay's limits still apply.
* Uploaded files are public and may be overwritten by anyone.
* On scratch.mit.edu, cloud data is visible in the project's cloud log, and
  the Community Guidelines apply to whatever is stored.

## Hosting

The server is one small Node process with no database, using a few MB of
memory. It needs a cloud server to join.

### Best: your own cloud server + TurboWarp Packager

You control the packet size, the limits and the uptime.

1. **Run `relay.js` and `scratchos-server.js` together on one host.** Good
   options:
   * a small VPS (Hetzner, DigitalOcean, Oracle's free tier) with Caddy in
     front for TLS;
   * **Fly.io** or **Railway** (both keep WebSocket processes running);
   * Render's paid tier (the free tier sleeps).

   Browsers on `https` pages need **`wss://`**: put the relay behind a TLS
   proxy and set `TRUST_PROXY=1`.

   ```
   # Caddyfile
   cloud.example.com {
       reverse_proxy localhost:9080
   }
   ```

   ```
   PORT=9080 TRUST_PROXY=1 MAX_VALUE=2048 node relay.js
   CLOUD_HOST=ws://localhost:9080 PROJECT_ID=scratchos MAX_PACKET=2048 node scratchos-server.js
   ```

   Keep both running with systemd or pm2, and back up `DATA_DIR`.
2. **Raise the packet size.** On your own relay, a value can be longer than
   Scratch's 256 digits. With `MAX_VALUE` and `MAX_PACKET` at 2048, each
   packet carries about 1000 characters instead of 118, which is about 8×
   faster. ScratchOS reads the size from the heartbeat, so nothing in the
   project has to change.
3. **Package ScratchOS** with the [TurboWarp Packager](https://packager.turbowarp.org/):
   * Cloud variables → "Use a custom cloud host", `wss://cloud.example.com`.
   * Set the same project id as `PROJECT_ID`.
   * Turn on the custom stage size (1280×720).

   Host the HTML anywhere static: GitHub Pages, Netlify or itch.io. Each
   player gets a random username, which the protocol doesn't use.

### Quick test: TurboWarp's public cloud server

`wss://clouddata.turbowarp.org` works with a shared Scratch project id and needs no
hosting for the relay. Run only `scratchos-server.js` with
`CLOUD_HOST=wss://clouddata.turbowarp.org PROJECT_ID=<id>`, a descriptive
`USERNAME`, and a `USER_AGENT` with a way to contact you, which its operators
ask bots for. Keep `MAX_PACKET` at 256 and the default limits, since the
server is shared with everyone else's projects. Use it for trying
things out, not as the permanent home.

### Possible but limited: scratch.mit.edu

To run on Scratch itself:

* The server must log in as a Scratcher account and connect to
  `wss://clouddata.scratch.mit.edu` with that session.
* Cloud variables work only for logged-in **Scratchers**, so New Scratchers
  are offline.
* Values are capped at 256 digits.
* Scratch throttles heavy cloud use, so set `SEND_PER_SEC=8`.
* Bots are against the spirit of the cloud rules unless the project is clear
  about it, and moderators may reset the variables.

The included server does not do the Scratch login. Add it with a library such
as scratchattach (Python) or by porting the session handshake.
