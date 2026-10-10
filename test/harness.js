// Headless test harness: runs a .sb3 in the real TurboWarp runtime
// (Scaffolding from @turbowarp/packager) inside Playwright's Chromium.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const SCAFFOLDING = path.join(__dirname, 'node_modules/@turbowarp/packager/dist/scaffolding/scaffolding-min.js');
const CHROMIUM = process.env.CHROMIUM_PATH || findChromium();

function findChromium() {
  const base = '/opt/pw-browsers';
  for (const d of fs.readdirSync(base)) {
    if (d.startsWith('chromium-')) {
      const p = path.join(base, d, 'chrome-linux', 'chrome');
      if (fs.existsSync(p)) return p;
    }
  }
  return path.join(base, 'chromium');
}

async function launch(sb3Path, opts = {}) {
  const browser = await chromium.launch({
    executablePath: CHROMIUM,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  const scale = opts.scale || 1;
  const page = await browser.newPage({ viewport: { width: 480 * scale, height: 360 * scale } });
  const logs = [];
  page.on('console', (m) => logs.push(m.text()));
  page.on('pageerror', (e) => logs.push('PAGEERROR ' + e.message));
  await page.setContent(`<!doctype html><html><head><style>
    html,body{margin:0;padding:0;background:#000;overflow:hidden}
    #project{width:${480 * scale}px;height:${360 * scale}px}
  </style></head><body><div id="project"></div></body></html>`);
  await page.addScriptTag({ path: SCAFFOLDING });
  const b64 = fs.readFileSync(sb3Path).toString('base64');
  await page.evaluate(async ({ b64, hq }) => {
    const bin = atob(b64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    const s = new Scaffolding.Scaffolding();
    s.width = 480; s.height = 360;
    s.setup();
    s.appendTo(document.getElementById('project'));
    window.scaffolding = s;
    window.vm = s.vm;
    await s.loadProject(buf.buffer);
    if (hq) s.renderer.setUseHighQualityRender(true);
    s.start();
    s.greenFlag();
  }, { b64, hq: !!opts.hq });

  const api = {
    browser, page, logs,
    sleep: (ms) => page.waitForTimeout(ms),
    async shot(file) {
      const el = await page.$('canvas');
      await el.screenshot({ path: file });
    },
    // read a variable/list from a sprite ("Stage" for globals) by display name
    async read(sprite, name) {
      return page.evaluate(({ sprite, name }) => {
        const t = sprite === 'Stage' ? vm.runtime.getTargetForStage() : vm.runtime.getSpriteTargetByName(sprite);
        for (const v of Object.values(t.variables)) if (v.name === name) return v.value;
        return undefined;
      }, { sprite, name });
    },
    async write(sprite, name, value) {
      return page.evaluate(({ sprite, name, value }) => {
        const t = sprite === 'Stage' ? vm.runtime.getTargetForStage() : vm.runtime.getSpriteTargetByName(sprite);
        for (const v of Object.values(t.variables)) if (v.name === name) { v.value = value; return true; }
        return false;
      }, { sprite, name, value });
    },
    async type(text, delay = 40) {
      for (const ch of text) {
        if (ch === '\n') await page.keyboard.press('Enter');
        else await page.keyboard.type(ch);
        await page.waitForTimeout(delay);
      }
    },
    async press(key, delay = 60) {
      await page.keyboard.press(key);
      await page.waitForTimeout(delay);
    },
    async close() { await browser.close(); },
  };
  return api;
}

module.exports = { launch };

if (require.main === module) {
  // node harness.js project.sb3 out.png [waitMs] [--hq] [--scale=N]
  (async () => {
    const [sb3, out, wait] = process.argv.slice(2);
    const hq = process.argv.includes('--hq');
    const sc = process.argv.find((a) => a.startsWith('--scale='));
    const h = await launch(sb3, { hq, scale: sc ? +sc.split('=')[1] : 1 });
    await h.sleep(+(wait || 2000));
    await h.shot(out);
    console.log(h.logs.join('\n'));
    await h.close();
  })().catch((e) => { console.error(e); process.exit(1); });
}
