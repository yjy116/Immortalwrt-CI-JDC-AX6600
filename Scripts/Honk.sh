#!/bin/bash
set -euo pipefail

SOURCE_DIR=${1:?pass the destination package directory}
WORKSPACE=${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}
python3 "$WORKSPACE/Scripts/proxy_sources.py" checkout honk \
  --source "$SOURCE_DIR" --commit "${HONK_COMMIT:-}"
patch --batch --forward --fuzz=0 -p1 -d "$SOURCE_DIR" < "$WORKSPACE/patches/honk/010-preserve-boot-opt-in.patch"
python3 "$WORKSPACE/Scripts/proxy_sources.py" prepare honk --source "$SOURCE_DIR"
