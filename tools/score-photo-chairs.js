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
    const trusted = o.iou_quality !== 'untrusted_room_background';
    const iou = (trusted && o.iou != null && isFinite(o.iou)) ? +o.iou : null;
    let rating = 'Wrong';
    if (topology_ok && iou != null) {
      if (iou >= 0.7) rating = 'Match';
      else if (iou >= 0.55) rating = 'Close+';
      else if (iou >= 0.4) rating = 'Close';
      else rating = 'Wrong';
    } else if (topology_ok && iou == null) {
      rating = o.ratingHint || 'Close';
    } else rating = 'Wrong';
    return { rating, topology_ok, iou: (o.iou != null && isFinite(o.iou)) ? +o.iou : null, missing_block: o.missing_block || null, notes: o.notes || '', method: 'silhouette-iou-v1' };
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
    .filter(id => {
      try {
        const meta = JSON.parse(fs.readFileSync(path.join(dir, id + '.json'), 'utf8'));
        if (meta && meta.status === 'awaiting_photo') return false;
      } catch (e) { /* score anyway */ }
      return fs.existsSync(path.join(dir, id + '.score.json'));
    })
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
console.log('| id | gold rating | topology_ok | gold iou | Create rating | Create iou | missing_block | notes |');
console.log('| --- | --- | --- | --- | --- | --- | --- | --- |');

let createMeasured = 0;
let createClosePlus = 0;
listChairs().forEach(id => {
  const pred = preds[id] || embeddedScore(id) || {};
  const scored = V.scorePhotoChair({
    topology_ok: pred.topology_ok,
    iou: pred.iou,
    iou_quality: pred.iou_quality,
    missing_block: pred.missing_block,
    notes: pred.notes,
    ratingHint: pred.ratingHint || pred.rating
  });
  const iouStr = scored.iou == null ? '—' : scored.iou.toFixed(2) + (pred.iou_quality === 'untrusted_room_background' ? '*' : '');
  const miss = scored.missing_block || '—';
  const notes = (scored.notes || pred.notes || '').replace(/\|/g, '/');
  const cr = pred.create || {};
  const createTrusted = cr.iou_quality !== 'untrusted_room_background';
  let createRating = cr.rating || cr.ratingHint || (cr.at ? 'pending IoU' : '—');
  if (cr.at && !createTrusted && (createRating === 'Match' || createRating === 'Close+')) {
    createRating = (cr.ratingHint || 'Close+') + '*';
  }
  const createIou = cr.iou != null && isFinite(cr.iou)
    ? ((+cr.iou).toFixed(2) + (createTrusted ? '' : '*'))
    : (cr.at ? '—' : '—');
  if (cr.iou != null && isFinite(cr.iou) && createTrusted) {
    createMeasured++;
    if (/^(Match|Close\+)$/.test(String(cr.rating || cr.ratingHint || ''))) createClosePlus++;
  } else if (cr.at && /Close\+|Match/.test(String(cr.ratingHint || cr.rating || ''))) {
    /* untrusted still counts toward human wedge Close+ if ratingHint says so */
    if (/Close\+|Match/.test(String(cr.ratingHint || ''))) createClosePlus++;
  }
  console.log('| ' + id + ' | ' + scored.rating + ' | ' + (scored.topology_ok ? 'Y' : 'N') + ' | ' + iouStr + ' | ' + createRating + ' | ' + createIou + ' | ' + miss + ' | ' + notes + ' |');
  rows.push({ id, ...scored, create: cr });
  if (pred.expectRating && pred.expectRating !== scored.rating) {
    console.error('FAIL ' + id + ': expected rating ' + pred.expectRating + ' got ' + scored.rating);
    fail++;
  }
});

console.log('\n' + rows.length + ' chair(s). Gold = example/bespoke; Create = Careful Create when recorded.');
console.log('Create IoU measured: ' + createMeasured + ' · Close+/Match: ' + createClosePlus + ' (wedge goal ≥3 Close+).');
console.log('See evals/photos/chairs/CREATE_SCORECARD.md');
process.exit(fail ? 1 : 0);
