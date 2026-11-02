"""Guard the read-only upstream harness and truthful package identity parsing."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("upstream", ROOT / "Scripts/luci_upnp/upstream.py")
UPSTREAM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPSTREAM)
IMPORTS = "import { popen, readfile } from 'fs';\nimport { connect } from 'ubus';\nimport { cursor } from 'uci';\n"
BODY = "function read_nft_rules() { return popen('nft --json list chain'); }\n"


class HarnessTests(unittest.TestCase):
    def test_preserves_reader_and_binds_io(self):
        source = IMPORTS + BODY + UPSTREAM.EXPORT
        generated = UPSTREAM.harness_source(source)
        self.assertIn(BODY, generated)
        self.assertIn('const popen = io.popen;', generated)
        self.assertIn('const system = io.system;', generated)
        self.assertNotIn("from 'fs'", generated)

    def test_unknown_import_or_export_is_rejected(self):
        source = IMPORTS + BODY + UPSTREAM.EXPORT
        for original, replacement in (("'fs'", "'fs2'"), (UPSTREAM.EXPORT, 'return {};')):
            with self.assertRaises(ValueError):
                UPSTREAM.harness_source(source.replace(original, replacement))

    def test_old_text_reader_is_not_misclassified(self):
        with self.assertRaisesRegex(ValueError, 'JSON'):
            UPSTREAM.harness_source(IMPORTS + BODY.replace(' --json', '') + UPSTREAM.EXPORT)

    def test_duplicate_package_version_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Makefile'
            path.write_text('PKG_VERSION:=one\nPKG_VERSION:=two\n')
            with self.assertRaises(ValueError):
                UPSTREAM.assignment(path, 'PKG_VERSION')

    def test_version_is_read_not_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Makefile'
            path.write_text('PKG_VERSION:=20991231\nPKG_RELEASE:=9\n')
            self.assertEqual(UPSTREAM.package_identity(path.parent),
                             {'version': '20991231', 'release': '9'})


if __name__ == '__main__':
    unittest.main()
