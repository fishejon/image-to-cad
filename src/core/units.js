/* Display units: the engine stays in millimetres; everything shown to a person is inches, snapped to 1/16". */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
CAD.MM_PER_IN = 25.4;
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
})(typeof globalThis !== 'undefined' ? globalThis : window);
