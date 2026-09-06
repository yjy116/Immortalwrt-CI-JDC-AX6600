#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CORE_WORKFLOW="$ROOT_DIR/.github/workflows/WRT-CORE.yml"

for workflow in \
	"$ROOT_DIR/.github/workflows/QCA-6.12-LiBwrt.yml" \
	"$ROOT_DIR/.github/workflows/QCA-6.12-VIKINGYFY.yml" \
	"$ROOT_DIR/.github/workflows/QCA-6.18-VIKINGYFY.yml"
do
	grep -Fq 'WRT_TEST: ${{inputs.TEST || false}}' "$workflow" || {
		echo "workflow_run must provide a boolean WRT_TEST fallback: $workflow"
		exit 1
	}

	grep -Fq 'default: false' "$workflow" || {
		echo "manual TEST input must use a boolean default: $workflow"
		exit 1
	}
done

core_test_block="$(sed -n '/^[[:space:]]*WRT_TEST:/,/^[[:space:]]*CI_NAME:/p' "$CORE_WORKFLOW")"
printf '%s\n' "$core_test_block" | grep -Fq 'default: false' || {
	echo "reusable WRT_TEST input must default to false"
	exit 1
}
printf '%s\n' "$core_test_block" | grep -Fq 'type: boolean' || {
	echo "reusable WRT_TEST input must remain boolean"
	exit 1
}

echo "workflow_run boolean input guard passed"
