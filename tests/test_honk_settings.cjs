const assert = require('node:assert/strict');
const { createServiceView, status, settle } = require('./honk_service_view.cjs');

async function testBootSetting({ owner, saved, requested, environment }) {
  const { render, nodes, calls } = createServiceView({ environment });
  assert.equal(calls.length, 0, 'module initialization must not invoke router RPC');
  render({ ...status, settings_owner: owner, boot_enabled: saved });
  const checkbox = nodes.find(node => node.id === 'honk-boot-enabled');
  assert.ok(checkbox && !checkbox.disabled, 'boot preference remains independently editable');
  assert.equal(checkbox.checked, saved);
  checkbox.checked = requested;
  nodes.find(node => node.id === 'honk-save-boot').events.click();
  await settle();
  assert.deepEqual(calls, [{ method: 'boot_settings', values: { boot_enabled: requested } }]);
}

async function testNetworkSavePreservesBootAndUpstreamFields(owner) {
  const { render, nodes, calls } = createServiceView();
  render({ ...status, settings_owner: owner, clash_api_enabled: true });
  const checkbox = nodes.find(node => node.id === 'honk-boot-enabled');
  assert.ok(checkbox, 'boot preference is visible');
  const toggle = nodes.find(node => node.role === 'switch');
  assert.equal(toggle['aria-checked'], 'true');
  toggle.events.click({ preventDefault() {} });
  assert.equal(toggle['aria-checked'], 'false');
  nodes.find(node => node.tag === 'form').events.submit({ preventDefault() {} });
  await settle();
  assert.deepEqual(calls, [{ method: 'settings', values: {
    lan_network: 'lan', lan_device: 'br-lan', listen_host: undefined, listen_port: 9527,
    clash_api_enabled: false, clash_host: undefined, clash_api_port: 9090,
    clash_api_secret: '', clash_api_secret_mode: 'keep', expect_sha256: 'a'.repeat(64)
  } }], 'normal save retains the upstream runtime fields and optimistic hash, not boot policy');
  assert.equal(checkbox.checked, false);
}

(async () => {
  for (const owner of ['system', 'file']) {
    for (const [saved, requested] of [[false, false], [false, true], [true, false]])
      await testBootSetting({ owner, saved, requested });
    await testNetworkSavePreservesBootAndUpstreamFields(owner);
  }
  for (const rpctimeout of [0, 20, 600])
    await testBootSetting({ owner: 'file', saved: false, requested: true, environment: { rpctimeout } });
  console.log('Honk overview saves boot policy independently and preserves upstream network settings');
})().catch(error => { console.error(error); process.exitCode = 1; });
