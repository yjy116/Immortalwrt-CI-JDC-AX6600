"""Reject drift between maintained pins, Makefiles and released assets."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from proxy_metadata import assignment, checked_hash, daede_metadata, honk_metadata, verify_provenance

CORE = "a" * 40
HASH = "b" * 64
PINS = {"CORE_COMMIT": CORE, "CORE_REPOSITORY": "https://github.com/daeuniverse/honk.git",
        "DOONA_COMMIT": "c" * 40, "DOONA_ARCHIVE": "doona-cccccccc-bbbbbbbbbbbb.tar.gz"}
CORE_MAKE = f"""PKG_VERSION:=2026.11.03
PKG_RELEASE:=1
CORE_COMMIT:={CORE}
HONK_SOURCE_TAG?=source-123
HONK_SOURCE_URL?=https://github.com/kenzok8/openwrt-honk/releases/download/$(HONK_SOURCE_TAG)
PKG_SOURCE:=$(HONK_ASSET)
PKG_SOURCE_URL?=$(HONK_SOURCE_URL)/
PKG_HASH:=$(HONK_HASH)
""" + "".join(f"HONK_ASSET_{arch}?=honk-core-$(CORE_COMMIT)-{arch.lower()}.tar.gz\n"
              f"HONK_HASH_{arch}?={HASH}\n" for arch in ("AARCH64", "X86_64", "ARMV7"))
UI_MAKE = f"""PKG_VERSION:=2026.11.03
PKG_RELEASE:=1
HONK_SOURCE_TAG?=source-123
PKG_SOURCE_URL?=https://github.com/kenzok8/openwrt-honk/releases/download/$(HONK_SOURCE_TAG)
PKG_SOURCE:={PINS['DOONA_ARCHIVE']}
PKG_HASH:={HASH}
"""


class MetadataTests(unittest.TestCase):
    def test_reads_latest_makefile_hashes_not_historical_constants(self):
        result = honk_metadata(CORE_MAKE, UI_MAKE, PINS)
        self.assertEqual(result["source_tag"], "source-123")
        self.assertEqual(result["assets"]["aarch64"]["sha256"], HASH)
        self.assertEqual(result["assets"]["doona"]["name"], PINS["DOONA_ARCHIVE"])

    def test_mismatched_tag_and_pin_fail(self):
        for core, ui in ((CORE_MAKE, UI_MAKE.replace("source-123", "source-456")),
                         (CORE_MAKE.replace(CORE, "d" * 40), UI_MAKE)):
            with self.assertRaises(ValueError):
                honk_metadata(core, ui, PINS)

    def test_missing_or_skip_hash_fails(self):
        for value in ("SKIP", "", "b" * 63, "$(shell command)"):
            with self.assertRaises(ValueError):
                checked_hash(value)

    def test_duplicate_assignment_cannot_hide_override(self):
        for operator in (":=", "+="):
            with self.assertRaises(ValueError):
                assignment(f"PKG_HASH:=good\nPKG_HASH{operator}SKIP\n", "PKG_HASH")

    def test_moving_source_url_and_unsafe_asset_fail(self):
        for ui in (UI_MAKE.replace("$(HONK_SOURCE_TAG)", "staging"),
                   UI_MAKE.replace(PINS["DOONA_ARCHIVE"], "../bad.tar.gz")):
            with self.assertRaises(ValueError):
                honk_metadata(CORE_MAKE, ui, PINS)

    def test_provenance_must_match_maintainer_core_and_architecture(self):
        valid = {"core": {"repository": PINS["CORE_REPOSITORY"],
                          "commit": CORE, "architectures": ["aarch64", "armv7", "x86_64"]}}
        verify_provenance(valid, PINS)
        for update in ({"commit": "d" * 40}, {"architectures": ["x86_64"]},
                       {"repository": "https://example.invalid/core.git"}):
            with self.assertRaises(ValueError):
                verify_provenance({"core": {**valid["core"], **update}}, PINS)

    def test_daede_rejects_missing_or_mismatched_source_pins(self):
        pins = {"DAE_VERSION": "2026.10.30", "DAED_VERSION": "2026.10.30"}
        pins.update({name: CORE for name in ("CORE_COMMIT", "CORE_UPSTREAM_COMMIT",
                    "DAED_COMMIT", "WING_COMMIT", "OUTBOUND_COMMIT",
                    "QUICGO_BASE_COMMIT", "QUICGO_PERF_TIP")})
        makefiles = {name: f"PKG_VERSION:=2026.10.30\nPKG_RELEASE:=1\n"
                     f"PKG_SOURCE:={name}-src-2026.10.30-bbbbbbbbbbbb.tar.gz\n"
                     f"PKG_SOURCE_URL:=https://github.com/kenzok8/openwrt-daede/releases/download/{name}-src\n"
                     f"PKG_HASH:={HASH}\n" for name in ("dae", "daed")}
        makefiles["luci-app-daede"] = "PKG_VERSION:=1.15\nPKG_RELEASE:=6\n"
        self.assertEqual(daede_metadata(makefiles, pins)["assets"]["dae"]["sha256"], HASH)
        for changed in ({key: value for key, value in pins.items() if key != "CORE_COMMIT"},
                        {**pins, "DAED_VERSION": "2026.01.01"}):
            with self.assertRaises(ValueError):
                daede_metadata(makefiles, changed)


if __name__ == "__main__":
    unittest.main()
