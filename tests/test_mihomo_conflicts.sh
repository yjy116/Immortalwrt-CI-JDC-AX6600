#!/bin/bash
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT
mkdir -p "$TEST_DIR/package/OpenWrt-nikki/"{mihomo-alpha,mihomo-meta}
mkdir -p "$TEST_DIR/feeds/packages"

# Reproduce the reciprocal provider conflicts from current OpenWrt-nikki.
printf '%s\n' '  PROVIDES:=mihomo' '  CONFLICTS:=mihomo-meta' \
  > "$TEST_DIR/package/OpenWrt-nikki/mihomo-alpha/Makefile"
printf '%s\n' '  PROVIDES:=mihomo' '  CONFLICTS:=mihomo-alpha' \
  '  DEFAULT_VARIANT:=1' \
  > "$TEST_DIR/package/OpenWrt-nikki/mihomo-meta/Makefile"

cd "$TEST_DIR/package"
export WRT_DIR="$TEST_DIR" GITHUB_WORKSPACE="$TEST_DIR"
bash "$ROOT_DIR/Scripts/Handles.sh"

if grep -q 'CONFLICTS:=mihomo-meta' OpenWrt-nikki/mihomo-alpha/Makefile; then
  echo "Mihomo providers still create a reciprocal Kconfig dependency"
  exit 1
fi
grep -q 'CONFLICTS:=mihomo-alpha' OpenWrt-nikki/mihomo-meta/Makefile
grep -q 'DEFAULT_VARIANT:=1' OpenWrt-nikki/mihomo-meta/Makefile
grep -q 'PROVIDES:=mihomo' OpenWrt-nikki/mihomo-alpha/Makefile
grep -q 'PROVIDES:=mihomo' OpenWrt-nikki/mihomo-meta/Makefile

cp OpenWrt-nikki/mihomo-alpha/Makefile "$TEST_DIR/alpha.once"
cp OpenWrt-nikki/mihomo-meta/Makefile "$TEST_DIR/meta.once"
bash "$ROOT_DIR/Scripts/Handles.sh"
cmp "$TEST_DIR/alpha.once" OpenWrt-nikki/mihomo-alpha/Makefile
cmp "$TEST_DIR/meta.once" OpenWrt-nikki/mihomo-meta/Makefile
echo "Mihomo conflict normalization preserves providers and is idempotent"
