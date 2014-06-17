# -*- coding: utf-8 -*-
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file LICENSE.txt.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
#Modules General
import os
import sys
from xml.etree import ElementTree
import xbmc
import xbmcaddon
import ambibox

__addon__ = xbmcaddon.Addon("script.ambibox")
__cwd__ = __addon__.getAddonInfo('path')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__settings__ = xbmcaddon.Addon("script.ambibox")
__language__ = __settings__.getLocalizedString
__scriptname__ = __addon__.getAddonInfo('name')

sys.path.append(__resource__)
__settingsdir__ = xbmc.translatePath(os.path.join(__cwd__, 'resources'))
ambibox = ambibox.AmbiBox(__settings__.getSetting("host"), int(__settings__.getSetting("port")))


def info(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg,), level=xbmc.LOGNOTICE)


def notification(text):
    text = text.encode('utf-8')
    info(text)
    if __settings__.getSetting("notification") == 'true':
        icon = __settings__.getAddonInfo("icon")
        smallicon = icon.encode("utf-8")
        xbmc.executebuiltin('Notification(AmbiBox,' + text + ',1000,' + smallicon + ')')


def updateprofilesettings():
    global ambibox
    pstrl = []
    if ambibox.connect() == 0:
        pfls = ambibox.getProfiles()
        defpfl = "None"
        pstrl.append('None')
        pstrl.append('|')
        for pfl in pfls:
            pstrl.append(str(pfl))
            pstrl.append('|')
            if str(pfl).lower() == 'default':
                defpfl = str(pfl)
        del pstrl[-1]
        pstr = "".join(pstrl)
        doc = ElementTree.parse(__settingsdir__ + "\\settings.xml")
        repl = ".//setting[@type='labelenum']"
        fixg = doc.iterfind(repl)
        for fixe in fixg:
            fixe.set('values', pstr)
            fixe.set('default', defpfl)
        doc.write(__settingsdir__ + "\\settings.xml")
        info('Settings refreshed from Ambibox Profiles')
        notification(__language__(32036))
    else:
        notification(__language__(32031))


def chkProfileSettings():
    global ambibox
    if ambibox.connect() == 0:
        __settings = xbmcaddon.Addon("script.ambibox")
        pfls = ambibox.getProfiles()
        sets2chk = ['default_profile', 'audio_profile', 'video_profile']
        vidfmts = ['2D', '3DS', '3DT']
        ars = ['43', '32', '169', '185', '22', '24']
        for vidfmt in vidfmts:
            for ar in ars:
                setn = vidfmt + '_' + ar
                sets2chk.append(setn)
        for setn in sets2chk:
            pname = __settings.getSetting(setn)
            if pname != 'None':
                if not(pname in pfls):
                    __settings.setSetting(setn, 'None')


def main():
    updateprofilesettings()
    chkProfileSettings()
    xbmc.executebuiltin('UpdateLocalAddons')

main()
