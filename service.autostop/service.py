import xbmc
import time
import xbmcaddon
import xbmcgui
import xbmcplugin
from common import settings

pos = 0
file = ''
count = 0 
pacount = 0
plcount = 0

xbmc.log("Autostop addon service started." , xbmc.LOGINFO)
  
class XBMCPlayer(xbmc.Player):
    
    def __init__(self, *args):
        self.paflag = 0
        self.plflag = 0
        pass
 
    def onPlayBackStarted(self):
        file = xbmc.Player().getPlayingFile()
        self.paflag = 0
        self.plflag = 1
 
    def onPlayBackPaused(self):
        xbmc.log("Autostop playback paused" , xbmc.LOGDEBUG)
        self.paflag = 1
        self.plflag = 0
 
    def onPlayBackResumed(self):
        file = self.getPlayingFile()
        xbmc.log("Autostop playback resumed" , xbmc.LOGDEBUG)
        self.paflag = 0
        self.plflag = 1
 
    def onPlayBackEnded(self):
        xbmc.log("Autostop playback ended" , xbmc.LOGDEBUG)
        pos = 0
        self.paflag = 0
        self.plflag = 0
 
    def onPlayBackStopped(self):
        self.paflag = 0
        self.plflag = 0

             
player = XBMCPlayer()
 
monitor = xbmc.Monitor()      
 
#while True:
while not monitor.abortRequested():

    pacount += 1
    if pacount % 10 == 0:                          # Check for paused video every 10 seconds
        pastoptime = int(settings('pastop'))
        xbmc.log('Autostop pause count and stop time ' + str(pacount) + ' ' + str(pastoptime) +    \
        ' ' + str(player.paflag), xbmc.LOGDEBUG)
        if pastoptime > 0 and pacount >= pastoptime * 60 and player.paflag == 1:
            if xbmc.Player().isPlayingVideo():
                ptag = xbmc.Player().getVideoInfoTag()
                ptitle = ptag.getTitle()
            elif xbmc.Player().isPlayingAudio():
                ptag = xbmc.Player().getMusicInfoTag()
                ptitle = ptag.getTitle()                
            else:
                ptitle = "playing file"
            pos = xbmc.Player().getTime()
            xbmc.Player().stop()
            pacount = 0
            mgenlog ='Autostop stopped paused playback: ' + ptitle +     \
            ' at: ' + time.strftime("%H:%M:%S", time.gmtime(pos))
            xbmc.log(mgenlog, xbmc.LOGINFO)
            dialog = xbmcgui.Dialog()
            dialog.notification('Autostop Paused Timer', mgenlog, xbmcgui.NOTIFICATION_INFO, 5000)
            if settings('screensaver') == 'true':  #  Active screensaver if option selected
                xbmc.executebuiltin('ActivateScreensaver')
        elif player.paflag == 0:
            pacount = 0

    plcount += 1 
    if plcount % 10 == 0:                          # Check for playing video every 10 seconds
        plstoptime = int(settings('plstop'))
        xbmc.log('Autostop play count and stop time ' + str(plcount) + ' ' + str(plstoptime) +    \
        ' ' + str(player.plflag), xbmc.LOGDEBUG)
        if plstoptime > 0 and plcount >= plstoptime * 60 and player.plflag == 1:
            if xbmc.Player().isPlayingVideo():
                ptag = xbmc.Player().getVideoInfoTag()
                ptitle = ptag.getTitle()
            elif xbmc.Player().isPlayingAudio():
                ptag = xbmc.Player().getMusicInfoTag()
                ptitle = ptag.getTitle()                
            else:
                ptitle = "playing file"
            pos = xbmc.Player().getTime()
            xbmc.Player().stop()
            plcount = 0
            mgenlog ='Autostop stopped current playback: ' + ptitle +     \
            ' at: ' + time.strftime("%H:%M:%S", time.gmtime(pos))
            xbmc.log(mgenlog, xbmc.LOGINFO)
            dialog = xbmcgui.Dialog()
            dialog.notification('Autostop Sleep Timer', mgenlog, xbmcgui.NOTIFICATION_INFO, 5000)
            if settings('screensaver') == 'true':  #  Active screensaver if option selected
                xbmc.executebuiltin('ActivateScreensaver')
        elif player.plflag == 0:
            plcount = 0


    if monitor.waitForAbort(1): # Sleep/wait for abort for 1 second.
        xbmc.log("Autostop addon service stopped." , xbmc.LOGINFO)
        break # Abort was requested while waiting. Exit the while loop.


