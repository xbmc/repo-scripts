from __future__ import division
import xbmc, xbmcgui, xbmcaddon

__addon__           = xbmcaddon.Addon()
__addonid__         = __addon__.getAddonInfo('id')
__addonname__       = __addon__.getAddonInfo('name')
__addonauthor__     = __addon__.getAddonInfo('author')
__addonpath__       = __addon__.getAddonInfo('path')
__addonversion__    = __addon__.getAddonInfo('version')
__icon__            = __addon__.getAddonInfo('icon')
__language__        = __addon__.getLocalizedString


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")

    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def executeJSONRPC(jsonStr):
    import json

    response = json.loads(xbmc.executeJSONRPC(jsonStr))
    response = response['result'] if 'result' in response else response

    return response

class Main:
    def __init__(self):
        # catch: addon settings change and Screensaver start
        # ...also call first time _getSettings()
        self.serviceMonitor = serviceMonitor(self._getSettings(), self._onScreensaverAction)

        if self.startupPartyMode and self._viewCountdown():
            self.runPartyMode()

        while not xbmc.abortRequested:
            xbmc.sleep(1000)

    def _getSettings(self):
        log('reading settings')

        self.startupPartyMode                           = __addon__.getSetting('startup-partymode') == 'true'
        self.delayStartupPartyMode                      = int(__addon__.getSetting('delay-startup-partymode'))
        self.startOnScreensaverPartyMode                = __addon__.getSetting('start-on-screensaver-partymode') == 'true'
        self.avoidOnPauseStartOnScreensaverPartyMode    = __addon__.getSetting('avoid-on-pause-start-on-screensaver-partymode') == 'true'
        self.startupPlaylist                            = __addon__.getSetting('startup-playlist') == 'true'
        self.startupPlaylistPartymode                   = __addon__.getSetting('startup-playlist-partymode') == 'true'
        self.startupPlaylistPath                        = xbmc.getInfoLabel( "Skin.String(Startup.Playlist.Path)" )
        self.startupFavourites                          = __addon__.getSetting('startup-favourites') == 'true'
        self.startupFavouritesPath                      = xbmc.getInfoLabel('Skin.String(Startup.Favourites.Path)')

        self.visualisationPartymode                     = __addon__.getSetting('visualisation-partymode') == 'true'
        self.delayVisualisationPartyMode                = int(__addon__.getSetting('delay-visualisation-partymode'))
        
        self.volumePartyMode                            = __addon__.getSetting('volume-partymode') == 'true'
        self.volumeLevelPartyMode                       = int(__addon__.getSetting('volume-level-partymode'))

        self.playbackRandom                             = int(__addon__.getSetting('playback-random'))
        self.playbackRepeat                             = int(__addon__.getSetting('playback-repeat'))

    def runPartyMode(self):
        if self.volumePartyMode:
            executeJSONRPC('{{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {{ "volume": {0}}}, "id": 1}}'.format(self.volumeLevelPartyMode))

        if self.startupPlaylist:

            log('Start Playlist: ' + self.startupPlaylistPath)

            if self.startupPlaylistPartymode:
                xbmc.executebuiltin("XBMC.PlayerControl(PartyMode(" + self.startupPlaylistPath + ")")
            else:
                xbmc.executebuiltin("XBMC.PlayMedia(" + self.startupPlaylistPath + ")")

        elif self.startupFavourites:

            log('Start Favourites: ' + self.startupFavouritesPath)

            xbmc.executebuiltin(self.startupFavouritesPath)

        else:

            log('Start PartyMode')

            xbmc.executebuiltin("XBMC.PlayerControl(PartyMode)")

        if self.playbackRandom == 1:
            log('Setting Random to Off')
            xbmc.executebuiltin("XBMC.PlayerControl(RandomOff)")
        elif self.playbackRandom == 2:
            log('Setting Random to On')
            xbmc.executebuiltin("XBMC.PlayerControl(RandomOn)")

        if self.playbackRepeat == 1:
            log('Setting Repeat to Off')
            xbmc.executebuiltin("XBMC.PlayerControl(RepeatOff)")
        elif self.playbackRepeat == 2:
            log('Setting Repeat to One')
            xbmc.executebuiltin("XBMC.PlayerControl(RepeatOne)")
        elif self.playbackRepeat == 3:
            log('Setting Repeat to All')
            xbmc.executebuiltin("XBMC.PlayerControl(RepeatAll)")

        self.activateVisualisation()


    def activateVisualisation(self):
        if self.visualisationPartymode:

            xbmc.sleep(self.delayVisualisationPartyMode * 1000)

            log('Activate Visualisation')

            # if user have not stopped party mode in meantime
            if xbmc.Player().isPlaying():
                xbmc.executebuiltin("XBMC.ActivateWindow(visualisation)")


    def _onScreensaverAction(self):
        if self.startOnScreensaverPartyMode:

            # if something is in pause and avoidOnPauseStartOnScreensaverPartyMode == true
            if self.avoidOnPauseStartOnScreensaverPartyMode and xbmc.Player().isPlaying():
                log('Avoid PartyMode on Screensaver because something is paused')

            else:
                xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(30100), 6000, __icon__)).encode('utf-8', 'ignore'))

                self.runPartyMode()

    def _viewCountdown(self):
        conutdownDlg = xbmcgui.DialogProgress()
        if self.startupPlaylist:
            msg = 30103
        elif self.startupFavourites:
            msg = 30104
        else:
            msg = 30102
        conutdownDlg.create( __language__(30101), __language__(msg) % self.delayStartupPartyMode)

        finished = True
        countdownGap = 100

        time = 0
        startDelayPartyModeSeconds = self.delayStartupPartyMode * 1000

        while time < startDelayPartyModeSeconds:

            percent = int((time / startDelayPartyModeSeconds) * 100)

            seconds = str((startDelayPartyModeSeconds - time) / 1000) + ' seconds'

            conutdownDlg.update(percent, '', '', seconds)

            xbmc.sleep(countdownGap)
            time += countdownGap

            if conutdownDlg.iscanceled():
                finished = False
                break

        conutdownDlg.close()

        return finished

class serviceMonitor(xbmc.Monitor):
    def __init__(self, onSettingsChangedAction=None, onScreensaverActivatedAction=None):
        xbmc.Monitor.__init__(self)

        self.onSettingsChangedAction = onSettingsChangedAction
        self.onScreensaverActivatedAction = onScreensaverActivatedAction

    def onSettingsChanged(self):
        log('onSettingsChanged')

        if self.onSettingsChangedAction: self.onSettingsChangedAction()

    def onScreensaverActivated(self):
        log('onScreensaverActivated')

        if self.onScreensaverActivatedAction: self.onScreensaverActivatedAction()

    def setOnSettingsChangedAction(self, action):
        self.onSettingsChangedAction = action

    def setOnScreensaverActivatedAction(self, action):
        self.onScreensaverActivatedAction = action

if __name__ == "__main__":
    log('service version %s started' % __addonversion__)

    Main()
