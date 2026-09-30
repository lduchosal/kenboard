const test = require('node:test');
const assert = require('node:assert/strict');
const { escapeHtml, inlineJson, detailHtml } = require('../src/detail');

const task = {
  id: 7,
  title: 'A <b>&</b> "q"',
  status: 'doing',
  who: 'Claude',
  due_date: null,
  description: '# t\n</script><script>x',
};
const args = {
  task,
  url: 'https://kb/cat/c.html#ID-7',
  cspSource: 'vscode-res:',
  nonce: 'N0NCE',
  iconUri: 'vscode-res:/icon.png',
  scriptUris: ['m.js', 'p.js', 'r.js'],
};

test('escapeHtml', () => {
  assert.equal(
    escapeHtml(`<a href="x">'&'</a>`),
    '&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;',
  );
});

test('inlineJson cannot close the script element', () => {
  const out = inlineJson('</script>&');
  assert.doesNotMatch(out, /<|>|&/);
  assert.equal(JSON.parse(out), '</script>&');
});

test('detailHtml: escaped title, meta, icon above button, nonce scripts, markdown source', () => {
  const html = detailHtml(args);
  assert.match(html, /A &lt;b&gt;&amp;&lt;\/b&gt; &quot;q&quot;/);
  assert.match(
    html,
    /<span class="fullscreen-id">#7<\/span>\s*<span class="fullscreen-status">doing<\/span>/,
  );
  assert.match(
    html,
    /<div class="task-avatar">C<\/div>\s*<span style="font-weight:600">Claude<\/span>/,
  );
  assert.match(
    html,
    /<img src="vscode-res:\/icon.png" alt="kenboard">\s*<a class="btn" href="https:\/\/kb\/cat\/c.html#ID-7">Ouvrir sur kenboard<\/a>/,
  );
  assert.match(html, /script-src 'nonce-N0NCE'/);
  assert.match(
    html,
    /<script nonce="N0NCE" src="m.js"><\/script>\n<script nonce="N0NCE" src="p.js">/,
  );
  assert.doesNotMatch(html, /<\/script><script>x/);
  assert.match(html, /id="md">"# t\\n\\u003c\/script\\u003e/);
});

test('detailHtml: empty description placeholder', () => {
  const html = detailHtml({ ...args, task: { ...task, description: '' } });
  assert.match(html, /pas de description/);
});
