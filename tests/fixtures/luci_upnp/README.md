# LuCI regression source

`luci.upnp` is the unmodified Apache-2.0 upstream file from OpenWrt LuCI commit
`075b59fbacd1478f71ad053fbefce5522a80dce9`, Git blob
`f72b57b7ba84188b9b78854bf7ad0711394a0045`:

https://github.com/openwrt/luci/blob/075b59fbacd1478f71ad053fbefce5522a80dce9/applications/luci-app-upnp/root/usr/share/rpcd/ucode/luci.upnp

It is a test fixture, not a firmware source pin. The deployed package continues
to follow the configured LuCI feed. `live-20261021-tcp` in the parser cases is
the literal nft rule saved during authorized router testing on 2026-10-21;
the remaining cases cover protocol/format variations and non-mapping input.
