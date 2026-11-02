"""Check source hooks support the upstream monorepo without version pinning."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("installer", ROOT / "Scripts/miniupnpd/install.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class LayoutTests(unittest.TestCase):
    def test_nested_source_paths_used_by_all_hooks(self):
        text = (ROOT / "Scripts/miniupnpd/hooks.mk").read_text()
        self.assertIn('MINIUPNPD_FIX_SOURCE = $(PKG_BUILD_DIR)/$(CONFIGURE_PATH)', text)
        self.assertEqual(text.count('"$(MINIUPNPD_FIX_SOURCE)"'), 2)
        self.assertIn('"$(MINIUPNPD_FIX_SOURCE)/miniupnpd-backports.json"', text)
        self.assertIn('--source-commit "$(PKG_SOURCE_VERSION)"', text)
        self.assertIn('--archive-sha256 "$(PKG_HASH)"', text)

    def test_unknown_layout_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            path = package / "Makefile"
            original = 'CONFIGURE_PATH:=new-daemon\n$(eval $(call BuildPackage,miniupnpd-nftables))\n'
            path.write_text(original)
            with self.assertRaisesRegex(ValueError, 'layout'):
                INSTALLER.install(package)
            self.assertEqual(path.read_text(), original)

    def test_nested_install_keeps_upstream_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            path = package / "Makefile"
            path.write_text('PKG_VERSION:=20261101\nCONFIGURE_PATH:=miniupnpd\n'
                            '$(eval $(call BuildPackage,miniupnpd-nftables))\n')
            INSTALLER.install(package)
            INSTALLER.install(package)
            self.assertIn('PKG_VERSION:=20261101', path.read_text())
            self.assertEqual(path.read_text().count(INSTALLER.INCLUDE), 1)


if __name__ == '__main__':
    unittest.main()
