import urllib
import os
import sys
from traceback import print_exc
import re
import socket
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import time

__addon__     = xbmcaddon.Addon()
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

DATA_PATH = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ), __addonid__ )
RESOURCES_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources' ) )
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )
if not xbmcvfs.exists(DATA_PATH): xbmcvfs.mkdir(DATA_PATH)

def log(msg):
    xbmc.log( str( msg ),level=xbmc.LOGDEBUG )

def footprints():
    log( "### %s starting ..." % __addonname__ )
    log( "### author: %s" % __author__ )
    log( "### version: %s" % __version__ )

def get_html_source( url , save=False):
    """ fetch the html source """
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    succeed = 0
    while succeed < 5:
        try:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )
            htmlsource = sock.read()
            if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
            sock.close()
            succeed = 5
            return htmlsource
        except:
            succeed = succeed + 1
            print_exc()
            log( "### ERROR opening page %s ---%s---" % ( url , succeed) )
    return ""

class NextAired:
    def __init__(self):
        self._parse_argv()
        self.nextlist = []
        testtime = os.path.join( DATA_PATH , "next_aired.db" )
        if xbmcvfs.exists(testtime):
            if time.time() - os.path.getmtime(testtime) > 21600: # time in second for file peremption 43200=1/2day
                log( "###db old more than 24h, rescanning..." )
                self.scan_info()
            else : 
                log( "###db less than 24, fetch local data..." )
                self.current_show_data = self.get_list("next_aired.db")
                if self.current_show_data == "[]": self.scan_info()
        else: 
            log( "###db doesn't exist, scanning for data..." )
            self.scan_info()
        if self.current_show_data: 
            log( "###data available" )
            for show in self.current_show_data:
                if show.get("Next Episode" , False):
                    self.nextlist.append(show)
    #                 log( "######################" )
    #                 for i in show.keys():
    #                     log( "###" + i + ": " + show[i] )
            log( "### next list: %s shows ### %s" % ( len(self.nextlist) , self.nextlist ) )
            self.nextlist = sorted( self.nextlist, key=lambda item: str( item.get( "RFC3339", "~" ) ).lower(), reverse=False )
            self.check_today_show()
            self.push_data()
        else: log( "### no current show data..." )
        if self.PROGRESS:
            import next_aired_dialog
            next_aired_dialog.MyDialog(self.nextlist)
        if self.ALARM: self._set_alarm()

    def _parse_argv( self ):
        try:
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            # no params passed
            params = {}
        # set our preferences
        log( params )
        self.ALARM = int( params.get( "alarm", "0" ) )
        self.PROGRESS = params.get( "silent", True ) == True

    def _set_alarm( self ):
        # only run if user/skinner preference
        if self.ALARM == "0": return
        # set the alarms command
        log( "### Alarm enabled: %s" % self.ALARM )
        command = "XBMC.RunScript(%s,silent=True&alarm=%d)" % ( os.path.join( __cwd__, __file__ ), self.ALARM, )
        xbmc.executebuiltin( "AlarmClock(NextAired,%s,%d,true)" % ( command, self.ALARM, ) )

    def check_today_show(self):
        self.todayshow = 0
        self.todaylist = []
        today = time.strftime('%Y-%m-%d',time.localtime()) 
        log( today )
        #log( time.strftime("%Y") )
        for show in self.nextlist:
            log( "################" )
            log( "###%s" % show.get("localname") )
