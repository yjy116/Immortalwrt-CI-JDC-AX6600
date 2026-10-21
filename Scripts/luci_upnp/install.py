"""Repair only the known LuCI nft reader; retain upstream fixes that pass checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 60
OLD_PATTERN = r'/^\t\tiif ".+" @nh,72,8 (0x6|0x11) th dport ([0-9]+) dnat ip to ([0-9.]+):([0-9]+)/'
PR9148_PATTERN = r'/^\s*iif ".+" @nh,72,8 (0x6|0x11) th dport ([0-9]+) .*dnat ip to ([0-9.]+):([0-9]+)/'
NEW_PATTERN = (r'/^\s*iif "[^"]+" (@nh,72,8 |ip protocol )(0x6|0x11|tcp|udp) '
               r'(th|tcp|udp) dport ([0-9]+)( counter packets [0-9]+ bytes [0-9]+)? '
               r'dnat ip to ([0-9.]+):([0-9]+)(\s|$)/')
REFERENCES = {
    "counter_proposal": "https://github.com/openwrt/luci/pull/9148",
    "counter_commit": "9f52246f6fc40420be8ee962502ac967f0f3ec26",
    "decoded_protocol_proposal": "https://github.com/openwrt/luci/pull/8415",
    "decoded_protocol_head": "7050081007b9111df1e3bf7d0f4b5c66a88beff3",
    "status_at_review": "Both proposals unmerged on 2026-10-21; scoped adaptation",
}


def validate(path):
    return subprocess.run(["node", str(HERE / "check_parser.cjs"), str(path)],
                          capture_output=True, text=True, timeout=TIMEOUT_SECONDS)


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("Unknown LuCI reader structure; review upstream instead of overwriting")
    return text.replace(before, after, 1)


def repair_source(text):
    start = text.index("\t\t\tif (nft) {")
    end = text.index("\n\t\t\treturn ubus.defer(", start)
    block = text[start:end]
    patterns = [pattern for pattern in (OLD_PATTERN, PR9148_PATTERN) if pattern in block]
    if len(patterns) != 1:
        raise ValueError("Unrecognized LuCI nft parser; automatic repair refused")
    replacements = (
        (patterns[0], NEW_PATTERN),
        ("(m[1] == '0x6')", "(m[2] == '0x6' || m[2] == 'tcp')"),
        ("extport: +m[2]", "extport: +m[4]"),
        ("intaddr: arrtoip(iptoarr(m[3]))", "intaddr: arrtoip(iptoarr(m[6]))"),
        ("intport: +m[4]", "intport: +m[7]"),
    )
    for before, after in replacements:
        block = replace_once(block, before, after)
    return text[:start] + block + text[end:]


def install(path):
    original = path.read_bytes()
    check = validate(path)
    status = "already-compatible"
    if check.returncode:
        updated = repair_source(original.decode("utf-8")).encode("utf-8")
        with tempfile.TemporaryDirectory(prefix="luci-upnp-check-") as directory:
            candidate = Path(directory) / "luci.upnp"
            candidate.write_bytes(updated)
            verified = validate(candidate)
            if verified.returncode:
                raise ValueError("Repaired LuCI parser failed regression checks:\n" + verified.stderr)
        if path.read_bytes() != original:
            raise ValueError("LuCI source changed during verification")
        path.write_bytes(updated)
        status = "applied"
    return {"status": status, "references": REFERENCES,
            "input_sha256": hashlib.sha256(original).hexdigest(),
            "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scope": "nft get_status parsing only; no UCI, services or firewall changes"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = install(args.source)
    encoded = json.dumps(receipt, indent=2) + "\n"
    if args.receipt:
        args.receipt.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
