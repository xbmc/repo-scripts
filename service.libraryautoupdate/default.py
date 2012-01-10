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
            sleep_time = 10
            
            timer_amounts = {}
            timer_amounts['0'] = 1
            timer_amounts['1'] = 2
            timer_amounts['2'] = 5
            timer_amounts['3'] = 10
            timer_amounts['4'] = 15
            timer_amounts['5'] = 24

            #check if we should run an update
            if(now > self.last_run + (timer_amounts[Addon.getSetting('timer_amount')] * 60 * 60)):

                #make sure player isn't running
                if(xbmc.Player().isPlaying() == False):
                    
                    if(self.scanRunning() == False):
                        
                        #run the update
                        if(Addon.getSetting('update_video') == 'true'):
                            xbmc.log('Updating Video')
                            xbmc.executebuiltin('UpdateLibrary(video)')
                            time.sleep(1)
                            
                        if(Addon.getSetting('update_music') == 'true'):
                            #check if scan is running again, wait until finished if it is
                            while(self.scanRunning()):
                                time.sleep(10)
                            
                            xbmc.log('Update Music')
                            xbmc.executebuiltin('UpdateLibrary(music)')
                        
                        #reset the last run timer    
                        self.last_run = now
                        xbmc.log("Update Library will run again in " + str(timer_amounts[Addon.getSetting("timer_amount")]) + " hours")
                else:
                    xbmc.log("Player is running, waiting until finished")
                    
            #put the thread to sleep for x number of seconds
            time.sleep(sleep_time)
            
    def scanRunning(self):
        #check if any type of scan is currently running
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True
        else:
            return False
           
#run the program
xbmc.log("Update Library Service starting...")
AutoUpdater().runProgram()

