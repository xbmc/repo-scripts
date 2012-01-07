from time import strptime, time, mktime
import os, sys, re, socket, urllib, unicodedata, simplejson
from traceback import print_exc
from datetime import datetime, date, timedelta, tzinfo
from dateutil import tz
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
# http://mail.python.org/pipermail/python-list/2009-June/596197.html
import _strptime

__addon__     = xbmcaddon.Addon()
__settings__  = xbmcaddon.Addon( "script.tv.show.next.aired" )
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

# Get localized date format
DATE_FORMAT = xbmc.getRegion('dateshort').lower()

if not xbmcvfs.exists(DATA_PATH):
    xbmcvfs.mkdir(DATA_PATH)

def log(msg):
    xbmc.log( str( msg ),level=xbmc.LOGDEBUG )

def footprints():
    log( "### %s starting ..." % __addonname__ )
    log( "### author: %s" % __author__ )
    log( "### version: %s" % __version__ )

def get_html_source(url , save=False):
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    succeed = 0
    while succeed < 5:
        try:
            if (not xbmc.abortRequested):
                urllib.urlcleanup()
                sock = urllib.urlopen(url)
                htmlsource = sock.read()
                if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
                sock.close()
                succeed = 5
                return htmlsource
            else:
                self.close("xbmc exit")
        except:
            succeed = succeed + 1
            print_exc()
            log( "### ERROR opening page %s ---%s---" % ( url , succeed) )
    return ""

def _unicode( text, encoding='utf-8' ):
    try: text = unicode( text, encoding )
    except: pass
    return text

def normalize_string( text ):
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text

