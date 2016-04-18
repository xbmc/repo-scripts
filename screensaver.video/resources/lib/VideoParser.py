# Copied (and slightly altered) from script.pseudotv.live
# with permission of Lunatixz:
#   http://forum.xbmc.org/showthread.php?tid=177296
# On 21st January 2014
#   https://github.com/Lunatixz/script.pseudotv.live/tree/master/resources/lib/parsers

import os

import parsers.MP4Parser as MP4Parser
import parsers.AVIParser as AVIParser
import parsers.MKVParser as MKVParser
import parsers.FLVParser as FLVParser
import parsers.TSParser as TSParser

from parsers.FileAccess import FileAccess


class VideoParser:
    def __init__(self):
        self.AVIExts = ['.avi']
        self.MP4Exts = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts = ['.mkv']
        self.FLVExts = ['.flv']
        self.TSExts = ['.ts', '.m2ts']

    def log(self, msg):
        FileAccess.log("VideoParser: %s" % msg)

    def getVideoLength(self, filename):
        self.log("getVideoLength " + filename)

        if len(filename) == 0:
            self.log("No file name specified")
            return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        elif ext in self.FLVExts:
            self.parser = FLVParser.FLVParser()
        elif ext in self.TSExts:
            self.parser = TSParser.TSParser()
        else:
            self.log("No parser found for extension %s" % ext)
            return 0

        return self.parser.determineLength(filename)
