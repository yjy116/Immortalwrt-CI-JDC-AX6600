#!/usr/bin/env python3
"""Correct one independently reproduced OWRT firewall4 source archive hash."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PACKAGE = Path("package/network/config/firewall4/Makefile")
SOURCE_COMMIT = "3722eadc088c3ab81389596ca9796112b436583a"
DECLARED_HASH = "a95c6cfe419c7d4e22bda5608aa6e46c67dadc9c7096879702d614cc498759d0"
VERIFIED_HASH = "9ce4fee1c5f90e5b097216ef49c8ec981adc5911939622d031f555d103a58ba3"
SOURCE_ARCHIVE = "firewall4-2026.11.08~3722eadc.tar.zst"
EXPECTED_RECIPE = {"PKG_NAME": "firewall4", "PKG_SOURCE_PROTO": "git",
                   "PKG_SOURCE_URL": "$(PROJECT_GIT)/project/firewall4.git",
                   "PKG_SOURCE_DATE": "2026-11-08"}


def assignment(text, key):
    pattern = rf"^{re.escape(key)}[ \t]*(?::=|=)[ \t]*(\S+)[ \t\r]*$"
    matches = list(re.finditer(pattern, text, re.M))
    if len(matches) != 1:
        raise ValueError(f"Review firewall4 metadata: expected one {key} assignment")
    return matches[0]


def verify_recipe(text, root):
    for key, value in EXPECTED_RECIPE.items():
        if assignment(text, key)[1] != value:
            raise ValueError(f"Review changed firewall4 archive identity: {key}")
    overrides = r"^(?:PKG_SOURCE|PKG_SOURCE_SUBDIR|PKG_VERSION)[ \t]*[:?+]?="
    if re.search(overrides, text, re.M):
        raise ValueError("Review changed firewall4 archive name/subdirectory")
    download = (root / "include/download.mk").read_text(encoding="utf-8")
    if assignment(download, "PROJECT_GIT")[1] != "https://git.openwrt.org":
        raise ValueError("Review changed firewall4 source repository")


def corrected_recipe(text, root):
    commit = assignment(text, "PKG_SOURCE_VERSION")[1]
    mirror = assignment(text, "PKG_MIRROR_HASH")
    if commit != SOURCE_COMMIT:
        return text, "unmodified"
    verify_recipe(text, root)
    if mirror[1] == VERIFIED_HASH:
        return text, "verified"
    if mirror[1] != DECLARED_HASH:
        raise ValueError("Review unknown firewall4 hash for the same source revision")
    start, end = mirror.span(1)
    return text[:start] + VERIFIED_HASH + text[end:], "corrected"


def install(root):
    path = root / PACKAGE
    original = path.read_bytes().decode("utf-8")
    updated, state = corrected_recipe(original, root)
    receipt = {
        "source_commit": assignment(original, "PKG_SOURCE_VERSION")[1],
        "declared_hash": assignment(original, "PKG_MIRROR_HASH")[1],
        "effective_hash": assignment(updated, "PKG_MIRROR_HASH")[1],
        "state": state,
        "reviewed_commit": SOURCE_COMMIT,
        "reviewed_archive": SOURCE_ARCHIVE,
        "recipe_sha256": hashlib.sha256(updated.encode("utf-8")).hexdigest(),
        "reviewed_verification": "Two Linux CI archives and independent GNU-tar/zstd-1.5.7 reproduction",
    }
    if updated != original:
        path.write_bytes(updated.encode("utf-8"))
    (root / "FIREWALL4-SOURCE.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"firewall4 source hash: {state}; {receipt['source_commit']}; {receipt['effective_hash']}")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    install(parser.parse_args().root)


if __name__ == "__main__":
    main()
