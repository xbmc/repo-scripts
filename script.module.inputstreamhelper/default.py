# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper API script entry point '''

from __future__ import absolute_import, division, unicode_literals
import os
import sys
import xbmc
import xbmcaddon


def to_unicode(text, encoding='utf-8'):
    ''' Force text to unicode '''
    return text.decode(encoding) if isinstance(text, bytes) else text


sys.path.append(os.path.join(to_unicode(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))), 'lib'))
from inputstreamhelper.api import run  # noqa: E402

run(sys.argv)
