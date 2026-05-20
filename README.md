# ImmortalWrt CI for JDCloud Athena / JDC AX6600

本仓库用于通过 GitHub Actions 编译京东云雅典娜 / JDC AX6600 (`jdcloud_re-cs-02`) 固件。

当前路线以 [davidtall/DaeWRT-CI](https://github.com/davidtall/DaeWRT-CI) 为模板基座，保留模板原有 daed、dae、nikki、eBPF、NSS、SKB recycler、IPQ60XX-WIFI 等配置，再追加本仓库需要的 JDC AX6600 单设备、大分区和插件配置。

## 设备配置

- 设备：京东云雅典娜 / JDC AX6600
- OpenWrt profile：`jdcloud_re-cs-02`
- Target：`qualcommax/ipq60xx`
- 固件类型：大分区固件，构建时把 `KERNEL_SIZE` 从 `6144k` 调整为 `12288k`
- 默认地址：`192.168.80.1`
- 默认 Wi-Fi：`Athena`
- 默认 Wi-Fi 密码：`77915558`
- 默认主题：`aurora`

## 大分区提醒

本仓库默认构建 12MiB Kernel 大分区固件，适合已经刷入京东云雅典娜大分区补丁的设备。

如果设备仍是原始 6MiB Kernel 分区，请不要直接刷入本仓库生成的 `.bin` 固件。

## 模板保留内容

已同步 DaeWRT-CI 的主要模板文件：

- `Config/GENERAL.txt`
- `Config/IPQ60XX-WIFI.txt`
- `Config/IPQ60XX-NOWIFI.txt`
- `Config/IPQ807X-WIFI.txt`
- `Config/IPQ807X-NOWIFI.txt`
- `Config/MEDIATEK.txt`
- `Config/ROCKCHIP.txt`
- `Config/X86.txt`
- `Scripts/function.sh`
- `Scripts/Settings.sh`
- `Scripts/Packages.sh`
- `Scripts/Handles.sh`
- `Scripts/init_build_environment.sh`
- `package/dae`
- `package/luci-app-dae`
- `package/v2ray-geodata`
- `patches/`
- `files/`
- `tests/`
- `diy.sh`

`Config/JDC-AX6600.txt` 是在 DaeWRT `IPQ60XX-WIFI` 思路上追加的单设备配置，只编译 `jdcloud_re-cs-02`，避免把模板中的全部 IPQ60XX 设备一起编译。

## 追加插件

在不删减 DaeWRT 模板配置的基础上，额外启用：

- `luci-app-qbittorrent`
- `luci-app-mini-diskmanager`
- `luci-app-mountd`
- `luci-app-partexp`
- `luci-app-samba4`
- `luci-app-homeproxy`
- `luci-app-openclash`
- `luci-app-adguardhome`
- `luci-app-tailscale`
- `luci-app-easytier`
- `luci-app-usb-printer`

同步补充的底包包括：

- `qbittorrent`
- `parted`
- `mountd`
- `resize2fs`
- `tune2fs`
- `losetup`
- `samba4-server`
- `wsdd2`
- `adguardhome`
- `tailscale`
- `easytier`
- `p910nd`
- `kmod-usb-printer`

说明：`luci-app-mountd` 在当前 ImmortalWrt 主线 feed 中未检索到明确 LuCI 包，本仓库仍按需求保留该配置，并补入 `mountd` 底包。若上游确实没有该 LuCI 包，`make defconfig` 会在最终配置中体现出来。

## GitHub Actions 编译

1. 进入仓库的 GitHub Actions 页面。
2. 选择 `京东云雅典娜 DaeWRT 大分区固件`。
3. 点击 `Run workflow`。
4. `PACKAGE` 可临时追加 `.config` 行，多行使用换行分隔。
5. `TEST=true` 时只生成最终配置，不编译固件。

编译完成后，固件和最终 `.config` 会发布到 GitHub Releases。

## 缓存清理

默认不需要定期清理 cache。正常保留 cache 可以减少重复下载和工具链构建时间。

如果遇到缓存损坏、上游大改、工具链污染、错误位置不稳定等情况，可以手动运行 `一键清理缓存` workflow。它只删除 GitHub Actions cache，不会删除 Releases、固件产物、源码文件、workflow 运行记录或仓库内容。

## 参考来源

- [davidtall/DaeWRT-CI](https://github.com/davidtall/DaeWRT-CI)：当前模板基座。
- [VIKINGYFY/OpenWRT-CI](https://github.com/VIKINGYFY/OpenWRT-CI)：高通 / IPQ60XX / NSS 编译路线参考。
- [ones20250/Openwrt-AX6600](https://github.com/ones20250/Openwrt-AX6600)：京东云雅典娜设备特化参考。
- [yjy116/Immortalwrt-CI-GL-AXT1800](https://github.com/yjy116/Immortalwrt-CI-GL-AXT1800)：既有插件需求来源。

## English

This repository builds ImmortalWrt firmware for JDCloud Athena / JDC AX6600 (`jdcloud_re-cs-02`) with GitHub Actions.

It uses [davidtall/DaeWRT-CI](https://github.com/davidtall/DaeWRT-CI) as the base template, keeps the template daed/dae/nikki/eBPF/NSS/SKB recycler/IPQ60XX-WIFI configuration, and adds the requested JDC AX6600 single-device, large-partition, and plugin selections.

The build changes `KERNEL_SIZE` from `6144k` to `12288k`, so the generated `.bin` image is intended only for devices that have already been flashed with the large-partition patch.
