"""Verify the complete upstream UPnP pair without rewriting its JSON reader."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 60
RPC_PATH = "luci-app-upnp/root/usr/share/rpcd/ucode/luci.upnp"
IMPORT = re.compile(r"^import \{ ([a-z_, ]+) \} from '(fs|ubus|uci)';$", re.M)
EXPORT = "return { 'luci.upnp': methods };"


def harness_source(source):
    imports = IMPORT.findall(source)
    if sorted(module for _, module in imports) != ["fs", "ubus", "uci"]:
        raise ValueError("Unknown UPnP imports; review upstream before testing")
    if source.count(EXPORT) != 1 or "nft --json list chain" not in source:
        raise ValueError("Expected the upstream JSON UPnP reader")
    bindings = [f"const {name.strip()} = io.{name.strip()};"
                for names, _ in imports for name in names.split(",")]
    bindings += ["const system = io.system;", "const sleep = io.sleep;"]
    body = IMPORT.sub("", source).replace(
        EXPORT, "return { methods, read_nft_rules, parse_lease, remove_lease };")
    return "return function(io) {\n" + "\n".join(bindings) + "\n" + body + "\n};\n"


def assignment(path, name):
    text = path.read_text(encoding="utf-8")
    found = re.findall(rf"^{name}:=([^\n]+)$", text, re.M)
    if len(found) != 1:
        raise ValueError(f"Expected one {name} in {path}")
    return found[0].strip()


def package_identity(directory):
    makefile = directory / "Makefile"
    return {"version": assignment(makefile, "PKG_VERSION"),
            "release": assignment(makefile, "PKG_RELEASE")}


def receipt(packages):
    commit = subprocess.check_output(
        ["git", "-C", str(packages), "rev-parse", "HEAD"],
        text=True, timeout=TIMEOUT_SECONDS).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid upstream package commit")
    roots = [packages / name for name in ("miniupnpd", "luci-app-upnp")]
    files = sorted(path for root in roots for path in root.rglob("*") if path.is_file())
    hashes = {path.relative_to(packages).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in files}
    return {"status": "upstream-json-verified", "provider": "VIKINGYFY/packages",
            "provider_commit": commit, "packages": {root.name: package_identity(root) for root in roots},
            "daemon_source_commit": assignment(roots[0] / "Makefile", "PKG_SOURCE_VERSION"),
            "source_sha256": hashes,
            "checks": ["native-ucode-json-status-and-leases", "shell-config-and-lease-migration"],
            "scope": "Offline regression; no router, forwarding or public reachability test"}


def verify(options):
    source = (options.packages / RPC_PATH).read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="upnp-json-") as temporary:
        harness = Path(temporary) / "reader.uc"
        harness.write_text(harness_source(source), encoding="utf-8", newline="\n")
        subprocess.run([options.ucode, "-L", options.library,
                        str(ROOT / "tests/test_upnp_json.uc"), str(harness)],
                       check=True, timeout=TIMEOUT_SECONDS)
    migration = options.packages / "miniupnpd/files/miniupnpd.defaults.migration"
    subprocess.run(["bash", str(ROOT / "tests/test_upnp_migration.sh"), str(migration)],
                   check=True, timeout=TIMEOUT_SECONDS)
    return receipt(options.packages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", type=Path)
    parser.add_argument("--ucode", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    options = parser.parse_args()
    options.receipt.unlink(missing_ok=True)
    result = verify(options)
    options.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"UPnP pair verified: {result['provider_commit']}")


if __name__ == "__main__":
    main()
