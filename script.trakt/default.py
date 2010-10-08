import sys
import os
import xbmc
import xbmcaddon
import xbmcgui
import string
import webbrowser
import time
import ConfigParser
import string

###General vars
__scriptname__ = "trakt"
__author__ = "Sean Rudford"
__url__ = "http://trakt.tv/"
# __svn_url__ = ""
# __credits__ = ""
__version__ = "0.0.4"
__XBMC_Revision__ = ""

def addPadding(number):
    if len(number) == 1:
        number = '0' + number
    return number

def CheckAndSubmit(Manual=False):
    sType = ""
    if xbmc.Player().isPlayingVideo():
        Debug('Video found playing',False)
        bLibraryExcluded = False
        bRatingExcluded = False
        bPathExcluded = False
        bExcluded = False
        short = ""
        title = ""
        imdburl = ""
        global VideoThreshold
        global lasttitle
        global lastUpdate
        
        pauseCheck = xbmc.Player().getTime()
        time.sleep(1)
        if xbmc.Player().isPlayingVideo():
            if (xbmc.Player().getTime() == pauseCheck):
                Debug('Video is currently paused', False)
                return
        else:
            Debug('Video ended during pause check', False)
            return
        
        if (xbmc.getInfoLabel("VideoPlayer.Year") == ""):
            Debug('Video is not in library', False)
            bLibraryExcluded = True
        if ((xbmc.getInfoLabel("VideoPlayer.mpaa") == "XXX")):
            Debug('Video is with XXX mpaa rating', False)
            bRatingExcluded = True
        if ((__settings__.getSetting( "ExcludePath" ) != "") and (__settings__.getSetting( "ExcludePathOption" ) == 'true')):
            currentPath = xbmc.Player().getPlayingFile()
            if (currentPath.find(__settings__.getSetting( "ExcludePath" )) > -1):
                Debug('Video is located in excluded path', False)
                bPathExcluded = True
        if ((__settings__.getSetting( "ExcludePath2" ) != "") and (__settings__.getSetting( "ExcludePathOption2" ) == 'true')):
            currentPath = xbmc.Player().getPlayingFile()
            if (currentPath.find(__settings__.getSetting( "ExcludePath2" )) > -1):
                Debug('Video is located in excluded path 2', False)
                bPathExcluded = True
        if ((__settings__.getSetting( "ExcludePath3" ) != "") and (__settings__.getSetting( "ExcludePathOption3" ) == 'true')):
            currentPath = xbmc.Player().getPlayingFile()
            if (currentPath.find(__settings__.getSetting( "ExcludePath3" )) > -1):
                Debug('Video is located in excluded path 3', False)
                bPathExcluded = True                     
        
        if len(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")) >= 1: # TvShow
            sType = "TVShow"   
            Debug("Found TV Show", False)     
            # format: title, year, season, episode
            title = (unicode(xbmc.getInfoLabel("VideoPlayer.TvShowTitle"), 'utf-8') +
                    ',' + unicode(xbmc.getInfoLabel("VideoPlayer.Year"), 'utf-8') +
                    ',' + unicode(addPadding(xbmc.getInfoLabel("VideoPlayer.Season")), 'utf-8') +
                    ',' + unicode(addPadding(xbmc.getInfoLabel("VideoPlayer.Episode")), 'utf-8'))
            # title = title.replace('%EPISODENAME%', unicode(xbmc.getInfoLabel("VideoPlayer.Title"), 'utf-8'))
            # title = title.replace('%EPISODENUMBER%', unicode(xbmc.getInfoLabel("VideoPlayer.Episode"), 'utf-8'))
            # title = title.replace('%EPISODENUMBER_PADDED%', unicode(addPadding(xbmc.getInfoLabel("VideoPlayer.Episode")), 'utf-8'))            
            # title = title.replace('%SEASON%', , 'utf-8'))
            # title = title.replace('%SEASON_PADDED%', unicode(addPadding(xbmc.getInfoLabel("VideoPlayer.Season")), 'utf-8'))

        elif len(xbmc.getInfoLabel("VideoPlayer.Title")) >= 1: #Movie
            sType = "Movie"
            Debug("Found Movie", False)
            # format: title, year
            title = unicode(xbmc.getInfoLabel("VideoPlayer.Title"), 'utf-8') + ',' + unicode(xbmc.getInfoLabel("VideoPlayer.Year"), 'utf-8')

            if (xbmc.getInfoLabel("VideoPlayer.Year") != ""):
                try:
                    query = "select case when not movie.c09 is null then movie.c09 else 'NOTFOUND' end as [MovieID] from movie where movie.c00 = '" + unicode(xbmc.getInfoLabel("VideoPlayer.Title")) + "' limit 1"
                    res = xbmc.executehttpapi("queryvideodatabase(" + query + ")")
                    movieid = re.findall('>(.*?)<',res) # find it
                    if len(movieid[1].strip()) >= 1:
                        imdburl = "http://www.imdb.com/title/" + str(movieid[1].strip())
                except:        
                    imdburl = ""
                
            #don't submit if not in library
            if (xbmc.getInfoLabel("VideoPlayer.Year") == ""):
                title = ""

        if (bLibraryExcluded or bPathExcluded or bRatingExcluded):
            bExcluded = True
            Debug("Excluded", False)
        
        Debug("Title: " + title)
        
        if ((title != "" and lasttitle != title)  and not bExcluded):
            iPercComp = CalcPercentageRemaining(xbmc.getInfoLabel("VideoPlayer.Time"), xbmc.getInfoLabel("VideoPlayer.Duration"))
            if (iPercComp > (float(VideoThreshold) / 100)):
                Debug('Title: ' + title + ', sending watched status, current percentage: ' + str(iPercComp), True)
                SendUpdate(title, sType, "watched")
                lasttitle = title
            elif (time.time() - lastUpdate >= 900):
                Debug('Title: ' + title + ', sending watching status, current percentage: ' + str(iPercComp), True)
                SendUpdate(title, sType, "watching")
                lastUpdate = time.time();
    
    else:
        Debug('Resetting last update timestamp')
        lastUpdate = 0
    
###Path handling
BASE_PATH = xbmc.translatePath( os.getcwd() )
RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources' ) )
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )
LANGUAGE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'language' ) )
MEDIA_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'skins' ) )
sys.path.append (BASE_RESOURCE_PATH)
sys.path.append (LANGUAGE_RESOURCE_PATH)

