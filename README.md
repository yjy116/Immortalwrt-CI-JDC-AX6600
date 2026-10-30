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
- honk / luci-app-honk（内置 Doona）

`QCA-6.18-VIKINGYFY` 从 `VIKINGYFY/immortalwrt` 的 `owrt` 分支实时拉取，每次新构建使用当时的最新源码提交。编译仓库自身仍在 `main` 分支维护；两者不是同一个分支。
已选插件优先跟随 ImmortalWrt feeds、VIKINGYFY/OpenWRT-CI 和项目基板维护的当前来源；设备无关插件不会盲目同步。

## OWRT PPE + NSS 迁移

2026-10-30 起，6.18 工作流采用 `Config/OWRT/` 的精简设备选择，以上游 `owrt` 的内核基础配置、PPE/EDMA 驱动、NSS 固件、无线固件、内存预留及启动方式为准。`Config/GENERAL.txt` 的现有插件和插件选项不删减，DAE/DAED/Honk 的已核验来源与服务互斥修复不变。原配置文件继续供其他旧工作流使用，不混入本次构建。

- 有线数据通路跟随上游 PPE/EDMA；WIFI 版使用 `ATH11K_NSS_WIFI` 和 `kmod-nss-wifi-drv`，QCN9074 固件由上游设备定义选择。NOWIFI 版去掉无线默认包，保留独立 NSS 驱动，不套用旧 `main` 的 Q6 内存缩减和 SKB recycler 强制选项。
- 保留 `luci-app-sqm`，后端由旧 `sqm-scripts-nss` 改为 feeds 的 `sqm-scripts`，加入上游 `qca-ppe-qos` 与对应 LuCI 界面。旧 NSS qdisc/crypto/ECM 驱动不与新架构混用；这不代表新驱动提供旧驱动全部硬件加速能力。当前 feeds 的 SQM 是否含 `hw_ppe.qos` / `ppe_cake.qos` 必须以实际文件为准，不能仅凭 PPE QoS 界面宣称硬件 CAKE 可用。
- 明确保留的定制例外：现有全部插件及依赖、eBPF/BTF 必要配置、LAN/SSID/现有密码、LED 配置迁移、MiniUPnP/LuCI 修复、已选京东云设备的 12 MiB Kernel。除此以外，不追加旧分支的内核调优或内存配置。
- `defconfig` 后逐项核验请求的软件包及插件子选项；固件打包时核验 manifest，发现丢包明确失败。缓存按源码仓库和分支隔离，staging 额外按源码提交隔离。

从旧 NSS 固件升级时，应备份网络、无线、代理和 SQM 配置。新分支采用不同的网络数据通路，不能假设旧 `ethX` 接口、SQM 的 `nss*.qos` 脚本或整份网络备份可原样恢复；先核对新固件的接口和可用队列脚本，再恢复业务设置。12 MiB 镜像只适用于已完成对应大分区修改的设备。本仓库不会自动修改分区、刷机或重启路由器。

编译与离线检查不能代替实机 WAN/LAN、Wi-Fi、PPPoE/VLAN、UPnP 和透明代理/eBPF 与硬件卸载交互验证；迁移版未完成实测前保留上一版固件作为回退依据。

USB 打印保留 `luci-app-usb-printer`、`p910nd` 和 `kmod-usb-printer`。上游现在要求显式选择 `printer-support`（打印设备组及热插拔规则），本仓库已补齐；构建会在 `defconfig` 后核验整条依赖，避免驱动及界面被静默取消选择。实际 USB 打印仍需连接打印机验证。

## Honk 与内置 Doona

