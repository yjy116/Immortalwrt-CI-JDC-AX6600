"""Validate the maintained packages' download contract without evaluating Make."""
import re

REPOSITORIES = {
    "daede": "https://github.com/kenzok8/openwrt-daede.git",
    "honk": "https://github.com/kenzok8/openwrt-honk.git",
}
ARCHITECTURES = ("aarch64", "x86_64", "armv7")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def assignment(text, name):
    values = re.findall(rf"^{re.escape(name)}([?:+]?=)([^\n]*)$", text, re.M)
    require(len(values) == 1, f"Expected one {name} assignment, found {len(values)}")
    operator, value = values[0]
    require(operator != "+=", f"Unsupported {name} append assignment")
    return value.strip()


def checked_hash(value):
    require(re.fullmatch(r"[a-f0-9]{64}", value), f"Invalid SHA-256: {value}")
    return value


def checked_commit(value):
    require(re.fullmatch(r"[a-f0-9]{40}", value), f"Invalid commit: {value}")
    return value


def pins_values(text):
    names = re.findall(r"^([A-Z][A-Z0-9_]+)=", text, re.M)
    values = {name: assignment(text, name) for name in names}
    for name, value in values.items():
        if name.endswith("_COMMIT") or name == "QUICGO_PERF_TIP":
            checked_commit(value)
    return values


def package_version(text):
    version = assignment(text, "PKG_VERSION")
    release = assignment(text, "PKG_RELEASE")
    require(re.fullmatch(r"[0-9][A-Za-z0-9._-]*", version), "Invalid package version")
    require(re.fullmatch(r"[0-9]+", release), "Invalid package release")
    return f"{version}-r{release}"


def source_asset(name, url, digest):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz", name), "Invalid archive name")
    return {"name": name, "url": f"{url.rstrip('/')}/{name}", "sha256": checked_hash(digest)}


def honk_core_assets(text, pins, base):
    require(assignment(text, "CORE_COMMIT") == pins["CORE_COMMIT"], "Honk core pin mismatch")
    require(assignment(text, "PKG_SOURCE") == "$(HONK_ASSET)", "Unknown Honk archive selector")
    require(assignment(text, "PKG_HASH") == "$(HONK_HASH)", "Unknown Honk hash selector")
    require(assignment(text, "PKG_SOURCE_URL").rstrip("/") == "$(HONK_SOURCE_URL)",
            "Unknown Honk source URL")
    result = {}
    for arch in ARCHITECTURES:
        name = assignment(text, "HONK_ASSET_" + arch.upper())
        name = name.replace("$(CORE_COMMIT)", pins["CORE_COMMIT"])
        require(name == f"honk-core-{pins['CORE_COMMIT']}-{arch}.tar.gz", "Core archive mismatch")
        result[arch] = source_asset(name, base, assignment(text, "HONK_HASH_" + arch.upper()))
    return result


def honk_metadata(core, ui, pins):
    checked_commit(pins["CORE_COMMIT"])
    checked_commit(pins["DOONA_COMMIT"])
    tag = assignment(core, "HONK_SOURCE_TAG")
    require(re.fullmatch(r"source-[0-9]+", tag), "Expected immutable source run tag")
    require(assignment(ui, "HONK_SOURCE_TAG") == tag, "Honk/Doona source tag mismatch")
    base = REPOSITORIES["honk"].removesuffix(".git") + "/releases/download/" + tag
    for text, name in ((core, "HONK_SOURCE_URL"), (ui, "PKG_SOURCE_URL")):
        url = assignment(text, name).replace("$(HONK_SOURCE_TAG)", tag).rstrip("/")
        require(url == base, "Source URL does not match immutable tag")
    assets = honk_core_assets(core, pins, base)
    name = assignment(ui, "PKG_SOURCE")
    require(name == pins["DOONA_ARCHIVE"], "Doona archive pin mismatch")
    assets["doona"] = source_asset(name, base, assignment(ui, "PKG_HASH"))
    return {"source_tag": tag, "assets": assets, "versions": {
        "honk": package_version(core), "luci-app-honk": package_version(ui)}}


def daede_metadata(makefiles, pins):
    for key in ("CORE_COMMIT", "CORE_UPSTREAM_COMMIT", "DAED_COMMIT", "WING_COMMIT",
                "OUTBOUND_COMMIT", "QUICGO_BASE_COMMIT", "QUICGO_PERF_TIP"):
        checked_commit(pins.get(key, ""))
    assets = {}
    for package in ("dae", "daed"):
        text = makefiles[package]
        require(assignment(text, "PKG_VERSION") == pins[package.upper() + "_VERSION"],
                f"{package} source version does not match pins")
        url = assignment(text, "PKG_SOURCE_URL").rstrip("/")
        expected = REPOSITORIES["daede"].removesuffix(".git") + f"/releases/download/{package}-src"
        require(url == expected, f"Unknown {package} source provider")
        assets[package] = source_asset(assignment(text, "PKG_SOURCE"), url,
                                       assignment(text, "PKG_HASH"))
    return {"assets": assets,
            "versions": {name: package_version(text) for name, text in makefiles.items()}}


def verify_provenance(provenance, pins):
    core = provenance.get("core", {})
    require(core.get("commit") == pins["CORE_COMMIT"], "Provenance core commit mismatch")
    require(core.get("repository") == pins["CORE_REPOSITORY"], "Provenance repository mismatch")
    require(set(core.get("architectures", [])) == set(ARCHITECTURES), "Provenance architecture mismatch")
