import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("owrt_fullcone", ROOT / "Scripts/owrt_fullcone.py")
fullcone = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fullcone)

LOOKUP = """+find_appropriate_dst(struct net *net,
+                     struct nf_conntrack_tuple *result)
+{
+\t\t\tnf_ct_invert_tuple(result,
+\t\t\t\t\t   &ct->tuplehash[IP_CT_DIR_ORIGINAL].tuple);
+\t\t\tresult->src = tuple->src;
+\t\t\tfound = 1;
+\t\t\tbreak;
+\t\t}
+\t}
+\tspin_unlock_bh(lock);
+\treturn found;
 }
"""


class FullconeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / fullcone.BASE_PATCH
        self.base.parent.mkdir(parents=True)
        self.base.write_text(LOOKUP)
        self.makefile = self.root / fullcone.PACKAGE_MAKEFILE
        self.makefile.parent.mkdir(parents=True)
        self.makefile.write_text("PKG_VERSION:=20261016\nPKG_RELEASE:=1\n"
                                 "SONIC_SOURCE_VERSION:=43cb2060fc34ccd2714e8ee4db6890da0de537f8\n")
        (self.root / ".config").write_text("CONFIG_PACKAGE_fullconenat-sonic=y\n"
                                           "CONFIG_PACKAGE_luci-app-fullconenat-sonic=y\n")

    def test_backport_is_idempotent_and_records_truthful_source(self):
        receipt = fullcone.install(self.root)
        self.assertEqual("backported", receipt["direction_fix"])
        self.assertEqual("20261016-r1", receipt["package_version"])
        self.assertEqual(fullcone.FIX_COMMIT, receipt["fix_commit"])
        self.assertEqual(receipt, fullcone.install(self.root))
        self.assertEqual(LOOKUP, self.base.read_text())
        self.assertEqual(fullcone.BACKPORT.read_bytes(), (self.root / fullcone.FIX_PATCH).read_bytes())
        installed = self.root / "files/usr/share/fullconenat-sonic/CI-SOURCE.json"
        self.assertEqual(receipt, json.loads(installed.read_text()))

    def test_native_fix_skips_backport_and_removes_only_our_duplicate(self):
        fullcone.install(self.root)
        self.base.write_text(LOOKUP.replace("+\t\t\tfound = 1;",
            "+\t\t\t/* Restored after inversion. */\n"
            "+\t\t\tresult->dst.dir = IP_CT_DIR_ORIGINAL;\n+\t\t\tfound = 1;"))
        self.assertEqual("upstream", fullcone.install(self.root)["direction_fix"])
        self.assertFalse((self.root / fullcone.FIX_PATCH).exists())

    def test_unknown_lookup_fails_without_installing_patch(self):
        self.base.write_text(LOOKUP.replace("result->src = tuple->src;", "new_lookup(result);"))
        with self.assertRaisesRegex(ValueError, "Review changed SONiC"):
            fullcone.install(self.root)
        self.assertFalse((self.root / fullcone.FIX_PATCH).exists())

    def test_unowned_patch_is_not_overwritten(self):
        dest = self.root / fullcone.FIX_PATCH
        dest.write_text("unrelated existing patch\n")
        with self.assertRaisesRegex(ValueError, "existing patch"):
            fullcone.install(self.root)
        self.assertEqual("unrelated existing patch\n", dest.read_text())

    def test_backend_and_luci_must_both_be_selected(self):
        for name in ("fullconenat-sonic", "luci-app-fullconenat-sonic"):
            with self.subTest(package=name):
                (self.root / ".config").write_text(f"CONFIG_PACKAGE_{name}=y\n")
                with self.assertRaisesRegex(ValueError, "SONiC packages"):
                    fullcone.install(self.root)


if __name__ == "__main__":
    unittest.main()
