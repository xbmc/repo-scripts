import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from common import settings, playCount, sleepNotify, stopPlayback, translate

pos = 0
count = 0 
pacount = 0
plcount = 0
extime = 0
padjust = settings('padjust')
plstoptime = int(settings('plstop'))
plnotify = int(settings('plnotify'))
plextend = int(settings('plextend'))
settings('extime', '0')
asevlog = settings('asevlog')
settings('notifyset', 'no')
settings('varextnotify', 'no')

xbmc.log("Autostop addon service started." , xbmc.LOGINFO)
  
class XBMCPlayer(xbmc.Player):
    
    def __init__(self, *args):
        self.paflag = 0
        self.plflag = 0
        pass
      
    def onPlayBackStarted(self):
        self.paflag = 0
        self.plflag = 1
 
    def onPlayBackPaused(self):
        xbmc.log("Autostop playback paused" , xbmc.LOGDEBUG)
        self.paflag = 1
        self.plflag = 0
 
    def onPlayBackResumed(self):
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
 
while not monitor.abortRequested():

    pacount += 1
    if pacount % 10 == 0:                            # Check for paused video every 10 seconds
        try:
            pastoptime = int(settings('pastop'))
            xbmc.log('Autostop pause count and stop time ' + str(pacount) + ' ' + str(pastoptime) +    \
            ' ' + str(player.paflag), xbmc.LOGDEBUG)
            if pastoptime > 0 and pacount >= pastoptime * 60 and player.paflag == 1:
                pos = xbmc.Player().getTime()
                logmsg = translate(30319)
                notifymsg = translate(30317)
                pacount = 0
                stopPlayback(notifymsg, logmsg)      # Stop playback if paused too long
            elif player.paflag == 0:
                pacount = 0
        except:
            xbmc.log('Autostop pause count and stop time exception error' + str(pacount) + ' ' + \
            str(pastoptime) + ' ' + str(player.paflag), xbmc.LOGINFO)
                       

    plcount = playCount(plcount, padjust, player.plflag, player.paflag, asevlog)
    sleepNotify(plcount, plstoptime, player.plflag, plnotify, plextend, asevlog, player.paflag) 
    if plcount % 10 == 0:                            # Check for playing video every 10 seconds
        try:
            plstoptime = int(settings('plstop'))
            padjust = settings('padjust')
            plnotify = int(settings('plnotify'))
            plextend = int(settings('plextend'))
            extime = float(settings('extime'))
            asevlog = settings('asevlog')
            totalstoptime = plstoptime + extime
            if asevlog == 'true':
                xbmc.log('Autostop play count and stop time ' + str(plcount) + ' ' +         \
                str(plstoptime) + ' ' + str(player.plflag), xbmc.LOGINFO)
            if plstoptime > 0 and plcount >= totalstoptime * 60 and (player.plflag > 0 or    \
            (player.plflag == 0 and player.paflag == 1)):
                logmsg = translate(30320)
                notifymsg = translate(30310)
                plcount = 0
                stopPlayback(notifymsg, logmsg)      # Stop playback if playing too long
            if plstoptime == 0:                      # Don't increment plcount if sleep setting is 0
                plcount = 0
            #xbmc.log("Autostop plstoptime." + str(plstoptime) + ' ' + str(plcount), xbmc.LOGINFO)
        except:
            xbmc.log('Autostop play count and stop time exception error' + str(pacount) + ' ' \
            + str(pastoptime) + ' ' + str(player.paflag), xbmc.LOGINFO)
                 

    if monitor.waitForAbort(1): # Sleep/wait for abort for 1 second.
        xbmc.log("Autostop addon service stopped." , xbmc.LOGINFO)
        break # Abort was requested while waiting. Exit the while loop.


