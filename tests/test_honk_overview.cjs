const assert = require('node:assert/strict');
const { createServiceView, status, settle } = require('./honk_service_view.cjs');

async function testBootSaveBusyAndFailure() {
  let rejectSave;
  const pending = new Promise((resolve, reject) => { rejectSave = reject; });
  const page = createServiceView({ response: () => pending });
  page.render(status);
  const button = page.nodes.find(node => node.id === 'honk-save-boot');
  assert.ok(button, 'overview exposes the boot-only command');
  button.events.click();
  assert.ok(page.isBusy(), 'boot-only save participates in overview busy state');
  await page.refresh();
  assert.equal(page.pollCount(), 0, 'poll must not replace a pending form');
  rejectSave(new Error('commit failed'));
  await settle();
  assert.ok(!page.isBusy() && !button.disabled, 'save controls recover after failure');
  assert.ok(page.nodes.some(node => node.textContent === 'commit failed'), 'failure remains visible');
  await page.refresh();
  assert.equal(page.pollCount(), 1, 'normal polling resumes');
}

async function testBootSaveWaitsForNetworkSave() {
  let resolveSave;
  const pending = new Promise(resolve => { resolveSave = resolve; });
  const page = createServiceView({ response: () => pending });
  page.render(status);
  page.nodes.find(node => node.tag === 'form').events.submit({ preventDefault() {} });
  const button = page.nodes.find(node => node.id === 'honk-save-boot');
  assert.ok(button, 'boot command is present alongside network settings');
  button.events.click();
  assert.equal(page.calls.length, 1, 'boot save must not race a pending network save');
  assert.equal(page.calls[0].method, 'settings');
  resolveSave({ ok: true });
  await settle();
  button.events.click();
  await settle();
  assert.equal(page.calls[1].method, 'boot_settings');
}

(async () => {
  await testBootSaveBusyAndFailure();
  await testBootSaveWaitsForNetworkSave();
  console.log('Honk overview preserves pending boot saves, failure feedback and operation ordering');
})().catch(error => { console.error(error); process.exitCode = 1; });
