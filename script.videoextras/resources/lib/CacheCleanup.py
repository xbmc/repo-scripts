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
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
import sys
import os
import re
import traceback
#Modules XBMC
import xbmc
import xbmcvfs
import xbmcaddon


__addon__     = xbmcaddon.Addon(id='script.videoextras')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__profile__   = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

#################################
# Class to tidy up any
#################################
class CacheCleanup():

    # Cleans out all the cached files
    @staticmethod
    def removeAllCachedFiles():
        CacheCleanup.removeCacheFile(Settings.MOVIES, True)
        CacheCleanup.removeCacheFile(Settings.TVSHOWS, True)
        CacheCleanup.removeCacheFile(Settings.MUSICVIDEOS, True)

        CacheCleanup.removeCacheFile('overlay_image_used.txt')


    # Removes the cache file for a given type
    @staticmethod
    def removeCacheFile(target, isDir=False):
        try:
            fullFilename = os_path_join(__profile__, target)
        
            log("VideoExtrasCleanup: Checking cache file %s" % fullFilename)
        
            # If the file already exists, delete it
            if xbmcvfs.exists(fullFilename):
                if isDir:
                    # Remove the png files in the directory first
                    dirs, files = xbmcvfs.listdir(fullFilename)
                    for aFile in files:
                        m = re.search("[0-9]+[a-zA-Z_]*.png", aFile, re.IGNORECASE)
                        if m:
                            pngFile = os_path_join( fullFilename, aFile )
                            xbmcvfs.delete(pngFile)
                    # Now remove the actual directory
                    xbmcvfs.rmdir(fullFilename)
                else:
                    xbmcvfs.delete(fullFilename)
        except:
            log("CacheCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)