#             test = timedelta(i.get("RFC3339", "0")) - timedelta(time.strftime(strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())))
#             log( test )
            if str(show.get("RFC3339" , "" )[:10]) == str(today): 
                self.todayshow = self.todayshow + 1
                self.todaylist.append(show.get("localname"))
                log( "TODAY" )
                show["Today"] = "True"
            log( "###%s" % show.get("Next Episode", "")  )
            log( "###%s" % show.get("RFC3339", "no rfc") )
            log( str(show.get("RFC3339", "")[:10]) )
        log( "###today show: %s - %s" % ( self.todayshow , str(self.todaylist).strip("[]") ) )

    def push_data(self):
        # grab the home window
        self.WINDOW = xbmcgui.Window( 10000 )
        # reset Total property for visible condition
        self.WINDOW.setProperty( "NextAired.Total" , str(len(self.nextlist)) )
        self.WINDOW.setProperty( "NextAired.TodayTotal" , str(self.todayshow) )
        self.WINDOW.setProperty( "NextAired.TodayShow" , str(self.todaylist).strip("[]") )
        for count in range( len(self.nextlist) ):
            # we clear title for visible condition
            self.WINDOW.clearProperty( "NextAired.%d.Title" % ( count + 1, ) )
        for count, current_show in enumerate( self.nextlist ): 
            #log( "###%d %s" % ( count + 1 , current_show["localname"] ) )
            self.WINDOW.setProperty( "NextAired.%d.Today" % ( count + 1, ), current_show.get( "Today" , "False"))
            self.WINDOW.setProperty( "NextAired.%d.ShowTitle" % ( count + 1, ), current_show.get( "localname", "" ))
            try:
                next = current_show.get( "Next Episode","").split("^")
                self.WINDOW.setProperty( "NextAired.%d.NextDate" % ( count + 1, ), next[2] or "")
                self.WINDOW.setProperty( "NextAired.%d.NextTitle" % ( count + 1, ), next[1] or "")
                self.WINDOW.setProperty( "NextAired.%d.NextNumber" % ( count + 1, ), next[0] or "")
            except: print_exc()
            try:
                latest = current_show.get("Latest Episode","").split("^")
                self.WINDOW.setProperty( "NextAired.%d.LatestDate" % ( count + 1, ), latest[2] or "")
                self.WINDOW.setProperty( "NextAired.%d.LatestTitle" % ( count + 1, ), latest[1] or "")
                self.WINDOW.setProperty( "NextAired.%d.LatestNumber" % ( count + 1, ), latest[0] or "")
            except: print_exc()
            self.WINDOW.setProperty( "NextAired.%d.Airtime" % ( count + 1, ), current_show.get("Airtime", "" )) 
            self.WINDOW.setProperty( "NextAired.%d.Showpath" % ( count + 1, ), current_show.get("path", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Status" % ( count + 1, ), current_show.get("Status", "" ))
            self.WINDOW.setProperty( "NextAired.%d.ep_img" % ( count + 1, ), current_show.get("ep_img", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Network" % ( count + 1, ), current_show.get("Network", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Started" % ( count + 1, ), current_show.get("Started", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Classification" % ( count + 1, ), current_show.get("Classification", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Genres" % ( count + 1, ), current_show.get("Genres", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Premiered" % ( count + 1, ), current_show.get("Premiered", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Country" % ( count + 1, ), current_show.get("Country", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Runtime" % ( count + 1, ), current_show.get("Runtime", "" )) 
            try:
                airday, shortime = current_show.get("Airtime", "  at  " ).split(" at ")
                self.WINDOW.setProperty( "NextAired.%d.airday" % ( count + 1, ), airday)
                self.WINDOW.setProperty( "NextAired.%d.shortime" % ( count + 1, ), shortime)
            except: log( "### %s" % current_show.get("Airtime", "  at  " ) )
            #log( airday, shortime )


    def scan_info(self):
        if self.PROGRESS: 
            DIALOG_PROGRESS = xbmcgui.DialogProgress()
            DIALOG_PROGRESS.create( __language__(32101) , __language__(32102) )
        socket.setdefaulttimeout(10)
        self.total_reaquest = 0
        self.total_next_found = 0
        self.total_error = 0 
        self.total_canceled = 0
        self.total_current = 0
        self.total_error = 0
        self.count = 0
        self.current_show_data = []
        self.canceled = self.get_list("canceled.db")
        if not self.listing(): self.close("error listing")
        self.total_show = len(self.TVlist)
        log( "###canceled list: %s " % self.canceled )

        for show in self.TVlist:
            current_show = {}
            self.count = self.count +1
            if self.PROGRESS:
                percent = int( float( self.count * 100 ) / self.total_show )
                DIALOG_PROGRESS.update( percent , __language__(32102) , "%s" % show[0] )
                if DIALOG_PROGRESS.iscanceled():
                    DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
                    break
            log( "###%s" % show[0] )
            current_show["localname"] = show[0]
            current_show["path"] = show[1]
            current_show["thumbnail"] = show[2]
            if show[0] in self.canceled: log( "### %s canceled/Ended" % show[0] )
            else:
                self.get_show_info( current_show )
                log( current_show )
                if current_show.get("Status") == "Canceled/Ended": self.canceled.append(current_show["localname"])
                else: self.current_show_data.append(current_show)

        self.save_file( self.canceled , "canceled.db")
        self.save_file( self.current_show_data , "next_aired.db")
        if self.PROGRESS:DIALOG_PROGRESS.close()
        
    def get_show_info( self , current_show ):
        log( "### get info %s" % current_show["localname"] )
        # get info for show with exact name
        log( "### searching for %s" % current_show["localname"] )
        log( "###search url: http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"] ) )  #DEBUG
        result_info = get_html_source( "http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"]))
        log( "### parse informations" )
        #log( "### %s" % result_info )
        result = re.findall("(?m)(.*)@(.*)", result_info)
        current_show["ep_img"] = current_show["thumbnail"]
        if result:
            # get short tvshow info and next aired episode
            for item in result:
                current_show[item[0].replace("<pre>" , "")] = item[1]
                #log( "### %s : %s " % ( item[0].replace("<pre>" , "") , item[1] ) ) #DEBUG


    def get_list(self , listname ):
        path = os.path.join( DATA_PATH , listname )
        if xbmcvfs.exists(path):
            log( "### Load list: %s" % path )
            return self.load_file(path)
        else:
            log( "### Load list: no file found! generating %s !" % listname )
            return []

    def load_file( self , file_path ):
        try:
            return eval( file( file_path, "r" ).read() )
        except:
            print_exc()
            log( "### ERROR could not load file %s" % temp )
            return "[]"

    def save_file( self , txt , filename):
        path = os.path.join( DATA_PATH , filename )
        try:
            if txt:file( path , "w" ).write( repr( txt ) )
        except:
            print_exc()
            log( "### ERROR could not save file %s" % DATA_PATH )

    def listing(self):
        # json statement for tv shows
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "thumbnail"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        log( json_response )
        self.TVlist = []
        for tvshowitem in json_response:
            log( tvshowitem )
            findtvshowname = re.search( '"label": ?"(.*?)",["\n]', tvshowitem )
            if findtvshowname:
                tvshowname = ( findtvshowname.group(1) )
                findpath = re.search( '"file": ?"(.*?)",["\n]', tvshowitem )
                if findpath:
                    path = (findpath.group(1))
                else:
                    path = ''
                findthumbnail = re.search( '"thumbnail": ?"(.*?)",["\n]', tvshowitem )
                if findthumbnail:
                    thumbnail = (findthumbnail.group(1))
                else:
                    thumbnail = ''
                self.TVlist.append( ( tvshowname , path, thumbnail ) )
        log( self.TVlist )
        return self.TVlist

    def close(self , msg ):
        log( msg )
        exit

if ( __name__ == "__main__" ): 
    footprints()
    NextAired()

