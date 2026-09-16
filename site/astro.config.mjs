// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  site: 'https://siliconvalueindex.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
  vite: {
    // The pipeline writes ../data/site/*.json; allow the dev server to read it.
    server: { fs: { allow: ['..'] } },
  },
});
