const test = require('node:test');
const assert = require('node:assert/strict');
const { KenApi, boardUrl } = require('../src/api');

const cfg = {
  baseUrl: 'https://kb',
  projectId: 'p 1',
  apiToken: 'tok',
  kenFile: null,
  iniFile: null,
};

function fakeFetch(status, body) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url, init });
    return { ok: status < 400, status, json: async () => body };
  };
  return { impl, calls };
}

test('listTasks: GET with Bearer and encoded project', async () => {
  const { impl, calls } = fakeFetch(200, []);
  await new KenApi(cfg, impl).listTasks();
  assert.equal(calls[0].url, 'https://kb/api/v1/tasks?project=p%201');
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer tok');
  assert.equal(calls[0].init.body, undefined);
});

test('getTask: GET one task by id', async () => {
  const { impl, calls } = fakeFetch(200, { id: 7 });
  await new KenApi(cfg, impl).getTask(7);
  assert.equal(calls[0].url, 'https://kb/api/v1/tasks/7');
  assert.equal(calls[0].init.method, 'GET');
});

test('setStatus: PATCH JSON body', async () => {
  const { impl, calls } = fakeFetch(200, { id: 7, status: 'doing' });
  await new KenApi(cfg, impl).setStatus(7, 'doing');
  assert.equal(calls[0].url, 'https://kb/api/v1/tasks/7');
  assert.equal(calls[0].init.method, 'PATCH');
  assert.equal(calls[0].init.body, '{"status":"doing"}');
  assert.equal(calls[0].init.headers['Content-Type'], 'application/json');
});

test('HTTP error surfaces status and API error message', async () => {
  const { impl } = fakeFetch(403, { error: 'forbidden' });
  await assert.rejects(new KenApi(cfg, impl).listTasks(), /HTTP 403 \(forbidden\)/);
});

test('boardUrl: category page, optional #ID- anchor', () => {
  assert.equal(boardUrl('https://kb', 'c1'), 'https://kb/cat/c1.html');
  assert.equal(boardUrl('https://kb', 'c1', 42), 'https://kb/cat/c1.html#ID-42');
});
