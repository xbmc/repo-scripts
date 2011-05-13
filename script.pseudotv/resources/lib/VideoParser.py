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
import os, platform
import subprocess

import parsers.MP4Parser as MP4Parser
import parsers.AVIParser as AVIParser
import parsers.MKVParser as MKVParser
import parsers.FLVParser as FLVParser

from Globals import *



class VideoParser:
    def __init__(self):
        self.AVIExts = ['.avi']
        self.MP4Exts = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v']
        self.MKVExts = ['.mkv']
        self.FLVExts = ['.flv']
        self.mountedFS = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('VideoParser: ' + msg, level)


    def finish(self):
        if self.mountedFS == True:
            pipe = os.popen("umount \"" + xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt') + "\"")
            self.mountedFS = False


    def getVideoLength(self, filename):
        filename = xbmc.makeLegalFilename(filename)
        self.log("getVideoLength " + filename)

        if len(filename) == 0:
            self.log("No file name specified")
            return 0

        self.log("os name is " + os.name)

        if os.path.exists(filename) == False:
            if filename[0:6].lower() == 'smb://':
                filename = self.handleSMB(filename)
            else:
                self.log("Unable to open the file")
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
        else:
            self.log("No parser found for extension " + ext)
            return 0

        return self.parser.determineLength(filename)


    def handleSMB(self, filename):
        self.log("handleSMB")
        # On Windows, replace smb:// with \\ so that python can access it
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
        elif os.name.lower() == 'posix':
            newfilename = '//' + filename[6:]
            return self.mountPosixSMB(newfilename)

        return filename


    def mountPosixSMB(self, filename):
        if not os.path.exists(xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt/')):
            os.makedirs(xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt/'))

        if self.mountedFS == True:
            newfilename = xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt/') + os.path.split(filename)[1]

            if os.path.exists(newfilename):
                return newfilename

            pipe = os.popen("umount \"" + xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt') + "\"")
            self.mountedFS = False

        newfilename = self.mountFs(filename, 'cifs')

        if os.path.exists(newfilename):
            self.mountedFS = True
            return newfilename

        newfilename = self.mountFs(filename, 'smbfs')

        if os.path.exists(newfilename):
            self.mountedFS = True
            return newfilename

        return filename


    def mountFs(self, filename, fstype):
        dirpart, filename = os.path.split(filename)
        pipe = os.popen("mount -t " + fstype + " \"" + dirpart + "\" \"" + xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt') + "\"")
        newfilename = xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt/') + filename

        if os.path.exists(newfilename):
            return newfilename

        # Only try adding "Guest" if there is no username already there
        if dirpart.find('@') == -1:
            dirpart = "//Guest:@" + dirpart[2:]
            pipe = os.popen("mount -t " + fstype + " \"" + dirpart + "\" \"" + xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt') + "\"")

            if os.path.exists(newfilename):
                return newfilename

        # Seperate the username and password and try that
        username = dirpart[2:dirpart.find(':')]
        password = dirpart[dirpart.find(':') + 1:dirpart.find('@')]
        dirpart = '//' + dirpart[dirpart.find('@') + 1:]
        pipe = os.popen("mount -t cifs \"" + dirpart + "\" \"" + xbmc.translatePath('special://profile/addon_data/script.pseudotv/mountpnt') + "\" -o username=" + username + ",password=" + password)
        return newfilename
