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
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import os
import urllib2
import hashlib
import sys
from _winreg import *

__addon__ = xbmcaddon.Addon('script.ambibox')
__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__settings__ = xbmcaddon.Addon("script.ambibox")
__language__ = __settings__.getLocalizedString

"""
debug = True
remote = False
if debug:
    if remote:
        sys.path.append(r'C:\\Users\\Ken User\\AppData\\Roaming\\XBMC\\addons\\script.ambibox\\resources\\lib\\pycharm-debug.py3k\\')
        import pydevd
        pydevd.settrace('192.168.1.103', port=51234, stdoutToServer=True, stderrToServer=True)
    else:
        sys.path.append('C:\Program Files (x86)\JetBrains\PyCharm 3.1.3\pycharm-debug-py3k.egg')
        import pydevd
        pydevd.settrace('localhost', port=51234, stdoutToServer=True, stderrToServer=True)

    if xbmcvfs.exists(__resource__ + r'\\mediainfo.dll'):
        try:
            xbmcvfs.delete(__resource__ + r'\\mediainfo.dll')
        except Exception, e:
            pass
"""

# Check if user has installed mediainfo.dll to resources/lib or has installed full Mediainfo package
__usingMediaInfo__ = False
if xbmcvfs.exists(xbmc.translatePath(os.path.join('mediainfo.dll'))):
    __usingMediaInfo__ = True
else:
    try:
        aReg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        key = OpenKey(aReg, r'Software\Microsoft\Windows\CurrentVersion\App Paths\MediaInfo.exe')
        path = QueryValue(key, None)
        CloseKey(key)
        CloseKey(aReg)
        if path != '':
            __usingMediaInfo__ = True
    except WindowsError, e:
        pass

if __usingMediaInfo__ is True:
    dialog = xbmcgui.Dialog()
    dialog.ok(__language__(32040), __language__(32062))
    del dialog
    sys.exit()


def main():
    dialog = xbmcgui.Dialog()
    if dialog.yesno(__language__(32040), __language__(32063)):
        del dialog
        downloadfile("https://github.com/AmbiBox/AmbiBox-XBMC/releases/download/pre-mediainfo/mediainfo.dll")


def downloadfile(url):
    file_name = url.split('/')[-1]
    fullfn = xbmc.translatePath(os.path.join(__resource__, file_name))
    try:
        u = urllib2.urlopen(url)
        f = open(fullfn, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        mprogress = xbmcgui.DialogProgress()
        mprogress.create(__language__(32064) % (file_name, file_size))

        file_size_dl = 0
        block_sz = 8192
        while True and not mprogress.iscanceled():
            mbuffer = u.read(block_sz)
            if not mbuffer:
                break

            file_size_dl += len(mbuffer)
            f.write(mbuffer)
            state = int(file_size_dl * 100. / file_size)
            mprogress.update(state)
        if mprogress.iscanceled():
            dialog = xbmcgui.Dialog()
            dialog.ok('', __language__(32066))
            sys.exit()
        mprogress.close()
        f.close()
        del u
    except Exception, e:
        try:
            mprogress.close()
            f.close()
            del u
        except:
            pass
        dialog = xbmcgui.Dialog()
        dialog.ok('', __language__(32065))
        if xbmcvfs.exists(fullfn):
            try:
                xbmcvfs.delete(fullfn)
            except:
                pass
        sys.exit()
    success = checkhash(fullfn)
    if success:
        dialog = xbmcgui.Dialog()
        dialog.ok('', __language__(32067))
    else:
        dialog = xbmcgui.Dialog()
        dialog.ok('', __language__(32065))
        if xbmcvfs.exists(fullfn):
            try:
                xbmcvfs.delete(fullfn)
            except:
                pass


def createhash(fname):
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(fname, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    hashfn = fname.split('.')[-1] + '.sha1'
    with open(hashfn, 'wb') as afile:
        strbuf = str(hasher.hexdigest())
        afile.write(strbuf)


def checkhash(fname):
    chkhash = '98842ed38d167f23681d9cb0f1c00c65069cda8d'
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    try:
        with open(fname, 'rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(BLOCKSIZE)
    except:
        success = False
    else:
        success = hasher.hexdigest() == chkhash
    return success

main()
