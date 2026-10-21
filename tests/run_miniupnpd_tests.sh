#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
FIXTURES=$(mktemp -d)
trap 'rm -rf "$FIXTURES"' EXIT
export MINIUPNPD_TEST_DIR="$FIXTURES"

# Fixed regression fixtures only; firmware still uses the current feed version.
curl --fail --location --show-error \
  https://github.com/miniupnp/miniupnp/releases/download/miniupnpd_2_3_11/miniupnpd-2.3.11.tar.gz \
  -o "$FIXTURES/release.tar.gz"
printf '%s  %s\n' \
  91994b127da735b2c97f19992e34420648c0e8c4ace8a4bcb0596e7685c48678 \
  "$FIXTURES/release.tar.gz" | sha256sum --check --strict
tar -xzf "$FIXTURES/release.tar.gz" -C "$FIXTURES"

git init -q "$FIXTURES/upstream"
git -C "$FIXTURES/upstream" fetch -q --depth=1 https://github.com/miniupnp/miniupnp.git \
  05bb29e78d882990efe13e8a5663b69313dc97fd
git -C "$FIXTURES/upstream" checkout -q --detach FETCH_HEAD
git clone -q --depth=1 --filter=blob:none --sparse \
  https://github.com/immortalwrt/packages.git "$FIXTURES/packages"
git -C "$FIXTURES/packages" sparse-checkout set net/miniupnpd
git -C "$FIXTURES/packages" fetch -q --depth=1 origin 72c7391fb2d04080afd0bfe919605749f81eb747
git -C "$FIXTURES/packages" checkout -q --detach FETCH_HEAD

timeout 60s python3 "$ROOT/tests/test_miniupnpd_backports.py"
timeout 60s python3 "$ROOT/tests/test_miniupnpd_runtime.py"
