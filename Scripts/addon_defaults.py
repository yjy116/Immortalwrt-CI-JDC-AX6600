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


def speedtest_python_dependencies(text, urllib_provider, speedtest_source):
    email = r'\+python3-email(?=\s|$)'
    resources = r'\+python3-pkg-resources(?=\s|$)'
    if re.search(email, text):
        provider = re.search(
            r'\$\(call Py3BasePackage,python3-urllib,(.*?)^\)\)',
            urllib_provider, re.M | re.S)
        if (not re.search(r'\+python3-urllib(?=\s|$)', text) or not provider
                or not re.search(r'^\s*/usr/lib/python\$\(PYTHON3_VERSION\)/email(?:\s|$)',
                                 provider[1], re.M)):
            raise ValueError('Review netspeedtest email module provider')
        text = re.sub(email, '', text)
    if re.search(resources, text):
        if 'pkg_resources' in speedtest_source:
            raise ValueError('Review netspeedtest pkg_resources runtime dependency')
        text = re.sub(resources, '', text)
    return text


def speedtest_recipe(root):
    package = root / 'netspeedtest/luci-app-netspeedtest'
    recipe = speedtest_dependencies((package / 'Makefile').read_text(encoding='utf-8'))
    provider = root.parent / 'feeds/packages/lang/python/python3/files/python3-package-urllib.mk'
    urllib = provider.read_text(encoding='utf-8') if re.search(r'\+python3-email(?=\s|$)', recipe) else ''
    source = (package / 'root/usr/bin/speedtest').read_text(encoding='utf-8')
    return package / 'Makefile', speedtest_python_dependencies(recipe, urllib, source)


def apply(root):
    changes = (
        ('luci-app-netmonitor/root/etc/config/netmonitor', monitor_defaults),
        ('openwrt-natmapt/files/natmap.config', natmap_defaults),
    )
    # Validate every source before writing any of the adaptations.
    results = [(root / path, adapt((root / path).read_text(encoding='utf-8')))
               for path, adapt in changes]
    results.append(speedtest_recipe(root))
    for path, text in results:
        path.write_text(text, encoding='utf-8', newline='\n')
        print(f'Optional addon adaptation: {path.relative_to(root)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package_root', type=Path)
    apply(parser.parse_args().package_root)
