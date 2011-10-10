import time
import xbmc
import xbmcaddon
                
class AutoUpdater:             
    def runProgram(self):
        Addon = xbmcaddon.Addon(id='service.libraryautoupdate')
        
        #set last run to 0 so it will run the first time
        self.last_run = 0
        
        while(not xbmc.abortRequested):
            now = time.time()
            
            timer_amounts = {}
            timer_amounts['0'] = 1
            timer_amounts['1'] = 2
            timer_amounts['2'] = 5
            timer_amounts['3'] = 10
            timer_amounts['4'] = 15
            timer_amounts['5'] = 24

            #only do this if we are not playing anything
            if(xbmc.Player().isPlaying() == False and now > self.last_run + (timer_amounts[Addon.getSetting('timer_amount')] * 60 * 60)):
                #run the update since we have just started the program
                if(Addon.getSetting('update_video') == 'true'):
                    xbmc.log('Updating Video')
                    xbmc.executebuiltin('UpdateLibrary(video)')
                if(Addon.getSetting('update_music') == 'true'):
                    xbmc.log('Updating Music')
                    xbmc.executebuiltin('UpdateLibrary(music)')
                    
                #reset the last run timer    
                self.last_run = now
                xbmc.log("Update Library will run again in " + str(timer_amounts[Addon.getSetting("timer_amount")]) + " hours")
                
            #put the thread to sleep for x number of seconds
            time.sleep(60)

#run the program
xbmc.log("Update Library Service starting...")
AutoUpdater().runProgram()

