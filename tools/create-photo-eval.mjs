#!/usr/bin/env node
/**
 * Careful Create against local eval photos → stance dump + score.create block.
 *
 * Usage:
 *   npm run create:photos -- chair_04
 *   npm run create:photos -- --all
 *   npm run create:photos -- chair_04 --quality balanced
 *
 * Auth: local ANTHROPIC_API_KEY / .env, OR Vercel proxy (default
 * https://image-to-cad-gray.vercel.app/api/messages). Override with CREATE_PROXY_URL.
 * Does not measure silhouette IoU (use measure:chair-iou --spec … after).
 */
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import vm from 'vm';

const require = createRequire(import.meta.url);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const chairsDir = path.join(root, 'evals/photos/chairs');
const outDir = path.join(chairsDir, 'out');

function loadDotEnv() {
  const p = path.join(root, '.env');
  if (!fs.existsSync(p)) return;
  fs.readFileSync(p, 'utf8').split('\n').forEach(line => {
    const s = line.trim();
    if (!s || s.startsWith('#')) return;
    const i = s.indexOf('=');
    if (i < 0) return;
    const k = s.slice(0, i).trim();
    let v = s.slice(i + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    if (k && process.env[k] == null) process.env[k] = v;
  });
}
loadDotEnv();

const WEDGE = new Set(['chair_02', 'chair_04']); /* primary Create scorecard gate */
const ALL_READY = () => fs.readdirSync(chairsDir)
  .filter(f => /^chair_\d+\.jpg$/i.test(f) || /^chair_\d+\.png$/i.test(f) || /^chair_\d+\.webp$/i.test(f))
  .map(f => f.replace(/\.(jpg|jpeg|png|webp)$/i, ''))
  .filter((id, i, a) => a.indexOf(id) === i)
  .sort();

const argv = process.argv.slice(2);
const quality = (() => {
  const i = argv.indexOf('--quality');
  return i >= 0 ? argv[i + 1] : 'careful';
})();
const model = (() => {
  const i = argv.indexOf('--model');
  return i >= 0 ? argv[i + 1] : 'claude-sonnet-5-5';
})();
const ids = argv.includes('--all')
  ? [...WEDGE]
  : argv.filter(a => !a.startsWith('--') && a !== quality && a !== model && argv[argv.indexOf(a) - 1] !== '--quality' && argv[argv.indexOf(a) - 1] !== '--model');

if (!ids.length) {
  console.error('Usage: npm run create:photos -- chair_04 | --all');
  process.exit(1);
}

const apiKey = process.env.ANTHROPIC_API_KEY || '';
const proxyUrl = process.env.CREATE_PROXY_URL
  || process.env.PROXY_URL
  || 'https://image-to-cad-gray.vercel.app/api/messages';
const useProxy = !apiKey;
if (useProxy) {
  console.log('No local ANTHROPIC_API_KEY — using Vercel proxy: ' + proxyUrl);
}

/* Load CAD + vision in a VM (same as tests/helpers.js). */
global.THREE = require('three');
global.window = global;
global.fetch = fetch;
for (const f of [
  'src/core/geo.js', 'src/core/curves.js', 'src/core/units.js', 'src/core/csg.js',
  'src/core/checks.js', 'src/core/joinery.js', 'src/core/spec.js', 'src/core/exporter.js',
  'src/core/store.js', 'src/ai/vision.js'
]) {
  vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f });
}
const CAD = global.CAD;
const V = CAD.vision;

function findPhoto(id) {
  return ['.jpg', '.jpeg', '.png', '.webp']
    .map(ext => path.join(chairsDir, id + ext))
    .find(p => fs.existsSync(p));
}

function loadMeta(id) {
  const p = path.join(chairsDir, id + '.json');
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : {};
}

function metricsFromMeta(meta) {
  const mm = meta.source && meta.source.dims_mm;
  if (!mm) return null;
  return { wMm: mm.overall_w || 0, dMm: mm.overall_d || 0, hMm: mm.overall_h || 0 };
}

function mimeFor(p) {
  if (/\.png$/i.test(p)) return 'image/png';
  if (/\.webp$/i.test(p)) return 'image/webp';
  return 'image/jpeg';
}

