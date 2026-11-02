import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'Scripts/netspeedtest_check.py'
spec = importlib.util.spec_from_file_location('netspeedtest_check', SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class NetspeedtestCheckTests(unittest.TestCase):
    def test_current_failure_is_reported_before_rootfs_install(self):
        recipe = 'LUCI_DEPENDS:=+python3-urllib +python3-email +python3-pkg-resources\n'
        metadata = 'Package: python3-urllib\nVersion: 3.14.7-r1\n'
        config = 'CONFIG_PACKAGE_python3-urllib=y\n'
        with self.assertRaisesRegex(ValueError, 'python3-email.*python3-pkg-resources'):
            check.verify(recipe, metadata, config)

    def test_available_and_selected_dependencies_pass(self):
        recipe = 'LUCI_DEPENDS:=+python3-light \\\n  +python3-urllib +iperf3\nLUCI_PKGARCH:=all\n'
        names = ('python3-light', 'python3-urllib', 'iperf3')
        metadata = ''.join(f'Package: {name}\nVersion: 1\n\n' for name in names)
        config = ''.join(f'CONFIG_PACKAGE_{name}=y\n' for name in names)
        self.assertEqual(check.verify(recipe, metadata, config), names)

    def test_available_but_not_built_into_image_fails(self):
        with self.assertRaisesRegex(ValueError, 'not selected.*python3-urllib'):
            check.verify('LUCI_DEPENDS:=+python3-urllib\n', 'Package: python3-urllib\n',
                         'CONFIG_PACKAGE_python3-urllib=m\n')

    def test_changed_dependency_expression_requires_review(self):
        with self.assertRaisesRegex(ValueError, 'expression'):
            check.verify('LUCI_DEPENDS:=+FOO:python3-urllib\n', '', '')

    def test_missing_dependency_declaration_fails(self):
        with self.assertRaisesRegex(ValueError, 'LUCI_DEPENDS'):
            check.verify('LUCI_TITLE:=Speedtest\n', '', '')

    def test_appended_dependencies_cannot_be_silently_ignored(self):
        recipe = 'LUCI_DEPENDS:=+iperf3\nLUCI_DEPENDS+=+missing-package\n'
        with self.assertRaisesRegex(ValueError, 'LUCI_DEPENDS'):
            check.verify(recipe, 'Package: iperf3\n', 'CONFIG_PACKAGE_iperf3=y\n')

    def test_reassigned_dependencies_cannot_be_silently_ignored(self):
        recipe = 'LUCI_DEPENDS:=+iperf3\nLUCI_DEPENDS:=+missing-package\n'
        with self.assertRaisesRegex(ValueError, 'LUCI_DEPENDS'):
            check.verify(recipe, 'Package: iperf3\n', 'CONFIG_PACKAGE_iperf3=y\n')


if __name__ == '__main__':
    unittest.main()
