/* Workspace + HITL feedback persistence: IndexedDB primary, localStorage fallback. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
const Store = CAD.store = {};
Store.LS_KEY = 'image-to-cad.workspace';
Store.LS_FEEDBACK = 'image-to-cad.feedback';
Store.LS_EXAMPLES = 'image-to-cad.examples';
Store.DB_NAME = 'image-to-cad';
Store.DB_VER = 2;
Store.STORE = 'meta';
Store.RECORD = 'workspace';
Store.FEEDBACK = 'feedback';
Store.EXAMPLES = 'examples';

function readLS(key) {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}
function writeLS(key, data) {
  try {
    if (typeof localStorage === 'undefined') return false;
    localStorage.setItem(key, JSON.stringify(data));
    return true;
  } catch (e) { return false; }
}

function openDB() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') return reject(new Error('no indexedDB'));
    const req = indexedDB.open(Store.DB_NAME, Store.DB_VER);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(Store.STORE)) db.createObjectStore(Store.STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('indexedDB open failed'));
  });
}

function idbGet(key) {
  return openDB().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(Store.STORE, 'readonly');
    const req = tx.objectStore(Store.STORE).get(key);
    req.onsuccess = () => { db.close(); resolve(req.result || null); };
    req.onerror = () => { db.close(); reject(req.error); };
  }));
}
function idbSet(key, data) {
  return openDB().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(Store.STORE, 'readwrite');
    tx.objectStore(Store.STORE).put(data, key);
    tx.oncomplete = () => { db.close(); resolve(true); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  }));
}

Store.normalize = function (data) {
  if (!data || typeof data !== 'object') return null;
  if (!data.docs || typeof data.docs !== 'object') return null;
  return {
    version: data.version || 1,
    activeId: data.activeId || null,
    docs: data.docs,
    updated: data.updated || Date.now()
  };
};

Store.read = async function () {
  try {
    const fromIdb = await idbGet(Store.RECORD);
    const n = Store.normalize(fromIdb);
    if (n && n.docs && Object.keys(n.docs).length) return n;
  } catch (e) { /* fall through */ }
  return Store.normalize(readLS(Store.LS_KEY));
};

Store.write = async function (data) {
  const n = Store.normalize(Object.assign({}, data, { updated: Date.now(), version: 1 }));
  if (!n) return false;
  writeLS(Store.LS_KEY, n);
  try { await idbSet(Store.RECORD, n); } catch (e) { /* LS may still have it */ }
  return true;
};

Store.pack = function (docs, activeId) {
  const clean = {};
  Object.values(docs || {}).forEach(d => {
    if (!d || !d.id) return;
    clean[d.id] = {
      id: d.id,
      name: d.name || 'Untitled',
      source: d.source || null,
      updated: d.updated || 0,
      spec: d.spec,
      ov: d.ov || {}
    };
  });
  return {
    version: 1,
    kind: 'image-to-cad-workspace',
    exportedAt: Date.now(),
    activeId: activeId || null,
    docs: clean
  };
};

Store.unpack = function (raw) {
  let data = raw;
  if (typeof raw === 'string') {
    try { data = JSON.parse(raw); } catch (e) { throw new Error('workspace file is not valid JSON'); }
  }
  if (!data || data.kind !== 'image-to-cad-workspace') throw new Error('not an image-to-cad workspace pack');
  const n = Store.normalize(data);
  if (!n || !Object.keys(n.docs).length) throw new Error('workspace pack has no designs');
  return n;
};

/* ---------- HITL feedback + example bank ---------- */
Store.FAILURE_TAGS = ['proportions', 'count', 'section', 'topology', 'missing', 'extra', 'dimensions', 'other'];

Store.uid = function () {
  return 'f' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
};

async function readList(idbKey, lsKey) {
  try {
    const fromIdb = await idbGet(idbKey);
    if (Array.isArray(fromIdb)) return fromIdb;
    if (fromIdb && Array.isArray(fromIdb.items)) return fromIdb.items;
  } catch (e) { /* fall through */ }
  const ls = readLS(lsKey);
  if (Array.isArray(ls)) return ls;
  if (ls && Array.isArray(ls.items)) return ls.items;
  return [];
}
async function writeList(idbKey, lsKey, items) {
  const payload = { version: 1, updated: Date.now(), items: items || [] };
  writeLS(lsKey, payload);
  try { await idbSet(idbKey, payload); } catch (e) { /* ok */ }
  return true;
}

