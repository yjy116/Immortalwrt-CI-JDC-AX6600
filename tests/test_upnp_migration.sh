#!/bin/bash
set -euo pipefail
SOURCE=$(realpath "${1:?upstream migration script required}")
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export WORK

# Export only isolated test doubles; the upstream shell script remains unchanged.
uci() {
    [ "${1:-}" != -q ] || shift
    case "$1:$2" in
        get:upnpd.config.force_forwarding) test -f "$WORK/old" && cat "$WORK/old" ;;
        get:upnpd.config.ext_allow_private_ipv4) test -f "$WORK/new" && cat "$WORK/new" ;;
        get:upnpd.config.upnp_lease_file) printf '%s\n' "$WORK/leases" ;;
        rename:upnpd.config.force_forwarding=ext_allow_private_ipv4) mv "$WORK/old" "$WORK/new" ;;
        delete:upnpd.config.force_forwarding) rm "$WORK/old" ;;
        commit:upnpd) test "${FAIL_COMMIT:-0}" = 0 ;;
        *) echo "Unexpected uci: $*" >&2; return 99 ;;
    esac
}
pidof() { test "${RUNNING:-0}" = 1; }
sleep() { :; }
export -f uci pidof sleep

printf '%s\n' 0 > "$WORK/old"
printf '%s\n' 'TCP:60281:192.0.2.10:60281:100:qBittorrent:test' \
    'UDP:60282::192.0.2.11:60282:200:new' \
    'TCP:60283:198.51.100.2:192.0.2.12:60283:300:remote' > "$WORK/leases"
printf '%s\n' 'TCP:60281::192.0.2.10:60281:100:qBittorrent:test' \
    'UDP:60282::192.0.2.11:60282:200:new' \
    'TCP:60283:198.51.100.2:192.0.2.12:60283:300:remote' > "$WORK/expected"
bash "$SOURCE"
test ! -e "$WORK/old"
test "$(cat "$WORK/new")" = 0
cmp "$WORK/leases" "$WORK/expected"
bash "$SOURCE"
cmp "$WORK/leases" "$WORK/expected"

printf '%s\n' 1 > "$WORK/old"
bash "$SOURCE"
test ! -e "$WORK/old"
test "$(cat "$WORK/new")" = 0

printf '%s\n' 1 > "$WORK/old"
if RUNNING=1 bash "$SOURCE"; then echo 'Running daemon must block migration' >&2; exit 1; fi
test -e "$WORK/old"
cmp "$WORK/leases" "$WORK/expected"
if FAIL_COMMIT=1 bash "$SOURCE"; then echo 'Commit failure must be exposed' >&2; exit 1; fi
echo 'Upstream migration: legacy rename, explicit value retention, mixed leases, idempotence and errors passed'
