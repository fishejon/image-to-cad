/* Workspace persistence: IndexedDB primary, localStorage fallback, export/import packs. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
const Store = CAD.store = {};
Store.LS_KEY = 'image-to-cad.workspace';
Store.DB_NAME = 'image-to-cad';
Store.DB_VER = 1;
Store.STORE = 'meta';
Store.RECORD = 'workspace';

function readLS() {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(Store.LS_KEY) : null;
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}
function writeLS(data) {
  try {
    if (typeof localStorage === 'undefined') return false;
    localStorage.setItem(Store.LS_KEY, JSON.stringify(data));
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

function idbGet() {
  return openDB().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(Store.STORE, 'readonly');
    const req = tx.objectStore(Store.STORE).get(Store.RECORD);
    req.onsuccess = () => { db.close(); resolve(req.result || null); };
    req.onerror = () => { db.close(); reject(req.error); };
  }));
}
function idbSet(data) {
  return openDB().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(Store.STORE, 'readwrite');
    tx.objectStore(Store.STORE).put(data, Store.RECORD);
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
    const fromIdb = await idbGet();
    const n = Store.normalize(fromIdb);
    if (n && n.docs && Object.keys(n.docs).length) return n;
  } catch (e) { /* fall through */ }
  return Store.normalize(readLS());
};

Store.write = async function (data) {
  const n = Store.normalize(Object.assign({}, data, { updated: Date.now(), version: 1 }));
  if (!n) return false;
  writeLS(n);
  try { await idbSet(n); } catch (e) { /* LS may still have it */ }
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
})(typeof globalThis !== 'undefined' ? globalThis : window);
