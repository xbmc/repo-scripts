import datetime, os, subprocess, time
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
from threading import Thread
from resources.common.xlogger import Logger
from resources.common.fix_utf8 import smartUTF8
from resources.common.fileops import popenWithTimeout

### get addon info and set globals
addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo( 'id' )
addonversion = addon.getAddonInfo( 'version' )
addonpath    = addon.getAddonInfo( 'path' ).decode( 'utf-8' )
addonicon    = xbmc.translatePath( '%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[SpeedFan Info]'
logdebug     = addon.getSetting( 'logging' ) 

lw = Logger( preamble = preamble, logdebug = logdebug )


#global used to tell the worker thread the status of the window
windowopen   = True

#capture a couple of actions to close the window
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92


def updateWindow( name, w ):
    #this is the worker thread that updates the window information every w seconds
    #this strange looping exists because I didn't want to sleep the thread for very long
    #as time.sleep() keeps user input from being acted upon
    delay = addon.getSetting( 'update_delay' )
    while windowopen and (not xbmc.abortRequested):
        #start counting up to the delay set in the preference and sleep for one second
        for i in range( int( delay ) ):
            #as long as the window is open, keep sleeping
            if windowopen:
                time.sleep(1)
            #otherwise drop out of the loop so we can exit the thread
            else:
            	break
        #as long as the window is open grab new data and refresh the window
        if windowopen:
            lw.log( ['window is still open, updating the window with new data'] );
            w._populate_from_all_logs()


class Main( xbmcgui.WindowXMLDialog ): 
    
    def __init__( self, *args, **kwargs ): pass

        
    def onInit( self ):
        self._get_settings()
        self._populate_from_all_logs()


    def onAction( self, action ):
        #captures user input and acts as needed
        lw.log( ['running onAction from SpeedFanInfoWindow class'] )
        if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
            #if the user hits back or exit, close the window
            lw.log( ['user initiated previous menu or back'] )
            global windowopen
            #set this to false so the worker thread knows the window is being closed
            windowopen = False
            lw.log( ['set windowopen to false'] )
            #tell the window to close
            lw.log( ['tell the window to close'] )
            self.close()


    def _get_log_files( self ):
        #SpeedFan rolls the log every day, so we have to look for the log file based on the date
        log_file_date = datetime.date(2011,1,29).today().isoformat().replace('-','')
        log_files = []
        for info_set in self.LOGINFO:
            if info_set['use_log'] == 'true':
                log_file = os.path.join( info_set['loc'], 'SFLog' + log_file_date + '.csv' )
                log_files.append( (info_set['title'], log_file) )
        return log_files


    def _get_settings( self ):
        self.LISTCONTROL = self.getControl( 120 )
        self.SHOWCOMPACT = addon.getSetting( 'show_compact' )
        if addon.getSetting( 'use_external_script' ) == 'true':
            self.EXTERNALSCRIPT = addon.getSetting( 'external_script' )
            self.EXTERNALTIMEOUT = int( addon.getSetting( 'external_timeout' ) )
        else:
            self.EXTERNALSCRIPT = ''
            self.EXTERNALTIMEOUT = 0
        self.LOGINFO = []        
        for i in range( 3 ):
            log_info = {}
            if i == 0:
                log_num = ''
                log_info['use_log'] = 'true'
            else:
                log_num = str( i + 1 )
                log_info['use_log'] = addon.getSetting( 'use_log' + log_num )
            log_info['loc'] = addon.getSetting( 'log_location' + log_num )
            log_info['title'] = addon.getSetting( 'log_title' + log_num )
            self.LOGINFO.append( log_info )


    def _parse_log( self ):
        #parse the log for information, see readme for how to setup SpeedFan output so that the script
        lw.log( ['started parsing log'] );
        lw.log( ['read the log file'] )
        first, last = self._read_log_file()
        temps = []
        speeds = []
        voltages = []
        percents = []
        others = []
        if first == '' or last == '':
            return temps, speeds, voltages, percents, others
        #pair up the heading with the value
        lw.log( ['pair up the heading with the value'] );
        for s_item, s_value in map( None, first.split( '\t' ), last.split( '\t' ) ):
            item_type = s_item.split( '.' )[-1].rstrip().lower()
            item_text = os.path.splitext( s_item )[0].rstrip()
            #round the number, drop the decimal and then covert to a string
            #skip the rounding for the voltage and other readings
            if item_type == 'voltage' or item_type == 'other':
                s_value = s_value.rstrip()
            else:
                try:
                    s_value = str( int( round( float( s_value.rstrip() ) ) ) )
                except ValueError:
                    s_value = str( int( round( float( s_value.rstrip().replace(',', '.') ) ) ) )
            if item_type == "temp":
                lw.log( ['put the information in the temperature array'] )
                if addon.getSetting( 'temp_scale' ) == 'Celcius':
                    temps.append( [item_text + ':', s_value + 'C'] )
                else:
                    temps.append( [item_text + ':', str( int( round( ( float( s_value ) * 1.8 ) + 32 ) ) ) + 'F'] ) 
            elif item_type == "speed":
                lw.log( ['put the information in the speed array'] )
                speeds.append( [item_text + ':', s_value + 'rpm'] )
            elif item_type == "voltage":
                lw.log( ['put the information in the voltage array'] )
                voltages.append( [item_text + ':', s_value + 'v'] )
            elif item_type == "percent":
                lw.log( ['put the information in the percent array'] );
                percents.append( [item_text, s_value + '%'] )
            elif item_type == "other":
                lw.log( ['put the information in the other array'] );
                others.append( [item_text + ":", s_value] )                
        lw.log( [temps, speeds, voltages, percents, others, 'ended parsing log, displaying results'] )
        return temps, speeds, voltages, percents, others


    def _populate_from_all_logs( self ):
        lw.log( ['reset the window to prep it for data'] )
        self.LISTCONTROL.reset()
        displayed_log = False
        #if there is an external script defined, call it
        if self.EXTERNALSCRIPT:
            lw.log( ['trying to execute external script to generate log file'] )
            result, loglines = popenWithTimeout( self.EXTERNALSCRIPT, self.EXTERNALTIMEOUT )
            lw.log( loglines )
        for title, logfile in self._get_log_files():
            self.LOGFILE = logfile
            if title:
                item = xbmcgui.ListItem( label=title )
                item.setProperty( 'istitle','true' )
                self.LISTCONTROL.addItem( item )
            if xbmcvfs.exists( logfile ):
                displayed_log = True
                self._populate_from_log()
        if displayed_log:
            self.setFocus( self.LISTCONTROL )
        else:
            command = 'XBMC.Notification(%s, %s, %s, %s)' % ( smartUTF8( language( 30103 ) ), smartUTF8( language( 30104 ) ), 6000, smartUTF8( addonicon ) )
            xbmc.executebuiltin( command )

                     
    def _populate_from_log( self ):
        #get all this stuff into list info items for the window
        temps, speeds, voltages, percents, others = self._parse_log()
        lw.log( ['starting to convert output for window'] )
        #add a fancy degree symbol to the temperatures
        for i in range(len(temps)):
              temps[i][1] = temps[i][1][:-1] + u'\N{DEGREE SIGN}' + temps[i][1][-1:]
        #now parse all the data and get it into ListIems for display on the page
        #this allows for a line space *after* the first one so the page looks pretty
        firstline_shown = False
        lw.log( ['put in all the temperature information'] )
        if temps:
            self._populate_list( language( 30100 ), temps, firstline_shown )
            firstline_shown = True
        lw.log( ['put in all the speed information (including percentages)'] )
        if speeds:
            lw.log( ['adding the percentages to the end of the speeds'] )
            en_speeds = []
            for i in range( len( speeds ) ):
                #if there is a matching percentage, add it to the end of the speed
                percent_match = False
                percent_value = ''
                for j in range( len( percents ) ):
                    if (speeds[i][0][:-1] == percents[j][0]):
                        lw.log( ['matched speed ' + speeds[i][0][:-1] + ' with percent ' + percents[j][0]] )
                        percent_match = True
                        percent_value = percents[j][1]
                if percent_match:
                    if speeds[i][1] == '0rpm':
                        en_speeds.append( (speeds[i][0], percent_value) )
                    else:
                        en_speeds.append( (speeds[i][0], speeds [i][1] + ' (' + percent_value + ')') )
                else:
                    en_speeds.append( (speeds[i][0], speeds [i][1]) )
            self._populate_list( language( 30101 ), en_speeds, firstline_shown )
            firstline_shown = True
        lw.log( ['put in all the voltage information'] )
        if voltages:
            self._populate_list( language( 30102 ), voltages, firstline_shown )
        lw.log( ['put in all the other information'] )
        if others:
            self._populate_list( language( 30105 ), others, firstline_shown )
        #add empty line at end in case there's another log file
        item = xbmcgui.ListItem()
        self.LISTCONTROL.addItem( item ) #this adds an empty line
        lw.log( ['completed putting information into lists, displaying window'] )

            
    def _populate_list( self, title, things, titlespace ):
        #this takes an arbitrary list of readings and gets them into the ListItems
        lw.log( ['create the list item for the title of the section'] ) 
        if titlespace:
            item = xbmcgui.ListItem()
            self.LISTCONTROL.addItem( item ) #this adds an empty line
        item = xbmcgui.ListItem( label=title )
        item.setProperty( 'istitle','true' )
        self.LISTCONTROL.addItem( item )
        #now add all the data (we want two columns in full mode and one column for compact)
        if self.SHOWCOMPACT == "true":
            lw.log( ['add all the data to the one column format'] )
            for onething in things:
                    item = xbmcgui.ListItem( label=onething[0],label2='' )
                    item.setProperty( 'value',onething[1] )
                    self.LISTCONTROL.addItem( item )
        else:
            lw.log( ['add all the data to the two column format'] )
            nextside = 'left'
            for  onething in things:
                if(nextside == 'left'):
                    left_label = onething[0]
                    left_value = onething[1]
                    nextside = 'right'
                else:
                    item = xbmcgui.ListItem( label=left_label,label2=onething[0] )
                    item.setProperty( 'value',left_value )
                    item.setProperty( 'value2',onething[1] )
                    nextside = 'left'
                    self.LISTCONTROL.addItem( item )
            if(nextside == 'right'):
                item = xbmcgui.ListItem( label=left_label,label2='' )
                item.setProperty( 'value',left_value )
                self.LISTCONTROL.addItem( item )


    def _parse_line( self, f, s_pos ):
        file_size = f.size()
        read_size = int( addon.getSetting( 'read_size' ) )
        if s_pos == 2:
            direction = -1
            offset = read_size
        else:
            direction = 1
            offset = 0
        while True:
            if file_size < read_size:
                read_size = file_size
            f.seek( direction*offset, s_pos )
            read_str = f.read( read_size )
            lw.log( [read_str] )
            # Remove newline at the end
            try:
                if read_str[offset - 1] == '\n':
                    read_str = read_str[0:-1]
            except:
                pass
            lines = read_str.split('\n')
            if len( lines ) > 1:  # Got a complete line
                if s_pos == 2:
                    return lines[-1]
                else:
                    return lines[0]
            if offset == file_size:   # Reached the beginning
                return ''
            offset += read_size


    def _read_log_file( self ):
        #try and open the log file
        lw.log( ['trying to open logfile ' + self.LOGFILE] )
        try:
            f = xbmcvfs.File( self.LOGFILE )
        except Exception, e:
            lw.log( ['unexpected error when reading log file', e], xbmc.LOGERROR )
            return ('', '')
        lw.log( ['opened logfile ' + self.LOGFILE] )
        #get the first and last line of the log file
        #the first line has the header information, and the last line has the last log entry
        first = self._parse_line( f, 0 )
        last = self._parse_line( f, 2 )
        f.close()
        lw.log( ['first line: ' + first, 'last line: ' + last] )
        return first, last


#run the script
if ( __name__ == "__main__" ):
    lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
    lw.log( ['debug logging set to %s' % logdebug], xbmc.LOGNOTICE )
    if xbmcgui.Window( 10000 ).getProperty( "speedfan.running" ) == "true":
        lw.log( ['script already running, aborting subsequent run attempts'] )
    else:
        xbmcgui.Window( 10000 ).setProperty( "speedfan.running",  "true" )
        if (addon.getSetting('show_compact') == "true"):
            transparency_image = "speedfan-panel-compact-" + str(int(round(float(addon.getSetting('transparency'))))) + ".png"
            xbmcgui.Window( 10000 ).setProperty( "speedfan.panel.compact",  transparency_image )
            #create a new object to get all the work done
            w = Main( "speedfaninfo-compact.xml", addonpath )
        else:
            #create a new object to get all the work done
            w = Main( "speedfaninfo-main.xml", addonpath )
        #create and start a separate thread for the looping process that updates the window
        t1 = Thread( target=updateWindow,args=("thread 1", w) )
        t1.setDaemon( True )
        t1.start()
        #create and open the window
        w.doModal()
        #just some cleanup
        del t1
        del w
        xbmcgui.Window(10000).setProperty( "speedfan.running",  "false" )
lw.log( ['script stopped'], xbmc.LOGNOTICE )