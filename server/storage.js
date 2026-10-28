/* Optional R2/S3 image storage. Opt-in only — never upload without consent=true.
   Env: R2_ACCOUNT_ID (or S3_ENDPOINT), R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, optional R2_PUBLIC_BASE_URL */
const crypto = require('crypto');

function enabled() {
  return !!(
    (process.env.R2_ACCOUNT_ID || process.env.S3_ENDPOINT) &&
    process.env.R2_ACCESS_KEY_ID &&
    process.env.R2_SECRET_ACCESS_KEY &&
    process.env.R2_BUCKET
  );
}

function endpoint() {
  if (process.env.S3_ENDPOINT) return process.env.S3_ENDPOINT.replace(/\/$/, '');
  return 'https://' + process.env.R2_ACCOUNT_ID + '.r2.cloudflarestorage.com';
}

function sha256Hex(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function parseDataUrl(dataUrl) {
  const m = String(dataUrl || '').match(/^data:([^;]+);base64,(.+)$/i);
  if (!m) return null;
  const mediaType = m[1];
  const buf = Buffer.from(m[2], 'base64');
  return { mediaType, buf };
}

function publicUrl(key) {
  const base = (process.env.R2_PUBLIC_BASE_URL || '').replace(/\/$/, '');
  if (base) return base + '/' + key;
  return null;
}

/**
 * Put object via AWS SigV4 (S3-compatible). Zero extra deps beyond Node crypto.
 */
async function putObject({ key, body, contentType }) {
  if (!enabled()) return { ok: false, error: 'storage not configured' };
  const host = endpoint().replace(/^https?:\/\//, '');
  const region = process.env.R2_REGION || 'auto';
  const service = 's3';
  const method = 'PUT';
  const amzDate = new Date().toISOString().replace(/[:-]|\.\d{3}/g, '');
  const dateStamp = amzDate.slice(0, 8);
  const payloadHash = crypto.createHash('sha256').update(body).digest('hex');
  const canonicalUri = '/' + process.env.R2_BUCKET + '/' + key.split('/').map(encodeURIComponent).join('/');
  const canonicalHeaders =
    'content-type:' + contentType + '\n' +
    'host:' + host + '\n' +
    'x-amz-content-sha256:' + payloadHash + '\n' +
    'x-amz-date:' + amzDate + '\n';
  const signedHeaders = 'content-type;host;x-amz-content-sha256;x-amz-date';
  const canonicalRequest = [method, canonicalUri, '', canonicalHeaders, signedHeaders, payloadHash].join('\n');
  const credentialScope = dateStamp + '/' + region + '/' + service + '/aws4_request';
  const stringToSign = [
    'AWS4-HMAC-SHA256',
    amzDate,
    credentialScope,
    crypto.createHash('sha256').update(canonicalRequest).digest('hex')
  ].join('\n');
  const hmac = (k, d) => crypto.createHmac('sha256', k).update(d).digest();
  const kDate = hmac('AWS4' + process.env.R2_SECRET_ACCESS_KEY, dateStamp);
  const kRegion = hmac(kDate, region);
  const kService = hmac(kRegion, service);
  const kSigning = hmac(kService, 'aws4_request');
  const signature = crypto.createHmac('sha256', kSigning).update(stringToSign).digest('hex');
  const authorization =
    'AWS4-HMAC-SHA256 Credential=' + process.env.R2_ACCESS_KEY_ID + '/' + credentialScope +
    ', SignedHeaders=' + signedHeaders + ', Signature=' + signature;
  const url = endpoint() + canonicalUri;
  const r = await fetch(url, {
    method: 'PUT',
    headers: {
      'content-type': contentType,
      host,
      'x-amz-content-sha256': payloadHash,
      'x-amz-date': amzDate,
      authorization
    },
    body
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    return { ok: false, status: r.status, error: text.slice(0, 300) };
  }
  return { ok: true, key, url: publicUrl(key) };
}

/**
 * @param {{ runId: string, consent: boolean, dataUrl?: string, mediaType?: string, bytes?: Buffer }} o
 */
async function uploadRunImage(o) {
  if (!o || !o.consent) return { ok: false, error: 'consent required' };
  if (!o.runId) return { ok: false, error: 'runId required' };
  let buf = o.bytes || null;
  let mediaType = o.mediaType || 'image/jpeg';
  if (!buf && o.dataUrl) {
    const parsed = parseDataUrl(o.dataUrl);
    if (!parsed) return { ok: false, error: 'invalid data URL' };
    buf = parsed.buf;
    mediaType = parsed.mediaType;
  }
  if (!buf || !buf.length) return { ok: false, error: 'empty image' };
  if (buf.length > 8 * 1024 * 1024) return { ok: false, error: 'image too large (max 8MB)' };
  const hash = sha256Hex(buf);
  const ext = /png/i.test(mediaType) ? 'png' : (/webp/i.test(mediaType) ? 'webp' : 'jpg');
  const key = 'runs/' + String(o.runId).replace(/[^A-Za-z0-9._:-]/g, '_') + '/' + hash.slice(0, 16) + '.' + ext;
  if (!enabled()) {
    return { ok: true, skippedUpload: true, imageHash: hash, imageUrl: null, imageConsent: true };
  }
  const put = await putObject({ key, body: buf, contentType: mediaType });
  if (!put.ok) return put;
  return { ok: true, imageHash: hash, imageUrl: put.url, imageConsent: true, key: put.key };
}

module.exports = { enabled, sha256Hex, parseDataUrl, uploadRunImage, putObject, publicUrl };
