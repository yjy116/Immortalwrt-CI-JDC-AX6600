#!/bin/bash
set -euo pipefail

SOURCE_DIR=${1:?pass the destination package directory}
WORKSPACE=${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}
python3 "$WORKSPACE/Scripts/proxy_sources.py" checkout daede \
  --source "$SOURCE_DIR" --commit "${DAEDE_COMMIT:-}"
patch --batch --forward --fuzz=0 -p1 -d "$SOURCE_DIR" < "$WORKSPACE/patches/daede/010-unified-backends.patch"
install -m 0755 "$WORKSPACE/files/etc/uci-defaults/89-daede-migrate" \
  "$SOURCE_DIR/luci-app-daede/root/etc/uci-defaults/89-daede-migrate"

python3 "$WORKSPACE/Scripts/proxy_sources.py" prepare daede --source "$SOURCE_DIR"
