import time
import xbmc
import xbmcaddon
from cronex import CronExpression

class AutoUpdater:
    addon_id = "service.libraryautoupdate"
    Addon = xbmcaddon.Addon(addon_id)
    datadir = Addon.getAddonInfo('profile')
    sleep_time = 10
    forceUpdate = False
    
    #setup the timer amounts
    timer_amounts = {}
    timer_amounts['0'] = 1
    timer_amounts['1'] = 2
    timer_amounts['2'] = 5
    timer_amounts['3'] = 10
    timer_amounts['4'] = 15
    timer_amounts['5'] = 24
        
    def runProgram(self):

        if(self.Addon.getSetting('use_advanced_timer') == 'false'):        
            #check if we should delay the first run
            if(int(self.Addon.getSetting("startup_delay")) != 0):
                self.readLastRun()
                
                #check if we would have run an update anyway
                if(time.time() >= self.last_run + (timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60)):
                    #trick system by subtracting the timer amount then adding a delay (now - timer + delay = nextrun)
                    self.last_run = time.time() - (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 *60) + (int(self.Addon.getSetting("startup_delay")) * 60)
                    self.writeLastRun()
                    self.log("Setting delay at " + self.Addon.getSetting("startup_delay") + " minute")

        #run until XBMC quits
        while(not xbmc.abortRequested):

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
        if(now >= self.last_run + (self.timer_amounts[self.Addon.getSetting('timer_amount')] * 60 * 60)):
            #make sure player isn't running
            if(xbmc.Player().isPlaying() == False or self.Addon.getSetting('run_during_playback') == 'true'):
                if(self.scanRunning() == False):
                    self.runUpdates()
                    self.log("will run again in " + str(self.timer_amounts[self.Addon.getSetting("timer_amount")]) + " hours")
                        
            else:
                self.log("Player is running, waiting until finished")
                    
            

    def runAdvanced(self):        
        self.readLastRun()

        #create the cron expression
        cron = CronExpression(self.Addon.getSetting("cron_expression") + " XBMC_COMMAND")

        #check if we should run, and that we haven't already run the update within the past minute - alternatively check that we shouldn't force an update
        structTime = time.localtime()
        if((cron.check_trigger((structTime[0],structTime[1],structTime[2],structTime[3],structTime[4])) and time.time() > self.last_run + 60) or self.forceUpdate):
            #make sure player isn't running
            if(xbmc.Player().isPlaying() == False or self.Addon.getSetting('run_during_playback') == 'true'):
                self.forceUpdate = False
                if(self.scanRunning() == False):
                    self.runUpdates()
                    self.log("will run again according to: " + self.Addon.getSetting("cron_expression"))
                            
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

        #reset the last run timer    
        self.last_run = time.time()
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
        f = open(xbmc.translatePath(self.datadir + "last_run.txt"),"w")
        
        #write out the value for the last time the program ran
        f.write(str(self.last_run));
        f.close();

    def log(self,message):
        xbmc.log('service.libraryautoupdate: ' + message)

