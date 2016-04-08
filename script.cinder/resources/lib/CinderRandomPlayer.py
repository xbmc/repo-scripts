# This file is part of Cinder.
#
# Cinder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cinder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cinder.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import xbmcaddon
import xbmcgui
import pykodi
import random
import sys


class CinderRandomPlayer(object):

    def __init__(self, additionalSourceList, additionalSourceWeightList):
        self.configSettings = {}

        # aquire the users configuration settings
        self.aquireConfigSettings(additionalSourceList, additionalSourceWeightList)


    # Gets the user specified configuration from KODI
    def aquireConfigSettings(self, additionalSourceList, additionalSourceWeightList):
        settings = xbmcaddon.Addon(id='script.cinder')

        configKeyList = [ 'WatchedRandomMode', 'NumberOfShows', 'ShufflePlaylist', \
                          'SkipSources', 'BootstrapPlayback', 'Source1Uri', 'Source1Weight', \
                          'Source2Uri', 'Source2Weight', 'Source3Uri', 'Source3Weight', \
                          'Source4Uri', 'Source4Weight', 'Source5Uri', 'Source5Weight', \
                          'Source6Uri', 'Source6Weight', 'Source7Uri', 'Source7Weight', \
                          'Source8Uri', 'Source8Weight', 'Source9Uri', 'Source9Weight', \
                          'Source10Uri', 'Source10Weight', 'Source11Uri', 'Source11Weight', \
                          'Source12Uri', 'Source12Weight', 'Source13Uri', 'Source13Weight', \
                          'Source14Uri', 'Source14Weight', 'Source15Uri', 'Source15Weight', \
                          'Source16Uri', 'Source16Weight', 'Source17Uri', 'Source17Weight', \
                          'Source18Uri', 'Source18Weight', 'Source19Uri', 'Source19Weight', \
                          'Source20Uri', 'Source20Weight' ]

        self.configSettings = {}
        self.configSettings['SourceUriList'] = []
        self.configSettings['SourceWeightList'] = []

        for configKey in configKeyList: 
            if configKey.find('Source') == 0:
                value = settings.getSetting(configKey) 
                if len(value) == 0:
                    pykodi.log(configKey + ": SKIPPING", xbmc.LOGDEBUG)
                else:
                    index = configKey.find('Weight')
                    if index == -1:
                        self.configSettings[configKey] = settings.getSetting(configKey) 
                        self.configSettings['SourceUriList'].append(value)
                        pykodi.log(configKey + ": " + value, xbmc.LOGDEBUG)
                    else:
                        modifiedKey = configKey[:index] + 'Uri'
                        if modifiedKey in self.configSettings.keys():
                            self.configSettings[configKey] = settings.getSetting(configKey) 
                            self.configSettings['SourceWeightList'].append(value)
                            pykodi.log(configKey + ": " + value, xbmc.LOGDEBUG)
                        else:
                            pykodi.log(configKey + ": SKIPPING", xbmc.LOGDEBUG)
            else:
                self.configSettings[configKey] = settings.getSetting(configKey) 
                pykodi.log(configKey + ": " + self.configSettings[configKey], xbmc.LOGDEBUG)

        # append additional sources that the user may have passed in via lists in the
        # constructor
        for additionalSource in additionalSourceList:
            self.configSettings['SourceUriList'].append(additionalSource)
        for additionalSourceWeight in additionalSourceWeightList:
            self.configSettings['SourceWeightList'].append(additionalSourceWeight)


    # Sets up the random playlist and starts playing it on the first call. Additional calls
    # append episodes onto the playlist
    def playRandomPlaylist(self, randomFileList):
        if self.queuedEpisodes == None:
            # create a new playlist and start playing it
            self.queuedEpisodes = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            self.queuedEpisodes.clear()
            for randomFile in randomFileList:
                self.queuedEpisodes.add(randomFile.get('file'), xbmcgui.ListItem(randomFile.get('label')))
            xbmc.Player().play(self.queuedEpisodes)
            xbmc.executebuiltin('Dialog.Close(busydialog)')
        else:
            # append to the existing playlist that is already playing
            for randomFile in randomFileList:
                self.queuedEpisodes.add(randomFile.get('file'), xbmcgui.ListItem(randomFile.get('label')))


    # Finds a random episode and starts playing it as soon as possible. Returns True if the first source
    # should be skipped based on configuration settings
    def bootstrapPlayback(self):
        skipFirstSource = True

        indexList = range(0, len(self.configSettings['SourceUriList']))
        if self.configSettings['SkipSources'] == "true" or \
           self.configSettings['ShufflePlaylist'] == "true":
            skipFirstSource = False
            random.shuffle(indexList)
            random.shuffle(indexList)
            random.shuffle(indexList)

        # attempt to find an episode from any sources only once 
        # let the caller do multiple sweeps
        for index in indexList: 
            showWeight = int(self.configSettings['SourceWeightList'][index])
            if random.randint(1, 100) > showWeight:
                continue

            videos = self.getRandomEpisode(self.configSettings['SourceUriList'][index])

            # skip duplicate videos
            if self.isDuplicate(videos): 
                # should not hit this since its the first episode queued up
                # need to call isDuplicate to have it added to in internal
                # list
                continue

            self.playRandomPlaylist(videos)
            return skipFirstSource
        return skipFirstSource


    # Returns True if the episode has already been queued up. Keeps track of which
    # episodes have been provided as a parameter
    def isDuplicate(self, randomFileList):
        # there should only be one file in randomFileList
        for randomFile in randomFileList:
            for queuedEpisodeDuplicate in self.queuedEpisodesDuplicateCheck:
                if randomFile['file'] == queuedEpisodeDuplicate['file']: 
                    return True
            self.queuedEpisodesDuplicateCheck.append(randomFile)
            return False
        return False


    # Plays random episodes according to the user specified configuration settings
    def playRandomEpisodes(self):
        xbmc.executebuiltin('ActivateWindow(busydialog)')

        self.queuedEpisodesDuplicateCheck = []
        self.queuedEpisodes = None
        numberOfShows = int(self.configSettings['NumberOfShows']) 

        skipFirstSource = False
        if self.configSettings['BootstrapPlayback'] == "true":
            skipFirstSource = self.bootstrapPlayback()
            numberOfShows -= 1

            # catch the case of the user only wanting 1 episode queued up
            if numberOfShows <= 0:
                return

        episodeList = []
        sweepCount = 0
        while True:

            sweepCount += 1
            if sweepCount > 100:
                # after 100 attempts to fill up the playlist cancel the process
                # the user is probably in 'watched' or 'unwatched' only modes
                # and the process is not finding anything
                xbmcgui.Dialog().notification('Cinder Error:', 'Unable to find episodes. Try "All videos" mode', xbmcgui.NOTIFICATION_WARNING)
                xbmc.executebuiltin('Dialog.Close(busydialog)')
                return

            index = 0
            for sourceEntry in self.configSettings['SourceUriList']:
                if skipFirstSource == True:
                    index += 1
                    skipFirstSource = False
                    continue

                if self.configSettings['SkipSources'] == "true":
                    if random.randint(0, 1) == 0:
                        index += 1
                        continue

                showWeight = int(self.configSettings['SourceWeightList'][index])
                if random.randint(1, 100) > showWeight:
                    index += 1
                    continue

                index += 1

                videos = self.getRandomEpisode(sourceEntry)

                # skip duplicate videos
                if self.isDuplicate(videos): 
                    continue

                for videoEntry in videos:
                    episodeList.append(videoEntry) 

                    # once the list is the right length short circuit the process
                    if len(episodeList) >= numberOfShows:
                        if self.configSettings['ShufflePlaylist'] == "true":
                            random.shuffle(episodeList)
                        self.playRandomPlaylist(episodeList)
                        return


    # Gets a random episode from the given SBM share
    def getRandomEpisode(self, fullpath):
        maxAttempts = 5
        currentAttempt = 0
        while currentAttempt < maxAttempts:
            randomFileList = self.getRandomEpisodeRecusive(fullpath)
            if len(randomFileList) > 0:
                # found something
                return randomFileList
            else:
                # increment the escape counter
                currentAttempt += 1

        # exceeded the retry count return an empty list
        return []


    # Returns True if the given fileEntry is a directory
    def isDirectory(self, fileEntry):
        if fileEntry['filetype'] == 'directory':
            return True
        return False


    # Returns True if the given fileEntry meets the criteria for random playback
    def shouldPlayFile(self, fileEntry):
        watchedRandomMode = int(self.configSettings['WatchedRandomMode'])

        if fileEntry['file'].endswith(('.m3u', '.db', '.txt', '.id', '.nfo', '.pls', '.cue')):
            return False

        if ('playcount' in fileEntry.keys()) == False:
            # skip files that are not in the Kodi SQL database
            return False

        if watchedRandomMode == 1:

            # user only wants previously unwatched files
            if fileEntry['playcount'] > 0:
                return False

        elif watchedRandomMode == 2:

            # user only wants previously watched files
            if fileEntry['playcount'] == 0:
                return False
 
        # user wants both watched and unwatched files
        return True


    # Helper function to get a random episode. Should not be called directly
    def getRandomEpisodeRecusive(self, fullpath):
        jsonRequest = pykodi.get_base_json_request('Files.GetDirectory')
        jsonRequest['params'] = {'directory': fullpath, 'media': 'video'}
        jsonRequest['params']['sort'] = {'method': 'random'}
        jsonRequest['params']['properties'] = ['playcount']
        jsonRequest['params']['limits'] = {'end': 10}

        jsonResponse = pykodi.execute_jsonrpc(jsonRequest)

        pykodi.log(str(jsonResponse), xbmc.LOGDEBUG)
        if 'result' in jsonResponse and 'files' in jsonResponse['result']:

            # note: for some reason KODI returns the same videos at the front
            #       of the retuned random list if there is a large number of files. 
            #       Reverse the returned list to get
            #       more random results in the case of a lot of files in the
            #       smb source
            for fileEntry in list(reversed(jsonResponse['result']['files'])):

                # recurse down directories
                if self.isDirectory(fileEntry):
                    if fileEntry['label'] in ('extrafanart', 'extrathumbs'):
                        continue
                    subdirectoryResult = self.getRandomEpisodeRecusive(fileEntry['file'])
                    if len(subdirectoryResult) == 0:
                        # didn't find anything in the subdirectory
                        continue
                    else:
                        # found something in the subdirectory
                        return subdirectoryResult 

                # this is a file see if we can play it
                if self.shouldPlayFile(fileEntry):
                    # yes it can be played
                    return [ fileEntry ]
                else:
                    # no it can't be played
                    continue
            # we have walked off of the end of the 'files' list so return an empty list
        elif 'error' in jsonResponse:
            xbmcgui.Dialog().notification('Cinder Error:', 'Invalid: ' + fullpath, xbmcgui.NOTIFICATION_WARNING)
            pykodi.log(jsonResponse, xbmc.LOGDEBUG)
            xbmc.executebuiltin('Dialog.Close(busydialog)')
            sys.exit(1)

        return []
