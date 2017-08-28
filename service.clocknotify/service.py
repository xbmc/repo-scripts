# -*- coding: cp1252 -*-
import time
from datetime import datetime
import xbmc
import xbmcgui
import xbmcvfs
import os
import urllib2
import resources.lib.utils as utils

UPGRADE_INT = 1  #to keep track of any upgrade notifications

# ID HOME window
WINDOW_HOME = 10000
WINDOW_FULLSCREEN_VIDEO = 12005
# Control ID in window Home.xml
TimeLabel = None
TimeLabelID = None

x = int(utils.getSetting('x'))
y = int(utils.getSetting('y'))
width = int(utils.getSetting('width'))
height = int(utils.getSetting('height'))
font = utils.getSetting('font')
color = utils.getSetting('color')

class ClockNotify:
    last_run = 0
    sleep_time = 500
    schedules = []
    lock = False
    
    monitor = None

    def __init__(self):
        utils.check_data_dir()  #in case this directory does not exist yet

    def runProgram(self):
        #utils.showNotification("test for ClockNotify", "It works")
        
        #init        
        VideoWin = xbmcgui.Window(WINDOW_FULLSCREEN_VIDEO)  
        try:
            TimeLabel = VideoWin.getControl(TimeLabelID)
        except:
            TimeLabel = xbmcgui.ControlLabel(x, y, width, height, '', font, color)
            # seem useless
            TimeLabel.setAnimations([('visiblechange', 'effect=fade time=3000',)])
            TimeLabel.setVisible(False)
            
            #for test
            #TimeLabel.setVisible(True)
            #TimeLabel.setLabel(time.strftime("%H:%M:%S", time.localtime()))
            
        try:
            VideoWin.addControl(TimeLabel)
            #TimeLabel.setVisible(False)
        except:
            pass
        # get control id
        TimeLabelID = TimeLabel.getId()   
        TimeLabelVisible = False 
            
        BeginMin = 0
        DeltaSecs = 10
        
        if(BeginMin == 0):
            BeginMin = 60
        
        while(not xbmc.abortRequested):
            
            NextNotifyTimeStamp = time.time()
            localtime = time.localtime(NextNotifyTimeStamp)
            NextClockTimeDelta = (BeginMin-localtime.tm_min-1) * 60 + (60-localtime.tm_sec)
            NextNotifyTimeStamp += NextClockTimeDelta
            NextNotifyTimeStampLog = time.localtime(NextNotifyTimeStamp)
            utils.log("NextNotifyTimeStamp is " + str(NextNotifyTimeStampLog))
                
            
            sleepTime = 300 
            bInMinRange = abs(time.time() - NextNotifyTimeStamp) < 40
            if(bInMinRange):
                sleepTime = 300
            else:
                sleepTime = 1000 * 30
                
            if(bInMinRange and abs(time.time() - NextNotifyTimeStamp) < DeltaSecs and (not TimeLabelVisible)):
                TimeLabelVisible = True
                TimeLabel.setVisible(TimeLabelVisible)
                utils.log("ClockNotify setVisible ")
                
            if(bInMinRange and abs(time.time() - NextNotifyTimeStamp) > DeltaSecs and TimeLabelVisible):
                TimeLabelVisible = False
                TimeLabel.setVisible(TimeLabelVisible)
                utils.log("ClockNotify Hidden ")
            
            if(TimeLabelVisible):   
                TimeLabel.setLabel(time.strftime("%H:%M:%S", time.localtime()))
            
            utils.log("ClockNotify sleep " + str(sleepTime))
            xbmc.sleep(sleepTime)

        #clean up on exit
        VideoWin.removeControl(TimeLabel)