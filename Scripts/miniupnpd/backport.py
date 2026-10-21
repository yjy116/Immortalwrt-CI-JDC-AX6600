"""Apply missing official fixes after feed patches; verify before compilation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from source_checks import (SOURCE_FILES, nft_family_fixed, parser_refactored,
                           private_wan_fixed, verify)

BUNDLE = Path(__file__).resolve().parent
RECEIPT = "miniupnpd-backports.json"
PATCH_TIMEOUT = 15
PATCHES = {
    "010-private-wan-recovery.patch": (
        "2dcf63959950dbb2c3f97b7bd63773d499749134",
        "7693f9de36a2d564f1f5b629b6be4c618419f6052ed6bd719e4623af62a44f48"),
    "020-nft-meta-parser.patch": (
        "320ebf576432cef95b0964e42bb5a4c6c8633e7e",
        "01559c62ee09efff86cee45761f11098237379d400b20cc37e83c88b8d8bfca7"),
    "030-nft-family-match.patch": (
        "a8de55a0ae4829d59498667120d1e88933dc0f5d",
        "9285fa038ebfe31cbb878098fd2ada6d6cd0ed3691e827e7e1f34862c4840daf"),
}


def source_hashes(directory):
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in SOURCE_FILES}


def checked_patch(name):
    path = BUNDLE / "patches" / name
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != PATCHES[name][1]:
        raise ValueError(f"Backport patch hash mismatch: {name}")
    return data


def apply_patch(directory, name):
    data = checked_patch(name)
    command = ["patch", "--batch", "--forward", "--fuzz=0",
               "--no-backup-if-mismatch", "-p1"]
    for flags in (["--dry-run"], []):
        result = subprocess.run(command + flags, cwd=directory, input=data,
                                capture_output=True, timeout=PATCH_TIMEOUT)
        if result.returncode:
            detail = (result.stdout + result.stderr).decode("utf-8", errors="replace")
            raise ValueError(f"Cannot apply {name}; review upstream changes:\n{detail}")


def fix_source(directory):
    state = {"private_wan": "already-present", "nft_family": "already-present"}
    if not private_wan_fixed(directory):
        apply_patch(directory, "010-private-wan-recovery.patch")
        state["private_wan"] = "applied"
    if not nft_family_fixed(directory):
        if not parser_refactored(directory):
            apply_patch(directory, "020-nft-meta-parser.patch")
        apply_patch(directory, "030-nft-family-match.patch")
        state["nft_family"] = "applied"
    verify(directory)
    return state


def prepare(options):
    for name in PATCHES:
        checked_patch(name)
    # A conflict must not leave a half-patched build tree or a success receipt.
    receipt = options.source / RECEIPT
    receipt.unlink(missing_ok=True)
    before = source_hashes(options.source)
    with tempfile.TemporaryDirectory(prefix="miniupnpd-backport-") as temporary:
        scratch = Path(temporary)
        for name in SOURCE_FILES:
            (scratch / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(options.source / name, scratch / name)
        state = fix_source(scratch)
        for name in SOURCE_FILES:
            if (scratch / name).read_bytes() != (options.source / name).read_bytes():
                shutil.copyfile(scratch / name, options.source / name)
    report = {"version": options.version, "release": options.release,
              "variant": options.variant, "fixes": state,
              "upstream_commits": {name: data[0] for name, data in PATCHES.items()},
              "patch_sha256": {name: data[1] for name, data in PATCHES.items()},
              "input_sha256": before, "source_sha256": source_hashes(options.source)}
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def verify_receipt(directory):
    verify(directory)
    report = json.loads((directory / RECEIPT).read_text(encoding="utf-8"))
    if report["source_sha256"] != source_hashes(directory):
        raise ValueError("Prepared MiniUPnP source hash changed before compilation")
    print("MiniUPnP official fixes and prepared source hashes verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--release", default="unknown")
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--verify-only", action="store_true")
    options = parser.parse_args()
    if options.verify_only:
        verify_receipt(options.source)
    else:
        prepare(options)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"ERROR: MiniUPnP backport: {error}", file=sys.stderr)
        sys.exit(1)
