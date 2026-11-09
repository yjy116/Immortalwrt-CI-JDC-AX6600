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

## 上游插件补齐与 Vantage

2026-11-02 对照 [VIKINGYFY/OpenWRT-CI](https://github.com/VIKINGYFY/OpenWRT-CI/tree/967e4c7728fba8e54c62066b5507aed015844588) 和 `owrt` 的 `17d1ac0c`，在保留原有插件的基础上补齐以下通用应用。构建继续跟随各自维护分支，不将本次核对提交冒充永久最新版本。

| 应用 | 来源 | 集成方式 |
| --- | --- | --- |
| NATMapT / LuCI 界面、STUN 客户端 | `muink/openwrt-natmapt`、`muink/luci-app-natmapt`、`muink/openwrt-stuntman` 的 `master` | 补齐上游默认选择；保持全局关闭，只保留一个未启用模板，去掉上游示例映射、示例账号和通知配置。不会自动修改 qBittorrent。 |
| 网络测速 | `sirpdboy/netspeedtest:main` | 同时包含 Homebox、Ookla 客户端；复用原有 `iperf3`，不混装互斥的 `iperf3-ssl`。核实当前 `python3-urllib` 已提供 `email` 且实际测速脚本不使用 `pkg_resources` 后，移除两个过时的拆分包依赖；不固定旧 Python 版本。编译前检查依赖包存在且已选入镜像。不自动开始测速或启动测速服务器。 |
| 网络向导 | `sirpdboy/luci-app-netwizard:main` | 按上游逻辑开机跳过配置应用；仅在用户主动保存时修改网络。与原有 Router Tool 功能重叠，不要连续使用两个向导覆盖配置。 |
| 上网时间控制 | `sirpdboy/luci-app-timecontrol:main` | 保持上游规则未启用；按需配置。硬件卸载与时间控制规则的实机交互尚未验证。 |
| 网络质量监控 | `LianXia233/luci-app-netmonitor:main` | 固件默认关闭全局探测；保留上游目标配置，用户启用后才探测。 |
| Vantage 主题与仪表盘 | [anothaDev/luci-theme-vantage:main](https://github.com/anothaDev/luci-theme-vantage) | 同时选择 `luci-theme-vantage` 和 `luci-app-vantage`，与上游 CI 来源一致；本次核对版本为 `1.0.12-r1`。 |

`QCA-6.18-VIKINGYFY` 默认主题改为 Vantage，Argon、Aurora 等原有选择保留。首次进入这一主题版本时，末尾的 UCI defaults 脚本选用 Vantage，并在 LuCI 配置记录标记；之后手动切换主题不会在普通重启或保留配置升级时被重新覆盖。恢复旧备份可能带回旧主题和服务配置，不能保证旧配置跨版本兼容。

本次不修改已有 `qca-ppe-qos` / `luci-app-qca-ppe-qos` 的选择或运行设置；源码和上游默认值仍随 `owrt` 自然更新。`luci-app-router-tool`、SONiC Fullcone、LED 等也已存在，不重复添加。MiniUPnP 与 LuCI UPnP 同时迁移到 VIKINGYFY 的整套维护包，详见下文；移除 feeds 中的同名提供者，避免混用新旧接口。

未纳入的上游差异：

- CHFS：当前包装允许 `PKG_HASH:=skip` 和 HTTP 下载回退，且带默认管理口令，暂不作为已验证插件加入；原 Samba4、磁盘管理、qBittorrent 保留。
- 机型专用风扇、FM350/H5000M/MT5700 蜂窝模块控制、QModem-generic、TMI PoE：不对应 AX6600 当前硬件用途，不批量安装。
- `ksmbd`、AHCI/NVMe 及工具、额外 EHCI、OpenVPN 内核卸载、IPv6 NAT：属于另一套文件共享或硬件/网络功能，不仅是 LuCI 插件。现有 Samba4、USB3/xHCI 与代理方案不替换。
- Fluent、Footstrap、Shadcn：上游提供的其他可选主题，本次按用户指定使用 Vantage，不额外安装所有皮肤。

“不恢复备份”只能减少历史配置冲突，不能证明所有服务同时启用兼容。新增插件通过构建中的依赖、defconfig 和 manifest 核验；代理转发、QoS/访问控制、测速及页面实际运行仍需新固件实机验证。项目不会自动刷机、连接路由器改配置或重启。

## OWRT PPE + NSS 迁移

2026-10-30 起，6.18 工作流采用 `Config/OWRT/` 的精简设备选择，以上游 `owrt` 的内核基础配置、PPE/EDMA 驱动、NSS 固件、无线固件、内存预留及启动方式为准。`Config/GENERAL.txt` 的现有插件和插件选项不删减，DAE/DAED/Honk 的已核验来源与服务互斥修复不变。原配置文件继续供其他旧工作流使用，不混入本次构建。

- 有线数据通路跟随上游 PPE/EDMA；WIFI 版使用 `ATH11K_NSS_WIFI` 和 `kmod-nss-wifi-drv`，QCN9074 固件由上游设备定义选择。NOWIFI 版去掉无线默认包，保留独立 NSS 驱动，不套用旧 `main` 的 Q6 内存缩减和 SKB recycler 强制选项。
- 保留 `luci-app-sqm`，后端由旧 `sqm-scripts-nss` 改为 feeds 的 `sqm-scripts`，加入上游 `qca-ppe-qos` 与对应 LuCI 界面。旧 NSS qdisc/crypto/ECM 驱动不与新架构混用；这不代表新驱动提供旧驱动全部硬件加速能力。当前 feeds 的 SQM 是否含 `hw_ppe.qos` / `ppe_cake.qos` 必须以实际文件为准，不能仅凭 PPE QoS 界面宣称硬件 CAKE 可用。
- 原插件选择在生成 OWRT 配置时按上游包定义适配：`kmod-nft-fullcone` 对应内核集成的 `fullconenat-sonic`，`kmod-usb-xhci` 对应 `kmod-usb-xhci-hcd`；保留 USB 3.0、`kmod-sound-core` 和 `kmod-usb-audio`，并为所选音频包补齐 `audio-support` 硬件前置条件。旧 Fullcone 模块与新方案冲突，不再混装；这些转换不修改其他工作流使用的 `Config/GENERAL.txt`。替代包及音频依赖同样必须通过 defconfig 和固件 manifest 完整性核验，不能静默丢失。
- Fullcone 同时选择 `fullconenat-sonic` 和 `luci-app-fullconenat-sonic`，界面集成于网络/防火墙。截至 2026-10-30，OWRT 包版本为 `20261016-r1`；另补入 SONiC 源项目 10 月 27 日的 [e5cbaad 回包 NAT 修复](https://github.com/mufeng05/openwrt-sonic-fullcone/commit/e5cbaad43fe15c8f879a0f456b448d578c0eac4d)。保留 OWRT 的锁、隔离映射、PPE 和 firewall4 集成，不用其他项目的整套补丁覆盖。上游源码已含该方向修复时自动不再添加本地补丁，未知实现变更明确报错。Release 的 `FULLCONE-SOURCE.json` 和固件 `/usr/share/fullconenat-sonic/CI-SOURCE.json` 记录真实包版本、修复提交及补丁哈希，不伪造版本号。编译通过不代表实机 NAT 类型或公网入站连接已验证。
- 明确保留的定制例外：现有全部插件及依赖、eBPF/BTF 必要配置、LAN/SSID/现有密码、LED 配置迁移、MiniUPnP/LuCI 修复、已选京东云设备的 12 MiB Kernel。除此以外，不追加旧分支的内核调优或内存配置。
- `defconfig` 后逐项核验请求的软件包及插件子选项；固件打包时核验 manifest，发现丢包明确失败。缓存按源码仓库和分支隔离，staging 额外按源码提交隔离。

构建机固定为依赖初始化脚本已支持的 Ubuntu 24.04，避免 `ubuntu-latest` 切换到 26.04 后在准备阶段报 `Unsupported OS`。这只固定 CI 主机，不回退固件源码、内核或插件版本。

从旧 NSS 固件升级时，应备份网络、无线、代理和 SQM 配置。新分支采用不同的网络数据通路，不能假设旧 `ethX` 接口、SQM 的 `nss*.qos` 脚本或整份网络备份可原样恢复；先核对新固件的接口和可用队列脚本，再恢复业务设置。12 MiB 镜像只适用于已完成对应大分区修改的设备。本仓库不会自动修改分区、刷机或重启路由器。

编译与离线检查不能代替实机 WAN/LAN、Wi-Fi、PPPoE/VLAN、UPnP 和透明代理/eBPF 与硬件卸载交互验证；迁移版未完成实测前保留上一版固件作为回退依据。

USB 打印保留 `luci-app-usb-printer`、`p910nd` 和 `kmod-usb-printer`。上游现在要求显式选择 `printer-support`（打印设备组及热插拔规则），本仓库已补齐；构建会在 `defconfig` 后核验整条依赖，避免驱动及界面被静默取消选择。实际 USB 打印仍需连接打印机验证。

## Honk 与内置 Doona

新增 [kenzok8/openwrt-honk](https://github.com/kenzok8/openwrt-honk) 的 `honk` 和 `luci-app-honk`，保留原有 DAE、DAED、daede 管理界面及其他插件。Doona 静态界面随 `luci-app-honk` 安装到 `/usr/share/doona`，不需要另装 `luci-app-doona`，也不额外启动面板服务。

自 2026-11-04 起，每次构建跟随维护源 `main` 的最新提交，不再固定历史版本。此次主机核验基线为 `2026.11.03-r1`、打包提交 `036d31fc9d0c30fca12501f22960529c7f6b97fd`；核心来自 `daeuniverse/honk` 提交 `77176ff8e8cc2b75385a7030dc376536c382574a`，Doona 为 `0.1.0-rc.5`、提交 `46e153cf405ce665983794cf297fb5cf6d38084c`。实际固件以该次 Release 的来源记录为准。

构建采用维护源已发布的静态 musl 核心（雅典娜使用 AArch64）和 Doona 静态资源，再由本仓库的 OpenWrt 工具链打包；**不是在本仓库重新编译 Rust 核心**。QCA 工作流在矩阵开始前统一解析 DAEDE/Honk 的最新 `main` 提交，WIFI/NOWIFI 共用本次 SHA，构建中途不再追逐分支变动。`Scripts/Honk.sh` 使用该提交 Makefile 中的 `source-<run_id>` 和 SHA-256，不加载生成的 Makefile 覆盖、不使用可变 `staging` 或 `SKIP`。GitHub Release 的资产摘要必须与 Makefile 一致；来源 JSON 另行校验 SHA-256，并核对核心仓库、提交及架构。下载后再校验实际归档，检查静态 AArch64 核心和 Doona 页面及源码记录。

为避免普通 Release 下载入口的网关错误，来源 JSON、AArch64 核心和 Doona 使用 GitHub 官方 Release asset API 下载。资产编号、名称、原始 URL 和摘要必须对应本次锁定的维护源；核心与界面归档在 `make download` 前写入 `dl`，校验通过才复用缓存。HTTP 错误或哈希不一致直接失败，不切换镜像或版本。

每次 Release 的 `HONK-SOURCE.txt` 记录实际打包提交、组件 pins、版本、原始下载 URL/哈希及 API 资产编号、已适配文件哈希和预编译来源。跟随的是维护源已集成的组合，不是绕过维护者直接追核心开发分支；维护源缺少资产、校验不一致或本地兼容补丁冲突时明确失败，不退回旧版本。上游已移除独立开机开关，本仓库通过 `patches/honk/010-preserve-boot-opt-in.patch` 保留原开关、恢复配置和默认关闭行为，保存其他设置不会强制开启自启。自定义配置文件模式提供独立的自启保存命令，只修改启动偏好和启动链接，不改网络配置或重启服务。

使用说明：

1. 固件保持原有默认：Honk 未初始化、未启用、不开机自启，不会自动接管现有 DAE/DAED。
2. 使用 Honk 前，在 daede 界面停止当前 DAE/DAED 后端并关闭其开机自启；其他透明代理也应先停止。Honk 启动检查会对正在运行的 DAE/DAED 等代理明确报冲突，不会替你自动停止它们。
3. 在「服务 → Honk」初始化、运行系统检查、配置节点或订阅后启动；初始化完成、服务运行且 API 就绪后，再进入 Doona。Honk 需要 Linux 6.12+、内核 BTF 和相应 eBPF 模块，本固件保留这些依赖。管理入口只应在可信 LAN 内使用，不要暴露到 WAN。
4. 切回 DAE/DAED 前，先停止 Honk 并关闭其开机自启，再通过 daede 启动所选后端。daede 原有互斥仅覆盖 DAE 与 DAED，不能把它理解为 Honk 与 DAE/DAED 的双向自动互斥；不要同时开启两套透明代理。

保留 LAN、Wi-Fi、LED 修复、12 MiB Kernel、NSS/eBPF 和缓存策略。主机静态检查和固件编译不等于实机转发验证；Honk/Doona 的启动、订阅、eBPF 转发与 NSS 交互仍需刷入后验证，本任务不会自动刷机或重启路由器。

Honk and bundled Doona are added alongside DAE/DAED, disabled by default. The firmware packages hash-verified upstream static binaries and UI assets, with provenance in `HONK-SOURCE.txt`. Stop the active proxy before switching; on-device forwarding and NSS interaction are not yet validated.

## MiniUPnP 上游修复与自动接续

2026-11-02 起，`miniupnpd-nftables` 与 `luci-app-upnp` 整套跟随 [VIKINGYFY/packages:main](https://github.com/VIKINGYFY/packages)。本次核对提交为 `1d676e3edcb5838fcffcbfe53aa459908810f999`，核心包装 `20261101-r1` 使用官方 `miniupnp/miniupnp` 的 `d7b1860` 源码，LuCI 包为 `20261027-r7`。不冻结这些版本，构建记录当时实际版本与提交。

新包原生已包含以下官方修复，仍通过源码感知钩子验证，后续上游变更不能静默丢失：

- [2dcf639](https://github.com/miniupnp/miniupnp/commit/2dcf63959950dbb2c3f97b7bd63773d499749134)：启用 `ext_allow_private_ipv4` 时，WAN 断线后恢复为内网/CGNAT 地址，也能重新允许端口映射。
- [a8de55a](https://github.com/miniupnp/miniupnp/commit/a8de55a0ae4829d59498667120d1e88933dc0f5d)：为 nftables `inet` 表的映射规则添加正确的 IPv4/IPv6 限定，同时包含其前置解析器重构 `320ebf5`。

`Scripts/miniupnpd/install.py` 将钩子接入软件包的 `Prepare/Post`，在**解包和所有包内补丁之后**检查实际源码，支持新包的 `miniupnpd/` 子目录。缺失时应用本仓库带 SHA-256 校验的官方补丁；上游已包含完整修复时记录 `already-present`，不重复打补丁，也不根据版本号猜测是否修复。冲突先在临时副本暴露，不把半套补丁写回源码。编译前再次核对修复及源码哈希，编译成功后生成来源记录。

每次完整构建的 Release 附带 `MINIUPNPD-SOURCE.json`，包含当次软件包版本、核心源提交、源码归档校验值、两项修复状态及补丁/源码 SHA-256。`LUCI-UPNP-SOURCE.json` 另记录整套包的维护提交、版本和文件哈希。不要单独用旧 feeds 的 LuCI 或核心覆盖新包；优先通过本仓库重编译成对更新。

保留上游启动脚本、backend 标记、防火墙 include 和 UCI defaults 迁移：已有 `force_forwarding` 改名为 `ext_allow_private_ipv4`，已存在的新选项值优先保留；旧六字段租约补上空的 remote-host 字段，已有七字段租约不重复转换。`/etc/config/upnpd` 仍为 conffile，不主动改写用户映射权限、端口或内网接口。CI 使用隔离 UCI/进程测试桩执行真实迁移脚本，验证旧值、新值、混合租约、重复执行和错误退出；不是路由器实机迁移验收。

以后上游发布包含这些修复的新版本，会自动识别并跳过。**无法保证任意未来重构都无需适配**：若实现结构已改变且不能确认修复，构建明确失败并指出位置，需要重新审查，绝不静默跳过或退回旧版。升级不改变现有插件、LAN/Wi-Fi、LED、NSS/eBPF 或 12 MiB Kernel 配置。

回归测试使用真实 `2.3.11` 源码、已修复的官方源码、ImmortalWrt 补丁和本机 C 编译器，覆盖重复执行、部分修复、冲突、篡改检测及 WAN 恢复和 nftables 地址族行为；测试固定版本仅是对照样本，不限制固件版本。Linux 下运行：

```sh
bash tests/run_miniupnpd_tests.sh
```

CI 每次自动执行以上测试。测试与编译成功不等于实机公网可达：CGNAT 上游的端口开放不受本机 MiniUPnP 控制；本项目不会自动刷机、重启路由器或放宽防火墙权限。

### LuCI 端口映射显示兼容

映射在内核中生效而页面显示为空，也可能是 `/usr/share/rpcd/ucode/luci.upnp` 的解析问题。新版 nft 规则包含 `counter packets … bytes …`，并可能把旧的 `@nh,72,8` 协议表达式显示为 `ip protocol tcp/udp`，旧 LuCI 解析器会漏掉这些规则。

现在使用 VIKINGYFY 的完整 JSON 状态读取实现，通过 `nft --json` 解析表达式，不再靠文本正则跳过计数器；同时适配新租约、token 删除接口、LuCI 页面和 ACL。旧的 `Scripts/luci_upnp/install.py` 不再用于实际固件，仅保留旧解析器作为历史回归对照。**截至 2026-11-02，OpenWrt LuCI PR #9148 已关闭但未合并，#8415 仍未合并**，不能把本次 VIKINGYFY 修复描述为 OpenWrt 官方 LuCI 已合入。

构建时 `Scripts/luci_upnp/upstream.py` 用原生 ucode 执行实际包中的 JSON 读取、租约和状态合并逻辑，覆盖 TCP/UDP、raw/decoded/meta 协议表达式、counter、无效规则、命令失败及错误删除 token。测试只替换外部 I/O，不重写上游解析函数；未知源码布局或测试失败明确阻断构建，不静默退回旧解析器。

本地基础检查：`python tests/test_upnp_layout.py`、`python tests/test_upnp_harness.py`；迁移回归：`bash tests/test_upnp_migration.sh <上游miniupnpd目录>/files/miniupnpd.defaults.migration`。CI 先用 `tests/run_luci_upnp_tests.sh` 构建测试解释器并验证历史故障对照，再执行新的整套包核验。每个回归测试命令限时 60 秒，输入均为离线样本，不创建真实端口映射，不更改代理或网络服务；测试解释器版本不限制固件的软件包版本。

上游页面的删除操作会停启 MiniUPnP 服务并从租约中移除对应条目，不能当作完全无中断的删除。实机验收应先记录已有映射，再用未占用的高端口建立短时 TCP/UDP 测试映射，对照内核规则、`luci.upnp.get_status` 与网页，最后通过 UPnP 协议删除自己创建的测试映射并回查，不删除业务映射。离线回归通过不等于已验证实机页面、qBittorrent 自动申请或公网可达。

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

2026-11-04 主机核验基线（每次构建继续跟随维护源 `main`，非永久固定值）：

| 组件 | 版本 / 源码 |
| --- | --- |
| 打包仓库 | `1eedcafd1cd4d8a89ac928be6608df76ffb38f78` |
| dae / daed | `2026.10.30-r1` |
| luci-app-daede | `1.15-r13` |
| DAED 前端 | `be4ef873c352a9ec930c877a3a821163f4b4ac0a`，包含 v2.1.1 |
| dae-wing | `b089b568649f03f909477adb6c7db25535a58782` |
| 两份 DAE 核心 | 官方 `29a70280fd7e0e73233e623d6dcd004c245882e2` 合并到性能基线 `be2b6047eff8be8da7dfdcd0c007fd6d9f7f5175` |

两份源码归档使用维护源 Makefile 的 SHA-256，依赖和源码组合记录在该提交的 `ci/pins.env`；版本和提交格式在准备阶段核对，下载后再次核验实际归档哈希。源码包内含已构建的 Web 静态资源，Go/eBPF 后端在我们的固件构建中编译，不安装第三方预编译内核包或额外软件源。

`Scripts/Daede.sh` 使用本次构建统一解析的最新打包提交，保留主包构建、服务互斥和旧配置/订阅迁移补丁；每次准备都严格应用补丁并执行行为回归，未知冲突明确失败。每次 Release 附带 `DAEDE-SOURCE.txt`，记录真实打包提交、组件 pins、包版本、归档 URL/SHA-256 和适配后文件哈希。构建触发时才拉取最新，不等同于上游一提交就自动触发本仓库编译。
本固件的这三个包请通过 GitHub 重新编译升级；使用 daede 界面的在线包更新可能覆盖本仓库的服务互斥补丁。

### 后端切换与升级

- 在「服务 → daede」选择后端。切换先停止当前服务，再关闭两边的 UCI 启用标记和开机自启，最后保存选择；按上游交互设计，切换后需要点击启动。
- 两个后端共享 eBPF/cgroup 附着点，不应同时运行。本仓库补丁还让启动脚本核对所选后端及另一进程状态，覆盖开机和 `/etc/init.d/dae(d) start`；失败明确报错。不要绕过服务管理直接同时运行两个二进制。
- 升级前停止代理并备份 `/etc/config/dae`、`/etc/config/daed`、`/etc/dae/`、`/etc/daed/`（含 `wing.db` 及 WAL）和 `/etc/crontabs/root`。新后端继续使用这些数据路径，但数据库跨版本兼容和实际转发仍须刷机验证。
- 首次启动移除旧 `luci_daed` 和旧热插拔重启脚本；旧订阅 cron 命令替换为新更新器，时间表达式不变，原 cron 留在 `/etc/daede-migration-backup/root.cron`。请在新界面填写 DAED 面板账号密码，再检查订阅自动更新；新更新器需要这些凭据，缺失会报错，不会假报成功。之后在界面保存更新计划时，以新界面的每日/每周选项为准。
- 原来只启用独立 DAE 时保留该后端选择；其他情况采用上游 DAED 默认选择。两边旧启用标记都为 1 时，非选中后端启动会被拒绝，请在界面完成一次切换并确认状态。
- 保留 LAN `192.168.80.1`、SSID `Athena`、现有 Wi-Fi 密码、12 MiB Kernel、NSS/eBPF 和其他插件。选用固件内置 BTF，不使用外部内核 BTF 包。

Both standalone DAE and DAED now use the same reviewed kenzok8 packaging source. DAED embeds its own DAE core; updating only its frontend does not update both cores. Local patches persist exclusive backend selection and reject unsafe service starts. Back up configuration and the stopped database before upgrading; host tests and successful builds do not prove on-device forwarding or database migration.
