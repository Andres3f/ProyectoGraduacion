/**
 * Codemod de modo oscuro: añade la variante `dark:` a las clases de color.
 *
 * Solo se transforman los tokens listados en MAP; todo lo demás queda intacto.
 * Es idempotente: si la variante `dark:` ya está, no la duplica.
 *
 * Uso:  node scripts/darkmode-codemod.mjs
 */
import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join } from 'path';

const MAP = {
  // ── Texto ────────────────────────────────────────────────────
  'text-gray-900': 'dark:text-gray-100',
  'text-gray-800': 'dark:text-gray-100',
  'text-gray-700': 'dark:text-gray-200',
  'text-gray-600': 'dark:text-gray-300',
  'text-gray-500': 'dark:text-gray-400',
  'text-gray-400': 'dark:text-gray-500',
  'text-gray-300': 'dark:text-gray-600',
  'text-brand-700': 'dark:text-brand-300',
  'text-brand-600': 'dark:text-brand-400',
  'text-red-700': 'dark:text-red-400',
  'text-red-600': 'dark:text-red-400',
  'text-red-500': 'dark:text-red-400',
  'text-yellow-800': 'dark:text-yellow-300',
  'text-green-700': 'dark:text-green-400',
  'text-green-600': 'dark:text-green-400',
  'text-amber-900': 'dark:text-amber-200',
  'text-amber-600': 'dark:text-amber-300',
  'text-blue-700': 'dark:text-blue-400',
  'hover:text-gray-600': 'dark:hover:text-gray-300',
  'hover:text-gray-900': 'dark:hover:text-gray-100',
  'hover:text-red-700': 'dark:hover:text-red-300',

  // ── Fondos ───────────────────────────────────────────────────
  'bg-white': 'dark:bg-gray-800',
  'bg-white/95': 'dark:bg-gray-800/95',
  'bg-gray-50': 'dark:bg-gray-900',
  'bg-gray-100': 'dark:bg-gray-800',
  'bg-gray-200': 'dark:bg-gray-700',
  'bg-brand-50': 'dark:bg-gray-800',
  'bg-brand-50/50': 'dark:bg-gray-800/50',
  'bg-brand-100': 'dark:bg-brand-900',
  'bg-red-50': 'dark:bg-red-950',
  'bg-red-100': 'dark:bg-red-900',
  'bg-green-50': 'dark:bg-green-950',
  'bg-green-100': 'dark:bg-green-900',
  'bg-yellow-50': 'dark:bg-yellow-950',
  'bg-amber-50': 'dark:bg-amber-950',
  'bg-blue-50': 'dark:bg-blue-950',
  'hover:bg-gray-50': 'dark:hover:bg-gray-700',
  'hover:bg-gray-100': 'dark:hover:bg-gray-700',
  'hover:bg-gray-200': 'dark:hover:bg-gray-600',
  'hover:bg-gray-700': 'dark:hover:bg-gray-600',
  'hover:bg-brand-100': 'dark:hover:bg-brand-900',
  'hover:bg-brand-700': 'dark:hover:bg-brand-500',
  'hover:bg-red-600': 'dark:hover:bg-red-500',
  'hover:bg-red-700': 'dark:hover:bg-red-500',
  'hover:bg-green-700': 'dark:hover:bg-green-500',
  'hover:bg-emerald-700': 'dark:hover:bg-emerald-500',

  // ── Bordes y divisores ───────────────────────────────────────
  'border-gray-100': 'dark:border-gray-700',
  'border-gray-200': 'dark:border-gray-700',
  'border-gray-300': 'dark:border-gray-600',
  'border-gray-700': 'dark:border-gray-600',
  'border-amber-200': 'dark:border-amber-800',
  'divide-gray-100': 'dark:divide-gray-700',
};

// Un token de clase completo: variantes opcionales + propiedad + color + tono.
// `white` y `black` no llevan tono numérico; el resto de colores sí.
const CLASS_TOKEN =
  /(?:[a-z-]+:)*(?:bg|text|border|divide)-(?:(?:white|black)|(?:brand|cement|red|green|blue|yellow|amber|emerald|slate|zinc|neutral|stone|gray)-\d{2,3})(?:\/\d{1,3})?/g;

// Bloques de estilo: className="...", className={`...`}, className={...}
const CLASSNAME_BLOCK = /className=(?:"[^"]*"|\{`[^`]*`\}|\{(?:[^{}]|\{[^{}]*\})*\})/g;

// 1) Reparación: separa variantes `dark:` que quedaron pegadas al token previo
//    (p. ej. "bg-whitedark:bg-gray-800" -> "bg-white dark:bg-gray-800").
function repairGlued(src) {
  return src.replace(/([a-zA-Z0-9/\]])(dark:[a-z-]+)/g, '$1 $2');
}

// 2) Inserta la variante `dark:` tras cada clase base que la necesite.
function addDarkVariants(src) {
  return src.replace(CLASSNAME_BLOCK, (block) =>
    block.replace(CLASS_TOKEN, (cls, offset, whole) => {
      const dark = MAP[cls];
      if (!dark) return cls;
      // Idempotencia: si la variante ya sigue al token, no la duplicamos.
      const after = whole.slice(offset + cls.length);
      if (new RegExp('^\\s*' + dark.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(after)) {
        return cls;
      }
      return cls + ' ' + dark;
    })
  );
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

const root = new URL('../src/', import.meta.url).pathname;
let repaired = 0;
let changed = 0;
for (const f of walk(root)) {
  const src = readFileSync(f, 'utf8');
  const fixed = addDarkVariants(repairGlued(src));
  if (fixed === src) continue;
  writeFileSync(f, fixed);
  changed++;
  console.log('  ✓ ' + f.replace(root, ''));
}
console.log(`\n${changed} archivo(s) modificados.`);
