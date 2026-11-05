"""Preserve upstream RPC additions while registering the local boot preference."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Scripts"))
SPEC = importlib.util.spec_from_file_location("honk_rpc", ROOT / "Scripts/honk_rpc.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source(methods):
    return ('#!/bin/sh\ncase "$1" in\nlist)\n\t\techo \''
            + json.dumps(methods, separators=(",", ":"))
            + "'\n\t\t;;\ncall)\n\tcase \"$2\" in\n"
            + "\tboot_settings)\n\t\tboot_settings\n\t\t;;\n\tesac\n\t;;\nesac\n")


def listed(text):
    result = subprocess.run(["bash", "-c", text, "honk", "list"],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class HonkRpcRegistryTests(unittest.TestCase):
    def test_old_and_new_upstream_methods_survive_actual_list_execution(self):
        base = {"status": {}, "settings": {"boot_enabled": "Boolean"}}
        for extra in ({}, {"config_detach": {"dry_run": "Boolean"}},
                      {"future_method": {"input": "String", "number": "Integer"}}):
            methods = {**base, **extra}
            result = MODULE.register_boot_method(source(methods))
            self.assertEqual(listed(result), {
                **methods, "boot_settings": {"boot_enabled": "Boolean"}})

    def test_existing_matching_registration_is_idempotent(self):
        text = source({"settings": {"boot_enabled": "Boolean"},
                       "boot_settings": {"boot_enabled": "Boolean"}})
        self.assertEqual(MODULE.register_boot_method(text), text)

    def test_json_escapes_remain_safe_in_shell_literal(self):
        text = source({"settings": {"boot_enabled": "Boolean"}, "escaped": {"field": "String"}})
        text = text.replace('"field"', '"field\\u0027s"')
        expected = listed(text)
        self.assertEqual(listed(MODULE.register_boot_method(text)), {
            **expected, "boot_settings": {"boot_enabled": "Boolean"}})

    def test_conflicting_upstream_boot_method_is_not_overwritten(self):
        text = source({"settings": {"boot_enabled": "Boolean"},
                       "boot_settings": {"enabled": "String"}})
        with self.assertRaisesRegex(ValueError, "boot_settings"):
            MODULE.register_boot_method(text)

    def test_invalid_or_ambiguous_registry_fails(self):
        valid = source({"settings": {"boot_enabled": "Boolean"}})
        cases = (valid.replace('echo \'' + '{', 'echo \'invalid{'), valid + valid,
                 valid.replace('"settings":', '"settings":{},"settings":'))
        for text in cases:
            with self.assertRaises(ValueError):
                MODULE.register_boot_method(text)

    def test_missing_handler_or_changed_settings_contract_fails(self):
        valid = source({"settings": {"boot_enabled": "Boolean"}})
        for text in (valid.replace("\tboot_settings)", "\tunrelated)"),
                     valid.replace('"Boolean"', '"String"')):
            with self.assertRaises(ValueError):
                MODULE.register_boot_method(text)


if __name__ == "__main__":
    unittest.main()
