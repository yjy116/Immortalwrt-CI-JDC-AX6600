"""Validate prepared Honk packages and downloaded inputs, without a router."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("HONK_SOURCE_DIR", ROOT / "wrt/package/openwrt-honk"))
ASSETS = Path(os.environ.get("HONK_ASSET_DIR", ROOT / "wrt/dl"))
CORE_COMMIT = "8b6778cefa12611492187ac2560f014452f0a64a"
DOONA_COMMIT = "25fc26a7a17697c1c11a3b31f51940966ac86c2f"
PACKAGING_COMMIT = "52ecdb1bb26e04be782bcb368973fd54d4a44af6"
SOURCE_URL = "https://github.com/kenzok8/openwrt-honk/releases/download/source-38236606118"
ELF_MACHINE_AARCH64 = 183
ELF_PROGRAM_INTERPRETER = 3


def read(relative):
    return (SOURCE / relative).read_text(encoding="utf-8")


def make_values(relative):
    return dict(re.findall(r"^([A-Z0-9_]+):=(.*)$", read(relative), re.M))


class HonkIntegration(unittest.TestCase):
    def test_packages_are_selected_without_replacing_daede(self):
        config = (ROOT / "Config/GENERAL.txt").read_text(encoding="utf-8")
        for package in ("honk", "luci-app-honk", "dae", "daed", "luci-app-daede"):
            self.assertIn(f"CONFIG_PACKAGE_{package}=y", config.splitlines())
        self.assertNotIn("CONFIG_PACKAGE_luci-app-doona=y", config)

    def test_exact_packaging_and_release_receipt(self):
        head = subprocess.check_output(
            ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(head, PACKAGING_COMMIT)
        receipt = read("ci/HONK-SOURCE.txt")
        self.assertIn(f"PACKAGING_COMMIT={PACKAGING_COMMIT}", receipt)
        self.assertIn("v2026.10.12-r38236606118", receipt)
        self.assertIn("CORE_BUILD=upstream-prebuilt-static-musl", receipt)

    def test_pinned_core_and_doona_metadata(self):
        core = make_values("honk/generated-stage.mk")
        doona = make_values("luci-app-honk/generated-doona-stage.mk")
        self.assertEqual(core["PKG_SOURCE_URL"].rstrip("/"), SOURCE_URL)
        self.assertEqual(doona["PKG_SOURCE_URL"].rstrip("/"), SOURCE_URL)
        for arch in ("AARCH64", "X86_64", "ARMV7"):
            self.assertRegex(core[f"HONK_HASH_{arch}"], r"^[a-f0-9]{64}$")
            self.assertIn(CORE_COMMIT, core[f"HONK_ASSET_{arch}"])
        self.assertEqual(doona["PKG_HASH"], make_values("luci-app-honk/Makefile")["PKG_HASH"])
        provenance = json.loads(read("honk/generated-provenance.json"))
        self.assertEqual(provenance["core"]["commit"], CORE_COMMIT)
        self.assertIn("aarch64", provenance["core"]["architectures"])
        self.assertIn(f"DOONA_COMMIT={DOONA_COMMIT}", read("ci/pins.env"))

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
                                    capture_output=True, timeout=10,
                                    env={**os.environ, "ACTIVE_PROXY": active})
            self.assertEqual(result.returncode, 0 if active == "none" else 1)
            if active != "none":
                self.assertIn(f"conflicting process {active}", result.stderr)

    def test_downloaded_archives_match_pins(self):
        core = make_values("honk/generated-stage.mk")
        doona = make_values("luci-app-honk/generated-doona-stage.mk")
        for name, expected in ((core["HONK_ASSET_AARCH64"], core["HONK_HASH_AARCH64"]),
                               (doona["PKG_SOURCE"], doona["PKG_HASH"])):
            with (ASSETS / name).open("rb") as stream:
                self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(), expected)

    def test_corrupt_stage_is_rejected_before_install(self):
        setup = (ROOT / "Scripts/Honk.sh").read_text(encoding="utf-8")
        function = re.search(r"^download_stage\(\) \{\n.*?^\}", setup, re.M | re.S)
        self.assertIsNotNone(function)
        # Replace network I/O only; exercise the real hash check and installation.
        script = "set -eu\nSOURCE_DIR=.\nHONK_SOURCE_URL=https://example.invalid\n"
        script += 'curl() { printf "tampered input" > "${@: -1}"; }\n'
        script += function.group(0)
        script += '\ndownload_stage generated-stage.mk "' + "0" * 64 + '" honk\n'
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "honk"
            package.mkdir()
            result = subprocess.run(["bash", "-c", script], cwd=directory,
                                    text=True, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FAILED", result.stdout)
            self.assertFalse((package / "generated-stage.mk").exists())

    def test_core_is_static_aarch64_elf(self):
        stage = make_values("honk/generated-stage.mk")
        with tarfile.open(ASSETS / stage["HONK_ASSET_AARCH64"]) as archive:
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
        stage = make_values("luci-app-honk/generated-doona-stage.mk")
        with tarfile.open(ASSETS / stage["PKG_SOURCE"]) as archive:
            names = archive.getnames()
            for filename in ("index.html", "SOURCE", "LICENSE", "THIRD-PARTY-NOTICES.txt"):
                self.assertIn("doona/" + filename, names)
            source = archive.extractfile("doona/SOURCE").read().decode()
            self.assertIn(DOONA_COMMIT, source)
            self.assertTrue(any(name.startswith("doona/assets/") for name in names))


if __name__ == "__main__":
    unittest.main()
