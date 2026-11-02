#!/usr/bin/env python3
"""Keep newly bundled optional tools inactive and compatible with existing apps."""

import argparse
from pathlib import Path
import re

IPERF_CHOICE = '$(if $(find_package iperf3-ssl),+iperf3-ssl,+iperf3)'


def monitor_defaults(text):
    pattern = r"(^config global 'global'\s*\n)(.*?)(?=^config |\Z)"
    section = re.search(pattern, text, re.M | re.S)
    if not section:
        raise ValueError('Review changed netmonitor global section')
    body, count = re.subn(r"^(\s*option enabled )'[01]'", r"\1'0'", section[2], flags=re.M)
    if count != 1:
        raise ValueError('Review changed netmonitor enable option')
    return text[:section.start()] + section[1] + body + text[section.end():]


def natmap_defaults(text):
    sections = re.split(r'(?=^config )', text, flags=re.M)
    actual = [part for part in sections if part.startswith('config ')]
    if len(actual) < 2 or not actual[0].startswith('config global\n'):
        raise ValueError('Review changed natmap default sections')
    template = actual[1]
    if not template.startswith('config natmap\n'):
        raise ValueError('Review changed natmap example layout')
    for section in (actual[0], template):
        options = re.findall(r"^\s*option enable '([01])'", section, re.M)
        if options != ['0']:
            raise ValueError('Review changed natmap default enable state')
    return actual[0].rstrip() + '\n\n' + template.rstrip() + '\n'


def speedtest_dependencies(text):
    if IPERF_CHOICE in text:
        return text.replace(IPERF_CHOICE, '+iperf3')
    if re.search(r'\+iperf3(?=\s|$)', text) and 'iperf3-ssl' not in text:
        return text
    raise ValueError('Review changed netspeedtest iperf3 dependency')


def apply(root):
    changes = (
        ('luci-app-netmonitor/root/etc/config/netmonitor', monitor_defaults),
        ('openwrt-natmapt/files/natmap.config', natmap_defaults),
        ('netspeedtest/luci-app-netspeedtest/Makefile', speedtest_dependencies),
    )
    # Validate every source before writing any of the adaptations.
    results = [(root / path, adapt((root / path).read_text(encoding='utf-8')))
               for path, adapt in changes]
    for path, text in results:
        path.write_text(text, encoding='utf-8', newline='\n')
        print(f'Optional addon adaptation: {path.relative_to(root)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package_root', type=Path)
    apply(parser.parse_args().package_root)
