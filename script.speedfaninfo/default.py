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
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ ).decode("utf-8")
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
        lw.log('running __init__ from SpeedFanInfoWindow class', xbmc.LOGDEBUG)
        
    def onInit(self):
        #tell the object to go read the log file, parse it, and put it into listitems for the XML
        lw.log('running inInit from SpeedFanInfoWindow class', xbmc.LOGDEBUG)
        self.populateFromLog()

    def onAction(self, action):
        #captures user input and acts as needed
        lw.log('running onAction from SpeedFanInfoWindow class', xbmc.LOGDEBUG)
        if(action == ACTION_PREVIOUS_MENU or action == ACTION_BACK):
            #if the user hits back or exit, close the window
            lw.log('user initiated previous menu or back', xbmc.LOGDEBUG)
            global __windowopen__
            #set this to false so the worker thread knows the window is being closed
            __windowopen__ = False
            lw.log('set windowopen to false', xbmc.LOGDEBUG)
            #tell the window to close
            lw.log('tell the window to close', xbmc.LOGDEBUG)
            self.close()
            
    def populateFromLog(self):        
        #get all this stuff into list info items for the window
        lw.log('attempting to add info of ' +  xbmcgui.Window(xbmcgui.getCurrentWindowId()).getProperty("panel.compact") , xbmc.LOGDEBUG)
        lw.log('running populateFromLog from SpeedFanInfoWindow class', xbmc.LOGDEBUG)
        #create new log parser and logger obejects
        lw.log('create new LogParser object', xbmc.LOGDEBUG)
        lp = LogParser()
        #get the information from the SpeedFan Log
        lw.log('ask the LogParser to get temps, speeds, voltages, and percents', xbmc.LOGDEBUG)
        temps, speeds, voltages, percents = lp.parseLog()
        lw.log('starting to convert output for window', xbmc.LOGDEBUG)
        #add a fancy degree symbol to the temperatures
        lw.log('add fancy degree symbol to temperatures', xbmc.LOGDEBUG)
        for i in range(len(temps)):
              temps[i][1] = temps[i][1][:-1] + u'\N{DEGREE SIGN}' + temps[i][1][-1:]
      #now parse all the data and get it into ListIems for display on the page
        lw.log('reset the window to prep it for data', xbmc.LOGDEBUG)
        self.getControl(120).reset()
        #this allows for a line space *after* the first one so the page looks pretty
        firstline_shown = False
        #put in all the temperature information
        lw.log('put in all the temperature information', xbmc.LOGDEBUG)
        if(len(temps) > 0):
            self.populateList(__localize__(30100), temps, firstline_shown)
            firstline_shown = True
        #put in all the speed information (including percentage)
        lw.log('put in all the speed information (including percentages)', xbmc.LOGDEBUG)
        if(len(speeds) > 0):
            lw.log('adding the percentages to the end of the speeds', xbmc.LOGDEBUG)
            en_speeds = []
            for i in range(len(speeds)):
                #if there is a matching percentage, add it to the end of the speed
                percent_match = False
                percent_value = ''
                for j in range(len(percents)):
                    if (speeds[i][0][:-1] == percents[j][0]):
                        lw.log('matched speed ' + speeds[i][0][:-1] + ' with percent ' + percents[j][0], xbmc.LOGDEBUG)
                        percent_match = True
                        percent_value = percents[j][1]
                if percent_match:
                    en_speeds.append((speeds[i][0], speeds [i][1] + ' (' + percent_value + ')'))
                else:
                    en_speeds.append((speeds[i][0], speeds [i][1]))
            self.populateList(__localize__(30101), en_speeds, firstline_shown)
            firstline_shown = True
        #put in all the voltage information
        lw.log('put in all the voltage information', xbmc.LOGDEBUG)
        if(len(voltages) > 0):
            self.populateList(__localize__(30102), voltages, firstline_shown)
        #log that we're done and ready to show the page
        lw.log('completed putting information into lists, displaying window', xbmc.LOGDEBUG)
            
    def populateList(self, title, things, titlespace):
        #this takes an arbitrating list of readings and gets them into the ListItems
        lw.log('running populateList from SpeedFanInfoWindow class', xbmc.LOGDEBUG)        
        #create the list item for the title of the section
        lw.log('create the list item for the title of the section', xbmc.LOGDEBUG)        
        if(titlespace):
            item = xbmcgui.ListItem()
            self.getControl(120).addItem(item) #this adds an empty line
        item = xbmcgui.ListItem(label=title)
        item.setProperty('istitle','true')
        self.getControl(120).addItem(item)
        #now add all the data (we want two columns inf full mode and one column for compact)
        if (__addon__.getSetting('show_compact') == "true"):
            lw.log('add all the data to the one column format', xbmc.LOGDEBUG)
            for onething in things:
                    item = xbmcgui.ListItem(label=onething[0],label2='')
                    item.setProperty('value',onething[1])
                    self.getControl(120).addItem(item)
        else:
            lw.log('add all the data to the two column format', xbmc.LOGDEBUG)        
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
        lw.log('running __init__ from LogParser class', xbmc.LOGDEBUG)        
        # and define it as self

    def readLogFile(self):
        #try and open the log file
        lw.log('running readLogFile from LogParser class', xbmc.LOGDEBUG)        
        #SpeedFan rolls the log every day, so we have to look for the log file based on the date
        #SpeedFan also does numerics if it has to roll the log during the day
        #but in my testing it only uses the numeric log for a couple of minutes and then goes
        #back to the main dated log, so I only read the main log file for a given date
        log_file_date = datetime.date(2011,1,29).today().isoformat().replace('-','')
        log_file_raw = __addon__.getSetting('log_location') + 'SFLog' + log_file_date
        log_file = log_file_raw + '.csv'
        lw.log('trying to open logfile ' + log_file, xbmc.LOGDEBUG)
        try:
            f = open(log_file, 'rb')
        except IOError:
            lw.log('no log file found', xbmc.LOGERROR)
            if(__addon__.getSetting('log_location') == ''):
                xbmc.executebuiltin('XBMC.Notification("Log File Error", "No log file location defined.", 6000, '+ __addonicon__ +')')
            else:
                xbmc.executebuiltin('XBMC.Notification("Log File Error", "No log file in defined location.", 6000, ' + __addonicon__ + ')')            
            return
        lw.log('opened logfile ' + log_file, xbmc.LOGDEBUG)
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
        lw.log('first line: ' + first, xbmc.LOGDEBUG)
        lw.log('last line: ' + last, xbmc.LOGDEBUG)
        return first, last

    def parseLog(self):
        #parse the log for information, see readme for how to setup SpeedFan output so that the script
        lw.log('running parseLog from LogParser class', xbmc.LOGDEBUG)        
        #can parse out the useful information
        lw.log('started parsing log',xbmc.LOGDEBUG);
        if(__addon__.getSetting('temp_scale') == 'Celcius'):
            temp_scale = 'C'
        else:
            temp_scale = 'F'
        #read the log file
        lw.log('read the log file',xbmc.LOGDEBUG);
        first, last = self.readLogFile()
        #pair up the heading with the value
        lw.log('pair up the heading with the value',xbmc.LOGDEBUG);
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
                lw.log('put the information in the temperature array',xbmc.LOGDEBUG);
                temps.append([item_text + ':', s_value + temp_scale])
            elif(item_type == "speed"):
                #put this info in the speed array
                lw.log('put the information in the speed array',xbmc.LOGDEBUG);
                speeds.append([item_text + ':', s_value + 'rpm'])
            elif(item_type == "voltage"):
                #put this info in the voltage array
                lw.log('put the information in the voltage array',xbmc.LOGDEBUG);
                voltages.append([item_text + ':', s_value + 'v'])
            elif(item_type == "percent"):
                #put this info to the percent array
                lw.log('put the information in the percent array',xbmc.LOGDEBUG);
                percents.append([item_text, s_value + '%'])
        #log some additional data if advanced logging is one
        lw.log(temps, speeds, voltages, percents, xbmc.LOGDEBUG)
        #log that we're done parsing the file
        lw.log('ended parsing log, displaying results', xbmc.LOGDEBUG)
        return temps, speeds, voltages, percents
                
