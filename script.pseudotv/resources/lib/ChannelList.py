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

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random
import httplib
import base64


from xml.dom.minidom import parse, parseString

from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser



class ChannelList:
    def __init__(self):
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.showList = []
        self.videoParser = VideoParser()
        self.httpJSON = True
        self.sleepTime = 0
        self.exitThread = False
        self.discoveredWebServer = False


    def setupList(self):
        self.channels = []
        self.findMaxChannels()
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.updateDialog = xbmcgui.DialogProgress()
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.updateDialog.create("PseudoTV", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except:
            self.lastResetTime = 0

        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except:
            self.lastExitTime = int(time.time())

        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.updateDialog.update(i * 100 // self.maxChannels, "Updating channel " + str(i + 1))
            self.channels.append(Channel())

            # If the user pressed cancel, stop everything and exit
            if self.updateDialog.iscanceled():
                self.log('Update channels cancelled')
                self.updateDialog.close()
                return None

            self.setupChannel(i + 1)

        REAL_SETTINGS.setSetting('ForceChannelReset', 'false')
        self.updateDialog.update(100, "Update complete")
        self.updateDialog.close()

        return self.channels


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)


    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        self.maxChannels = 0

        for i in range(999):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''

            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
            except:
                pass

            if chtype == 0:
                if os.path.exists(xbmc.translatePath(chsetting1)):
                    self.maxChannels = i + 1
            elif chtype < 7:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1

        self.log('findMaxChannels return ' + str(self.maxChannels))


    def determineWebServer(self):
        if self.discoveredWebServer:
            return

        self.discoveredWebServer = True
        self.webPort = 8080
        self.webUsername = ''
        self.webPassword = ''
        fle = xbmc.translatePath("special://profile/guisettings.xml")

        try:
            xml = open(fle, "r")
        except:
            self.log("determineWebServer Unable to open the settings file", xbmc.LOGERROR)
            self.httpJSON = False
            return

        try:
            dom = parse(xml)
        except:
            self.log('determineWebServer Unable to parse settings file', xbmc.LOGERROR)
            self.httpJSON = False
            return

        xml.close()

        try:
            plname = dom.getElementsByTagName('webserver')
            self.httpJSON = (plname[0].childNodes[0].nodeValue.lower() == 'true')
            self.log('determineWebServer is ' + str(self.httpJSON))

            if self.httpJSON == True:
                plname = dom.getElementsByTagName('webserverport')
                self.webPort = int(plname[0].childNodes[0].nodeValue)
                self.log('determineWebServer port ' + str(self.webPort))
                plname = dom.getElementsByTagName('webserverusername')
                self.webUsername = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer username ' + self.webUsername)
                plname = dom.getElementsByTagName('webserverpassword')
                self.webPassword = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer password is ' + self.webPassword)
        except:
            return


    # Code for sending JSON through http adapted from code by sffjunkie (forum.xbmc.org/showthread.php?t=92196)
    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
        usedhttp = False

        self.determineWebServer()

        # If there have been problems using the server, just skip the attempt and use executejsonrpc
        if self.httpJSON == True:
            payload = command.encode('utf-8')
            headers = {'Content-Type': 'application/json-rpc; charset=utf-8'}

            if self.webUsername != '':
                userpass = base64.encodestring('%s:%s' % (self.webUsername, self.webPassword))[:-1]
                headers['Authorization'] = 'Basic %s' % userpass

            self.webPort = 8080

            try:
                conn = httplib.HTTPConnection('127.0.0.1', self.webPort)
                conn.request('POST', '/jsonrpc', payload, headers)
                response = conn.getresponse()

                if response.status == 200:
                    data = response.read()
                    usedhttp = True

                conn.close()
            except:
                pass

        if usedhttp == False:
            self.httpJSON = False
            data = xbmc.executeJSONRPC(command)

        return data


    def setupChannel(self, channel):
        self.log('setupChannel ' + str(channel))
        returnval = False
        createlist = True
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        needsreset = False

        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
        except:
            pass

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
        except:
            pass

        if chtype == 9999:
            self.channels[channel - 1].isValid = False
            return False

        # If possible, use an existing playlist
        if os.path.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'):
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time'))

                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True

                    # If this channel has been watched for longer than it lasts, reset the channel
                    if self.channelResetSetting == 0 and self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                        createlist = self.forceReset

                    if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        timedif = time.time() - self.lastResetTime

                        if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                            createlist = self.forceReset

                        if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                            createlist = self.forceReset

                        if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                            createlist = self.forceReset

                        if timedif < 0:
                            createlist = self.forceReset

                        if createlist:
                            ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))

                    if self.channelResetSetting == 4:
                        createlist = self.forceReset
            except:
                pass

        if createlist or needsreset:
            if self.makeChannelList(channel, chtype, chsetting1, chsetting2) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].totalTimePlayed = 0
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')

        self.clearPlaylistHistory(channel)

        if chtype == 6:
            if chsetting2 == str(MODE_SERIAL):
                self.channels[channel - 1].mode = MODE_SERIAL

        # if there is no start mode in the channel mode flags, set it to the default
        if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
            if self.startMode == 0:
                self.channels[channel - 1].mode = MODE_RESUME
            elif self.startMode == 1:
                self.channels[channel - 1].mode = MODE_REALTIME
            elif self.startMode == 2:
                self.channels[channel - 1].mode = MODE_RANDOM

        if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
            self.channels[channel - 1].isPaused = True

        if self.channels[channel - 1].mode & MODE_RANDOM > 0:
            self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

        if self.channels[channel - 1].mode & MODE_REALTIME > 0:
            chantime = 0

            try:
                chantime = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time'))
            except:
                pass

            timedif = int(time.time()) - self.lastExitTime
            self.channels[channel - 1].totalTimePlayed += timedif

        if self.channels[channel - 1].mode & MODE_RESUME > 0:
            self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
            self.channels[channel - 1].totalTimePlayed = 0

        while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
            self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
            self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, chsetting1)
        return returnval


    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("channel not valid, ignoring")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > 60 * 60 * 24:
            try:
                fle = open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            fle.write("#EXTM3U\n")
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 24)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i)
                    tmpstr = tmpstr[:600]
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = tmpstr + '\n' + self.channels[channel - 1].getItemFilename(i)
                    fle.write("#EXTINF:" + tmpstr + "\n")
                else:
                    timeremoved = tottime

            fle.close()

            if timeremoved > 0:
                self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')

            self.channels[channel - 1].totalTimePlayed -= timeremoved



    def getChannelName(self, chtype, setting1):
        self.log('getChannelName ' + str(chtype))

        if len(setting1) == 0:
            return ''

        if chtype == 0:
            return self.getSmartPlaylistName(setting1)
        elif chtype == 1 or chtype == 2 or chtype == 5 or chtype == 6:
            return setting1
        elif chtype == 3:
            return setting1 + " TV"
        elif chtype == 4:
            return setting1 + " Movies"

        return ''


    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        fle = xbmc.translatePath(fle)

        try:
            xml = open(fle, "r")
        except:
            self.log("getSmartPlaylisyName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''


    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, append = False):
        self.log('makeChannelList ' + str(channel))

        if chtype == 0:
            fle = setting1
        else:
            fle = self.makeTypePlaylist(chtype, setting1, setting2)

        fle = xbmc.translatePath(fle)

        if len(fle) == 0:
            self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
            return False

        try:
            xml = open(fle, "r")
        except:
            self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return False

        try:
            dom = parse(xml)
        except:
            self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return False

        xml.close()

        if self.getSmartPlaylistType(dom) == 'mixed':
            fileList = self.buildMixedFileList(dom)
        else:
            fileList = self.buildFileList(fle)

        try:
            if append == True:
                channelplaylist = open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r+")
                channelplaylist.seek(0, 2)
            else:
                channelplaylist = open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            channelplaylist.write("#EXTM3U\n")

        if len(fileList) == 0:
            self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
            channelplaylist.close()
            return False

        try:
            order = dom.getElementsByTagName('order')

            if order[0].childNodes[0].nodeValue.lower() == 'random':
                random.shuffle(fileList)
        except:
            pass

        fileList = fileList[:250]

        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write("#EXTINF:" + string + "\n")

        channelplaylist.close()
        self.log('makeChannelList return')
        return True


    def appendChannel(self, channel):
        self.log("appendChannel")
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''

        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
        except:
            self.log("appendChannel unable to get channel settings")
            return False

        return self.makeChannelList(channel, chtype, chsetting1, chsetting2, True)


    def makeTypePlaylist(self, chtype, setting1, setting2):
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()

            return self.createNetworkPlaylist(setting1)
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()

            return self.createStudioPlaylist(setting1)
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()

            return self.createGenrePlaylist('episodes', chtype, setting1)
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()

            return self.createGenrePlaylist('movies', chtype, setting1)
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())

            return self.createGenreMixedPlaylist(setting1)
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()

            return self.createShowPlaylist(setting1, setting2)

        self.log('makeTypePlaylists invalid channel type: ' + str(chtype))
        return ''


    def createNetworkPlaylist(self, network):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Network_' + network + '.xsp')

        try:
            fle = open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, network))
        network = network.lower()
        added = False

        for i in range(len(self.showList)):
            if self.threadPause() == False:
                fle.close()
                return ''

            if self.showList[i][1].lower() == network:
                theshow = self.cleanString(self.showList[i][0])
                fle.write('    <rule field="tvshow" operator="is">' + theshow + '</rule>\n')
                added = True

        self.writeXSPFooter(fle, 250, "random")
        fle.close()

        if added == False:
            return ''

        return flename


    def createShowPlaylist(self, show, setting2):
        order = 'random'

        try:
            setting = int(setting2)

            if setting & MODE_ORDERAIRDATE > 0:
                order = 'airdate'
        except:
            pass

        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + show + '_' + order + '.xsp')

        try:
            fle = open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, show))
        show = self.cleanString(show)
        fle.write('    <rule field="tvshow" operator="is">' + show + '</rule>\n')
        self.writeXSPFooter(fle, 250, order)
        fle.close()
        return flename


    def createGenreMixedPlaylist(self, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Mixed_' + genre + '.xsp')

        try:
            fle = open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, 250, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')

        try:
            fle = open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, genre))
        genre = self.cleanString(genre)
        fle.write('    <rule field="genre" operator="is">' + genre + '</rule>\n')
        self.writeXSPFooter(fle, 250, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')

        try:
            fle = open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, studio))
        studio = self.cleanString(studio)
        fle.write('    <rule field="studio" operator="is">' + studio + '</rule>\n')
        self.writeXSPFooter(fle, 250, "random")
        fle.close()
        return flename


    def writeXSPHeader(self, fle, pltype, plname):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="' + pltype + '">\n')
        plname = self.cleanString(plname)
        fle.write('    <name>' + plname + '</name>\n')
        fle.write('    <match>one</match>\n')


    def writeXSPFooter(self, fle, limit, order):
        fle.write('    <limit>' + str(limit) + '</limit>\n')
        fle.write('    <order direction="ascending">' + order + '</order>\n')
        fle.write('</smartplaylist>\n')


    def cleanString(self, string):
        newstr = string
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        return newstr


    def fillTVInfo(self):
        self.log("fillTVInfo")
        json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"fields":["studio", "genre"]}, "id": 1}'
        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                break

            match = re.search('"studio" *: *"(.*?)",', f)
            network = ''

            if match:
                found = False
                network = match.group(1).strip()

                for item in self.networkList:
                    if item.lower() == network.lower():
                        found = True
                        break

                if found == False and len(network) > 0:
                    self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = match.group(1).strip()
                self.showList.append([show, network])

            match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip()

                    for g in self.showGenreList:
                        if curgenre == g.lower():
                            found = True
                            break

                    if found == False:
                        self.showGenreList.append(genre.strip())

        self.networkList.sort(key=lambda x: x.lower())
        self.showGenreList.sort(key=lambda x: x.lower())
        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self):
        self.log("fillMovieInfo")
        studioList = []
        json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"fields":["studio", "genre"]}, "id": 1}'
        json_folder_detail = self.sendJSON(json_query)
