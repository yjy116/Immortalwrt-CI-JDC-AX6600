#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/Scripts/function.sh"
config=$(mktemp)
trap 'rm -f "$config"' EXIT
export WRT_REPO=https://github.com/VIKINGYFY/immortalwrt.git

for WRT_BRANCH in main owrt; do
  export WRT_BRANCH
  : > "$config"
  cat_ebpf_config "$config"
  grep -Fxq 'CONFIG_KERNEL_DEBUG_INFO_BTF=y' "$config"
  if [[ "$WRT_BRANCH" == owrt ]]; then
    uses_owrt_ppe
    if grep -q 'CONFIG_KERNEL_TRANSPARENT_HUGEPAGE' "$config"; then
      echo 'OWRT must retain upstream THP defaults, not legacy tuning' >&2
      exit 1
    fi
  else
    ! uses_owrt_ppe
    grep -Fxq 'CONFIG_KERNEL_TRANSPARENT_HUGEPAGE=y' "$config"
  fi
done
grep -Fq 'runs-on: ubuntu-24.04' "$ROOT_DIR/.github/workflows/WRT-CORE.yml"
echo 'OWRT branch selection, upstream memory defaults and build host checks passed'
