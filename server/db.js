/* Optional Postgres (Neon / any PG). No-ops when DATABASE_URL is unset. */
const fs = require('fs');
const path = require('path');

let pool = null;
let ensurePromise = null;

function enabled() {
  return !!process.env.DATABASE_URL;
}

function getPool() {
  if (!enabled()) return null;
  if (pool) return pool;
  const { Pool } = require('pg');
  pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.DATABASE_SSL === '0' ? false : { rejectUnauthorized: false },
    max: Math.min(5, +(process.env.DATABASE_POOL_MAX || 3)),
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 8000
  });
  pool.on('error', err => {
    try { console.log(JSON.stringify({ kind: 'db_pool_error', error: err && err.message })); } catch (e) { /* ignore */ }
  });
  return pool;
}

async function query(text, params) {
  const p = getPool();
  if (!p) return null;
  return p.query(text, params);
}

async function ensureSchema() {
  if (!enabled()) return { skipped: true };
  if (ensurePromise) return ensurePromise;
  ensurePromise = (async () => {
    const sqlPath = path.join(__dirname, 'sql', '001_hitl.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');
    await query(sql);
    return { ok: true };
  })().catch(err => {
    ensurePromise = null;
    try { console.log(JSON.stringify({ kind: 'db_migrate_error', error: err && err.message })); } catch (e) { /* ignore */ }
    return { ok: false, error: err && err.message };
  });
  return ensurePromise;
}

async function withSchema(fn) {
  if (!enabled()) return null;
  const mig = await ensureSchema();
  if (mig && mig.ok === false) return null;
  return fn();
}

function resetForTests() {
  ensurePromise = null;
  if (pool) {
    const old = pool;
    pool = null;
    return old.end().catch(() => {});
  }
}

module.exports = { enabled, getPool, query, ensureSchema, withSchema, resetForTests };
