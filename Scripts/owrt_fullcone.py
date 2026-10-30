#!/usr/bin/env python3
"""Backport the SONiC tuple-direction fix without replacing OWRT integration."""

import argparse
import hashlib
import json
from pathlib import Path
import re

PATCH_DIR = Path("target/linux/generic/hack-6.18")
BASE_PATCH = PATCH_DIR / "984-add-sonic-fullcone-support.patch"
FIX_PATCH = PATCH_DIR / "984-fix-sonic-fullcone-direction.patch"
PACKAGE_MAKEFILE = Path("package/network/utils/fullconenat-sonic/Makefile")
BACKPORT = Path(__file__).resolve().parents[1] / "patches/fullcone/010-original-direction.patch"
FIX_COMMIT = "e5cbaad43fe15c8f879a0f456b448d578c0eac4d"
REVIEWED_HEAD = "c30deb96b543afc8cb8c75d28ba921ec75cfd070"
REQUIRED = {"CONFIG_PACKAGE_fullconenat-sonic=y", "CONFIG_PACKAGE_luci-app-fullconenat-sonic=y"}


def direction_status(patch):
    postimage = "\n".join(line[1:] for line in patch.splitlines()
                          if line.startswith(("+", " ")) and not line.startswith("+++"))
    function = re.search(r"\bfind_appropriate_dst\([^{}]+\)\n\{(.*?)^\}", postimage, re.M | re.S)
    if not function:
        raise ValueError("Review changed SONiC find_appropriate_dst implementation")
    body = re.sub(r"/\*.*?\*/", "", function[1], flags=re.S)
    lookup = (r"nf_ct_invert_tuple\(result,\s*&ct->tuplehash\[IP_CT_DIR_ORIGINAL\]\.tuple\);"
              r"\s*result->src\s*=\s*tuple->src;\s*")
    if re.search(lookup + r"result->dst\.dir\s*=\s*IP_CT_DIR_ORIGINAL;", body):
        return "upstream"
    if re.search(lookup + r"found\s*=\s*1;", body):
        return "backported"
    raise ValueError("Review changed SONiC tuple-direction logic before backporting")


def package_info(makefile):
    values = {}
    for key in ("PKG_VERSION", "PKG_RELEASE", "SONIC_SOURCE_VERSION"):
        matches = re.findall(rf"^{key}:=(\S+)$", makefile, re.M)
        if len(matches) != 1:
            raise ValueError(f"Review SONiC package metadata: {key}")
        values[key] = matches[0]
    return {"package_version": f"{values['PKG_VERSION']}-r{values['PKG_RELEASE']}",
            "owrt_declared_source": values["SONIC_SOURCE_VERSION"]}


def sync_patch(root, state):
    dest = root / FIX_PATCH
    payload = BACKPORT.read_bytes()
    if dest.exists() and dest.read_bytes() != payload:
        raise ValueError(f"Refusing to overwrite an existing patch: {dest}")
    if state == "backported":
        dest.write_bytes(payload)
    elif dest.exists():
        dest.unlink()
    return hashlib.sha256(payload).hexdigest() if state == "backported" else None


def install(root):
    config = (root / ".config").read_text(encoding="utf-8")
    if not REQUIRED <= set(config.splitlines()):
        raise ValueError("Both SONiC packages must survive defconfig")
    base = (root / BASE_PATCH).read_bytes()
    state = direction_status(base.decode("utf-8"))
    receipt = package_info((root / PACKAGE_MAKEFILE).read_text(encoding="utf-8"))
    receipt.update({"source_repo": "https://github.com/mufeng05/openwrt-sonic-fullcone",
                    "reviewed_source_head": REVIEWED_HEAD, "fix_commit": FIX_COMMIT,
                    "direction_fix": state, "owrt_base_patch_sha256": hashlib.sha256(base).hexdigest(),
                    "backport_sha256": sync_patch(root, state),
                    "integration": "OWRT native kernel/firewall/LuCI with tuple-direction fix"})
    content = json.dumps(receipt, indent=2) + "\n"
    (root / "FULLCONE-SOURCE.json").write_text(content, encoding="utf-8", newline="\n")
    installed = root / "files/usr/share/fullconenat-sonic/CI-SOURCE.json"
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_text(content, encoding="utf-8", newline="\n")
    print(f"SONiC Fullcone direction fix: {state}; wrapper {receipt['package_version']}")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    install(parser.parse_args().root)


if __name__ == "__main__":
    main()