from utilities import *
    
Debug('----------- ' + __scriptname__ + ' by ' + __author__ + ', version ' + __version__ + ' -----------', False)

###Settings related parsing
__settings__ = xbmcaddon.Addon(id='script.trakt')
__language__ = __settings__.getLocalizedString

# __language__ = xbmc.Language( os.getcwd() ).getLocalizedString
_ = sys.modules[ "__main__" ].__language__
# __settings__ = xbmc.Settings( path=os.getcwd() )

###Vars and initial load
bRun = True #Enter idle state waiting to submit
bStartup = False
bShortcut = False
bUsername = False
bPassword = False
lasttitle = ""
lastUpdate = 0

bAutoStart = False
bRunBackground = False
bAutoSubmitVideo = False
VideoThreshold = 0

if (__settings__.getSetting( "AutoStart" ) == 'true'): bAutoStart = True
if (__settings__.getSetting( "RunBackground" ) == 'true'): bRunBackground = True
if (__settings__.getSetting( "AutoSubmitVideo" ) == 'true'): bAutoSubmitVideo = True

bUsername = __settings__.getSetting( "Username" )
bPassword = __settings__.getSetting( "Password" )

VideoThreshold = int(__settings__.getSetting( "VideoThreshold" ))
if (VideoThreshold == 0): VideoThreshold = 75
elif (VideoThreshold == 1): VideoThreshold = 95

bFirstRun = CheckIfFirstRun()

try:
    count = len(sys.argv) - 1
    if (sys.argv[1] == '-startup'):
        bStartup = True			
except:
    pass

Debug( '::Settings::', True)
Debug( 'AutoStart: ' + str(bAutoStart), True)
Debug( 'RunBackground: ' + str(bRunBackground), True)
Debug( 'Username: ' + bUsername, True)
Debug( 'Password: ' + bPassword, True)
Debug( 'FirstRun: ' + str(bFirstRun), True)
Debug( 'AutoSubmitVideo:' + str(bAutoSubmitVideo), True)
Debug( 'VideoThreshold: ' + str(VideoThreshold), True)
Debug( 'Startup: ' + str(bStartup), True)
Debug( '::Settings::', True)

###Initial checks

#New Version
# if ((CheckVersion() != __version__ ) and (bShowWhatsNew)):
#     try:
#         import urllib
#         usock = urllib.urlopen("http://xbtweet.googlecode.com/svn/trunk/xbTweet/whatsnew" + __version__ + ".txt")
#         message = usock.read()
#         usock.close()
# 
#         import gui_welcome
#         ui = gui_welcome.GUI( "script-xbTweet-Generic.xml" , os.getcwd(), "Default")
#         ui.setParams ("message",  __language__(30043), message, 0)
#         ui.doModal()
#         del ui
# 
#         #bRun = True
#         WriteVersion(__version__)
#     except:
#         Debug('Failed to validate if new version', False)

###Main logic
if (not xbmc.getCondVisibility('videoplayer.isfullscreen') and not bShortcut and not bStartup):
    Debug(  'Pressed in scripts menu', False)        
    SetAutoStart(bAutoStart)

#Startup Execution 
if ((bStartup and bAutoStart) or bRun):
    Debug(  'Entering idle state, waiting for media playing...', False)

    xbmc.executebuiltin('Notification(Trakt,' + __language__(45050).encode( "utf-8", "ignore" ) + ',3000)')

    while 1:
        #If Set To AutoSubmit
        if (bAutoSubmitVideo):
            CheckAndSubmit()

        time.sleep(15)

Debug( 'Exiting...', False)
