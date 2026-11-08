const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createDom } = require('./honk_dom.cjs');

const source = process.argv[2];
assert.ok(source, 'pass prepared Honk source');
const viewDir = path.join(source, 'luci-app-honk/htdocs/luci-static/resources/view/honk');
const read = name => fs.readFileSync(path.join(viewDir, name), 'utf8');

function harness(environment = {}) {
  const { nodes, element, document } = createDom();
  const luci = { env: { ...environment } };
  const calls = [];
  const rpc = { declare: spec => (...args) => {
    calls.push({ method: spec.method, values: Object.fromEntries(
      (spec.params || []).map((key, index) => [key, args[index]])) });
    return Promise.resolve({ ok: true });
  } };
  const api = new Function('rpc', 'baseclass', 'E', 'document', 'L', read('rpc.js'))(
    rpc, { extend: x => x }, element, document, luci);
  const honk = { ...api, installStyles() {}, resultMessage: (_, message) => message };
  const view = new Function('view', 'honk', 'E', '_', read('settings.js'))(
    { extend: x => x }, honk, element, text => text);
  return { view, nodes, calls };
}

async function testBootSetting(saved, requested, environment) {
  const { view, nodes, calls } = harness(environment);
  assert.equal(calls.length, 0, 'module initialization must not invoke router RPC');
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
  const clashToggle = nodes.find(node => node.role === 'switch');
  assert.ok(clashToggle.disabled, 'upstream file-owned switch remains read-only');
  clashToggle.events.click({ preventDefault() {} });
  assert.equal(nodes.find(node => node.id === 'honk-clash-enabled').checked, false);
}

async function testUpstreamSwitchWithBootPreference() {
  const { view, nodes, calls } = harness();
  view.render({ networks: ['lan'], status: { lan_network: 'lan', listen_port: 9527,
    boot_enabled: false, settings_owner: 'system', clash_api_enabled: true,
    clash_api_port: 9090, clash_api_secret_set: true } });
  const toggle = nodes.find(node => node.role === 'switch');
  assert.equal(toggle['aria-checked'], 'true', 'upstream control restores saved state');
  toggle.events.click({ preventDefault() {} });
  assert.equal(toggle['aria-checked'], 'false');
  assert.equal(nodes.find(node => node.id === 'honk-clash-enabled').checked, false);
  nodes.find(node => node.tag === 'form').events.submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, 'settings');
  assert.equal(calls[0].values.clash_api_enabled, false);
  assert.equal(calls[0].values.boot_enabled, false, 'Clash switch must not enable boot');
  assert.ok(nodes.find(node => node.id === 'honk-switch-styles'));
}

(async () => {
  await testBootSetting(false, false);
  await testBootSetting(false, true);
  await testBootSetting(true, false);
  // Exercise LuCI environment initialization without pinning an upstream timeout policy.
  const rpcTimeoutCases = { unset: 0, short: 20, extended: 600 };
  for (const rpctimeout of Object.values(rpcTimeoutCases))
    await testBootSetting(false, false, { rpctimeout });
  await testFileOwnedBootSetting();
  await testUpstreamSwitchWithBootPreference();
  console.log('Honk settings renders saved opt-in and sends explicit false/true via RPC');
})().catch(error => { console.error(error); process.exitCode = 1; });
