// Run the factor cases written by tools/test_factors.py on the JavaScript engine.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const EE = require('../assets/ee-engine.js');

const cases = JSON.parse(readFileSync(process.argv[2] || '/tmp/ee-factor-cases.json', 'utf8'));
let bad = 0, n = 0;
for (const c of cases) {
  if (c.f === 'raises') continue;
  const args = c.args.map((a) => JSON.stringify(a)).join(', ');
  const got = EE.ev(`${c.f}(${args})`, {});
  const err = Math.abs(got - c.want);
  if (!(err <= Math.max(1e-12, c.tol * Math.abs(c.want)))) {
    bad++;
    console.log(`JS ${c.f}(${args}) = ${got}, want ${c.want}`);
  }
  n++;
}
const mustThrow = [
  'RATE(5, -100, 10000)', 'IRR([1000, 500, 500])', 'IRR([-1000, 3000, -2200], -0.5, 1.0)',
  'PA(-1, 5)', 'PA(0.1, -2)',
];
for (const e of mustThrow) {
  try { EE.ev(e, {}); bad++; console.log(`JS ${e} returned a value instead of throwing`); } catch (err) { /* expected */ }
}
if (bad) { console.log(`${bad} JavaScript factor tests failed`); process.exit(1); }
console.log(`${n} factor cases match in JavaScript; bad inputs throw`);
