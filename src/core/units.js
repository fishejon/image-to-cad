/* Display units: the engine stays in millimetres; everything shown to a person is inches (1/16") and pounds. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
CAD.MM_PER_IN = 25.4;
CAD.LB_PER_KG = 2.2046226218;
CAD.toSixteenth = function (mm) { return Math.round((+mm || 0) / CAD.MM_PER_IN * 16); };
CAD.fmtInch = function (mm) {
  const neg = mm < 0, n = Math.abs(CAD.toSixteenth(mm));
  let whole = Math.floor(n / 16), frac = n % 16, a = frac, b = 16;
  while (b) { const t = a % b; a = b; b = t; }
  let s = '';
  if (whole) s += whole;
  if (frac) s += (s ? ' ' : '') + (frac / a) + '/' + (16 / a);
  if (!s) s = '0';
  return (neg ? '−' : '') + s + '"';
};
CAD.fmtInch3 = function (arr) { return (arr || []).map(CAD.fmtInch).join(' × '); };
CAD.fmtLb = function (kg, d) {
  const n = (+kg || 0) * CAD.LB_PER_KG;
  return n.toLocaleString('en-US', { maximumFractionDigits: d === undefined ? 1 : d, minimumFractionDigits: d === undefined ? 1 : d }) + ' lb';
};
/* Rewrite millimetre amounts in free text (cut-list notes, part specs) as inch fractions. */
CAD.inchifyText = function (s) {
  if (s == null || s === '') return '';
  let t = String(s);
  const num = '(\\d+(?:\\.\\d+)?)';
  t = t.replace(new RegExp(num + '\\s*[×x]\\s*' + num + '\\s*[×x]\\s*' + num + '\\s*mm\\b', 'gi'), (_, a, b, c) => CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b) + ' × ' + CAD.fmtInch(+c));
  t = t.replace(new RegExp(num + '\\s*[×x]\\s*' + num + '\\s*mm\\b', 'gi'), (_, a, b) => CAD.fmtInch(+a) + ' × ' + CAD.fmtInch(+b));
  t = t.replace(new RegExp(num + '\\s*mm\\b', 'gi'), (_, a) => CAD.fmtInch(+a));
  return t;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
