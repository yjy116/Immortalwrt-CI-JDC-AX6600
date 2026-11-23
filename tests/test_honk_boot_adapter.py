"""Replay the boot adapter on pristine upstream files and exercise source drift."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ["HONK_SOURCE_DIR"]).resolve()
CONTROL = "honk/files/control.sh"
VIEW = "luci-app-honk/htdocs/luci-static/resources/view/honk/"
MENU = "luci-app-honk/root/usr/share/luci/menu.d/luci-app-honk.json"
PATHS = (CONTROL, "honk/files/90-honk-boot", "honk/files/honk.init",
         "luci-app-honk/root/usr/libexec/rpcd/honk", MENU,
         "luci-app-honk/root/usr/share/rpcd/acl.d/luci-app-honk.json",
         "luci-app-honk/Makefile", VIEW + "overview.js", VIEW + "rpc.js")


class HonkBootAdapterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.source = Path(directory.name)
        for path in PATHS:
            result = subprocess.run(["git", "-C", str(SOURCE), "show", f"HEAD:{path}"],
                                    capture_output=True, check=True, timeout=10)
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result.stdout)

    def adapt(self):
        return subprocess.run([sys.executable, str(ROOT / "Scripts/honk_boot.py"), str(self.source)],
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_replay_preserves_upstream_views_menu_and_settings_logic(self):
        views = {name: (self.source / VIEW / name).read_bytes() for name in ("overview.js", "rpc.js")}
        menu = json.loads((self.source / MENU).read_bytes())
        control = self.source / CONTROL
        original = control.read_bytes()
        result = self.adapt()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, content in views.items():
            self.assertEqual((self.source / VIEW / name).read_bytes(), content)
        self.assertEqual(control.read_bytes(), original.replace(
            b"new_boot_enabled=1 ;; esac\n\tnew_boot_enabled=1\n",
            b"new_boot_enabled=$boot_enabled ;; esac\n", 1))
        updated = json.loads((self.source / MENU).read_bytes())
        local = updated.pop("admin/services/honk/boot-policy")
        self.assertEqual(updated, menu)
        self.assertEqual(local["action"], {"type": "view", "path": "honk/boot-policy"})
        self.assertTrue((self.source / VIEW / "boot-policy.js").is_file())

    def test_prepared_upstream_views_are_untouched(self):
        for path in (VIEW + "overview.js", VIEW + "rpc.js"):
            self.assertEqual((SOURCE / path).read_bytes(), (self.source / path).read_bytes())

    def test_unrelated_context_drift_does_not_block_preparation(self):
        control = self.source / CONTROL
        before = control.read_bytes().replace(
            b"\tnew_boot_enabled=1\n", b"\t# New upstream explanation\n\tnew_boot_enabled=1\n")
        self.assertIn(b"# New upstream explanation", before)
        control.write_bytes(before)
        init = self.source / "honk/files/honk.init"
        init.write_bytes(init.read_bytes().replace(b"boot() {\n", b"boot() {\n\t# New upstream comment\n"))
        result = self.adapt()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"# New upstream explanation", control.read_bytes())
        self.assertIn(b"# New upstream comment", init.read_bytes())

    def test_unknown_forcing_statement_fails_without_partial_edits(self):
        control = self.source / CONTROL
        before = control.read_bytes().replace(b"\tnew_boot_enabled=1\n", b"\tnew_boot_enabled=2\n")
        self.assertIn(b"\tnew_boot_enabled=2\n", before)
        control.write_bytes(before)
        result = self.adapt()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("settings forced boot preference", result.stderr)
        self.assertEqual(control.read_bytes(), before)
        self.assertFalse((self.source / VIEW / "boot-policy.js").exists())


if __name__ == "__main__":
    unittest.main()
