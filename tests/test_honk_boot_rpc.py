"""Run the boot-only RPC with router JSON, UCI, init and lock I/O isolated."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

SOURCE = Path(os.environ["HONK_SOURCE_DIR"])
RPC_PATH = "luci-app-honk/root/usr/libexec/rpcd/honk"
IO = r'''
json_load() { [ "$JSON_OK" = 1 ]; }
json_get_var() { printf -v "$1" '%s' "$REQUESTED"; }
json_get_type() { printf -v "$1" '%s' "$KIND"; }
emit_result() { echo "result:$*"; }
honk_lock_acquire() { [ "$LOCK_OK" = 1 ]; }
honk_lock_release() { :; }
uci() {
    case "$*" in
        '-q get honk.main.boot_enabled') echo "$OLD" ;;
        'set honk.main.boot_enabled='*) echo "uci:$*" ;;
        'commit honk')
            echo "uci:$*"
            commits=$((commits + 1))
            [ "$FAIL" != all ] && { [ "$FAIL" != commit ] || [ "$commits" -gt 1 ]; } ;;
        *) echo "UNEXPECTED:$*"; return 1 ;;
    esac
}
service_honk() {
    echo "service:$*"
    links=$((links + 1))
    case "$1" in enable|disable) ;; *) echo UNEXPECTED; return 1 ;; esac
    [ "$FAIL" != link ] || [ "$links" -gt 1 ]
}
'''


def invoke(journal=None, **overrides):
    env = {**os.environ, "JSON_OK": "1", "REQUESTED": "1", "KIND": "boolean", "OLD": "0",
           "LOCK_OK": "1", "FAIL": "none", **overrides}
    text = (SOURCE / RPC_PATH).read_text(encoding="utf-8")
    functions = [re.search(rf"^{name}\(\) \{{\n.*?^\}}", text, re.M | re.S).group(0)
                 for name in ("store_boot_preference", "boot_settings")]
    code = IO + "\n" + "\n".join(functions).replace("/etc/init.d/honk", "service_honk")
    if journal:
        code = code.replace(f"/etc/.honk-{journal}/journal", "/dev/null")
    return subprocess.run(["bash", "-c", code + "\nboot_settings"], env=env,
                          input="{}", capture_output=True, text=True, timeout=10)


class HonkBootRpcTests(unittest.TestCase):
    def test_unfinished_maintenance_and_update_refuse_writes(self):
        for journal in ("maintenance", "update"):
            result = invoke(journal=journal)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), f"result:false {journal}_recovery_required")

    def test_only_boot_preference_and_startup_link_change(self):
        for value, command in (("0", "disable"), ("1", "enable")):
            result = invoke(REQUESTED=value)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [
                f"uci:set honk.main.boot_enabled={value}", "uci:commit honk",
                f"service:{command}", "result:true settings_saved"])

    def test_invalid_request_and_lock_failure_do_not_write(self):
        for settings, error in (({"JSON_OK": "0"}, "invalid_request"),
                                ({"KIND": "string"}, "invalid_boolean_settings"),
                                ({"REQUESTED": "9"}, "invalid_boolean_settings"),
                                ({"LOCK_OK": "0"}, "operation_in_progress")):
            result = invoke(**settings)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), f"result:false {error}")

    def test_failed_commit_or_link_restores_previous_preference(self):
        for failure in ("commit", "link"):
            result = invoke(FAIL=failure)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uci:set honk.main.boot_enabled=0", result.stdout)
            self.assertIn("service:disable", result.stdout)
            self.assertTrue(result.stdout.endswith("result:false boot_update_failed_rolled_back\n"))

    def test_failed_rollback_is_visible(self):
        result = invoke(FAIL="all")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("result:false boot_update_and_rollback_failed", result.stdout)

    def test_rpc_is_registered_and_write_only(self):
        acl_path = SOURCE / "luci-app-honk/root/usr/share/rpcd/acl.d/luci-app-honk.json"
        acl = json.loads(acl_path.read_text(encoding="utf-8"))["luci-app-honk"]
        self.assertIn("boot_settings", acl["write"]["ubus"]["honk"])
        self.assertNotIn("boot_settings", acl["read"]["ubus"]["honk"])
        text = (SOURCE / RPC_PATH).read_text(encoding="utf-8")
        self.assertIn('"boot_settings":{"boot_enabled":"Boolean"}', text)
        self.assertRegex(text, r"boot_settings\)\s+boot_settings")


if __name__ == "__main__":
    unittest.main()
