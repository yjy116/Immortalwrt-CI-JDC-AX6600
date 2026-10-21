"""Source-aware repair and compatibility tests; no router or network mutations."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("luci_upnp", ROOT / "Scripts/luci_upnp/install.py")
FIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIX)
BASELINE = ROOT / "tests/fixtures/luci_upnp/luci.upnp"


class LuCIParserTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / "luci.upnp"
        self.original = BASELINE.read_bytes()
        self.source.write_bytes(self.original)

    def test_real_upstream_fixture_exposes_counter_bug(self):
        result = FIX.validate(self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy-tcp-counter", result.stderr)

    def test_repair_passes_all_rule_cases_and_is_idempotent(self):
        self.assertEqual(FIX.install(self.source)["status"], "applied")
        updated = self.source.read_bytes()
        self.assertEqual(FIX.validate(self.source).returncode, 0)
        self.assertEqual(FIX.install(self.source)["status"], "already-compatible")
        self.assertEqual(self.source.read_bytes(), updated)

    def test_unmerged_counter_only_proposal_is_not_sufficient(self):
        proposed = self.original.decode().replace(FIX.OLD_PATTERN, FIX.PR9148_PATTERN)
        self.source.write_text(proposed, encoding="utf-8")
        result = FIX.validate(self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live-20261021-tcp", result.stderr)
        self.assertEqual(FIX.install(self.source)["status"], "applied")

    def test_unrelated_future_upstream_changes_are_preserved(self):
        updated = FIX.repair_source(self.original.decode())
        updated = updated.replace("// Copyright 2022", "// Future upstream\n// Copyright 2022")
        # An equivalent implementation, not just our exact output, must be kept.
        updated = updated.replace("m[2] == '0x6' || m[2] == 'tcp'",
                                  "m[2] == 'tcp' || m[2] == '0x6'")
        self.source.write_text(updated, encoding="utf-8", newline="\n")
        self.assertEqual(FIX.install(self.source)["status"], "already-compatible")
        self.assertEqual(self.source.read_text(encoding="utf-8"), updated)

    def test_unknown_parser_fails_without_modifying_source(self):
        unknown = self.original.replace(b"@nh,72,8", b"@nh,72,16")
        self.source.write_bytes(unknown)
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            FIX.install(self.source)
        self.assertEqual(self.source.read_bytes(), unknown)

    def test_only_nft_reader_changes(self):
        before = self.original.decode()
        after = FIX.repair_source(before)
        start = before.index("\t\t\tif (nft) {")
        suffix = "\n\t\t\treturn ubus.defer("
        self.assertEqual(after[:start], before[:start])
        self.assertEqual(after[after.index(suffix):], before[before.index(suffix):])
        self.assertEqual(len(after.splitlines()), len(before.splitlines()))
        differences = sum(a != b for a, b in zip(after.splitlines(), before.splitlines()))
        self.assertEqual(differences, 5)

    def test_cli_receipt_matches_actual_source(self):
        receipt = self.source.with_suffix(".json")
        subprocess.run([sys.executable, str(ROOT / "Scripts/luci_upnp/install.py"),
                        str(self.source), "--receipt", str(receipt)],
                       check=True, capture_output=True, timeout=60)
        data = json.loads(receipt.read_text())
        self.assertEqual(data["output_sha256"], FIX.hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertNotEqual(data["input_sha256"], data["output_sha256"])


if __name__ == "__main__":
    unittest.main()
