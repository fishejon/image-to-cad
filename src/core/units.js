/* Display units: the engine stays in millimetres; everything shown to a person is inches (1/16") and pounds. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
CAD.MM_PER_IN = 25.4;
CAD.LB_PER_KG = 2.2046226218;
CAD.toSixteenth = function (mm) { return Math.round((+mm || 0) / CAD.MM_PER_IN * 16); };
CAD.fmtInch = function (mm) {
  const neg = mm < 0, n = Math.abs(CAD.toSixteenth(mm));
  let whole = Math.floor(n / 16), frac = n % 16, a = frac, b = 16;
  while (b) { const t = a % b; a = b; b = t; }
  let s = '';
  if (whole) s += whole;
  if (frac) s += (s ? ' ' : '') + (frac / a) + '/' + (16 / a);
  if (!s) s = '0';
  return (neg ? '−' : '') + s + '"';
};
CAD.fmtInch3 = function (arr) { return (arr || []).map(CAD.fmtInch).join(' × '); };
CAD.fmtLb = function (kg, d) {
  const n = (+kg || 0) * CAD.LB_PER_KG;
  return n.toLocaleString('en-US', { maximumFractionDigits: d === undefined ? 1 : d, minimumFractionDigits: d === undefined ? 1 : d }) + ' lb';
};
/* Rewrite millimetre amounts in free text (cut-list notes, part specs, guide labels) as inch fractions.
   Also catches bare "18 × 8" / "6 wide" style labels that omit the "mm" suffix. */
CAD.inchifyText = function (s) {
  if (s == null || s === '') return '';
  let t = String(s);
  const num = '(\\d+(?:\\.\\d+)?)';
  const bareOk = (n) => { const v = +n; return v >= 2 && v <= 5000 && !/\//.test(n); };
  t = t.replace(new RegExp(num + '\\s*[×x]\\s*' + num + '\\s*[×x]\\s*' + num + '\\s*mm\\b', 'gi'), (_, a, b, c) => CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b) + ' × ' + CAD.fmtInch(+c));
  t = t.replace(new RegExp(num + '\\s*[×x]\\s*' + num + '\\s*mm\\b', 'gi'), (_, a, b) => CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b));
  t = t.replace(new RegExp(num + '\\s*mm\\b', 'gi'), (_, a) => CAD.fmtInch(+a));
  t = t.replace(new RegExp('(^|[^\\d/"′″])' + num + '\\s*[×x]\\s*' + num + '\\s*[×x]\\s*' + num + '(?!\\s*["″]|\\s*/)', 'g'), (m, pre, a, b, c) => {
    if (!bareOk(a) || !bareOk(b) || !bareOk(c)) return m;
    return pre + CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b) + ' × ' + CAD.fmtInch(+c);
  });
  t = t.replace(new RegExp('(^|[^\\d/"′″])' + num + '\\s*[×x]\\s*' + num + '(?!\\s*["″]|\\s*/|\\s*mm)', 'g'), (m, pre, a, b) => {
    if (!bareOk(a) || !bareOk(b)) return m;
    return pre + CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b);
  });
  t = t.replace(new RegExp('(^|[^\\d/"′″])' + num + '\\s*(wide|thick|deep|tall|long)\\b', 'gi'), (m, pre, a, word) => {
    if (!bareOk(a)) return m;
    return pre + CAD.fmtInch(+a) + ' ' + word;
  });
  return t;
};

/* Softwood dimensional lumber — nominal name → actual dressed size (inches). */
CAD.DIM_LUMBER = [
  { nom: '1×2', t: .75, w: 1.5 }, { nom: '1×3', t: .75, w: 2.5 }, { nom: '1×4', t: .75, w: 3.5 },
  { nom: '1×6', t: .75, w: 5.5 }, { nom: '1×8', t: .75, w: 7.25 }, { nom: '1×10', t: .75, w: 9.25 }, { nom: '1×12', t: .75, w: 11.25 },
  { nom: '2×2', t: 1.5, w: 1.5 }, { nom: '2×3', t: 1.5, w: 2.5 }, { nom: '2×4', t: 1.5, w: 3.5 },
  { nom: '2×6', t: 1.5, w: 5.5 }, { nom: '2×8', t: 1.5, w: 7.25 }, { nom: '2×10', t: 1.5, w: 9.25 }, { nom: '2×12', t: 1.5, w: 11.25 },
  { nom: '4×4', t: 3.5, w: 3.5 }
];
/* Hardwood thickness (quarter system), actual after surfacing. Width is random — we report board feet / total length. */
CAD.HARDWOOD_THICK = [
  { nom: '4/4', t: 13 / 16 }, { nom: '5/4', t: 1 + 1 / 16 }, { nom: '6/4', t: 1 + 5 / 16 }, { nom: '8/4', t: 1.75 }
];
CAD.SHEET_STOCK = [
  { nom: '¼″ ply', t: .25 }, { nom: '⅜″ ply', t: .375 }, { nom: '½″ ply', t: .5 },
  { nom: '⅝″ ply', t: .625 }, { nom: '¾″ ply', t: .75 }
];

