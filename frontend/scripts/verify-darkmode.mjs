/**
 * Auditoría del modo oscuro. Comprueba, en todos los .jsx de src/:
 *   1. que no queden variantes `dark:` pegadas al token anterior;
 *   2. que toda clase base de MAP tenga su variante `dark:`;
 *   3. que no haya variantes `dark:` duplicadas.
 *
 * Uso: node scripts/verify-darkmode.mjs
 */
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';

const codemod = readFileSync(new URL('./darkmode-codemod.mjs', import.meta.url), 'utf8');
const MAP = eval(
  '(' +
    codemod.slice(
      codemod.indexOf('{', codemod.indexOf('const MAP')),
      codemod.indexOf('};', codemod.indexOf('const MAP')) + 1
    ) +
    ')'
);

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else if (e.name.endsWith('.jsx')) out.push(p);
  }
  return out;
}

const glued = new Set();
const missing = new Set();
const duplicated = new Set();
let pairs = 0;

for (const f of walk(new URL('../src/', import.meta.url).pathname)) {
  const src = readFileSync(f, 'utf8');
  const rel = f.replace(/.*\/src\//, 'src/');

  // 1) Pegados: carácter alfanumérico justo antes de `dark:`
  for (const m of src.matchAll(/([a-zA-Z0-9/\]])(dark:[a-z-]+)/g)) {
    glued.add(`${rel}  ::  ...${m[0]}...`);
  }

  // Normaliza a tokens sueltos para las comprobaciones 2 y 3.
  const tokens = src.replace(/[{}'"`]/g, ' ').split(/\s+/).filter(Boolean);

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    // 2) Clase base sin su variante
    if (MAP[t]) {
      // busca el siguiente token no vacío
      let j = i + 1;
      while (j < tokens.length && !tokens[j]) j++;
      if (tokens[j] === MAP[t]) pairs++;
      else missing.add(`${rel}  ::  ${t}`);
    }
    // 3) Variante dark repetida
    if (t.startsWith('dark:') && tokens[i + 1] === t) {
      duplicated.add(`${rel}  ::  ${t}`);
    }
  }
}

console.log(`pares base+dark correctos : ${pairs}`);
console.log(`variantes pegadas         : ${glued.size}`);
console.log(`clases base SIN dark      : ${missing.size}`);
console.log(`variantes dark duplicadas : ${duplicated.size}`);
for (const [label, set] of [
  ['PEGADAS', glued],
  ['SIN DARK', missing],
  ['DUPLICADAS', duplicated],
]) {
  if (!set.size) continue;
  console.log(`\n--- ${label} ---`);
  [...set].forEach((x) => console.log('  - ' + x));
}
