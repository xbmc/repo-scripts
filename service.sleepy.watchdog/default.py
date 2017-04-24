# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import traceback
import re
import time, datetime
import xbmc, xbmcgui, xbmcaddon

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('id')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__iconDefault__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'media', 'pawprint.png')
__iconError__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'media', 'pawprint_red.png')

LANGOFFSET = 32130

def traceError(err, exc_tb):
    while exc_tb:
        tb = traceback.format_tb(exc_tb)
        notifyLog('%s' % err, xbmc.LOGERROR)
        notifyLog('in module: %s' % (sys.argv[0].strip() or '<not defined>'), xbmc.LOGERROR)
        notifyLog('at line:   %s' % traceback.tb_lineno(exc_tb), xbmc.LOGERROR)
        notifyLog('in file:   %s' % tb[0].split(",")[0].strip()[6:-1],xbmc.LOGERROR)
        exc_tb = exc_tb.tb_next

def notifyLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (__addonname__, message.encode('utf-8')), level)

def notifyUser(message, icon=__iconDefault__, time=3000):
    xbmcgui.Dialog().notification(__LS__(32100), message.encode('utf-8'), icon, time)

class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.SettingsChanged = False

    def onSettingsChanged(self):
        self.SettingsChanged = True


    @classmethod
    def onNotification(cls, sender, method, data):
        notifyLog('Notification triggered')
        notifyLog('sender: %s' % (sender))
        notifyLog('method: %s' % (method))
        notifyLog('data:   %s' % (data))

