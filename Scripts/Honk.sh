#!/bin/bash
set -euo pipefail

SOURCE_DIR=${1:?pass the destination package directory}
WORKSPACE=${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}
python3 "$WORKSPACE/Scripts/proxy_sources.py" checkout honk \
  --source "$SOURCE_DIR" --commit "${HONK_COMMIT:-}"
python3 "$WORKSPACE/Scripts/honk_boot.py" "$SOURCE_DIR"
python3 "$WORKSPACE/Scripts/proxy_sources.py" prepare honk --source "$SOURCE_DIR"
