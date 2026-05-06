import { defineConfig } from 'vite';

// Single-bundle build for the kanban frontend. Source modules live under
// ``src/dashboard/static/js/``; output is one self-executing file at
// ``src/dashboard/static/dist/app.js`` that Flask serves directly. Format
// is ``iife`` so functions exposed on ``globalThis`` in main.js stay
// reachable by the inline ``onclick=""`` handlers in the Jinja templates.
export default defineConfig({
  build: {
    outDir: 'src/dashboard/static/dist',
    emptyOutDir: true,
    sourcemap: true,
    minify: 'esbuild',
    rollupOptions: {
      input: 'src/dashboard/static/js/main.js',
      output: {
        entryFileNames: 'app.js',
        format: 'iife',
        name: 'KenboardApp',
        // SortableJS, marked.js and DOMPurify are loaded as separate
        // <script> tags in base.html and used as window globals; treat
        // them as external so we don't try to bundle them in.
        globals: {
          sortablejs: 'Sortable',
          marked: 'marked',
          dompurify: 'DOMPurify',
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['src/dashboard/static/js/**/*.test.js'],
  },
});
