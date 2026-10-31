#!/usr/bin/env node
/* Score photo-loop chairs with the same rubric as the app (silhouette-iou-v1).
   Usage:
     node tools/score-photo-chairs.js
     node tools/score-photo-chairs.js --predictions evals/photos/chairs/predictions.json

   predictions.json shape:
     { "chair_01": { "topology_ok": false, "iou": 0.22, "missing_block": "bent_panel", "notes": "..." }, ... }

   Without predictions, uses embedded scores in each chair_NN.score.json if present,
   else falls back to SCORE.md manual rows (topology only → rating from hint).
*/
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const dir = path.join(root, 'evals/photos/chairs');

/* Minimal vision stub for scorePhotoChair without loading THREE */
const V = {
  scorePhotoChair(o) {
    o = o || {};
    const topology_ok = !!o.topology_ok;
    const iou = (o.iou != null && isFinite(o.iou)) ? +o.iou : null;
    let rating = 'Wrong';
    if (topology_ok && iou != null) {
      if (iou >= 0.7) rating = 'Match';
      else if (iou >= 0.55) rating = 'Close+';
      else if (iou >= 0.4) rating = 'Close';
      else rating = 'Wrong';
    } else if (topology_ok && iou == null) {
      rating = o.ratingHint || 'Close';
    } else rating = 'Wrong';
    return { rating, topology_ok, iou, missing_block: o.missing_block || null, notes: o.notes || '', method: 'silhouette-iou-v1' };
  }
};

function loadPredictions() {
  const i = process.argv.indexOf('--predictions');
  if (i < 0 || !process.argv[i + 1]) return {};
  return JSON.parse(fs.readFileSync(path.resolve(process.argv[i + 1]), 'utf8'));
}

function listChairs() {
  return fs.readdirSync(dir)
    .filter(f => /^chair_\d+\.json$/.test(f))
    .map(f => f.replace(/\.json$/, ''))
    .sort();
}

function embeddedScore(id) {
  const p = path.join(dir, id + '.score.json');
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const preds = loadPredictions();
const rows = [];
let fail = 0;
console.log('Photo chair scores (silhouette-iou-v1)\n');
console.log('| id | rating | topology_ok | iou | missing_block | notes |');
console.log('| --- | --- | --- | --- | --- | --- |');

listChairs().forEach(id => {
  const pred = preds[id] || embeddedScore(id) || {};
  const scored = V.scorePhotoChair({
    topology_ok: pred.topology_ok,
    iou: pred.iou,
    missing_block: pred.missing_block,
    notes: pred.notes,
    ratingHint: pred.ratingHint || pred.rating
  });
  const iouStr = scored.iou == null ? '—' : scored.iou.toFixed(2);
  const miss = scored.missing_block || '—';
  const notes = (scored.notes || pred.notes || '').replace(/\|/g, '/');
  console.log('| ' + id + ' | ' + scored.rating + ' | ' + (scored.topology_ok ? 'Y' : 'N') + ' | ' + iouStr + ' | ' + miss + ' | ' + notes + ' |');
  rows.push({ id, ...scored });
  if (pred.expectRating && pred.expectRating !== scored.rating) {
    console.error('FAIL ' + id + ': expected rating ' + pred.expectRating + ' got ' + scored.rating);
    fail++;
  }
});

console.log('\n' + rows.length + ' chair(s). Method: silhouette IoU when measured; else topology + ratingHint.');
console.log('Add/update ' + path.join('evals/photos/chairs', 'chair_NN.score.json') + ' or pass --predictions after measuring IoU in the app.');
process.exit(fail ? 1 : 0);
