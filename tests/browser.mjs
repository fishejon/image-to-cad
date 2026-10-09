// Headless-browser smoke test (optional; needs: npm i puppeteer-core @sparticuz/chromium). Usage: node tests/browser.mjs [shots-dir]
import chromium from '@sparticuz/chromium'; import puppeteer from 'puppeteer-core'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..'), out = process.argv[2] || path.join(root, 'tests/out'); fs.mkdirSync(out, { recursive: true });
const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), args: [...chromium.args, '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'], headless: 'shell', defaultViewport: { width: 1500, height: 900 } });
const page = await browser.newPage(), errs = []; page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
await page.setRequestInterception(true);
page.on('request', r => { const u = r.url(); const nm = path.join(root, 'node_modules/three'); if (u.includes('three.min.js')) return r.respond({ status: 200, contentType: 'application/javascript', body: fs.readFileSync(nm + '/build/three.min.js') }); if (u.includes('OrbitControls.js')) return r.respond({ status: 200, contentType: 'application/javascript', body: fs.readFileSync(nm + '/examples/js/controls/OrbitControls.js') }); if (u.startsWith('file:')) return r.continue(); r.abort(); });
await page.goto('file://' + path.join(root, 'dist/image-to-cad.html')); await page.waitForFunction(() => window.__cad && document.getElementById('loading').style.display === 'none', { timeout: 120000 }); await new Promise(r => setTimeout(r, 1200));
const ids = await page.evaluate(() => Object.keys(window.EXAMPLES)); const results = [];
for (const id of ids) { await page.evaluate(id => __cad.loadExample(id), id); await new Promise(r => setTimeout(r, 900)); await page.screenshot({ path: path.join(out, id + '.png') });
  results.push(await page.evaluate((id) => ({ id, pieces: __cad.S.R.length, errors: __cad.S.lastErrors.length, kin: Object.keys(__cad.S.M.kinematics).length, params: __cad.S.M.paramDefs.length }), id)); }
console.table(results); console.log('console errors:', errs); await browser.close(); if (errs.length || results.some(r => r.errors)) process.exit(1);
