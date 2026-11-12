"""Exercise the narrow source-aware firewall4 archive metadata correction."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Scripts/owrt_firewall4.py"
PACKAGE = Path("package/network/config/firewall4/Makefile")
COMMIT = "3722eadc088c3ab81389596ca9796112b436583a"
BAD_HASH = "a95c6cfe419c7d4e22bda5608aa6e46c67dadc9c7096879702d614cc498759d0"
GOOD_HASH = "9ce4fee1c5f90e5b097216ef49c8ec981adc5911939622d031f555d103a58ba3"
RECIPE = f"""include $(TOPDIR)/rules.mk
PKG_NAME:=firewall4
PKG_RELEASE:=2
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL=$(PROJECT_GIT)/project/firewall4.git
PKG_SOURCE_DATE:=2026-11-08
PKG_SOURCE_VERSION:={COMMIT}
PKG_MIRROR_HASH:={BAD_HASH}
include $(INCLUDE_DIR)/package.mk
$(eval $(call BuildPackage,firewall4))
"""


class FirewallArchive(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / PACKAGE).parent.mkdir(parents=True)
        download = self.root / "include/download.mk"
        download.parent.mkdir()
        download.write_text("PROJECT_GIT = https://git.openwrt.org\n", encoding="utf-8")

    def apply(self, recipe):
        path = self.root / PACKAGE
        path.write_text(recipe, encoding="utf-8", newline="\n")
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root)],
                                text=True, capture_output=True, timeout=10)
        return result, path.read_text(encoding="utf-8")

    def test_known_bad_hash_is_only_recipe_change(self):
        result, changed = self.apply(RECIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(changed, RECIPE.replace(BAD_HASH, GOOD_HASH))
        receipt = json.loads((self.root / "FIREWALL4-SOURCE.json").read_text())
        self.assertEqual(receipt["source_commit"], COMMIT)
        self.assertEqual(receipt["declared_hash"], BAD_HASH)
        self.assertEqual(receipt["effective_hash"], GOOD_HASH)
        self.assertEqual(receipt["state"], "corrected")

    def test_already_corrected_recipe_is_unchanged(self):
        recipe = RECIPE.replace(BAD_HASH, GOOD_HASH)
        result, changed = self.apply(recipe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(changed, recipe)

    def test_future_upstream_revision_is_unchanged(self):
        recipe = RECIPE.replace(COMMIT, "f" * 40).replace(BAD_HASH, "a" * 64)
        result, changed = self.apply(recipe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(changed, recipe)
        receipt = json.loads((self.root / "FIREWALL4-SOURCE.json").read_text())
        self.assertEqual(receipt["state"], "unmodified")
        self.assertEqual(receipt["effective_hash"], "a" * 64)

    def test_unknown_same_revision_metadata_is_rejected_without_writing(self):
        recipes = (RECIPE.replace(BAD_HASH, "a" * 64),
                   RECIPE.replace("2026-11-08", "2026-11-09"),
                   RECIPE.replace("PKG_SOURCE_PROTO:=git", "PKG_SOURCE_PROTO:=svn"),
                   RECIPE.replace("$(PROJECT_GIT)/project", "https://example.invalid/project"),
                   RECIPE + "PKG_SOURCE:=different.tar.zst\n",
                   RECIPE + "PKG_SOURCE_SUBDIR:=different\n",
                   RECIPE + "PKG_VERSION:=different\n",
                   RECIPE + f"PKG_MIRROR_HASH:={GOOD_HASH}\n")
        for recipe in recipes:
            with self.subTest(recipe=recipe):
                result, changed = self.apply(recipe)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(changed, recipe)
                self.assertFalse((self.root / "FIREWALL4-SOURCE.json").exists())

    def test_changed_project_git_is_not_silently_rebound(self):
        (self.root / "include/download.mk").write_text(
            "PROJECT_GIT = https://example.invalid\n", encoding="utf-8")
        result, changed = self.apply(RECIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(changed, RECIPE)


if __name__ == "__main__":
    unittest.main()
