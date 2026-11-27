// Render every bank item with the JavaScript engine and compare with the Python engine.
// Usage: python3 tools/dump_py.py > /tmp/py.json && node tools/check_js.mjs /tmp/py.json
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const EE = require('../assets/ee-engine.js');

const py = JSON.parse(readFileSync(process.argv[2], 'utf8'));
let bad = 0;
for (const rec of py) {
  const env = EE.compute(rec.item, rec.values);
  for (const field of ['text', 'text_en', 'solution', 'answer']) {
    if (!rec.item[field]) continue;
    const js = EE.render(rec.item[field], env);
    if (js !== rec.out[field]) {
      bad++;
      const a = js.split('\n'), b = rec.out[field].split('\n');
      const k = a.findIndex((l, j) => l !== b[j]);
      console.log(`MISMATCH ${rec.item.id} [${rec.tag}] ${field}\n  js: ${a[k]}\n  py: ${b[k]}`);
    }
  }
  if (rec.item.diagram) {
    const js = EE.diagramSvg(rec.item.diagram, env);
    if (js !== rec.out.diagram) { bad++; console.log(`MISMATCH ${rec.item.id} [${rec.tag}] diagram`); }
  }
}
console.log(`${py.length} renders checked, ${bad} mismatches`);
process.exit(bad ? 1 : 0);
