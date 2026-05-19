#!/bin/bash
# SPDX-License-Identifier: MIT

set -euo pipefail

DEFAULT_CONFIG="JDC-AX6600"
DEFAULT_THEME="aurora"
DEFAULT_NAME="JDC-AX6600"
DEFAULT_SSID="Athena"
DEFAULT_WORD="77915558"
DEFAULT_IP="192.168.101.1"
DEFAULT_PASSWORD="none"
DEFAULT_REPO="https://github.com/VIKINGYFY/immortalwrt.git"
DEFAULT_BRANCH="main"
DEFAULT_SOURCE="VIKINGYFY/immortalwrt"
MAX_CLONE_DEPTH=1

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
BUILD_DIR="$PROJECT_ROOT/wrt"
ARTIFACT_DIR="$PROJECT_ROOT/artifacts"
DOWNLOAD_DIR="$PROJECT_ROOT/dl"
CONFIG_FILE="$PROJECT_ROOT/Config/${WRT_CONFIG:-$DEFAULT_CONFIG}.txt"

run_privileged() {
	if [ "$(id -u)" -eq 0 ]; then
		"$@"
		return
	fi
	command -v sudo >/dev/null || {
		echo "root or sudo is required for dependency installation." >&2
		return 1
	}
	sudo -E "$@"
}

set_defaults() {
	export GITHUB_WORKSPACE="$PROJECT_ROOT"
	export WRT_CONFIG="${WRT_CONFIG:-$DEFAULT_CONFIG}"
	export WRT_THEME="${WRT_THEME:-$DEFAULT_THEME}"
	export WRT_NAME="${WRT_NAME:-$DEFAULT_NAME}"
	export WRT_SSID="${WRT_SSID:-$DEFAULT_SSID}"
	export WRT_WORD="${WRT_WORD:-$DEFAULT_WORD}"
	export WRT_IP="${WRT_IP:-$DEFAULT_IP}"
	export WRT_PW="${WRT_PW:-$DEFAULT_PASSWORD}"
	export WRT_REPO="${WRT_REPO:-$DEFAULT_REPO}"
	export WRT_BRANCH="${WRT_BRANCH:-$DEFAULT_BRANCH}"
	export WRT_SOURCE="${WRT_SOURCE:-$DEFAULT_SOURCE}"
	export WRT_PACKAGE="${WRT_PACKAGE:-}"
	export WRT_TEST="${WRT_TEST:-false}"
	export CCACHE_DIR="$PROJECT_ROOT/.ccache"
	CONFIG_FILE="$PROJECT_ROOT/Config/$WRT_CONFIG.txt"
}

install_dependencies() {
	export DEBIAN_FRONTEND=noninteractive
	run_privileged apt-get update
	run_privileged apt-get install -y --no-install-recommends \
		ca-certificates curl dos2unix file git jq libfuse-dev \
		python3-netifaces rsync
	run_privileged bash -c 'bash <(curl -fsSL https://build-scripts.immortalwrt.org/init_build_environment.sh)'
}

init_values() {
	local repo_slug

	[ -f "$CONFIG_FILE" ] || { echo "Missing config file: $CONFIG_FILE" >&2; return 1; }
	WRT_TARGET=$(sed -n 's/^CONFIG_TARGET_\([A-Za-z0-9_]\+\)=y$/\1/p' "$CONFIG_FILE" | head -n 1)
	WRT_DEVICE=$(sed -n 's/^CONFIG_TARGET_DEVICE_[^=]*_DEVICE_\([A-Za-z0-9_-]\+\)=y$/\1/p' "$CONFIG_FILE" | head -n 1)
	[ -n "$WRT_TARGET" ] || { echo "Unable to detect WRT_TARGET from $CONFIG_FILE" >&2; return 1; }
	[ -n "$WRT_DEVICE" ] || { echo "Unable to detect WRT_DEVICE from $CONFIG_FILE" >&2; return 1; }

	repo_slug="${CNB_REPO_SLUG:-local/JDC-AX6600}"
	export WRT_TARGET WRT_DEVICE
	export WRT_DATE
	export WRT_MARK="${repo_slug%%/*}"
	export WRT_INFO="${WRT_SOURCE%%/*}"
	WRT_DATE=$(TZ=UTC-8 date +"%y.%m.%d-%H.%M.%S")
}

prepare_workspace() {
	case "$BUILD_DIR" in
		"$PROJECT_ROOT"/wrt) ;;
		*) echo "Unsafe build directory: $BUILD_DIR" >&2; return 1 ;;
	esac
	rm -rf "$BUILD_DIR"
	mkdir -p "$BUILD_DIR" "$ARTIFACT_DIR" "$DOWNLOAD_DIR" "$CCACHE_DIR"
	find "$ARTIFACT_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

