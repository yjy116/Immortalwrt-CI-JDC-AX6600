"""Compile and execute the real upstream C functions with isolated I/O doubles."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(os.environ["MINIUPNPD_TEST_DIR"])
TIMEOUT = 15

WAN_ENVIRONMENT = r"""
#include <stddef.h>
#define INET_ADDRSTRLEN 16
#define LOG_INFO 1
#define LOG_WARNING 2
#define LOG_ERR 3
#define GETIFADDR_DEVICE_NOT_CONFIGURED -1
#define GETIFADDR_IF_DOWN -2
#define GETIFADDR_NO_ADDRESS -3
#define ALLOWPRIVATEIPV4MASK 1
#define GETFLAG(flag) allow_private
#define syslog(...) ((void)0)
struct in_addr { unsigned int value; };
static int link_status, reserved_ip, allow_private, disable_port_forwarding;
static const char *ext_if_name = "pppoe-wan";
static int getifaddr(const char *iface, char *ip, int size, struct in_addr *addr, void *mask)
{ (void)iface; (void)ip; (void)size; (void)addr; (void)mask; return link_status; }
static int addr_is_reserved(struct in_addr *addr) { (void)addr; return reserved_ip; }
"""
WAN_CASES = r"""
int main(void) {
    static const int cases[][5] = {
        {-2, 1, 1, 0, 1}, {0, 1, 1, 1, 0}, {0, 1, 0, 1, 1},
        {0, 0, 0, 1, 0}, {0, 1, 0, 0, 1}, {0, 1, 1, 0, 0}
    };
    unsigned int i;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        link_status = cases[i][0]; reserved_ip = cases[i][1];
        allow_private = cases[i][2]; disable_port_forwarding = cases[i][3];
        update_disable_port_forwarding();
        if (disable_port_forwarding != cases[i][4]) return (int)i + 1;
    }
    return 0;
}
"""
NFT_ENVIRONMENT = r"""
#include <stdint.h>
#include <stddef.h>
#define NFTNL_RULE_FAMILY 5
#define NFT_META_NFPROTO 15
#define NFT_REG_1 1
#define NFT_CMP_EQ 0
#define NFPROTO_INET 1
#define NFPROTO_IPV4 2
#define NFPROTO_IPV6 10
struct nftnl_rule { uint8_t family; };
static int calls, invalid;
static uint8_t compared;
static uint32_t nftnl_rule_get_u32(struct nftnl_rule *r, int key)
{ if (key != NFTNL_RULE_FAMILY) invalid = 1; return r->family; }
static void expr_add_meta(struct nftnl_rule *r, uint32_t key, uint32_t reg)
{ (void)r; ++calls; if (key != NFT_META_NFPROTO || reg != NFT_REG_1) invalid = 1; }
static void expr_add_cmp(struct nftnl_rule *r, uint32_t reg, int op, const void *data, size_t size)
{ (void)r; ++calls; compared = *(const uint8_t *)data;
  if (reg != NFT_REG_1 || op != NFT_CMP_EQ || size != 1) invalid = 1; }
"""
NFT_CASES = r"""
int main(void) {
    struct nftnl_rule rule = {NFPROTO_IPV4};
    expr_add_nfproto(&rule, NFPROTO_IPV4);
    if (calls != 0) return 1;
    rule.family = NFPROTO_IPV6;
    expr_add_nfproto(&rule, NFPROTO_IPV6);
    if (calls != 0) return 2;
    rule.family = NFPROTO_INET;
    expr_add_nfproto(&rule, NFPROTO_IPV4);
    if (calls != 2 || invalid || compared != NFPROTO_IPV4) return 3;
    expr_add_nfproto(&rule, NFPROTO_IPV6);
    if (calls != 4 || invalid || compared != NFPROTO_IPV6) return 4;
    return 0;
}
"""


def extract_function(path, name):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"static void\s+" + name + r"\([^;{]*\)\s*\{.*?^\}", text, re.M | re.S)
    if not match:
        raise AssertionError(f"Missing upstream function {name}")
    return match.group(0)


def execute_c(directory, source):
    path = directory / "check.c"
    executable = directory / ("check.exe" if os.name == "nt" else "check")
    path.write_text(source, encoding="utf-8")
    if os.name == "nt":
        command = ["cl", "/nologo", "/WX", str(path), f"/Fe:{executable}"]
    else:
        command = ["cc", "-Wall", "-Wextra", "-Werror", str(path), "-o", str(executable)]
    subprocess.run(command, cwd=directory, check=True, capture_output=True, timeout=TIMEOUT)
    return subprocess.run([str(executable)], timeout=TIMEOUT).returncode


class UpstreamRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "source"
        shutil.copytree(FIXTURES / "miniupnpd-2.3.11", self.source)

    def apply_fix(self):
        result = subprocess.run([sys.executable, str(ROOT / "Scripts/miniupnpd/backport.py"),
                                 str(self.source)], capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_private_wan_function_red_then_green(self):
        path = self.source / "miniupnpd.c"
        before = extract_function(path, "update_disable_port_forwarding")
        self.assertEqual(execute_c(self.directory, WAN_ENVIRONMENT + before + WAN_CASES), 2)
        self.apply_fix()
        after = extract_function(path, "update_disable_port_forwarding")
        self.assertEqual(execute_c(self.directory, WAN_ENVIRONMENT + after + WAN_CASES), 0)

    def test_real_nfproto_helper_only_emits_correct_inet_matches(self):
        self.apply_fix()
        helper = extract_function(self.source / "netfilter_nft/nftnlrdr_misc.c", "expr_add_nfproto")
        self.assertEqual(execute_c(self.directory, NFT_ENVIRONMENT + helper + NFT_CASES), 0)


if __name__ == "__main__":
    unittest.main()
