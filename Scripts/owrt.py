#!/usr/bin/env python3
"""Adapt the existing application configuration to the upstream OWRT data path."""

import argparse
from pathlib import Path
import re

TARGET = Path("target/linux/qualcommax")
KERNEL_SIZE = "12288k"
LEGACY_OPTION = re.compile(
    r"^(?:# )?CONFIG_(?:IPQ_MEM_PROFILE_|ATH11K_MEM_PROFILE_|"
    r"ATH11K_NSS_SUPPORT|NSS_DRV_|PACKAGE_kmod-qca-nss-|PACKAGE_sqm-scripts-nss)")
WIFI_PACKAGE = re.compile(
    r"-?(?:wpad(?:-\S+)?|hostapd(?:-\S+)?|kmod-ath(?:10k|11k)?(?:-\S+)?|"
    r"kmod-mac80211|kmod-cfg80211|ath(?:10k|11k)-firmware-\S+|ipq-wifi-\S+|"
    r"wifi-scripts|wireless-regdb|iw|iwinfo)")
PACKAGES = ("kmod-nss-wifi-drv", "nss-firmware", "luci-app-sqm", "sqm-scripts",
            "qca-ppe-qos", "luci-app-qca-ppe-qos", "tc-full", "miniupnpd-nftables")
PACKAGE_REPLACEMENTS = {"kmod-nft-fullcone": "fullconenat-sonic",
                        "kmod-usb-xhci": "kmod-usb-xhci-hcd"}
AUDIO_PACKAGES = {"CONFIG_PACKAGE_kmod-sound-core", "CONFIG_PACKAGE_kmod-usb-audio"}
BPF_KERNEL = ("BPF", "BPF_SYSCALL", "BPF_JIT", "CGROUPS", "KPROBES",
              "NET_INGRESS", "NET_EGRESS", "NET_CLS_ACT", "BPF_STREAM_PARSER",
              "DEBUG_INFO", "DEBUG_INFO_BTF", "KPROBE_EVENTS", "BPF_EVENTS")
REQUIRED_OPTIONS = {"CONFIG_ATH11K_NSS_WIFI", "CONFIG_KERNEL_DEBUG_INFO_BTF",
                    "CONFIG_KERNEL_CGROUP_BPF", "CONFIG_KERNEL_BPF_EVENTS",
                    "CONFIG_DAE_USE_KERNEL_BTF", "CONFIG_DAED_USE_KERNEL_BTF"}


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, value):
    path.write_text(value, encoding="utf-8", newline="\n")


def selected(config):
    return set(re.findall(r"^(CONFIG_[^=\s]+)=y$", config, re.M))


def replace_options(config, values):
    lines = []
    for line in config.splitlines():
        symbol = re.match(r"^(?:# )?(CONFIG_[^=\s]+)", line)
        if not symbol or symbol[1] not in values:
            lines.append(line)
    for key, enabled in values.items():
        lines.append(f"{key}=y" if enabled else f"# {key} is not set")
    return "\n".join(lines) + "\n"


def adapt_packages(config):
    requested = selected(config)
    replacements = {f"CONFIG_PACKAGE_{old}": f"CONFIG_PACKAGE_{new}"
                    for old, new in PACKAGE_REPLACEMENTS.items()
                    if f"CONFIG_PACKAGE_{old}" in requested}
    lines = []
    for line in config.splitlines():
        symbol = re.match(r"^(?:# )?(CONFIG_[^=\s]+)", line)
        if not symbol or symbol[1] not in replacements:
            lines.append(line)
    values = {symbol: True for symbol in replacements.values()}
    if "CONFIG_PACKAGE_fullconenat-sonic" in requested | values.keys():
        values["CONFIG_PACKAGE_luci-app-fullconenat-sonic"] = True
    for old, new in replacements.items():
        print(f"OWRT package migration: {old} -> {new}")
    if requested & AUDIO_PACKAGES:
        values["CONFIG_PACKAGE_audio-support"] = True
        print("OWRT audio dependency: CONFIG_PACKAGE_audio-support=y")
    return replace_options("\n".join(lines), values)


