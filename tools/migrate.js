#!/usr/bin/env node
/* Apply server/sql/*.sql against DATABASE_URL. */
const path = require('path');
const fs = require('fs');
const db = require('../server/db');

async function main() {
  if (!db.enabled()) {
    console.error('DATABASE_URL is not set');
    process.exit(1);
  }
  const dir = path.join(__dirname, '..', 'server', 'sql');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.sql')).sort();
  for (const f of files) {
    const sql = fs.readFileSync(path.join(dir, f), 'utf8');
    process.stdout.write('Applying ' + f + '… ');
    await db.query(sql);
    console.log('ok');
  }
  await db.resetForTests();
  console.log('migrate done');
}

main().catch(e => { console.error(e); process.exit(1); });
