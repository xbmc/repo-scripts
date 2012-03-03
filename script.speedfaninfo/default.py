import os, sys, time, datetime
import xbmcaddon, xbmc, xbmcgui
from threading import Thread
#this is a wrapper for the xbmc.log that adds logic for verbose or standard logging
import xlogger

### get addon info and set globals
__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__author__       = __addon__.getAddonInfo('author')
__version__      = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path')
__addondir__     = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__icon__         = __addon__.getAddonInfo('icon')
__localize__     = __addon__.getLocalizedString

#global used to tell the worker thread the status of the window
__windowopen__   = True

#capture a couple of actions to close the window
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92

#create a global logger object and set the preamble
lw = xlogger.inst
lw.setPreamble ('[speedfaninfo]')

#this is the class for creating and populating the window 
class SpeedFanInfoWindow(xbmcgui.WindowXMLDialog): 
    
    def __init__(self, *args, **kwargs):
        # and define it as self
        lw.log('running __init__ from SpeedFanInfoWindow class', 'verbose')

    def onInit(self):
        #tell the object to go read the log file, parse it, and put it into listitems for the XML
        lw.log('running inInit from SpeedFanInfoWindow class', 'verbose')
        self.populateFromLog()

    def onAction(self, action):
        #captures user input and acts as needed
        lw.log('running onAction from SpeedFanInfoWindow class', 'verbose')
        if(action == ACTION_PREVIOUS_MENU or action == ACTION_BACK):
            #if the user hits back or exit, close the window
            lw.log('user initiated previous menu or back', 'verbose')
            global __windowopen__
            #set this to false so the worker thread knows the window is being closed
            __windowopen__ = False
            lw.log('set windowopen to false', 'verbose')
            #tell the window to close
            lw.log('tell the window to close', 'verbose')
            self.close()
            
    def populateFromLog(self):        
        #get all this stuff into list info items for the window
        lw.log('running populateFromLog from SpeedFanInfoWindow class', 'verbose')
        #create new log parser and logger obejects
        lw.log('create new LogParser object', 'verbose')
        lp = LogParser()
        #get the information from the SpeedFan Log
        lw.log('ask the LogParser to get temps, speeds, voltages, and percents', 'verbose')
        temps, speeds, voltages, percents = lp.parseLog()
        lw.log('starting to convert output for window', 'verbose')
        #add a fancy degree symbol to the temperatures
        lw.log('add fancy degree symbol to temperatures', 'verbose')
        for i in range(len(temps)):
            temps[i][1] = temps[i][1][:-1] + unichr(176).encode("latin-1") + temps[i][1][-1:]
        #now parse all the data and get it into ListIems for display on the page
        lw.log('reset the window to prep it for data', 'verbose')
        self.getControl(120).reset()
        #this allows for a line space *after* the first one so the page looks pretty
        firstline_shown = False
        #put in all the temperature information
        lw.log('put in all the temperature information', 'verbose')
        if(len(temps) > 0):
            self.populateList(__localize__(30100), temps, firstline_shown)
            firstline_shown = True
        #put in all the speed information (including percentage)
        lw.log('put in all the speed information (including percentages)', 'verbose')
        if(len(speeds) > 0):
            #please don't ask why this is so complicated, the simple way caused a fatal error on Windows
            if(len(speeds) == len(percents)):
                en_speeds = []
                #add the percentage information to the end of the speed
                lw.log('adding the percentages to the end of the speeds', 'verbose')
                for i in range(len(speeds)):
                    en_speeds.append((speeds[i][0], speeds [i][1] + ' (' + percents[i][1] + ')'))
            else:
                en_speeds = speeds
            self.populateList(__localize__(30101), en_speeds, firstline_shown)
            firstline_shown = True
        #put in all the voltage information
        lw.log('put in all the voltage information', 'verbose')
        if(len(voltages) > 0):
            self.populateList(__localize__(30102), voltages, firstline_shown)
        #log that we're done and ready to show the page
        lw.log('completed putting information into lists, displaying window', 'standard')
            
    def populateList(self, title, things, titlespace):
        #this takes an arbitrating list of readings and gets them into the ListItems
        lw.log('running populateList from SpeedFanInfoWindow class', 'verbose')        
        #create the list item for the title of the section
        lw.log('create the list item for the title of the section', 'verbose')        
        if(titlespace):
            item = xbmcgui.ListItem()
            self.getControl(120).addItem(item) #this adds an empty line
        item = xbmcgui.ListItem(label=title)
        item.setProperty('istitle','true')
        self.getControl(120).addItem(item)
        #now add all the data (we want two columns to make good use of the page)
        lw.log('add all the data to the two column format', 'verbose')        
        nextside = 'left'
        for  onething in things:
            if(nextside == 'left'):
                left_label = onething[0]
                left_value = onething[1]
                nextside = 'right'
            else:
                item = xbmcgui.ListItem(label=left_label,label2=onething[0])
                item.setProperty('value',left_value)
                item.setProperty('value2',onething[1])
                nextside = 'left'
                self.getControl(120).addItem(item)
        if(nextside == 'right'):
            item = xbmcgui.ListItem(label=left_label,label2='')
            item.setProperty('value',left_value)
            self.getControl(120).addItem(item)

