#!/usr/bin/env python3
"""Resolve maintenance refs, prepare hash-checked receipts and verify downloads."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from proxy_metadata import (REPOSITORIES, checked_commit, checked_hash, daede_metadata,
                            honk_metadata, pins_values, require, verify_provenance)


def run(*args):
    return subprocess.check_output(args, text=True, encoding="utf-8").strip()


def resolve_head(repository):
    result = run("git", "ls-remote", "--exit-code", repository, "refs/heads/main")
    fields = result.split()
    require(len(fields) == 2 and fields[1] == "refs/heads/main", "Ambiguous upstream main")
    return checked_commit(fields[0])


def checkout(destination, repository, commit):
    checked_commit(commit)
    require(not destination.exists(), f"Checkout destination already exists: {destination}")
    run("git", "init", str(destination))
    run("git", "-C", str(destination), "fetch", "--depth=1", repository, commit)
    run("git", "-C", str(destination), "-c", "core.autocrlf=false", "checkout", "--detach", "FETCH_HEAD")
    require(run("git", "-C", str(destination), "rev-parse", "HEAD") == commit, "Checkout SHA mismatch")


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_file(path, expected):
    checked_hash(expected)
    require(file_hash(path) == expected, f"SHA-256 mismatch: {path}")


def download_verified(destination, asset):
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    subprocess.run(["curl", "--fail", "--location", "--show-error", "--silent",
                    asset["url"], "-o", str(temporary)], check=True)
    verify_file(temporary, asset["sha256"])
    temporary.replace(destination)


def honk_provenance(source, metadata, pins):
    tag = metadata["source_tag"]
    release = json.loads(run("gh", "api", f"repos/kenzok8/openwrt-honk/releases/tags/{tag}"))
    require(release["tag_name"] == tag and not release["draft"], "Unexpected source release")
    assets = {asset["name"]: asset for asset in release["assets"]}
    for asset in metadata["assets"].values():
        remote = assets[asset["name"]]
        require(remote["digest"] == "sha256:" + asset["sha256"], "Release/Makefile hash mismatch")
    remote = assets["generated-provenance.json"]
    digest = remote["digest"]
    require(digest.startswith("sha256:"), "Missing provenance SHA-256")
    url = REPOSITORIES["honk"].removesuffix(".git") + f"/releases/download/{tag}/{remote['name']}"
    asset = {"url": url, "sha256": checked_hash(digest.removeprefix("sha256:"))}
    destination = source / "honk/generated-provenance.json"
    download_verified(destination, asset)
    provenance = json.loads(destination.read_text(encoding="utf-8"))
    verify_provenance(provenance, pins)
    return {"asset": asset, "release_id": release["id"], "content": provenance}


def prepare(source, kind):
    pins_text = (source / "ci/pins.env").read_text(encoding="utf-8")
    pins = pins_values(pins_text)
    packages = ("dae", "daed", "luci-app-daede") if kind == "daede" else ("honk", "luci-app-honk")
    makefiles = {name: (source / name / "Makefile").read_text(encoding="utf-8") for name in packages}
    if kind == "daede":
        metadata = daede_metadata(makefiles, pins)
    else:
        for path in ("honk/generated-stage.mk", "luci-app-honk/generated-doona-stage.mk"):
            require(not (source / path).exists(), f"Unexpected Make override: {path}")
        metadata = honk_metadata(makefiles["honk"], makefiles["luci-app-honk"], pins)
        metadata = {**metadata, "provenance": honk_provenance(source, metadata, pins),
                    "core_build": "upstream-prebuilt-static-musl"}
    receipt = {**metadata, "packaging_repository": REPOSITORIES[kind], "packaging_branch": "main",
               "packaging_commit": checked_commit(run("git", "-C", str(source), "rev-parse", "HEAD")),
               "pins": pins, "files_sha256": tracked_hashes(source)}
    write_receipt(source, kind, receipt, pins_text)


def tracked_hashes(source):
    files = run("git", "-C", str(source), "ls-files").splitlines()
    migration = "luci-app-daede/root/etc/uci-defaults/89-daede-migrate"
    extra = [migration] if (source / migration).exists() else []
    return {name: file_hash(source / name) for name in sorted(set(files + extra))}


def write_receipt(source, kind, receipt, pins_text):
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    (source / "ci/PROXY-SOURCE.json").write_text(encoded, encoding="utf-8")
    header = (f"PACKAGING_REPO={receipt['packaging_repository']}\nPACKAGING_BRANCH=main\n"
              f"PACKAGING_COMMIT={receipt['packaging_commit']}\n")
    if kind == "honk":
        header += f"SOURCE_TAG={receipt['source_tag']}\nCORE_BUILD={receipt['core_build']}\n"
    (source / f"ci/{kind.upper()}-SOURCE.txt").write_text(header + pins_text + "\n" + encoded,
                                                         encoding="utf-8")


def verify_downloads(source, downloads):
    receipt = json.loads((source / "ci/PROXY-SOURCE.json").read_text(encoding="utf-8"))
    require(tracked_hashes(source) == receipt["files_sha256"], "Prepared package changed after verification")
    # This firmware is AArch64; other core architectures remain pinned in the receipt.
    for name, asset in receipt["assets"].items():
        if name not in ("x86_64", "armv7"):
            verify_file(downloads / asset["name"], asset["sha256"])
            print(f"Verified {name}: {asset['name']}")
    if "provenance" in receipt:
        verify_file(source / "honk/generated-provenance.json", receipt["provenance"]["asset"]["sha256"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("resolve", "checkout", "prepare", "verify"))
    parser.add_argument("kind", choices=tuple(REPOSITORIES) + ("all",))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--commit")
    parser.add_argument("--downloads", type=Path)
    args = parser.parse_args()
    if args.command == "resolve":
        kinds = REPOSITORIES if args.kind == "all" else (args.kind,)
        for kind in kinds:
            print(f"{kind.upper()}_COMMIT={resolve_head(REPOSITORIES[kind])}")
        return
    require(args.kind in REPOSITORIES and args.source is not None, "kind/source required")
    if args.command == "checkout":
        commit = args.commit if args.commit else resolve_head(REPOSITORIES[args.kind])
        checkout(args.source, REPOSITORIES[args.kind], commit)
    elif args.command == "prepare":
        prepare(args.source, args.kind)
    else:
        require(args.downloads is not None, "downloads required")
        verify_downloads(args.source, args.downloads)


if __name__ == "__main__":
    main()
