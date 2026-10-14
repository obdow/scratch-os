# ScratchOS network server

The server side of the ScratchOS network. See [docs/NETWORK.md](../docs/NETWORK.md)
for how it works, the limits, and where to host it.

```
npm install
node relay.js                                    # cloud server, ws://localhost:9080
CLOUD_HOST=ws://localhost:9080 PROJECT_ID=scratchos node scratchos-server.js
npm test                                         # protocol, concurrency and flood tests
```

| File | What it is |
|---|---|
| `relay.js` | a cloud-variable server speaking the TurboWarp / Scratch protocol (or use TurboWarp's) |
| `scratchos-server.js` | joins the cloud variables and answers ScratchOS: ping, get, put, list |
| `lib/protocol.js` | packet format and text encoding, shared with the kernel's `src/net.sbs` |
| `lib/client.js` | a client that behaves like ScratchOS, for tests and scripts |
| `data/pages/` | the pages the Browser shows at `net://` (read-only to computers) |
| `data/public/` | files anyone may upload or download |

Both programs are configured with environment variables, listed at the top of
each file.
