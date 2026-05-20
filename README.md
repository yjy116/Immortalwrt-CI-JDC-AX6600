# ImmortalWrt CI for JDCloud Athena / JDC AX6600

京东云雅典娜 / JDC AX6600 (`jdcloud_re-cs-02`) 的 ImmortalWrt GitHub Actions 编译项目。

An ImmortalWrt GitHub Actions build project for JDCloud Athena / JDC AX6600 (`jdcloud_re-cs-02`).

## 中文说明

### 项目定位

本仓库用于通过 GitHub Actions 编译京东云雅典娜 / JDC AX6600 2G 大分区固件。插件配置以 `yjy116/Immortalwrt-CI-GL-AXT1800` 为主，已移除 AXT1800 专用风扇控件，并结合 `VIKINGYFY/OpenWRT-CI`、`ones20250/Openwrt-AX6600`、`iamdjofoburs/Openwrt-AX6600` 与 `davidtall/OpenWRT-CI` 中针对 AX6600 的 eMMC、LED、NSS、无线、分区工具和大分区 Kernel 设置。

### 设备配置

- 设备：京东云雅典娜 / JDC AX6600
- OpenWrt profile：`jdcloud_re-cs-02`
- Target：`qualcommax/ipq60xx`
- 固件类型：2G 大分区固件，构建时将 `jdcloud_re-cs-02` 的 `KERNEL_SIZE` 调整为 `12288k`
- 默认地址：`192.168.101.1`
- 默认 Wi-Fi：`Athena`
- 默认 Wi-Fi 密码：`77915558`
- 默认主题：`aurora`

### 已启用的重点内容

- 保留 AXT1800 仓库的主要插件配置，去除 `luci-app-fancontrol` 与相关风扇控件。
- 添加 `luci-app-qbittorrent`，并从 `sbwml/luci-app-qbittorrent` 拉取插件源码。
- 添加雅典娜 LED 屏控制插件 `luci-app-athena-led`，并补齐构建所需的 `find_button` 辅助脚本。
- 添加 eMMC、分区扩容、自动挂载相关组件，包括 `block-mount`、`kmod-mmc`、`kmod-sdhci-msm`、`resize2fs`、`tune2fs` 等。
- 补齐 `ones20250/Openwrt-AX6600` 中启用而本仓库缺少的插件和包，包括 Sentinel、ARP bind、firewall4、NSS 驱动组、`athena-led-control`、`iptasn`、`iperf3`、OpenSSL 与 USB QMI 相关模块。
- 保留高通平台相关处理：NSS feed 控制、NSS 固件版本设置、NSS init 启动顺序调整、`ARM64_BRBE` 关闭。
- 参考 `davidtall/OpenWRT-CI` 的大分区路线，将 `jdcloud_re-cs-02` 的 `KERNEL_SIZE` 从默认 `6144k` 调整为 `12288k`。
- 保留 daed/eBPF/BTF、HomeProxy、OpenClash、Tailscale、EasyTier、ZeroTier、Samba、AdGuardHome、SQM、TTYD 等常用插件。

### 刷机提醒

本仓库当前产物面向已刷 2G 大分区和对应 U-Boot 的京东云雅典娜 / JDC AX6600。普通 6MiB kernel 分区环境不建议刷入本固件，否则可能因 kernel 分区不足导致刷写或启动失败。

### GitHub Actions 手动编译

1. 进入 GitHub Actions。
2. 选择 `京东云雅典娜2G大分区固件` workflow。
3. 点击 `Run workflow`。
4. 如需临时增删配置，在 `PACKAGE` 输入框填入额外 `.config` 行，多行使用换行分隔。
5. 如只想生成配置文件，将 `TEST` 设为 `true`。

编译完成后，固件和最终 `.config` 会发布到 GitHub Releases。

### GitHub Actions 缓存

默认不需要定期清理 cache。GitHub 会自动淘汰长期未访问的缓存，仓库缓存也有容量限制；正常情况下保留缓存可以明显减少重复下载和工具链构建时间。

如果遇到以下情况，可以手动运行 `一键清理缓存` workflow，把本仓库的 GitHub Actions cache 全部清掉：

- Actions 日志出现 cache restore/save 失败、缓存损坏或磁盘空间不足。
- 上游源码、工具链或 target 发生较大变化，怀疑旧缓存导致异常。
- 多次编译失败且错误位置不稳定，需要先排除脏缓存影响。

操作方式：

1. 进入 GitHub Actions。
2. 选择 `一键清理缓存` workflow。
3. 点击 `Run workflow`。
4. 清理完成后，再运行 `京东云雅典娜固件` workflow 重新编译。

`一键清理缓存` 只删除 GitHub Actions cache，不会删除 Releases、固件产物、源码文件、workflow 运行记录或仓库内容。清理后的第一次编译会重新下载源码包并重建工具链缓存，因此耗时会更长；后续编译会重新积累 cache。

