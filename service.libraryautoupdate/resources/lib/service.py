# -*- coding: cp1252 -*-
import time
from datetime import datetime
from kodi_six import xbmc, xbmcgui, xbmcvfs
from future.moves.urllib.request import urlopen, unquote
import json
import resources.lib.utils as utils
from resources.lib.croniter import croniter
from resources.lib.cronclasses import CronSchedule, CustomPathFile

UPGRADE_INT = 1  # to keep track of any upgrade notifications


class AutoUpdater:
    last_run = 0
    schedules = []
    lock = False

    monitor = None

    def __init__(self):
        utils.check_data_dir()  # in case this directory does not exist yet
        self.monitor = UpdateMonitor(update_settings=self.createSchedules, after_scan=self.databaseUpdated)
        self.readLastRun()

        # force and update on startup to create the array
        self.createSchedules(True)

    def runProgram(self):
        # a one-time catch for the startup delay
        if(utils.getSettingInt("startup_delay") != 0):
            count = 0
            while count < len(self.schedules):
                if(time.time() > self.schedules[count].next_run):
                    # we missed at least one update, fix this
                    self.schedules[count].next_run = time.time() + utils.getSettingInt("startup_delay") * 60
                count = count + 1

        utils.log(str(utils.getSettingInt('startup_delay')))
        # display upgrade messages if they exist
        if(utils.getSettingInt('upgrade_notes') < UPGRADE_INT):
            xbmcgui.Dialog().ok(utils.getString(30000), utils.getString(30030))
            utils.setSetting('upgrade_notes', str(UPGRADE_INT))

        # program has started, check if we should show a notification
        self.showNotify()

        while(True):

            # don't check unless new minute
            if(time.time() > self.last_run + 60):
                self.readLastRun()

                self.evalSchedules()

            # calculate the sleep time (next minute)
            now = datetime.now()
            if(self.monitor.waitForAbort(60 - now.second)):
                break

        # clean up monitor on exit
        del self.monitor

    def evalSchedules(self, manual=False):
        if(not self.lock):
            now = time.time()

            count = 0
            player = xbmc.Player()
            while count < len(self.schedules):
                cronJob = self.schedules[count]

                if(cronJob.next_run <= now):
                    if(not player.isPlaying() or utils.getSetting("run_during_playback") == "true"):

                        # check if run on idle is checked and screen is idle - disable this on manual run
                        if(not utils.getSettingBool('run_on_idle') or (utils.getSettingBool('run_on_idle') and (self.monitor.screensaver_running or manual))):

                            # check for valid network connection - check sources if setting enabled
                            if(self._networkUp() and (not utils.getSettingBool('check_sources') or (utils.getSettingBool('check_sources') and self._checkSources(cronJob)))):

                                # check if this scan was delayed due to playback
                                if(cronJob.on_delay):
                                    # add another minute to the delay
                                    self.schedules[count].next_run = now + 60
                                    self.schedules[count].on_delay = False
                                    utils.log(cronJob.name + " paused due to playback")

                                elif(not self.scanRunning()):
                                    # run the command for this job
                                    utils.log(cronJob.name)

                                    if(cronJob.timer_type == 'xbmc'):
                                        cronJob.executeCommand()
                                    else:
                                        self.cleanLibrary(cronJob)

                                    # find the next run time
                                    cronJob.next_run = self.calcNextRun(cronJob.expression, now)
                                    self.schedules[count] = cronJob

                                elif(self.scanRunning()):
                                    self.schedules[count].next_run = now + 60
                                    utils.log("Waiting for other scan to finish")
                            else:
                                utils.log("Network down, not running")
                        else:
                            utils.log("Skipping scan, only run when idle")
                    else:
                        self.schedules[count].on_delay = True
                        utils.log("Player is running, wait until finished")

                count = count + 1

            # write last run time
            now = time.time()
            self.last_run = now - (now % 60)

    def createSchedules(self, forceUpdate=False):
        utils.log("update timers")
        self.lock = True   # lock so the eval portion does not run
        self.schedules = []
        showDialogs = utils.getSettingBool('notify_next_run')  # if the user has selected to show dialogs for library operations

        if(utils.getSettingBool('clean_libraries')):
            # create clean schedule (if needed)
            if(utils.getSettingInt("clean_timer") != 0):

                if(utils.getSettingInt('library_to_clean') == 0 or utils.getSettingInt('library_to_clean') == 1):
                    # video clean schedule starts at 12am by default
                    aSchedule = CronSchedule()
                    aSchedule.name = utils.getString(30048)
                    aSchedule.timer_type = utils.__addon_id__
                    aSchedule.command = {'method': 'VideoLibrary.Clean', 'params': {'showdialogs': showDialogs}}
                    if(utils.getSettingInt("clean_timer") == 4):
                        aSchedule.expression = utils.getSetting("clean_video_cron_expression")
                    else:
                        aSchedule.expression = "0 0 " + aSchedule.cleanLibrarySchedule(utils.getSettingInt("clean_timer"))
                    aSchedule.next_run = self.calcNextRun(aSchedule.expression, time.time())

                    self.schedules.append(aSchedule)

                if(utils.getSettingInt('library_to_clean') == 2 or utils.getSettingInt('library_to_clean') == 0):
                    # music clean schedule starts at 2am by default
                    aSchedule = CronSchedule()
                    aSchedule.name = utils.getString(30049)
                    aSchedule.timer_type = utils.__addon_id__
                    aSchedule.command = {'method': 'AudioLibrary.Clean', 'params': {'showdialogs': showDialogs}}
                    if(utils.getSettingInt("clean_timer") == 4):
                        aSchedule.expression = utils.getSetting("clean_music_cron_expression")
                    else:
                        aSchedule.expression = "0 2 " + aSchedule.cleanLibrarySchedule(utils.getSettingInt("clean_timer"))
                    aSchedule.next_run = self.calcNextRun(aSchedule.expression, time.time())

                    self.schedules.append(aSchedule)

        if(utils.getSettingBool('update_video')):
            utils.log("Creating timer for Video Library")
            # create the video schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30012)
            aSchedule.command = {'method': 'VideoLibrary.Scan', 'params': {'showdialogs': showDialogs}}
            aSchedule.expression = self.checkTimer('video')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression, self.last_run)
            self.schedules.append(aSchedule)

        # add custom video paths (separate timers)
        customPaths = CustomPathFile('video')
        for aJob in customPaths.getSchedules(showDialogs):
            utils.log("Creating timer " + aJob.name)
            aJob.next_run = self.calcNextRun(aJob.expression, self.last_run)
            self.schedules.append(aJob)

        if(utils.getSettingBool('update_music')):
            utils.log("Creating timer for Music Library")
            # create the music schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30013)
            aSchedule.command = {'method': 'AudioLibrary.Scan', 'params': {'showdialogs': showDialogs}}
            aSchedule.expression = self.checkTimer('music')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression, self.last_run)

            self.schedules.append(aSchedule)

        # add custom music paths (separate timers)
        customPaths = CustomPathFile('music')
        for aJob in customPaths.getSchedules(showDialogs):
            utils.log("Creating timer " + aJob.name)
            aJob.next_run = self.calcNextRun(aJob.expression, self.last_run)
            self.schedules.append(aJob)

        # release the lock
        self.lock = False

        utils.log("Created " + str(len(self.schedules)) + " schedules", xbmc.LOGDEBUG)

        # show any notifications
        self.showNotify(not forceUpdate)

    def checkTimer(self, settingName):
        result = ''

        # figure out if using standard or advanced timer
        if(utils.getSettingBool(settingName + '_advanced_timer')):
            # copy the expression
            result = utils.getSetting(settingName + "_cron_expression")
        else:
            result = '0 */' + str(utils.getSetting(settingName + "_timer")) + ' * * *'

        return result

    def calcNextRun(self, cronExp, startTime):
        nextRun = -1

        try:
            # create croniter for this expression
            cron = croniter(cronExp, startTime)
            nextRun = cron.get_next(float)
        except ValueError:
            # error in syntax
            xbmcgui.Dialog().ok(utils.getString(30000), utils.getString(30016) % cronExp)
            utils.log('Cron syntax error %s' % cronExp, xbmc.LOGDEBUG)

            # rerun with a valid syntax
            nextRun = self.calcNextRun('0 */2 * * *', startTime)

        return nextRun

    def showNotify(self, displayToScreen=True):
        # go through and find the next schedule to run
        next_run_time = CronSchedule()
        for cronJob in self.schedules:
            if(cronJob.next_run < next_run_time.next_run or next_run_time.next_run == 0):
                next_run_time = cronJob

        inWords = self.nextRunCountdown(next_run_time.next_run)
        # show the notification (if applicable)
        if(next_run_time.next_run > time.time() and utils.getSettingBool('notify_next_run') and displayToScreen):
            utils.showNotification(utils.getString(30000), inWords + " - " + next_run_time.name)

        return inWords

    def nextRunCountdown(self, nextRun):
        # compare now with next date
        cronDiff = nextRun - time.time()

        if cronDiff < 0:
            return ""

        hours = int((cronDiff / 60) / 60)
        minutes = int(round(cronDiff / 60.0 - hours * 60))

        # we always have at least one minute
        if minutes == 0:
            minutes = 1

        result = str(hours) + " h " + str(minutes) + " m"
        if hours == 0:
            result = str(minutes) + " m"
        elif hours > 36:
            # just show the date instead
            result = datetime.fromtimestamp(nextRun).strftime('%m/%d %I:%M%p')
        elif hours > 24:
            days = int(hours / 24)
            hours = hours - days * 24
            result = str(days) + " d " + str(hours) + " h " + str(minutes) + " m"

        return result

    def cleanLibrary(self, cronJob):
        # check if we should verify with user first unless we're on 'clean after update'
        if(utils.getSettingBool('user_confirm_clean') and utils.getSettingInt('clean_timer') != 0):
            # user can decide 'no' here and exit this
            runClean = xbmcgui.Dialog().yesno(utils.getString(30000), utils.getString(30052), line2=utils.getString(30053), autoclose=15000)
            if(not runClean):
                return

        # run the clean operation
        utils.log("Cleaning Database")
        cronJob.executeCommand()

        # write last run time, will trigger notifications
        self.writeLastRun()

    def readLastRun(self):
        if(self.last_run == 0):
            # read it in from the settings
            if(xbmcvfs.exists(xbmcvfs.translatePath(utils.data_dir() + "last_run.txt"))):

                runFile = xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "last_run.txt"))

                try:
                    # there may be an issue with this file, we'll get it the next time through
                    self.last_run = float(runFile.read())
                except ValueError:
                    self.last_run = 0

                runFile.close()
            else:
                self.last_run = 0

    def writeLastRun(self):
        runFile = xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "last_run.txt"), 'w')
        runFile.write(str(self.last_run))
        runFile.close()

        self.showNotify(True)

    def scanRunning(self):
        # check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True
        else:
            return False

    def databaseUpdated(self, database):
        showDialogs = utils.getSettingBool('notify_next_run')  # if the user has selected to show dialogs for library operations
        # check if we should clean the library
        if(utils.getSettingBool('clean_libraries')):
            # check if should update while playing media
            if(not xbmc.Player().isPlaying() or utils.getSettingBool("run_during_playback")):
                if(utils.getSettingInt("clean_timer") == 0):
                    # check if we should clean music, or video
                    aJob = CronSchedule()
                    aJob.name = utils.getString(30048)
                    aJob.timer_type = utils.__addon_id__
                    if((utils.getSettingInt('library_to_clean') == 0 or utils.getSettingInt('library_to_clean') == 1) and database == 'video'):
                        # create the clean job schedule
                        aJob.command = {'method': 'VideoLibrary.Clean', 'params': {'showdialogs': showDialogs}}
                    if((utils.getSettingInt('library_to_clean') == 2 or utils.getSettingInt('library_to_clean') == 0) and database == 'music'):
                        aJob.command = {'method': 'AudioLibrary.Clean', 'params': {'showdialogs': showDialogs}}

                    self.cleanLibrary(aJob)

        # writeLastRun will trigger notifications
        self.writeLastRun()

    def _networkUp(self):
        try:
            urlopen('http://www.google.com', timeout=1)
            return True
        except Exception:
            pass

        return False

    def _checkSources(self, aJob):
        result = False
        mediaType = 'video'

        if(aJob.command['method'] == 'VideoLibrary.Scan' or aJob.command['method'] == 'AudioLibrary.Scan'):

            # set the media type
            if(aJob.command['method'] != 'VideoLibrary.Scan'):
                mediaType = 'music'

            if('directory' in aJob.command['params']):
                # we have a specific path to check
                result = self._sourceExists(aJob.command['params']['directory'])
            else:
                # check every video path
                response = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'method': 'Files.GetSources', 'params': {'media': mediaType}, 'id': 44})))

                # make sure we got something
                if('result' in response):
                    for source in response['result']['sources']:
                        if(not self._sourceExists(source['file'])):
                            # one failure fails the whole thing
                            return False
                    # if we make it this far we got them all
                    result = True
        else:
            # must be a cleaning, skip this check since Kodi will do it
            result = True

        return result

    def _sourceExists(self, source):
        utils.log("checking: " + source)
        # check if this is a multipath source
        if(source.startswith('multipath://')):
            # code adapted from xbmc source MultiPathDirectory.cpp
            source = source[12:]

            if(source[-1:] == "/"):
                source = source[:-1]
            splitSource = source.split('/')
            if(len(splitSource) > 0):
                for aSource in splitSource:
                    if not xbmcvfs.exists(unquote(aSource)):
                        # if one source in the multi does not exist, return false
                        return False
                # if we make it here they all exist
                return True
            else:
                return False
        else:
            return xbmcvfs.exists(source)


class UpdateMonitor(xbmc.Monitor):
    update_settings = None
    after_scan = None
    screensaver_running = False

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.update_settings = kwargs['update_settings']
        self.after_scan = kwargs['after_scan']

    def onSettingsChanged(self):
        xbmc.sleep(1000)  # slight delay for notifications
        self.update_settings()

    def onScanFinished(self, database):
        self.after_scan(database)

    def onScreensaverActivated(self):
        utils.log("screen saver on", xbmc.LOGDEBUG)
        self.screensaver_running = True

    def onScreensaverDeactivated(self):
        utils.log("screen saver off", xbmc.LOGDEBUG)
        self.screensaver_running = False