#        self.log(json_folder_detail)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip()

                    for g in self.movieGenreList:
                        if curgenre == g.lower():
                            found = True
                            break

                    if found == False:
                        self.movieGenreList.append(genre.strip())

            match = re.search('"studio" *: *"(.*?)",', f)

            if match:
                studios = match.group(1).split('/')

                for studio in studios:
                    curstudio = studio.strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount - 15) < abs(lastmatch - 15):
                bestmatch = i
                lastmatch = itemcount

        for i in range(len(studioList)):
            if studioList[i][1] == bestmatch:
                self.studioList.append(studioList[i][0])

        self.studioList.sort(key=lambda x: x.lower())
        self.movieGenreList.sort(key=lambda x: x.lower())
        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        self.log("makeMixedList return " + str(newlist))
        return newlist



    def buildFileList(self, dir_name, media_type="video", recursive="TRUE"):
        self.log("buildFileList")
        fileList = []
        json_query = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "fields":["duration","runtime","tagline","showtitle","album","artist","plot"]}, "id": 1}' % ( self.escapeDirJSON( dir_name ), media_type )
        json_folder_detail = self.sendJSON(json_query)
        self.log(json_folder_detail)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break

            match = re.search('"file" *: *"(.*?)",', f)

            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    if(recursive == "TRUE"):
                        fileList.extend(self.buildFileList(match.group(1), media_type, recursive))
                else:
                    duration = re.search('"duration" *: *([0-9]*?),', f)

                    try:
                        dur = int(duration.group(1))
                    except:
                        dur = 0

                    if dur == 0:
                        duration = re.search('"runtime" *: *"([0-9]*?)",', f)

                        try:
                            # Runtime is reported in minutes
                            dur = int(duration.group(1)) * 60
                        except:
                            dur = 0

                        if dur == 0:
                            dur = self.videoParser.getVideoLength(match.group(1).replace("\\\\", "\\"))

                    try:
                        if dur > 0:
                            title = re.search('"label" *: *"(.*?)"', f)
                            tmpstr = str(dur) + ','
                            showtitle = re.search('"showtitle" *: *"(.*?)"', f)
                            plot = re.search('"plot" *: *"(.*?)",', f)

                            if plot == None:
                                theplot = ""
                            else:
                                theplot = plot.group(1)

                            # This is a TV show
                            if showtitle != None and len(showtitle.group(1)) > 0:
                                tmpstr += showtitle.group(1) + "//" + title.group(1) + "//" + theplot
                            else:
                                tmpstr += title.group(1) + "//"
                                album = re.search('"album" *: *"(.*?)"', f)

                                # This is a movie
                                if album == None or len(album.group(1)) == 0:
                                    tagline = re.search('"tagline" *: *"(.*?)"', f)

                                    if tagline != None:
                                        tmpstr += tagline.group(1)

                                    tmpstr += "//" + theplot
                                else:
                                    artist = re.search('"artist" *: *"(.*?)"', f)
                                    tmpstr += album.group(1) + "//" + artist.group(1)

                            tmpstr = tmpstr[:600]
                            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                            tmpstr = tmpstr + '\n' + match.group(1).replace("\\\\", "\\")
                            fileList.append(tmpstr)
                    except:
                        pass
            else:
                continue

        self.videoParser.finish()
        return fileList


    def buildMixedFileList(self, dom1):
        fileList = []
        self.log('buildMixedFileList')

        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if os.path.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                fileList.extend(self.buildFileList(xbmc.translatePath('special://profile/playlists/video/') + rulename))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename))

        self.log("buildMixedFileList returning")
        return fileList


    def threadPause(self):
        if threading.activeCount() > 1:
            if self.exitThread == True:
                return False

            time.sleep(self.sleepTime)

        return True


    def escapeDirJSON(self, dir_name):
        if (dir_name.find(":")):
            dir_name = dir_name.replace("\\", "\\\\")

        return dir_name


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''
