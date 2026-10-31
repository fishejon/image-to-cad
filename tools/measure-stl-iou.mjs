#!/usr/bin/env node
/**
 * Measure silhouette IoU: reference photo vs an STL (e.g. lab bespoke export).
 * Requires: npm i -D puppeteer-core; local Chrome or @sparticuz/chromium
 *
 * Usage:
 *   node tools/measure-stl-iou.mjs chair_02 lab/furniture_cad/out/chair_02_bespoke/chair_02.stl --write
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const id = process.argv[2];
const stlArg = process.argv[3];
const write = process.argv.includes('--write');

if (!id || !stlArg) {
  console.error('Usage: node tools/measure-stl-iou.mjs <chair_id> <path/to.stl> [--write]');
  process.exit(1);
}

const stlPath = path.isAbsolute(stlArg) ? stlArg : path.join(root, stlArg);
if (!fs.existsSync(stlPath)) {
  console.error('STL not found: ' + stlPath);
  process.exit(2);
}

const photoCandidates = ['.jpg', '.jpeg', '.png', '.webp'].map(ext => path.join(root, 'evals/photos/chairs', id + ext));
const photo = photoCandidates.find(p => fs.existsSync(p));
if (!photo) {
  console.error('No photo for ' + id);
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
    '/usr/bin/chromium'
  ].filter(Boolean);
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      return { executablePath: p, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--disable-dev-shm-usage'] };
    }
  }
  throw new Error('No Chrome found');
}

const chrome = await resolveChrome();
const browser = await puppeteer.launch({
  executablePath: chrome.executablePath,
  args: chrome.args,
  headless: 'shell',
  defaultViewport: { width: 1200, height: 900 }
});
const page = await browser.newPage();

const stlBuf = fs.readFileSync(stlPath);
const photoBuf = fs.readFileSync(photo);
const photoMime = photo.endsWith('.png') ? 'image/png' : photo.endsWith('.webp') ? 'image/webp' : 'image/jpeg';
const threeMin = fs.readFileSync(path.join(root, 'node_modules/three/build/three.min.js'), 'utf8');
const stlLoaderSrc = fs.readFileSync(path.join(root, 'node_modules/three/examples/js/loaders/STLLoader.js'), 'utf8');

await page.setContent(`<!doctype html><html><body style="margin:0;background:#fff">
<canvas id="c" width="1200" height="900"></canvas>
</body></html>`);
await page.addScriptTag({ content: threeMin });
await page.addScriptTag({ content: stlLoaderSrc });

const photoB64 = photoBuf.toString('base64');
const stlB64 = stlBuf.toString('base64');
const result = await page.evaluate(async (stlB64, photoMime, photoB64) => {
  const size = 96;
  const maskFromUrl = (url) => new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      const c = document.createElement('canvas'); c.width = size; c.height = size;
      const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, size, size);
      const k = Math.min(size / im.width, size / im.height);
      const ww = Math.max(1, Math.round(im.width * k)), hh = Math.max(1, Math.round(im.height * k));
      x.drawImage(im, (size - ww) / 2, (size - hh) / 2, ww, hh);
      const data = x.getImageData(0, 0, size, size).data;
      const mask = new Uint8Array(size * size);
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

  const maskIoU = (a, b) => {
    if (!a || !b || a.length !== b.length || !a.length) return 1;
    let inter = 0, uni = 0;
    for (let i = 0; i < a.length; i++) {
      const A = a[i] > 0, B = b[i] > 0;
      if (A && B) inter++;
      if (A || B) uni++;
    }
    return uni ? inter / uni : 1;
  };

  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, alpha: false });
  renderer.setClearColor(0xffffff, 1);
  renderer.setSize(1200, 900, false);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xffffff);
  const camera = new THREE.PerspectiveCamera(35, 1200 / 900, 1, 5000);
  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const d1 = new THREE.DirectionalLight(0xffffff, 0.7); d1.position.set(2, 3, 4); scene.add(d1);
  const d2 = new THREE.DirectionalLight(0xffffff, 0.35); d2.position.set(-2, 1, -1); scene.add(d2);

  const bin = atob(stlB64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const loader = new THREE.STLLoader();
  const geom = loader.parse(bytes.buffer);
  geom.computeVertexNormals();
  const mesh = new THREE.Mesh(geom, new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.35, metalness: 0.05 }));
  scene.add(mesh);

  geom.computeBoundingBox();
  const box = geom.boundingBox;
  const center = new THREE.Vector3();
  box.getCenter(center);
  const size3 = new THREE.Vector3();
  box.getSize(size3);
  const maxDim = Math.max(size3.x, size3.y, size3.z);
  /* ¾ front-ish: +X right, +Z up (build123d), camera from front-right-above */
  const dist = maxDim * 2.4;
  camera.position.set(center.x + dist * 0.55, center.y - dist * 0.85, center.z + dist * 0.45);
  camera.up.set(0, 0, 1);
  camera.lookAt(center);
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);

  const modelUrl = canvas.toDataURL('image/jpeg', 0.92);
  const refUrl = 'data:' + photoMime + ';base64,' + photoB64;
  const ref = await maskFromUrl(refUrl);
  const model = await maskFromUrl(modelUrl);
  return {
    iou: maskIoU(ref.mask, model.mask),
    refFill: ref.fill,
    modelFill: model.fill,
    refSize: [ref.w, ref.h],
    bbox: { min: box.min.toArray(), max: box.max.toArray(), size: size3.toArray() },
    modelDataLen: modelUrl.length
  };
}, stlB64, photoMime, photoB64);

await browser.close();

const cells = 96 * 96;
console.log(JSON.stringify(result, null, 2));
if (!result || !isFinite(result.iou)) {
  console.error('IoU failed');
  process.exit(5);
}
if (result.refFill < cells * 0.02 || result.refFill > cells * 0.98) {
  console.error('Photo mask fill out of range: ' + result.refFill);
  process.exit(7);
}
if (result.modelFill < cells * 0.02 || result.modelFill > cells * 0.98) {
  console.error('Model mask fill out of range: ' + result.modelFill);
  process.exit(8);
}

const iou = Math.round(result.iou * 1000) / 1000;
const rated = iou >= 0.7 ? 'Match' : iou >= 0.55 ? 'Close+' : iou >= 0.4 ? 'Close' : 'Wrong';
console.log(id + ' IoU=' + iou + ' → ' + rated + ' (photo ' + result.refFill + ', model ' + result.modelFill + ')');

if (!write) {
  console.log('Pass --write to update score JSON');
  process.exit(0);
}

const scorePath = path.join(root, 'evals/photos/chairs', id + '.score.json');
const score = fs.existsSync(scorePath) ? JSON.parse(fs.readFileSync(scorePath, 'utf8')) : {};
score.iou = iou;
score.topology_ok = score.topology_ok !== false;
const finalRated = score.topology_ok === false ? 'Wrong' : rated;
score.ratingHint = finalRated;
score.expectRating = finalRated;
score.notes = ((score.notes || '').replace(/\s*IoU measured via measure-stl-iou\.mjs[^.]*\./g, '').trim()
  + ' IoU measured via measure-stl-iou.mjs vs ' + path.relative(root, stlPath) + '.').trim();
fs.writeFileSync(scorePath, JSON.stringify(score, null, 2) + '\n');
console.log('Wrote ' + path.relative(root, scorePath));
