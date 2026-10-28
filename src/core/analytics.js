/* PostHog product analytics — loads only when /api/status returns a project key.
   Opt-out: localStorage image-to-cad.telemetry=0 (same flag as /api/events). No photos. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
const A = CAD.analytics = {
  ready: false,
  key: null,
  host: null,
  _q: []
};

A.DEVICE_LS = 'image-to-cad.device';
A.deviceId = function () {
  try {
    let id = localStorage.getItem(A.DEVICE_LS);
    if (!id) {
      id = 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(A.DEVICE_LS, id);
    }
    return id;
  } catch (e) { return 'anon'; }
};

/** Stable anonymous distinct_id — hash of device id (no PII). */
A.distinctId = function () {
  const s = A.deviceId();
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return 'ph_' + (h >>> 0).toString(16);
};

A.enabled = function () {
  return !!(CAD.store && CAD.store.telemetryEnabled ? CAD.store.telemetryEnabled() : true);
};

function injectSnippet(key, host) {
  const apiHost = host || 'https://us.i.posthog.com';
  const ph = root.posthog = root.posthog || [];
  if (ph.__SV) return Promise.resolve(ph);
  return new Promise(function (resolve, reject) {
    (function (t, e) {
      var o, n, p, r;
      e.__SV = 1;
      e._i = [];
      e.init = function (i, s, a) {
        function g(t, e) {
          var o = e.split('.');
          2 === o.length && (t = t[o[0]], e = o[1]);
          t[e] = function () { t.push([e].concat(Array.prototype.slice.call(arguments, 0))); };
        }
        (p = t.createElement('script')).type = 'text/javascript';
        p.crossOrigin = 'anonymous';
        p.async = true;
        p.src = s.api_host.replace('.i.posthog.com', '-assets.i.posthog.com') + '/static/array.js';
        p.onload = function () { resolve(e); };
        p.onerror = function () { reject(new Error('posthog script failed')); };
        (r = t.getElementsByTagName('script')[0]).parentNode.insertBefore(p, r);
        var u = e;
        for (void 0 !== a ? u = e[a] = [] : a = 'posthog', u.people = u.people || [], u.toString = function (t) {
          var e = 'posthog'; return 'posthog' !== a && (e += '.' + a), t || (e += ' (stub)'), e;
        }, u.people.toString = function () { return u.toString(1) + '.people (stub)'; },
          o = 'init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetOptInCapturing optOutCapturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing opt_in_capturing opt_out_capturing flags get_property getSessionProperty set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_session_id createPersonProfile'.split(' '),
          n = 0; n < o.length; n++) g(u, o[n]);
        e._i.push([i, s, a]);
      };
    })(document, ph);
    try {
      ph.init(key, {
        api_host: apiHost,
        person_profiles: 'identified_only',
        persistence: 'localStorage+cookie',
        capture_pageview: true,
        capture_pageleave: true,
        autocapture: false,
        disable_session_recording: true,
        loaded: function (instance) {
          try { instance.identify(A.distinctId()); } catch (e) { /* ignore */ }
        }
      });
    } catch (e) { reject(e); }
  });
}

A.init = async function () {
  if (!A.enabled() || typeof fetch !== 'function') return false;
  try {
    const r = await fetch('/api/status', { cache: 'no-store' });
    if (!r.ok) return false;
    const st = await r.json();
    const key = st.posthogKey || st.posthog_key || null;
    if (!key) return false;
    A.key = key;
    A.host = st.posthogHost || st.posthog_host || 'https://us.i.posthog.com';
    await injectSnippet(A.key, A.host);
    A.ready = true;
    while (A._q.length) {
      const item = A._q.shift();
      A.capture(item.name, item.props);
    }
    return true;
  } catch (e) { return false; }
};

A.capture = function (name, props) {
  if (!name) return;
  if (!A.enabled()) return;
  const payload = Object.assign({ domain: 'furniture' }, props || {});
  if (!A.ready || !root.posthog || typeof root.posthog.capture !== 'function') {
    A._q.push({ name: String(name), props: payload });
    return;
  }
  try { root.posthog.capture(String(name), payload); } catch (e) { /* ignore */ }
};

})(typeof globalThis !== 'undefined' ? globalThis : window);
