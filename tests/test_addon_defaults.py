import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'Scripts/addon_defaults.py'
spec = importlib.util.spec_from_file_location('addon_defaults', SCRIPT)
addons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addons)


class AddonDefaultsTests(unittest.TestCase):
    def test_monitor_disables_global_but_preserves_targets(self):
        source = ("config global 'global'\n\toption enabled '1'\n"
                  "config target 'dns'\n\toption enabled '1'\n")
        result = addons.monitor_defaults(source)
        self.assertIn("config global 'global'\n\toption enabled '0'", result)
        self.assertIn("config target 'dns'\n\toption enabled '1'", result)
        self.assertEqual(addons.monitor_defaults(result), result)

    def test_monitor_rejects_unknown_layout(self):
        with self.assertRaisesRegex(ValueError, 'netmonitor'):
            addons.monitor_defaults("config settings 'main'\n")

    def test_natmap_drops_example_profiles_but_keeps_disabled_template(self):
        source = ("config global\n\toption enable '0'\n"
                  "config natmap\n\toption enable '0'\n\toption forward '0'\n"
                  "config natmap\n\toption enable '1'\n\toption comment 'example'\n")
        result = addons.natmap_defaults(source)
        self.assertEqual(result.count('config natmap'), 1)
        self.assertNotIn('example', result)
        self.assertEqual(addons.natmap_defaults(result), result)

    def test_natmap_rejects_changed_initial_state(self):
        source = "config global\n\toption enable '1'\nconfig natmap\n\toption enable '0'\n"
        with self.assertRaisesRegex(ValueError, 'natmap'):
            addons.natmap_defaults(source)

    def test_speedtest_uses_existing_iperf_without_conflicting_ssl_variant(self):
        source = 'LUCI_DEPENDS:=+jq ' + addons.IPERF_CHOICE + '\n'
        result = addons.speedtest_dependencies(source)
        self.assertEqual(result, 'LUCI_DEPENDS:=+jq +iperf3\n')
        self.assertEqual(addons.speedtest_dependencies(result), result)

    def test_speedtest_rejects_unknown_dependency(self):
        with self.assertRaisesRegex(ValueError, 'iperf3'):
            addons.speedtest_dependencies('LUCI_DEPENDS:=+iperf3-ssl\n')


if __name__ == '__main__':
    unittest.main()
