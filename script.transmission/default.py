# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

import os
import xbmc
import xbmcgui
import xbmcaddon
__scriptname__ = "Transmission-XBMC"
__author__ = "Correl Roush <correl@gmail.com>"
__url__ = "http://github.com/correl/Transmission-XBMC"
__svn_url__ = ""
__credits__ = ""
__version__ = "0.5.2"
__XBMC_Revision__ = "30377"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id='script.transmission')

__language__ = __settings__.getLocalizedString

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

if __name__ == '__main__':
    from gui import TransmissionGUI
    w = TransmissionGUI("script-Transmission-main.xml",os.getcwd() ,"Default")
    w.doModal()
    del w
