// Test unchanged upstream functions with isolated I/O, never the live firewall.
import { readfile } from 'fs';

const factory = loadstring(readfile(ARGV[0]))();
const PORT = 60281;
const ADDRESS = '192.0.2.10';

function sample(protocol, mode, counter) {
    const proto = protocol == 'tcp' ? 6 : 17;
    const left = mode == 'raw' ? { payload: { base: 'nh', offset: 72, len: 8 } } :
        mode == 'meta' ? { meta: { key: 'l4proto' } } :
        { payload: { protocol: 'ip', field: 'protocol' } };
    const expr = [
        { match: { op: '==', left, right: mode == 'raw' ? proto : protocol } },
        { match: { op: '==', left: { payload: { protocol: 'th', field: 'dport' } }, right: PORT } }
    ];
    if (counter)
        push(expr, { counter: { packets: 12, bytes: 3456 } });
    push(expr, { dnat: { family: 'ip', addr: ADDRESS, port: PORT } });
    return { rule: { family: 'inet', table: 'fw4', chain: 'upnp_prerouting', expr } };
}

function forbidden() {
    die('Unexpected I/O or service mutation during status regression');
}

function reader(options) {
    const io = {
        popen: function(command) {
            assert(command == 'nft --json list chain inet fw4 upnp_prerouting 2>/dev/null', command);
            return { read: () => options.output, close: () => options.exit ?? 0 };
        },
        readfile: function(path) {
            if (path == '/usr/share/miniupnpd/backend') return 'nftables\n';
            assert(path == '/var/run/miniupnpd.leases', path);
            return options.leases ?? '';
        },
        cursor: () => ({ get: () => null }),
        connect: () => ({ defer: function(object, method, args, callback) {
            assert(object == 'luci-rpc' && method == 'getHostHints', method);
            return callback(0, { test: { ipaddrs: [ADDRESS], name: 'test-client' } });
        } }),
        system: forbidden, sleep: forbidden, open: forbidden, access: forbidden,
        mkdtemp: forbidden, rename: forbidden, rmdir: forbidden,
        unlink: forbidden, writefile: forbidden
    };
    return factory(io);
}

function check_mapping(protocol, mode, counter) {
    const api = reader({ output: sprintf('%J', { nftables: [sample(protocol, mode, counter)] }) });
    const rows = api.read_nft_rules();
    assert(length(rows) == 1, `${protocol}/${mode}/${counter}: count`);
    const rule = rows[0];
    assert(rule.proto == uc(protocol) && rule.extport == PORT, 'Protocol/port mismatch');
    assert(rule.intaddr == ADDRESS && rule.intport == PORT, 'Destination mismatch');
    assert(rule.token == `${uc(protocol)}:${PORT}:${ADDRESS}:${PORT}`, 'Token mismatch');
}

for (let protocol in ['tcp', 'udp'])
    for (let mode in ['raw', 'decoded', 'meta'])
        for (let counter in [false, true])
            check_mapping(protocol, mode, counter);

assert(reader({ output: '{' }).read_nft_rules() == null, 'Invalid JSON must fail');
assert(reader({ output: '{}'}).read_nft_rules() == null, 'Missing nftables must fail');
assert(reader({ output: '{"nftables":[]}', exit: 1 }).read_nft_rules() == null, 'Command failure');
assert(length(reader({ output: '{"nftables":[]}' }).read_nft_rules()) == 0, 'Empty rules');

const ignored = sample('tcp', 'raw', true);
ignored.rule.chain = 'unrelated';
assert(length(reader({ output: sprintf('%J', { nftables: [ignored] }) }).read_nft_rules()) == 0,
    'Unrelated chain must not appear');
const invalid = sample('tcp', 'raw', true);
invalid.rule.expr[3].dnat.port = 0;
assert(length(reader({ output: sprintf('%J', { nftables: [invalid] }) }).read_nft_rules()) == 0,
    'Invalid destination must not appear');

const timestamp = time() + 300;
const lease = `TCP:${PORT}::${ADDRESS}:${PORT}:${timestamp}:qBittorrent:test`;
const api = reader({ output: sprintf('%J', { nftables: [sample('tcp', 'decoded', true)] }), leases: lease });
const parsed = api.parse_lease(lease);
assert(parsed.descr == 'qBittorrent:test' && parsed.timestamp == timestamp, 'Seven-field lease');
assert(api.parse_lease(`UDP:${PORT}:198.51.100.2:${ADDRESS}:${PORT}:0:remote`).proto == 'UDP', 'Remote host lease');
assert(api.parse_lease(`TCP:${PORT}:${ADDRESS}:${PORT}:${timestamp}:legacy`) == null, 'Old lease needs migration');
assert(api.parse_lease(`TCP:0::${ADDRESS}:${PORT}:0:bad`) == null, 'Bad lease port');
assert(api.parse_lease(`TCP:${PORT}::999.0.0.1:${PORT}:0:bad`) == null, 'Bad lease address');
let status;
api.methods.get_status.call({ reply: result => { status = result; } });
assert(length(status.rules) == 1 && status.rules[0].host_hint == 'test-client', 'Status host merge');
assert(status.rules[0].descr == 'qBittorrent:test', 'Status lease description');
assert(status.rules[0].expires > 0 && status.rules[0].expires <= 300, 'Remaining lease lifetime');
assert(api.methods.delete_rule.call({ args: { token: 'bad;command' } }).result == 'Invalid port mapping identifier',
    'Invalid delete token must not invoke services');
printf('Native upstream UPnP: 12 JSON variants plus failure, lease and status checks passed\n');
