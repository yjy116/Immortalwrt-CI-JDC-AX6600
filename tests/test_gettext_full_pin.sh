#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIN_SCRIPT="$ROOT_DIR/Scripts/pin_gettext_full.sh"
PIN_SOURCE="$ROOT_DIR/patches/gettext-full"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

[ -f "$PIN_SCRIPT" ] || {
	echo "missing gettext-full pin script"
	exit 1
}

mkdir -p "$TMP_DIR/package/libs/gettext-full/patches"
touch "$TMP_DIR/package/libs/gettext-full/patches/stale.patch"

sh "$PIN_SCRIPT" "$PIN_SOURCE" "$TMP_DIR/package/libs/gettext-full"

grep -q '^PKG_VERSION:=0.24.2$' "$TMP_DIR/package/libs/gettext-full/Makefile"
grep -q '^PKG_HASH:=fcc0187f597aef6bc5bc95c629db1126315beb196b20570eaec6a4941850f7c5$' \
	"$TMP_DIR/package/libs/gettext-full/Makefile"
[ ! -e "$TMP_DIR/package/libs/gettext-full/patches/stale.patch" ]
[ ! -e "$TMP_DIR/package/libs/gettext-full/patches/201-gnulib-ctype-macro-defaults.patch" ]
grep -q 'pin_gettext_full.sh' "$ROOT_DIR/Scripts/Packages.sh"

echo "gettext-full pin guard passed"
