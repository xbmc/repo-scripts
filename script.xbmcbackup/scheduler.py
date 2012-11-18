import xbmc
import datetime
import time
import os
import resources.lib.utils as utils
from resources.lib.croniter import croniter
from resources.lib.backup import XbmcBackup

class BackupScheduler:
    enabled = "false"
    next_run = 0
    settings_update_time = 0
    
    def __init__(self):
        self.enabled = utils.getSetting("enable_scheduler")

        if(self.enabled == "true"):
            self.setup()

    def setup(self):
        #scheduler was turned on, find next run time
        utils.log("scheduler enabled, finding next run time")
        self.findNextRun(time.time(),True)
        utils.log("scheduler will run again on " + datetime.datetime.fromtimestamp(self.next_run).strftime('%m-%d-%Y %H:%M'))
        
    def start(self):
        while(not xbmc.abortRequested):
            current_enabled = utils.getSetting("enable_scheduler")
            
            if(current_enabled == "true" and self.enabled == "false"):
                #scheduler was just turned on
                self.enabled = current_enabled
                self.setup()
            elif (current_enabled == "false" and self.enabled == "true"):
                #schedule was turn off
                self.enabled = current_enabled
            elif(self.enabled == "true"):
                #scheduler is still on
                now = time.time()

                if(self.next_run <= now):
                    if(utils.getSetting('run_silent') == 'false'):
                        utils.showNotification(utils.getString(30053))
                    #run the job in backup mode, hiding the dialog box
                    backup = XbmcBackup()
                    backup.run(XbmcBackup.Backup,True)
                    self.findNextRun(now,True)
                else:
                    self.findNextRun(now)

            time.sleep(10)

    def findNextRun(self,now,forceUpdate = False):
        mod_time = self.settings_update_time
        
        #check if the schedule has been modified
        try:
            #get the last modified time of the file
            mod_time = os.path.getmtime(xbmc.translatePath(utils.data_dir()) + "settings.xml")
        except:
            #don't do anything here
            mod_time = self.settings_update_time

        if(mod_time > self.settings_update_time or forceUpdate):
            self.settings_update_time = mod_time
            
            #find the cron expression and get the next run time
            cron_exp = self.parseSchedule()

            cron_ob = croniter(cron_exp,datetime.datetime.fromtimestamp(now))
            new_run_time = cron_ob.get_next(float)

            if(new_run_time != self.next_run):
                self.next_run = new_run_time
                utils.log("scheduler will run again on " + datetime.datetime.fromtimestamp(self.next_run).strftime('%m-%d-%Y %H:%M'))

    def parseSchedule(self):
        schedule_type = int(utils.getSetting("schedule_interval"))
        cron_exp = utils.getSetting("cron_schedule")

        hour_of_day = utils.getSetting("schedule_time")
        hour_of_day = int(hour_of_day[0:2])
        if(schedule_type == 0):
            #every day
           
            cron_exp = "0 " + str(hour_of_day) + " * * *"
        elif(schedule_type == 1):
            #once a week
            day_of_week = utils.getSetting("day_of_week")
            cron_exp = "0 " + str(hour_of_day) + " * * " + day_of_week
        elif(schedule_type == 2):
            #first day of month
            cron_exp = "0 " + str(hour_of_day) + " 1 * *"

        return cron_exp    
        
BackupScheduler().start()
