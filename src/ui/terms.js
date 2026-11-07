/* Shop-grade UI vocabulary (docs/plans/ui-ux-shop-grade.md §1, §11). */
(function (g) {
  const TERMS = {
    blank: 'The rectangular piece of stock a part is cut from',
    shaped_from_blank: 'The finished part is curved or carved, so the listed size is the blank',
    estimate: 'The size comes from proportions, not a known measurement',
    measured: 'The size follows from a size you gave',
    waste_allowance: 'Extra material added to cover cuts and mistakes',
    board_feet: 'Volume of lumber, thickness × width × length in inches ÷ 144',
    guessed: 'Hidden or unclear in the photo'
  };
  const STATUS = {
    measured: { label: 'Measured', title: TERMS.measured },
    estimated: { label: 'Estimated', title: TERMS.estimate },
    guessed: { label: 'Guessed', title: TERMS.guessed },
    good: { label: 'Good', title: 'Looks right against the photo' },
    close: { label: 'Close', title: 'Near match — check sizes' },
    check: { label: 'Check this', title: 'Needs a closer look' },
    shaped: { label: 'Shaped from blank', title: TERMS.shaped_from_blank }
  };
  function statusBadge(key) {
    const s = STATUS[key] || { label: key, title: '' };
    return '<span class="statusBadge" data-st="' + key + '" title="' + String(s.title).replace(/"/g, '&quot;') + '">' + s.label + '</span>';
  }
  g.CAD = g.CAD || {};
  g.CAD.uiTerms = { TERMS, STATUS, statusBadge };
})(typeof window !== 'undefined' ? window : globalThis);