新增 [kenzok8/openwrt-honk](https://github.com/kenzok8/openwrt-honk) 的 `honk` 和 `luci-app-honk`，保留原有 DAE、DAED、daede 管理界面及其他插件。Doona 静态界面随 `luci-app-honk` 安装到 `/usr/share/doona`，不需要另装 `luci-app-doona`，也不额外启动面板服务。

当前核验版本为 `2026.10.12-r1`，打包提交 `52ecdb1bb26e04be782bcb368973fd54d4a44af6`；核心来自 `Glassyiris/honk` 提交 `8b6778cefa12611492187ac2560f014452f0a64a`，Doona 为 `0.1.0-beta.20`、提交 `25fc26a7a17697c1c11a3b31f51940966ac86c2f`。

构建采用上游已发布的静态 musl 核心（雅典娜使用 AArch64）和 Doona 静态资源，再由本仓库的 OpenWrt 工具链打包；**不是在本仓库重新编译 Rust 核心**。`Scripts/Honk.sh` 固定正式版本对应的 `source-38236606118` 资产，并校验三个生成文件的 SHA-256；核心和 Doona 归档继续由 OpenWrt 的 `PKG_HASH` 校验，不使用可变 `staging` 或跳过校验。每次 Release 附带 `HONK-SOURCE.txt`，记录提交、资源校验值和构建来源。后续跟进上游正式版本时需一起更新提交、来源 tag 和生成文件校验值，并复验两组固件，不单独替换核心二进制。

使用说明：

1. 固件保持上游默认：Honk 未初始化、未启用、不开机自启，不会自动接管现有 DAE/DAED。
2. 使用 Honk 前，在 daede 界面停止当前 DAE/DAED 后端并关闭其开机自启；其他透明代理也应先停止。Honk 启动检查会对正在运行的 DAE/DAED 等代理明确报冲突，不会替你自动停止它们。
3. 在「服务 → Honk」初始化、运行系统检查、配置节点或订阅后启动；初始化完成、服务运行且 API 就绪后，再进入 Doona。Honk 需要 Linux 6.12+、内核 BTF 和相应 eBPF 模块，本固件保留这些依赖。管理入口只应在可信 LAN 内使用，不要暴露到 WAN。
4. 切回 DAE/DAED 前，先停止 Honk 并关闭其开机自启，再通过 daede 启动所选后端。daede 原有互斥仅覆盖 DAE 与 DAED，不能把它理解为 Honk 与 DAE/DAED 的双向自动互斥；不要同时开启两套透明代理。

保留 LAN、Wi-Fi、LED 修复、12 MiB Kernel、NSS/eBPF 和缓存策略。主机静态检查和固件编译不等于实机转发验证；Honk/Doona 的启动、订阅、eBPF 转发与 NSS 交互仍需刷入后验证，本任务不会自动刷机或重启路由器。

Honk and bundled Doona are added alongside DAE/DAED, disabled by default. The firmware packages hash-verified upstream static binaries and UI assets, with provenance in `HONK-SOURCE.txt`. Stop the active proxy before switching; on-device forwarding and NSS interaction are not yet validated.

## MiniUPnP 上游修复与自动接续

MiniUPnP 继续跟随 feeds 更新，不固定为 `2.3.11`，不替换 LuCI、启动脚本或用户的 UPnP 配置。构建时补齐以下官方修复：

- [2dcf639](https://github.com/miniupnp/miniupnp/commit/2dcf63959950dbb2c3f97b7bd63773d499749134)：启用 `ext_allow_private_ipv4` 时，WAN 断线后恢复为内网/CGNAT 地址，也能重新允许端口映射。
- [a8de55a](https://github.com/miniupnp/miniupnp/commit/a8de55a0ae4829d59498667120d1e88933dc0f5d)：为 nftables `inet` 表的映射规则添加正确的 IPv4/IPv6 限定，同时包含其前置解析器重构 `320ebf5`。

`Scripts/miniupnpd/install.py` 将钩子接入软件包的 `Prepare/Post`，在**解包和所有 feeds 补丁之后**检查实际源码。缺失时应用本仓库带 SHA-256 校验的官方补丁；上游已包含完整修复时记录 `already-present`，不重复打补丁，也不根据版本号猜测是否修复。冲突先在临时副本暴露，不把半套补丁写回源码。编译前再次核对修复及源码哈希，编译成功后生成来源记录。

每次完整构建的 Release 附带 `MINIUPNPD-SOURCE.json`，包含当次软件包版本、两项修复的应用状态、官方提交及补丁/源码 SHA-256。包版本号仍由上游维护，因此不能只看 `miniupnpd --version` 判断是否带本地修复；在线包升级也可能覆盖固件里的修复，需核对来源或通过本仓库重编译。

以后上游发布包含这些修复的新版本，会自动识别并跳过。**无法保证任意未来重构都无需适配**：若实现结构已改变且不能确认修复，构建明确失败并指出位置，需要重新审查，绝不静默跳过或退回旧版。升级不改变现有插件、LAN/Wi-Fi、LED、NSS/eBPF 或 12 MiB Kernel 配置。

回归测试使用真实 `2.3.11` 源码、已修复的官方源码、ImmortalWrt 补丁和本机 C 编译器，覆盖重复执行、部分修复、冲突、篡改检测及 WAN 恢复和 nftables 地址族行为；测试固定版本仅是对照样本，不限制固件版本。Linux 下运行：

```sh
bash tests/run_miniupnpd_tests.sh
```

CI 每次自动执行以上测试。测试与编译成功不等于实机公网可达：CGNAT 上游的端口开放不受本机 MiniUPnP 控制；本项目不会自动刷机、重启路由器或放宽防火墙权限。

### LuCI 端口映射显示兼容

映射在内核中生效而页面显示为空，也可能是 `/usr/share/rpcd/ucode/luci.upnp` 的解析问题。新版 nft 规则包含 `counter packets … bytes …`，并可能把旧的 `@nh,72,8` 协议表达式显示为 `ip protocol tcp/udp`，旧 LuCI 解析器会漏掉这些规则。

本项目参考 [OpenWrt LuCI PR #9148](https://github.com/openwrt/luci/pull/9148) 的计数字段修复和 [PR #8415](https://github.com/openwrt/luci/pull/8415) 的协议格式适配，只修改 nft 状态读取的五行代码，兼容新旧格式及 TCP/UDP。**两项提案在 2026-10-21 核对时均未合并**；本仓库是经过回归验证的局部适配，不是宣称已经发布的官方修复，也不引入提案中的 UCI、权限或租约格式改版。

构建时 `Scripts/luci_upnp/install.py` 先验证实际 feeds 解析器：已兼容则保持上游文件不变，已知旧实现才应用修复；未知实现或测试失败会明确报错，不覆盖整包、不锁定 LuCI 版本。Release 的 `LUCI-UPNP-SOURCE.json` 记录修复状态、参考来源与文件前后 SHA-256。在线升级 `luci-app-upnp` 可能覆盖固件修复，应核对新包或重新构建。

本地基础检查：`python tests/test_luci_upnp.py`（需要 Node.js）。Linux 原生 ucode 回归：`bash tests/run_luci_upnp_tests.sh`（需要 Git、CMake、C 编译器、libjson-c-dev、Node.js、Python 3）；各测试命令限制为 60 秒。CI 对实际 feeds 文件再次执行原生 ucode 测试。所有测试使用离线规则输入，不创建真实端口映射，不更改代理或网络服务；原生测试只固定测试解释器版本，不固定固件的软件包版本。

实机验收应先记录已有映射，再用未占用的高端口建立短时 TCP/UDP 测试映射，对照内核规则、`luci.upnp.get_status` 与网页，最后通过 UPnP 删除自己创建的测试映射并回查。不要用页面的整服务重启路径清理测试，不删除业务映射。离线回归通过不等于已验证实机页面、qBittorrent 自动申请或公网可达。

## 雅典娜 LED 屏幕配置修复

首次启动以固件内 `/rom/etc/config/athena_led` 的实际配置格式为准，不再强制写入新版格式。当前 VIKINGYFY 插件读取 `config.enable`；旧迁移脚本误写成 `general.enabled`，会导致屏幕不亮。

- 配置格式匹配时，保留亮度、显示项目及手动关闭状态，不强制启用服务。
- 已知新旧格式不匹配时，先备份为 `/etc/config/athena_led.config-migrated`，已有备份则追加 `.1`、`.2` 等，再原子替换为固件默认配置。此时 LED 自定义选项需在界面重新设置；其他插件和网络设置不变。
- 缺少固件默认配置、格式未知或写入失败时向标准错误输出明确报错，不生成猜测配置；失败的迁移脚本会保留，供继续排查。

回归测试需要真实 OpenWrt `uci` 和 `ash`，不能在普通 Windows/Git Bash 中替代验证。把下面两个文件放到路由器同一临时目录后执行：

```sh
sh test_athena_led_config_migration_guard.sh ./99-athena-led-config-migration
```

文件分别位于 `tests/` 和 `files/etc/uci-defaults/`。测试只操作自动生成的临时配置，不修改当前 LED 或网络配置，覆盖配置保留、双向格式修复、备份、重复执行、异常配置和写入失败。

LED migration now follows the installed package's ROM defaults. Compatible custom settings are preserved; known schema mismatches are backed up before atomic replacement. Unknown schemas and I/O failures remain explicit errors. Regression tests require real OpenWrt UCI and use isolated temporary fixtures.

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
