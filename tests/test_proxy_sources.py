"""Use real Git histories to verify fresh resolution and frozen checkouts."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from proxy_sources import checkout, resolve_head, verify_file


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()


class SourceTests(unittest.TestCase):
    def test_new_build_follows_head_while_existing_lock_stays_fixed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "upstream"
            repo.mkdir()
            git(repo, "init", "-b", "main")
            git(repo, "-c", "user.name=Test", "-c", "user.email=test@local",
                "commit", "--allow-empty", "-m", "first")
            first = resolve_head(str(repo))
            git(repo, "-c", "user.name=Test", "-c", "user.email=test@local",
                "commit", "--allow-empty", "-m", "second")
            second = resolve_head(str(repo))
            self.assertNotEqual(first, second)
            checkout(root / "locked", str(repo), first)
            checkout(root / "fresh", str(repo), second)
            self.assertEqual(git(root / "locked", "rev-parse", "HEAD"), first)
            self.assertEqual(git(root / "fresh", "rev-parse", "HEAD"), second)

    def test_invalid_lock_does_not_fall_back_to_latest(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                checkout(Path(folder) / "target", "unused", "main")
            self.assertFalse((Path(folder) / "target").exists())

    def test_corrupt_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive"
            path.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                verify_file(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
