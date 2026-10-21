// Execute the actual nft reader in native ucode, not a translated regex engine.
import { readfile } from 'fs';

const block = readfile(ARGV[0]);
const samples = json(readfile(ARGV[1]));
assert(type(block) == 'string' && type(samples) == 'array', 'Missing test input');
const parse = loadstring('return function(nft, rules) {\n' + block + '\n};')();

function run(lines) {
    let index = 0;
    const rules = [];
    const nft = { read: function() { return lines[index++]; }, close: function() {} };
    parse(nft, rules);
    return rules;
}

function expected(sample, index) {
    return { num: `${index}`, proto: sample.proto, extport: sample.extport ?? 60281,
        intaddr: sample.intaddr ?? '192.168.100.1', intport: sample.intport ?? 60281,
        descr: '' };
}

function compare(actual, wanted, name) {
    assert(length(actual) == length(wanted), name + ': mapping count');
    for (let index = 0; index < length(wanted); index++) {
        for (let key, value in wanted[index])
            assert(actual[index][key] === value, name + ': ' + key);
    }
}

for (let sample in samples)
    compare(run([sample.line]), sample.proto ? [expected(sample, 1)] : [], sample.name);

const mixed = filter(samples, sample => sample.line != '');
const wanted = map(filter(mixed, sample => sample.proto), (sample, index) => expected(sample, index + 1));
compare(run(map(mixed, sample => sample.line)), wanted, 'mixed rule numbering');
printf('%d native ucode nft reader cases passed\n', length(samples) + 1);
