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

    def test_speedtest_obsolete_python_dependencies_are_removed_without_losing_modules(self):
        recipe = ('LUCI_DEPENDS:=+python3-light +python3-email +python3-pkg-resources '
                  '+python3-urllib +python3-xml +python3-openssl +ookla-speedtest\n')
        provider = ('$(eval $(call Py3BasePackage,python3-urllib, \\\n'
                    '/usr/lib/python$(PYTHON3_VERSION)/email \\\n))\n')
        result = addons.speedtest_python_dependencies(recipe, provider, 'import urllib.request\n')
        self.assertNotIn('+python3-email', result)
        self.assertNotIn('+python3-pkg-resources', result)
        for package in ('python3-light', 'python3-urllib', 'python3-xml', 'python3-openssl', 'ookla-speedtest'):
            self.assertIn('+' + package, result)
        self.assertEqual(addons.speedtest_python_dependencies(result, provider, ''), result)

    def test_speedtest_missing_email_provider_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, 'email'):
            addons.speedtest_python_dependencies('LUCI_DEPENDS:=+python3-email +python3-urllib\n', '', '')

    def test_speedtest_real_pkg_resources_usage_requires_review(self):
        with self.assertRaisesRegex(ValueError, 'pkg_resources'):
            addons.speedtest_python_dependencies('LUCI_DEPENDS:=+python3-pkg-resources\n', '',
                                                 'from pkg_resources import get_distribution\n')

    def test_speedtest_email_requires_selected_urllib_provider(self):
        provider = ('$(eval $(call Py3BasePackage,python3-urllib, \\\n'
                    '/usr/lib/python$(PYTHON3_VERSION)/email \\\n))\n')
        with self.assertRaisesRegex(ValueError, 'email'):
            addons.speedtest_python_dependencies('LUCI_DEPENDS:=+python3-email\n', provider, '')

    def test_speedtest_already_fixed_upstream_remains_unchanged(self):
        recipe = 'LUCI_DEPENDS:=+python3-urllib +python3-email-extra\n'
        self.assertEqual(addons.speedtest_python_dependencies(recipe, '', ''), recipe)


if __name__ == '__main__':
    unittest.main()
