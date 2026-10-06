#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT=${1:-$ROOT_DIR/files/etc/uci-defaults/99-athena-led-config-migration}
command -v uci >/dev/null || { echo 'Requires real OpenWrt uci; run on OpenWrt.' >&2; exit 1; }
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

legacy_config() {
  printf "config athena_led 'config'\n\toption enable '%s'\n\toption lightLevel '%s'\n" \
    "$2" "$3" > "$1"
}

modern_config() {
  printf "config settings 'general'\n\toption enabled '%s'\n\toption light_level '%s'\n" \
    "$2" "$3" > "$1"
}

new_case() {
  CASE_DIR="$TEST_DIR/$1"
  mkdir -p "$CASE_DIR/etc/config" "$CASE_DIR/rom/etc/config"
  CONFIG="$CASE_DIR/etc/config/athena_led"
  ROM="$CASE_DIR/rom/etc/config/athena_led"
  BACKUP="$CONFIG.config-migrated"
}

run_migration() {
  # Match S10boot's conditional sourcing, not standalone script execution.
  IPKG_INSTROOT="$CASE_DIR" sh -c '( . "$1" ) && exit 0; exit 1' sh "$SCRIPT"
}

assert_same() {
  cmp -s "$1" "$2" || { echo "FAIL: $3" >&2; exit 1; }
}

test_matching() {
  new_case "matching-$1"
  "$1" "$CONFIG" 0 2
  "$1" "$ROM" 1 5
  cp "$CONFIG" "$CASE_DIR/original"
  run_migration
  assert_same "$CONFIG" "$CASE_DIR/original" 'disabled/custom matching config changed'
  [ ! -e "$BACKUP" ] || { echo 'FAIL: matching config backed up'; exit 1; }
}

test_repair() {
  new_case "repair-$1"
  "$1" "$CONFIG" 1 2
  "$2" "$ROM" 1 5
  cp "$CONFIG" "$CASE_DIR/original"
  printf 'prior backup\n' > "$BACKUP"
  cp "$BACKUP" "$CASE_DIR/prior-backup"
  run_migration
  assert_same "$CONFIG" "$ROM" 'mismatch not restored from actual package defaults'
  assert_same "$BACKUP.1" "$CASE_DIR/original" 'incompatible config backup lost'
  assert_same "$BACKUP" "$CASE_DIR/prior-backup" 'prior backup overwritten'
  run_migration
  [ ! -e "$BACKUP.2" ] || { echo 'FAIL: migration not idempotent'; exit 1; }
}

test_invalid() {
  new_case "invalid-$1"
  legacy_config "$CONFIG" 1 2
  legacy_config "$ROM" 1 5
  case "$1" in
    missing-rom) rm "$ROM" ;;
    unknown-rom) printf "config future 'unknown'\n" > "$ROM" ;;
    unknown-current) printf "config future 'unknown'\n" > "$CONFIG" ;;
    mixed-current) modern_config "$CASE_DIR/modern" 1 5
      cat "$CASE_DIR/modern" >> "$CONFIG" ;;
  esac
  cp "$CONFIG" "$CASE_DIR/original"
  if run_migration > "$CASE_DIR/output" 2>&1; then
    echo "FAIL: $1 was silently accepted"; exit 1
  fi
  assert_same "$CONFIG" "$CASE_DIR/original" "$1 modified current config"
  [ ! -e "$BACKUP" ] || { echo "FAIL: $1 backed up before validation"; exit 1; }
}

test_write_failure() {
  new_case "write-failure-$1"
  modern_config "$CONFIG" 1 2
  legacy_config "$ROM" 1 5
  cp "$CONFIG" "$CASE_DIR/original"
  mkdir "$CASE_DIR/bin"
  case "$1" in
    backup) printf '#!/bin/sh\nexit 73\n' > "$CASE_DIR/bin/cp" ;;
    replacement) printf '#!/bin/sh\ncase "$1" in\n-p) exec /bin/cp "$@";;\n*) exit 74;;\nesac\n' > "$CASE_DIR/bin/cp" ;;
    install) printf '#!/bin/sh\nexit 75\n' > "$CASE_DIR/bin/mv" ;;
  esac
  chmod +x "$CASE_DIR/bin/"*
  if PATH="$CASE_DIR/bin:$PATH" run_migration > "$CASE_DIR/output" 2>&1; then
    echo "FAIL: $1 write failure reported success under boot sourcing"; exit 1
  fi
  assert_same "$CONFIG" "$CASE_DIR/original" "$1 failure damaged current config"
  if [ "$1" != backup ]; then
    assert_same "$BACKUP" "$CASE_DIR/original" "$1 failure lost backup"
  fi
}

test_matching legacy_config
test_matching modern_config
test_repair modern_config legacy_config
test_repair legacy_config modern_config
test_invalid missing-rom
test_invalid unknown-rom
test_invalid unknown-current
test_invalid mixed-current
test_write_failure backup
test_write_failure replacement
test_write_failure install
new_case absent-package
run_migration
[ ! -e "$CONFIG" ] || { echo 'FAIL: installed a missing package config'; exit 1; }
echo 'Athena LED migration: 12 real-UCI cases passed'
