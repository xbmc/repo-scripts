# -*- coding: cp1252 -*-
import time
from datetime import datetime
import xbmc
import xbmcgui
import xbmcvfs
import os
import urllib2
import resources.lib.utils as utils
from resources.lib.croniter import croniter

class AutoUpdater:
    last_run = 0
    sleep_time = 500
    schedules = []
    lock = False
    
    monitor = None
    
    #setup the timer amounts
    timer_amounts = {}
    timer_amounts['0'] = 1
    timer_amounts['1'] = 2
    timer_amounts['2'] = 4
    timer_amounts['3'] = 6
    timer_amounts['4'] = 12
    timer_amounts['5'] = 24

    def __init__(self):
        utils.check_data_dir()  #in case this directory does not exist yet
        self.monitor = UpdateMonitor(update_settings = self.createSchedules,after_scan = self.databaseUpdated)
        self.readLastRun()

        #force and update on startup to create the array
        self.createSchedules(True)
        
    def runProgram(self):
        #a one-time catch for the startup delay
        if(int(utils.getSetting("startup_delay")) != 0):
            count = 0
            while count < len(self.schedules):
                if(time.time() > self.schedules[count].next_run):
                    #we missed at least one update, fix this
                    self.schedules[count].next_run = time.time() + int(utils.getSetting("startup_delay")) * 60
                count = count + 1
                
        #program has started, check if we should show a notification
        self.showNotify()

        while(not xbmc.abortRequested):

            #don't check unless new minute
            if(time.time() > self.last_run + 60):
                self.readLastRun()

                self.evalSchedules()

            xbmc.sleep(self.sleep_time)

        #clean up monitor on exit
        del self.monitor

    def evalSchedules(self):
        if(not self.lock):
            now = time.time()
        
            count = 0
            tempLastRun = self.last_run
            while count < len(self.schedules):
                cronJob = self.schedules[count]
            
                if(cronJob.next_run <= now):
                    if(xbmc.Player().isPlaying() == False or utils.getSetting("run_during_playback") == "true"):

                        if(utils.getSetting('run_on_idle') == 'false' or (utils.getSetting('run_on_idle') == 'true' and self.monitor.screensaver_running)):
                            
                            #check for valid network connection
                            if(self._networkUp()):
                            
                                #check if this scan was delayed due to playback
                                if(cronJob.on_delay == True):
                                    #add another minute to the delay
                                    self.schedules[count].next_run = now + 60
                                    self.schedules[count].on_delay = False
                                    utils.log(cronJob.name + " paused due to playback")
                        
                                elif(self.scanRunning() == False):
                                    #run the command for this job
                                    utils.log(cronJob.name)

                                    if(cronJob.timer_type == 'xbmc'):
                                        xbmc.executebuiltin(cronJob.command)
                                    else:
                                        self.cleanLibrary(cronJob.command)

                                    #find the next run time
                                    cronJob.next_run = self.calcNextRun(cronJob.expression,now)
                                    self.schedules[count] = cronJob
                                
                                elif(self.scanRunning() == True):
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

            #write last run time
            now = time.time()
            self.last_run = now - (now % 60)
        
    def createSchedules(self,forceUpdate = False):
        utils.log("update timers")
        self.lock = True   #lock so the eval portion does not run
        self.schedules = []
            
        if(utils.getSetting('clean_libraries') == 'true'):
            #create clean schedule (if needed)
            if(int(utils.getSetting("clean_timer")) != 0):
                    
                if(utils.getSetting('library_to_clean') == '0' or utils.getSetting('library_to_clean') == '1'):
                    #video clean schedule starts at 12am by default
                    aSchedule = CronSchedule()
                    aSchedule.name = utils.getString(30048)
                    aSchedule.timer_type = utils.__addon_id__
                    aSchedule.command = 'video'
                    if(int(utils.getSetting("clean_timer")) == 4):
                        aSchedule.expression = utils.getSetting("clean_video_cron_expression")
                    else:
                        aSchedule.expression = "0 0 " + aSchedule.cleanLibrarySchedule(int(utils.getSetting("clean_timer")))
                    aSchedule.next_run = self.calcNextRun(aSchedule.expression,time.time())

                    self.schedules.append(aSchedule)
                        
                if(utils.getSetting('library_to_clean') == '2' or utils.getSetting('library_to_clean') == '0'):
                    #music clean schedule starts at 2am by default
                    aSchedule = CronSchedule()
                    aSchedule.name = utils.getString(30049)
                    aSchedule.timer_type = utils.__addon_id__
                    aSchedule.command = 'music'
                    if(int(utils.getSetting("clean_timer")) == 4):
                        aSchedule.expression = utils.getSetting("clean_music_cron_expression")
                    else:
                        aSchedule.expression = "0 2 " + aSchedule.cleanLibrarySchedule(int(utils.getSetting("clean_timer")))
                    aSchedule.next_run = self.calcNextRun(aSchedule.expression,time.time())
    
                    self.schedules.append(aSchedule)
                                                                                

        if(utils.getSetting('update_video') == 'true'):
            utils.log("Creating timer for Video Library");
            #create the video schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30012)
            aSchedule.command = 'UpdateLibrary(video)'
            aSchedule.expression = self.checkTimer('video')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                
            self.schedules.append(aSchedule)

        if(utils.getSetting('update_music') == 'true'):
            utils.log("Creating timer for Music Library");
            #create the music schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30013)
            aSchedule.command = 'UpdateLibrary(music)'
            aSchedule.expression = self.checkTimer('music')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                
            self.schedules.append(aSchedule)

        if(utils.getSetting('use_custom_1_path') == 'true'):
            utils.log("Creating timer for Custom Path 1");
            #create a custom video path schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30020)
            aSchedule.command = 'UpdateLibrary(video,' + utils.getSetting('custom_1_scan_path') + ')'
            aSchedule.expression = self.checkTimer('custom_1')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                
            self.schedules.append(aSchedule)

        if(utils.getSetting('use_custom_2_path') == 'true'):
            utils.log("Creating timer for Custom Path 2");
            #create a custom video path schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30021)
            aSchedule.command = 'UpdateLibrary(video,' + utils.getSetting('custom_2_scan_path') + ')'
            aSchedule.expression = self.checkTimer('custom_2')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                
            self.schedules.append(aSchedule)

        if(utils.getSetting('use_custom_3_path') == 'true'):
            utils.log("Creating timer for Custom Path 3");
            #create a custom video path schedule
            aSchedule = CronSchedule()
            aSchedule.name = utils.getString(30022)
            aSchedule.command = 'UpdateLibrary(video,' + utils.getSetting('custom_3_scan_path') + ')'
            aSchedule.expression = self.checkTimer('custom_3')
            aSchedule.next_run = self.calcNextRun(aSchedule.expression,self.last_run)
                
            self.schedules.append(aSchedule)

        #release the lock
        self.lock = False
        
        #show any notifications
        self.showNotify(not forceUpdate)
            
    def checkTimer(self,settingName):
        result = ''
        
        #figure out if using standard or advanced timer
        if(utils.getSetting(settingName + '_advanced_timer') == 'true'):
            #copy the expression
            result = utils.getSetting(settingName + "_cron_expression")
        else:
            result = '0 */' + str(self.timer_amounts[utils.getSetting(settingName + "_timer")]) + ' * * *'

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
        if(next_run_time.next_run > time.time() and utils.getSetting('notify_next_run') == 'true' and displayToScreen == True):
            utils.showNotification(utils.getString(30000),next_run_time.name + " - " + inWords)
                                   
        return inWords    

    def nextRunCountdown(self,nextRun):
        #compare now with next date
        cronDiff = nextRun - time.time()

        if cronDiff < 0:
            return ""
        
        hours = int((cronDiff / 60) / 60)
        minutes = int(round(cronDiff / 60.0 - hours * 60))

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
        

    def cleanLibrary(self,media_type):
        #check if we should verify with user first
        if(utils.getSetting('user_confirm_clean') == 'true'):
            #user can decide 'no' here and exit this
            runClean = xbmcgui.Dialog().yesno(utils.getString(30000),utils.getString(30052),line2=utils.getString(30053),autoclose=15000)
            if(not runClean):
                return
                
        #run the clean operation
        utils.log("Cleaning Database")
        xbmc.executebuiltin("CleanLibrary(" + media_type + ")")

        #write last run time, will trigger notifications
        self.writeLastRun()
    
    def readLastRun(self):
        if(self.last_run == 0):
            #read it in from the settings
            if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "last_run.txt"))):
                
                runFile = xbmcvfs.File(xbmc.translatePath(utils.data_dir() + "last_run.txt"))

                try:
                    #there may be an issue with this file, we'll get it the next time through
                    self.last_run = float(runFile.read())
                except ValueError:
                    self.last_run = 0 

                runFile.close()
            else:
               self.last_run = 0

    def writeLastRun(self):
        runFile = xbmcvfs.File(xbmc.translatePath(utils.data_dir() + "last_run.txt"),'w')
        runFile.write(str(self.last_run))
        runFile.close()

        self.showNotify(True)

    def scanRunning(self):
        #check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True            
        else:
            return False
        
    def databaseUpdated(self,database):
        #check if we should clean the library
        if(utils.getSetting('clean_libraries') == 'true'):
            #check if should update while playing media
            if(xbmc.Player().isPlaying() == False or utils.getSetting("run_during_playback") == "true"):
                if(int(utils.getSetting("clean_timer")) == 0):
                    #check if we should clean music, or video
                    if((utils.getSetting('library_to_clean') == '0' or utils.getSetting('library_to_clean') == '1') and database == 'video'):
                        self.cleanLibrary(database)
                    if((utils.getSetting('library_to_clean') == '2' or utils.getSetting('library_to_clean') == '0') and database == 'music'):
                        self.cleanLibrary(database)

        #writeLastRun will trigger notifications
        self.writeLastRun()

    def _networkUp(self):
        utils.log("Starting network check")
        try:
            response = urllib2.urlopen('http://www.google.com',timeout=1)
            return True
        except:
            pass

        return False

class CronSchedule:
    expression = ''
    name = 'library'
    timer_type = 'xbmc'
    command = 'UpdateLibrary(video)'
    next_run = 0
    on_delay = False  #used to defer processing until after player finishes

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

class UpdateMonitor(xbmc.Monitor):
    update_settings = None
    after_scan = None
    screensaver_running = False
    
    def __init__(self,*args,**kwargs):
        xbmc.Monitor.__init__(self)
        self.update_settings = kwargs['update_settings']
        self.after_scan = kwargs['after_scan']

    def onSettingsChanged(self):
        xbmc.sleep(1000) #slight delay for notifications
        self.update_settings()

    def onDatabaseUpdated(self,database):
        self.after_scan(database)

    def onScreensaverActivated(self):
        utils.log("screen saver on",xbmc.LOGDEBUG)
        self.screensaver_running = True

    def onScreensaverDeactivated(self):
        utils.log("screen saver off",xbmc.LOGDEBUG)
        self.screensaver_running = False
        
