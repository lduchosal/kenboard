const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { parseKenFile, parseIniFile, resolveConfig, configProblem } = require('../src/config');

test('parseKenFile: key=value, comments, blank lines', () => {
  const data = parseKenFile('# token\napi_token = abc=def\n\nproject_id=p1\nnoequals\n');
  assert.deepEqual(data, { api_token: 'abc=def', project_id: 'p1' });
});

test('parseIniFile: only the [ken] section, both separators', () => {
  const text = '[other]\nproject_id = nope\n[ken]\n; c\nProject_ID = p1\nbase_url: https://b/\n';
  assert.deepEqual(parseIniFile(text), { project_id: 'p1', base_url: 'https://b/' });
});

test('resolveConfig: env > .ken > ken.ini, found upwards, trailing slash stripped', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kenvsc-'));
  const sub = path.join(root, 'a', 'b');
  fs.mkdirSync(sub, { recursive: true });
  fs.writeFileSync(
    path.join(root, 'ken.ini'),
    '[ken]\nproject_id = ini\nbase_url = https://ini/\n',
  );
  fs.writeFileSync(path.join(root, 'a', '.ken'), 'project_id=ken\napi_token=tok\n');

  const cfg = resolveConfig(sub, {});
  assert.equal(cfg.projectId, 'ken');
  assert.equal(cfg.apiToken, 'tok');
  assert.equal(cfg.baseUrl, 'https://ini');
  assert.equal(configProblem(cfg), null);

  assert.equal(resolveConfig(sub, { KEN_PROJECT_ID: 'env' }).projectId, 'env');
});

test('configProblem: explains what is missing', () => {
  const base = { baseUrl: 'x', kenFile: null, iniFile: null, projectId: null, apiToken: null };
  assert.match(configProblem(base), /ken init/);
  assert.match(configProblem({ ...base, iniFile: 'ken.ini' }), /project_id/);
  assert.match(configProblem({ ...base, iniFile: 'ken.ini', projectId: 'p' }), /api_token/);
});
