/**
 * Transform INVERSO del codemod de modo oscuro: quita las variantes `dark:`
 * que el codemod insertó, reconstruyendo el estado previo al modo oscuro.
 *
 * Se usa para preparar el commit del trabajo previo (features) separado del
 * commit de modo oscuro, en archivos donde ambos cambios conviven.
 *
 * Uso: node scripts/undarkmode-codemod.mjs [--check]
 *   --check  no escribe: solo informa qué archivos quedarían sin cambios
 *            respecto a HEAD (es decir, los que son 100% modo oscuro).
 */
import { readFileSync, writeFileSync, readdirSync } from 'fs';
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

// Patrones "base dark:base" -> "base". Se ordenan del más largo al más corto
// para que una clave que sea prefijo de otra no se replacement incorrecto.
const PAIRS = Object.entries(MAP).sort((a, b) => b[0].length - a[0].length);

function esc(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function removeDark(src) {
  let out = src;
  for (const [base, dark] of PAIRS) {
    // Variante con separador de un espacio (lo que insertó el codemod).
    out = out.replaceAll(`${base} ${dark}`, base);
    // Variante pegada (estado intermedio corrupto que reparó el codemod).
    out = out.replaceAll(`${base.replace(/^(.*?)\b/g, '$1')}${dark}`, base);
  }
  return out;
}

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else if (e.name.endsWith('.jsx')) out.push(p);
  }
  return out;
}

const check = process.argv.includes('--check');
const root = new URL('../src/', import.meta.url).pathname;
for (const f of walk(root)) {
  const src = readFileSync(f, 'utf8');
  const out = removeDark(src);
  if (out === src) continue;
  if (!check) writeFileSync(f, out);
  console.log((check ? '  ? ' : '  ↩ ') + f.replace(root, ''));
}
