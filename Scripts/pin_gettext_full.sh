#!/bin/sh
set -eu

SOURCE_DIR=$1
TARGET_DIR=$2

[ -f "$SOURCE_DIR/Makefile" ] || {
	echo "gettext-full source is incomplete: $SOURCE_DIR" >&2
	exit 1
}

rm -rf "$TARGET_DIR"
mkdir -p "$(dirname "$TARGET_DIR")"
cp -R "$SOURCE_DIR" "$TARGET_DIR"
