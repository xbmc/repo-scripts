import xbmcaddon
import xbmc
import xbmcgui
import os
import time

cwd = xbmcaddon.Addon(id='service.nextup.notification').getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(cwd, 'resources', 'lib'))
sys.path.append(BASE_RESOURCE_PATH)

import Utils as utils
from Player import Player
from ClientInformation import ClientInformation
from ga_client import GoogleAnalytics


class Service():
    clientInfo = ClientInformation()
    addonName = clientInfo.getAddonName()
    WINDOW = xbmcgui.Window(10000)
    lastMetricPing = time.time()

    def __init__(self, *args):
        addonName = self.addonName

        self.logMsg("Starting NextUp Service", 0)
        self.logMsg("========  START %s  ========" % addonName, 0)
        self.logMsg("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.logMsg("%s Version: %s" % (addonName, self.clientInfo.getVersion()), 0)
        self.logMsg("Platform: %s" % (self.clientInfo.getPlatform()), 0)


    def logMsg(self, msg, lvl=1):
        className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, className), str(msg), int(lvl))

    def ServiceEntryPoint(self):
        player = Player()
        monitor = xbmc.Monitor()
        
        lastFile = None
        lastUnwatchedFile = None

        ga = GoogleAnalytics()
        ga.sendEventData("Application", "Startup")
        try:
            ga.sendEventData("Version", "OS", self.clientInfo.getPlatform())
            ga.sendEventData("PlayMode", "Mode", self.clientInfo.getPlayMode())
        except Exception:
            pass

        while not monitor.abortRequested():
            # check every 5 sec
            if monitor.waitForAbort(5):
                # Abort was requested while waiting. We should exit
                break
            if xbmc.Player().isPlaying():
                try:
                    # ping metrics server to keep sessions alive while playing
                    # ping every 5 min
                    timeSinceLastPing = time.time() - self.lastMetricPing
                    if(timeSinceLastPing > 300):
                        self.lastMetricPing = time.time()
                        ga.sendEventData("PlayAction", "PlayPing")

                    playTime = xbmc.Player().getTime()

                    totalTime = xbmc.Player().getTotalTime()

                    currentFile = xbmc.Player().getPlayingFile()

                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    notificationtime = addonSettings.getSetting("autoPlaySeasonTime")
                    nextUpDisabled = addonSettings.getSetting("disableNextUp") == "true"
                    randomunwatchedtime = addonSettings.getSetting("displayRandomUnwatchedTime")
                    displayrandomunwatched = addonSettings.getSetting("displayRandomUnwatched") == "true"
                    showpostplay = addonSettings.getSetting("showPostPlay") == "true"


                    if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True" and not nextUpDisabled and not showpostplay:
                            if (totalTime - playTime <= int(notificationtime) and (
                                    lastFile is None or lastFile != currentFile)) and totalTime != 0:
                                lastFile = currentFile
                                self.logMsg("Calling autoplayback totaltime - playtime is %s" % (totalTime - playTime), 2)
                                player.autoPlayPlayback()
                                self.logMsg("Netflix style autoplay succeeded.", 2)
                            self.logMsg("playtime is %s" % (int(playTime)), 2)
                            self.logMsg("randomunwatchedtime is %s" % (int(randomunwatchedtime)), 2)
                            if (int(playTime) >= int(randomunwatchedtime)) and (int(playTime) < int(int(randomunwatchedtime)+100))  and displayrandomunwatched and (
                                            lastUnwatchedFile is None or lastUnwatchedFile != currentFile):
                                self.logMsg("Calling display unwatched", 2)
                                lastUnwatchedFile = currentFile
                                player.displayRandomUnwatched()
                    elif xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True" and not nextUpDisabled and showpostplay:
                            if (totalTime - playTime <= 10) and totalTime != 0:
                                self.logMsg("Calling post playback", 2)
                                player.postPlayPlayback()
                            if (int(playTime) >= int(randomunwatchedtime)) and (int(playTime) < int(int(randomunwatchedtime)+100))  and displayrandomunwatched and (
                                            lastUnwatchedFile is None or lastUnwatchedFile != currentFile):
                                self.logMsg("Calling display unwatched", 2)
                                lastUnwatchedFile = currentFile
                                player.displayRandomUnwatched()


                except Exception as e:
                    self.logMsg("Exception in Playback Monitor Service: %s" % e)
                    if not (hasattr(e, 'quiet') and e.quiet):
                        ga = GoogleAnalytics()
                        errStrings = ga.formatException()
                        ga.sendEventData("Exception", errStrings[0], errStrings[1])
                    pass

        self.logMsg("======== STOP %s ========" % self.addonName, 0)

# start the service
Service().ServiceEntryPoint()
