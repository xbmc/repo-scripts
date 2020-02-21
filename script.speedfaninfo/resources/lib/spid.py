import datetime, os
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs
try:
    from itertools import izip_longest as _zip_longest
except ImportError:
    from itertools import zip_longest as _zip_longest
from resources.lib.xlogger import Logger
from resources.lib.kodisettings import getSettingBool, getSettingInt, getSettingString

addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo( 'id' )
addonversion = addon.getAddonInfo( 'version' )
addonpath    = addon.getAddonInfo( 'path' )
addonicon    = xbmc.translatePath( '%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[SpeedFan Info]'
logdebug     = getSettingBool( addon, 'logging', default=False )

lw = Logger( preamble=preamble, logdebug=logdebug )

lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
lw.log( ['debug logging set to %s' % logdebug], xbmc.LOGNOTICE )



class SpeedFanWindow( xbmcgui.WindowXMLDialog ):

    def __init__( self, *args, **kwargs ):
        self.KEEPRUNNING = True
        self.ACTION_PREVIOUS_MENU = 10
        self.ACTION_BACK = 92


    def onAction( self, action ):
        if action == self.ACTION_PREVIOUS_MENU or action == self.ACTION_BACK:
            lw.log( ['user initiated previous menu or back, telling addon to quit'] )
            self.KEEPRUNNING = False


    def KeepRunning( self ):
        return self.KEEPRUNNING



class Main():

    def __init__( self ):
        self._get_settings()
        self._init_vars()
        if self.GUIWINDOW.getProperty( 'SpeedFan.Running' ) == "True":
            lw.log( ['script already running, aborting subsequent run attempts'], xbmc.LOGNOTICE )
            return
        self.GUIWINDOW.setProperty( 'SpeedFan.Running',  'True' )
        self._init_window()
        self._populate_from_all_logs()
        if self.FOUNDLOGFILE:
            while not self.MONITOR.abortRequested() and self.SPEEDFANWINDOW.KeepRunning():
                for i in range( self.DELAY ):
                    if self.MONITOR.waitForAbort( 1 ) or not self.SPEEDFANWINDOW.KeepRunning():
                        break
                self._populate_from_all_logs()
        self.SPEEDFANWINDOW.close()
        self.GUIWINDOW.setProperty( 'SpeedFan.Running',  'False' )


    def _get_log_files( self ):
        log_file_date = datetime.date(2011,1,29).today().isoformat().replace('-','')
        log_files = []
        for info_set in self.LOGINFO:
            if info_set['use_log'] == 'true':
                log_file = os.path.join( info_set['loc'], 'SFLog' + log_file_date + '.csv' )
                log_files.append( (info_set['title'], log_file) )
        return log_files


    def _get_settings( self ):
        self.SHOWCOMPACT = getSettingBool( addon, 'show_compact' )
        self.TRANSPARENCY = getSettingString( addon, 'transparency', default='70' )
        self.TEMPSCALE = getSettingString( addon, 'temp_scale' )
        self.READSIZE = getSettingInt( addon, 'read_size' )
        self.DELAY = getSettingInt( addon, 'update_delay', default=30 )
        self.LOGINFO = []
        for i in range( 3 ):
            log_info = {}
            if i == 0:
                log_num = ''
                log_info['use_log'] = 'true'
            else:
                log_num = str( i + 1 )
                log_info['use_log'] = getSettingString( addon, 'use_log' + log_num )
            log_info['loc'] = getSettingString( addon, 'log_location' + log_num )
            log_info['title'] = getSettingString( addon, 'log_title' + log_num )
            self.LOGINFO.append( log_info )


    def _init_vars( self ):
        self.GUIWINDOW = xbmcgui.Window( 10000 )
        self.FOUNDLOGFILE = False
        self.MONITOR = xbmc.Monitor()


    def _init_window( self ):
        if self.SHOWCOMPACT:
            transparency_image = 'speedfan-panel-compact-%s.png' %  self.TRANSPARENCY
            self.GUIWINDOW.setProperty( 'speedfan.panel.compact',  transparency_image )
            self.SPEEDFANWINDOW = SpeedFanWindow( 'speedfaninfo-compact.xml', addonpath )
        else:
            self.SPEEDFANWINDOW = SpeedFanWindow( "speedfaninfo-main.xml", addonpath )
        self.SPEEDFANWINDOW.show()
        self.LISTCONTROL = self.SPEEDFANWINDOW.getControl( 120 )


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
        for s_item, s_value in _zip_longest( first.split( '\t' ), last.split( '\t' ) ):
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
                if self.TEMPSCALE == 'Celcius':
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
            self.SPEEDFANWINDOW.setFocus( self.LISTCONTROL )
            self.FOUNDLOGFILE = True
        else:
            lw.log( ['no logfile found, put up a notification and quitting'] )
            xbmcgui.Dialog().notification( language( 30103 ), language( 30104 ), icon=addonicon, time=6000 )


    def _populate_from_log( self ):
        #get all this stuff into list info items for the window
        temps, speeds, voltages, percents, others = self._parse_log()
        lw.log( ['starting to convert output for window'] )
        #add a fancy degree symbol to the temperatures
        formatted_temps = []
        for temp in temps:
            formatted_temps.append( [temp[0], temp[1][:-1] + u'\N{DEGREE SIGN}' + temp[1][-1:]] )
        #now parse all the data and get it into ListIems for display on the page
        #this allows for a line space *after* the first one so the page looks pretty
        firstline_shown = False
        lw.log( ['put in all the temperature information'] )
        if formatted_temps:
            self._populate_list( language( 30100 ), formatted_temps, firstline_shown )
            firstline_shown = True
        lw.log( ['put in all the speed information (including percentages)'] )
        if speeds:
            lw.log( ['adding the percentages to the end of the speeds'] )
            en_speeds = []
            for thespeed in speeds:
                #if there is a matching percentage, add it to the end of the speed
                percent_match = False
                percent_value = ''
                for thepercent in percents:
                    if (thespeed[0][:-1] == thepercent[0]):
                        lw.log( ['matched speed ' + thespeed[0][:-1] + ' with percent ' + thepercent[0]] )
                        percent_match = True
                        percent_value = thepercent[1]
                if percent_match:
                    if thespeed[1] == '0rpm':
                        en_speeds.append( (thespeed[0], percent_value) )
                    else:
                        en_speeds.append( (thespeed[0], thespeed[1] + ' (' + percent_value + ')') )
                else:
                    en_speeds.append( (thespeed[0], thespeed[1]) )
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
        if self.SHOWCOMPACT:
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
        lw.log( ['parsing line'] )
        file_size = f.size()
        read_size = self.READSIZE
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
            except IndexError:
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
        except Exception as e:
            lw.log( ['unexpected error when reading log file', e], xbmc.LOGERROR )
            return ('', '')
        lw.log( ['opened logfile ' + self.LOGFILE] )
        #get the first and last line of the log file
        #the first line has the header information, and the last line has the last log entry
        first_line = self._parse_line( f, 0 )
        last_line = self._parse_line( f, 2 )
        f.close()
        lw.log( ['first line: ' + first_line, 'last line: ' + last_line] )
        return first_line, last_line
