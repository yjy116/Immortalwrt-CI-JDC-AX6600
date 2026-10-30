import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("owrt", ROOT / "Scripts/owrt.py")
owrt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owrt)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "target/linux/qualcommax"
        for name in ["ipq60xx", "image", "dts"]:
            (self.target / name).mkdir(parents=True)
        (self.root / "package/qca-nss/nss-wifi-drv").mkdir(parents=True)
        (self.root / "package/qca-nss/nss-wifi-drv/Makefile").write_text("PKG_NAME:=nss-wifi-drv\n")
        (self.target / "Makefile").write_text(
            "KERNEL_PATCHVER:=6.18\nDEFAULT_PACKAGES += kmod-ath11k kmod-nss-wifi-drv wpad-openssl\n")
        (self.target / "ipq60xx/target.mk").write_text(
            "DEFAULT_PACKAGES += ath11k-firmware-ipq6018-ddwrt\n")
        (self.target / "ipq60xx/config-default").write_text(
            "CONFIG_QCOM_80211AX_PPE=y\nCONFIG_QCOM_EDMA=y\n")
        (self.target / "dts/device.dts").write_text('#include "ipq6018.dtsi"\n')
        (self.target / "image/ipq60xx.mk").write_text(
            "define Device/jdcloud_re-cs-02\n  KERNEL_SIZE := 6144k\n"
            "  DEVICE_PACKAGES := ath11k-firmware-qcn9074-ddwrt ipq-wifi-jdcloud_re-cs-02 luci-app-athena-led\n"
            "endef\ndefine Device/unrelated\n  KERNEL_SIZE := 6144k\nendef\n")
        self.config = self.root / ".config"
        self.config.write_text(
            "CONFIG_TARGET_DEVICE_qualcommax_ipq60xx_DEVICE_jdcloud_re-cs-02=y\n"
            "CONFIG_PACKAGE_luci-app-homeproxy=y\nCONFIG_PACKAGE_luci-app-honk=y\n"
            "CONFIG_PACKAGE_kmod-qca-nss-crypto=y\nCONFIG_IPQ_MEM_PROFILE_512=y\n"
            "CONFIG_PACKAGE_sqm-scripts-nss=y\n")

    def test_wifi_replaces_only_legacy_platform_options(self):
        owrt.prepare(self.root, "IPQ60XX-WIFI")
        config = self.config.read_text()
        for package in ["luci-app-homeproxy", "luci-app-honk", "kmod-nss-wifi-drv", "sqm-scripts", "luci-app-sqm"]:
            self.assertIn(f"CONFIG_PACKAGE_{package}=y\n", config)
        self.assertIn("CONFIG_ATH11K_NSS_WIFI=y\n", config)
        self.assertNotIn("CONFIG_IPQ_MEM_PROFILE", config)
        self.assertNotIn("kmod-qca-nss-", config)
        self.assertNotIn("sqm-scripts-nss", config)
        self.assertIn("ath11k-firmware-ipq6018-ddwrt", (self.target / "ipq60xx/target.mk").read_text())

    def test_nowifi_keeps_nss_and_upstream_device_tree(self):
        owrt.prepare(self.root, "IPQ60XX-NOWIFI")
        self.assertIn("# CONFIG_ATH11K_NSS_WIFI is not set", self.config.read_text())
        self.assertNotIn("kmod-ath11k", (self.target / "Makefile").read_text())
        self.assertIn("kmod-nss-wifi-drv", (self.target / "Makefile").read_text())
        self.assertNotIn("ath11k-firmware-", (self.target / "ipq60xx/target.mk").read_text())
        self.assertIn("luci-app-athena-led", (self.target / "image/ipq60xx.mk").read_text())
        self.assertEqual('#include "ipq6018.dtsi"\n', (self.target / "dts/device.dts").read_text())
        self.assertTrue((self.root / "package/qca-nss/nss-wifi-drv/Makefile").is_file())

    def test_upstream_replacements_preserve_fullcone_usb_and_audio(self):
        self.config.write_text(self.config.read_text() +
            "CONFIG_PACKAGE_kmod-nft-fullcone=y\nCONFIG_PACKAGE_kmod-usb-xhci=y\n"
            "CONFIG_PACKAGE_kmod-usb3=y\nCONFIG_PACKAGE_kmod-sound-core=y\n"
            "CONFIG_PACKAGE_kmod-usb-audio=y\n# CONFIG_PACKAGE_audio-support is not set\n"
            "# CONFIG_PACKAGE_fullconenat-sonic is not set\n")
        original = self.config.read_text()
        for profile in ("IPQ60XX-WIFI", "IPQ60XX-NOWIFI"):
            with self.subTest(profile=profile):
                self.config.write_text(original)
                owrt.prepare(self.root, profile)
                config = self.config.read_text()
                for name in ("fullconenat-sonic", "luci-app-fullconenat-sonic", "kmod-usb-xhci-hcd", "kmod-usb3",
                             "kmod-sound-core", "kmod-usb-audio", "audio-support"):
                    self.assertIn(f"CONFIG_PACKAGE_{name}=y\n", config)
                self.assertNotIn("CONFIG_PACKAGE_kmod-nft-fullcone", config)
                self.assertNotIn("CONFIG_PACKAGE_kmod-usb-xhci=", config)
                owrt.prepare(self.root, profile)
                self.assertEqual(config, self.config.read_text())

    def test_audio_gate_is_added_for_either_requested_audio_package(self):
        original = self.config.read_text()
        for name in ("kmod-sound-core", "kmod-usb-audio"):
            with self.subTest(package=name):
                self.config.write_text(original + f"CONFIG_PACKAGE_{name}=y\n")
                owrt.prepare(self.root, "IPQ60XX-WIFI")
                self.assertIn("CONFIG_PACKAGE_audio-support=y\n", self.config.read_text())

    def test_unrequested_replacements_and_audio_are_not_enabled(self):
        self.config.write_text(self.config.read_text() +
            "# CONFIG_PACKAGE_kmod-nft-fullcone is not set\n"
            "# CONFIG_PACKAGE_kmod-usb-xhci is not set\n"
            "# CONFIG_PACKAGE_kmod-usb-audio is not set\n")
        owrt.prepare(self.root, "IPQ60XX-WIFI")
        for name in ("fullconenat-sonic", "luci-app-fullconenat-sonic", "kmod-usb-xhci-hcd", "audio-support"):
            self.assertNotIn(f"CONFIG_PACKAGE_{name}=y", self.config.read_text())

    def test_replacement_or_audio_gate_loss_still_fails_verification(self):
        self.config.write_text(self.config.read_text() +
            "CONFIG_PACKAGE_kmod-nft-fullcone=y\nCONFIG_PACKAGE_kmod-usb-xhci=y\n"
            "CONFIG_PACKAGE_kmod-usb-audio=y\n")
        owrt.prepare(self.root, "IPQ60XX-WIFI")
        requested = self.config.read_text()
        (self.root / ".config.requested").write_text(requested)
        for name in ("fullconenat-sonic", "luci-app-fullconenat-sonic", "kmod-usb-xhci-hcd", "audio-support"):
            with self.subTest(package=name):
                self.config.write_text(requested.replace(f"CONFIG_PACKAGE_{name}=y\n", ""))
                with self.assertRaisesRegex(ValueError, name):
                    owrt.verify_packages(self.root)

    def test_kernel_layout_is_scoped_and_idempotent(self):
        owrt.prepare(self.root, "IPQ60XX-WIFI")
        first = (self.target / "image/ipq60xx.mk").read_text()
        owrt.prepare(self.root, "IPQ60XX-WIFI")
        self.assertEqual(first, (self.target / "image/ipq60xx.mk").read_text())
        self.assertIn("KERNEL_SIZE := 12288k", first)
        self.assertIn("Device/unrelated\n  KERNEL_SIZE := 6144k", first)

    def test_unrecognized_kernel_layout_fails(self):
        image = self.target / "image/ipq60xx.mk"
        image.write_text(image.read_text().replace("6144k", "16384k"))
        with self.assertRaisesRegex(ValueError, "KERNEL_SIZE"):
            owrt.prepare(self.root, "IPQ60XX-WIFI")

    def test_missing_requested_package_is_an_error(self):
        (self.root / ".config.requested").write_text("CONFIG_PACKAGE_luci-app-homeproxy=y\nCONFIG_PACKAGE_honk=y\n")
        self.config.write_text("CONFIG_PACKAGE_honk=y\n")
        with self.assertRaisesRegex(ValueError, "luci-app-homeproxy"):
            owrt.verify_packages(self.root)

    def test_package_suboptions_are_verified_too(self):
        value = "CONFIG_PACKAGE_luci-app-daede_daed=y\n"
        (self.root / ".config.requested").write_text(value)
        self.config.write_text(value)
        owrt.verify_packages(self.root)
        self.config.write_text("")
        with self.assertRaisesRegex(ValueError, "daede_daed"):
            owrt.verify_packages(self.root)

    def test_wifi_and_btf_cannot_disappear(self):
        (self.root / ".config.requested").write_text(
            "CONFIG_ATH11K_NSS_WIFI=y\nCONFIG_KERNEL_DEBUG_INFO_BTF=y\n")
        self.config.write_text("")
        with self.assertRaisesRegex(ValueError, "ATH11K_NSS_WIFI"):
            owrt.verify_packages(self.root)

    def test_nowifi_rejects_indirect_wireless_dependency(self):
        (self.root / ".config.requested").write_text("# CONFIG_ATH11K_NSS_WIFI is not set\n")
        self.config.write_text("CONFIG_PACKAGE_kmod-ath11k=y\n")
        with self.assertRaisesRegex(ValueError, "NOWIFI"):
            owrt.verify_packages(self.root)

    def test_manifest_detects_missing_plugin_not_virtual_option(self):
        (self.root / ".config.requested").write_text(
            "CONFIG_PACKAGE_honk=y\nCONFIG_PACKAGE_luci-app-daede_daed=y\n")
        (self.root / "tmp").mkdir()
        (self.root / "tmp/.packageinfo").write_text("Package: honk\n")
        manifest = self.root / "test.manifest"
        manifest.write_text("honk - 2026.10.12-r1\n")
        owrt.verify_manifest(self.root, manifest)
        manifest.write_text("other - 1\n")
        with self.assertRaisesRegex(ValueError, "honk"):
            owrt.verify_manifest(self.root, manifest)


if __name__ == "__main__":
    unittest.main()
