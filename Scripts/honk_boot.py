#!/usr/bin/env python3
"""Integrate the local Honk boot policy without patching upstream LuCI views."""
import argparse
import json
from pathlib import Path
import re

from honk_rpc import RPC_PATH, register_boot_method, unique_object
from proxy_metadata import require

LOCAL = Path(__file__).with_name("honk")
BOOT_VIEW = Path("luci-app-honk/htdocs/luci-static/resources/view/honk/boot-policy.js")
MENU = Path("luci-app-honk/root/usr/share/luci/menu.d/luci-app-honk.json")
ACL = Path("luci-app-honk/root/usr/share/rpcd/acl.d/luci-app-honk.json")
MENU_PARENT = "admin/services/honk"
BOOT_METHOD = "boot_settings"
BOOT_ORDER = 45
DEFAULTS = """# Restore startup registration from the saved preference without starting Honk.
. /lib/functions.sh
config_load honk
config_get_bool boot_enabled main boot_enabled 0
if [ "$boot_enabled" -eq 1 ]; then
	/etc/init.d/honk enable || exit 1
else
	/etc/init.d/honk disable || exit 1
fi"""
BOOT_GUARD = """	local boot_enabled
	config_load honk
	config_get_bool boot_enabled main boot_enabled 0
	[ "$boot_enabled" -eq 1 ] || return 0"""


def replace_one(text, pattern, replacement, contract):
    matches = list(re.finditer(pattern, text, re.M))
    require(len(matches) == 1, f"Honk boot adapter: expected one {contract}, found {len(matches)}")
    match = matches[0]
    updated = replacement(match) if callable(replacement) else match.expand(replacement)
    return text[:match.start()] + updated + text[match.end():]


def adapt_control(text):
    body = re.compile(r"(^settings\(\) \{\n)([\s\S]*?)(^\}$)", re.M)
    matches = list(body.finditer(text))
    require(len(matches) == 1, "Honk boot adapter: expected exactly one settings() function")
    match = matches[0]
    settings = replace_one(
        match[2], r'''^([ \t]*case "\$boot_enabled_type" in ''\|null\) new_boot_enabled=)1( ;; esac)$''',
        r"\g<1>$boot_enabled\2", "settings omitted boot preference")
    settings = replace_one(settings, r"^[ \t]*new_boot_enabled=1\n", "",
                           "settings forced boot preference")
    return text[:match.start(2)] + settings + text[match.end(2):]


def adapt_rpc(text):
    handler = (LOCAL / "boot-rpc.sh").read_text(encoding="utf-8")
    text = replace_one(text, r'^case "\$1" in\nlist\)$',
                       lambda match: handler + "\n\n" + match[0], "outer RPC dispatch")
    text = replace_one(text, r'^(\s*call\)\n[ \t]*case "\$2" in\n)',
                       r"\1\t\t\tboot_settings)\n\t\t\t\tboot_settings\n\t\t\t\t;;\n",
                       "RPC call dispatch")
    return register_boot_method(text)


def adapt_menu(text):
    entries = json.loads(text, object_pairs_hook=unique_object)
    route = f"{MENU_PARENT}/boot-policy"
    require(entries[MENU_PARENT]["action"]["type"] == "firstchild" and route not in entries,
            "Honk boot adapter: parent menu changed or boot-policy route already exists")
    entries[route] = {
        "title": "Boot policy", "order": BOOT_ORDER,
        "action": {"type": "view", "path": "honk/boot-policy"},
    }
    return json.dumps(entries, indent="\t") + "\n"


def adapt_acl(text):
    acl = json.loads(text, object_pairs_hook=unique_object)
    access = acl["luci-app-honk"]
    read = access["read"]["ubus"]["honk"]
    write = access["write"]["ubus"]["honk"]
    require("status" in read and "settings" in write and BOOT_METHOD not in read + write,
            "Honk boot adapter: status/settings ACL changed or boot_settings already present")
    write.append(BOOT_METHOD)
    return json.dumps(acl, indent="\t") + "\n"


def install_view(source):
    require(not (source / BOOT_VIEW).exists(), "Honk boot adapter: boot-policy.js already exists")
    recipe = (source / "luci-app-honk/Makefile").read_text(encoding="utf-8")
    view_glob = "./htdocs/luci-static/resources/view/honk/*.js"
    require(re.search(rf"^\t\$\(INSTALL_DATA\) {re.escape(view_glob)} "
                      r"\$\(1\)/www/luci-static/resources/view/honk/$", recipe, re.M),
            "Honk boot adapter: LuCI view install rule changed")
    return (LOCAL / "boot-policy.js").read_text(encoding="utf-8")


def apply_boot_policy(source):
    defaults = Path("honk/files/90-honk-boot")
    init = Path("honk/files/honk.init")

    def read(path):
        return (source / path).read_text(encoding="utf-8")

    updates = {
        Path("honk/files/control.sh"): adapt_control(read("honk/files/control.sh")),
        defaults: replace_one(read(defaults), r"^/etc/init\.d/honk enable$", DEFAULTS,
                              "first-boot registration"),
        init: replace_one(read(init), r"^(boot\(\) \{)$", r"\1\n" + BOOT_GUARD,
                         "init boot() entry point"),
        RPC_PATH: adapt_rpc(read(RPC_PATH)),
        MENU: adapt_menu(read(MENU)),
        ACL: adapt_acl(read(ACL)),
        BOOT_VIEW: install_view(source),
    }
    for path, content in updates.items():
        (source / path).write_text(content, encoding="utf-8", newline="\n")
    print("Honk boot policy: adapted startup and RPC; kept upstream LuCI views unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    apply_boot_policy(parser.parse_args().source)