class SleepyWatchdog(XBMCMonitor):

    def __init__(self):

        self.currframe = 0

        XBMCMonitor.__init__(self)
        self.getWDSettings()

    def getWDSettings(self):

        self.notifyUser = True if __addon__.getSetting('showPopup').upper() == 'TRUE' else False
        self.notificationTime = int(re.match('\d+', __addon__.getSetting('notificationTime')).group())
        self.sendCEC = True if __addon__.getSetting('sendCEC').upper() == 'TRUE' else False

        self.timeframe = False if __addon__.getSetting('timeframe') == '0' else True

        self.act_start = int(datetime.timedelta(hours=int(__addon__.getSetting('start'))).total_seconds())
        self.act_stop = int(datetime.timedelta(hours=int(__addon__.getSetting('stop'))).total_seconds())
        if self.act_stop < self.act_start: self.act_stop += 86400

        self.maxIdleTime = int(re.match('\d+', __addon__.getSetting('maxIdleTime')).group())*60
        self.action = int(__addon__.getSetting('action')) + LANGOFFSET
        self.jumpMainMenu = True if __addon__.getSetting('mainmenu').upper() == 'TRUE' else False
        self.keepAlive = True if __addon__.getSetting('keepalive').upper() == 'TRUE' else False
        self.addon_id = __addon__.getSetting('addon_id')

        # following commented code are preparations for actions within an alternate timeframe,
        # don't shure if I ever implement this...
        """
        # get alternate timeframe settings

        self.use_alternate_frame = True if (__addon__.getSetting('enableAltAction').upper() == 'TRUE' and self.timeframe) else False
        self.alternate_maxIdleTime = int(re.match('\d+', __addon__.getSetting('altMaxIdleTime')).group())*60
        self.alternate_action = int(__addon__.getSetting('altAction')) + LANGOFFSET
        self.alternate_jumpMainMenu = True if __addon__.getSetting('altMainmenu').upper() == 'TRUE' else False
        self.alternate_keepAlive = True if __addon__.getSetting('altKeepalive').upper() == 'TRUE' else False
        self.alternate_addon_id = __addon__.getSetting('altAddon_id')
        """

        self.testConfig = True if __addon__.getSetting('testConfig').upper() == 'TRUE' else False

        if (self.act_stop - self.act_start) <= self.maxIdleTime: xbmcgui.Dialog().ok(__LS__(32100), __LS__(32116))

        self.SettingsChanged = False

        notifyLog('settings (re)loaded...')
        notifyLog('notify user:              %s' % (self.notifyUser))
        notifyLog('Duration of notification: %s' % (self.notificationTime))
        notifyLog('send CEC:                 %s' % (self.sendCEC))
        notifyLog('Time frame:               %s' % (self.timeframe))
        notifyLog('Activity start:           %s' % (self.act_start))
        notifyLog('Activity stop:            %s' % (self.act_stop))
        notifyLog('max. idle time:           %s' % (self.maxIdleTime))
        notifyLog('Action:                   %s' % (self.action))
        notifyLog('Jump to main menue:       %s' % (self.jumpMainMenu))
        notifyLog('keep alive:               %s' % (self.keepAlive))
        notifyLog('run addon:                %s' % (self.addon_id))

        # following commented code are preparations for actions within an alternate timeframe,
        # don't shure if I ever implement this...
        """
        notifyLog('use alternate time frame: %s' % (self.use_alternate_frame))
        notifyLog('alt. max. idle time:      %s' % (self.alternate_maxIdleTime))
        notifyLog('alternate action:         %s' % (self.alternate_action))
        notifyLog('Jump to main menu:        %s' % (self.alternate_jumpMainMenu))
        notifyLog('keep alive:               %s' % (self.alternate_keepAlive))
        notifyLog('run addon:                %s' % (self.alternate_addon_id))
        notifyLog('Test run:                 %s' % (self.testConfig))
        """

        if self.testConfig:
            self.maxIdleTime = 60 + int(self.notifyUser)*self.notificationTime
            notifyLog('running in test mode for %s secs' % (self.maxIdleTime))

    def activeTimeFrame(self, debug=False):

        if not self.timeframe: return True

        _currframe = int((datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

        if _currframe < self.currframe: _currframe += 86400
        self.currframe = _currframe

        if debug: notifyLog('checking time frames: start: %s - current: %s - end: %s' % (self.act_start, self.currframe, self.act_stop))
        if self.act_start <= self.currframe <= self.act_stop: return True
        return False

    # user defined actions

    def stopVideoAudioTV(self):
        if xbmc.Player().isPlaying():
            notifyLog('media is playing, stopping it')
            xbmc.Player().stop()
            if self.jumpMainMenu:
                xbmc.sleep(500)
                notifyLog('jump to main menu')
                xbmc.executebuiltin('ActivateWindow(home)')

    @classmethod
    def quit(cls):
        notifyLog('quit kodi')
        xbmc.executebuiltin('Quit')

    @classmethod
    def systemReboot(cls):
        notifyLog('init system reboot')
        xbmc.restart()

    @classmethod
    def systemShutdown(cls):
        notifyLog('init system shutdown')
        xbmc.shutdown()

    @classmethod
    def systemHibernate(cls):
        notifyLog('init system hibernate')
        xbmc.executebuiltin('Hibernate')

    @classmethod
    def systemSuspend(cls):
        notifyLog('init system suspend')
        xbmc.executebuiltin('Suspend')

    def sendCecCommand(self):
        if not self.sendCEC: return
        notifyLog('send standby command via CEC')
        cec = subprocess.Popen('echo "standby 0" | cec-client -s', stdout=subprocess.PIPE, shell=True).communicate()
        for retstr in cec: notifyLog(str(retstr).strip())

    def runAddon(self):
        if xbmc.getCondVisibility('System.HasAddon(%s)' % (self.addon_id.split(',')[0])):
            notifyLog('run addon \'%s\'' % (self.addon_id))
            xbmc.executebuiltin('RunAddon(%s)' % (self.addon_id))
        else:
            notifyLog('could not run nonexistent addon \'%s\'' % (self.addon_id.split(',')[0]), level=xbmc.LOGERROR)

    def start(self):

        _currentIdleTime = 0
        _maxIdleTime = self.maxIdleTime
        _msgCnt = 0

        while not xbmc.Monitor.abortRequested(self):
            self.actionCanceled = False

            if _msgCnt % 10 == 0 and _currentIdleTime > 60 and not self.testConfig:
                notifyLog('idle time in active time frame: %s' % (time.strftime('%H:%M:%S', time.gmtime(_currentIdleTime))))

            if _currentIdleTime > xbmc.getGlobalIdleTime():
                notifyLog('user activity detected, reset idle time')
                _msgCnt = 0
                _maxIdleTime = self.maxIdleTime
                _currentIdleTime = 0

            _msgCnt += 1

            # Check if GlobalIdle longer than maxIdle and we're in a time frame

            if self.activeTimeFrame(debug=True):
                if _currentIdleTime > (_maxIdleTime - int(self.notifyUser)*self.notificationTime):

                    notifyLog('max idle time reached, ready to perform some action')

                    # Check if notification is allowed
                    if self.notifyUser:
                        count = 0
                        notifyLog('init notification countdown for action no. %s' % (self.action))

                        while (self.notificationTime - count > 0):
                            notifyUser(__LS__(32115) % (__LS__(self.action), self.notificationTime - count))
                            xbmc.sleep(9000)
                            count += 9
                            if _currentIdleTime > xbmc.getGlobalIdleTime():
                                self.actionCanceled = True
                                break

                    if not self.actionCanceled:

                        self.sendCecCommand()
                        {
                        32130: self.stopVideoAudioTV,
                        32131: self.systemReboot,
                        32132: self.systemShutdown,
                        32133: self.systemHibernate,
                        32134: self.systemSuspend,
                        32135: self.runAddon,
                        32136: self.quit
                        }.get(self.action)()
                        #
                        # ToDo: implement more user defined actions here
                        #       Action numbers are defined in settings.xml/strings.xml
                        #       also see LANGOFFSET
                        #
                        if self.testConfig:
                            notifyLog('watchdog was running in test mode, keep it alive')
                        else:
                            if self.keepAlive:
                                notifyLog('keep watchdog alive, update idletime for next cycle')
                                _maxIdleTime += self.maxIdleTime
                            else:
                                break
                    else:
                        notifyLog('Countdown canceled by user action')
                        notifyUser(__LS__(32118), icon=__iconError__)

                    # Reset test status
                    if self.testConfig:
                        __addon__.setSetting('testConfig', 'false')

            else:
                notifyLog('no active timeframe yet')

            #
            _loop = 1
            while not xbmc.Monitor.abortRequested(self):
                xbmc.sleep(1000)
                _loop += 1
                if self.activeTimeFrame(): _currentIdleTime += 1

                if self.SettingsChanged:
                    notifyLog('settings changed')
                    self.getWDSettings()
                    _maxIdleTime = self.maxIdleTime
                    break

                if self.testConfig or _currentIdleTime > xbmc.getGlobalIdleTime() or _loop > 60: break

# MAIN #

if __name__ == '__main__':
    try:
        WatchDog = SleepyWatchdog()
        notifyLog('Sleepy Watchdog kicks in')
        WatchDog.start()
        notifyLog('Sleepy Watchdog kicks off')
        del WatchDog

    except Exception, e:
        traceError(e, sys.exc_traceback)