function fitStock(Tmm, Wmm, catalog) {
  const Ti = Tmm / CAD.MM_PER_IN, Wi = Wmm / CAD.MM_PER_IN, pad = 1 / 16;
  let best = null;
  catalog.forEach(s => {
    const ok = (s.t + 1e-6 >= Ti - pad && s.w + 1e-6 >= Wi - pad);
    const okSwap = (s.t + 1e-6 >= Wi - pad && s.w + 1e-6 >= Ti - pad);
    if (!ok && !okSwap) return;
    const waste = ok ? (s.t * s.w - Ti * Wi) : (s.t * s.w - Wi * Ti);
    if (!best || waste < best.waste - 1e-9 || (Math.abs(waste - best.waste) < 1e-9 && s.t * s.w < best.area))
      best = { nom: s.nom, t: s.t, w: s.w, waste, area: s.t * s.w, swapped: !ok && okSwap };
  });
  return best;
}
function fitThickness(Tmm, list) {
  const Ti = Tmm / CAD.MM_PER_IN, pad = 1 / 16;
  let best = null;
  list.forEach(s => {
    if (s.t + 1e-6 < Ti - pad) return;
    const over = s.t - Ti;
    if (!best || over < best.over - 1e-9) best = { nom: s.nom, t: s.t, over };
  });
  return best;
}
/** Pick buy-stock for one finished blank (T×W×L mm). */
CAD.stockForPart = function (T, W, L, matName) {
  const name = String(matName || '').toLowerCase();
  const isSheet = /ply|veneer|mdf|osb|sheet|marble|stone|steel|aluminium|aluminum|glass/.test(name);
  const isHard = /walnut|oak|maple|cherry|ash|mahogany|teak|birch|cedar|wood|pine/.test(name) || !isSheet;
  if (isSheet) {
    const th = fitThickness(T, CAD.SHEET_STOCK) || fitThickness(T, CAD.HARDWOOD_THICK);
    return { kind: 'sheet', stock: th ? th.nom : CAD.fmtInch(T) + ' sheet', T: th ? th.t : T / CAD.MM_PER_IN, W: W / CAD.MM_PER_IN, L: L / CAD.MM_PER_IN, note: 'sheet good' };
  }
  const soft = fitStock(T, W, CAD.DIM_LUMBER);
  if (soft && soft.waste < 2.5) {
    return { kind: 'dim', stock: soft.nom, T: soft.t, W: soft.w, L: L / CAD.MM_PER_IN, note: soft.swapped ? 'rotate blank' : '' };
  }
  const ht = fitThickness(Math.min(T, W), CAD.HARDWOOD_THICK);
  const face = Math.max(T, W) / CAD.MM_PER_IN;
  return { kind: 'hardwood', stock: (ht ? ht.nom : CAD.fmtInch(Math.min(T, W))) + ' × ~' + CAD.fmtInch(face).replace(/"$/, '') + '"+', T: ht ? ht.t : Math.min(T, W) / CAD.MM_PER_IN, W: face, L: L / CAD.MM_PER_IN, note: 'hardwood / random width' };
};

/** Aggregate shopping list: dimensional lumber + hardwood + sheet. Lengths include ~15% waste, rounded up to the next foot. */
CAD.lumberList = function (M) {
  const rows = CAD.cutList(M), bags = {};
  rows.forEach(r => {
    const st = CAD.stockForPart(r.T, r.W, r.L, r.mat);
    const key = st.kind + '|' + st.stock + '|' + (r.mat || '');
    if (!bags[key]) bags[key] = { kind: st.kind, stock: st.stock, mat: r.mat, note: st.note, inches: 0, pieces: 0, parts: [] };
    bags[key].inches += st.L * r.qty;
    bags[key].pieces += r.qty;
    bags[key].parts.push({ name: r.name, qty: r.qty, finished: CAD.fmtInch3([r.T, r.W, r.L]) });
  });
  return Object.values(bags).map(b => {
    const withWaste = b.inches * 1.15;
    const feet = Math.max(1, Math.ceil(withWaste / 12));
    return Object.assign(b, {
      lengthIn: withWaste,
      buy: b.kind === 'sheet' ? (feet <= 8 ? 'one ~4×8 sheet (cut list below)' : feet + ' linear ft of sheet stock') : feet + ' ft',
      buyFeet: feet
    });
  }).sort((a, b) => a.kind.localeCompare(b.kind) || a.stock.localeCompare(b.stock));
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