async function runOne(id) {
  const photo = findPhoto(id);
  if (!photo) throw new Error('No photo for ' + id);
  const meta = loadMeta(id);
  const buf = fs.readFileSync(photo);
  const dataUrl = 'data:' + mimeFor(photo) + ';base64,' + buf.toString('base64');
  const preset = CAD.store.qualityPreset(quality);
  const metrics = metricsFromMeta(meta);
  const hints = [
    meta.notes || '',
    metrics ? ('overall ' + [metrics.wMm, metrics.dMm, metrics.hMm].filter(Boolean).join(' × ') + ' mm') : ''
  ].filter(Boolean).join('. ');

  let chairFewShot = null;
  try {
    const lakin = JSON.parse(fs.readFileSync(path.join(root, 'examples/lakin-chair.json'), 'utf8'));
    const dining = JSON.parse(fs.readFileSync(path.join(root, 'examples/dining-chair.json'), 'utf8'));
    const kind = CAD.store.pickChairFewShotKind({ structure: { memberContinuity: 'continuous' } }, hints);
    chairFewShot = CAD.store.chairFewShotFromExample(kind === 'lakin' ? lakin : dining, kind);
  } catch (e) { /* optional */ }

  const logs = [];
  console.log('\n=== ' + id + ' · Quality ' + preset.id + ' · ' + model + ' ===');
  const t0 = Date.now();
  const res = await V.run({
    image: dataUrl,
    hints,
    metrics,
    task: 'design',
    inputMode: 'photo',
    quality: preset.id,
    domain: 'furniture',
    pastExamples: chairFewShot ? [chairFewShot] : [],
    chairFewShot,
    provider: useProxy
      ? { kind: 'proxy', proxyUrl, model }
      : { kind: 'anthropic', apiKey, model },
    maxRounds: preset.rounds,
    visual: false, /* IoU measured separately via measure:chair-iou --spec */
    onLog: (m) => { logs.push(m); console.log('  ' + m); }
  });
  const ms = Date.now() - t0;
  const inv = res.inventory || {};
  const st = inv.structure || {};
  const got = V.analyzeStance(res.spec);
  const M = CAD.buildSpec(res.spec);
  const likeness = V.likeness(M, inv, { spec: res.spec, metrics });

  fs.mkdirSync(outDir, { recursive: true });
  const specPath = path.join(outDir, id + '.create.json');
  fs.writeFileSync(specPath, JSON.stringify(res.spec, null, 2) + '\n');

  const createBlock = {
    at: new Date().toISOString(),
    quality: preset.id,
    model,
    durationMs: ms,
    geometryOk: !!(res.rep && res.rep.ok),
    round: res.round || null,
    likenessPenalty: likeness.penalty || 0,
    inventoryStance: {
      legStance: st.legStance || null,
      frontLean: st.frontLean || null,
      rearLean: st.rearLean || null,
      backRake: st.backRake || null,
      rakeBreak: st.rakeBreak || null,
      memberContinuity: st.memberContinuity || null
    },
    inferredStance: {
      stance: got.stance,
      frontForward: !!got.frontForward,
      aftAboveSeat: !!got.aftAboveSeat,
      nearSeatBreak: !!got.nearSeatBreak,
      leanSweeps: got.leanSweeps,
      verticalLegs: got.verticalLegs
    },
    inventorySummary: V.summarizeInventory(inv),
    specPath: path.relative(root, specPath),
    iou: null,
    rating: null,
    ratingHint: null,
    wedge: WEDGE.has(id)
  };

  const scorePath = path.join(chairsDir, id + '.score.json');
  const score = fs.existsSync(scorePath) ? JSON.parse(fs.readFileSync(scorePath, 'utf8')) : {};
  score.create = createBlock;
  if (score.topology_ok == null && createBlock.geometryOk) score.topology_ok = true;
  fs.writeFileSync(scorePath, JSON.stringify(score, null, 2) + '\n');

  console.log('Wrote ' + path.relative(root, specPath));
  console.log('Stance inventory:', JSON.stringify(createBlock.inventoryStance));
  console.log('Stance inferred:', JSON.stringify(createBlock.inferredStance));
  console.log('Likeness penalty:', createBlock.likenessPenalty, '· geometryOk:', createBlock.geometryOk);
  console.log('Next: npm run build && npm run measure:chair-iou -- ' + id + ' --spec ' + createBlock.specPath + ' --write');
  return createBlock;
}

let failed = 0;
for (const id of ids) {
  try {
    await runOne(id);
  } catch (e) {
    failed++;
    console.error(id + ' FAILED: ' + (e && e.message ? e.message : e));
  }
}
console.log(failed ? '\n' + failed + ' failed' : '\nAll Create eval runs finished.');
process.exit(failed ? 1 : 0);
