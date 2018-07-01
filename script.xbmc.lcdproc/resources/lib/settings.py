'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi
    Copyright (C) 2012-2018 Daniel 'herrnst' Scheller

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import time

from .common import *

class Settings():

    ########
    # ctor
    def __init__(self):
        # init class members (settings) with defaults
        self._hostip              = "127.0.0.1"
        self._hostport            = 13666
        self._timer               = time.time()
        self._heartbeat           = False
        self._scrolldelay         = 1
        self._scrollmode          = "0"
        self._settingsChanged     = True
        self._dimonscreensaver    = False
        self._dimonshutdown       = False
        self._dimonvideoplayback  = False
        self._dimonmusicplayback  = False
        self._dimdelay            = 0
        self._navtimeout          = 3
        self._refreshrate         = 1
        self._hideconnpopups      = True
        self._usealternatecharset = False
        self._charset             = "iso-8859-1"
        self._useextraelements    = True

    def getHostIp(self):
        return self._hostip

    def getHostPort(self):
        return self._hostport

    def getHeartBeat(self):
        return self._heartbeat

    def getUseExtraElements(self):
        return self._useextraelements

    def getScrollDelay(self):
        return self._scrolldelay

    def getScrollMode(self):
        return self._scrollmode

    def getLCDprocScrollMode(self):
        if self._scrollmode == "1":
            return "h"
        return "m"

    def getDimOnScreensaver(self):
        return self._dimonscreensaver

    def getDimOnShutdown(self):
        return self._dimonshutdown

    def getDimOnVideoPlayback(self):
        return self._dimonvideoplayback

    def getDimOnMusicPlayback(self):
        return self._dimonmusicplayback

    def getDimDelay(self):
        return self._dimdelay

    def getNavTimeout(self):
        return self._navtimeout

    def getRefreshRate(self):
        return self._refreshrate

    def getHideConnPopups(self):
        return self._hideconnpopups

    def getCharset(self):
        ret = ""

        # if alternatecharset is disabled, return LCDproc's default
        if self._usealternatecharset == False:
            ret = "iso-8859-1"
        else:
            # make sure to keep this in sync with settings.xml!
            if self._charset == "1":
                ret = "iso-8859-15"
            elif self._charset == "2":
                ret = "koi8-r"
            elif self._charset == "3":
                ret = "cp1251"
            elif self._charset == "4":
                ret = "iso-8859-5"
            elif self._charset == "5":
                ret = "hd44780-a00"
            elif self._charset == "6":
                ret = "hd44780-a02"
            else:
                ret = "iso-8859-1"

        return ret

    # check for new settings and handle them if anything changed
    # only checks if the last check is 5 secs old
    # returns if a reconnect is needed due to settings change
    def checkForNewSettings(self):
    # TODO: for now impl. stat on addon.getAddonInfo('profile')/settings.xml and use mtime
    # check for new settings every 5 secs
        reconnect = False

        if time.time() - self._timer > 5:
            reconnect = self.setup()
            self._timer = time.time()

        return reconnect

    def didSettingsChange(self):
        settingsChanged = self._settingsChanged
        self._settingsChanged = False
        return settingsChanged

    # handle all settings that might require a reinit and/or reconnect
    # (e.g. network config changes)
    # returns true if reconnect is needed due to network changes
    def handleCriticalSettings(self):
        reconnect = False

        hostip           = KODI_ADDON_SETTINGS.getSetting("hostip")
        hostport         = int(KODI_ADDON_SETTINGS.getSetting("hostport"))
        heartbeat        = KODI_ADDON_SETTINGS.getSetting("heartbeat") == "true"
        useextraelements = KODI_ADDON_SETTINGS.getSetting("useextraelements") == "true"

        # server settings
        # we need to reconnect if networkaccess bool changes
        # or if network access is enabled and ip or port have changed
        if self._hostip != hostip or self._hostport != hostport or self._heartbeat != heartbeat:
            if self._hostip != hostip:
                log(LOGDEBUG, "settings: changed hostip to " + str(hostip))
                self._hostip = hostip
                reconnect = True

            if self._hostport != hostport:
                # make sure valid port number was given
                if hostport > 0 and hostport < 65536:
                    log(LOGDEBUG, "settings: changed hostport to " + str(hostport))
                    self._hostport = hostport
                    reconnect = True
                else:
                    log(LOGDEBUG, "settings: invalid hostport value " + str(hostport) + ", resetting to old value " + str(self._hostport))
                    KODI_ADDON_SETTINGS.setSetting("hostport", str(self._hostport))

            if self._heartbeat != heartbeat:
                log(LOGDEBUG, "settings: toggled heartbeat bool")
                self._heartbeat = heartbeat
                reconnect = True

        # extra element support needs a reinit+reconnect so the extraelement
        # support object resets
        if self._useextraelements != useextraelements:
            self._useextraelements = useextraelements
            reconnect = True

        return reconnect

    def handleLcdSettings(self):
        scrolldelay = int(float(KODI_ADDON_SETTINGS.getSetting("scrolldelay").replace(",", ".")))
        scrollmode = KODI_ADDON_SETTINGS.getSetting("scrollmode")
        dimonscreensaver = KODI_ADDON_SETTINGS.getSetting("dimonscreensaver") == "true"
        dimonshutdown = KODI_ADDON_SETTINGS.getSetting("dimonshutdown") == "true"
        dimonvideoplayback = KODI_ADDON_SETTINGS.getSetting("dimonvideoplayback") == "true"
        dimonmusicplayback = KODI_ADDON_SETTINGS.getSetting("dimonmusicplayback") == "true"
        dimdelay = int(float(KODI_ADDON_SETTINGS.getSetting("dimdelay").replace(",", ".")))
        navtimeout = int(float(KODI_ADDON_SETTINGS.getSetting("navtimeout").replace(",", ".")))
        refreshrate = int(float(KODI_ADDON_SETTINGS.getSetting("refreshrate").replace(",", ".")))
        hideconnpopups = KODI_ADDON_SETTINGS.getSetting("hideconnpopups") == "true"
        usealternatecharset = KODI_ADDON_SETTINGS.getSetting("usealternatecharset") == "true"
        charset = KODI_ADDON_SETTINGS.getSetting("charset")

        if self._scrolldelay != scrolldelay:
            self._scrolldelay = scrolldelay
            self._settingsChanged = True

        if self._scrollmode != scrollmode:
            self._scrollmode = scrollmode
            self._settingsChanged = True

        if self._dimonscreensaver != dimonscreensaver:
            self._dimonscreensaver = dimonscreensaver
            self._settingsChanged = True

        if self._dimonshutdown != dimonshutdown:
            self._dimonshutdown = dimonshutdown
            self._settingsChanged = True

        if self._dimonvideoplayback != dimonvideoplayback:
            self._dimonvideoplayback = dimonvideoplayback
            self._settingsChanged = True

        if self._dimonmusicplayback != dimonmusicplayback:
            self._dimonmusicplayback = dimonmusicplayback
            self._settingsChanged = True

        if self._dimdelay != dimdelay:
            self._dimdelay = dimdelay
            self._settingsChanged = True

        if self._navtimeout != navtimeout:
            self._navtimeout = navtimeout
            self._settingsChanged = True

        if self._refreshrate != refreshrate:
            self._refreshrate = refreshrate

            if refreshrate < 1:
                self._refreshrate = 1

            self._settingsChanged = True

        if self._hideconnpopups != hideconnpopups:
            self._hideconnpopups = hideconnpopups
            self._settingsChanged = True

        if self._usealternatecharset != usealternatecharset:
            self._usealternatecharset = usealternatecharset
            self._settingsChanged = True

        if self._charset != charset:
            self._charset = charset
            self._settingsChanged = True

    # handles all settings and applies them as needed
    # returns if a reconnect is needed due to settings changes
    def setup(self):
        reconnect = False
        reconnect = self.handleCriticalSettings()
        self.handleLcdSettings()

        return reconnect
