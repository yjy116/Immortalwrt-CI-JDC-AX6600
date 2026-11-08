"""Apply the boot opt-in patch to pristine files from the selected upstream SHA."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ["HONK_SOURCE_DIR"]).resolve()
PATCH = ROOT / "patches/honk/010-preserve-boot-opt-in.patch"


class HonkBootPatchTests(unittest.TestCase):
    def test_selected_upstream_accepts_complete_patch_without_fuzz(self):
        patch = PATCH.read_bytes()
        paths = [line.removeprefix("+++ b/") for line in patch.decode().splitlines()
                 if line.startswith("+++ b/")]
        with tempfile.TemporaryDirectory() as directory:
            for name in paths:
                result = subprocess.run(["git", "-C", str(SOURCE), "show", f"HEAD:{name}"],
                                        capture_output=True, check=True, timeout=10)
                target = Path(directory) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(result.stdout)
            result = subprocess.run(
                ["bash", "-c", "patch --dry-run --batch --forward --fuzz=0 -p1"],
                input=patch, capture_output=True, cwd=directory, timeout=10)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode())


if __name__ == "__main__":
    unittest.main()
