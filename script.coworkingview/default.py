import os
import sys

import xbmcaddon
import xbmcvfs

_addon = xbmcaddon.Addon()
_root = xbmcvfs.translatePath(_addon.getAddonInfo("path"))
if isinstance(_root, bytes):
    _root = _root.decode("utf-8")
_lib = os.path.join(_root, "resources", "lib")
if _lib not in sys.path:
    sys.path.append(_lib)

import gui

gui.run()
