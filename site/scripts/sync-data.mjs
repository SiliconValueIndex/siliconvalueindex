// Copy the pipeline output into public/data so the JSON is downloadable from the site.
import { cpSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, '..', '..', 'data', 'site');
const dst = join(here, '..', 'public', 'data');
mkdirSync(dst, { recursive: true });
cpSync(src, dst, { recursive: true });
console.log(`synced ${src} -> ${dst}`);
