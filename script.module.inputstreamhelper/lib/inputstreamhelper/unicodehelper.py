# -*- coding: utf-8 -*-
''' Implements Unicode Helper functions '''
from __future__ import absolute_import, division, unicode_literals


def to_unicode(text, encoding='utf-8'):
    ''' Force text to unicode '''
    return text.decode(encoding) if isinstance(text, bytes) else text


def from_unicode(text, encoding='utf-8'):
    ''' Force unicode to text '''
    import sys
    if sys.version_info.major == 2 and isinstance(text, unicode):  # noqa: F821; pylint: disable=undefined-variable
        return text.encode(encoding)
    return text
