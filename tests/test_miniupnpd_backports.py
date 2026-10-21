"""Offline integration tests against the actual upstream release and master."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Scripts/miniupnpd/backport.py"
INSTALLER = ROOT / "Scripts/miniupnpd/install.py"
FIXTURES = Path(os.environ["MINIUPNPD_TEST_DIR"])
FILES = ("miniupnpd.c", "netfilter_nft/nftnlrdr_misc.c",
         "netfilter_nft/nftnlrdr_misc.h")
TIMEOUT = 15


def snapshot(directory):
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in FILES}


class BackportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / "source"
        self.source.mkdir()
        self.copy_source(FIXTURES / "miniupnpd-2.3.11")

    def copy_source(self, source):
        for name in FILES:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)

    def run_backport(self, *options):
        self.assertTrue(SCRIPT.is_file(), "upgrade-aware backport runner is missing")
        return subprocess.run([sys.executable, str(SCRIPT), str(self.source),
                               *options], capture_output=True, text=True,
                              timeout=TIMEOUT)

    def apply(self):
        result = self.run_backport("--version", "2.3.11", "--release", "1",
                                   "--variant", "nftables")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.source / "miniupnpd-backports.json").read_text())

    def test_old_source_gets_both_fixes_and_receipt(self):
        before = snapshot(self.source)
        report = self.apply()
        self.assertNotEqual(before, snapshot(self.source))
        self.assertEqual(report["fixes"], {"private_wan": "applied", "nft_family": "applied"})
        self.assertEqual(report["source_sha256"], snapshot(self.source))
        self.assertEqual(self.run_backport("--verify-only").returncode, 0)

    def test_repeated_prepare_is_noop(self):
        self.apply()
        before = snapshot(self.source)
        report = self.apply()
        self.assertEqual(before, snapshot(self.source))
        self.assertEqual(set(report["fixes"].values()), {"already-present"})

    def test_official_master_needs_no_patch(self):
        self.copy_source(FIXTURES / "upstream/miniupnpd")
        before = snapshot(self.source)
        report = self.apply()
        self.assertEqual(before, snapshot(self.source))
        self.assertEqual(set(report["fixes"].values()), {"already-present"})

    def test_current_feed_patches_then_local_fixes(self):
        feed = FIXTURES / "packages/net/miniupnpd/patches"
        # Feed patches also touch other source files, so use the complete release.
        shutil.copytree(FIXTURES / "miniupnpd-2.3.11", self.source, dirs_exist_ok=True)
        for patch in sorted(feed.glob("*.patch")):
            result = subprocess.run(["patch", "--batch", "--fuzz=0", "-p1"],
                                    input=patch.read_bytes().replace(b"\r\n", b"\n"),
                                    cwd=self.source, capture_output=True, timeout=TIMEOUT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.apply()
        self.assertEqual(self.run_backport("--verify-only").returncode, 0)

    def test_only_wan_fixed_upstream_still_gets_nft_fix(self):
        self.apply()
        for name in FILES[1:]:
            shutil.copyfile(FIXTURES / "miniupnpd-2.3.11" / name, self.source / name)
        report = self.apply()
        self.assertEqual(report["fixes"], {"private_wan": "already-present", "nft_family": "applied"})

    def test_partial_upstream_backport_only_fills_missing_fix(self):
        self.apply()
        shutil.copyfile(FIXTURES / "miniupnpd-2.3.11/miniupnpd.c",
                        self.source / "miniupnpd.c")
        report = self.apply()
        self.assertEqual(report["fixes"], {"private_wan": "applied", "nft_family": "already-present"})

    def test_source_conflict_is_explicit_and_does_not_partially_patch(self):
        path = self.source / FILES[1]
        path.write_text(path.read_text().replace("parse_rule_meta(", "changed_parser("))
        before = snapshot(self.source)
        result = self.run_backport()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR", result.stderr)
        self.assertEqual(before, snapshot(self.source))
        self.assertFalse((self.source / "miniupnpd-backports.json").exists())

    def test_incomplete_family_fix_is_not_mistaken_for_success(self):
        self.copy_source(FIXTURES / "upstream/miniupnpd")
        path = self.source / FILES[1]
        text = path.read_text().replace("expr_add_nfproto(r, NFPROTO_IPV4);", "", 1)
        path.write_text(text)
        result = self.run_backport()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR", result.stderr)

    def test_missing_source_is_an_error(self):
        (self.source / FILES[2]).unlink()
        self.assertNotEqual(self.run_backport().returncode, 0)

    def test_compile_verification_rejects_modified_source(self):
        self.apply()
        path = self.source / "miniupnpd.c"
        path.write_text(path.read_text() + "\n/* modified after prepare */\n")
        result = self.run_backport("--verify-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", result.stderr.lower())

    def test_patch_hash_mismatch_is_rejected(self):
        self.assertTrue(SCRIPT.exists(), "backport runner is missing")
        bundle = Path(self.temporary.name) / "bundle"
        shutil.copytree(SCRIPT.parent, bundle)
        patch = bundle / "patches/010-private-wan-recovery.patch"
        patch.write_bytes(patch.read_bytes() + b"\nmodified\n")
        result = subprocess.run([sys.executable, str(bundle / SCRIPT.name), str(self.source)],
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", result.stderr.lower())


class InstallerTests(unittest.TestCase):
    def test_install_is_idempotent_and_does_not_pin_version(self):
        self.assertTrue(INSTALLER.exists(), "feed integration installer is missing")
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            makefile = package / "Makefile"
            original = "PKG_VERSION:=9.9.9\nPKG_RELEASE:=7\n"
            original += "$(eval $(call BuildPackage,miniupnpd-nftables))\n"
            makefile.write_text(original)
            for _ in range(2):
                result = subprocess.run([sys.executable, str(INSTALLER), directory],
                                        capture_output=True, text=True, timeout=TIMEOUT)
                self.assertEqual(result.returncode, 0, result.stderr)
            updated = makefile.read_text()
            self.assertIn("PKG_VERSION:=9.9.9\nPKG_RELEASE:=7\n", updated)
            self.assertEqual(updated.count("include $(CURDIR)/miniupnpd-backports/hooks.mk"), 1)
            self.assertLess(updated.index("hooks.mk"), updated.index("$(eval"))
            self.assertTrue((package / "miniupnpd-backports/backport.py").exists())


if __name__ == "__main__":
    unittest.main()
