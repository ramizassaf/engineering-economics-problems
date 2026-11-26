/* JavaScript twin of ee/engine.py. Keep the two in step:
   tools/check_js.mjs renders every bank item with both and compares. */
(function (root) {
  const FP = (i, n) => Math.pow(1 + i, n);
  const PF = (i, n) => Math.pow(1 + i, -n);
  const PA = (i, n) => (i === 0 ? n : (Math.pow(1 + i, n) - 1) / (i * Math.pow(1 + i, n)));
  const AP = (i, n) => 1 / PA(i, n);
  const FA = (i, n) => (i === 0 ? n : (Math.pow(1 + i, n) - 1) / i);
  const AF = (i, n) => 1 / FA(i, n);
  const PG = (i, n) => (Math.pow(1 + i, n) - i * n - 1) / (i * i * Math.pow(1 + i, n));
  const AG = (i, n) => 1 / i - n / (Math.pow(1 + i, n) - 1);
  const PGEO = (g, i, n) => (Math.abs(i - g) < 1e-12 ? n / (1 + i) : (1 - Math.pow((1 + g) / (1 + i), n)) / (i - g));
  const RATE = (n, A, P) => {
    let lo = 1e-9, hi = 1.0;
    for (let k = 0; k < 100; k++) {
      const mid = (lo + hi) / 2;
      if (A * PA(mid, n) > P) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  };
  const RATEF = (n, A, F) => {
    let lo = 1e-9, hi = 1.0;
    for (let k = 0; k < 100; k++) {
      const mid = (lo + hi) / 2;
      if (A * FA(mid, n) < F) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  };
  const GROWTH = (A1, P, i, n) => {
    let lo = -0.5, hi = 1.0;
    for (let k = 0; k < 100; k++) {
      const mid = (lo + hi) / 2;
      if (A1 * PGEO(mid, i, n) < P) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  };
  const r4 = (x) => Number(x.toFixed(4));
  const r2 = (x) => Number(x.toFixed(2));
  const HELPERS = {
    FP, PF, PA, AP, FA, AF, PG, AG, PGEO, RATE, RATEF, GROWTH, r4, r2,
    ln: Math.log, abs: Math.abs, max: Math.max, min: Math.min,
    floor: Math.floor, ceil: Math.ceil,
    pick: (c, a, b) => (c ? a : b),
    yrs: (n) => { n = Math.round(n); return n === 1 ? 'سنة واحدة' : n === 2 ? 'سنتين' : (n >= 3 && n <= 10 ? n + ' سنوات' : n + ' سنة'); },
  };

  function ev(expr, env) {
    const scope = Object.assign({}, HELPERS, env);
    const names = Object.keys(scope);
    // Python-only spellings are not allowed in the bank; ** works in both.
    const fn = new Function(...names, '"use strict"; return (' + expr + ');');
    return fn(...names.map((k) => scope[k]));
  }

  function compute(item, values) {
    const env = Object.assign({}, item.vars || {}, values || {});
    for (const line of item.calc || []) {
      const k = line.indexOf('=');
      env[line.slice(0, k).trim()] = ev(line.slice(k + 1).trim(), env);
    }
    return env;
  }

  function group(s) {
    let out = '';
    while (s.length > 3) { out = ',' + s.slice(-3) + out; s = s.slice(0, -3); }
    return s + out;
  }

  function fnum(x, d) {
    const neg = x < 0;
    x = Math.abs(x);
    let s = (Math.floor(x * Math.pow(10, d) + 0.5 + 1e-9) / Math.pow(10, d)).toFixed(d);
    if (s.includes('.')) { const [a, b] = s.split('.'); s = group(a) + '.' + b; }
    else s = group(s);
    if (neg && Number(s.replace(/,/g, '')) !== 0) s = '-' + s;
    return s;
  }

  function fmt(v, f) {
    if (typeof v === 'string') return v;
    if (!f) f = '2';
    if (f === '%') {
      let s = fnum(v * 100, 2);
      if (s.includes('.')) s = s.replace(/0+$/, '').replace(/\.$/, '');
      return s + '%';
    }
    if (f === '%2') return fnum(v * 100, 2) + '%';
    if (f === 'r') return Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : String(v);
    if (f === 'd2') return v >= 0 ? (Math.floor(v * 100 + 0.5 + 1e-9) / 100).toFixed(2) : '-' + fmt(-v, 'd2');
    if (f === 'n') return String(Math.round(v));
    if (f === 'f4') return v >= 0 ? (Math.floor(v * 1e4 + 0.5 + 1e-9) / 1e4).toFixed(4) : '-' + fmt(-v, 'f4');
    if (f === 'g') return Math.abs(v - Math.round(v)) < 1e-9 ? fnum(v, 0) : fnum(v, 2);
    if (/^\d+$/.test(f)) return fnum(v, Number(f));
    throw new Error('unknown format ' + f);
  }

  function mathCommas(text) {
    return text.replace(/\$\$([\s\S]+?)\$\$/g, (m, body) => '$$' + body.replace(/(\d),(?=\d)/g, '$1\\mathord{,}').replace(/(^|[^\\])%/g, '$1\\%') + '$$');
  }

  function render(tpl, env) {
    if (!tpl) return '';
    const out = tpl.replace(/\[\[(.+?)(?:\|([^\]]*))?\]\]/g, (m, e, f) => fmt(ev(e, env), f || ''));
    return mathCommas(out);
  }

  const c1 = (v) => (Math.floor(v * 10 + 0.5) / 10).toFixed(1);
  function svgDraw(n, flows, rateLabel) {
    const W = 640, H = 250, L = 50, R = 570, ax = 125;
    const step = (R - L) / Math.max(n, 1);
    const big = Math.max(1, ...flows.map((f) => Math.abs(f[1])));
    const p = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="DejaVu Sans, Arial, sans-serif" font-size="13">`,
      `<line x1="${L - 15}" y1="${ax}" x2="${R + 15}" y2="${ax}" stroke="#444" stroke-width="1.5"/>`];
    for (let k = 0; k <= n; k++) {
      const x = L + k * step;
      p.push(`<line x1="${c1(x)}" y1="${ax - 5}" x2="${c1(x)}" y2="${ax + 5}" stroke="#444"/>`);
      p.push(`<text x="${c1(x + 4)}" y="${ax + 18}" fill="#555" font-size="12">${k}</text>`);
    }
    if (rateLabel) p.push(`<text x="${R + 15}" y="16" text-anchor="end" fill="#222">${rateLabel}</text>`);
    for (const [t, a, lab] of flows) {
      const x = L + t * step, h = 30 + 50 * Math.abs(a) / big, up = a > 0;
      const y2 = up ? ax - h : ax + h, col = up ? '#1b6e3a' : '#1f4e8c', tip = up ? 8 : -8;
      p.push(`<line x1="${c1(x)}" y1="${ax}" x2="${c1(x)}" y2="${c1(y2 + tip)}" stroke="${col}" stroke-width="2.2"/>`);
      p.push(`<path d="M${c1(x - 5)} ${c1(y2 + tip)} L${c1(x + 5)} ${c1(y2 + tip)} L${c1(x)} ${c1(y2)} Z" fill="${col}"/>`);
      const ty = up ? y2 - 6 : y2 + 16;
      p.push(`<text x="${c1(x)}" y="${c1(ty)}" text-anchor="middle" fill="#111" font-weight="bold">${lab}</text>`);
    }
    p.push('</svg>');
    return p.join('');
  }

  function diagramSvg(spec, env) {
    const n = Math.round(ev(String(spec.n), env));
    const flows = (spec.flows || []).map((f) => {
      const t = ev(String(f[0]), env), a = ev(String(f[1]), env);
      return [t, a, f.length > 2 ? render(f[2], env) : fmt(Math.abs(a), 'g')];
    });
    for (const s of spec.series || []) {
      const t1 = Math.round(ev(String(s[0]), env)), t2 = Math.round(ev(String(s[1]), env));
      for (let t = t1; t <= t2; t++) {
        const e2 = Object.assign({}, env, { t });
        const a = ev(String(s[2]), e2);
        let lab;
        if (s.length > 3) lab = render(s[3], e2);
        else if ((t2 - t1 + 1 > 8 || n > 10) && t !== t1 && t !== t2) lab = '';
        else lab = fmt(Math.abs(a), 'g');
        flows.push([t, a, lab]);
      }
    }
    return svgDraw(n, flows, spec.i ? render(spec.i, env) : '');
  }

  function draw(item, rnd) {
    const vals = {};
    for (const [k, [lo, hi, st]] of Object.entries(item.random || {})) {
      const steps = Math.round((hi - lo) / st);
      vals[k] = Number((lo + st * Math.floor(rnd() * (steps + 1))).toFixed(10));
    }
    return vals;
  }

  const EE = { ev, compute, fmt, fnum, render, mathCommas, diagramSvg, svgDraw, draw };
  if (typeof module !== 'undefined' && module.exports) module.exports = EE;
  else root.EE = EE;
})(typeof window !== 'undefined' ? window : globalThis);
