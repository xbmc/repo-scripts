# -*- coding: cp1252 -*-
import time
from datetime import datetime
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import os
from resources.lib.croniter import croniter

class CronSchedule:
    expression = ''
    name = 'library'
    timer_type = 'xbmc'
    command = 'UpdateLibrary(video)'
    next_run = 0
    on_delay = False  #used to defer processing until after player finishes
    clean_library = False  #if clean library command should be run after this schedule

    def cleanLibrarySchedule(self,selectedIndex):
        if(selectedIndex == 1):
            #once per day
            return "* * *"
        elif (selectedIndex == 2):
            #once per week
            return "* * 0"
        else:
            #once per month
            return "1 * *"
            
class AutoUpdater:
    addon_id = "service.libraryautoupdate"
    Addon = xbmcaddon.Addon(addon_id)
    datadir = Addon.getAddonInfo('profile')
    addondir = Addon.getAddonInfo('path')
    last_run = 0
    sleep_time = 10
    schedules = []
    settings_update_time = 0
    
    #setup the timer amounts
    timer_amounts = {}
    timer_amounts['0'] = 1
    timer_amounts['1'] = 2
    timer_amounts['2'] = 4
    timer_amounts['3'] = 6
    timer_amounts['4'] = 12
    timer_amounts['5'] = 24

    def __init__(self):
        self.readLastRun()

        #force and update on startup to create the array
        self.createSchedules(True)
        
    def runProgram(self):
        #a one-time catch for the startup delay
        if(int(self.Addon.getSetting("startup_delay")) != 0):
            count = 0
            while count < len(self.schedules):
                if(time.time() > self.schedules[count].next_run):
                    #we missed at least one update, fix this
                    self.schedules[count].next_run = time.time() + int(self.Addon.getSetting("startup_delay")) * 60
                count = count + 1
                
        #program has started, check if we should show a notification
        self.showNotify()

        while(not xbmc.abortRequested):
            self.readLastRun()

            self.evalSchedules()

            time.sleep(self.sleep_time)

    def evalSchedules(self):
        now = time.time()
        self.createSchedules()
        
        count = 0
        tempLastRun = self.last_run
        while count < len(self.schedules):
            cronJob = self.schedules[count]
            
            if(cronJob.next_run <= now and now > tempLastRun + 60):
                if(xbmc.Player().isPlaying() == False or self.Addon.getSetting("run_during_playback") == "true"):
                    #check if this scan was delayed due to playback
                    if(cronJob.on_delay == True):
                        #add another minute to the delay
                        self.schedules[count].next_run = now + 60
                        self.schedules[count].on_delay = False
                        self.log(cronJob.name + " paused due to playback")
                        
                    elif(self.scanRunning() == False):
                        #run the command for this job
                        self.log(cronJob.name)

                        if(cronJob.timer_type == 'xbmc'):
                            xbmc.executebuiltin(cronJob.command)
                            self.waitForScan()
                        else:
                            self.cleanLibrary(cronJob)

                        self.last_run = time.time() - (time.time() % 60)
                        self.writeLastRun()
                        
                        #find the next run time
                        cronJob.next_run = self.calcNextRun(cronJob.expression,now)
                        self.schedules[count] = cronJob

                        #show any notifications
                        self.showNotify()

                        #check if we should clean the library too
                        if(cronJob.clean_library):
                            self.cleanLibrary(cronJob)
                else:
                    self.schedules[count].on_delay = True
                    self.log("Player is running, wait until finished")
                        
            count = count + 1            
        
    def createSchedules(self,forceUpdate = False):
        mod_time = self.settings_update_time

        try:
            #get the last modified time of the file
            mod_time = os.path.getmtime(xbmc.translatePath(self.datadir) + "settings.xml")
        except:
            #don't do anything here
            mod_time = self.settings_update_time

        if(mod_time > self.settings_update_time or forceUpdate):
            self.log("update timers")
            self.schedules = []

            clean_video_after_update = False
            clean_music_after_update = True
            
            if(self.Addon.getSetting('clean_libraries') == 'true'):
                #create clean schedule (if needed)
                if(int(self.Addon.getSetting("clean_timer")) == 0):
                    if(self.Addon.getSetting('library_to_clean') == '0' or self.Addon.getSetting('library_to_clean') == '1'):
                        clean_video_after_update = True
                    if(self.Addon.getSetting('library_to_clean') == '2' or self.Addon.getSetting('library_to_clean') == '0'):
                        clean_music_after_update = True
                else:
                    #create a separate schedule for cleaning - use right now rather than last_run, never 'catch-up'
                    clean_video_after_update = False
                    clean_music_after_update = False
                    
                    if(self.Addon.getSetting('library_to_clean') == '0' or self.Addon.getSetting('library_to_clean') == '1'):
                        #video clean schedule starts at 12am
                        aSchedule = CronSchedule()
                        aSchedule.name = self.Addon.getLocalizedString(30048)
                        aSchedule.timer_type = self.addon_id
                        aSchedule.command = 'video'
                        aSchedule.expression = "0 0 " + aSchedule.cleanLibrarySchedule(int(self.Addon.getSetting("clean_timer")))
                        aSchedule.next_run = self.calcNextRun(aSchedule.expression,time.time())

                        self.schedules.append(aSchedule)
                        
                    if(self.Addon.getSetting('library_to_clean') == '2' or self.Addon.getSetting('library_to_clean') == '0'):
                        #music clean schedule starts at 2am
                        aSchedule = CronSchedule()
                        aSchedule.name = self.Addon.getLocalizedString(30049)
                        aSchedule.timer_type = self.addon_id
                        aSchedule.command = 'music'
                        aSchedule.expression = "0 2 " + aSchedule.cleanLibrarySchedule(int(self.Addon.getSetting("clean_timer")))
                        aSchedule.next_run = self.calcNextRun(aSchedule.expression,time.time())
    
                        self.schedules.append(aSchedule)
                                                                                

            if(self.Addon.getSetting('update_video') == 'true'):
                #create the video schedule
                aSchedule = CronSchedule()
                aSchedule.name = self.Addon.getLocalizedString(30004)
                aSchedule.command = 'UpdateLibrary(video)'
                aSchedule.expression = self.checkTimer('video')
                aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                aSchedule.clean_library = clean_video_after_update
                
                self.schedules.append(aSchedule)

            if(self.Addon.getSetting('update_music') == 'true'):
                #create the music schedule
                aSchedule = CronSchedule()
                aSchedule.name = self.Addon.getLocalizedString(30005)
                aSchedule.command = 'UpdateLibrary(music)'
                aSchedule.expression = self.checkTimer('music')
                aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                aSchedule.clean_library = clean_music_after_update
                
                self.schedules.append(aSchedule)

            if(self.Addon.getSetting('use_custom_1_path') == 'true'):
                #create a custom video path schedule
                aSchedule = CronSchedule()
                aSchedule.name = self.Addon.getLocalizedString(30020)
                aSchedule.command = 'UpdateLibrary(video,' + self.Addon.getSetting('custom_1_scan_path') + ')'
                aSchedule.expression = self.checkTimer('custom_1')
                aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                aSchedule.clean_library = clean_video_after_update
                
                self.schedules.append(aSchedule)

            if(self.Addon.getSetting('use_custom_2_path') == 'true'):
                #create a custom video path schedule
                aSchedule = CronSchedule()
                aSchedule.name = self.Addon.getLocalizedString(30021)
                aSchedule.command = 'UpdateLibrary(video,' + self.Addon.getSetting('custom_2_scan_path') + ')'
                aSchedule.expression = self.checkTimer('custom_2')
                aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                aSchedule.clean_library = clean_video_after_update
                
                self.schedules.append(aSchedule)

            if(self.Addon.getSetting('use_custom_3_path') == 'true'):
                #create a custom video path schedule
                aSchedule = CronSchedule()
                aSchedule.name = self.Addon.getLocalizedString(30022)
                aSchedule.command = 'UpdateLibrary(video,' + self.Addon.getSetting('custom_3_scan_path') + ')'
                aSchedule.expression = self.checkTimer('custom_3')
                aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                aSchedule.clean_library = clean_video_after_update
                
                self.schedules.append(aSchedule)
                
            #update the mod time for the file
            self.settings_update_time = mod_time

            #show any notifications
            self.showNotify(not forceUpdate)
            
    def checkTimer(self,settingName):
        result = ''
        
        #figure out if using standard or advanced timer
        if(self.Addon.getSetting(settingName + '_advanced_timer') == 'true'):
            #copy the expression
            result = self.Addon.getSetting(settingName + "_cron_expression")
        else:
            result = '0 */' + str(self.timer_amounts[self.Addon.getSetting(settingName + "_timer")]) + ' * * *'

        return result
    
    def calcNextRun(self,cronExp,startTime):
        
        #create croniter for this expression
        cron = croniter(cronExp,startTime)
        nextRun = cron.get_next(float)

        return nextRun

    def showNotify(self,displayToScreen = True):
        #go through and find the next schedule to run
        next_run_time = CronSchedule()
        for cronJob in self.schedules:
            if(cronJob.next_run < next_run_time.next_run or next_run_time.next_run == 0):
                next_run_time = cronJob

        inWords = self.nextRunCountdown(next_run_time.next_run)
        #show the notification (if applicable)
        if(next_run_time.next_run > time.time() and self.Addon.getSetting('notify_next_run') == 'true' and displayToScreen == True):
            xbmc.executebuiltin("Notification(" + self.Addon.getLocalizedString(30000) + "," + next_run_time.name + " - " + inWords + ",4000," + xbmc.translatePath(self.addondir + "/resources/images/clock.png") + ")")

        return inWords    

    def nextRunCountdown(self,nextRun):
        #compare now with next date
        cronDiff = nextRun - time.time()

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
        

    def cleanLibrary(self,cronJob):
        #check which database we're in
        media_type = 'video'
        if(cronJob.command.find('music') != -1):
            media_type = 'music'
        
        #check if we should verify paths
        if(self.Addon.getSetting("verify_paths") == 'true'):
            response = eval(xbmc.executeJSONRPC('{ "jsonrpc" : "2.0", "method" : "Files.GetSources", "params":{"media":"' + media_type + '"}, "id": 1}'))
            for source in response['result']['sources']:
                if not xbmcvfs.exists(source['file']):
                    #let the user know this failed, if they subscribe to notifications
                    if(self.Addon.getSetting('notify_next_run') == 'true'):
                        xbmc.executebuiltin("Notification(" + self.Addon.getLocalizedString(30050) + ",Source " + source['label'] + " does not exist,4000," + xbmc.translatePath(self.addondir + "/resources/images/clock.png") + ")")

                    self.log("Path " + source['file'] + " does not exist")
                    return

        #also check if we should verify with user first
        if(self.Addon.getSetting('user_confirm_clean') == 'true'):
            #user can decide 'no' here and exit this
            runClean = xbmcgui.Dialog().yesno(self.Addon.getLocalizedString(30000),self.Addon.getLocalizedString(30052),self.Addon.getLocalizedString(30053))
            if(not runClean):
                return
                
        #run the clean operation
        self.log("Cleaning Database")
        xbmc.executebuiltin("CleanLibrary(" + media_type + ")")
    
    def readLastRun(self):
        
        try:
            self.last_run = 0
            f = open(unicode(xbmc.translatePath(self.datadir + "last_run.txt"),'utf-8'),"r")
            strlastRun = f.read()
            if len(strlastRun) != 0 :
                self.last_run = float(strlastRun) 
            f.close()
        except:
            #the file doesn't exist, most likely first time running
            self.last_run = 0

    def writeLastRun(self):
        #create the addon folder if it doesn't exist
        if(not os.path.exists(unicode(xbmc.translatePath(self.datadir),'utf-8'))):
            os.makedirs(unicode(xbmc.translatePath(self.datadir),'utf-8'))

        f = open(unicode(xbmc.translatePath(self.datadir + "last_run.txt"),'utf-8'),"w")
        
        #write out the value for the last time the program ran
        f.write(str(self.last_run));
        f.close();

    def scanRunning(self):
        #check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True            
        else:
            return False
        
    def waitForScan(self):
        #what for scan to start
        time.sleep(2)

        while(self.scanRunning()):
            time.sleep(5)

    def log(self,message):
        xbmc.log('service.libraryautoupdate: ' + message)


