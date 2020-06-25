# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements Unicode Helper functions"""
from __future__ import absolute_import, division, unicode_literals


def to_unicode(text, encoding='utf-8', errors='strict'):
    """Force text to unicode"""
    if isinstance(text, bytes):
        return text.decode(encoding, errors)
    return text


def from_unicode(text, encoding='utf-8', errors='strict'):
    """Force unicode to text"""
    import sys
    if sys.version_info.major == 2 and isinstance(text, unicode):  # noqa: F821; pylint: disable=undefined-variable,useless-suppression
        return text.encode(encoding, errors)
    return text


def compat_path(path, encoding='utf-8', errors='strict'):
    """Convert unicode path to bytestring if needed"""
    import sys
    if (sys.version_info.major == 2 and isinstance(path, unicode)  # noqa: F821; pylint: disable=undefined-variable,useless-suppression
            and not sys.platform.startswith('win')):
        return path.encode(encoding, errors)
    return path
