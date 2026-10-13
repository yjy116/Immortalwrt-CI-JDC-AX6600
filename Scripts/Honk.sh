#!/bin/bash
set -euo pipefail

SOURCE_DIR=${1:?pass the destination package directory}
HONK_REPO=https://github.com/kenzok8/openwrt-honk.git
HONK_COMMIT=52ecdb1bb26e04be782bcb368973fd54d4a44af6
HONK_RELEASE=v2026.10.12-r38236606118
HONK_SOURCE_TAG=source-38236606118
HONK_SOURCE_URL=https://github.com/kenzok8/openwrt-honk/releases/download/$HONK_SOURCE_TAG

git init "$SOURCE_DIR"
git -C "$SOURCE_DIR" fetch --depth=1 "$HONK_REPO" "$HONK_COMMIT"
git -C "$SOURCE_DIR" -c core.autocrlf=false checkout --detach FETCH_HEAD
test "$(git -C "$SOURCE_DIR" rev-parse HEAD)" = "$HONK_COMMIT"

# Upstream Makefiles need these generated inputs; never use mutable staging/SKIP.
download_stage() {
  local name=$1 hash=$2 package=$3
  local destination="$SOURCE_DIR/$package/$name"
  curl --fail --location --show-error "$HONK_SOURCE_URL/$name" -o "$destination.tmp"
  printf '%s  %s\n' "$hash" "$destination.tmp" | sha256sum --check --strict
  mv "$destination.tmp" "$destination"
}

download_stage generated-stage.mk \
  534de1bc50183577d57ec91f0b8b3ba499722b1be6815dbf422bca26fe90b121 honk
download_stage generated-provenance.json \
  04c168b50801644b630e355fe9baceee061f246e3194e8897f5e136bff22eb46 honk
download_stage generated-doona-stage.mk \
  c5013b4707959ec09e28b75e09a01ab4fcc3087ac4b7eada784c7903884f5e4c luci-app-honk

{
  printf 'PACKAGING_REPO=%s\nPACKAGING_COMMIT=%s\n' "$HONK_REPO" "$HONK_COMMIT"
  printf 'RELEASE=%s\nSOURCE_TAG=%s\n' "$HONK_RELEASE" "$HONK_SOURCE_TAG"
  printf 'CORE_BUILD=upstream-prebuilt-static-musl\n'
  cat "$SOURCE_DIR/ci/pins.env"
  cat "$SOURCE_DIR/honk/generated-stage.mk"
  cat "$SOURCE_DIR/luci-app-honk/generated-doona-stage.mk"
  cat "$SOURCE_DIR/honk/generated-provenance.json"
} > "$SOURCE_DIR/ci/HONK-SOURCE.txt"
cat "$SOURCE_DIR/ci/HONK-SOURCE.txt"
