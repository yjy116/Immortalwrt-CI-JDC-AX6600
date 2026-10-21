// Exercise the actual ucode nft read loop, replacing only its stream input.
// CI also runs this same extracted block in the native ucode interpreter.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const cases = require('./cases.json');

function nftBlock(source) {
  const start = source.indexOf('\t\t\tif (nft) {');
  const end = source.indexOf('\n\t\t\treturn ubus.defer(', start);
  assert.ok(start >= 0 && end > start, 'Unknown LuCI nft reader layout; review upstream');
  return source.slice(start, end);
}

function expected(sample, num = 1) {
  return { num: String(num), proto: sample.proto, extport: sample.extport ?? 60281,
    intaddr: sample.intaddr ?? '192.168.100.1', intport: sample.intport ?? 60281,
    descr: '' };
}

function run(block, lines) {
  let index = 0;
  const rules = [];
  const nft = { read: () => lines[index++], close: () => {} };
  const context = { nft, rules, length: value => value?.length ?? 0,
    match: (value, pattern) => value.match(pattern), push: (array, value) => array.push(value),
    uc: value => value.toUpperCase(), iptoarr: value => value, arrtoip: value => value };
  // Fail if a source revision tries to mutate services or execute a command.
  const forbidden = () => { throw new Error('Parser must not execute commands'); };
  const invoke = new Function(...Object.keys(context), 'system', 'popen', block);
  invoke(...Object.values(context), forbidden, forbidden);
  return rules;
}

function check(source) {
  const block = nftBlock(source);
  for (const sample of cases) {
    const wanted = sample.proto ? [expected(sample)] : [];
    assert.deepEqual(run(block, [sample.line]), wanted, sample.name);
  }
  const mixed = cases.filter(sample => sample.line !== '');
  const wanted = mixed.filter(sample => sample.proto).map((sample, i) => expected(sample, i + 1));
  assert.deepEqual(run(block, mixed.map(sample => sample.line)), wanted, 'mixed rule numbering');
  return block;
}

if (require.main === module) {
  const source = fs.readFileSync(process.argv[2], 'utf8');
  if (process.argv[3] === '--extract') process.stdout.write(nftBlock(source));
  else {
    check(source);
    console.log(`${cases.length + 1} LuCI nft reader cases passed`);
  }
}

module.exports = { check, nftBlock };