class NextAired:
    def __init__(self):
        footprints()
        self.WINDOW = xbmcgui.Window( 10000 )
        self.date = date.today()
        self.datestr = str(self.date)
        self.weekday = date.today().weekday()
        self.days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        self.ampm = xbmc.getCondVisibility('substring(System.Time,Am)') or xbmc.getCondVisibility('substring(System.Time,Pm)')
        self._parse_argv()
        if __settings__.getSetting( "AddonVersion" ) != __version__:
            __settings__.setSetting ( id = "AddonVersion", value = "%s" % __version__ )
            self.FORCEUPDATE = True
        if self.BACKEND:
            self.run_backend()
        else:
            self.update_data()
            if self.SILENT == "":
                self.show_gui()
            else:
                oldweekday = date.today().weekday()
                while (not xbmc.abortRequested):
                    xbmc.sleep(1000)
                    newweekday = date.today().weekday()
                    if newweekday != oldweekday:
                        oldweekday = newweekday
                        self.FORCEUPDATE = True
                        log( "### it's midnight, force update" )
                        self.update_data()
                self.close("xbmc is closing, stop script")

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        log( "### params: %s" % params )
        self.SILENT = params.get( "silent", "" )
        self.BACKEND = params.get( "backend", False )
        self.FORCEUPDATE = params.get( "force", False ) or __settings__.getSetting("ForceUpdate") == "true"

    def update_data(self):
        self.nextlist = []
        dbfile = os.path.join( DATA_PATH , "next_aired.db" )
        if xbmcvfs.exists(dbfile):
            if self.FORCEUPDATE:
                log( "### update forced, rescanning..." )
                __settings__.setSetting(id="ForceUpdate", value="false")
                self.scan_info()
            elif time() - os.path.getmtime(dbfile) > 86400:
                log( "### db more than 24h old, rescanning..." )
                self.scan_info()
            else: 
                log( "### db less than 24h old, fetch local data..." )
                self.current_show_data = self.get_list("next_aired.db")
                if self.current_show_data == "[]":
                    self.scan_info()
        else:
            log( "### db doesn't exist, scanning for data..." )
            self.scan_info()
        if self.current_show_data:
            log( "### data available" )
            for show in self.current_show_data:
                if show.get("Next Episode" , False):
                    self.nextlist.append(show)
            log( "### next list: %s shows ### %s" % ( len(self.nextlist) , self.nextlist ) )
            self.nextlist = sorted( self.nextlist, key=lambda item: str( item.get( "RFC3339", "~" ) ).lower(), reverse=False )
            self.check_today_show()
            self.push_data()
        else:
            log( "### no current show data..." )

    def scan_info(self):
        if self.SILENT == "":
            DIALOG_PROGRESS = xbmcgui.DialogProgress()
            DIALOG_PROGRESS.create( __language__(32101) , __language__(32102) )
        socket.setdefaulttimeout(10)
        self.count = 0
        self.current_show_data = []
        self.canceled = []
        if not self.listing():
            self.close("error listing")
        self.total_show = len(self.TVlist)
        for show in self.TVlist:
            current_show = {}
            self.count += 1
            if self.SILENT == "":
                percent = int( float( self.count * 100 ) / self.total_show )
                DIALOG_PROGRESS.update( percent , __language__(32102) , "%s" % show[0] )
                if DIALOG_PROGRESS.iscanceled():
                    __settings__.setSetting( id="ForceUpdate", value="true" ) 
                    DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
                    break
            log( "### %s" % show[0] )
            current_show["localname"] = show[0]
            current_show["path"] = show[1]
            current_show["thumbnail"] = show[2]
            current_show["fanart"] = show[3]
            current_show["dbid"] = show[4]
            self.get_show_info( current_show )
            self.localize_show_datetime( current_show )
            log( current_show )
            if current_show.get("Status") == "Canceled/Ended":
                self.canceled.append(current_show)
            else:
                self.current_show_data.append(current_show)
        self.save_file( self.canceled , "canceled.db")
        self.save_file( self.current_show_data , "next_aired.db")
        if self.SILENT == "":
            DIALOG_PROGRESS.close()

    def listing(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "thumbnail", "fanart"], "sort": { "method": "label" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log("### %s" % json_response)
        self.TVlist = []
        if json_response['result'].has_key('tvshows'):
            for item in json_response['result']['tvshows']:
                tvshowname = item['label']
                tvshowname = normalize_string( tvshowname )
                path = item['file']
                thumbnail = item['thumbnail']
                fanart = item['fanart']
                dbid = 'videodb://2/2/' + str(item['tvshowid']) + '/'
                self.TVlist.append( ( tvshowname , path, thumbnail, fanart, dbid ) )
        log( "### list: %s" % self.TVlist )
        return self.TVlist

    def get_show_info( self , current_show ):
        log( "### get info %s" % current_show["localname"] )
        log( "### searching for %s" % current_show["localname"] )
        log( "### search url: http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"] ) )
        result_info = get_html_source( "http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"]))
        log( "### parse informations" )
        result = re.findall("(?m)(.*)@(.*)", result_info)
        current_show["ep_img"] = current_show["thumbnail"]
        if result:
            for item in result:
                current_show[item[0].replace("<pre>" , "")] = item[1]

    def localize_show_datetime(self, current_show):
        nextdate = current_show.get( "RFC3339" , "" )
        process = True
        if len(nextdate) > 23:
            try:
                strdate, timezone = nextdate.rsplit( "-", 1 )
                offset = -1
            except:
                log( "### error splitting next date (1)" )
                process = False
            if process == False or len(timezone) < 3 or len(timezone) > 6:
                try:
                    strdate, timezone = nextdate.rsplit( "+", 1 )
                    offset = 1
                except:
                    log( "### error splitting next date (2)" )
                    process = False
        else:
            process = False
        if process == True:
            try:
                timezone = timezone.split( ":" )
            except:
                log( "### error splitting next date (2)" )
            timeoffset = timedelta( hours = offset * int( timezone[0] ), minutes = offset * int ( timezone[1] ) )
            date = datetime.fromtimestamp( mktime( strptime( strdate, '%Y-%m-%dT%H:%M:%S' ) ) )
            date = date.replace(tzinfo=tz.tzoffset(None, ( offset * 3600 * int( timezone[0] ) ) + ( offset * 60 * int ( timezone[1] ) )))
            log( '### nextdate %s' % date.isoformat() )
            datelocal = date.astimezone(tz.tzlocal())
            log( '### nextdate with local time zone %s' % datelocal.isoformat() )
            current_show["RFC3339"] = datelocal.isoformat()
            weekdaydiff = datelocal.weekday() - date.weekday()
            if weekdaydiff == -1:
                weekdaydiff = 6
            elif weekdaydiff == -6:
                weekdaydiff = 1
            try:
                airday = current_show.get("Airtime").split(" at ")[0]
            except:
                airday = ""
                log( "### error splitting airtime" )
            if weekdaydiff != 0 and airday != "":
                try:
                    airdays = airday.split( " ," )
                except:
                    log( "### error splitting airtime" )
                for count, day in enumerate (airdays):
                    if day in self.days:
                        newindex = (self.days.index(day) + weekdaydiff) % 7
                        airdays[count] = self.days[newindex]
                airday = ', '.join(airdays)
            if airday != "":
                if self.ampm:
                    current_show["Airtime"] = airday + " at " + datelocal.strftime('%I:%M %p')
                else:
                    current_show["Airtime"] = airday + " at " + datelocal.strftime('%H:%M')
            try:
                next = current_show.get("Next Episode").split("^")
                next.extend(['',''])
            except:
                next = ['','','']
            current_show["NextNumber"] = next[0]
            current_show["NextTitle"] = next[1]
            current_show["NextDate"] = datelocal.strftime(DATE_FORMAT)
        latest = current_show.get("Latest Episode","").split("^")
        latest.extend(['',''])
        if len(latest[2]) == 11:
            latesttime = strptime( latest[2], '%b/%d/%Y' )
            date = datetime(latesttime[0],latesttime[1],latesttime[2])
            latest[2] = date.strftime(DATE_FORMAT)
        current_show["LatestNumber"] = latest[0]
        current_show["LatestTitle"] = latest[1]
        current_show["LatestDate"] = latest[2]   

    def check_today_show(self):
        self.todayshow = 0
        self.todaylist = []
        self.date = date.today()
        self.datestr = str(self.date)
        log( self.datestr )
        for show in self.nextlist:
            log( "################" )
            log( "### %s" % show.get("localname") )
            if show.get("RFC3339" , "" )[:10] == self.datestr:
                self.todayshow = self.todayshow + 1
                self.todaylist.append(show.get("localname"))
                log( "TODAY" )
            log( "### %s" % show.get("Next Episode", "")  )
            log( "### %s" % show.get("RFC3339", "no rfc") )
            log( str(show.get("RFC3339", "")[:10]) )
        log( "### today show: %s - %s" % ( self.todayshow , str(self.todaylist).strip("[]") ) )

    def get_list(self , listname ):
        path = os.path.join( DATA_PATH , listname )
        if xbmcvfs.exists(path):
            log( "### Load list: %s" % path )
            return self.load_file(path)
        else:
            log( "### Load list: %s not found!" % listname )
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
            if txt:
                file( path , "w" ).write( repr( txt ) )
        except:
            print_exc()
            log( "### ERROR could not save file %s" % DATA_PATH )

    def push_data(self):
        self.WINDOW.setProperty("NextAired.Total" , str(len(self.nextlist)))
        self.WINDOW.setProperty("NextAired.TodayTotal" , str(self.todayshow))
        self.WINDOW.setProperty("NextAired.TodayShow" , str(self.todaylist).strip("[]"))
        for count in range( len(self.nextlist) ):
            self.WINDOW.clearProperty("NextAired.%d.Label" % ( count + 1, ))
        self.count = 0
        for current_show in self.nextlist:
            if current_show.get("RFC3339" , "" )[:10] == self.datestr:
                self.count += 1
                self.set_labels('windowpropertytoday', current_show)

    def show_gui(self):
        for count in range(0, 7):
            if count - self.weekday == 0:
                self.WINDOW.setProperty("NextAired.TodayDate", self.date.strftime(DATE_FORMAT))
                self.WINDOW.setProperty("NextAired.%d.Date" % ( count + 1 ), self.date.strftime(DATE_FORMAT))
            elif count - self.weekday > 0:
                self.WINDOW.setProperty("NextAired.%d.Date" % ( count + 1 ), ( self.date + timedelta( days = ( count - self.weekday ) ) ).strftime(DATE_FORMAT))
            else:
                self.WINDOW.setProperty("NextAired.%d.Date" % ( count + 1 ), ( self.date + timedelta( days = ( ( 7 - self.weekday ) + count ) ) ).strftime(DATE_FORMAT))
        import next_aired_dialog
        next_aired_dialog.MyDialog(self.nextlist, self.set_labels)

    def run_backend(self):
        self._stop = False
        self.previousitem = ''
        self.complete_show_data = self.get_list("next_aired.db")
       	self.complete_show_data.extend(self.get_list("canceled.db"))
        if self.complete_show_data == "[]":
            self._stop = True
        while not self._stop:
            self.selecteditem = xbmc.getInfoLabel("ListItem.TVShowTitle")
            if self.selecteditem != self.previousitem:
                self.WINDOW.clearProperty("NextAired.Label")
                self.previousitem = self.selecteditem
                for item in self.complete_show_data:
                    if self.selecteditem == item.get("localname", ""):
                        self.set_labels('windowproperty', item)
                        break
            xbmc.sleep(100)
            if not xbmc.getCondVisibility("Window.IsVisible(10025)"):
                self.WINDOW.clearProperty("NextAired.Label")
                self._stop = True

    def set_labels(self, infolabel, item, return_items = False ):
        if (infolabel == 'windowproperty') or (infolabel == 'windowpropertytoday'):
            label = xbmcgui.Window( 10000 )
            if infolabel == "windowproperty":
                prefix = 'NextAired.'
            else:
                prefix = 'NextAired.' + str(self.count) + '.'
            label.setProperty(prefix + "Label", item.get("localname", ""))
            label.setProperty(prefix + "Thumb", item.get("ep_img", ""))
        else:
            label = xbmcgui.ListItem()
            prefix = ''
            label.setLabel(item.get("localname", ""))
            label.setThumbnailImage(item.get("ep_img", ""))
        label.setProperty(prefix + "AirTime", item.get("Airtime", ""))
        label.setProperty(prefix + "Path", item.get("path", ""))
        label.setProperty(prefix + "Library", item.get("dbid", ""))
        label.setProperty(prefix + "Status", item.get("Status", ""))
        label.setProperty(prefix + "Network", item.get("Network", ""))
        label.setProperty(prefix + "Started", item.get("Started", ""))
        label.setProperty(prefix + "Classification", item.get("Classification", ""))
        label.setProperty(prefix + "Genre", item.get("Genres", ""))
        label.setProperty(prefix + "Premiered", item.get("Premiered", ""))
        label.setProperty(prefix + "Country", item.get("Country", ""))
        label.setProperty(prefix + "Runtime", item.get("Runtime", ""))
        label.setProperty(prefix + "Fanart", item.get("fanart", ""))
        if item.get("RFC3339" , "" )[:10] == self.datestr:
            label.setProperty(prefix + "Today", "True")
        else:
            label.setProperty(prefix + "Today", "False")
        label.setProperty(prefix + "NextDate", item.get("NextDate", ""))
        label.setProperty(prefix + "NextTitle", item.get("NextTitle", ""))
        label.setProperty(prefix + "NextNumber", item.get("NextNumber", ""))
        nextnumber = item.get("NextNumber","").split("x")
        nextnumber.extend([''])
        label.setProperty(prefix + "NextEpisodeNumber", nextnumber[1])
        label.setProperty(prefix + "NextSeasonNumber", nextnumber[0])
        label.setProperty(prefix + "LatestDate", item.get("LatestDate", ""))
        label.setProperty(prefix + "LatestTitle", item.get("LatestTitle", ""))
        label.setProperty(prefix + "LatestNumber", item.get("LatestNumber", ""))
        latestnumber = item.get("LatestNumber", "").split("x")
        latestnumber.extend([''])
        label.setProperty(prefix + "LatestEpisodeNumber", latestnumber[1])
        label.setProperty(prefix + "LatestSeasonNumber", latestnumber[0])
        daytime = item.get("Airtime","").split(" at ")
        daytime.extend([''])
        label.setProperty(prefix + "AirDay", daytime[0])
        label.setProperty(prefix + "ShortTime", daytime[1])
        if return_items:
            return label

    def close(self , msg ):
        log( "### %s" % msg )
        exit

if ( __name__ == "__main__" ):
    NextAired()
