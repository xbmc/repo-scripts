import time
from datetime import datetime
import xbmc
import xbmcaddon
import os
from resources.lib.croniter import croniter

class AutoUpdater:
    addon_id = "service.libraryautoupdate"
    Addon = xbmcaddon.Addon(addon_id)
    datadir = Addon.getAddonInfo('profile')
    addondir = Addon.getAddonInfo('path')
    sleep_time = 10
    forceUpdate = False
    previousTimer = 0
    
    #setup the timer amounts
    timer_amounts = {}
    timer_amounts['0'] = 1
    timer_amounts['1'] = 2
    timer_amounts['2'] = 5
    timer_amounts['3'] = 10
    timer_amounts['4'] = 15
    timer_amounts['5'] = 24

    def __init__(self):
        self.readLastRun()
        
    def runProgram(self):
        
        if(self.Addon.getSetting('use_advanced_timer') == 'false'):        
            #check if we should delay the first run
            if(int(self.Addon.getSetting("startup_delay")) != 0):
                
                #check if we would have run an update anyway
                if(time.time() >= self.last_run + (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60)):
                    #trick system by subtracting the timer amount then adding a delay (now - timer + delay = nextrun)
                    self.last_run = time.time() - (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 *60) + (int(self.Addon.getSetting("startup_delay")) * 60)
                    self.writeLastRun()
                    self.log("Setting delay at " + self.Addon.getSetting("startup_delay") + " minute")

            self.showNotify(self.last_run + (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60))
            self.currentTimer = self.Addon.getSetting('timer_amount')
        else:
            self.currentTimer = self.Addon.getSetting("cron_expression")
            cronExp = croniter(self.Addon.getSetting("cron_expression"),datetime.now())
            self.showNotify(cronExp.get_next(float))
        
        #run until XBMC quits
        while(not xbmc.abortRequested):
            self.checkTimer()
            
            if(self.Addon.getSetting('use_advanced_timer') == 'true'):
                self.runAdvanced()
            else:
                self.runStandard()
            
            #put the thread to sleep for x number of seconds
            time.sleep(self.sleep_time)
            

    def runStandard(self):        
        now = time.time()

        self.readLastRun()
            
        #check if we should run an update
        if(now >= self.last_run + (self.timer_amounts[self.currentTimer] * 60 * 60)):
            #make sure player isn't running
            if(xbmc.Player().isPlaying() == False or self.Addon.getSetting('run_during_playback') == 'true'):
                if(self.scanRunning() == False):
                    self.runUpdates()
                    self.showNotify(self.last_run + (self.timer_amounts[self.currentTimer] * 60 * 60))
                    self.log("will run again in " + str(self.timer_amounts[self.currentTimer]) + " hours")
                        
            else:
                self.log("Player is running, waiting until finished")
                    
            

    def runAdvanced(self):        
        self.readLastRun()
        now = time.time()
        
        #create the cron expression
        cron = croniter(self.currentTimer,datetime.fromtimestamp(now - 60))
        runCron = cron.get_next(float)
        
        #check if we should run, and that we haven't already run the update within the past minute - alternatively check that we shouldn't force an update
        if((runCron <= now and time.time() > self.last_run + 60) or self.forceUpdate):
            #make sure player isn't running
            if(xbmc.Player().isPlaying() == False or self.Addon.getSetting('run_during_playback') == 'true'):
                self.forceUpdate = False
                if(self.scanRunning() == False):
                    self.runUpdates()
                    nextRun = cron.get_next(float)
                    self.showNotify(nextRun)
                    self.log("will run again in " + self.nextRun(nextRun))
                            
            else:
                #force an update if this 
                self.forceUpdate = True
                self.log("Player is running, waiting until finished")
    
    def scanRunning(self):
        #check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True            
        else:
            return False
        
    def runUpdates(self):
        #run the update
        if(self.Addon.getSetting('update_video') == 'true'):
            self.log('Updating Video')
            xbmc.executebuiltin('UpdateLibrary(video)')
            time.sleep(1)
                            
        if(self.Addon.getSetting('update_music') == 'true'):
            #check if scan is running again, wait until finished if it is
            while(self.scanRunning()):
                time.sleep(10)
                            
            self.log('Update Music')
            xbmc.executebuiltin('UpdateLibrary(music)')

        #reset the last run timer - mod to top of minute (thanks pkscuot)     
        self.last_run = time.time() - (time.time() % 60)
        self.writeLastRun()

    def readLastRun(self):
        
        try:
            f = open(xbmc.translatePath(self.datadir + "last_run.txt"),"r")
            self.last_run = float(f.read())
            f.close()
        except IOError:
            #the file doesn't exist, most likely first time running
            self.last_run = 0
        

    def writeLastRun(self):
        #create the addon folder if it doesn't exist
        if(not os.path.exists(xbmc.translatePath(self.datadir))):
            os.makedirs(xbmc.translatePath(self.datadir))
            
        f = open(xbmc.translatePath(self.datadir + "last_run.txt"),"w")
        
        #write out the value for the last time the program ran
        f.write(str(self.last_run));
        f.close();

    def showNotify(self,timestamp):
        #don't show anything if the update will happen now
        if(timestamp > time.time() and self.Addon.getSetting('notify_next_run') == 'true'):
            self.log(self.addondir)
            xbmc.executebuiltin("Notification(Library Auto Update,Next run: " + self.nextRun(timestamp) + ",4000," + xbmc.translatePath(self.addondir + "/icon.png") + ")")

    def calcNextRun(self):
        if(self.Addon.getSetting('use_advanced_timer') == 'false'):
            return self.nextRun(self.last_run + (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60))
        else:
            cronExp = croniter(self.Addon.getSetting("cron_expression"),datetime.now())
            return self.nextRun(cronExp.get_next(float))
                
                
    def nextRun(self,nextRun):
        #compare now with next date
        cronDiff = nextRun - time.time() + 60

        if cronDiff < 0:
            return ""
        
        hours = int((cronDiff / 60) / 60)
        minutes = int((cronDiff / 60) - hours * 60)

        #we always have at least one minute
        if minutes == 0:
            minutes = 1

        result = str(hours) + " h " + str(minutes) + " m"
        if hours == 0:
            result = str(minutes) + " m"
        elif hours > 36:
            #just show the date instead
            result = datetime.fromtimestamp(nextRun).strftime('%m/%d %I:%M%p')
        elif hours > 24:
            days = int(hours / 24)
            hours = hours - days * 24
            result = str(days) + " d " + str(hours) + " h " + str(minutes) + " m"
       
        return result
        
    def checkTimer(self):
        if(self.Addon.getSetting('use_advanced_timer') == 'false'):
            if  self.Addon.getSetting('timer_amount') != self.currentTimer:
                self.showNotify(self.last_run + (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60))
                self.currentTimer = self.Addon.getSetting('timer_amount')
        else:
            if self.Addon.getSetting("cron_expression") != self.currentTimer:
                cronExp = croniter(self.Addon.getSetting("cron_expression"),datetime.now())
                self.showNotify(cronExp.get_next(float))
                self.currentTimer = self.Addon.getSetting("cron_expression")
        
    def log(self,message):
        xbmc.log('service.libraryautoupdate: ' + message)