### 自动编译

`Auto-Build` 每 10 天检查一次 `VIKINGYFY/immortalwrt:main` 近期更新。检测到上游更新后，会先清理旧 Release 和 workflow 运行记录，再触发 `京东云雅典娜2G大分区固件` 正式编译。

### 目录结构

```text
.
|-- Config/
|   |-- JDC-AX6600.txt
|   `-- GENERAL.txt
|-- Scripts/
|   |-- Handles.sh
|   |-- Packages.sh
|   |-- Settings.sh
|   `-- find_button.sh
`-- .github/workflows/
    |-- Auto-Build.yml
    |-- Clear-Cache.yml
    |-- JDC-AX6600.yml
    `-- WRT-CORE.yml
```

### 参考来源

- `yjy116/Immortalwrt-CI-GL-AXT1800`：插件基线、工作流风格、通用脚本。
- `VIKINGYFY/OpenWRT-CI`：IPQ60XX/QCA 通用配置、NSS 相关处理、包管理脚本。
- `ones20250/Openwrt-AX6600`：AX6600 单设备 profile、eMMC/LED/无线/内存调优设置。
- `iamdjofoburs/Openwrt-AX6600`：AX6600 标准 6MiB Kernel 限制下的轻量配置对照。
- `davidtall/OpenWRT-CI`：daed/eBPF 大分区路线和 `KERNEL_SIZE=12288k` 处理方式。
- `unraveloop/JDC-AX6600-Athena-LED-Controller`：雅典娜 LED 屏 LuCI 插件。

## English

### Purpose

This repository builds 2G large-partition ImmortalWrt firmware for JDCloud Athena / JDC AX6600 through GitHub Actions. The package baseline follows `yjy116/Immortalwrt-CI-GL-AXT1800`, with AXT1800 fan-control pieces removed. Device-specific settings for eMMC, LED, NSS, wireless tuning, partition tools, and large-partition kernel sizing are merged from the referenced AX6600 repositories.

### Device

- Device: JDCloud Athena / JDC AX6600
- OpenWrt profile: `jdcloud_re-cs-02`
- Target: `qualcommax/ipq60xx`
- Firmware type: 2G large-partition build with `KERNEL_SIZE=12288k` for `jdcloud_re-cs-02`
- Default address: `192.168.101.1`
- Default Wi-Fi SSID: `Athena`
- Default Wi-Fi password: `77915558`
- Default theme: `aurora`

### Highlights

- Keeps the main plugin set from the AXT1800 repository while removing `luci-app-fancontrol`.
- Adds qBittorrent through `luci-app-qbittorrent` from `sbwml/luci-app-qbittorrent`.
- Adds Athena LED screen support through `luci-app-athena-led` and a build-time `find_button` helper.
- Adds eMMC, partition expansion, and automount packages such as `block-mount`, `kmod-mmc`, `kmod-sdhci-msm`, `resize2fs`, and `tune2fs`.
- Adds plugin and package selections enabled by `ones20250/Openwrt-AX6600` but missing here, including Sentinel, ARP bind, firewall4, NSS driver packages, `athena-led-control`, `iptasn`, `iperf3`, OpenSSL, and USB QMI modules.
- Keeps Qualcomm platform handling for NSS feed control, NSS firmware version, NSS init order, and `ARM64_BRBE` disablement.
- Follows the large-partition route from `davidtall/OpenWRT-CI` and sets `jdcloud_re-cs-02` `KERNEL_SIZE` from the default `6144k` to `12288k`.
- Keeps daed/eBPF/BTF, HomeProxy, OpenClash, Tailscale, EasyTier, ZeroTier, Samba, AdGuardHome, SQM, and TTYD.

### Flashing Notice

The generated images target JDCloud Athena / JDC AX6600 devices already using the 2G large-partition layout and matching U-Boot. They are not recommended for the stock 6 MiB kernel partition layout because the kernel image may not fit.

### Build

Run the `京东云雅典娜2G大分区固件` workflow manually from GitHub Actions. Use `PACKAGE` to append temporary `.config` lines, and set `TEST` to `true` when you only want to generate the final config without compiling firmware.

The generated firmware and final config are uploaded to GitHub Releases.

### Cache Cleanup

Cache cleanup is not needed regularly. GitHub can evict stale cache entries automatically, and keeping cache normally makes builds faster.

Run the `一键清理缓存` workflow only when cache restore/save fails, disk space becomes tight, upstream source/toolchain changes are large, or repeated failures look like cache pollution. It deletes all GitHub Actions cache entries in this repository, but it does not delete Releases, firmware files, source files, workflow run history, or repository content. The first build after cleanup will be slower because caches need to be rebuilt.
