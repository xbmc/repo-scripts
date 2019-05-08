# -*- coding: utf-8 -*-
'''
XBMC Playback Resumer
Copyright (C) 2014 BradVido/bossanova808

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''
import xbmc
import xbmcaddon
import xbmcgui
import os
import json
from time import time
from random import randint

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__kodiversion__ = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[0:4])
__language__ = __addon__.getLocalizedString
__profile__ = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode('utf-8') #addon_data folder
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

saveintervalsecs = 20 #default. Configured in settings.
resumeonstartup = False #default. Configured in sttings
autoplayrandom = False #default. Configured in settings
currentPlayingFilePath = '' #The str full path of the video file currently playing
typeOfVideo = 'unknown' #The type of video currently playing (episode, movie, musicvideo, etc.)
libraryId = -1 #The id of the video currently playing (if its in the library)
videoTypesInLibrary={"movies": True, "episodes": True, "musicvideos": True} #init as true. will become false if they are not found

# Create the addon_settings dir if not exists
if not os.path.exists(__profile__):
    os.makedirs(__profile__)

# Two files to persistenly track the last played file and the resume point
lastPlayedTrackerFilePath = os.path.join(__profile__,"lastplayed.txt")
resumePointTrackerFilePath = os.path.join(__profile__,"resumepoint.txt")

# Tag our logs with the addon name to make them easy to find..
def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )


# Helper function to get string type from settings
def getSetting(setting):
    return __addon__.getSetting(setting).strip()

# Helper function to get bool type from settings
def getSettingAsBool(setting):
    return getSetting(setting).lower() == "true"

# Check exclusion settings for filename passed as argument
def isExcluded(fullpath):

    if not fullpath:
        return True

    log("isExcluded(): Checking exclusion settings for '%s'." % fullpath)

    if (fullpath.find("pvr://") > -1) and getSettingAsBool('ExcludeLiveTV'):
        log("isExcluded(): Video is playing via Live TV, which is currently set as excluded location.")
        return True

    if (fullpath.find("http://") > -1) and getSettingAsBool('ExcludeHTTP'):
        log("isExcluded(): Video is playing via HTTP source, which is currently set as excluded location.")
        return True

    ExcludePath = getSetting('ExcludePath')
    if ExcludePath and getSettingAsBool('ExcludePathOption'):
        if (fullpath.find(ExcludePath) > -1):
            log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 1." % ExcludePath)
            return True

    ExcludePath2 = getSetting('ExcludePath2')
    if ExcludePath2 and getSettingAsBool('ExcludePathOption2'):
        if (fullpath.find(ExcludePath2) > -1):
            log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 2." % ExcludePath2)
            return True

    ExcludePath3 = getSetting('ExcludePath3')
    if ExcludePath3 and getSettingAsBool('ExcludePathOption3'):
        if (fullpath.find(ExcludePath3) > -1):
            log("isExcluded(): Video is playing from '%s', which is currently set as excluded path 3." % ExcludePath3)
            return True

    return False

# Main function - updates the resume point in the Kodi library periodically

def updateResumePoint(seconds):
    
    global currentPlayingFilePath
    global libraryId
    
    seconds = int(seconds)

    if currentPlayingFilePath == '':
        log("No valid currentPlayingFilePath found -- not setting resume point")
        return
    
    # -1 indicates that the video has stopped playing
    if seconds < 0:
        
        # check if xbmc is acually shutting down (abortRequested happens slightly after onPlayBackStopped, hence the sleep/wait/check)
        for i in range(0, 30):
            
            if xbmc.abortRequested:
                log("Since XBMC is shutting down, will save resume point")
                # xbmc is shutting down while playing a video. We want to keep the resume point.
                return
            
            if xbmc.Player().isPlaying():
                # a new video has started playing. XBMC is not shutting down
                break
            
            xbmc.sleep(100)

    # Update the resume point in the tracker file
    log("Setting custom resume seconds to %d" % seconds)
    f = open(resumePointTrackerFilePath, 'w+')
    f.write(str(seconds))
    f.close()
    
    # Update the native XBMC resume point via JSON-RPC API
    if libraryId < 0:
        log("Will not update XBMC native resume point because this file is not in the library: " + currentPlayingFilePath)        
        return 
    if (seconds == -2):
        log("Will not update XBMC native resume point because the file was stopped normally")
        return
    if seconds < 0:
        # zero indicates to JSON-RPC to remove the bookmark
        seconds = 0
        log("Setting XBMC native resume point to "+("be removed" if seconds == 0 else str(seconds)+" seconds")+" for "+typeOfVideo +" id "+ str(libraryId))
    
    # Determine the JSON-RPC setFooDetails method to use and what the library id name is based of the type of video
    method = ''
    idname = ''
    if typeOfVideo == 'episode':
        method = 'SetEpisodeDetails'
        idname = 'episodeid'
    elif typeOfVideo == 'movie':
        method = 'SetMovieDetails'
        idname = 'movieid'
    else:#music video
        method = 'SetMusicVideoDetails'
        idname = 'musicvideoid'
        
    # https://github.com/xbmc/xbmc/commit/408ceb032934b3148586500cc3ffd34169118fea
    query = {
        "jsonrpc": "2.0",
        "id": "setResumePoint",
        "method": "VideoLibrary."+method,
        "params": {
            idname: libraryId,
            "resume": {
                "position": seconds,
                #"total": 0 #Not needed: http://forum.xbmc.org/showthread.php?tid=161912&pid=1596436#pid1596436
            }
        }
    }

    log("Executing JSON-RPC: " + json.dumps(query))
    jsonResponse = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    log("VideoLibrary." + method + " response: " + json.dumps(jsonResponse))


# Persistently tracks the currently playing file (in case of crash, for possible resuming)

def updatecurrentPlayingFilePath(filepath):

    global currentPlayingFilePath
    global libraryId
    global typeOfVideo
    
    if isExcluded(filepath):
        log("Skipping excluded filepath: " + filepath)
        currentPlayingFilePath = ''
        return
    
    currentPlayingFilePath = filepath
    
    # write the full path to a file for persistant tracking
    f = open(lastPlayedTrackerFilePath, 'w+')
    f.write(filepath)
    f.close()
    log('Last played file set to: "%s"' % filepath)
    
    # check if its a library video and get the libraryId and typeOfVideo
    
    query = {
        "jsonrpc": "2.0",
        "method": "Files.GetFileDetails",
        "params": {
            "file": filepath,
            "media": "video",
            "properties": [
                "playcount",
                "runtime"
            ]
        },
        "id": "fileDetailsCheck"
    }
    
    log("Executing JSON-RPC: " + json.dumps(query))
    jsonResponse = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    log("Files.GetFileDetails response: " + json.dumps(jsonResponse))
    
    typeOfVideo = 'unknown'

    try:
        typeOfVideo = jsonResponse['result']['filedetails']['type']
    except:
        libraryId = -1
        log("Could not determine type of video; assuming video is not in XBMC's library: " + currentPlayingFilePath)        

    if typeOfVideo == 'episode' or typeOfVideo == 'movie' or typeOfVideo == 'musicvideo':
        libraryId = jsonResponse['result']['filedetails']['id']
        log("The libraryid for this " + typeOfVideo + " is " + str(libraryId))
    else:
        libraryId = -1
        log("This type of video is not supported for resume points because it is not in XBMC's library: " + typeOfVideo + ": " + currentPlayingFilePath)

# Automatically resume a video after a crash, if one was playing...

def resumeIfWasPlaying():

    global resumeonstartup

    if resumeonstartup and os.path.exists(resumePointTrackerFilePath) and os.path.exists(lastPlayedTrackerFilePath):
        
        f = open(resumePointTrackerFilePath, 'r')
        resumePoint = float(f.read())
        f.close()
        
        # neg 1 means the video wasn't playing when xbmc ended
        if resumePoint <0:
            log("Not resuming playback because nothing was playing when XBMC ended")
            return False

        f = open(lastPlayedTrackerFilePath, 'r')
        fullPath = f.read()
        f.close()

        strTimestamp = str(int(resumePoint / 60))+":"+("%02d" % (resumePoint % 60))
        
        log("Will resume playback at "+ strTimestamp+" of "+ fullPath)      
        
        xbmc.Player().play(fullPath)
        
        # wait up to 10 secs for the video to start playing befor we try to seek
        for i in range(0, 1000):
            if not xbmc.Player().isPlayingVideo() and not xbmc.abortRequested:
                xbmc.sleep(100)
            else:
                xbmc.executebuiltin('Notification(Resuming Playback At ' + strTimestamp + ',3000)')
                xbmc.Player().seekTime(resumePoint)             
                return True 

    return False

# Get a random video from the library for playback

def getRandomLibraryVideo():    

    global videoTypesInLibrary

    if not videoTypesInLibrary['episodes'] and not videoTypesInLibrary['movies'] and not not videoTypesInLibrary['musicvideos']:
        log("No episodes, movies, or music videos exist in the XBMC library. Cannot autoplay a random video")
        return
    
    rint = randint(0,2)
    if rint == 0:
        resultType = 'episodes'
        method = "GetEpisodes"      
    elif rint == 1:
        resultType = 'movies'
        method = "GetMovies"
    elif rint == 2:
        resultType = 'musicvideos'
        method = "GetMusicVideos"
        
    if not videoTypesInLibrary[resultType]:
        return getRandomLibraryVideo() # get a different one
        
    log("Getting next random video from " + resultType)
    
    query = {
        "jsonrpc": "2.0",
        "id": "randomLibraryVideo",
        "method": "VideoLibrary."+method,
        "params": {
            "limits": {
                "end": 1
            },
            "sort": {
                "method": "random"
            },
            "properties": [
                "file"
            ]
        }
    }
    
    log("Executing JSON-RPC: " + json.dumps(query))
    jsonResponse = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    log("VideoLibrary." + method + " response: " + json.dumps(jsonResponse))
    
    # found a video
    if jsonResponse['result']['limits']['total'] > 0: 
        videoTypesInLibrary[resultType] = True
        return jsonResponse['result'][resultType][0]['file']
    # no videos of this type
    else: 
        log("There are no "+ resultType +" in the library")
        videoTypesInLibrary[resultType] = False
        return getRandomLibraryVideo()


# Play a random video if the setting is enabled

def autoplayrandomIfEnabled():

    if autoplayrandom:

        log("autoplayrandom is enabled, so will play a new random video now")       

        videoPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

        #make sure the current playlist has finished completely
        if not xbmc.Player().isPlayingVideo() and (videoPlaylist.getposition() == -1 or videoPlaylist.getposition() == videoPlaylist.size()):
            fullpath = getRandomLibraryVideo()
            log("Auto-playing next random video because nothing is playing and playlist is empty: " + fullpath)         
            xbmc.Player().play(fullpath)
            xbmc.executebuiltin('Notification(Auto-playing random video,' + fullpath + ',3000)')
        else:
            log("Not autoplaying a new random video because we are not at the end of the playlist or something is already playing: currentPosition="+str(videoPlaylist.getposition())+", size=" + str(videoPlaylist.size()))

# Load the addon setting into our globals

def loadSettings():

    global saveintervalsecs
    global resumeonstartup
    global autoplayrandom

    saveintervalsecs = int(float(__addon__.getSetting("saveintervalsecs")))
    resumeonstartup = getSettingAsBool("resumeonstartup")
    autoplayrandom = getSettingAsBool("autoplayrandom")
    
    log('Settings loaded: saveintervalsecs=%d, resumeonstartup=%s, autoplayrandom=%s' % (saveintervalsecs, str(resumeonstartup), str(autoplayrandom)))

# Main function to update the resume point periodically...
def handlePlayback():

    global saveintervalsecs

    log("Playback started")

    if not xbmc.Player().isPlayingVideo():
        log("Not playing a video - skipping: " + xbmc.Player().getPlayingFile())
        return

    xbmc.sleep(1500) # give it a bit to start playing and let the stopped method finish
    
    updatecurrentPlayingFilePath(xbmc.Player().getPlayingFile())    
    
    while xbmc.Player().isPlaying() and not xbmc.abortRequested:
        
        updateResumePoint(xbmc.Player().getTime())
        
        for i in range(0, saveintervalsecs):
            # Shutting down or not playing video anymore...stop handling playback
            if(xbmc.abortRequested or not xbmc.Player().isPlaying()):
                return
            # Otherwise sleep 1 second & loop           
            xbmc.sleep(1000)


# Kodi Player Event Handling

class MyPlayer( xbmc.Player ):
    
    def __init__( self, *args ):
        xbmc.Player.__init__( self )
        log('MyPlayer - init')

    def onPlayBackPaused( self ):
        global g_pausedTime
        g_pausedTime = time()
        log('Paused. Time: %d' % g_pausedTime)

    def onPlayBackEnded( self ):#video ended normally (user didn't stop it)
        log("Playback ended")
        updateResumePoint(-1)
        autoplayrandomIfEnabled()

    def onPlayBackStopped( self ):
        log("Playback stopped")
        updateResumePoint(-2)
        #autoplayrandomIfEnabled() #if user stopped video, they probably don't want a new random one to start

    def onPlayBackSeek( self, time, seekOffset ):
        log("Playback seeked (time)")
        updateResumePoint(xbmc.Player().getTime())

    def onPlayBackSeekChapter( self, chapter ):
        log("Playback seeked (chapter)")
        updateResumePoint(xbmc.Player().getTime())

    # These two events have changed from Kodi Leia - in general, post Leia, we want to wait onAVStarted.  
    # Before Leia we use onPlayBackStarted.
    
    def onPlayBackStarted( self ):
        if __kodiversion__ < 17.9:
            handlePlayback()

    def onAVStarted( self ):
        if __kodiversion__ >= 17.9:
            handlePlayback()

# Kodi Event Handling

class MyMonitor( xbmc.Monitor ):

    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        log('MyMonitor - init')

    def onSettingsChanged( self ):
        loadSettings()

    def onAbortRequested(self):
        log("Abort Requested!")

# MAIN - get this thing going...

log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

xbmc_monitor = MyMonitor()
loadSettings()
player_monitor = MyPlayer()

resumedPlayback = resumeIfWasPlaying()
if not resumedPlayback and not xbmc.Player().isPlayingVideo():
    autoplayrandomIfEnabled()

while not xbmc.abortRequested:
    xbmc.sleep(100)

