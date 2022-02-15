import xbmc, xbmcaddon, xbmcgui
from threading import Timer
from plexapi.server import PlexServer
from lib.definitions import *
import pprint
import time

def closeDialog():
    global Dialog
    global timer
    global running
    global Ran
    global default_timeout
    Dialog.close()
    timer.cancel()
    Ran = True
    running = False
    timer = Timer(default_timeout, closeDialog)

def onPlay():
    xbmc.log("PLAY========***************",xbmc.LOGINFO)
    global Ran
    global introFound
    global introStartTime
    global introEndTime
    Ran = False
    introFound = False
    myPlayer = xbmc.Player()  # make Player() a single call.
    while not myPlayer.isPlayingVideo():
        time.sleep(1)
    if myPlayer.isPlayingVideo():
        season_number = myPlayer.getVideoInfoTag().getSeason()
        episode_number = myPlayer.getVideoInfoTag().getEpisode()
        show = myPlayer.getVideoInfoTag().getTVShowTitle()
        baseurl = xbmcaddon.Addon().getSettingString("plex_base_url")
        token = xbmcaddon.Addon().getSettingString("auth_token")
        plex = PlexServer(baseurl, token)
        shows = plex.library.section('TV Shows')
        show = shows.search(show)[0]
        episode = show.episode(None, season_number, episode_number)
        for marker in episode.markers:
            if (marker.type == "intro"):
                introFound = True
                introStartTime = marker.start / 1000
                introEndTime = marker.end / 1000

def monitor():
    monitor = xbmc.Monitor()
    global introFound
    global introStartTime
    global introEndTime
    global Ran
    global Dialog
    global running
    global timer
    global default_timeout
    Dialog = CustomDialog('script-dialog.xml', addonPath)
    while not monitor.abortRequested():
        # check every 5 sec
        if monitor.waitForAbort(3):
            # Abort was requested while waiting. We should exit
            break

        if xbmc.Player().isPlaying():
            if introFound:
                if xbmc.Player().getTime() > introStartTime and xbmc.Player().getTime() < introEndTime:
                    if not running and not Ran:
                        timeout = introEndTime - xbmc.Player().getTime()
                        default_timeout
                        if timeout > default_timeout:
                            timeout = default_timeout
                        timer = Timer(timeout, closeDialog)
                        timer.start()
                        Dialog.show()
                        running = True

def onSeek():
    global Ran
    Ran = False

timer = Timer(default_timeout, closeDialog)

class CustomDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, xmlFile, resourcePath):
        None

    def onInit(self):
        instuction = ''

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
            self.close()

    def onControl(self, control):
        pass

    def onFocus(self, control):
        pass

    def onClick(self, control):
        global introEndTime
        if control == OK_BUTTON:
            xbmc.Player().seekTime(int(introEndTime))

        if control in [OK_BUTTON, NEW_BUTTON, DISABLE_BUTTON]:
            self.close()
