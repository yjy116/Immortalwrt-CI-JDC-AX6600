#!/bin/bash
set -eu

cd "$1"
jobs="$(nproc)"

# Match OpenWrt's download prerequisites, but do not let its final submake
# hide an earlier failure in the semicolon-separated top-level recipe.
make -j"$jobs" V=s tools/flock/compile tools/zstd/compile
for target in tools/download toolchain/download package/download target/download; do
    make -j"$jobs" V=s "$target"
done
