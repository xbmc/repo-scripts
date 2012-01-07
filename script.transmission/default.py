# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

import os
import sys
import xbmc
import xbmcaddon

__scriptname__ = "Transmission-XBMC"
__author__ = "Correl Roush <correl@gmail.com>"
__url__ = "http://github.com/correl/Transmission-XBMC"
__svn_url__ = ""
__credits__ = ""
__version__ = "0.5.2"
__XBMC_Revision__ = "30377"

__settings__ = xbmcaddon.Addon(id='script.transmission')
__language__ = __settings__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

if __name__ == '__main__':
    from gui import TransmissionGUI
    w = TransmissionGUI("script-Transmission-main.xml", __settings__.getAddonInfo('path') , "Default")
    w.doModal()
    del w
