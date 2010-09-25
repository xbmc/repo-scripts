import os
import xbmc
import xbmcaddon

Addon = xbmcaddon.Addon(id=os.path.basename(os.getcwd()))

class Main:

    def __init__(self):
	#cancel the alarm if it is already running
	xbmc.executebuiltin('CancelAlarm(updatelibrary)')
	
        timer_amounts = {}
        timer_amounts['0'] = '120'
        timer_amounts['1'] = '300'
        timer_amounts['2'] = '600'
        timer_amounts['3'] = '900'
        timer_amounts['4'] = '1440'
        
        #only do this if we are not playing anything
        if(xbmc.Player().isPlaying() == False):
            #run the update since we have just started the program
            if(Addon.getSetting('update_video')):
                xbmc.executebuiltin('UpdateLibrary(video)')
            if(Addon.getSetting('update_music')):
                xbmc.executebuiltin('UpdateLibary(music)')
        
        #reset the timer
        xbmc.executebuiltin('AlarmClock(updatelibrary,XBMC.RunScript(script.libraryautoupdate),' +
                            timer_amounts[Addon.getSetting('timer_amount')] +  ',true)')

        xbmc.log('update library add-on complete')
#run the program
run_program = Main()
