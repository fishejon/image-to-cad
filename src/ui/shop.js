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
    checklist: {}
  };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

  Shop.workerBase = function () {
    try { return (localStorage.getItem('image-to-cad.worker') || '').replace(/\/$/, ''); } catch (e) { return ''; }
  };

  Shop.setWorkerBase = function (url) {
    try { localStorage.setItem('image-to-cad.worker', url || ''); } catch (e) { /* ignore */ }
  };

  Shop.pingWorker = async function () {
    const base = Shop.workerBase();
    const via = base || '';
    try {
      if (via) {
        const r = await fetch(via + '/health');
        Shop.state.workerOnline = r.ok;
        return r.ok;
      }
      const r = await fetch('/api/jobs');
      if (r.status === 503) { Shop.state.workerOnline = false; return false; }
      Shop.state.workerOnline = r.ok || r.status === 200;
      return Shop.state.workerOnline;
    } catch (e) {
      Shop.state.workerOnline = false;
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
      <h3>Run mode</h3>
      <div class="shopModes">
        <label class="shopMode${st.mode === 'shop' ? ' on' : ''}"><input type="radio" name="shopMode" value="shop"${st.mode === 'shop' ? ' checked' : ''}> <b>Shop-grade</b><span>Real geometry + lists · several minutes · worker</span></label>
        <label class="shopMode${st.mode === 'classic' ? ' on' : ''}"><input type="radio" name="shopMode" value="classic"${st.mode === 'classic' ? ' checked' : ''}> <b>Classic</b><span>Faster simple shapes · current Create</span></label>
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

  CAD.shop = Shop;
})(typeof window !== 'undefined' ? window : globalThis);
