#!/usr/bin/env node
/**
 * Optional: measure silhouette IoU for a photo chair via headless Chromium.
 * Requires: npm i -D puppeteer-core  (Chrome or @sparticuz/chromium)
 *           npm run build
 *
 * Usage:
 *   npm run measure:chair-iou -- chair_02
 *   node tools/measure-chair-iou.mjs chair_02 --example dining-chair
 *
 * Baseline only: photo vs a built-in EXAMPLE mesh, not Create-from-photo likeness.
 * Rejects empty / saturated masks (those falsely yield IoU=1 via maskIoU).
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const id = process.argv[2];
const exIdx = process.argv.indexOf('--example');
const exampleId = exIdx >= 0 ? process.argv[exIdx + 1] : 'dining-chair';
const write = process.argv.includes('--write');

if (!id) {
  console.error('Usage: node tools/measure-chair-iou.mjs <chair_id> [--example dining-chair] [--write]');
  process.exit(1);
}

const photoCandidates = ['.jpg', '.jpeg', '.png', '.webp'].map(ext => path.join(root, 'evals/photos/chairs', id + ext));
const photo = photoCandidates.find(p => fs.existsSync(p));
if (!photo) {
  console.error('No local photo for ' + id + ' under evals/photos/chairs/ (jpg/png/webp). Photos are gitignored — keep them locally.');
  process.exit(2);
}

let puppeteer;
try {
  puppeteer = (await import('puppeteer-core')).default;
} catch (e) {
  console.error('Install: npm i -D puppeteer-core');
  process.exit(3);
}

async function resolveChrome() {
  try {
    const chromium = (await import('@sparticuz/chromium')).default;
    return { executablePath: await chromium.executablePath(), args: [...chromium.args, '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] };
  } catch (_) { /* fall through */ }
  const candidates = [
    process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser'
  ].filter(Boolean);
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      return { executablePath: p, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--disable-dev-shm-usage'] };
    }
  }
  throw new Error('No Chrome/Chromium found. Set CHROME_PATH or npm i -D @sparticuz/chromium');
}

const dist = path.join(root, 'dist/image-to-cad.html');
if (!fs.existsSync(dist)) {
  console.error('Missing dist/image-to-cad.html — run: npm run build');
  process.exit(4);
}

const chrome = await resolveChrome();
const browser = await puppeteer.launch({
  executablePath: chrome.executablePath,
  args: chrome.args,
  headless: 'shell',
  defaultViewport: { width: 1200, height: 900 }
});
const page = await browser.newPage();
const photoBuf = fs.readFileSync(photo);
const photoMime = photo.endsWith('.png') ? 'image/png' : photo.endsWith('.webp') ? 'image/webp' : 'image/jpeg';
const photoB64 = photoBuf.toString('base64');

await page.setRequestInterception(true);
page.on('request', r => {
  const u = r.url();
  const nm = path.join(root, 'node_modules/three');
  if (u.includes('three.min.js')) return r.respond({ status: 200, contentType: 'application/javascript', body: fs.readFileSync(nm + '/build/three.min.js') });
  if (u.includes('OrbitControls.js')) return r.respond({ status: 200, contentType: 'application/javascript', body: fs.readFileSync(nm + '/examples/js/controls/OrbitControls.js') });
  if (u.startsWith('file:')) return r.continue();
  r.abort();
});

await page.goto('file://' + dist);
await page.waitForFunction(() => window.__cad && document.getElementById('loading').style.display === 'none', { timeout: 120000 });
const hasEx = await page.evaluate((exampleId) => !!(window.EXAMPLES && window.EXAMPLES[exampleId]), exampleId);
if (!hasEx) {
  await browser.close();
  console.error('Example not found: ' + exampleId);
  process.exit(6);
}
await page.evaluate((exampleId) => __cad.loadExample(exampleId), exampleId);
await new Promise(r => setTimeout(r, 1200));
await page.evaluate(() => {
  __cad.viewNow('iso');
  if (__cad.updateVisuals) __cad.updateVisuals();
  if (__cad.renderer && __cad.scene && __cad.camera) __cad.renderer.render(__cad.scene, __cad.camera);
});
await new Promise(r => setTimeout(r, 500));

