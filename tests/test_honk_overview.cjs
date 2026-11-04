const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = process.argv[2];
assert.ok(source, 'pass prepared Honk source');
const text = fs.readFileSync(path.join(source,
  'luci-app-honk/htdocs/luci-static/resources/view/honk/overview.js'), 'utf8');

function upstreamFunction(name) {
  const start = text.indexOf('\t\tfunction ' + name + '(');
  const end = text.indexOf('\n\t\tfunction ', start + 1);
  assert.ok(start >= 0 && end > start);
  return text.slice(start, end);
}

function harness() {
  const nodes = [];
  const element = (tag, attrs = {}, children = []) => {
    const node = { tag, ...attrs, children, events: {},
      appendChild(child) { this.children = [...this.children, child]; },
      addEventListener(event, callback) { this.events[event] = callback; } };
    nodes.push(node);
    return node;
  };
  let rejectSave, polls = 0;
  const pending = new Promise((resolve, reject) => { rejectSave = reject; });
  const honk = { bootSettings: () => pending, ensureOk: value => value,
    status: () => { polls++; return Promise.resolve({}); } };
  const code = `const data = { networks: ['lan'] };
    const clashSecret = '';
    let busy = false, setupBusy = false, settingsBusy = false;
    const field = (label, input) => E('label', {}, [label, input]);
    const renderStatus = () => {}, renderSetup = () => {};
    ${upstreamFunction('renderServiceSettings')}
    ${upstreamFunction('refresh')}
    return { renderServiceSettings, refresh, isBusy: () => settingsBusy };`;
  return { ...new Function('E', 'honk', '_', code)(element, honk, value => value),
    nodes, rejectSave, pollCount: () => polls };
}

(async () => {
  const page = harness();
  page.renderServiceSettings({ settings_owner: 'file', boot_enabled: false, lan_network: 'lan' });
  const button = page.nodes.find(node => node.tag === 'button' && node.children === 'Save boot setting');
  button.events.click();
  assert.ok(page.isBusy(), 'boot-only save participates in overview busy state');
  await page.refresh();
  assert.equal(page.pollCount(), 0, 'poll must not replace a pending form');
  page.rejectSave(new Error('commit failed'));
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(!page.isBusy() && !button.disabled, 'save controls recover after failure');
  assert.ok(page.nodes.some(node => node.textContent === 'commit failed'), 'failure remains visible');
  await page.refresh();
  assert.equal(page.pollCount(), 1, 'normal polling resumes');
  console.log('Honk overview preserves pending boot save and failure feedback across polling');
})().catch(error => { console.error(error); process.exitCode = 1; });
