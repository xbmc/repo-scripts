#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmc
import xbmcaddon
import xbmcgui
import os
import sys
from datetime import datetime

__Version__ = "1.1.2"

PYVER = float('{}.{}'.format(*sys.version_info[:2]))

def GetXBMCVersion():
    version = xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')
    version = version.split('.')
    return int(version[0]), int(version[1]) #major, minor



ADDON   =  xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
if PYVER < 3.0:
    ADDON_PATH = ADDON.getAddonInfo('path').decode('utf-8')
else:
    ADDON_PATH = ADDON.getAddonInfo('path')

ADDON_USERDATA_FOLDER = xbmc.translatePath("special://profile/addon_data/"+ADDONID)
KEYMAPS_USERDATA_FOLDER = xbmc.translatePath('special://userdata/keymaps')
BASEPATH = os.path.join(ADDON_PATH,r"resources")
if BASEPATH not in sys.path:
    sys.path.insert(2,BASEPATH)

DATAFILE_LOCATIONFILE = os.path.join(BASEPATH, r"data/dataFileLocation.py")
ADDON_DATAFILENAME = os.path.join(ADDON_USERDATA_FOLDER,"LTVPL.pkl")
DEFAULTPATH ='dataFilePath = r"' + ADDON_DATAFILENAME + '"'
DEBUGFILE_LOCATIONFILE = os.path.join(BASEPATH, r"data/debugFileLocation.py")
DEBUGFILE_DEFAULTPATH = os.path.join(BASEPATH, r"data/debugcache.json")
DEBUGFILE_LOCATIONCONTENT = 'DEBUGCACHEFILE = r"' + DEBUGFILE_DEFAULTPATH + '"'
XMLPATH = os.path.join(ADDON_PATH, 'resources/skins/Default/720p')
FANART_PATH = os.path.join(ADDON_PATH, 'fanart.jpg')
BGDIMAGE = os.path.join(ADDON_PATH, 'resources/skins/Default/media', 'WhiteBlank.png')

HOME    =  ADDON_PATH
ROOT    =  ADDON.getSetting('FOLDER')
PROFILE =  os.path.join(ROOT, 'Super Favourites')
VERSION = '1.0.0'
ICON    =  os.path.join(HOME, 'icon.png')
FANART  =  os.path.join(HOME, 'fanart.jpg')
SEARCH  =  os.path.join(HOME, 'resources', 'media', 'search.png')
# GETTEXT =  ADDON.getLocalizedString
LTVPL_HEADER = LTVPL = 'Live TV Playlist'

ACTIVATIONKEY = 'activationkey'

def GETTEXT(id):
    return ADDON.getLocalizedString(id).encode('utf-8')

def getRegionDatetimeFmt():
    timefmt = xbmc.getRegion('time')
    timefmt = timefmt.replace(':%S','')

    if "%I%I" in timefmt:
        timefmt = timefmt.replace('%I%I', "%I")
    elif "%H%H" in timefmt:
        timefmt = timefmt.replace('%H%H', "%H")

    return xbmc.getRegion('dateshort') + " " + timefmt

def setUSpgmDate(obj):
    try:
        dateformat = xbmc.getRegion('dateshort')
        pgmDate = obj.getProperty('pgmDate')
        liDateTime = datetime.strptime(pgmDate, dateformat)
        USpgmDate = liDateTime.strftime("%m/%d/%Y")
        obj.setProperty('USpgmDate', USpgmDate)
    except: pass

def DialogOK(title, line1, line2='', line3=''):
    d = xbmcgui.Dialog()
    d.ok(title + ' - ' + VERSION, line1, line2 , line3)


def DialogYesNo(title, line1, line2='', line3='', noLabel=None, yesLabel=None):
    d = xbmcgui.Dialog()
    if noLabel is None or yesLabel is None:
        return d.yesno(title + ' - ' + VERSION, line1, line2 , line3) == True
    else:
        return d.yesno(title + ' - ' + VERSION, line1, line2 , line3, noLabel, yesLabel) == True


def generateMD5(text):
    if not text:
        return ''

    try:
        import hashlib
        return hashlib.md5(text).hexdigest()
    except:
        try:
            import md5
            return md5.new(text).hexdigest()
        except:
            pass

    return '0'

def GetFolder(title):
    default = ROOT #ADDON.getAddonInfo('profile')
    folder  = xbmc.translatePath(PROFILE)

    if not os.path.isdir(folder):
        os.makedirs(folder)

    folder = xbmcgui.Dialog().browse(3, title, 'files', '', False, False, default)
    if folder == default:
        return None

    return xbmc.translatePath(folder)
