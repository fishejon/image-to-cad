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
/** Thickness in lumber quarters (always n/4″): 1.75″ → 7/4″, 0.75″ → 3/4″. */
CAD.fmtThick = function (mm) {
  const neg = mm < 0, q = Math.round(Math.abs(+mm || 0) / CAD.MM_PER_IN * 4);
  if (!q) return '0"';
  return (neg ? '−' : '') + q + '/4"';
};
CAD.fmtInch3 = function (arr) { return (arr || []).map(CAD.fmtInch).join(' × '); };
/** Finished blank: thickness in quarters, width & length to 1/16″. */
CAD.fmtBlank = function (T, W, L) { return CAD.fmtThick(T) + ' × ' + CAD.fmtInch(W) + ' × ' + CAD.fmtInch(L); };
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
    const fmt = /^thick$/i.test(word) ? CAD.fmtThick : CAD.fmtInch;
    return pre + fmt(+a) + ' ' + word;
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
  return { kind: 'hardwood', stock: (ht ? ht.nom : CAD.fmtInch(Math.min(T, W))) + ' × ≥' + CAD.fmtInch(face).replace(/"$/, '') + '"', T: ht ? ht.t : Math.min(T, W) / CAD.MM_PER_IN, W: face, L: L / CAD.MM_PER_IN, note: 'hardwood / random width' };
};

const BOARD_LENS = [96, 120, 144]; /* 8′, 10′, 12′ */
const KERF = 1 / 8;
const fmtFt = in_ => { const f = Math.round(in_ / 12); return f + '′'; };
const roundUpBoard = used => {
  for (let i = 0; i < BOARD_LENS.length; i++) if (used <= BOARD_LENS[i] + 1e-6) return BOARD_LENS[i];
  return Math.ceil(used / 12) * 12;
};

/** First-fit decreasing: pack cut lengths (inches) onto boards, then round each board up to 8′/10′/12′. */
function packBoards(cuts) {
  const items = cuts.slice().sort((a, b) => b.len - a.len);
  const bins = [];
  items.forEach(it => {
    let placed = false;
    for (let i = 0; i < bins.length; i++) {
      const need = it.len + (bins[i].cuts.length ? KERF : 0);
      if (bins[i].used + need <= 144 + 1e-6) { bins[i].cuts.push(it); bins[i].used += need; placed = true; break; }
    }
    if (!placed) bins.push({ cuts: [it], used: it.len });
  });
  return bins.map((b, i) => {
    const bought = roundUpBoard(b.used);
    return { n: i + 1, usedIn: b.used, buyIn: bought, buy: fmtFt(bought), cuts: b.cuts };
  });
}

function expandBlanks(M) {
  const out = [];
  CAD.cutList(M).forEach(r => {
    const st = CAD.stockForPart(r.T, r.W, r.L, r.mat);
    for (let q = 0; q < r.qty; q++) {
      out.push({
        id: r.id, name: r.name, mat: r.mat, grp: r.grp,
        T: r.T, W: r.W, L: r.L,
        finished: CAD.fmtBlank(r.T, r.W, r.L),
        stock: st.stock, kind: st.kind, note: st.note,
        stockT: st.T, stockW: st.W, len: st.L
      });
    }
  });
  return out;
}

/**
 * Optimized buy plan: nest blanks onto shared boards of the same stock.
 * Returns { boards: [...], summary: [...], blanks: [...] }.
 * Each board has a cut list of the parts taken from it.
 */
CAD.lumberPlan = function (M) {
  const blanks = expandBlanks(M), groups = {};
  blanks.forEach(b => {
    const key = b.kind + '|' + b.stock + '|' + (b.mat || '');
    if (!groups[key]) groups[key] = { kind: b.kind, stock: b.stock, mat: b.mat, note: b.note, blanks: [] };
    groups[key].blanks.push(b);
  });
  const boards = [];
  Object.values(groups).forEach(g => {
    if (g.kind === 'sheet') {
      /* Pack onto 4×8 sheets by area (simple strip along long edge). */
      const sheetL = 96, sheetW = 48, strips = [];
      g.blanks.slice().sort((a, b) => Math.max(b.L, b.W) - Math.max(a.L, a.W)).forEach(b => {
        const pl = Math.max(b.len, b.stockW), pw = Math.min(b.len, b.stockW) || b.stockW;
        let placed = false;
        for (let i = 0; i < strips.length; i++) {
          if (strips[i].w + 1e-6 >= pw && strips[i].used + pl + KERF <= sheetL + 1e-6) {
            strips[i].cuts.push(Object.assign({ len: pl }, b)); strips[i].used += pl + KERF; placed = true; break;
          }
        }
        if (!placed) {
          if (pl <= sheetL + 1e-6 && pw <= sheetW + 1e-6) strips.push({ w: pw, used: pl, cuts: [Object.assign({ len: pl }, b)] });
          else strips.push({ w: pw, used: pl, cuts: [Object.assign({ len: pl }, b)], over: true });
        }
      });
      strips.forEach((s, i) => {
        boards.push({
          id: boards.length + 1, kind: g.kind, stock: g.stock, mat: g.mat, note: g.note,
          buy: s.over ? 'oversize — special order' : '4×8 sheet',
          buyIn: sheetL, usedIn: s.used, label: g.stock + ' · sheet ' + (i + 1),
          cuts: s.cuts.map(c => ({ name: c.name, id: c.id, finished: c.finished, len: CAD.fmtInch(c.len * CAD.MM_PER_IN), lenIn: c.len }))
        });
      });
      return;
    }
    const packed = packBoards(g.blanks.map(b => Object.assign({ len: b.len }, b)));
    packed.forEach(p => {
      boards.push({
        id: boards.length + 1, kind: g.kind, stock: g.stock, mat: g.mat, note: g.note,
        buy: p.buy, buyIn: p.buyIn, usedIn: p.usedIn,
        label: g.stock + ' × ' + p.buy,
        cuts: p.cuts.map(c => ({ name: c.name, id: c.id, finished: c.finished, len: CAD.fmtInch(c.len * CAD.MM_PER_IN), lenIn: c.len }))
      });
    });
  });
  boards.sort((a, b) => a.stock.localeCompare(b.stock) || a.id - b.id);
  const summaryMap = {};
  boards.forEach(b => {
    const key = b.kind + '|' + b.stock + '|' + b.buy + '|' + (b.mat || '');
    if (!summaryMap[key]) summaryMap[key] = { kind: b.kind, stock: b.stock, mat: b.mat, buy: b.buy, qty: 0, boards: [], pieces: 0, note: b.note };
    summaryMap[key].qty++; summaryMap[key].boards.push(b); summaryMap[key].pieces += b.cuts.length;
  });
  const summary = Object.values(summaryMap).map(s => Object.assign(s, {
    label: s.qty + '× ' + s.stock + (s.buy.indexOf('sheet') >= 0 ? '' : ' × ' + s.buy),
    buyLine: s.qty + ' ' + (s.qty === 1 ? 'pc' : 'pcs') + ' · ' + s.stock + (s.buy.indexOf('sheet') >= 0 || s.buy.indexOf('oversize') >= 0 ? ' (' + s.buy + ')' : ' × ' + s.buy)
  })).sort((a, b) => a.stock.localeCompare(b.stock));
  return { boards, summary, blanks };
};

/** Back-compat aggregate list (one row per stock type). */
CAD.lumberList = function (M) {
  const plan = CAD.lumberPlan(M);
  return plan.summary.map(s => ({
    kind: s.kind, stock: s.stock, mat: s.mat, note: s.note || '',
    pieces: s.pieces, buy: s.buyLine, buyFeet: s.qty, boards: s.boards, parts: s.boards.flatMap(b => b.cuts)
  }));
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
