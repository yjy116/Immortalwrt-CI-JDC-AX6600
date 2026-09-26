# OpenWRT-CI 
云编译OpenWRT固件，开启内核eBPF，支持DAED 内核级透明代理

官方版：
https://github.com/immortalwrt/immortalwrt.git

高通版：
https://github.com/VIKINGYFY/immortalwrt.git

LiBWrt：
https://github.com/LiBwrt/openwrt-6.x

京东云亚瑟 AX1800 Pro DAED 需要更换分区表和uboot,具体使用方法详见恩山帖子:
https://www.right.com.cn/forum/thread-8402269-1-1.html

# 固件简要说明：

固件每周一早上4点自动清理旧版本，随后编译最新上游源码；也可在 Actions 中手动触发。

固件信息里的时间为编译开始的时间，方便核对上游源码提交时间。

MEDIATEK系列、QUALCOMMAX系列、ROCKCHIP系列、X86系列。

# 目录简要说明：

workflows——自定义CI配置

Scripts——自定义脚本

Config——自定义配置

# 本仓库追加插件

在 darkrain88/daed-immWRT-CI-david 基板上，额外启用以下插件：

- luci-app-qbittorrent
- luci-app-tailscale
- luci-app-easytier
- luci-app-usb-printer
- luci-app-adguardhome
- luci-app-mini-diskmanager

源码构建时从 `VIKINGYFY/immortalwrt` 的 `main` 分支实时拉取，因此每次新构建都会使用当时的最新源码提交。
已选插件优先跟随 ImmortalWrt feeds、VIKINGYFY/OpenWRT-CI 和项目基板维护的当前来源；设备无关插件不会盲目同步。

## DAE / DAED 统一维护

独立 `dae`、`daed` 和 `luci-app-daede` 均来自 [kenzok8/openwrt-daede](https://github.com/kenzok8/openwrt-daede)。旧 `QiuSimons/luci-app-daed`、本地 DAE 包覆盖及两个旧 LuCI 入口已移除，但保留两种代理后端功能。

`dae` 是独立代理核心；`daed` 是前端和 `dae-wing` 后端，内部另嵌一份 DAE 核心，不会调用系统 `/usr/bin/dae`。只升级 DAED 前端不等于升级这两份核心。

当前核验基线：

| 组件 | 版本 / 源码 |
| --- | --- |
| 打包仓库 | `0b0e5d671e5748a060fbd79abc2f73733b09f902` |
| dae / daed | `2026.09.24-r2` |
| luci-app-daede | `1.15-r6` |
| DAED 前端 | `be4ef873c352a9ec930c877a3a821163f4b4ac0a`，包含 v2.1.1 |
| dae-wing | `b089b568649f03f909477adb6c7db25535a58782` |
| 两份 DAE 核心 | 官方 `6f2f2aa66084f3d736e4bf86a327e3523b3cdede` 合并到性能基线 `be2b6047eff8be8da7dfdcd0c007fd6d9f7f5175` |

已核对两份带 SHA-256 校验的源码包：核心实现一致，仅 `go.mod`、`go.sum` 和 PGO 文件位置有差异；依赖和源码固定信息见上游 `ci/pins.env`。源码包内含已构建的 Web 静态资源，Go/eBPF 后端在我们的固件构建中编译，不安装第三方预编译内核包或额外软件源。

`Scripts/Daede.sh` 固定已核验的打包提交；后续跟进上游时更新该提交并重新验证补丁和两组构建，不是永久锁定旧版本。每次 Release 附带 `DAEDE-SOURCE.txt`，便于核对真实构建来源。
本固件的这三个包请通过 GitHub 重新编译升级；使用 daede 界面的在线包更新可能覆盖本仓库的服务互斥补丁。

### 后端切换与升级

- 在「服务 → daede」选择后端。切换先停止当前服务，再关闭两边的 UCI 启用标记和开机自启，最后保存选择；按上游交互设计，切换后需要点击启动。
- 两个后端共享 eBPF/cgroup 附着点，不应同时运行。本仓库补丁还让启动脚本核对所选后端及另一进程状态，覆盖开机和 `/etc/init.d/dae(d) start`；失败明确报错。不要绕过服务管理直接同时运行两个二进制。
- 升级前停止代理并备份 `/etc/config/dae`、`/etc/config/daed`、`/etc/dae/`、`/etc/daed/`（含 `wing.db` 及 WAL）和 `/etc/crontabs/root`。新后端继续使用这些数据路径，但数据库跨版本兼容和实际转发仍须刷机验证。
- 首次启动移除旧 `luci_daed` 和旧热插拔重启脚本；旧订阅 cron 命令替换为新更新器，时间表达式不变，原 cron 留在 `/etc/daede-migration-backup/root.cron`。请在新界面填写 DAED 面板账号密码，再检查订阅自动更新；新更新器需要这些凭据，缺失会报错，不会假报成功。之后在界面保存更新计划时，以新界面的每日/每周选项为准。
- 原来只启用独立 DAE 时保留该后端选择；其他情况采用上游 DAED 默认选择。两边旧启用标记都为 1 时，非选中后端启动会被拒绝，请在界面完成一次切换并确认状态。
- 保留 LAN `192.168.80.1`、SSID `Athena`、现有 Wi-Fi 密码、12 MiB Kernel、NSS/eBPF 和其他插件。选用固件内置 BTF，不使用外部内核 BTF 包。

Both standalone DAE and DAED now use the same reviewed kenzok8 packaging source. DAED embeds its own DAE core; updating only its frontend does not update both cores. Local patches persist exclusive backend selection and reject unsafe service starts. Back up configuration and the stopped database before upgrading; host tests and successful builds do not prove on-device forwarding or database migration.
