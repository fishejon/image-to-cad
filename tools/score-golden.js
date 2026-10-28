#!/usr/bin/env node
/* Weekly / CI golden inventory scorer. Compares expected vs actual inventories.
   Usage:
     node tools/score-golden.js
     node tools/score-golden.js --predictions evals/golden/predictions.json
   predictions.json shape: { "<case-id>": { inventory object }, ... }
*/
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const GOLDEN = path.join(ROOT, 'evals', 'golden');

function loadCases() {
  return fs.readdirSync(GOLDEN)
    .filter(f => f.endsWith('.json'))
    .sort()
    .map(f => JSON.parse(fs.readFileSync(path.join(GOLDEN, f), 'utf8')));
}

function aspectErr(a, b) {
  if (!a || !b) return 0;
  const keys = ['w', 'd', 'h'];
  let e = 0;
  keys.forEach(k => {
    const x = +a[k] || 0, y = +b[k] || 0;
    if (x > 0 && y > 0) e = Math.max(e, Math.abs(x - y) / Math.max(x, y));
  });
  return e;
}

function scoreCase(expected, actual) {
  const issues = [];
  if (!actual || typeof actual !== 'object') return { ok: false, issues: ['missing actual inventory'], penalty: 100 };

  const ec = expected.counts || {}, ac = actual.counts || {};
  ['legs', 'drawers', 'doors', 'shelves', 'slats'].forEach(k => {
    if (ec[k] != null && +ec[k] !== +((ac[k] != null ? ac[k] : 0))) {
      issues.push('count ' + k + ': expected ' + ec[k] + ' got ' + (ac[k] != null ? ac[k] : 0));
    }
  });

  const es = expected.structure || {}, as = actual.structure || {};
  if (es.memberContinuity && es.memberContinuity !== 'unknown') {
    if ((as.memberContinuity || 'unknown') !== es.memberContinuity) {
      issues.push('memberContinuity: expected ' + es.memberContinuity + ' got ' + (as.memberContinuity || 'unknown'));
    }
  }
  if (es.dominantSection && es.dominantSection !== 'unknown') {
    if ((as.dominantSection || 'unknown') !== es.dominantSection) {
      issues.push('dominantSection: expected ' + es.dominantSection + ' got ' + (as.dominantSection || 'unknown'));
    }
  }

  const ae = aspectErr(expected.aspect, actual.aspect);
  if (expected.aspect && ae > 0.2) issues.push('aspect err ' + ae.toFixed(2) + ' > 0.20');

  const penalty = issues.length * 20 + (ae > 0.2 ? Math.round(ae * 50) : 0);
  return { ok: issues.length === 0, issues, penalty, aspectErr: ae };
}

function parseArgs(argv) {
  const out = { predictions: null };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--predictions' && argv[i + 1]) { out.predictions = argv[++i]; }
  }
  return out;
}

function main() {
  const args = parseArgs(process.argv);
  let predictions = {};
  if (args.predictions) {
    predictions = JSON.parse(fs.readFileSync(path.resolve(args.predictions), 'utf8'));
  }
  const cases = loadCases();
  let fail = 0;
  console.log('Golden inventory score (' + cases.length + ' cases)\n');
  cases.forEach(c => {
    const actual = (predictions[c.id] && (predictions[c.id].inventory || predictions[c.id])) || c.actual || null;
    const r = scoreCase(c.expected, actual);
    const mark = r.ok ? '✓' : '✗';
    console.log(mark + ' ' + c.id + (r.ok ? '' : ' — ' + r.issues.join('; ')));
    if (!r.ok) fail++;
  });
  console.log('\n' + (cases.length - fail) + '/' + cases.length + ' passed');
  process.exit(fail ? 1 : 0);
}

if (require.main === module) main();
module.exports = { scoreCase, loadCases, aspectErr };
