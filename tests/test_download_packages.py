"""Check download stage ordering and failure propagation without network access."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Scripts/download_packages.sh"
STAGES = ("tools/flock/compile tools/zstd/compile", "tools/download",
          "toolchain/download", "package/download", "target/download")
TEST_TIMEOUT = 10
FAILURE_CODE = 23


class DownloadStages(unittest.TestCase):
    def run_download(self, failing=""):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            make = bin_dir / "make"
            make.write_text(
                '#!/bin/sh\n'
                'printf "%s\\n" "$*" >> "$CALL_LOG"\n'
                'printf "%s\\n" "$*" | grep -Fq -- "$FAIL_TARGET" && '
                '[ -n "$FAIL_TARGET" ] && { echo "download failed" >&2; exit 23; }\n'
                'exit 0\n', encoding="utf-8", newline="\n")
            make.chmod(0o755)
            log = root / "calls.log"
            env = {**os.environ, "CALL_LOG": str(log), "FAIL_TARGET": failing}
            # Git Bash must translate Windows paths before constructing PATH.
            command = 'export PATH="$(cd "$1" && pwd):$PATH"; bash "$2" "$3"'
            result = subprocess.run(
                ["bash", "-c", command, "test", str(bin_dir), str(SCRIPT), str(root)],
                env=env, text=True, capture_output=True, timeout=TEST_TIMEOUT)
            calls = log.read_text().splitlines() if log.exists() else []
            return result, calls

    def test_success_runs_every_download_stage(self):
        result, calls = self.run_download()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), len(STAGES))
        for call, stage in zip(calls, STAGES):
            self.assertTrue(call.endswith(stage), call)
            self.assertIn("V=s", call)

    def test_failure_stops_before_later_stages(self):
        for index, stage in enumerate(STAGES):
            with self.subTest(stage=stage):
                result, calls = self.run_download(stage.split()[0])
                self.assertEqual(result.returncode, FAILURE_CODE, result.stderr)
                self.assertEqual(len(calls), index + 1)
                self.assertIn("download failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