def updateWindow(name, w):
    #this is the worker thread that updates the window information every w seconds
    #this strange looping exists because I didn't want to sleep the thread for very long
    #as time.sleep() keeps user input from being acted upon
    lw.log('running the worker thread from inside the def',xbmc.LOGDEBUG);
    while __windowopen__ and (not xbmc.abortRequested):
        #start counting up to the delay set in the preference and sleep for one second
        lw.log('start counting the delay set in the preference',xbmc.LOGDEBUG);
        for i in range(int(__addon__.getSetting('update_delay'))):
            #as long as the window is open, keep sleeping
            if __windowopen__:
                lw.log('window is still open, sleep 1 second',xbmc.LOGDEBUG);
                time.sleep(1)
            #otherwise drop out of the loop so we can exit the thread
            else:
            	break
        #as long as the window is open grab new data and refresh the window
        if __windowopen__:
            lw.log('window is still open, updating the window with new data',xbmc.LOGDEBUG);
            w.populateFromLog()

#run the script
if ( xbmcgui.Window(10000).getProperty("speedfan.running") == "true" ):
    lw.log('script already running, aborting subsequent run attempts', xbmc.LOGNOTICE)
else:
    xbmcgui.Window(10000).setProperty( "speedfan.running",  "true" )
    lw.log('starting script', xbmc.LOGNOTICE)
    lw.log('attempting to create main script object', xbmc.LOGDEBUG)
    if (__addon__.getSetting('show_compact') == "true"):
        transparency_image = "speedfan-panel-compact-" + str(int(round(float(__addon__.getSetting('transparency'))))) + ".png"
        xbmcgui.Window(10000).setProperty("speedfan.panel.compact",  transparency_image)
        #create a new object to get all the work done
        w = SpeedFanInfoWindow("speedfaninfo-compact.xml", __addonpath__, "Default")
    else:
        #create a new object to get all the work done
        w = SpeedFanInfoWindow("speedfaninfo-main.xml", __addonpath__, "Default")
    lw.log('main script object created', 'attempting to create worker thread', xbmc.LOGDEBUG)
    #create and start a separate thread for the looping process that updates the window
    t1 = Thread(target=updateWindow,args=("thread 1",w))
    t1.setDaemon(True)
    lw.log('worker thread created', 'attempting to start worker thread', xbmc.LOGDEBUG)
    t1.start()
    lw.log('worker thread started', 'request window open via doModal', xbmc.LOGDEBUG)
    #create and open the window
    w.doModal()
    #just some cleanup
    lw.log('attempting to delete main object', 'attempting to delete worker thread', xbmc.LOGDEBUG)
    del t1
    del w
    lw.log('main object deleted', 'worker thread deleted', xbmc.LOGDEBUG)
    lw.log('exiting script', xbmc.LOGNOTICE)
    del lw
    xbmcgui.Window(10000).setProperty( "speedfan.running",  "false" )