class LogParser():
    def __init__(self):
        lw.log('running __init__ from LogParser class', 'verbose')        
        # and define it as self

    def readLogFile(self):
        #try and open the log file
        lw.log('running readLogFile from LogParser class', 'verbose')        
        #SpeedFan rolls the log every day, so we have to look for the log file based on the date
        #SpeedFan also does numerics if it has to roll the log during the day
        #but in my testing it only uses the numeric log for a couple of minutes and then goes
        #back to the main dated log, so I only read the main log file for a given date
        log_file_date = datetime.date(2011,1,29).today().isoformat().replace('-','')
        log_file_raw = __addon__.getSetting('log_location') + 'SFLog' + log_file_date
        log_file = log_file_raw + '.csv'
        lw.log('trying to open logfile ' + log_file, 'verbose')
        try:
            f = open(log_file, 'rb')
        except IOError:
            lw.log('no log file found', 'standard')
            if(__addon__.getSetting('log_location') == ''):
                xbmc.executebuiltin('XBMC.Notification("Log File Error", "No log file location defined.", 6000)')
            else:
                xbmc.executebuiltin('XBMC.Notification("Log File Error", "No log file in defined location.", 6000)')            
            return
        lw.log('opened logfile ' + log_file, 'verbose')
        #get the first and last line of the log file
        #the first line has the header information, and the last line has the last log entry
        #Speedfan updates the log every three seconds, so I didn't want to read the whole log
        #file in just to get the last line
        first = next(f).decode()
        read_size = 1024
        offset = read_size
        f.seek(0, 2)
        file_size = f.tell()
        while 1:
            if file_size < offset:
                offset = file_size
            f.seek(-1*offset, 2)
            read_str = f.read(offset)
            # Remove newline at the end
            if read_str[offset - 1] == '\n':
                read_str = read_str[0:-1]
            lines = read_str.split('\n')
            if len(lines) > 1:  # Got a line
                last = lines[len(lines) - 1]
                break
            if offset == file_size:   # Reached the beginning
                last = read_str
                break
            offset += read_size
        f.close()
        #some additional information for advanced logging
        lw.log('first line: ' + first, 'verbose')
        lw.log('last line: ' + last, 'verbose')
        return first, last

    def parseLog(self):
        #parse the log for information, see readme for how to setup SpeedFan output so that the script
        lw.log('running parseLog from LogParser class', 'verbose')        
        #can parse out the useful information
        lw.log('started parsing log','verbose');
        if(__addon__.getSetting('temp_scale') == 'Celcius'):
            temp_scale = 'C'
        else:
            temp_scale = 'F'
        #read the log file
        lw.log('read the log file','verbose');
        first, last = self.readLogFile()
        #pair up the heading with the value
        lw.log('pair up the heading with the value','verbose');
        temps = []
        speeds = []
        voltages = []
        percents = []
        for s_item, s_value in map(None, first.split('\t'), last.split('\t')):
            item_type = s_item.split('.')[-1].rstrip().lower()
            item_text = os.path.splitext(s_item)[0].rstrip()
            #round the number, drop the decimal and then covert to a string
            #skip the rounding for the voltage reading
            if(item_type == 'voltage'):
                s_value = s_value.rstrip()
            else:
                try:
                    s_value = str(int(round(float(s_value.rstrip()))))
                except ValueError:
                    s_value = str(int(round(float(s_value.rstrip().replace(',', '.')))))
            if(item_type == "temp"):
                #put this info in the temperature array
                lw.log('put the information in the temperature array','verbose');
                temps.append([item_text + ':', s_value + temp_scale])
            elif(item_type == "speed"):
                #put this info in the speed array
                lw.log('put the information in the speed array','verbose');
                speeds.append([item_text + ':', s_value + 'rpm'])
            elif(item_type == "voltage"):
                #put this info in the voltage array
                lw.log('put the information in the voltage array','verbose');
                voltages.append([item_text + ':', s_value + 'v'])
            elif(item_type == "percent"):
                #put this info to the percent array
                lw.log('put the information in the percent array','verbose');
                percents.append([item_text, s_value + '%'])
        #log some additional data if advanced logging is one
        lw.log(temps, speeds, voltages, percents, 'verbose')
        #log that we're done parsing the file
        lw.log('ended parsing log, displaying results', 'standard')
        return temps, speeds, voltages, percents
                
def updateWindow(name, w):
    #this is the worker thread that updates the window information every w seconds
    #this strange looping exists because I didn't want to sleep the thread for very long
    #as time.sleep() keeps user input from being acted upon
    lw.log('running the worker thread from inside the def','verbose');
    while __windowopen__:
        #start counting up to the delay set in the preference and sleep for one second
        lw.log('start counting the delay set in the preference','verbose');
        for i in range(int(__addon__.getSetting('update_delay'))):
            #as long as the window is open, keep sleeping
            if __windowopen__:
                lw.log('window is still open, sleep 1 second','verbose');
                time.sleep(1)
            #otherwise drop out of the loop so we can exit the thread
            else:
            	break
        #as long as the window is open grab new data and refresh the window
        if __windowopen__:
            lw.log('window is still open, updating the window with new data','verbose');
            w.populateFromLog()

#run the script
#create a new object to get all the work done
lw.log('attempting to create main script object', 'verbose')
w = SpeedFanInfoWindow("speedfaninfo-main.xml", __addonpath__, "Default")
lw.log('main script object created', 'attempting to create worker thread' 'verbose')
#create and start a separate thread for the looping process that updates the window
t1 = Thread(target=updateWindow,args=("thread 1",w))
t1.setDaemon(True)
lw.log('worker thread created', 'attempting to start worker thread' 'verbose')
t1.start()
lw.log('worker thread started', 'request window open via doModal', 'verbose')
#create and open the window
w.doModal()
#just some cleanup
lw.log('attempting to delete main object', 'attempting to delete worker thread', 'verbose')
del t1
del w
lw.log('main object deleted', 'worker thread deleted', 'exiting script', 'verbose')
del lw