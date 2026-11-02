#!/usr/bin/env python3
"""Verify normalized netspeedtest dependencies before the firmware build."""

import argparse
from pathlib import Path
import re


def dependencies(recipe):
    declarations = re.findall(r'^\s*LUCI_DEPENDS\s*([:+?]?=)([^\n]*)',
                              recipe.replace('\\\n', ' '), re.M)
    if len(declarations) != 1 or declarations[0][0] != ':=':
        raise ValueError('Review netspeedtest LUCI_DEPENDS declarations: expected one := assignment')
    tokens = declarations[0][1].split()
    if not tokens or not all(re.fullmatch(r'\+[A-Za-z0-9_.-]+', token) for token in tokens):
        raise ValueError('Review changed netspeedtest dependency expression')
    return tuple(token[1:] for token in tokens)


def verify(recipe, metadata, config):
    required = dependencies(recipe)
    available = set(re.findall(r'^Package: (\S+)$', metadata, re.M))
    missing = sorted(set(required) - available)
    if missing:
        raise ValueError('netspeedtest dependencies absent from package metadata: ' + ', '.join(missing))
    selected = set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=y$', config, re.M))
    missing = sorted(set(required) - selected)
    if missing:
        raise ValueError('netspeedtest dependencies not selected in image: ' + ', '.join(missing))
    return required


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wrt_root', type=Path)
    root = parser.parse_args().wrt_root
    recipe = root / 'package/netspeedtest/luci-app-netspeedtest/Makefile'
    names = verify(recipe.read_text(encoding='utf-8'),
                   (root / 'tmp/.packageinfo').read_text(encoding='utf-8'),
                   (root / '.config').read_text(encoding='utf-8'))
    print('netspeedtest dependencies available and selected: ' + ', '.join(names))


if __name__ == '__main__':
    main()
