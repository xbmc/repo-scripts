import time
from datetime import datetime
import xbmc
import xbmcvfs
import xbmcgui
from . import utils as utils
from resources.lib.croniter import croniter
from resources.lib.backup import XbmcBackup

UPGRADE_INT = 2  # to keep track of any upgrade notifications


class BackupScheduler:
    monitor = None
    enabled = False
    next_run = 0
    next_run_path = None
    restore_point = None

    def __init__(self):
        self.monitor = UpdateMonitor(update_method=self.settingsChanged)
        self.enabled = utils.getSettingBool("enable_scheduler")
        self.next_run_path = xbmcvfs.translatePath(utils.data_dir()) + 'next_run.txt'

        # display upgrade messages if they exist
        if(utils.getSettingInt('upgrade_notes') < UPGRADE_INT):
            xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30132))
            utils.setSetting('upgrade_notes', str(UPGRADE_INT))

        # check if a backup should be resumed
        resumeRestore = self._resumeCheck()

        if(resumeRestore):
            restore = XbmcBackup()
            restore.selectRestore(self.restore_point)
            # skip the advanced settings check
            restore.skipAdvanced()
            restore.restore()

        if(self.enabled):

            # sleep for 2 minutes so Kodi can start and time can update correctly
            xbmc.Monitor().waitForAbort(120)

            nr = 0
            if(xbmcvfs.exists(self.next_run_path)):

                with xbmcvfs.File(self.next_run_path) as fh:
                    try:
                        # check if we saved a run time from the last run
                        nr = float(fh.read())
                    except ValueError:
                        nr = 0

            # if we missed and the user wants to play catch-up
            if(0 < nr <= time.time() and utils.getSettingBool('schedule_miss')):
                utils.log("scheduled backup was missed, doing it now...")
                progress_mode = utils.getSettingInt('progress_mode')

                if(progress_mode == 0):
                    progress_mode = 1  # Kodi just started, don't block it with a foreground progress bar

                self.doScheduledBackup(progress_mode)

            self.setup()

    def setup(self):
        # scheduler was turned on, find next run time
        utils.log("scheduler enabled, finding next run time")
        self.findNextRun(time.time())

    def start(self):

        while(not self.monitor.abortRequested()):

            if(self.enabled):
                # scheduler is still on
                now = time.time()

                if(self.next_run <= now):
                    progress_mode = utils.getSettingInt('progress_mode')
                    self.doScheduledBackup(progress_mode)

                    # check if we should shut the computer down
                    if(utils.getSettingBool("cron_shutdown")):
                        # wait 10 seconds to make sure all backup processes and files are completed
                        time.sleep(10)
                        xbmc.executebuiltin('ShutDown()')
                    else:
                        # find the next run time like normal
                        self.findNextRun(now)

            xbmc.sleep(500)

        # delete monitor to free up memory
        del self.monitor

    def doScheduledBackup(self, progress_mode):
        if(progress_mode != 2):
            utils.showNotification(utils.getString(30053))

        backup = XbmcBackup()

        if(backup.remoteConfigured()):

            if(utils.getSettingInt('progress_mode') in [0, 1]):
                backup.backup(True)
            else:
                backup.backup(False)

            # check if this is a "one-off"
            if(utils.getSettingInt("schedule_interval") == 0):
                # disable the scheduler after this run
                self.enabled = False
                utils.setSetting('enable_scheduler', 'false')
        else:
            utils.showNotification(utils.getString(30045))

    def findNextRun(self, now):
        progress_mode = utils.getSettingInt('progress_mode')

        # find the cron expression and get the next run time
        cron_exp = self.parseSchedule()

        cron_ob = croniter(cron_exp, datetime.fromtimestamp(now))
        new_run_time = cron_ob.get_next(float)

        if(new_run_time != self.next_run):
            self.next_run = new_run_time
            utils.log("scheduler will run again on " + utils.getRegionalTimestamp(datetime.fromtimestamp(self.next_run), ['dateshort', 'time']))

            # write the next time to a file
            with xbmcvfs.File(self.next_run_path, 'w') as fh:
                fh.write(str(self.next_run))

            # only show when not in silent mode
            if(progress_mode != 2):
                utils.showNotification(utils.getString(30081) + " " + utils.getRegionalTimestamp(datetime.fromtimestamp(self.next_run), ['dateshort', 'time']))

    def settingsChanged(self):
        current_enabled = utils.getSettingBool("enable_scheduler")

        if(current_enabled and not self.enabled):
            # scheduler was just turned on
            self.enabled = current_enabled
            self.setup()
        elif (not current_enabled and self.enabled):
            # schedule was turn off
            self.enabled = current_enabled

        if(self.enabled):
            # always recheck the next run time after an update
            self.findNextRun(time.time())

    def parseSchedule(self):
        schedule_type = utils.getSettingInt("schedule_interval")
        cron_exp = utils.getSetting("cron_schedule")

        hour_of_day = utils.getSetting("schedule_time")
        hour_of_day = int(hour_of_day[0:2])
        if(schedule_type == 0 or schedule_type == 1):
            # every day
            cron_exp = "0 " + str(hour_of_day) + " * * *"
        elif(schedule_type == 2):
            # once a week
            day_of_week = utils.getSetting("day_of_week")
            cron_exp = "0 " + str(hour_of_day) + " * * " + day_of_week
        elif(schedule_type == 3):
            # first day of month
            cron_exp = "0 " + str(hour_of_day) + " 1 * *"

        return cron_exp

    def _resumeCheck(self):
        shouldContinue = False
        if(xbmcvfs.exists(xbmcvfs.translatePath(utils.data_dir() + "resume.txt"))):
            rFile = xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "resume.txt"), 'r')
            self.restore_point = rFile.read()
            rFile.close()
            xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "resume.txt"))
            shouldContinue = xbmcgui.Dialog().yesno(utils.getString(30042), "%s\n%s" % (utils.getString(30043), utils.getString(30044)))

        return shouldContinue


class UpdateMonitor(xbmc.Monitor):
    update_method = None

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.update_method = kwargs['update_method']

    def onSettingsChanged(self):
        self.update_method()
