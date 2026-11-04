"""Execute upstream boot and settings selection code with router I/O isolated."""
import os
from pathlib import Path
import re
import subprocess
import unittest

SOURCE = Path(os.environ["HONK_SOURCE_DIR"])


def shell(code):
    return subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=10)


class HonkBootTests(unittest.TestCase):
    def test_first_boot_preserves_preference_without_starting_service(self):
        text = (SOURCE / "honk/files/90-honk-boot").read_text(encoding="utf-8")
        # Replace only router I/O, executing the complete defaults script.
        text = text.replace(". /lib/functions.sh", ":")
        text = text.replace("/etc/init.d/honk", "service_honk")
        for setting, command in ((0, "disable"), (1, "enable")):
            script = ('config_load() { :; }; uci() { return 1; };\n'
                      'service_honk() { echo "$*"; };\n'
                      f'config_get_bool() {{ printf -v "$1" "%s" {setting}; }};\n')
            result = shell(script + text)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), command)

    def test_boot_requires_explicit_opt_in(self):
        text = (SOURCE / "honk/files/honk.init").read_text(encoding="utf-8")
        function = re.search(r"^boot\(\) \{\n.*?^\}", text, re.M | re.S).group(0)
        for setting in (0, 1):
            script = ('config_load() { :; }; start() { echo STARTED; };\n'
                      f'config_get_bool() {{ printf -v "$1" "%s" {setting}; }};\n')
            result = shell(script + function + "\nboot\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual("STARTED" in result.stdout, setting == 1)

    def test_saving_unrelated_settings_preserves_boot_preference(self):
        text = (SOURCE / "honk/files/control.sh").read_text(encoding="utf-8")
        block = re.search(r'\tcase "\$boot_enabled_type" in \'\'\|null\).*?\n\tnew_enabled=\$enabled',
                          text, re.S).group(0)
        for old, kind, requested, expected in ((0, "null", "", 0), (1, "null", "", 1),
                                                (1, "boolean", 0, 0), (0, "boolean", 1, 1)):
            script = (f"boot_enabled={old}; boot_enabled_type={kind}; new_boot_enabled={requested}\n"
                      + block + '\nprintf "%s" "$new_boot_enabled"\n')
            result = shell(script)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, str(expected))


if __name__ == "__main__":
    unittest.main()
