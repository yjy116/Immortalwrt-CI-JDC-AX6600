const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createDom } = require('./honk_dom.cjs');

const source = process.argv[2];
assert.ok(source, 'pass prepared Honk source');
const code = fs.readFileSync(path.join(source,
  'luci-app-honk/htdocs/luci-static/resources/view/honk/boot-policy.js'), 'utf8');

function page(saved, response) {
  const { nodes, element } = createDom();
  const calls = [];
  const rpc = { declare: spec => (...args) => {
    calls.push([spec.object, spec.method, spec.params, args]);
    return spec.method === 'status' ? Promise.resolve({ boot_enabled: saved }) : response();
  } };
  const view = new Function('view', 'rpc', 'E', '_', code)(
    { extend: object => object }, rpc, element, text => text);
  assert.equal(calls.length, 0, 'module initialization does not call the router');
  return { view, nodes, calls };
}

function controls(nodes) {
  const input = nodes.find(node => node.id === 'honk-boot-enabled');
  const button = nodes.find(node => node.tag === 'button');
  const message = nodes.find(node => node.role === 'status');
  const submit = () => nodes.find(node => node.tag === 'form').events.submit({ preventDefault() {} });
  return { input, button, message, submit };
}

async function testSave(saved) {
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  const { view, nodes, calls } = page(saved, () => pending);
  view.render(await view.load());
  const { input, button, message, submit } = controls(nodes);
  assert.equal(input.checked, saved);
  input.checked = !saved;
  const saving = submit();
  assert.ok(input.disabled && button.disabled);
  await submit();
  assert.deepEqual(calls, [
    ['honk', 'status', undefined, []],
    ['honk', 'boot_settings', ['boot_enabled'], [!saved]]
  ]);
  resolve({ ok: true });
  await saving;
  assert.equal(message.textContent, 'Settings saved.');
  assert.ok(!input.disabled && !button.disabled);
}

async function testFailure(response) {
  const { view, nodes } = page(false, response);
  view.render(await view.load());
  const { input, button, message, submit } = controls(nodes);
  await submit();
  assert.equal(message.textContent, 'commit failed');
  assert.ok(!input.disabled && !button.disabled);
}

(async () => {
  for (const saved of [false, true])
    await testSave(saved);
  await testFailure(() => Promise.resolve({ ok: false, message: 'commit failed' }));
  await testFailure(() => Promise.reject(new Error('commit failed')));
  const { view } = page(undefined);
  const unavailable = await view.load();
  assert.throws(() => view.render(unavailable), /unavailable/);
  console.log('Honk boot page preserves both preferences, isolates writes and exposes failures');
})().catch(error => { console.error(error); process.exitCode = 1; });
