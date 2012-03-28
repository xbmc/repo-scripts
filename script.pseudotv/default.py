#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.


import xbmc, xbmcgui
import xbmcaddon


# Script constants
__scriptname__ = "PseudoTV"
__author__     = "Jason102"
__url__        = "http://github.com/Jasonra/XBMC-PseudoTV"
__settings__   = xbmcaddon.Addon(id='script.pseudotv')
__cwd__        = __settings__.getAddonInfo('path')


# Adapting a solution from ronie (http://forum.xbmc.org/showthread.php?t=97353)
if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True":
    xbmcgui.Window(10000).setProperty("PseudoTVRunning", "True")    
    shouldrestart = False

    if xbmc.executehttpapi("GetGuiSetting(1, services.webserver)")[4:] == "False":
        try:
            forcedserver = __settings__.getSetting("ForcedWebServer") == "True"
        except:
            forcedserver = False

        if forcedserver == False:
            dlg = xbmcgui.Dialog()
            retval = dlg.yesno('PseudoTV', 'PseudoTV will run more efficiently with the web', 'server enabled.  Would you like to turn it on?')
            __settings__.setSetting("ForcedWebServer", "True")

            if retval:
                xbmc.executehttpapi("SetGUISetting(3, services.webserverport, 8152)")
                xbmc.executehttpapi("SetGUISetting(1, services.webserver, true)")
                dlg.ok('PseudoTV', 'XBMC needs to shutdown in order to apply the', 'changes.')
                xbmc.executebuiltin("RestartApp()")
                shouldrestart = True

    if shouldrestart == False:
        xbmc.executebuiltin('RunScript("' + __cwd__ + '/pseudotv.py' + '")')
else:
    xbmc.log('script.PseudoTV - Already running, exiting', xbmc.LOGERROR)
