"""Recognize the reviewed upstream fixes, not an assumed version number."""
import re

SOURCE_FILES = ("miniupnpd.c", "netfilter_nft/nftnlrdr_misc.c",
                "netfilter_nft/nftnlrdr_misc.h")


def code(path):
    text = path.read_text(encoding="utf-8")
    # Ignore comments and quoted literals before inspecting balanced C bodies.
    pattern = r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27'
    return re.sub(pattern, " ", text, flags=re.S)


def function(text, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{", text)
    if not match:
        raise ValueError(f"Unrecognized upstream source: missing function {name}")
    depth = 1
    for end in range(match.end(), len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            return re.sub(r"\s+", "", text[match.end():end])
    raise ValueError(f"Unbalanced function {name}")


def private_wan_fixed(directory):
    body = function(code(directory / SOURCE_FILES[0]), "update_disable_port_forwarding")
    condition = "elseif(disable_port_forwarding&&(!reserved||GETFLAG(ALLOWPRIVATEIPV4MASK))){"
    return bool(re.search(re.escape(condition) + r"[^{}]*disable_port_forwarding=0;", body))


def parser_refactored(directory):
    body = function(code(directory / SOURCE_FILES[1]), "parse_rule_meta")
    return "caseNFT_META_OIF:set_reg(r,dreg,RULE_REG_IIF,0);break;" in body


def nft_family_fixed(directory):
    text = code(directory / SOURCE_FILES[1])
    if not re.search(r"\bexpr_add_nfproto\s*\([^;{}]*\)\s*\{", text):
        return False
    helper = function(text, "expr_add_nfproto")
    required = ("uint8_tfamily=(uint8_t)nftnl_rule_get_u32(r,NFTNL_RULE_FAMILY);",
                "if(family!=NFPROTO_INET)return;",
                "expr_add_meta(r,NFT_META_NFPROTO,NFT_REG_1);",
                "expr_add_cmp(r,NFT_REG_1,NFT_CMP_EQ,&nfproto,sizeof(uint8_t));")
    if not all(fragment in helper for fragment in required):
        return False
    for name in ("snat", "dnat", "filter", "filter6"):
        body = function(text, "rule_set_" + name)
        family = "NFPROTO_IPV6" if name == "filter6" else "NFPROTO_IPV4"
        call = f"expr_add_nfproto(r,{family});"
        if call not in body or body.index(call) > body.index("expr_add_payload("):
            return False
    meta = function(text, "parse_rule_meta")
    cmp = function(text, "parse_rule_cmp")
    return ("caseNFT_META_NFPROTO:set_reg(r,dreg,RULE_REG_PROTO,0);break;" in meta
            and "caseRULE_REG_PROTO:break;" in cmp
            and "RULE_REG_PROTO," in code(directory / SOURCE_FILES[2]))


def verify(directory):
    if not private_wan_fixed(directory):
        raise ValueError("Private WAN recovery fix is missing or unrecognized")
    if not nft_family_fixed(directory):
        raise ValueError("nftables family fix is incomplete or unrecognized")
