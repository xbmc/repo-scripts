import urllib
import os
import re
from traceback import print_exc
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

__addon__     = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addonid__   = __addon__.getAddonInfo('id')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__cwd__       = __addon__.getAddonInfo('path')
__language__  = __addon__.getLocalizedString
__useragent__    = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

SOURCEPATH = __cwd__
RESOURCES_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources' ) )
DIALOG_DOWNLOAD = xbmcgui.DialogProgress()
ACTION_PREVIOUS_MENU = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )
from file_item import Thumbnails
thumbnails = Thumbnails()

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

    try:
        if os.path.isfile( url ): sock = open( url, "r" )
        else:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )

        htmlsource = sock.read()
        if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
        sock.close()
        return htmlsource
    except:
        print_exc()
        log( "### ERROR opening page %s" % url )
        xbmcgui.Dialog().ok(__language__(32101) , __language__(32102))
        return False

class downloader:
    def __init__(self):
        log( "### logo downloader initializing..." )
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) ):
            os.makedirs( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) )
        self.clearart = False
        self.logo = False
        self.show_thumb = False
        self.banner = False
        self.poster = False
        self.mode = ""
        self.error = ""
        self.reinit()
        log( "### args: %s" % sys.argv )
        try: log( "### arg 0: %s" % sys.argv[0] )
        except:   log( "### no arg0" )
        try: log( "### arg 1: %s" % sys.argv[1] )
        except:   log( "### no arg1" )
        try: log( "### arg 2: %s" % sys.argv[2] )
        except:   log( "### no arg2" )
        try: log( "### arg 3: %s" % sys.argv[3] )
        except:   log( "### no arg3" )
        try: log( "### arg 4: %s" % sys.argv[4] )
        except:   log( "### no arg4" )
        try: log( "arg 5: %s" % sys.argv[5] )
        except:   log( "### no arg5" ) 
        try: log( "### arg 6: %s" % sys.argv[6] )
        except:   log( "### no arg6" )
        try: log( "### arg 7: %s" % sys.argv[7] )
        except:   log( "### no arg7" ) 

        for item in sys.argv:
            match = re.search("mode=(.*)" , item)
            if match: self.mode = match.group(1)
            match = re.search("clearart=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.clearart = match.group(1)
                else: pass
            match = re.search("logo=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.logo = match.group(1)
                else: pass
            match = re.search("showthumb=(.*)" , item)
            if match:
                if not match.group(1) == "False": self.show_thumb = match.group(1)
                else: pass
            match = re.search("showname=" , item)
            if match: self.show_name = item.replace( "showname=" , "" )
            else: pass
            match = re.search("banner=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.banner = match.group(1)
                else: pass
            match = re.search("poster=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.poster = match.group(1)
                else: pass

        if self.mode == "solo": 
            log( "### Start Solo Mode" )
            self.solo_mode()
        elif self.mode == "bulk": 
            log( "### Start Bulk Mode" )
            self.bulk_mode()

    def solo_mode(self):
        self.get_tvid_path()
        self.id_verif()
        if self.tvdbid:
            self.type_list = []
            if self.logo:self.type_list.append ("logo")
            if self.clearart:self.type_list.append ("clearart")
            if self.show_thumb:self.type_list.append ("showthumb")
            if self.banner:self.type_list.append ("banner")
            if self.poster:self.type_list.append ("poster")
            
            if self.choice_type():
                self.image_list = False
                if self.logo:
                    if self.logo == "True": self.filename = "logo.png"
                    else: self.filename = self.logo
                    self.get_lockstock_xml()
                    self.search_logo()
                elif self.clearart: 
                    if self.clearart == "True": self.filename = "clearart.png"
                    else: self.filename = self.clearart
                    self.get_lockstock_xml()
                    self.search_clearart()
                elif self.show_thumb:
                    if self.show_thumb == "True": self.filename = "folder.jpg"
                    else: self.filename = self.show_thumb
                    self.get_lockstock_xml()
                    self.search_show_thumb()
                elif self.banner:
                    if self.banner == "True": self.filename = "folder.jpg"
                    else: self.filename = self.banner
                    self.get_tvdb_xml()
                    self.search_banner()
                elif self.poster:
                    if self.poster == "True": self.filename = "folder.jpg"
                    else: self.filename = self.poster
                    self.get_tvdb_xml()
                    self.search_poster()
                
                if self.image_list: 
                    if self.choose_image(): 
                        self.print_class_var()
                        if self.download_image(): xbmcgui.Dialog().ok(__language__(32103) , __language__(32104) )
                        else:
                            if self.error == "download":
                                xbmcgui.Dialog().ok(__language__(32101) , __language__(32105) )
                            elif self.error == "copy":
                                xbmcgui.Dialog().ok(__language__(32101) , __language__(32126) )
        else: xbmcgui.Dialog().ok(__language__(32101) , __language__(32106) )

    def bulk_mode(self):
        log( "### get tvshow list" )
        DIALOG_PROGRESS = xbmcgui.DialogProgress()
        DIALOG_PROGRESS.create( __language__(32107), __language__(32108))
        self.logo_found = 0
        self.logo_download = 0
        self.thumb_found = 0
        self.thumb_download = 0
        self.clearart_found = 0
        self.clearart_download = 0
        self.poster_found = 0
        self.poster_download = 0
        self.banner_found = 0
        self.banner_download = 0
        self.TV_listing()
        processeditems = 0

        log( "###clearart#%s###" % self.clearart )
        log( "###logo#%s###" % self.logo )
        log( "###show_thumb#%s###" % self.show_thumb )

        for currentshow in self.TVlist:
            log( "####################" )
            processeditems = processeditems + 1
            totalitems = len( self.TVlist )
            DIALOG_PROGRESS.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32108), currentshow["name"] )
            if DIALOG_PROGRESS.iscanceled():
                DIALOG_PROGRESS.close()
                xbmcgui.Dialog().ok(__language__(32109),__language__(32110))
                break
            try:
                self.show_path = currentshow["path"]
                self.tvdbid = currentshow["id"]
                self.show_name = currentshow["name"]
                log( "### show_name: %s" % self.show_name )
                log( "### tvdbid: %s" % self.tvdbid )
                log( "### show_path: %s" % self.show_path )
                log( "### check id" )
                self.id_verif()

                if self.logo:
                    log( "### Search logo for %s" % self.show_name )
                    if self.logo == "True": self.filename = "logo.png"
                    else: self.filename = self.logo
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        log( "### get lockstock xml" )
                        self.get_lockstock_xml()
                        if self.search_logo():
                            log( "### found logo for %s" % self.show_name )
                            if self.download_image():
                                self.logo_download = self.logo_download +1
                                log( "### logo downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: logo for %s" % self.show_name )
                    else: 
                        log( "### %s already exist, skipping" % self.filename )
                        self.logo_found = self.logo_found + 1
                    self.image_url = False
                    self.filename = False

#                 if self.clearart or self.show_thumb: 
#                     log( "### get xbmcstuff xml"
#                     self.get_xbmcstuff_xml()

                if self.clearart:
                    log( "### Search clearart for %s" % self.show_name )
                    if self.clearart == "True": self.filename = "clearart.png"
                    else: self.filename = self.clearart
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_clearart():
                            log( "### found clearart for %s" % self.show_name )
                            if self.download_image():
                                self.clearart_download = self.clearart_download +1
                                log( "### clearart downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: clearart for %s" % self.show_name )
                    else: 
                        self.clearart_found = self.clearart_found +1
                        log( "### %s already exist, skipping" % self.filename )
                    self.image_url = False
                    self.filename = False

                if self.show_thumb:
                    log( "### Search showthumb for %s" % self.show_name )
                    if self.show_thumb == "True": self.filename = "folder.jpg"
                    else: self.filename = self.show_thumb
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_show_thumb():
                            log( "### found show thumb for %s" % self.show_name )
                            if self.download_image():
                                self.thumb_download = self.thumb_download +1
                                log( "### showthumb downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: showthumb for %s" % self.show_name )
                    else: 
                        self.thumb_found = self.thumb_found + 1
                        log( "### %s already exist, skipping" % self.filename )
                    self.image_url = False
                    self.filename = False

                if self.poster or self.banner: 
                    log( "### get tvdb xml" )
                    self.get_tvdb_xml()

                if self.poster:
                    log( "### Search poster for %s" % self.show_name )
                    if self.poster == "True": self.filename = "folder.jpg"
                    else: self.filename = self.poster
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_poster():
                            log( "### found show thumb for %s" % self.show_name )
                            if self.download_image():
                                self.poster_download = self.poster_download +1
                                log( "### poster downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: poster for %s" % self.show_name )
                    else: 
                        self.poster_found = self.poster_found + 1
                        log( "### %s already exist, skipping" % self.filename )
                    self.image_url = False
                    self.filename = False

                if self.banner:
                    log( "### Search banner for %s" % self.show_name )
                    if self.banner == "True": self.filename = "folder.jpg"
                    else: self.filename = self.banner
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_banner():
                            log( "### found show thumb for %s" % self.show_name )
                            if self.download_image():
                                self.banner_download = self.banner_download +1
                                log( "### banner downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: banner for %s" % self.show_name )
                    else: 
                        self.banner_found = self.banner_found + 1
                        log( "### %s already exist, skipping" % self.filename )
                    self.image_url = False
                    self.filename = False
                    
                self.reinit()
            except:
                log( "### error with: %s" % currentshow )
                print_exc()
        DIALOG_PROGRESS.close()
        log( "### total tvshow = %s" % len(self.TVlist) )
        log( "### logo found = %s" % self.logo_found )
        log( "### logo download = %s" % self.logo_download )
        log( "### thumb found = %s" % self.thumb_found )
        log( "### thumb download = %s" % self.thumb_download )
        log( "### clearart found = %s" % self.clearart_found )
        log( "### clearart download = %s" % self.clearart_download )
        log( "### banner found = %s" % self.banner_found )
        log( "### banner download = %s" % self.banner_download )
        log( "### poster found = %s" % self.poster_found )
        log( "### poster download = %s" % self.poster_download )
        msg = "DOWNLOADED: "
        msg2 ="FOUND: "
        if self.logo: 
            msg = msg + "logo: %s " % self.logo_download
            msg2 = msg2 + "logo: %s " % self.logo_found
        if self.clearart: 
            msg = msg + "clearart: %s " % self.clearart_download
            msg2 = msg2 + "clearart: %s " % self.clearart_found
        if self.show_thumb: 
            msg = msg + "thumb: %s " % self.thumb_download
            msg2 = msg2 + "thumb: %s " % self.thumb_found
        if self.poster: 
            msg = msg + "poster: %s " % self.poster_download
            msg2 = msg2 + "poster: %s " % self.poster_found
        if self.banner: 
            msg = msg + "banner: %s " % self.banner_download
            msg2 = msg2 + "banner: %s " % self.banner_found

        xbmcgui.Dialog().ok(__language__(32111) + ' ' + str( len(self.TVlist) ) + ' ' + __language__(32112) , msg , msg2 )
        xbmcgui.Dialog().ok(__language__(32113), __language__(32114) , __language__(32115).upper() )

    def reinit(self):
        log( "### reinit" )
        self.show_path = False
        self.tvdbid = False
        self.show_name = ""
        self.xbmcstuff_xml = False
        self.lockstock_xml = False
        self.tvdb_xml = False

    def print_class_var(self):
        try: log( "###show name: %s" % self.show_name )
        except: log( "###show name:" )
        try: log( "###mode: %s" % self.mode )
        except: log( "###mode:" )
        try: log( "###clearart: %s" % self.clearart )
        except: log( "###clearart:" )
        try: log( "###logo: %s" % self.logo )
        except: log( "###logo:" )
        try: log( "###thumb: %s" % self.show_thumb )
        except: log( "###thumb:" )
        try: log( "###show path: %s" % self.show_path )
        except: log( "###show path:" )
        try: log( "###id: %s" % self.tvdbid )
        except: log( "###id:" )
        try: log( "###lockstock xml: %s" % self.lockstock_xml )
        except: log( "###lockstock xml:" )
        try: log( "###image list: %s" % self.image_list )
        except: log( "###image list:" )
        try: log( "###image url: %s" % self.image_url )
        except: log( "###image url:" )
        try: log( "###filename: %s" % self.filename )
        except: log( "###filename:" )
        try: log( "###xbmcstuff_xml: %s" % self.xbmcstuff_xml )
        except: log( "###xbmcstuff_xml:" )

    def TV_listing(self):
        # json statement for tv shows
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"fields": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        self.TVlist = []
        for tvshowitem in json_response:
            log( "### tv show: %s" % tvshowitem )
            findtvshowname = re.search( '"label":"(.*?)","', tvshowitem )
            if findtvshowname:
                tvshowname = ( findtvshowname.group(1) )
                findpath = re.search( '"file":"(.*?)","', tvshowitem )
                if findpath:
                    path = (findpath.group(1))
                    findimdbnumber = re.search( '"imdbnumber":"(.*?)","', tvshowitem )
                    if findimdbnumber:
                        imdbnumber = (findimdbnumber.group(1))
                    else:
                        imdbnumber = ''
                    TVshow = {}
                    TVshow["name"] = tvshowname
                    TVshow["id"] = imdbnumber
                    TVshow["path"] = path
                    self.TVlist.append(TVshow)

    def get_tvid_path( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"fields": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        for tvshowitem in json_response:
            findtvshowname = re.search( '"label":"(.*?)","', tvshowitem )
            if findtvshowname:
                tvshowname = (findtvshowname.group(1))
                tvshowmatch = re.search( '.*' + self.show_name + '.*', tvshowname, re.I )
                if tvshowmatch:
                    log( "### tv show: %s" % tvshowitem )
                    findpath = re.search( '"file":"(.*?)","', tvshowitem )
                    if findpath:
                        path = (findpath.group(1))
                        self.show_path = path
                        findimdbnumber = re.search( '"imdbnumber":"(.*?)","', tvshowitem )
                        if findimdbnumber:
                            imdbnumber = (findimdbnumber.group(1))
                            self.tvdbid = imdbnumber
                        else:
                            self.tvdbid = False
        log( "### json dat: %s" % json_query )

    def id_verif(self):
        if self.tvdbid:
            if self.tvdbid[0:2] == "tt" or self.tvdbid == "" :
                log( "### IMDB id found (%s) or no id found in db, checking for nfo" % self.show_path )
                try: self.tvdbid = self.get_nfo_id()
                except:
                    self.tvdbid = False
                    log( "### Error checking for nfo: %stvshow.nfo" % self.show_path.replace("\\\\" , "\\") )
                    print_exc()

    def get_nfo_id( self ):
        nfo= os.path.join(self.show_path , "tvshow.nfo")
        log( "### nfo file: %s" % nfo )
        if xbmcvfs.exists(nfo):
            if nfo.startswith("smb://"):
                copy = xbmcvfs.copy( nfo, xbmc.translatePath('special://profile/addon_data/%s/temp/tvshow.nfo' % __addonid__ ) )
                if copy:
                    nfo_read = file( xbmc.translatePath('special://profile/addon_data/%s/temp/tvshow.nfo' % __addonid__ ), "r" ).read()
                    xbmcvfs.delete( xbmc.translatePath('special://profile/addon_data/%s/temp/tvshow.nfo' % __addonid__ ) )
                else:
                    log( "### failed to copy tvshow.nfo" )
            else:
                nfo_read = file(nfo, "r" ).read()
            log( "nfo_read" )
        else: log( "###tvshow.nfo not found !" )
        tvdb_id = re.findall( "<tvdbid>(\d{1,10})</tvdbid>", nfo_read ) or re.findall( "<id>(\d{1,10})</id>", nfo_read )
        if tvdb_id: 
            log( "### tvdb id: %s" % tvdb_id[0] )
            return tvdb_id[0]
        else:
            log( "### no tvdb id found in: %s" % nfo )
            return False

    def get_lockstock_xml(self):
        self.lockstock_xml = get_html_source( "http://fanart.tv/api/fanart.php?id=" + str( self.tvdbid ) )
        log( "### lockstock: %s" % self.lockstock_xml )

#     def get_xbmcstuff_xml(self):
#         self.xbmcstuff_xml = get_html_source ("http://www.xbmcstuff.com/tv_scraper.php?&id_scraper=p7iuVTQXQWGyWXPS&size=big&thetvdb=" + str( self.tvdbid ) )

    def get_tvdb_xml(self):
        self.tvdb_xml = get_html_source ("http://www.thetvdb.com/api/F90E687D789D7F7C/series/%s/banners.xml" % str( self.tvdbid ) )

    def search_logo( self ):
        match = re.findall("""<clearlogo url="(.*?)"/>""" , str( self.lockstock_xml) )
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            log( "### No logo found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32117) )
            self.image_list = False
            return False

    def search_clearart( self ):
        match = re.findall("""<clearart url="(.*?)"/>""" , str( self.lockstock_xml) )
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            log( "### No clearart found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32118) )
            self.image_list = False
            return False

    def search_show_thumb( self ):
        match = re.findall("""<tvthumb url="(.*?)"/>""" , str( self.lockstock_xml) )
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            log( "### No show thumb found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32119) )
            self.image_list = False
            return False

    def search_poster( self ):
        match = re.findall("<BannerPath>(.*?)</BannerPath>\s+<BannerType>poster</BannerType>" , self.tvdb_xml)
        if match: 
            if self.mode == "solo" :
                self.image_list = []
                for i in match:
                    self.image_list.append("http://www.thetvdb.com/banners/" + i)
            if self.mode == "bulk" : self.image_url = "http://www.thetvdb.com/banners/" + match[0]
            return True
            
    def search_banner( self ):
        match = re.findall("<BannerPath>(.*?)</BannerPath>\s+<BannerType>series</BannerType>" , self.tvdb_xml)
        if match: 
            if self.mode == "solo" :
                self.image_list = []
                for i in match:
                    self.image_list.append("http://www.thetvdb.com/banners/" + i)
            if self.mode == "bulk" : self.image_url = "http://www.thetvdb.com/banners/" + match[0]
            return True

    def choice_type(self):
        select = xbmcgui.Dialog().select(__language__(32120) , self.type_list)
        if select == -1: 
            log( "### Canceled by user" )
            xbmcgui.Dialog().ok(__language__(32121) , __language__(32122) )
            return False
        else:
            if self.type_list[select] == "logo" : self.clearart = self.show_thumb = self.banner = self.poster = False
            elif self.type_list[select] == "showthumb" : self.clearart = self.logo = self.banner = self.poster = False
            elif self.type_list[select] == "clearart" : self.logo = self.show_thumb = self.banner = self.poster = False
            elif self.type_list[select] == "banner" : self.logo = self.show_thumb = self.clearart = self.poster = False
            elif self.type_list[select] == "poster" : self.logo = self.show_thumb = self.banner = self.clearart = False
            return True

    def choose_image(self):
        #select = xbmcgui.Dialog().select(__language__(32123) , self.image_list)
        log( "### image list: %s" % self.image_list )
        self.image_url = MyDialog(self.image_list)
        if self.image_url: return True
        else: return False
#         if select == -1: 
#             log( "### Canceled by user" )
#             xbmcgui.Dialog().ok(__language__(32121) , __language__(32122) )
#             self.image_url = False
#             return False
#         else:
#             self.image_url = self.image_list[select]
#             return True

    def erase_current_cache(self):
        try: 
            
            if not self.filename == "folder.jpg": cached_thumb = thumbnails.get_cached_video_thumb( os.path.join( self.show_path , self.filename )).replace( "\\Video" , "").replace("tbn" , "png")
            else: cached_thumb = thumbnails.get_cached_video_thumb(self.show_path)
            log( "### cache %s" % cached_thumb )
            copy = xbmcvfs.copy( os.path.join( self.show_path , self.filename ) , cached_thumb )
            if copy:
                pass
#                xbmc.executebuiltin( 'XBMC.ReloadSkin()' )
            else:
                log( "### failed to copy to cached thumb" )
        except :
            print_exc()
            log( "### cache erasing error" )

    def download_image( self ):
        DIALOG_DOWNLOAD.create( __language__(32107), __language__(32124) + ' ' + self.show_name , __language__(32125) )
        tmpdestination = xbmc.translatePath( 'special://profile/addon_data/%s/temp/%s' % ( __addonid__ , self.filename ) )
        destination = os.path.join( self.show_path , self.filename )
        log( "### download :" + self.image_url )
        log( "### path: " + repr(destination).strip("'u") )

        try:
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                log( "### percent: %s" % percent )
                DIALOG_DOWNLOAD.update( percent , __language__(32124) + ' ' + self.show_name , __language__(32124) + self.filename )
            if xbmcvfs.exists(self.show_path):
                fp , h = urllib.urlretrieve( self.image_url.replace(" ", "%20") , tmpdestination , _report_hook )
                log( h )
                if xbmcvfs.exists(tmpdestination):
                    log( "### download successful" )
                else:
                    log( "### download failed" )
                    self.error = "download"
                    xbmcvfs.delete(tmpdestination)
                    DIALOG_DOWNLOAD.close()
                    return False
                copy = xbmcvfs.copy(tmpdestination, destination)
                if copy:
                    log( "### copy successful" )
                else:
                    log( "### copy failed" )
                    self.error = "copy"
                    xbmcvfs.delete(tmpdestination)
                    DIALOG_DOWNLOAD.close()
                    return False
                xbmcvfs.delete(tmpdestination)
                if self.mode == "solo": self.erase_current_cache()
                return True
            else : log( "### problem with path: %s" % self.show_path )
        except :
            log( "### Image download Failed !!!" )
            print_exc()
            return False

class MainGui( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        xbmc.executebuiltin( "Skin.Reset(AnimeWindowXMLDialogClose)" )
        xbmc.executebuiltin( "Skin.SetBool(AnimeWindowXMLDialogClose)" )
        self.listing = kwargs.get( "listing" )

    def onInit(self):
        try :
            self.img_list = self.getControl(6)
            self.img_list.controlLeft(self.img_list)
            self.img_list.controlRight(self.img_list)
            self.getControl(3).setVisible(False)
        except :
            print_exc()
            self.img_list = self.getControl(3)

        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(__language__(32123))

        for image in self.listing :
            listitem = xbmcgui.ListItem( image.split("/")[-1] )
            listitem.setIconImage( image )
            listitem.setLabel2(image)
            log( "### image: %s" % image )
            self.img_list.addItem( listitem )
        self.setFocus(self.img_list)

    def onAction(self, action):
        #Close the script
        if action in ACTION_PREVIOUS_MENU:
            self.close() 

    def onClick(self, controlID):
        log( "### control: %s" % controlID )
        """
            Notice: onClick not onControl
            Notice: it gives the ID of the control not the control object
        """
        #action sur la liste
        if controlID == 6 or controlID == 3: 
            #Renvoie l'item selectionne
            num = self.img_list.getSelectedPosition()
            log( "### position: %s" % num )
            self.selected_url = self.img_list.getSelectedItem().getLabel2()
            self.close()

    def onFocus(self, controlID):
        pass

def MyDialog(tv_list):
    w = MainGui( "DialogSelect.xml", SOURCEPATH, listing=tv_list )
    w.doModal()
    try: return w.selected_url
    except: 
        print_exc()
        return False
    del w

if ( __name__ == "__main__" ): 
    footprints()
    downloader()
    log( "### logo downloader exiting..." )
