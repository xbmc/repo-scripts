#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Video ScreenSaver.
#
# Video ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Video ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Video ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import sys, traceback

from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

# Plugin Info
ADDON_ID       = 'screensaver.videosaver'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
VIDEO_EXTS     = xbmc.getSupportedMedia('video')

def selectDialog(list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True):
    if multi == True:
        if preselect is None: preselect = []
        select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else:
        if preselect is None:  preselect = -1
        select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
    if select is not None: return select
    return None

def buildMenuListItem(label1="", label2="", path="", art={'thumb':ICON,'fanart':FANART}, offscreen=True):
    liz = xbmcgui.ListItem(label1, label2, path, offscreen)
    liz.setArt(art)
    return liz
    
def browseDialog(type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False):
    if prompt and not default:
        if options is None:
            options  = [{"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":VIDEO_EXTS , "type":type, "multi":False},
                        {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""         , "type":type, "multi":False},
                        {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""         , "type":type, "multi":False},
                        {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""         , "type":type, "multi":False}]
        if type == 0: 
            options.insert(0,{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://profile/playlists/video/" , "mask":'.xsp'     , "type":1, "multi":False})
        listitems = [buildMenuListItem(option['label'],option['label2']) for option in options]
        select    = selectDialog(listitems, LANGUAGE(32018), multi=False)
        if select is not None:
            shares    = options[select]['label'].lower().replace("network","")
            mask      = options[select]['mask']
            type      = options[select]['type']
            multi     = options[select]['multi']
            default   = options[select]['default']
            
    if multi == True:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        # type integer - the type of browse dialog.
        # 1	ShowAndGetFile
        # 2	ShowAndGetImage
        retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    else:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        # type integer - the type of browse dialog.
        # 0	ShowAndGetDirectory
        # 1	ShowAndGetFile
        # 2	ShowAndGetImage
        # 3	ShowAndGetWriteableDirectory
        retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    if retval:
        if prompt and retval == default: return None
        return retval
    return None
      
if __name__ == '__main__':
    if not xbmcgui.Window(10000).getProperty("%s.Running"%(ADDON_ID)) == "True":
        xbmcgui.Window(10000).setProperty("%s.Running"%(ADDON_ID), "True")
        if sys.argv[1] == '-file':
            retval = browseDialog(type=1,heading=LANGUAGE(32014))#, default=REAL_SETTINGS.getSetting("VideoFile"))
            if retval: REAL_SETTINGS.setSetting("VideoFile",retval.strip())
        elif sys.argv[1] == '-folder': 
            retval = browseDialog(type=0,heading=LANGUAGE(32015))#, default=REAL_SETTINGS.getSetting("VideoFolder"))
            if retval: REAL_SETTINGS.setSetting("VideoFolder",retval.strip())
        xbmcgui.Window(10000).setProperty("%s.Running"%(ADDON_ID), "False")