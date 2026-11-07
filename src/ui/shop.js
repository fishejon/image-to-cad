/* Shop-grade UI: intake → progress → review compare → worker jobs (ui-ux-shop-grade.md). */
(function (g) {
  const CAD = g.CAD || (g.CAD = {});
  const Shop = CAD.shop = CAD.shop || {};

  Shop.STEPS = [
    { id: 'read', label: 'Reading your photo' },
    { id: 'build', label: 'Building the model' },
    { id: 'check', label: 'Checking against the photo' },
    { id: 'adjust', label: 'Adjusting' },
    { id: 'lists', label: 'Making your lists' }
  ];

  Shop.state = Shop.state || {
    mode: 'shop', /* shop | classic */
    jobId: null,
    jobStatus: null,
    workerOnline: null,
    workerDetail: '',
    round: 0,
    maxRounds: 4,
    stepId: 'read',
    statusLine: '',
    startedAt: 0,
    spendUsd: 0,
    spendCap: 2,
    previews: [],
    bestSpec: null,
    assumptions: [],
    questions: [],
    knownSize: null, /* { dim:'h'|'w'|'d', valueMm, label } */
    noSize: false,
    materialsBrief: '',
    photos: [], /* { url, role } */
    compare: 'side', /* side | overlay | silhouette */
    overlayT: 0.5,
    scopeTier: null, /* full | blank | ask */
    checklist: {},
    domain: 'woodworking',
    lists: null, /* worker lists.json */
    parts: null, /* worker parts.json */
    artifacts: [],
    pollTimer: null,
    pendingQuestion: null,
    cancelRequested: false
  };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

  Shop.domainProfiles = {
    woodworking: { label: 'Woodworking', listHint: 'Boards, plywood, and blanks' },
    cabinetry: { label: 'Cabinetry', listHint: 'Sheet goods + edge banding' },
    metal: { label: 'Metal fab', listHint: 'Stock lengths — nesting differs' }
  };

  Shop.workerBase = function () {
    try { return (localStorage.getItem('image-to-cad.worker') || '').replace(/\/$/, ''); } catch (e) { return ''; }
  };

  Shop.setWorkerBase = function (url) {
    try { localStorage.setItem('image-to-cad.worker', url || ''); } catch (e) { /* ignore */ }
  };

  Shop.pingWorker = async function () {
    const base = Shop.workerBase();
    try {
      if (base) {
        const r = await fetch(base + '/health');
        Shop.state.workerOnline = r.ok;
        Shop.state.workerDetail = r.ok ? 'direct Worker URL' : ('health HTTP ' + r.status);
        return r.ok;
      }
      const r = await fetch('/api/jobs', { cache: 'no-store' });
      if (r.status === 503) {
        Shop.state.workerOnline = false;
        Shop.state.workerDetail = 'WORKER_JOBS_URL unset on server';
        return false;
      }
      if (r.status === 401 || r.status === 403) {
        Shop.state.workerOnline = false;
        Shop.state.workerDetail = 'unauthorized — set WORKER_JOBS_TOKEN on Vercel (same as Fly) and redeploy';
        return false;
      }
      Shop.state.workerOnline = r.ok;
      Shop.state.workerDetail = r.ok ? 'via /api/jobs' : ('HTTP ' + r.status);
      return Shop.state.workerOnline;
    } catch (e) {
      Shop.state.workerOnline = false;
      Shop.state.workerDetail = e.message || 'unreachable';
      return false;
    }
  };

  Shop.persistJob = function (doc) {
    if (!doc) return;
    doc.shopJobId = Shop.state.jobId;
    doc.shopMode = Shop.state.mode;
    try {
      const raw = localStorage.getItem('image-to-cad.shopRun');
      const o = raw ? JSON.parse(raw) : {};
      o.jobId = Shop.state.jobId;
      o.docId = doc.id;
      o.at = Date.now();
      localStorage.setItem('image-to-cad.shopRun', JSON.stringify(o));
    } catch (e) { /* ignore */ }
  };

  Shop.restoreJobHint = function () {
    try {
      const o = JSON.parse(localStorage.getItem('image-to-cad.shopRun') || 'null');
      if (o && o.jobId) return o;
    } catch (e) { /* ignore */ }
    return null;
  };

  Shop.progressHtml = function () {
    const st = Shop.state;
    const elapsed = st.startedAt ? Math.round((Date.now() - st.startedAt) / 1000) : 0;
    const steps = Shop.STEPS.map(s => {
      const on = s.id === st.stepId;
      const done = Shop.STEPS.findIndex(x => x.id === st.stepId) > Shop.STEPS.findIndex(x => x.id === s.id);
      return `<li class="${done ? 'done' : ''}${on ? ' on' : ''}">${esc(s.label)}</li>`;
    }).join('');
    const prev = st.previews.length
      ? `<div class="shopPrev"><img src="${st.previews[st.previews.length - 1]}" alt="Round preview"><button type="button" class="btn sm" id="shopPrevPrev" ${st.previews.length < 2 ? 'disabled' : ''}>Previous round</button></div>`
      : '<div class="card" style="font-size:12px;color:var(--dim)">Preview appears after each round.</div>';
    const worker = st.workerOnline === true ? 'Worker online' : st.workerOnline === false ? 'Worker offline' : 'Checking worker…';
    const nearCap = st.spendUsd >= st.spendCap * 0.85;
    const capWarn = nearCap
      ? `<div class="card warn" role="status"><b>Near spend cap</b> ~$${Number(st.spendUsd).toFixed(2)} of $${st.spendCap} — stop and keep best, or continue.</div>`
      : '';
    return `<div class="shopProgress" role="status" aria-live="polite">
      ${capWarn}
      <div class="row" style="gap:8px;align-items:center;flex-wrap:wrap">
        <span class="statusBadge" data-st="${st.workerOnline ? 'good' : 'check'}">${esc(worker)}</span>
        <span style="font-size:12px;color:var(--dim)">Round ${st.round || '—'} of ${st.maxRounds}</span>
        <span style="font-size:12px;color:var(--dim)">${elapsed}s elapsed · typical 2–8 min</span>
        <span style="font-size:12px;color:var(--dim)">Spend ~$${Number(st.spendUsd || 0).toFixed(2)} / $${st.spendCap}</span>
      </div>
      <ol class="shopSteps">${steps}</ol>
      <div class="card" id="shopStatusLine"><b>Now:</b> ${esc(st.statusLine || 'Starting…')}</div>
      ${st.pendingQuestion ? `<div class="card warn" id="shopAskCard"><b>Question</b><div style="margin-top:6px">${esc(st.pendingQuestion.question || '')}</div>
        ${(st.pendingQuestion.choices || []).map(c => `<button type="button" class="btn sm" data-shop-ans="${esc(c)}" style="margin:4px 4px 0 0">${esc(c)}</button>`).join('')}
        <textarea id="shopAskAns" rows="2" placeholder="Your answer" style="width:100%;margin-top:8px;background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:6px"></textarea>
        <button class="btn pri sm" id="shopAskSend" style="width:100%;margin-top:6px">Send answer</button>
      </div>` : ''}
      ${prev}
      <div class="grid2" style="margin-top:8px">
        <button class="btn pri sm" id="shopStopKeep">Stop and keep best</button>
        <button class="btn sm" id="shopBg">Run in background</button>
      </div>
      <button class="btn sm" id="shopCancel" style="width:100%;margin-top:6px">Cancel with no result</button>
    </div>`;
  };

  Shop.compareHtml = function (photoUrl) {
    const st = Shop.state;
    if (!photoUrl) return '<div class="card">No reference photo yet.</div>';
    return `<div class="shopCompare">
      <div class="mtabs">
        <button type="button" class="btn sm${st.compare === 'side' ? ' on' : ''}" data-cmp="side">Side by side</button>
        <button type="button" class="btn sm${st.compare === 'overlay' ? ' on' : ''}" data-cmp="overlay">Overlay</button>
        <button type="button" class="btn sm${st.compare === 'silhouette' ? ' on' : ''}" data-cmp="silhouette">Silhouette</button>
      </div>
      <div class="shopCmpBody" data-mode="${esc(st.compare)}">
        <div class="shopCmpPhoto"><img src="${photoUrl}" alt="Reference"></div>
        <div class="shopCmpModel" id="shopCmpModelSlot"><div class="card" style="font-size:12px;color:var(--dim)">Model view stays in the main viewport — use this photo for comparison.</div></div>
      </div>
      ${st.compare === 'overlay' ? `<input type="range" id="shopOverlay" min="0" max="100" value="${Math.round(st.overlayT * 100)}" style="width:100%">` : ''}
    </div>`;
  };

  Shop.timelineHtml = function (log) {
    const lines = (log || []).slice(-40);
    if (!lines.length) return '<div class="card">No run log yet.</div>';
    return `<div class="shopTimeline"><h3>Run timeline</h3>
      <ol>${lines.map((m, i) => `<li><span class="n">${i + 1}</span> ${esc(typeof m === 'string' ? m : JSON.stringify(m))}</li>`).join('')}</ol>
      <button class="btn sm" id="shopCopyLog">Copy log</button></div>`;
  };

  Shop.intakeHtml = function () {
    const st = Shop.state;
    const photos = st.photos.map((p, i) => `<div class="shopPhotoChip"><img src="${p.url}" alt=""><span>${esc(p.role || 'photo')}</span><button type="button" data-rm="${i}" class="btn sm">×</button></div>`).join('');
    return `<div class="shopIntake">
      <h3>New design · Shop-grade</h3>
      <p class="card" style="font-size:12px;color:var(--dim)">Take a picture, get something you can build. One known size makes the lists reliable.</p>
      <div id="shopDrop" class="shopDrop"><div><b>Drop, paste, or click</b> for a photo</div>
        <div style="font-size:12px;color:var(--dim);margin-top:4px">Straight-on, full piece in frame, little clutter</div>
        <input type="file" id="shopFile" accept="image/*" multiple hidden></div>
      <div class="shopPhotoRow">${photos || ''}</div>
      <div id="shopPhotoWarn" class="card warn" style="display:none;margin-top:8px"></div>
      <h3>One known size</h3>
      <div class="row" style="flex-wrap:wrap;gap:6px">
        <select id="shopDim" class="btn"><option value="h">Overall height</option><option value="w">Overall width</option><option value="d">Overall depth</option></select>
        <input id="shopSize" type="text" placeholder="e.g. 32 in or 813 mm" style="flex:1;min-width:8em;background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:4px 6px">
      </div>
      <div class="chk" style="margin-top:6px"><input type="checkbox" id="shopNoSize"${st.noSize ? ' checked' : ''}><label for="shopNoSize">I don’t know a size — accuracy will be lower</label></div>
      <h3>Materials (optional)</h3>
      <textarea id="shopMats" rows="2" placeholder="e.g. oak, ¾″ plywood back" style="width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:6px">${esc(st.materialsBrief)}</textarea>
      <h3>Domain</h3>
      <select id="shopDomain" class="btn" style="width:100%">${Object.keys(Shop.domainProfiles).map(k =>
        `<option value="${esc(k)}"${(st.domain || 'woodworking') === k ? ' selected' : ''}>${esc(Shop.domainProfiles[k].label)}</option>`).join('')}</select>
      <h3>Run mode</h3>
      <div class="shopModes">
        <label class="shopMode${st.mode === 'shop' ? ' on' : ''}"><input type="radio" name="shopMode" value="shop"${st.mode === 'shop' ? ' checked' : ''}> <b>Shop-grade</b><span>Real geometry + lists · several minutes · worker</span></label>
        <label class="shopMode${st.mode === 'classic' ? ' on' : ''}"><input type="radio" name="shopMode" value="classic"${st.mode === 'classic' ? ' checked' : ''}> <b>Classic</b><span>Faster simple shapes · Vercel proxy</span></label>
      </div>
      <p style="font-size:11px;color:var(--dim)">Photos stay in this browser unless you opt in to upload for training. Shop-grade uses the worker key — you don’t paste an API key here.</p>
      <button class="btn pri" id="shopContinue" style="width:100%;margin-top:10px" disabled>${st.mode === 'classic' ? 'Continue to Classic Create' : 'Continue to read-back'}</button>
    </div>`;
  };

  Shop.readbackHtml = function (inventory) {
    const inv = inventory || {};
    const parts = (inv.parts || inv.members || []).slice(0, 12);
    const partRows = parts.length
      ? parts.map((p, i) => {
        const name = typeof p === 'string' ? p : (p.name || p.id || 'Part ' + (i + 1));
        return `<tr><td>${esc(name)}</td><td><input data-part="${i}" value="${esc(name)}" style="width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:4px;padding:2px 4px"></td></tr>`;
      }).join('')
      : `<tr><td colspan="2" style="color:var(--dim)">Parts will be listed after inventory — confirm assumptions below and start.</td></tr>`;
    const assumptions = Shop.state.assumptions.length
      ? Shop.state.assumptions
      : [
        Shop.state.noSize ? 'Scale: estimated from proportions (no known size)' : 'Scale: from your known size',
        'Thickness: typical furniture stock unless noted',
        Shop.state.materialsBrief ? 'Material: ' + Shop.state.materialsBrief : 'Material: default hardwood / plywood'
      ];
    Shop.state.assumptions = assumptions;
    return `<div class="shopReadback">
      <h3>What I see</h3>
      <table><tr><th>Part</th><th>Name</th></tr>${partRows}</table>
      <h3>Assumptions</h3>
      <ul id="shopAssume">${assumptions.map((a, i) => `<li><input data-as="${i}" value="${esc(a)}" style="width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:4px;padding:2px 4px"></li>`).join('')}</ul>
      <h3>Questions</h3>
      <div class="card" style="font-size:12px;color:var(--dim)">At most two questions when something is ambiguous. Skip = use best guess.</div>
      <div id="shopQs"></div>
      <button class="btn pri" id="shopStartBuild" style="width:100%;margin-top:10px">Start build</button>
      <button class="btn sm" id="shopBackIntake" style="width:100%;margin-top:6px">Back</button>
    </div>`;
  };

  Shop.reviewSummaryHtml = function (opts) {
    opts = opts || {};
    const match = opts.matchLabel || 'Close';
    const badge = (CAD.uiTerms && CAD.uiTerms.statusBadge) ? CAD.uiTerms.statusBadge : function (k) { return k; };
    return `<div class="shopReview">
      <div class="card"><b>Review</b>
        <div style="margin-top:6px">${badge(match === 'Match' || match === 'Good' ? 'good' : match === 'Close' || match === 'Close+' ? 'close' : 'check')} photo match ·
          ${badge(opts.knownSize ? 'measured' : 'estimated')} scale ·
          ${esc(String(opts.partCount || '—'))} part types</div>
        <div style="font-size:12px;color:var(--dim);margin-top:6px">Size vs known: ${esc(opts.sizeNote || (opts.knownSize ? 'checked against your measurement' : 'no known size — lists are estimates'))}</div>
      </div>
      <div class="grid2" style="margin-top:8px">
        <button class="btn pri sm" id="shopAccept">Accept and plan the build</button>
        <button class="btn sm" id="shopFix">Fix something</button>
      </div>
      <button class="btn sm" id="shopRetry" style="width:100%;margin-top:6px">Try again</button>
    </div>`;
  };

  Shop.scopeBannerHtml = function () {
    const t = Shop.state.scopeTier;
    if (!t || t === 'full') return '';
    if (t === 'blank') return `<div class="card warn"><b>Shaped blank estimate</b> This piece is organic or sculpted. Lists show blank stock sizes, not CNC toolpaths.</div>`;
    if (t === 'ask') return `<div class="card warn"><b>Need more detail</b> The photo isn’t enough for a full model. Answer the question or try another photo.</div>`;
    return '';
  };

  Shop.apiRoot = function () {
    const base = Shop.workerBase();
    return base || '';
  };

  Shop.jobsUrl = function (path) {
    path = path || '';
    const root = Shop.apiRoot();
    if (root) return root + (path.startsWith('/jobs') ? path : '/jobs' + path);
    return '/api/jobs' + (path === '/jobs' || path === '' ? '' : path.replace(/^\/jobs/, ''));
  };

  Shop.fetchJson = async function (path, init) {
    const r = await fetch(Shop.jobsUrl(path), Object.assign({ cache: 'no-store' }, init || {}));
    const text = await r.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch (e) { body = { raw: text }; }
    if (!r.ok) {
      const msg = (body && body.error && (body.error.message || body.error)) || body.error || ('HTTP ' + r.status);
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      err.status = r.status;
      err.body = body;
      throw err;
    }
    return body;
  };

  Shop.buildPrompt = function () {
    const st = Shop.state;
    const bits = [
      'Build shop-grade furniture from the reference photo.',
      'Produce an assembly (STL/STEP) and cut/material lists via tools.',
      'Domain profile: ' + (st.domain || 'woodworking') + '.'
    ];
    if (st.knownSize && !st.noSize) {
      const dim = st.knownSize.dim === 'w' ? 'width' : st.knownSize.dim === 'd' ? 'depth' : 'height';
      bits.push('Known overall ' + dim + ': ' + st.knownSize.label + ' (' + Math.round(st.knownSize.valueMm) + ' mm).');
    } else {
      bits.push('No known size — estimate scale from proportions and ask_user only if stuck.');
    }
    if (st.materialsBrief) bits.push('Materials: ' + st.materialsBrief);
    (st.assumptions || []).forEach(a => bits.push('Assumption: ' + a));
    if (st.photos.length > 1) bits.push('User provided ' + st.photos.length + ' photos; primary is front/overall.');
    return bits.join(' ');
  };

  Shop.createAndRunJob = async function () {
    const st = Shop.state;
    const photo = (st.photos[0] && st.photos[0].url) || null;
    const body = {
      prompt: Shop.buildPrompt(),
      photo_b64: photo,
      domain: st.domain || 'woodworking',
      run: true,
      async: true
    };
    const created = await Shop.fetchJson('/jobs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body)
    });
    const job = created.job || created;
    st.jobId = job.id;
    st.jobStatus = job.status;
    st.spendUsd = job.spend_usd_approx || 0;
    st.round = job.rounds || 0;
    st.artifacts = job.artifacts || [];
    st.statusLine = 'Worker job ' + job.id + ' · ' + (job.status || 'queued');
    st.stepId = 'build';
    return job;
  };

  Shop.pollJob = async function (jobId) {
    return Shop.fetchJson('/jobs/' + encodeURIComponent(jobId));
  };

  Shop.resumeJob = async function (jobId, answer) {
    return Shop.fetchJson('/jobs/' + encodeURIComponent(jobId) + '/resume', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ answer: answer, async: true })
    });
  };

  Shop.artifactUrl = function (jobId, name) {
    return Shop.jobsUrl('/jobs/' + encodeURIComponent(jobId) + '/artifacts/' + encodeURIComponent(name));
  };

  Shop.fetchArtifactJson = async function (jobId, name) {
    const r = await fetch(Shop.artifactUrl(jobId, name), { cache: 'no-store' });
    if (!r.ok) throw new Error('artifact ' + name + ' HTTP ' + r.status);
    return r.json();
  };

  Shop.applyJobSnapshot = function (job) {
    if (!job) return;
    const st = Shop.state;
    st.jobId = job.id || st.jobId;
    st.jobStatus = job.status;
    st.spendUsd = Number(job.spend_usd_approx || 0);
    st.round = Number(job.rounds || 0);
    st.artifacts = job.artifacts || [];
    st.pendingQuestion = job.pending_question || null;
    if (job.status === 'needs_user') {
      st.stepId = 'adjust';
      st.statusLine = (st.pendingQuestion && st.pendingQuestion.question) || 'Waiting for your answer…';
      st.scopeTier = 'ask';
    } else if (job.status === 'running' || job.status === 'queued') {
      st.stepId = st.round > 1 ? 'check' : 'build';
      st.statusLine = 'Worker ' + job.status + (st.round ? ' · round ' + st.round : '');
    } else if (job.status === 'succeeded') {
      st.stepId = 'lists';
      st.statusLine = 'Build finished — loading lists…';
    } else if (job.status === 'failed') {
      st.statusLine = 'Failed: ' + (job.error || 'unknown');
    }
    /* Mirror tool log into AI log strings for Check timeline */
    if (Array.isArray(job.log) && job.log.length) {
      const lines = job.log.slice(-30).map(e => {
        if (typeof e === 'string') return e;
        const tool = e.tool || e.name || 'step';
        const ok = e.result && e.result.ok === false ? '✗' : '·';
        return ok + ' ' + tool + (e.result && e.result.error ? ': ' + e.result.error : '');
      });
      return lines;
    }
    return null;
  };

  Shop.loadJobProducts = async function (jobId) {
    const arts = Shop.state.artifacts || [];
    const names = arts.map(a => a.name || a);
    let lists = null, parts = null;
    if (names.indexOf('lists.json') >= 0) {
      try { lists = await Shop.fetchArtifactJson(jobId, 'lists.json'); } catch (e) { /* optional */ }
    }
    const partsName = names.find(n => /\.parts\.json$/i.test(n));
    if (partsName) {
      try { parts = await Shop.fetchArtifactJson(jobId, partsName); } catch (e) { /* optional */ }
    }
    Shop.state.lists = lists;
    Shop.state.parts = parts;
    return { lists, parts, artifacts: arts };
  };

  /** Convert worker PartRecords into a simple solid-box SPEC for the browser viewer. */
  Shop.partsToSpec = function (partsDoc, meta) {
    meta = meta || {};
    const rows = (partsDoc && partsDoc.parts) || (Array.isArray(partsDoc) ? partsDoc : []);
    const parts = [];
    let x = 0;
    rows.forEach((p, i) => {
      const T = Math.max(1, +p.thickness_mm || 20);
      const W = Math.max(1, +p.width_mm || 50);
      const L = Math.max(1, +p.length_mm || 100);
      const id = String(p.id || ('p' + i)).replace(/[^a-zA-Z0-9_]/g, '_');
      const qty = Math.max(1, +p.qty || 1);
      const mat = /oak|walnut|maple|cherry|ash|birch|pine|poplar/i.test(p.material || '')
        ? String(p.material).toLowerCase().split(/[^a-z]/)[0]
        : 'oak';
      parts.push({
        id: id,
        name: p.name || id,
        group: 'case',
        material: mat,
        kind: 'solid',
        grain: p.grain === 'x' || p.grain === 'y' || p.grain === 'z' ? p.grain : 'z',
        qty: qty,
        ops: [{ add: [0, 0, 0, L, W, T] }],
        instances: Array.from({ length: qty }, (_, n) => ({ at: [x, n * (W + 10), 0] })),
        notes: p.curved ? ['Shaped from blank — listed size is stock'] : (p.notes ? [String(p.notes)] : [])
      });
      x += L + 20;
    });
    return {
      name: meta.name || (partsDoc && partsDoc.meta && partsDoc.meta.name) || 'Shop build',
      units: 'mm',
      description: meta.description || 'Built by shop-grade worker from photo. Box preview of blanks — download STEP/STL from Ship for exact solids.',
      assumptions: Shop.state.assumptions || [],
      params: {},
      groups: [{ id: 'case', name: 'Parts' }],
      steps: [{ title: 'Worker assembly', parts: parts.map(p => p.id) }],
      parts: parts,
      __shopJobId: Shop.state.jobId,
      __ai: true,
      __trusted: true
    };
  };

  Shop.multiPhotoReviewHtml = function () {
    const photos = Shop.state.photos || [];
    if (photos.length < 2) return '';
    return `<div class="shopMultiPhoto"><h3>Photos</h3><div class="shopPhotoRow">${photos.map((p, i) =>
      `<button type="button" class="shopPhotoChip" data-photo="${i}"><img src="${p.url}" alt=""><span>${esc(p.role || 'photo')}</span></button>`
    ).join('')}</div></div>`;
  };

  CAD.shop = Shop;
})(typeof window !== 'undefined' ? window : globalThis);
