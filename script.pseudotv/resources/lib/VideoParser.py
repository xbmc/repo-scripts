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

import xbmc
import os

import parsers.MP4Parser as MP4Parser
import parsers.AVIParser as AVIParser
import parsers.MKVParser as MKVParser

from Globals import *



class VideoParser:
    def __init__(self):
        self.AVIExts = ['.avi']
        self.MP4Exts = ['.mp4', '.m4v', '.3gp', '.3g2']
        self.MKVExts = ['.mkv']


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('VideoParser: ' + msg, level)


    def getVideoLength(self, filename):
        self.log("getVideoLength " + filename)
        filename = xbmc.makeLegalFilename(filename)

        if len(filename) == 0:
            self.log("No file name specified")
            return 0

        if os.path.exists(filename) == False:
            self.log("File doesn't exist")
            return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        else:
            self.log("No parser found for extension " + ext)
            return 0

        return self.parser.determineLength(filename)

