#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


import platform
import xbmc
import lib.common
from lib.common import log
from lib.common import upgrade_message as _upgrademessage

__addon__        = lib.common.__addon__
__addonversion__ = lib.common.__addonversion__
__addonname__    = lib.common.__addonname__
__addonpath__    = lib.common.__addonpath__
__icon__         = lib.common.__icon__
__localize__     = lib.common.__localize__


class Main:
    def __init__(self):
        linux = False
        packages = []
        if __addon__.getSetting("versioncheck_enable") == 'true' and not xbmc.getCondVisibility('System.HasAddon(os.openelec.tv)'):
            if not sys.argv[0]:
                xbmc.executebuiltin('XBMC.AlarmClock(CheckAtBoot,XBMC.RunScript(service.xbmc.versioncheck, started),00:00:30,silent)')
                xbmc.executebuiltin('XBMC.AlarmClock(CheckWhileRunning,XBMC.RunScript(service.xbmc.versioncheck, started),24:00:00,silent,loop)')
            elif sys.argv[0] and sys.argv[1] == 'started':
                if xbmc.getCondVisibility('System.Platform.Linux'):
                    packages = ['xbmc']
                    # _versionchecklinux(packages)
                else:
                    oldversion, msg = _versioncheck()
                    if oldversion:
                        _upgrademessage(msg, False)
            else:
                pass
                
def _versioncheck():
    # initial vars
    from lib.json import get_installedversion, get_versionfilelist
    from lib.versions import compare_version
    # retrieve versionlists from supplied version file
    versionlist = get_versionfilelist()
    # retrieve version installed
    version_installed = get_installedversion()
    # copmpare installed and available
    oldversion, msg = compare_version(version_installed, versionlist)
    return oldversion, msg


def _versionchecklinux(packages):
    if (platform.dist()[0] == "Ubuntu" or platform.dist()[0] == "Debian"):
        try:
            # try aptdeamon first
            from lib.aptdeamonhandler import AptdeamonHandler
            handler = AptdeamonHandler()
        except:
            # fallback to shell
            # since we need the user password, ask to check for new version first
            if _upgrademessage(32015, True):
                from lib.shellhandlerapt import ShellHandlerApt
                sudo = True
                handler = ShellHandlerApt(sudo)

    else:
        log("Unsupported platform %s" %platform.dist()[0])
        sys.exit(0)

    if handler:
        if handler.check_upgrade_available(packages[0]):
            if _upgrademessage(32012, True):
                if handler.upgrade_package(packages[0]): 
                    from lib.common import message_upgrade_success, message_restart
                    message_upgrade_success()
                    message_restart()
    else:
        log("Error: no handler found")



if (__name__ == "__main__"):
    log('Version %s started' % __addonversion__)
    Main()
