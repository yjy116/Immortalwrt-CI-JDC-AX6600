#!/bin/bash
# SPDX-License-Identifier: MIT

set -euo pipefail

disable_kernel_option() {
	local option=$1
	local config_dir=$2
	[ -d "$config_dir" ] || return 0
	find "$config_dir" -maxdepth 1 -type f -name "config-*" | while read -r config_file; do
		sed -i "/^CONFIG_${option}=\\|^# CONFIG_${option} is not set/d" "$config_file"
		echo "# CONFIG_${option} is not set" >> "$config_file"
	done
}

apply_sed_to_matches() {
	local search_dir=$1
	local file_name=$2
	local sed_expr=$3
	find "$search_dir" -type f -name "$file_name" 2>/dev/null | while read -r target_file; do
		sed -i "$sed_expr" "$target_file"
	done
}

set_sysctl_value() {
	local key=$1
	local value=$2
	local file=$3
	local escaped_key=${key//./\\.}
	sed -i "/^${escaped_key}=/d" "$file"
	echo "$key=$value" >> "$file"
}

ensure_min_sysctl_value() {
	local key=$1
	local min_value=$2
	local file=$3
	local escaped_key=${key//./\\.}
	local current_value

	current_value=$(sed -n "s/^${escaped_key}=\\([0-9]\\+\\).*/\\1/p" "$file")
	if [ -z "$current_value" ] || [ "$current_value" -lt "$min_value" ]; then
		set_sysctl_value "$key" "$min_value" "$file"
	fi
}

write_network_accel_defaults() {
	local defaults_dir="./package/base-files/files/etc/uci-defaults"
	local defaults_file="$defaults_dir/99-jdc-ax6600-network-accel"
	mkdir -p "$defaults_dir"
cat > "$defaults_file" <<'EOF'
#!/bin/sh
set -e

uci -q set network.globals='globals'
uci -q set network.globals.packet_steering='1'
uci -q commit network

uci -q set irqbalance.irqbalance='irqbalance'
uci -q set irqbalance.irqbalance.enabled='1'
uci -q commit irqbalance
[ -x /etc/init.d/irqbalance ] && /etc/init.d/irqbalance enable

exit 0
EOF
	chmod +x "$defaults_file"
}

apply_sed_to_matches "./feeds/luci/collections/" "Makefile" "/attendedsysupgrade/d"
apply_sed_to_matches "./feeds/luci/collections/" "Makefile" "s/luci-theme-bootstrap/luci-theme-$WRT_THEME/g"
apply_sed_to_matches "./feeds/luci/modules/luci-mod-system/" "flash.js" "s/192\\.168\\.[0-9]*\\.[0-9]*/$WRT_IP/g"
apply_sed_to_matches "./feeds/luci/modules/luci-mod-status/" "10_system.js" "s/(\\(luciversion || ''\\))/(\\1) + (' \\/ $WRT_MARK-$WRT_DATE')/g"

wifi_sh=$(find ./target/linux/{mediatek/filogic,qualcommax}/base-files/etc/uci-defaults/ -type f -name "*set-wireless.sh" 2>/dev/null | head -n 1)
wifi_uc="./package/network/config/wifi-scripts/files/lib/wifi/mac80211.uc"
if [ -n "$wifi_sh" ]; then
	sed -i "s/BASE_SSID='.*'/BASE_SSID='$WRT_SSID'/g" "$wifi_sh"
	sed -i "s/BASE_WORD='.*'/BASE_WORD='$WRT_WORD'/g" "$wifi_sh"
elif [ -f "$wifi_uc" ]; then
	sed -i "s/ssid='.*'/ssid='$WRT_SSID'/g" "$wifi_uc"
	sed -i "s/key='.*'/key='$WRT_WORD'/g" "$wifi_uc"
	sed -i "s/country='.*'/country='CN'/g" "$wifi_uc"
	sed -i "s/encryption='.*'/encryption='psk2+ccmp'/g" "$wifi_uc"
fi

cfg_file="./package/base-files/files/bin/config_generate"
sed -i "s/192\.168\.[0-9]*\.[0-9]*/$WRT_IP/g" "$cfg_file"
sed -i "s/hostname='.*'/hostname='$WRT_NAME'/g" "$cfg_file"

echo "CONFIG_PACKAGE_luci=y" >> ./.config
echo "CONFIG_LUCI_LANG_zh_Hans=y" >> ./.config
echo "CONFIG_PACKAGE_luci-theme-$WRT_THEME=y" >> ./.config
echo "CONFIG_PACKAGE_luci-app-$WRT_THEME-config=y" >> ./.config

if [ -f "$GITHUB_WORKSPACE/Config/PRIVATE.txt" ]; then
	cat "$GITHUB_WORKSPACE/Config/PRIVATE.txt" >> ./.config
fi

if [ -n "${WRT_PACKAGE:-}" ]; then
	echo -e "$WRT_PACKAGE" >> ./.config
fi

if [[ "${WRT_TARGET^^}" == *"QUALCOMMAX"* ]]; then
	disable_kernel_option "ARM64_BRBE" "./target/linux/qualcommax"
	disable_kernel_option "ARM64_BRBE" "./target/linux/qualcommax/ipq60xx"
	echo "CONFIG_FEED_nss_packages=n" >> ./.config
	echo "CONFIG_FEED_sqm_scripts_nss=n" >> ./.config
	echo "CONFIG_NSS_FIRMWARE_VERSION_12_5=y" >> ./.config
	echo "CONFIG_PACKAGE_kmod-usb-serial-qualcomm=y" >> ./.config
	write_network_accel_defaults
fi

sysctl_file="./package/base-files/files/etc/sysctl.conf"
min_free_kbytes=16384
ensure_min_sysctl_value "vm.min_free_kbytes" "$min_free_kbytes" "$sysctl_file"
set_sysctl_value "net.core.default_qdisc" "fq" "$sysctl_file"
set_sysctl_value "net.ipv4.tcp_congestion_control" "bbr" "$sysctl_file"
