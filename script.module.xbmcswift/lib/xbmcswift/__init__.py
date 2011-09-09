# Mock up the xbmc modules if we are running on the command line.
# TODO: Only mock the modules if we are running on the command line,
# we don't want to mask any real import errors when running in XBMC.
try:
    import xbmc
    import xbmcgui
    import xbmcplugin
    import xbmcaddon
    #import xbmcvfs
except ImportError:
    from mock import MockClass
    from mockxbmc.xbmc import translatePath
    xbmc = MockClass()
    xbmc.translatePath = translatePath

    xbmcgui = MockClass()

    xbmcplugin = MockClass()

    xbmcaddon = MockClass()
    from mockxbmc.xbmcaddon import Addon
    xbmcaddon.Addon = Addon
    xbmcvfs = MockClass()

from common import (urlparse, pickle_dict, unpickle_dict, clean_dict,
    download_page, parse_qs, parse_url_qs, unhex)
from plugin import Plugin
from module import Module 
from urls import (AmbiguousUrlException,
    NotFoundException, UrlRule)
