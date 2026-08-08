#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOW="$ROOT_DIR/.github/workflows/WRT-CORE.yml"

compiler_block="$(sed -n '/- name: Cache Compiler Outputs/,/- name: Cache Staging Dependencies/p' "$WORKFLOW")"
staging_block="$(sed -n '/- name: Cache Staging Dependencies/,/- name: Refresh the cache/p' "$WORKFLOW")"

printf '%s\n' "$compiler_block" | grep -Fq '${{ env.WRT_DIR }}/.ccache'
if printf '%s\n' "$compiler_block" | grep -Fq '${{ env.WRT_DIR }}/staging_dir'; then
	echo "compiler cache must not restore staging_dir"
	exit 1
fi

printf '%s\n' "$staging_block" | grep -Fq '${{ env.WRT_DIR }}/staging_dir'
printf '%s\n' "$staging_block" | grep -Fq 'staging-${{ env.WRT_ARCH }}-${{ hashFiles('"'"'**/repo_flag'"'"') }}-${{ env.WRT_HASH }}-'
if printf '%s\n' "$staging_block" | grep -Fq '${{ env.WRT_DIR }}/.ccache'; then
	echo "staging cache must not restore .ccache"
	exit 1
fi

if grep -Fq 'pin_gettext_full.sh' "$ROOT_DIR/Scripts/Packages.sh"; then
	echo "temporary gettext pin must be removed after cache isolation"
	exit 1
fi

echo "source-isolated staging cache guard passed"
