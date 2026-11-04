const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = process.argv[2];
assert.ok(source, 'pass prepared Honk source');
const viewDir = path.join(source, 'luci-app-honk/htdocs/luci-static/resources/view/honk');
const read = name => fs.readFileSync(path.join(viewDir, name), 'utf8');

function harness() {
  const calls = [];
  const rpc = { declare: spec => (...args) => {
    calls.push({ method: spec.method, values: Object.fromEntries(
      (spec.params || []).map((key, index) => [key, args[index]])) });
    return Promise.resolve({ ok: true });
  } };
  const api = new Function('rpc', 'baseclass', read('rpc.js'))(rpc, { extend: x => x });
  const nodes = [];
  const element = (tag, attrs = {}, children = []) => {
    const node = { tag, ...attrs, children, value: '', events: {},
      appendChild(child) { this.children = [...this.children, child]; },
      addEventListener(event, callback) { this.events[event] = callback; },
      removeAttribute(name) { delete this[name]; } };
    nodes.push(node);
    return node;
  };
  const honk = { ...api, installStyles() {}, resultMessage: (_, message) => message };
  const view = new Function('view', 'honk', 'E', '_', read('settings.js'))(
    { extend: x => x }, honk, element, text => text);
  return { view, nodes, calls };
}

async function testBootSetting(saved, requested) {
  const { view, nodes, calls } = harness();
  view.render({ networks: ['lan'], status: { lan_network: 'lan', listen_port: 9527,
    boot_enabled: saved, settings_owner: 'system', clash_api_enabled: false, clash_api_port: 9090 } });
  const checkbox = nodes.find(node => node.id === 'honk-boot-enabled');
  assert.ok(checkbox, 'boot opt-in remains available');
  assert.equal(checkbox.checked, saved);
  checkbox.checked = requested;
  nodes.find(node => node.tag === 'form').events.submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, [{ method: 'settings', values: { lan_network: 'lan', listen_port: 9527,
    boot_enabled: requested, clash_api_enabled: false, clash_api_port: 9090, clash_api_secret: '' } }]);
}

async function testFileOwnedBootSetting() {
  const { view, nodes, calls } = harness();
  view.render({ networks: ['lan'], status: { lan_network: 'lan', listen_port: 9527,
    boot_enabled: false, settings_owner: 'file', clash_api_enabled: false, clash_api_port: 9090 } });
  const checkbox = nodes.find(node => node.id === 'honk-boot-enabled');
  assert.ok(!checkbox.disabled, 'file-owned network config must not lock boot preference');
  checkbox.checked = true;
  const button = nodes.find(node => node.id === 'honk-save-boot');
  assert.ok(button && !button.disabled, 'independent boot command is available');
  button.events.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, [{ method: 'boot_settings', values: { boot_enabled: true } }]);
  assert.ok(nodes.find(node => node.id === 'honk-lan-network').disabled);
}

(async () => {
  await testBootSetting(false, false);
  await testBootSetting(false, true);
  await testBootSetting(true, false);
  await testFileOwnedBootSetting();
  console.log('Honk settings renders saved opt-in and sends explicit false/true via RPC');
})().catch(error => { console.error(error); process.exitCode = 1; });