clone_source() {
	git clone --depth="$MAX_CLONE_DEPTH" --single-branch --branch "$WRT_BRANCH" "$WRT_REPO" "$BUILD_DIR"
	WRT_HASH=$(git -C "$BUILD_DIR" log -1 --pretty=format:'%h')
	export WRT_HASH

	local mirrors_file="$BUILD_DIR/scripts/projectsmirrors.json"
	[ -f "$mirrors_file" ] && sed -i '/.cn\//d; /tencent/d; /aliyun/d' "$mirrors_file"
	rm -rf "$BUILD_DIR/dl"
	ln -s "$DOWNLOAD_DIR" "$BUILD_DIR/dl"
}

normalize_scripts() {
	find "$PROJECT_ROOT/Config" "$PROJECT_ROOT/Scripts" -type f \
		\( -name "*.txt" -o -name "*.sh" \) \
		-exec dos2unix {} \; -exec chmod +x {} \;
}

update_feeds() {
	cd "$BUILD_DIR"
	./scripts/feeds update -a
	./scripts/feeds install -a
}

apply_customizations() {
	cd "$BUILD_DIR/package"
	"$PROJECT_ROOT/Scripts/Packages.sh"
	"$PROJECT_ROOT/Scripts/Handles.sh"
}

generate_config() {
	cd "$BUILD_DIR"
	cat "$CONFIG_FILE" "$PROJECT_ROOT/Config/GENERAL.txt" >> .config
	"$PROJECT_ROOT/Scripts/Settings.sh"
	make defconfig -j"$(nproc)"
}

download_packages() {
	[ "$WRT_TEST" != "true" ] || return 0
	cd "$BUILD_DIR"
	make download -j"$(nproc)"
}

compile_firmware() {
	[ "$WRT_TEST" != "true" ] || return 0
	cd "$BUILD_DIR"
	find package/ -name Makefile -path "*/ubus/*" \
		-exec sed -i 's/-Werror/-Wno-error=format-nonliteral/g' {} +
	if make -j"$(nproc)"; then
		return 0
	fi
	echo "Parallel build failed. Running serial V=s once to expose the root cause." >&2
	make -j1 V=s || true
	return 1
}

copy_firmware_files() {
	local file base ext name
	find "$BUILD_DIR/bin/targets" -type f -iname "*$WRT_DEVICE*" | while read -r file; do
		base=$(basename "$file")
		ext="${base#*.}"
		name=$(echo "$base" | grep -io "$WRT_DEVICE[^.]*" | head -n 1)
		cp -f "$file" "$ARTIFACT_DIR/$WRT_INFO-$WRT_BRANCH-$name-$WRT_DATE.$ext"
	done
}

package_artifacts() {
	cd "$BUILD_DIR"
	cp -f .config "$ARTIFACT_DIR/Config-$WRT_CONFIG-$WRT_INFO-$WRT_BRANCH-$WRT_DATE.txt"
	if [ "$WRT_TEST" != "true" ]; then
		copy_firmware_files
		find ./bin/targets -type f \( -name "*.manifest" -o -name "*.buildinfo" -o -name "*sha256sums*" \) \
			-exec cp -f {} "$ARTIFACT_DIR/" \;
	fi
	write_build_info
}

write_build_info() {
	local kernel="none"
	local list="none"
	local targets_dir="$BUILD_DIR/bin/targets"

	if [ -d "$targets_dir" ]; then
		kernel=$(find "$targets_dir" -type f -name "*.manifest" \
			-exec awk '/^kernel - / { print $3; exit }' {} \; | head -n 1)
		list=$(find "$targets_dir" -type f -name "*.manifest" \
			-exec awk '/^luci-(app|theme)/ { print $1 }' {} \; | sort -u | tr '\n' ' ')
	fi
	cat > "$ARTIFACT_DIR/build-info.txt" <<EOF
Firmware: JDCloud Athena / JDC AX6600
Config: $WRT_CONFIG
Target: $WRT_TARGET
Device: $WRT_DEVICE
Source: $WRT_REPO
Branch: $WRT_BRANCH
Source commit: ${WRT_HASH:-unknown}
Login address: $WRT_IP
Login password: $WRT_PW
Wi-Fi SSID: $WRT_SSID
Wi-Fi password: $WRT_WORD
Kernel: ${kernel:-none}
LuCI packages: ${list:-none}
EOF
}

print_machine_info() {
	cd "$BUILD_DIR"
	lscpu
	df -h
	du -h --max-depth=1
}

main() {
	set_defaults
	install_dependencies
	init_values
	prepare_workspace
	clone_source
	normalize_scripts
	update_feeds
	apply_customizations
	generate_config
	download_packages
	compile_firmware
	print_machine_info
	package_artifacts
}

main "$@"
