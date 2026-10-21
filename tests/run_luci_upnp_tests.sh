#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${RUNNER_TEMP:-/tmp}/luci-upnp-tests"
UCODE_COMMIT=4a28662538275b67a0bcf11de25c365c1ec7a99d
mkdir -p "$WORK"

if [ ! -d "$WORK/ucode/.git" ]; then
    git init -q "$WORK/ucode"
fi
git -C "$WORK/ucode" fetch -q --depth=1 https://github.com/jow-/ucode.git "$UCODE_COMMIT"
git -C "$WORK/ucode" checkout -q --detach "$UCODE_COMMIT"
cmake -S "$WORK/ucode" -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release \
    -DFFI_SUPPORT=OFF -DDIGEST_SUPPORT=OFF -DUBUS_SUPPORT=OFF -DUCI_SUPPORT=OFF \
    -DULOOP_SUPPORT=OFF -DRTNL_SUPPORT=OFF -DNL80211_SUPPORT=OFF
cmake --build "$WORK/build" --target ucode fs_lib -j2

CHECK="$ROOT/Scripts/luci_upnp/check_parser.cjs"
CASES="$ROOT/Scripts/luci_upnp/cases.json"
BASELINE="$ROOT/tests/fixtures/luci_upnp/luci.upnp"
NATIVE="$ROOT/tests/test_luci_upnp.uc"
timeout 60s python3 "$ROOT/tests/test_luci_upnp.py"

node "$CHECK" "$BASELINE" --extract > "$WORK/baseline.uc"
if timeout 60s "$WORK/build/ucode" -L "$WORK/build/*.so" "$NATIVE" "$WORK/baseline.uc" "$CASES" > "$WORK/red.log" 2>&1; then
    echo 'ERROR: baseline must reproduce the counter parsing bug' >&2
    exit 1
fi
grep -F 'legacy-tcp-counter: mapping count' "$WORK/red.log"
cp "$BASELINE" "$WORK/luci.upnp"
python3 "$ROOT/Scripts/luci_upnp/install.py" "$WORK/luci.upnp"
node "$CHECK" "$WORK/luci.upnp" --extract > "$WORK/fixed.uc"
timeout 60s "$WORK/build/ucode" -L "$WORK/build/*.so" "$NATIVE" "$WORK/fixed.uc" "$CASES"

if [ -n "${GITHUB_ENV:-}" ]; then
    echo "LUCI_UPNP_UCODE=$WORK/build/ucode" >> "$GITHUB_ENV"
    echo "LUCI_UPNP_LIB=$WORK/build/*.so" >> "$GITHUB_ENV"
fi
