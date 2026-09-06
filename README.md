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
