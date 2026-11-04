"""Validate prepared Honk packages and downloaded inputs, without a router."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("HONK_SOURCE_DIR", ROOT / "wrt/package/openwrt-honk"))
ASSETS = Path(os.environ.get("HONK_ASSET_DIR", ROOT / "wrt/dl"))
ELF_MACHINE_AARCH64 = 183
ELF_PROGRAM_INTERPRETER = 3


def read(relative):
    return (SOURCE / relative).read_text(encoding="utf-8")


def receipt():
    return json.loads(read("ci/PROXY-SOURCE.json"))


class HonkIntegration(unittest.TestCase):
    def test_packages_are_selected_without_replacing_daede(self):
        config = (ROOT / "Config/GENERAL.txt").read_text(encoding="utf-8")
        for package in ("honk", "luci-app-honk", "dae", "daed", "luci-app-daede"):
            self.assertIn(f"CONFIG_PACKAGE_{package}=y", config.splitlines())
        self.assertNotIn("CONFIG_PACKAGE_luci-app-doona=y", config)

    def test_exact_packaging_and_release_receipt(self):
        head = subprocess.check_output(
            ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(head, receipt()["packaging_commit"])
        text = read("ci/HONK-SOURCE.txt")
        self.assertIn(f"PACKAGING_COMMIT={head}", text)
        self.assertIn("PACKAGING_BRANCH=main", text)
        self.assertIn("CORE_BUILD=upstream-prebuilt-static-musl", text)

    def test_pinned_core_and_doona_metadata(self):
        metadata = receipt()
        for arch in ("aarch64", "x86_64", "armv7"):
            asset = metadata["assets"][arch]
            self.assertRegex(asset["sha256"], r"^[a-f0-9]{64}$")
            self.assertIn(metadata["pins"]["CORE_COMMIT"], asset["name"])
        provenance = json.loads(read("honk/generated-provenance.json"))
        self.assertEqual(provenance["core"]["commit"], metadata["pins"]["CORE_COMMIT"])
        self.assertIn("aarch64", provenance["core"]["architectures"])

    def test_default_off_and_required_runtime_files(self):
        config = read("honk/files/honk.config")
        for flag in ("enabled", "boot_enabled", "initialized"):
            self.assertRegex(config, rf"option {flag} '0'")
        self.assertIn('"$HONK_CONTROL" preflight || return 1', read("honk/files/honk.init"))
        core = read("honk/Makefile")
        for dependency in ("kmod-sched-bpf", "kmod-veth", "kmod-nft-queue",
                           "@KERNEL_DEBUG_INFO_BTF", "sqlite3-cli"):
            self.assertIn("+" + dependency, core)
        self.assertIn("/usr/share/honk/provenance.json", core)
        self.assertIn("/usr/share/doona", read("luci-app-honk/Makefile"))

    def test_upstream_conflict_function_rejects_dae_and_daed(self):
        # Exercise the upstream function unchanged; only process lookup is stubbed.
        control = read("honk/files/control.sh")
        function = re.search(r"^check_conflicts\(\) \{\n.*?^\}", control, re.M | re.S)
        self.assertIsNotNone(function)
        script = "fail() { echo \"$*\" >&2; return 1; }\n"
        script += 'pidof() { [ "$1" = "$ACTIVE_PROXY" ]; }\n'
        script += function.group(0) + "\ncheck_conflicts\n"
        for active in ("none", "dae", "daed"):
            result = subprocess.run(["bash", "-c", script], text=True,
                                    capture_output=True, encoding="utf-8", timeout=10,
                                    env={**os.environ, "ACTIVE_PROXY": active})
            self.assertEqual(result.returncode, 0 if active == "none" else 1)
            if active != "none":
                self.assertIn(active, result.stderr)

    def test_downloaded_archives_match_pins(self):
        for kind in ("aarch64", "doona"):
            asset = receipt()["assets"][kind]
            with (ASSETS / asset["name"]).open("rb") as stream:
                self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(), asset["sha256"])

    def test_core_is_static_aarch64_elf(self):
        with tarfile.open(ASSETS / receipt()["assets"]["aarch64"]["name"]) as archive:
            binary = next(item for item in archive if item.name.endswith("/honk-core"))
            data = archive.extractfile(binary).read()
        self.assertEqual(data[:6], b"\x7fELF\x02\x01")
        self.assertEqual(struct.unpack_from("<H", data, 18)[0], ELF_MACHINE_AARCH64)
        offset = struct.unpack_from("<Q", data, 32)[0]
        entry_size, count = struct.unpack_from("<HH", data, 54)
        types = [struct.unpack_from("<I", data, offset + n * entry_size)[0]
                 for n in range(count)]
        self.assertNotIn(ELF_PROGRAM_INTERPRETER, types)

    def test_doona_assets_and_source_are_bundled(self):
        with tarfile.open(ASSETS / receipt()["assets"]["doona"]["name"]) as archive:
            names = archive.getnames()
            for filename in ("index.html", "SOURCE", "LICENSE", "THIRD-PARTY-NOTICES.txt"):
                self.assertIn("doona/" + filename, names)
            source = archive.extractfile("doona/SOURCE").read().decode()
            self.assertIn(receipt()["pins"]["DOONA_COMMIT"], source)
            self.assertTrue(any(name.startswith("doona/assets/") for name in names))


if __name__ == "__main__":
    unittest.main()