const result = await page.evaluate(async (photoMime, photoB64) => {
  const size = 96;
  const maskFromUrl = (url) => new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      const c = document.createElement('canvas'); c.width = size; c.height = size;
      const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, size, size);
      const k = Math.min(size / im.width, size / im.height);
      const ww = Math.max(1, Math.round(im.width * k)), hh = Math.max(1, Math.round(im.height * k));
      x.drawImage(im, (size - ww) / 2, (size - hh) / 2, ww, hh);
      const data = x.getImageData(0, 0, size, size).data, mask = new Uint8Array(size * size);
      let fill = 0;
      for (let i = 0, p = 0; i < data.length; i += 4, p++) {
        const a = data[i + 3], lum = 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
        const on = (a > 20 && lum < 245) ? 1 : 0;
        mask[p] = on; fill += on;
      }
      resolve({ mask, fill, w: im.width, h: im.height });
    };
    im.onerror = () => reject(new Error('image load failed'));
    im.src = url;
  });

  if (__cad.renderer && __cad.scene && __cad.camera) __cad.renderer.render(__cad.scene, __cad.camera);
  const modelUrl = __cad.renderer.domElement.toDataURL('image/jpeg', 0.92);
  const refUrl = 'data:' + photoMime + ';base64,' + photoB64;
  const ref = await maskFromUrl(refUrl);
  const model = await maskFromUrl(modelUrl);
  const iou = __cad.CAD.vision.maskIoU(ref.mask, model.mask);
  return {
    iou,
    refFill: ref.fill,
    modelFill: model.fill,
    refSize: [ref.w, ref.h],
    modelDataLen: modelUrl.length,
    pieces: __cad.S.R ? __cad.S.R.length : 0,
    errors: (__cad.S.lastErrors || []).length
  };
}, photoMime, photoB64);

await browser.close();

const cells = 96 * 96;
console.log(JSON.stringify(result, null, 2));

if (!result || result.iou == null || !isFinite(result.iou)) {
  console.error('IoU measurement failed');
  process.exit(5);
}
if (result.refFill < cells * 0.02 || result.refFill > cells * 0.98) {
  console.error('Photo silhouette mask looks empty or saturated (fill=' + result.refFill + '/' + cells + '). Not writing score.');
  process.exit(7);
}
if (result.modelFill < cells * 0.02 || result.modelFill > cells * 0.98) {
  console.error('Model silhouette mask looks empty or saturated (fill=' + result.modelFill + '/' + cells + '). Headless WebGL may not be rendering — measure in the app instead.');
  process.exit(8);
}
if (result.pieces < 1) {
  console.error('Example loaded with 0 pieces');
  process.exit(9);
}

const iou = Math.round(result.iou * 1000) / 1000;
const rated = (() => {
  if (iou >= 0.7) return 'Match';
  if (iou >= 0.55) return 'Close+';
  if (iou >= 0.4) return 'Close';
  return 'Wrong';
})();
console.log(id + ' IoU=' + iou + ' → ' + rated + ' (photo fill ' + result.refFill + ', model fill ' + result.modelFill + ')');
console.log('Note: photo vs EXAMPLE mesh is a tooling baseline, not photo→Create likeness.');

if (!write) {
  console.log('Pass --write to update evals/photos/chairs/' + id + '.score.json');
  process.exit(0);
}

const scorePath = path.join(root, 'evals/photos/chairs', id + '.score.json');
const score = fs.existsSync(scorePath) ? JSON.parse(fs.readFileSync(scorePath, 'utf8')) : {};
score.iou = iou;
if (score.topology_ok == null) score.topology_ok = true;
score.notes = ((score.notes || '').replace(/\s*IoU measured via measure-chair-iou\.mjs[^.]*\./g, '').trim()
  + ' IoU measured via measure-chair-iou.mjs vs example ' + exampleId + '.').trim();
const finalRated = score.topology_ok === false ? 'Wrong' : rated;
score.ratingHint = finalRated;
score.expectRating = finalRated;
fs.writeFileSync(scorePath, JSON.stringify(score, null, 2) + '\n');
console.log('Wrote ' + path.relative(root, scorePath));
