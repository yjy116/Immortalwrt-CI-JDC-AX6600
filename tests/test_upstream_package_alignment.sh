#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PACKAGES="$ROOT_DIR/Scripts/Packages.sh"
GENERAL="$ROOT_DIR/Config/GENERAL.txt"
ENVIRONMENT="$ROOT_DIR/Scripts/init_build_environment.sh"
CORE_WORKFLOW="$ROOT_DIR/.github/workflows/WRT-CORE.yml"

if grep -Fq 'UPDATE_PACKAGE "gecoosac"' "$PACKAGES"; then
	echo "GecoosAC must have one provider: VIKINGYFY/packages"
	exit 1
fi

if grep -Fq 'UPDATE_PACKAGE "fancontrol"' "$PACKAGES"; then
	echo "fan control must not be fetched for JDCloud Athena"
	exit 1
fi

viking_line="$(grep -F 'UPDATE_PACKAGE "viking"' "$PACKAGES")"
for package in axonhub gecoosac sing-box luci-app-homeproxy luci-app-wolplus luci-app-wolultra
do
	printf '%s\n' "$viking_line" | grep -Fq "$package" || {
		echo "missing VIKINGYFY package replacement alias: $package"
		exit 1
	}
done

grep -Fq 'CONFIG_PACKAGE_luci-app-wolultra=y' "$GENERAL" || {
	echo "current VIKINGYFY WoL package must be selected"
	exit 1
}
if grep -Fq 'CONFIG_PACKAGE_luci-app-wolplus=y' "$GENERAL"; then
	echo "retired VIKINGYFY WoL package must not remain selected"
	exit 1
fi

for package in luci-app-gecoosac luci-app-mini-diskmanager
do
	grep -Fq "CONFIG_PACKAGE_${package}=y" "$GENERAL" || {
		echo "missing selected upstream package: $package"
		exit 1
	}
done

grep -Fq 'UPDATE_PACKAGE "diskman" "sbwml/luci-app-diskman" "main"' "$PACKAGES" || {
	echo "DiskMan source must follow the current VIKINGYFY CI override"
	exit 1
}
grep -Fq 'UPDATE_PACKAGE "diskmanager" "4IceG/luci-app-mini-diskmanager" "main"' "$PACKAGES" || {
	echo "mini-diskmanager source must follow the current VIKINGYFY CI override"
	exit 1
}
grep -Fq 'UPDATE_PACKAGE "lucky" "gdy666/luci-app-lucky" "main"' "$PACKAGES" || {
	echo "Lucky source must follow the current darkrain base override"
	exit 1
}

grep -Fq 'golang-1.25-go' "$ENVIRONMENT" || {
	echo "build environment must match the current ImmortalWrt Go toolchain"
	exit 1
}
if grep -Fq 'golang-1.26-go' "$ENVIRONMENT"; then
	echo "obsolete Go 1.26 request must be removed"
	exit 1
fi
grep -Fq "go-version: '1.25'" "$CORE_WORKFLOW" || {
	echo "setup-go fallback must match the current ImmortalWrt Go toolchain"
	exit 1
}

echo "upstream package alignment guard passed"
