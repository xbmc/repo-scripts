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
THUMBS_CACHE_PATH = os.path.join( xbmc.translatePath( "special://profile/" ), "Thumbnails/Video" )
DIALOG_DOWNLOAD = xbmcgui.DialogProgress()
ACTION_PREVIOUS_MENU = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )


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
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) ):
            os.makedirs( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) )
        self.clearart = False
        self.characterart = False
        self.logo = False
        self.show_thumb = False
        self.banner = False
        self.poster = False
        self.default_banner = False
        self.default_poster = False
        self.default_show_thumb = False
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
        try: log( "### arg 5: %s" % sys.argv[5] )
        except:   log( "### no arg5" )
        try: log( "### arg 6: %s" % sys.argv[6] )
        except:   log( "### no arg6" )
        try: log( "### arg 7: %s" % sys.argv[7] )
        except:   log( "### no arg7" )
        try: log( "### arg 8: %s" % sys.argv[8] )
        except:   log( "### no arg8" )

        if sys.argv == ['']:
            log( "### script run by user" )
            self.banner = __addon__.getSetting('banner')
            if self.banner == "true":
                self.banner = "banner.jpg"
            else:
                self.banner = False
            self.characterart = __addon__.getSetting('characterart')
            if self.characterart == "true":
                self.characterart = "character.png"
            else:
                self.characterart = False
            self.clearart = __addon__.getSetting('clearart')
            if self.clearart == "true":
                self.clearart = "clearart.png"
            else:
                self.clearart = False
            self.logo = __addon__.getSetting('logo')
            if self.logo == "true":
                self.logo = "logo.png"
            else:
                self.logo = False
            self.poster = __addon__.getSetting('poster')
            if self.poster == "true":
                self.poster = "poster.jpg"
            else:
                self.poster = False
            self.show_thumb = __addon__.getSetting('show_thumb')
            if self.show_thumb == "true":
                self.show_thumb = "landscape.jpg"
            else:
                self.show_thumb = False
            self.download_thumb = __addon__.getSetting('download_thumb')
            log( "### download_thumb:%s ###" % self.download_thumb )
            if self.download_thumb == "true":
                self.default_thumb = __addon__.getSetting('default_thumb')
                if self.default_thumb == "Banner":
                    self.default_banner = True            
                    self.banner = "banner.jpg"
                elif self.default_thumb == "Poster":
                    self.default_poster = True              
                    self.poster = "poster.jpg"
                elif self.default_show_thumb == "ShowThumb":
                    self.default_show_thumb = True             
                    self.show_thumb = "landscape.jpg"
                log( "### default_thumb:%s ###" % self.default_thumb )
            self.mode = "bulk"

        else:
            log( "### script run by skin" )
            for item in sys.argv:
                match = re.search("mode=(.*)" , item)
                if match: self.mode = match.group(1)
                match = re.search("clearart=(.*)" , item)
                if match: 
                    if not match.group(1) == "False": self.clearart = match.group(1)
                    else: pass
                match = re.search("characterart=(.*)" , item)
                if match: 
                    if not match.group(1) == "False": self.characterart = match.group(1)
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
            if self.logo:self.type_list.append (__language__(32128))
            if self.clearart:self.type_list.append (__language__(32129))
            if self.characterart:self.type_list.append (__language__(32130))
            if self.show_thumb:self.type_list.append (__language__(32131))
            if self.banner:self.type_list.append (__language__(32132))
            if self.poster:self.type_list.append (__language__(32133))
            if len(self.type_list) == 1:
                self.type_list[0] = "True"
            if ( len(self.type_list) == 1 ) or self.choice_type():
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
                elif self.characterart: 
                    if self.characterart == "True": self.filename = "character.png"
                    else: self.filename = self.characterart
                    self.get_lockstock_xml()
                    self.search_characterart()
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
                        if not self.download_image():
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
        self.characterart_found = 0
        self.characterart_download = 0
        self.poster_found = 0
        self.poster_download = 0
        self.banner_found = 0
        self.banner_download = 0
        self.TV_listing()
        processeditems = 0

        log( "### banner:%s ###" % self.banner )
        log( "### clearart:%s ###" % self.clearart )
        log( "### characterart:%s ###" % self.characterart )
        log( "### logo:%s ###" % self.logo )
        log( "### poster:%s ###" % self.poster )
        log( "### show_thumb:%s ###" % self.show_thumb )

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

                if self.clearart:
                    log( "### Search clearart for %s" % self.show_name )
                    if self.clearart == "True": self.filename = "clearart.png"
                    else: self.filename = self.clearart
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        log( "### get lockstock xml" )
                        self.get_lockstock_xml()
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

                if self.characterart:
                    log( "### Search characterart for %s" % self.show_name )
                    if self.characterart == "True": self.filename = "character.png"
                    else: self.filename = self.characterart
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        log( "### get lockstock xml" )
                        self.get_lockstock_xml()
                        if self.search_characterart():
                            log( "### found characterart for %s" % self.show_name )
                            if self.download_image():
                                self.characterart_download = self.characterart_download +1
                                log( "### characterart downloaded for %s" % self.show_name )
                            else:
                                log( "### failed: characterart for %s" % self.show_name )
                    else: 
                        self.characterart_found = self.characterart_found +1
                        log( "### %s already exist, skipping" % self.filename )
                    self.image_url = False
                    self.filename = False

                if self.show_thumb:
                    log( "### Search showthumb for %s" % self.show_name )
                    if self.show_thumb == "True": self.filename = "folder.jpg"
                    else: self.filename = self.show_thumb
                    if not xbmcvfs.exists( os.path.join( self.show_path , self.filename ) ):
                        log( "### get lockstock xml" )
                        self.get_lockstock_xml()
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
                            log( "### found poster for %s" % self.show_name )
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
                            log( "### found banner for %s" % self.show_name )
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
        log( "### characterart found = %s" % self.characterart_found )
        log( "### characterart download = %s" % self.characterart_download )
        log( "### banner found = %s" % self.banner_found )
        log( "### banner download = %s" % self.banner_download )
        log( "### poster found = %s" % self.poster_found )
        log( "### poster download = %s" % self.poster_download )
        msg = "DOWNLOADED: "
        msg2 ="FOUND: "
        if self.logo:
            msg = msg + __language__(32128) + ": %s " % self.logo_download
            msg2 = msg2 + __language__(32128) + ": %s " % self.logo_found
        if self.clearart:
            msg = msg + __language__(32129) + ": %s " % self.clearart_download
            msg2 = msg2 + __language__(32129) + ": %s " % self.clearart_found
        if self.characterart:
            msg = msg + __language__(32130) + ": %s " % self.characterart_download
            msg2 = msg2 + __language__(32130) + ": %s " % self.characterart_found
        if self.show_thumb:
            msg = msg + __language__(32131) + ": %s " % self.thumb_download
            msg2 = msg2 + __language__(32131) + ": %s " % self.thumb_found
        if self.banner:
            msg = msg + __language__(32132) + ": %s " % self.banner_download
            msg2 = msg2 + __language__(32132) + ": %s " % self.banner_found
        if self.poster:
            msg = msg + __language__(32133) + ": %s " % self.poster_download
            msg2 = msg2 + __language__(32133) + ": %s " % self.poster_found

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
        try: log( "### show name: %s" % self.show_name )
        except: log( "### show name:" )
        try: log( "### mode: %s" % self.mode )
        except: log( "### mode:" )
        try: log( "### clearart: %s" % self.clearart )
        except: log( "### clearart:" )
        try: log( "### characterart: %s" % self.characterart )
        except: log( "### characterart:" )
        try: log( "### logo: %s" % self.logo )
        except: log( "### logo:" )
        try: log( "### thumb: %s" % self.show_thumb )
        except: log( "### thumb:" )
        try: log( "### show path: %s" % self.show_path )
        except: log( "### show path:" )
        try: log( "### id: %s" % self.tvdbid )
        except: log( "### id:" )
        try: log( "### lockstock xml: %s" % self.lockstock_xml )
        except: log( "### lockstock xml:" )
        try: log( "### image list: %s" % self.image_list )
        except: log( "### image list:" )
        try: log( "### image url: %s" % self.image_url )
        except: log( "### image url:" )
        try: log( "### filename: %s" % self.filename )
        except: log( "### filename:" )
        try: log( "### xbmcstuff_xml: %s" % self.xbmcstuff_xml )
        except: log( "### xbmcstuff_xml:" )

    def TV_listing(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        self.TVlist = []
        for tvshowitem in json_response:
            log( "### tv show: %s" % tvshowitem )
            findtvshowname = re.search( '"label": ?"(.*?)",["\n]', tvshowitem )
            if findtvshowname:
                tvshowname = ( findtvshowname.group(1) )
                findpath = re.search( '"file": ?"(.*?)",["\n]', tvshowitem )
                if findpath:
                    path = (findpath.group(1))
                    findimdbnumber = re.search( '"imdbnumber": ?"(.*?)",["\n]', tvshowitem )
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
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        for tvshowitem in json_response:
            findtvshowname = re.search( '"label": ?"(.*?)",["\n]', tvshowitem )
            if findtvshowname:
                tvshowname = (findtvshowname.group(1))
                tvshowmatch = re.search( '.*' + self.show_name.replace('(','[(]').replace(')','[)]').replace('+','[+]') + '.*', tvshowname, re.I )
                if tvshowmatch:
                    log( "### tv show: %s" % tvshowitem )
                    findpath = re.search( '"file": ?"(.*?)",["\n]', tvshowitem )
                    if findpath:
                        path = (findpath.group(1))
                        self.show_path = path
                        findimdbnumber = re.search( '"imdbnumber": ?"(.*?)",["\n]', tvshowitem )
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
        else: log( "### tvshow.nfo not found !" )
        tvdb_id = re.findall( "<tvdbid>(\d{1,10})</tvdbid>", nfo_read ) or re.findall( "<id>(\d{1,10})</id>", nfo_read )
        if tvdb_id: 
            log( "### tvdb id: %s" % tvdb_id[0] )
            return tvdb_id[0]
        else:
            log( "### no tvdb id found in: %s" % nfo )
            return False

    def get_lockstock_xml(self):
        self.lockstock_xml = get_html_source( "http://fanart.tv/api/fanart.php?v=4&id=" + str( self.tvdbid ) )
        log( "### lockstock: %s" % self.lockstock_xml )

    def get_tvdb_xml(self):
        self.tvdb_xml = get_html_source ("http://www.thetvdb.com/api/F90E687D789D7F7C/series/%s/banners.xml" % str( self.tvdbid ) )

    def search_logo( self ):
        match = re.findall("""<clearlogo .*? url="(.*?)"/>""" , str( self.lockstock_xml) )
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
        match = re.findall("""<clearart .*? url="(.*?)"/>""" , str( self.lockstock_xml) )
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else:
            log( "### No clearart found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32118) )
            self.image_list = False
            return False

    def search_characterart( self ):
        match = re.findall("""<characterart .*? url="(.*?)"/>""" , str( self.lockstock_xml) )
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else:
            log( "### No characterart found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32127) )
            self.image_list = False
            return False

    def search_show_thumb( self ):
        match = re.findall("""<tvthumb .*? url="(.*?)"/>""" , str( self.lockstock_xml) )
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
        else:
            log( "### No poster found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32135) )
            self.image_list = False
            return False

    def search_banner( self ):
        match = re.findall("<BannerPath>(.*?)</BannerPath>\s+<BannerType>series</BannerType>" , self.tvdb_xml)
        if match: 
            if self.mode == "solo" :
                self.image_list = []
                for i in match:
                    self.image_list.append("http://www.thetvdb.com/banners/" + i)
            if self.mode == "bulk" : self.image_url = "http://www.thetvdb.com/banners/" + match[0]
            return True
        else:
            log( "### No banner found !" )
            if self.mode == "solo": xbmcgui.Dialog().ok(__language__(32116) , __language__(32134) )
            self.image_list = False
            return False

    def choice_type(self):
        select = xbmcgui.Dialog().select(__language__(32120) , self.type_list)
        if select == -1: 
            log( "### Canceled by user" )
            xbmcgui.Dialog().ok(__language__(32121) , __language__(32122) )
            return False
        else:
            if self.type_list[select] == __language__(32128) : self.clearart = self.show_thumb = self.banner = self.poster = self.characterart = False
            elif self.type_list[select] == __language__(32129) : self.logo = self.show_thumb = self.banner = self.poster = self.characterart = False
            elif self.type_list[select] == __language__(32130) : self.logo = self.show_thumb = self.banner = self.poster = self.clearart = False
            elif self.type_list[select] == __language__(32131) : self.clearart = self.logo = self.banner = self.poster = self.characterart = False
            elif self.type_list[select] == __language__(32132) : self.logo = self.show_thumb = self.clearart = self.poster = self.characterart = False
            elif self.type_list[select] == __language__(32133) : self.logo = self.show_thumb = self.banner = self.clearart = self.characterart = False
            return True

    def choose_image(self):
        log( "### image list: %s" % self.image_list )
        self.image_url = MyDialog(self.image_list)
        if self.image_url: return True
        else: return False

    def erase_current_cache(self):
        try: 
            cached_thumb = self.get_cached_thumb(self.show_path, self.filename)
            log( "### cache %s" % cached_thumb )
            if xbmcvfs.exists( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") ):
                xbmcvfs.delete( cached_thumb.replace("png" , "dds").replace("jpg" , "dds") )
            copy = xbmcvfs.copy( os.path.join( self.show_path , self.filename ) , cached_thumb )
            if copy:
                xbmc.executebuiltin( 'XBMC.ReloadSkin()' )
                xbmc.executebuiltin( "Notification(" + __language__(32103) + "," + __language__(32104) + ")" )
            else:
                log( "### failed to copy to cached thumb" )
        except :
            print_exc()
            log( "### cache erasing error" )

    def get_cached_thumb( self, path, filename ):
        if path.startswith( "stack://" ):
            path = strPath[ 8 : ].split( " , " )[ 0 ]
        if filename == "folder.jpg":
            cachedthumb = xbmc.getCacheThumbName( path )
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb )
        else:
            cachedthumb = xbmc.getCacheThumbName( os.path.join( path, filename ) )
            if ".jpg" in filename:
                cachedthumb = cachedthumb.replace("tbn" , "jpg")
            elif ".png" in filename:
                cachedthumb = cachedthumb.replace("tbn" , "png")      
            thumbpath = os.path.join( THUMBS_CACHE_PATH, cachedthumb[0], cachedthumb ).replace( "/Video" , "")    
        return thumbpath

    def download_image( self ):
        DIALOG_DOWNLOAD.create( __language__(32107), __language__(32124) + ' ' + self.show_name , __language__(32125) )
        tmpdestination = xbmc.translatePath( 'special://profile/addon_data/%s/temp/%s' % ( __addonid__ , self.filename ) )
        destination = os.path.join( self.show_path , self.filename )
        log( "### download: %s" % self.image_url )
        log( "### path: %s" % repr(destination).strip("'u") )

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

                if self.default_banner and self.filename == "banner.jpg":
                    copy_default = True
                elif self.default_poster and self.filename == "poster.jpg":
                    copy_default = True
                elif self.default_show_thumb and self.filename == "landscape.jpg":
                    copy_default = True
                else:                
                    copy_default = False
                if copy_default:
                    destination = os.path.join( self.show_path , "folder.jpg" )
                    copy = xbmcvfs.copy(tmpdestination, destination)
                    if copy:
                        log( "### copy to default thumb successful" )
                    else:
                        log( "### copy to default thumb failed" )

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
        if action in ACTION_PREVIOUS_MENU:
            self.close() 

    def onClick(self, controlID):
        log( "### control: %s" % controlID )
        if controlID == 6 or controlID == 3: 
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
