/* New numbers for examples and problems on the website.
   Every .ee-item block carries data-id; its template comes from assets/bank/chNN.json,
   the same bank that produced the printed book. Needs ee-engine.js, marked and KaTeX. */
(function () {
  const here = document.currentScript.src.replace(/[^/]*$/, '');
  const banks = {};
  const LETTERS = ['أ', 'ب', 'ج', 'د', 'هـ'];

  function loadBank(ch) {
    if (!banks[ch]) {
      banks[ch] = fetch(here + 'bank/' + ch + '.json')
        .then((r) => (r.ok ? r.json() : []))
        .then((list) => Object.fromEntries(list.map((it) => [it.id, it])))
        .catch(() => ({}));
    }
    return banks[ch];
  }

  // Markdown with display math: math goes through KaTeX as MathML, the rest through marked.
  function md(text) {
    const math = [];
    const src = text.replace(/\$\$([\s\S]+?)\$\$/g, (m, tex) => {
      math.push('<div class="ee-math">' + katex.renderToString(tex.trim(), { displayMode: true, output: 'mathml', throwOnError: false }) + '</div>');
      return '\n\n@@MATH' + (math.length - 1) + '@@\n\n';
    });
    let html = marked.parse(src, { gfm: true });
    html = html.replace(/<p>@@MATH(\d+)@@<\/p>/g, (m, k) => math[Number(k)]);
    return html;
  }

  function statement(it, env) {
    let s = EE.render(it.text.trim(), env);
    if (it.kind === 'mcq') s += '\n\n' + it.options.map((o, k) => LETTERS[k] + ') ' + EE.render(o, env)).join('\\\n');
    return s;
  }

  function solution(it, env) {
    const s = EE.render(it.solution.trim(), env);
    return it.kind === 'mcq' ? 'الجواب (' + LETTERS[it.correct] + '). ' + s : s;
  }

  function figure(it, env) {
    if (!it.diagram) return '';
    return '<div class="ee-fig">' + EE.diagramSvg(it.diagram, env) + '</div>';
  }

  function build(box, it) {
    const original = box.innerHTML;
    const kind = box.dataset.kind;
    const label = box.dataset.label;
    const bar = document.createElement('div');
    bar.className = 'ee-bar';
    const bNew = button('أرقام جديدة', 'ee-new');
    const bOrig = button('الأرقام الأصلية', 'ee-orig');
    bOrig.hidden = true;
    bar.append(bNew, bOrig);
    const body = document.createElement('div');
    body.className = 'ee-body';
    body.innerHTML = original;
    box.innerHTML = '';
    box.append(bar, body);

    bNew.addEventListener('click', () => {
      let env, tries = 0;
      do { env = EE.compute(it, EE.draw(it, Math.random)); tries++; }
      while (!Object.values(env).every((v) => typeof v !== 'number' || Number.isFinite(v)) && tries < 20);
      let html;
      if (kind === 'example') {
        const title = it.title ? ': ' + EE.render(it.title, env) : '';
        html = md('**مثال ' + label + title + '**\n\n' + statement(it, env)) + figure(it, env) +
               md('**الحل:**\n\n' + solution(it, env));
      } else {
        html = md('**' + label + '** ' + statement(it, env)) + figure(it, env) +
               '<details class="ee-sol"><summary>الحل بهذه الأرقام</summary>' + md(solution(it, env)) + '</details>';
      }
      body.innerHTML = html;
      body.classList.add('ee-random');
      bOrig.hidden = false;
    });
    bOrig.addEventListener('click', () => {
      body.innerHTML = original;
      body.classList.remove('ee-random');
      bOrig.hidden = true;
    });
  }

  function button(text, cls) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ee-btn ' + cls;
    b.textContent = text;
    return b;
  }

  document.addEventListener('ee-ready', () => {
    document.querySelectorAll('.ee-item[data-id]').forEach(async (box) => {
      const ch = 'ch' + box.dataset.id.slice(1, 3);
      const bank = await loadBank(ch);
      const it = bank[box.dataset.id];
      if (it) build(box, it);
    });
  });
})();
