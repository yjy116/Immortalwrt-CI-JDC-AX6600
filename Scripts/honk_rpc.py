#!/usr/bin/env python3
"""Merge the boot-only RPC declaration without replacing upstream methods."""
import argparse
import json
from pathlib import Path
import re

from proxy_metadata import require

RPC_PATH = Path("luci-app-honk/root/usr/libexec/rpcd/honk")
BOOT_SCHEMA = {"boot_enabled": "Boolean"}
REGISTRY = re.compile(r"^list\)\n[ \t]+echo '(?P<methods>\{[^'\n]*\})'\n", re.M)


def unique_object(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), "Duplicate Honk RPC JSON member")
    return result


def register_boot_method(text):
    matches = list(REGISTRY.finditer(text))
    require(len(matches) == 1, "Expected one Honk RPC list JSON declaration")
    match = matches[0]
    methods = json.loads(match["methods"], object_pairs_hook=unique_object)
    require(isinstance(methods.get("settings"), dict)
            and methods["settings"].get("boot_enabled") == "Boolean",
            "Upstream Honk settings boot contract changed")
    require(re.search(r"^\s*boot_settings\)\s*\n\s*boot_settings\s*\n\s*;;", text, re.M),
            "Honk boot_settings handler missing")
    if "boot_settings" in methods:
        require(methods["boot_settings"] == BOOT_SCHEMA, "Conflicting Honk boot_settings schema")
        return text
    merged = json.dumps({**methods, "boot_settings": BOOT_SCHEMA}, separators=(",", ":"))
    merged = merged.replace("'", r"\u0027")
    return text[:match.start("methods")] + merged + text[match.end("methods"):]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    path = args.source / RPC_PATH
    text = path.read_text(encoding="utf-8")
    updated = register_boot_method(text)
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
