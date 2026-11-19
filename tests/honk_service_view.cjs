const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createDom } = require('./honk_dom.cjs');

const source = process.argv[2];
assert.ok(source, 'pass prepared Honk source');
const viewDir = path.join(source, 'luci-app-honk/htdocs/luci-static/resources/view/honk');
const read = name => fs.readFileSync(path.join(viewDir, name), 'utf8');

function upstreamFunction(text, name) {
  const start = text.indexOf('\t\tfunction ' + name + '(');
  const end = text.indexOf('\n\t\tfunction ', start + 1);
  assert.ok(start >= 0 && end > start, 'upstream function missing: ' + name);
  return text.slice(start, end);
}

function createServiceView({ response = () => Promise.resolve({ ok: true }), environment = {} } = {}) {
  const { nodes, element, document } = createDom();
  const calls = [];
  const rpc = { declare: spec => (...args) => {
    const call = { method: spec.method, values: Object.fromEntries(
      (spec.params || []).map((key, index) => [key, args[index]])) };
    calls.push(call);
    return response(call);
  } };
  const api = new Function('rpc', 'baseclass', 'E', 'document', 'L', '_', read('rpc.js'))(
    rpc, { extend: value => value }, element, document, { env: { ...environment } }, value => value);
  let polls = 0;
  const honk = { ...api, resultMessage: (_, message) => message,
    status: () => { polls++; return Promise.resolve({}); } };
  const text = read('overview.js');
  const code = `const data = { candidates: [] };
    let formSnapshotSha = null;
    let busy = false, setupBusy = false, settingsBusy = false;
    const field = (label, input) => E('label', {}, [label, input]);
    const renderStatus = () => {}, renderSetup = () => {};
    ${upstreamFunction(text, 'splitAddress')}
    ${upstreamFunction(text, 'renderServiceSettings')}
    ${upstreamFunction(text, 'refresh')}
    return { render: renderServiceSettings, refresh, isBusy: () => settingsBusy };`;
  return { ...new Function('E', 'honk', '_', code)(element, honk, value => value),
    nodes, calls, pollCount: () => polls };
}

const status = { lan_network: 'lan', runtime_lan: 'br-lan', listen_port: 9527,
  runtime_listen: '0.0.0.0:9527', boot_enabled: false, settings_owner: 'file',
  clash_api_enabled: false, clash_api_port: 9090, config_sha256: 'a'.repeat(64) };
const settle = () => new Promise(resolve => setImmediate(resolve));

module.exports = { createServiceView, status, settle };
