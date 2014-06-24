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
# *from mediainfodll import MediaInfo, Stream

from mediainfodll import MediaInfo, Stream
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')


def info(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg,), level=xbmc.LOGNOTICE)


class Media:

    def __init__(self):
        self.mi = MediaInfo()

    def getInfos(self, mfile):
        nfile = self.smbToUNC(mfile)
        self.mi.Open(nfile)
        width = self.mi.Get(Stream.Video, 0, "Width")
        height = self.mi.Get(Stream.Video, 0, "Height")
        ratio = self.mi.Get(Stream.Video, 0, "PixelAspectRatio")
        dar = self.mi.Get(Stream.Video, 0, "DisplayAspectRatio")
        self.mi.Close()
        try:
            width = int(float(width))
            height = int(float(height))
        except:
            width = int(0)
            height = int(0)
        try:
            dar = float(dar)
        except:
            dar = float(0)

        return [width, height, 1, dar]

    def smbToUNC(self, smbFile):
        testFile = smbFile[0:3]
        newFile = ""
        if testFile == "smb":
            for i in xrange(0, len(smbFile)):
                if smbFile[i] == "/":
                    newFile += "\\"
                else:
                    newFile = newFile + smbFile[i]
            retFile = newFile[4:]
        else:
            retFile = smbFile
        return retFile

