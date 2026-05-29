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
    include: [
      'src/dashboard/static/js/**/*.test.js',
      // #520 (annotations epic): the extension's content-script pure
      // helpers (e.g. buildMarkdown) live alongside their source under
      // ``extension/content/`` and use the same vitest harness. The
      // bundle itself is excluded from coverage like the rest of
      // ``extension/`` (it is shipped as a release zip, not part of the
      // Vite-bundled frontend).
      'extension/content/**/*.test.js',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: 'coverage',
      include: ['src/dashboard/static/js/**/*.js'],
      // Test files, the entry that just wires globals, and the bundle
      // output don't need coverage themselves.
      exclude: [
        'src/dashboard/static/js/**/*.test.js',
        'src/dashboard/static/js/main.js',
        'src/dashboard/static/dist/**',
      ],
    },
  },
});