Store.readFeedback = function () { return readList(Store.FEEDBACK, Store.LS_FEEDBACK); };
Store.writeFeedback = function (items) { return writeList(Store.FEEDBACK, Store.LS_FEEDBACK, items); };
Store.addFeedback = async function (entry) {
  const items = await Store.readFeedback();
  const row = Object.assign({
    id: Store.uid(),
    createdAt: Date.now(),
    rating: 'close',
    failureTags: [],
    note: ''
  }, entry || {});
  items.unshift(row);
  await Store.writeFeedback(items.slice(0, 200));
  return row;
};

Store.readExamples = function () { return readList(Store.EXAMPLES, Store.LS_EXAMPLES); };
Store.writeExamples = function (items) { return writeList(Store.EXAMPLES, Store.LS_EXAMPLES, items); };
Store.addExample = async function (entry) {
  const items = await Store.readExamples();
  const row = Object.assign({
    id: Store.uid(),
    createdAt: Date.now(),
    inventory: null,
    specSummary: null,
    hints: '',
    object: ''
  }, entry || {});
  items.unshift(row);
  await Store.writeExamples(items.slice(0, 40));
  return row;
};

/** Compact spec for few-shot injection (ids, kinds, names, groups — not full ops). */
Store.summarizeSpec = function (spec) {
  if (!spec || typeof spec !== 'object') return null;
  return {
    name: spec.name || '',
    parts: (spec.parts || []).slice(0, 24).map(p => ({
      id: p.id,
      name: p.name,
      kind: p.kind || (p.prims ? 'mesh' : 'solid'),
      group: p.group,
      material: p.material,
      shapeHint: p.prims && p.prims[0] ? p.prims[0].type : (p.ops ? 'box-ops' : undefined)
    }))
  };
};

/** Pick up to `n` past successes for prompt injection (most recent; prefer same object name). */
Store.pickExamples = function (items, o) {
  o = o || {};
  const list = (items || []).filter(x => x && (x.specSummary || x.inventory));
  if (!list.length) return [];
  const want = String((o.inventory && o.inventory.object) || o.object || '').toLowerCase().trim();
  const scored = list.map((x, i) => {
    let s = list.length - i;
    const obj = String(x.object || (x.inventory && x.inventory.object) || '').toLowerCase();
    if (want && obj && (obj === want || obj.indexOf(want) >= 0 || want.indexOf(obj) >= 0)) s += 50;
    return { x, s };
  });
  scored.sort((a, b) => b.s - a.s);
  return scored.slice(0, o.n || 1).map(r => r.x);
};

Store.formatExamplesForPrompt = function (examples) {
  if (!examples || !examples.length) return '';
  const blocks = examples.map((ex, i) => {
    const bits = ['SIMILAR PAST SUCCESS #' + (i + 1) + ' (user marked Match — reuse construction patterns, not copy sizes blindly):'];
    if (ex.object || (ex.inventory && ex.inventory.object)) bits.push('Object: ' + (ex.object || ex.inventory.object));
    if (ex.inventory) bits.push('Inventory: ' + JSON.stringify(ex.inventory).slice(0, 900));
    if (ex.specSummary) bits.push('Part layout: ' + JSON.stringify(ex.specSummary).slice(0, 1100));
    if (ex.hints) bits.push('User hints then: ' + String(ex.hints).slice(0, 200));
    return bits.join('\n');
  });
  return blocks.join('\n\n');
};

/** Map UI quality preset → rounds + default visual critic. */
Store.qualityPreset = function (id) {
  const map = {
    fast: { id: 'fast', rounds: 1, visual: false, label: 'Fast', hint: '1 pass, geometry only' },
    balanced: { id: 'balanced', rounds: 2, visual: true, label: 'Balanced', hint: '2 passes + photo match' },
    careful: { id: 'careful', rounds: 4, visual: true, label: 'Careful', hint: '4 passes + photo match' }
  };
  return map[id] || map.balanced;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
