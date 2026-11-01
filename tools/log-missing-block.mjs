#!/usr/bin/env node
/**
 * Append a missing_block line to evals/photos/chairs/failure_log.jsonl
 * Usage: node tools/log-missing-block.mjs chair_05 organic_taper_leg "sculptural mid-thick legs"
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const logPath = path.join(root, 'evals/photos/chairs/failure_log.jsonl');
const [photoId, need, ...noteParts] = process.argv.slice(2);
if (!photoId || !need) {
  console.error('Usage: node tools/log-missing-block.mjs <photo_id> <need> [notes…]');
  process.exit(1);
}
const row = {
  ts: new Date().toISOString(),
  kind: 'missing_block',
  need,
  photo_id: photoId,
  template: null,
  notes: noteParts.join(' ') || ''
};
fs.appendFileSync(logPath, JSON.stringify(row) + '\n');
console.log('Appended', row);
