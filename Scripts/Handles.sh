#!/bin/bash
# SPDX-License-Identifier: MIT

set -euo pipefail

PKG_PATH="$GITHUB_WORKSPACE/wrt/package/"

if [ -d *"homeproxy"* ]; then
	hp_rule="surge"
	hp_path="homeproxy/root/etc/homeproxy"
	rm -rf "./$hp_path/resources/"*
	git clone -q --depth=1 --single-branch --branch "release" "https://github.com/Loyalsoldier/surge-rules.git" "./$hp_rule/"
	cd "./$hp_rule/"
	res_ver=$(git log -1 --pretty=format:'%s' | grep -o "[0-9]*")
	echo "$res_ver" | tee china_ip4.ver china_ip6.ver china_list.ver gfw_list.ver
	awk -F, '/^IP-CIDR,/{print $2 > "china_ip4.txt"} /^IP-CIDR6,/{print $2 > "china_ip6.txt"}' cncidr.txt
	sed 's/^\.//g' direct.txt > china_list.txt
	sed 's/^\.//g' gfw.txt > gfw_list.txt
	mv -f ./{china_*,gfw_list}.{ver,txt} "../$hp_path/resources/"
	cd ..
	rm -rf "./$hp_rule/"
	cd "$PKG_PATH"
fi

homeproxy_makefile="../feeds/luci/applications/luci-app-homeproxy/Makefile"
if [ -f "$homeproxy_makefile" ]; then
	sed -i 's#+sing-box[[:space:]]*\\#+sing-box-tiny \\#g' "$homeproxy_makefile"
fi

if [ -d *"luci-theme-argon"* ]; then
	cd ./luci-theme-argon/
	sed -i "s/primary '.*'/primary '#31a1a1'/; s/'0.2'/'0.5'/; s/'none'/'bing'/; s/'600'/'normal'/" ./luci-app-argon-config/root/etc/config/argon
	cd "$PKG_PATH"
fi

if [ -d *"luci-app-aurora-config"* ]; then
	cd ./luci-app-aurora-config/
	find ./root/usr/share/aurora/ -type f -name "*.template" -exec sed -i "s/nav_submenu_type '.*'/nav_submenu_type 'boxed-dropdown'/g" {} +
	cd "$PKG_PATH"
fi

if [ -d *"luci-app-mini-diskmanager"* ]; then
	menu="./luci-app-mini-diskmanager/root/usr/share/luci/menu.d/luci-app-mini-diskmanager.json"
	sed -i "s/services/system/g" "$menu"
fi

if [ -d "./JDC-AX6600-Athena-LED-Controller/luci-app-athena-led" ]; then
	rm -rf ./luci-app-athena-led
	mv ./JDC-AX6600-Athena-LED-Controller/luci-app-athena-led ./luci-app-athena-led
	rm -rf ./JDC-AX6600-Athena-LED-Controller
fi

if [ -d "./luci-app-athena-led" ]; then
	mkdir -p ./luci-app-athena-led/root/usr/bin
	if [ ! -f ./luci-app-athena-led/root/usr/bin/find_button.sh ]; then
		cp "$GITHUB_WORKSPACE/Scripts/find_button.sh" ./luci-app-athena-led/root/usr/bin/find_button.sh
	fi
fi

if [ -d "./OpenWrt-nikki/mihomo-alpha" ] && [ -d "./OpenWrt-nikki/mihomo-meta" ]; then
	echo "Removing OpenWrt-nikki/mihomo-alpha to avoid Kconfig recursion with mihomo-meta."
	rm -rf ./OpenWrt-nikki/mihomo-alpha
fi

if [ -f "./luci-app-iperf3/Makefile" ]; then
	sed -i 's#include ../../luci.mk#include $(TOPDIR)/feeds/luci/luci.mk#g' ./luci-app-iperf3/Makefile
fi

nss_drv="../feeds/nss_packages/qca-nss-drv/files/qca-nss-drv.init"
if [ -f "$nss_drv" ]; then
	sed -i 's/START=.*/START=85/g' "$nss_drv"
fi

nss_pbuf="./kernel/mac80211/files/qca-nss-pbuf.init"
if [ -f "$nss_pbuf" ]; then
	sed -i 's/START=.*/START=86/g' "$nss_pbuf"
fi

ts_file=$(find ../feeds/packages/ -maxdepth 3 -type f -wholename "*/tailscale/Makefile" -print -quit)
if [ -n "$ts_file" ]; then
	sed -i '/\/files/d' "$ts_file"
fi

rust_file=$(find ../feeds/packages/ -maxdepth 3 -type f -wholename "*/rust/Makefile" -print -quit)
if [ -n "$rust_file" ]; then
	sed -i 's/ci-llvm=true/ci-llvm=false/g' "$rust_file"
fi
