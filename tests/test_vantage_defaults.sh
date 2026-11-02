#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/files/etc/uci-defaults/zzzz-vantage-theme"

# Exercise the real first-boot script against an isolated UCI command stub.
uci() {
  case "$*" in
    '-q get luci.main.ci_default_theme')
      [[ -n "$marker" ]] || return 1
      printf '%s\n' "$marker" ;;
    'set luci.main.mediaurlbase=/luci-static/vantage')
      [[ "$fail_write" == 0 ]] || return 1
      theme=vantage ;;
    'set luci.main.ci_default_theme=vantage') marker=vantage ;;
    'commit luci') committed=1 ;;
    *) echo "Unexpected UCI write: $*" >&2; return 1 ;;
  esac
}

test -f "$SCRIPT" || { echo 'Missing Vantage first-boot default script' >&2; exit 1; }
(
  marker='' theme=aurora committed=0 fail_write=0
  # A successful script uses exit, so inspect state in an EXIT trap.
  trap '[[ "$theme" == vantage && "$marker" == vantage && "$committed" == 1 ]]' EXIT
  source "$SCRIPT"
)
(
  marker=vantage theme=argon committed=0 fail_write=0
  trap '[[ "$theme" == argon && "$committed" == 0 ]]' EXIT
  source "$SCRIPT"
)
# Run separately: a conditional subshell would suppress set -e inside the script.
set +e
(
  marker='' theme=aurora committed=0 fail_write=1
  source "$SCRIPT"
)
result=$?
set -e
[[ "$result" != 0 ]] || { echo 'UCI failure must not report success' >&2; exit 1; }
echo 'Vantage first-boot, preserved later choice and write-error checks passed'
