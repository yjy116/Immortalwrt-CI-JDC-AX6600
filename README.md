# ImmortalWrt CI for JDCloud Athena / JDC AX6600

京东云雅典娜 / JDC AX6600 (`jdcloud_re-cs-02`) 的 ImmortalWrt 云编译项目。  
An ImmortalWrt cloud build project for JDCloud Athena / JDC AX6600 (`jdcloud_re-cs-02`).

## 中文说明

### 项目定位

本仓库用于在 GitHub Actions 上自动编译京东云雅典娜 / JDC AX6600 固件。插件配置以 `yjy116/Immortalwrt-CI-GL-AXT1800` 为主，已移除 AXT1800 专用风扇控件，并结合 `VIKINGYFY/OpenWRT-CI` 与 `ones20250/Openwrt-AX6600` 中针对 AX6600 的 eMMC、LED、NSS、无线和分区工具设置。

### 设备配置

- 设备：京东云雅典娜 / JDC AX6600
- OpenWrt profile：`jdcloud_re-cs-02`
- Target：`qualcommax/ipq60xx`
- 默认地址：`192.168.101.1`
- 默认 Wi-Fi：`Athena`
- 默认 Wi-Fi 密码：`77915558`
- 默认主题：`aurora`

### 已启用的重点内容

- 继承 AXT1800 仓库的主要插件配置，去除 `luci-app-fancontrol` 与相关风扇控件。
- 添加 `luci-app-qbittorrent`，并从 `sbwml/luci-app-qbittorrent` 拉取插件源码。
- 添加雅典娜 LED 屏控制插件 `luci-app-athena-led`，并补齐构建所需的 `find_button` 辅助脚本。
- 添加 eMMC / 分区扩容 / 自动挂载相关组件：`block-mount`、`kmod-mmc`、`kmod-sdhci-msm`、`resize2fs`、`tune2fs` 等。
- 补齐 `ones20250/Openwrt-AX6600` 中启用而本仓库缺少的插件和包，包括 Sentinel、ARP bind、firewall4、NSS 驱动组、`athena-led-control`、`iptasn`、`iperf3`、OpenSSL 与 USB QMI 相关模块。
- 保留高通平台相关处理：NSS feed 控制、NSS 固件版本设置、NSS init 启动顺序调整、`ARM64_BRBE` 关闭。
- 保留 HomeProxy、OpenClash、daed、Tailscale、EasyTier、ZeroTier、Samba、AdGuardHome、SQM、TTYD 等常用插件。

### 手动编译

1. 进入 GitHub Actions。
2. 选择 `JDC-AX6600` workflow。
3. 点击 `Run workflow`。
4. 如需临时增删配置，在 `PACKAGE` 输入框填入额外 `.config` 行，多行使用 `\n` 分隔。
5. 如只想生成配置文件，将 `TEST` 设为 `true`。

编译完成后，固件和最终 `.config` 会发布到 Releases。

### 自动编译

`Auto-Build` 每 10 天检查一次 `VIKINGYFY/immortalwrt:main` 近期更新。检测到上游更新后，会先清理旧 Release 和 workflow 运行记录，再触发 `JDC-AX6600` 正式编译。

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
    |-- JDC-AX6600.yml
    `-- WRT-CORE.yml
```

### 参考来源

- `yjy116/Immortalwrt-CI-GL-AXT1800`：插件基线、工作流风格、通用脚本。
- `VIKINGYFY/OpenWRT-CI`：IPQ60XX/QCA 通用配置、NSS 相关处理、包管理脚本。
- `ones20250/Openwrt-AX6600`：AX6600 单设备 profile、eMMC/LED/无线/内存调优设置。
- `unraveloop/JDC-AX6600-Athena-LED-Controller`：雅典娜 LED 屏 LuCI 插件。

## English

### Purpose

This repository builds ImmortalWrt firmware for JDCloud Athena / JDC AX6600 through GitHub Actions. The package baseline follows `yjy116/Immortalwrt-CI-GL-AXT1800`, with the AXT1800 fan-control pieces removed. Device-specific settings for eMMC, LED, NSS, wireless tuning, and partition tools are merged from `VIKINGYFY/OpenWRT-CI` and `ones20250/Openwrt-AX6600`.

### Device

- Device: JDCloud Athena / JDC AX6600
- OpenWrt profile: `jdcloud_re-cs-02`
- Target: `qualcommax/ipq60xx`
- Default address: `192.168.101.1`
- Default Wi-Fi SSID: `Athena`
- Default Wi-Fi password: `77915558`
- Default theme: `aurora`

### Highlights

- Keeps the main plugin set from the AXT1800 repository while removing `luci-app-fancontrol`.
- Adds qBittorrent through `luci-app-qbittorrent` from `sbwml/luci-app-qbittorrent`.
- Adds Athena LED screen support through `luci-app-athena-led` and a build-time `find_button` helper.
- Adds eMMC, partition expansion, and automount packages such as `block-mount`, `kmod-mmc`, `kmod-sdhci-msm`, `resize2fs`, and `tune2fs`.
- Adds plugin/package selections enabled by `ones20250/Openwrt-AX6600` but missing here, including Sentinel, ARP bind, firewall4, NSS driver packages, `athena-led-control`, `iptasn`, `iperf3`, OpenSSL, and USB QMI modules.
- Keeps Qualcomm platform handling for NSS feed control, NSS firmware version, NSS init order, and `ARM64_BRBE` disablement.

### Build

Run the `JDC-AX6600` workflow manually from GitHub Actions. Use `PACKAGE` to append temporary `.config` lines, and set `TEST` to `true` when you only want to generate the final config without compiling firmware.

The generated firmware and final config are uploaded to GitHub Releases.
