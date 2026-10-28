/* joinery.js — mating pairs from labeled features + shop-ready guide copy (category-agnostic). */
(function (root) {
'use strict';
const CAD = root.CAD;
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
if (!CAD.sanitizeHTML) CAD.sanitizeHTML = s => esc(s).replace(/&lt;(\/?)(b|i|br)\s*\/?&gt;/gi, '<$1$2>');
const clean = t => CAD.sanitizeHTML(t);
const inch = t => CAD.inchifyText ? CAD.inchifyText(t) : String(t == null ? '' : t);
const sizeOf = box => {
  if (!box || box.length < 6) return '';
  const dx = Math.abs(box[3] - box[0]), dy = Math.abs(box[4] - box[1]), dz = Math.abs(box[5] - box[2]);
  const dims = [dx, dy, dz].sort((a, b) => b - a);
  return CAD.fmtInch3 ? CAD.fmtInch3(dims) : dims.map(d => Math.round(d)).join(' × ') + ' mm';
};

/** Canonical joinery methods for classify, chips, and revise prompts. */
CAD.JOINT_METHODS = [
  { id: 'mortise_and_tenon', label: 'Mortise & tenon', group: 'casework', interlocking: false },
  { id: 'bridal', label: 'Bridle / open mortise', group: 'casework', interlocking: false },
  { id: 'half_lap', label: 'Half-lap', group: 'casework', interlocking: false },
  { id: 'dado', label: 'Dado / housing', group: 'casework', interlocking: false },
  { id: 'rabbet', label: 'Rabbet', group: 'casework', interlocking: false },
  { id: 'groove', label: 'Groove / panel', group: 'casework', interlocking: false },
  { id: 'tongue', label: 'Tongue & groove', group: 'casework', interlocking: false },
  { id: 'dowel', label: 'Dowel / peg', group: 'casework', interlocking: false },
  { id: 'spline', label: 'Spline / biscuit', group: 'casework', interlocking: false },
  { id: 'mitre', label: 'Mitre', group: 'casework', interlocking: false },
  { id: 'dovetail', label: 'Dovetail', group: 'interlock', interlocking: true },
  { id: 'box_joint', label: 'Box / finger joint', group: 'interlock', interlocking: true },
  { id: 'finger_lap', label: 'Finger / comb lap', group: 'interlock', interlocking: true },
  { id: 'scarf', label: 'Scarf / kama-tsugi', group: 'interlock', interlocking: true },
  { id: 'wedge_tenon', label: 'Wedged / keyed tenon', group: 'interlock', interlocking: true },
  { id: 'housings_with_shoulders', label: 'Stopped housing', group: 'interlock', interlocking: false },
  { id: 'fastener', label: 'Screw / hardware', group: 'casework', interlocking: false },
  { id: 'glue_only', label: 'Glue-only butt', group: 'casework', interlocking: false }
];
CAD.jointMethodInfo = function (id) {
  return CAD.JOINT_METHODS.find(m => m.id === id) || null;
};
/** Classify a joint from tag/label text. */
CAD.classifyJoint = function (label, tag, kind) {
  const s = (String(label || '') + ' ' + String(tag || '') + ' ' + String(kind || '')).toLowerCase();
  if (/dove.?tail|ari.?kumi|half.?blind.?dove/.test(s)) return 'dovetail';
  if (/box.?joint|finger.?joint/.test(s)) return 'box_joint';
  if (/finger.?lap|comb.?lap|comb.?joint/.test(s)) return 'finger_lap';
  if (/scarf|kama.?tsugi|kane.?tsugi/.test(s)) return 'scarf';
  if (/shachi|wedge.?tenon|keyed.?tenon|fox.?wedge|draw.?wedge/.test(s)) return 'wedge_tenon';
  if (/bridle|open.?mortise/.test(s)) return 'bridal';
  if (/half.?lap|halving/.test(s)) return 'half_lap';
  if (/stopped.?housing|housing.?with.?shoulder/.test(s)) return 'housings_with_shoulders';
  if (/mortise|tenon/.test(s)) return 'mortise_and_tenon';
  if (/dado|housing/.test(s)) return 'dado';
  if (/rabbet|rebate/.test(s)) return 'rabbet';
  if (/groove|panel.?groove|floating.?panel/.test(s)) return 'groove';
  if (/spline|biscuit/.test(s)) return 'spline';
  if (/dowel|peg|draw.?bor/.test(s)) return 'dowel';
  if (/tongue/.test(s)) return 'tongue';
  if (/finger|comb/.test(s)) return 'box_joint';
  if (/mitre|miter/.test(s)) return 'mitre';
  if (/screw|bolt|hardware/.test(s)) return 'fastener';
  if (/glue.?only|butt.?joint|glue.?butt/.test(s)) return 'glue_only';
  if (kind === 'cut') return 'pocket';
  if (kind === 'add') return 'projection';
  return 'joint';
};

CAD.jointMethodLabel = function (method) {
  const known = CAD.jointMethodInfo(method);
  if (known) return known.label;
  return ({
    pocket: 'Cut pocket',
    projection: 'Standing tenon / tongue',
    joint: 'Joinery'
  })[method] || 'Joinery';
};

CAD.jointInterlockingHint = function (method) {
  const info = CAD.jointMethodInfo(method);
  if (!info || !info.interlocking) return '';
  if (method === 'dovetail') return 'Model mating pins and tails as labeled cut/add features with fill:true (exact mating voids/projections), not magic butts.';
  if (method === 'box_joint' || method === 'finger_lap') return 'Model interlocking fingers as paired cut/add features with fill:true on receiving cuts.';
  if (method === 'scarf') return 'Model the scarf faces (and any keys/wedges) as labeled mating cut/add geometry with fill where appropriate.';
  if (method === 'wedge_tenon') return 'Model the tenon, mortise, and wedge/key as labeled features; fill:true on the receiving mortise.';
  return 'Model interlocking members as exact mating cut/add features with tag+label and fill:true — not unlabeled contact.';
};

/** Prefill sentence for revise when user picks a joinery chip. */
CAD.reviseJointPrompt = function (target, requestedMethod) {
  const req = CAD.jointMethodInfo(requestedMethod) || { id: requestedMethod, label: CAD.jointMethodLabel(requestedMethod) };
  const a = (target && (target.cutName || target.aName || target.cutId || target.a)) || 'part A';
  const b = (target && (target.addName || target.bName || target.addId || target.b)) || 'part B';
  const cur = target && target.method ? CAD.jointMethodLabel(target.method) : 'the current joint';
  const hint = CAD.jointInterlockingHint(req.id);
  let s = 'Change the joint between "' + a + '" and "' + b + '" from ' + cur + ' to ' + req.label +
    ' (method id: ' + req.id + '). Keep overall sizes. Update both mating features (tag+label; fill:true on receiving cuts). Prefer Quality Careful if the joint is interlocking.';
  if (hint) s += ' ' + hint;
  return s;
};

/**
 * Mating joints: fill:true cuts paired with the part(s) that occupy them.
 * Falls back to tag-matched add features when fill geometry is sparse.
 */
CAD.matingJoints = function (M) {
  if (!M || !M.defs) return [];
  const out = [], seen = new Set();
  const push = j => {
    const key = [j.cutId, j.cutTag || '', j.addId, j.addTag || '', j.label || ''].join('|');
    if (seen.has(key)) return;
    seen.add(key);
    out.push(j);
  };
  const fills = typeof CAD.jointFill === 'function' ? CAD.jointFill(M) : [];
  fills.forEach(row => {
    if (!(row.ratio > 0.45)) return;
    const cutId = String(row.part || '').split('#')[0];
    const cutDef = M.defs.get(cutId);
    if (!cutDef) return;
    const cutFeat = (cutDef.solid.feat || []).find(f => f.kind === 'cut' && f.tag === row.tag) ||
      (cutDef.solid.feat || []).find(f => f.kind === 'cut' && f.fill);
    const mates = row.by ? String(row.by).split('+').filter(Boolean) : [];
    mates.forEach(addId => {
      const addDef = M.defs.get(addId);
      if (!addDef) return;
      const addFeat = (addDef.solid.feat || []).find(f => f.kind === 'add' && (f.tag === row.tag || (cutFeat && f.tag === cutFeat.tag))) ||
        (addDef.solid.feat || []).find(f => f.kind === 'add' && f.label);
      const label = (cutFeat && cutFeat.label) || (addFeat && addFeat.label) || row.tag || 'Joint';
      const method = CAD.classifyJoint(label, row.tag || (cutFeat && cutFeat.tag), 'cut');
      push({
        cutId, addId,
        cutName: cutDef.name || cutId,
        addName: addDef.name || addId,
        cutTag: cutFeat ? cutFeat.tag : row.tag,
        addTag: addFeat ? addFeat.tag : null,
        label, method,
        size: sizeOf(cutFeat && cutFeat.box),
        fillRatio: row.ratio,
        cutFeat, addFeat
      });
    });
  });
  /* Tag-matched pairs not caught by fill (e.g. labeled but fill false) */
  const cuts = [], adds = [];
  M.defs.forEach(d => {
    (d.solid.feat || []).forEach(f => {
      if (!f.label && !f.tag) return;
      if (f.kind === 'cut') cuts.push({ def: d, f });
      else if (f.kind === 'add') adds.push({ def: d, f });
    });
  });
  cuts.forEach(c => {
    adds.forEach(a => {
      if (c.def.id === a.def.id) return;
      const sameTag = c.f.tag && a.f.tag && c.f.tag === a.f.tag;
      const labClose = c.f.label && a.f.label && String(c.f.label).replace(/\s+/g, '').toLowerCase() === String(a.f.label).replace(/\s+/g, '').toLowerCase();
      if (!sameTag && !labClose) return;
      const label = c.f.label || a.f.label || c.f.tag;
      push({
        cutId: c.def.id, addId: a.def.id,
        cutName: c.def.name || c.def.id, addName: a.def.name || a.def.id,
        cutTag: c.f.tag, addTag: a.f.tag,
        label, method: CAD.classifyJoint(label, c.f.tag, 'cut'),
        size: sizeOf(c.f.box), fillRatio: null,
        cutFeat: c.f, addFeat: a.f
      });
    });
  });
  return out;
};

const boxCenter = b => [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2];
const distPointBox = (p, b) => {
  const dx = Math.max(b[0] - p[0], 0, p[0] - b[3]);
  const dy = Math.max(b[1] - p[1], 0, p[1] - b[4]);
  const dz = Math.max(b[2] - p[2], 0, p[2] - b[5]);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
};
const pointInPad = (p, b, g) => p[0] >= b[0] - g && p[0] <= b[3] + g && p[1] >= b[1] - g && p[1] <= b[4] + g && p[2] >= b[2] - g && p[2] <= b[5] + g;

/**
 * Joints / unlabeled contacts near a world-space point (mm).
 * Returns sorted list of target descriptors: { kind, dist, ... }.
 */
CAD.jointsNearPoint = function (M, worldPoint, radiusMm) {
  radiusMm = radiusMm == null ? 12 : radiusMm;
  if (!M || !worldPoint) return [];
  const p = Array.isArray(worldPoint) ? worldPoint : [worldPoint.x, worldPoint.y, worldPoint.z];
  const hits = [];
  const firstInst = id => {
    for (let i = 0; i < M.insts.length; i++) if (M.insts[i].def === id) return M.insts[i];
    return null;
  };
  CAD.matingJoints(M).forEach(j => {
    let best = Infinity, cutWorld = null, addWorld = null;
    const ic = firstInst(j.cutId), ia = firstInst(j.addId);
    if (ic && j.cutFeat && j.cutFeat.box) {
      cutWorld = CAD.xfBoxes([j.cutFeat.box], ic.m)[0];
      best = Math.min(best, distPointBox(p, cutWorld));
    }
    if (ia && j.addFeat && j.addFeat.box) {
      addWorld = CAD.xfBoxes([j.addFeat.box], ia.m)[0];
      best = Math.min(best, distPointBox(p, addWorld));
    }
    if (!(best <= radiusMm)) return;
    hits.push(Object.assign({}, j, {
      kind: 'joint',
      dist: best,
      cutWorld, addWorld,
      center: cutWorld ? boxCenter(cutWorld) : (addWorld ? boxCenter(addWorld) : p.slice())
    }));
  });
  if (typeof CAD.unlabeledContacts === 'function') {
    const contacts = CAD.unlabeledContacts(M, Math.max(2, radiusMm));
    contacts.forEach(c => {
      const ia = firstInst(c.a), ib = firstInst(c.b);
      if (!ia || !ib) return;
      CAD.instBoxes(M, ia); CAD.instBoxes(M, ib);
      const nearA = pointInPad(p, ia._ab, radiusMm), nearB = pointInPad(p, ib._ab, radiusMm);
      if (!nearA && !nearB) return;
      /* Prefer points in the padded overlap of both AABBs */
      const pad = g => [Math.max(ia._ab[0], ib._ab[0]) - g, Math.max(ia._ab[1], ib._ab[1]) - g, Math.max(ia._ab[2], ib._ab[2]) - g,
        Math.min(ia._ab[3], ib._ab[3]) + g, Math.min(ia._ab[4], ib._ab[4]) + g, Math.min(ia._ab[5], ib._ab[5]) + g];
      const ov = pad(radiusMm);
      if (ov[0] > ov[3] || ov[1] > ov[4] || ov[2] > ov[5]) return;
      const dist = distPointBox(p, ov);
      if (dist > radiusMm) return;
      const da = M.defs.get(c.a), db = M.defs.get(c.b);
      hits.push({
        kind: 'contact', dist, method: 'glue_only', label: 'Unlabeled contact',
        cutId: c.a, addId: c.b,
        cutName: (da && da.name) || c.a, addName: (db && db.name) || c.b,
        a: c.a, b: c.b, aName: (da && da.name) || c.a, bName: (db && db.name) || c.b,
        center: boxCenter(ov), cutWorld: ia._ab.slice(), addWorld: ib._ab.slice()
      });
    });
  }
  hits.sort((a, b) => a.dist - b.dist);
  return hits;
};

/** Best single target near a point, or null. */
CAD.resolveJointTarget = function (M, worldPoint, radiusMm) {
  const hits = CAD.jointsNearPoint(M, worldPoint, radiusMm);
  return hits.length ? hits[0] : null;
};

/** Shop-ready bullets for one mating joint. */
CAD.joineryHowTo = function (j) {
  const method = j.method || CAD.classifyJoint(j.label, j.cutTag, 'cut');
  const lab = inch(j.label || 'joint');
  const size = j.size ? ' (' + j.size + ')' : '';
  const cut = esc(inch(j.cutName || j.cutId));
  const add = esc(inch(j.addName || j.addId));
  const title = CAD.jointMethodLabel(method) + ': ' + add + ' → ' + cut;
  const text = [];
  const tools = ['Marking knife', 'Square', 'Chisels', 'Saw'];
  let tip = 'Cut a scrap test of this joint before touching the finished blanks.';
  let chk = 'Dry-fit ' + add + ' into ' + cut + ' — snug hand pressure, no gaps at the shoulders.';

  if (method === 'mortise_and_tenon') {
    text.push('On <b>' + cut + '</b>, lay out the mortise from <b>' + esc(lab) + '</b>' + size + '. Knife the perimeter; keep the wall thicknesses equal on both cheeks.');
    text.push('Drill out most of the waste, then chop and pare to the knife lines. Walls must be flat and square to the face.');
    text.push('On <b>' + add + '</b>, mark the matching tenon. Saw the cheeks and shoulders; pare until it enters the mortise with light hand pressure.');
    text.push('Mark the pair together. Glue on the long-grain cheeks only; clamp across the joint until set.');
    tools.push('Mortise gauge', 'Brad-point bit', 'Mallet');
    tip = 'Leave the tenon a hair proud of the mortise depth so it seats fully without bottoming on glue.';
    chk = 'Shoulders sit tight all around; the assembly stays square when dry-clamped.';
  } else if (method === 'dado') {
    text.push('On <b>' + cut + '</b>, lay out the dado from <b>' + esc(lab) + '</b>' + size + '. Score both shoulders with a knife.');
    text.push('Saw or router the waste between the lines; pare the floor flat so the mating blank sits fully.');
    text.push('Fit <b>' + add + '</b> into the dado. The blank thickness should match the dado width — trim the blank or deepen the dado, never force it.');
    text.push('Glue the dado floor and cheeks; clamp until set. Check the shelf/panel is square to the side.');
    tools.push('Router or dado stack', 'Shoulder plane');
  } else if (method === 'rabbet') {
    text.push('On <b>' + cut + '</b>, cut the rabbet <b>' + esc(lab) + '</b>' + size + ' along the marked edge.');
    text.push('Seat <b>' + add + '</b> fully into the rabbet so the faces flush where the design requires.');
    text.push('Glue the long-grain meeting faces; clamp without tipping the thin lip.');
    tools.push('Rabbet plane or router');
  } else if (method === 'groove') {
    text.push('On <b>' + cut + '</b>, plough the groove <b>' + esc(lab) + '</b>' + size + '. Keep depth consistent end to end.');
    text.push('Fit <b>' + add + '</b> so it floats or seats as designed — leave seasonal play for panels across the grain.');
    text.push('Glue only where the design calls for a fixed edge; otherwise leave the panel free in the groove.');
    tools.push('Plough plane or router');
    tip = 'For floating panels, glue only the centre of one end so the panel can move.';
  } else if (method === 'tongue') {
    text.push('Cut the tongue on <b>' + add + '</b> to <b>' + esc(lab) + '</b>' + size + ', then fit it into the mating groove/dado on <b>' + cut + '</b>.');
    text.push('Pare until the shoulders seat flush. Glue the tongue cheeks; clamp across the joint.');
  } else if (method === 'dowel') {
    text.push('Mark matching dowel centres on <b>' + cut + '</b> and <b>' + add + '</b> from <b>' + esc(lab) + '</b>.');
    text.push('Drill to depth with a stop. Dry-fit with dowels, then glue and clamp.');
    tools.push('Dowelling jig', 'Brad-point bit');
  } else if (method === 'mitre') {
    text.push('Cut matching mitres on <b>' + cut + '</b> and <b>' + add + '</b> at the angle in <b>' + esc(lab) + '</b>.');
    text.push('Dry-fit for a closed seam; reinforce with splines, biscuits, or glue blocks if the joint is structural.');
    tools.push('Mitre saw or shooting board');
  } else {
    text.push('Join <b>' + add + '</b> to <b>' + cut + '</b> at <b>' + esc(lab) + '</b>' + size + '.');
    text.push('Remove waste on the receiving part (orange), leave the mating projection (green), and pare to a snug dry fit before glue.');
    text.push('Glue the long-grain meeting faces; clamp square until set.');
  }
  return { title, method, text: text.map(clean), tools: tools.map(t => esc(inch(t))), tip: clean(tip), chk: clean(chk) };
};

/** Short assembly hint for a set of part ids involved in a step. */
CAD.asmJoineryHint = function (M, partIds) {
  const set = new Set(partIds || []);
  const joints = CAD.matingJoints(M).filter(j => set.has(j.cutId) || set.has(j.addId));
  if (!joints.length) return null;
  const lines = joints.slice(0, 4).map(j => {
    const how = CAD.joineryHowTo(j);
    return 'Join <b>' + esc(inch(j.addName)) + '</b> into <b>' + esc(inch(j.cutName)) + '</b> — ' + CAD.jointMethodLabel(j.method) +
      (j.label ? ' (<b>' + esc(inch(j.label)) + '</b>)' : '') + '. Dry-fit, glue long-grain faces, clamp square.';
  });
  return { text: lines.map(clean), joints };
};

/**
 * Auto-generated build-guide plan (pages). Hand-authored M.spec.guide still wins in guide.js.
 */
CAD.buildGuidePlan = function (M) {
  const S = [], add = o => { o.n = S.length + 1; S.push(o); return o; };
  const E = s => esc(inch(s));
  const defs = [...M.defs.values()];
  const joints = CAD.matingJoints(M);
  const unlabeled = typeof CAD.unlabeledContacts === 'function' ? CAD.unlabeledContacts(M) : [];

  add({
    kind: 'hero', phase: 'Welcome', title: E(M.meta.name),
    text: [].concat(
      M.meta.description ? [E(M.meta.description)] : [],
      ['Finished size <b>' + (CAD.fmtInch3 ? CAD.fmtInch3(M.size) : E(M.size.join('×'))) + '</b>: ' + defs.length + ' part types, ' + M.insts.length + ' pieces.',
        'How to read the pictures: <b>orange parts</b> are new in this step; <b>orange boxes</b> are material to remove; <b>green boxes</b> are tenons and tongues you leave standing.',
        joints.length
          ? 'This guide has <b>' + joints.length + ' labeled joint' + (joints.length === 1 ? '' : 's') + '</b>. Each joinery page shows the mating pair and how to cut and assemble it.'
          : 'Labeled joinery is missing on some meetings — add tag+label (and fill:true on cuts) in the Spec so the guide can show real joints.'],
      (M.meta.assumptions || []).slice(0, 2).map(a => 'Assumed: ' + E(a))
    ),
    tools: [], tip: 'Dry-fit every joint before gluing.'
  });
  add({
    kind: 'flat', phase: 'Welcome', title: 'Parts overview',
    text: ['<b>' + defs.length + ' part types, ' + M.insts.length + ' pieces.</b> Each tile shows the part name and quantity.',
      'Part names match the cut list. Joinery sizes on later pages are pocket/tenon sizes, not the overall blank.'],
    tools: [], tip: 'Label every part with its name and an orientation arrow as soon as you make it.'
  });
  add({ kind: 'cutlist', phase: 'Prepare', title: 'Cut list & milling', text: [] });

  if (unlabeled.length) {
    add({
      kind: 'text', phase: 'Prepare', title: 'Unlabeled contacts — fix before cutting',
      text: [
        'These parts nearly touch without tagged joinery. The model may be holding itself with magic butt joints — do not trust glue-only contact for structure.',
        unlabeled.slice(0, 10).map(u => '<b>' + E(u.a) + '</b> ↔ <b>' + E(u.b) + '</b>').join('<br>'),
        'In the Spec tab, add a cut with fill:true and a mating add (tag+label) for each pair, or merge continuous members into one part. Then reopen the guide.'
      ].map(clean),
      tools: []
    });
  }

  const covered = new Set();
  joints.slice(0, 14).forEach(j => {
    const how = CAD.joineryHowTo(j);
    covered.add(j.cutId); covered.add(j.addId);
    const tags = [j.cutTag, j.addTag].filter(Boolean);
    add({
      kind: 'subset',
      phase: 'Joinery',
      title: how.title,
      show: [
        { def: j.cutId, idx: 1, ex: [-90, 40, 20] },
        { def: j.addId, idx: 1, ex: [90, -40, -10] }
      ],
      tags,
      dir: [.85, -.75, .55],
      zoom: 420,
      parts: [
        { def: j.cutId, qty: (M.defs.get(j.cutId) || {}).qty || 1 },
        { def: j.addId, qty: (M.defs.get(j.addId) || {}).qty || 1 }
      ],
      text: how.text,
      tools: how.tools,
      tip: how.tip,
      chk: how.chk,
      joinLabel: CAD.jointMethodLabel(j.method) + (j.label ? ' · ' + inch(j.label) : ''),
      method: j.method
    });
  });

  /* Remaining labeled parts without a dedicated mating page */
  defs.filter(d => (d.solid.feat || []).some(f => f.label) && !covered.has(d.id))
    .sort((a, b) => String(a.grp).localeCompare(String(b.grp)))
    .slice(0, 10)
    .forEach(d => {
      const feats = d.solid.feat.filter(f => f.label), tags = [...new Set(feats.map(f => f.tag).filter(Boolean))];
      const seen = new Set(), tx = [];
      feats.forEach(f => {
        if (seen.has(f.label)) return; seen.add(f.label);
        const lab = E(f.label);
        const method = CAD.classifyJoint(f.label, f.tag, f.kind);
        tx.push(f.kind === 'cut'
          ? 'Remove <b>' + lab + '</b> (orange) — ' + CAD.jointMethodLabel(method) + '. Knife the layout, remove waste, pare to the lines.'
          : 'Leave <b>' + lab + '</b> (green) — ' + CAD.jointMethodLabel(method) + '. Saw cheeks and shoulders; pare to fit its mate.');
      });
      (d.notes || []).forEach(n => tx.push(E(n)));
      tx.push('Make <b>' + d.qty + '</b> of these.');
      add({
        kind: 'part', phase: 'Joinery', title: 'Make the joints: ' + E(d.name),
        focus: [d.id], tags, dir: [.8, .85, .6], zoom: 'first',
        parts: [{ def: d.id, qty: d.qty }],
        text: tx.slice(0, 6).map(clean),
        tools: (d.tools && d.tools.length ? d.tools : ['Marking knife', 'Square', 'Chisels', 'Saw']).map(t => E(t)),
        tip: 'Cut one test joint in scrap first.',
        chk: 'Dry-fit with its mating part before any glue.'
      });
    });

  M.steps.forEach((s, k) => {
    if (!M.insts.some(i => i.step === k)) return;
    const partIds = [...new Set(M.insts.filter(i => i.step === k).map(i => i.def))];
    const hint = CAD.asmJoineryHint(M, partIds);
    const nt = (s.notes || []).map(E);
    const text = hint && hint.text.length
      ? hint.text.concat(nt.length ? nt : [])
      : (nt.length ? nt : [
        'Dry-fit the new parts on the joint faces shown in the Joinery pages.',
        'Glue only long-grain meeting faces; clamp until set.',
        'Check the assembly is square and flat before the next step.'
      ]);
    const joinLabel = hint && hint.joints[0]
      ? CAD.jointMethodLabel(hint.joints[0].method) + (hint.joints[0].label ? ' · ' + inch(hint.joints[0].label) : '')
      : null;
    add({
      kind: 'asm', phase: 'Assembly', title: E(s.title), asm: k,
      dir: [.7, -.9, .6],
      text: text.map(clean),
      tools: (s.tools && s.tools.length ? s.tools : ['Glue', 'Clamps', 'Square']).map(t => E(t)),
      tip: s.tip ? E(s.tip) : (hint ? 'One joint at a time — do not glue the whole frame in one scramble.' : undefined),
      chk: s.check ? E(s.check) : (hint ? 'After clamping, diagonals match and faces sit flush at each joint.' : undefined),
      joinLabel
    });
  });

  add({
    kind: 'hero', phase: 'Finish', title: 'Finish and enjoy', final: true,
    text: ['Sand, finish and check every moving part.', 'Keep this guide with the spec file so the design can be changed and rebuilt.'],
    tools: []
  });
  return S;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
