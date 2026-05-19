#!/bin/bash
# SPDX-License-Identifier: MIT

set -euo pipefail

update_package() {
	local pkg_name=$1
	local pkg_repo=$2
	local pkg_branch=$3
	local pkg_special=${4:-}
	local pkg_aliases=${5:-}
	local repo_name=${pkg_repo#*/}

	echo "Updating package: $pkg_name"
	for name in $pkg_name $pkg_aliases; do
		find ../feeds/luci/ ../feeds/packages/ -maxdepth 3 -type d -iname "*$name*" 2>/dev/null | while read -r dir; do
			rm -rf "$dir"
			echo "Deleted package directory: $dir"
		done
	done

	git clone --depth=1 --single-branch --branch "$pkg_branch" "https://github.com/$pkg_repo.git"

	if [[ "$pkg_special" == "pkg" ]]; then
		local tmp_dir
		local pkg_dir
		tmp_dir=$(mktemp -d)
		pkg_dir=$(find "./$repo_name" -mindepth 2 -maxdepth 4 -type f -name Makefile -path "*$pkg_name*" -printf '%h\n' | head -n 1)
		[ -n "$pkg_dir" ] || { echo "Package directory not found: $pkg_name in $repo_name" >&2; exit 1; }
		cp -rf "$pkg_dir" "$tmp_dir/"
		rm -rf "./$repo_name/"
		cp -rf "$tmp_dir/$(basename "$pkg_dir")" ./
		rm -rf "$tmp_dir"
		return
	fi

	if [[ "$pkg_special" == "name" ]]; then
		mv -f "$repo_name" "$pkg_name"
	fi
}

update_version() {
	local pkg_name=$1
	local pkg_mark=${2:-false}
	local pkg_files

	pkg_files=$(find ./ ../feeds/packages/ -maxdepth 3 -type f -wholename "*/$pkg_name/Makefile")
	[ -n "$pkg_files" ] || { echo "$pkg_name not found."; return; }

	for pkg_file in $pkg_files; do
		local pkg_repo pkg_tag old_ver old_url old_file old_hash pkg_url new_ver new_url new_hash
		pkg_repo=$(grep -Po "PKG_SOURCE_URL:=https://.*github.com/\K[^/]+/[^/]+(?=.*)" "$pkg_file")
		pkg_tag=$(curl -fsSL "https://api.github.com/repos/$pkg_repo/releases" | jq -r "map(select(.prerelease == $pkg_mark)) | first | .tag_name")
		old_ver=$(grep -Po "PKG_VERSION:=\K.*" "$pkg_file")
		old_url=$(grep -Po "PKG_SOURCE_URL:=\K.*" "$pkg_file")
		old_file=$(grep -Po "PKG_SOURCE:=\K.*" "$pkg_file")
		old_hash=$(grep -Po "PKG_HASH:=\K.*" "$pkg_file")
		pkg_url=$([[ "$old_url" == *"releases"* ]] && echo "${old_url%/}/$old_file" || echo "${old_url%/}")
		new_ver=$(echo "$pkg_tag" | sed -E 's/[^0-9]+/\./g; s/^\.|\.$//g')
		new_url=$(echo "$pkg_url" | sed "s/\$(PKG_VERSION)/$new_ver/g; s/\$(PKG_NAME)/$pkg_name/g")
		new_hash=$(curl -fsSL "$new_url" | sha256sum | cut -d ' ' -f 1)

		echo "$pkg_name old: $old_ver $old_hash"
		echo "$pkg_name new: $new_ver $new_hash"
		if [[ "$new_ver" =~ ^[0-9].* ]] && dpkg --compare-versions "$old_ver" lt "$new_ver"; then
			sed -i "s/PKG_VERSION:=.*/PKG_VERSION:=$new_ver/g" "$pkg_file"
			sed -i "s/PKG_HASH:=.*/PKG_HASH:=$new_hash/g" "$pkg_file"
		fi
	done
}

update_package "argon" "sbwml/luci-theme-argon" "openwrt-25.12"
update_package "aurora" "eamonxg/luci-theme-aurora" "master"
update_package "aurora-config" "eamonxg/luci-app-aurora-config" "master"
update_package "kucat" "sirpdboy/luci-theme-kucat" "master"
update_package "kucat-config" "sirpdboy/luci-app-kucat-config" "master"

update_package "athena-led" "unraveloop/JDC-AX6600-Athena-LED-Controller" "main"
update_package "momo" "nikkinikki-org/OpenWrt-momo" "main"
update_package "nikki" "nikkinikki-org/OpenWrt-nikki" "main"
update_package "openclash" "vernesong/OpenClash" "dev" "pkg"
update_package "passwall" "Openwrt-Passwall/openwrt-passwall" "main" "pkg"
update_package "passwall2" "Openwrt-Passwall/openwrt-passwall2" "main" "pkg"
update_package "luci-app-tailscale" "asvow/luci-app-tailscale" "main"

update_package "ddns-go" "sirpdboy/luci-app-ddns-go" "main"
update_package "diskman" "sbwml/luci-app-diskman" "main"
update_package "luci-app-mini-diskmanager" "4IceG/luci-app-mini-diskmanager" "main" "pkg"
update_package "easytier" "EasyTier/luci-app-easytier" "main"
update_package "luci-app-iperf3" "Gevatter-Tod/luci-app-iperf3" "main"
update_package "netwizard" "sirpdboy/luci-app-netwizard" "main"
update_package "openlist2" "sbwml/luci-app-openlist2" "main"
update_package "partexp" "sirpdboy/luci-app-partexp" "main"
update_package "qbittorrent" "sbwml/luci-app-qbittorrent" "master" "" "qt6base qt6tools rblibtorrent"
update_package "qmodem" "FUjr/QModem" "main"
update_package "quickfile" "sbwml/luci-app-quickfile" "main"
update_package "timecontrol" "sirpdboy/luci-app-timecontrol" "main"
update_package "viking" "VIKINGYFY/packages" "main" "" "luci-app-timewol luci-app-wolplus"
update_package "vnt" "lmq8267/luci-app-vnt" "main"

if [ -f "$GITHUB_WORKSPACE/Scripts/PRIVATE.sh" ]; then
	source "$GITHUB_WORKSPACE/Scripts/PRIVATE.sh"
fi