def set_kernel_layout(root, config):
    image = root / TARGET / "image/ipq60xx.mk"
    content = read(image)
    devices = re.findall(r"^CONFIG_TARGET_DEVICE_qualcommax_ipq60xx_DEVICE_(jdcloud_[^=]+)=y$", config, re.M)
    for device in devices:
        pattern = rf"(^define Device/{re.escape(device)}\n)(.*?)(^endef$)"
        match = re.search(pattern, content, re.M | re.S)
        if not match:
            raise ValueError(f"Missing selected device: {device}")
        sizes = re.findall(r"KERNEL_SIZE\s*:=\s*(\S+)", match[2])
        if sizes not in (["6144k"], [KERNEL_SIZE]):
            raise ValueError(f"Review changed KERNEL_SIZE for {device}: {sizes}")
        body = re.sub(r"KERNEL_SIZE\s*:=\s*\S+", f"KERNEL_SIZE := {KERNEL_SIZE}", match[2])
        content = content[:match.start()] + match[1] + body + match[3] + content[match.end():]
    if "jdcloud_re-cs-02" not in devices:
        raise ValueError("AX6600 profile must select jdcloud_re-cs-02")
    write(image, content)


def remove_wifi_defaults(root):
    for relative in ("Makefile", "ipq60xx/target.mk", "image/ipq60xx.mk"):
        path = root / TARGET / relative
        # Remove package tokens only; leave package definitions and DTS memory intact.
        content = re.sub(r"(?<!\S)\S+(?!\S)",
                         lambda m: "" if WIFI_PACKAGE.fullmatch(m[0]) else m[0], read(path))
        write(path, content)


def prepare(root, profile):
    if profile not in ("IPQ60XX-WIFI", "IPQ60XX-NOWIFI"):
        raise ValueError(f"Unsupported OWRT migration profile: {profile}")
    if not (root / "package/qca-nss/nss-wifi-drv/Makefile").is_file():
        raise ValueError("OWRT source is missing nss-wifi-drv; do not apply legacy NSS settings")
    kernel = root / TARGET / "ipq60xx/config-default"
    if not {"CONFIG_QCOM_80211AX_PPE", "CONFIG_QCOM_EDMA"} <= selected(read(kernel)):
        raise ValueError("OWRT IPQ60xx target must provide the PPE/EDMA data path")
    config_path = root / ".config"
    config = "\n".join(line for line in read(config_path).splitlines() if not LEGACY_OPTION.match(line))
    config = adapt_packages(config)
    set_kernel_layout(root, config)
    wifi = profile == "IPQ60XX-WIFI"
    values = {f"CONFIG_PACKAGE_{name}": True for name in PACKAGES}
    values.update({"CONFIG_ATH11K_NSS_WIFI": wifi, "CONFIG_PACKAGE_tc-tiny": False})
    if not wifi:
        remove_wifi_defaults(root)
        values.update({symbol: False for symbol in selected(config)
                       if symbol.startswith("CONFIG_PACKAGE_")
                       and WIFI_PACKAGE.fullmatch(symbol.removeprefix("CONFIG_PACKAGE_"))})
    write(config_path, replace_options(config, values))
    write(kernel, replace_options(read(kernel), {f"CONFIG_{name}": True for name in BPF_KERNEL}))


def requested_packages(root):
    return {key for key in selected(read(root / ".config.requested")) if key.startswith("CONFIG_PACKAGE_")}


def verify_packages(root):
    requested = read(root / ".config.requested")
    actual = selected(read(root / ".config"))
    required = requested_packages(root) | (selected(requested) & REQUIRED_OPTIONS)
    missing = required - actual
    if missing:
        raise ValueError("Packages/options disappeared after defconfig:\n" + "\n".join(sorted(missing)))
    if "# CONFIG_ATH11K_NSS_WIFI is not set" in requested:
        wireless = {symbol for symbol in actual if symbol == "CONFIG_ATH11K_NSS_WIFI"
                    or (symbol.startswith("CONFIG_PACKAGE_")
                        and WIFI_PACKAGE.fullmatch(symbol.removeprefix("CONFIG_PACKAGE_")))}
        if wireless:
            raise ValueError("NOWIFI unexpectedly enables wireless:\n" + "\n".join(sorted(wireless)))


def verify_manifest(root, manifest):
    real_packages = set(re.findall(r"^Package: (\S+)$", read(root / "tmp/.packageinfo"), re.M))
    wanted = {key.removeprefix("CONFIG_PACKAGE_") for key in requested_packages(root)} & real_packages
    installed = {line.split(" - ", 1)[0] for line in read(manifest).splitlines()}
    missing = wanted - installed
    if missing:
        raise ValueError(f"{manifest.name} missing requested packages:\n" + "\n".join(sorted(missing)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "manifest"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.profile)
    elif args.command == "verify":
        verify_packages(args.root)
    else:
        if not args.manifest:
            parser.error("manifest requires --manifest")
        verify_manifest(args.root, args.manifest)
    print(f"OWRT {args.command}: passed")


if __name__ == "__main__":
    main()
