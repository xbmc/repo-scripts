# *  Credits:
# *
# *  divingmule for script.image.lastfm.slideshow
# *  grajen3 for script.ImageCacher
# *
# *  code of both scripts is used in script.artistslideshow
# *
# *
# *  Last.fm:      http://www.last.fm/
# *  htbackdrops:  http://www.htbackdrops.com/

import urllib, re, os, sys, time, unicodedata, socket, shutil
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from elementtree import ElementTree as xmltree

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path')
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ ).decode("utf-8")
__language__     = __addon__.getLocalizedString

socket.setdefaulttimeout(10)

LANGUAGES = (
# Full Language name[0]         ISO 639-1[1]   Script Language[2]
    ("Albanian"                   , "sq",            "0"  ),
    ("Arabic"                     , "ar",            "1"  ),
    ("Belarusian"                 , "hy",            "2"  ),
    ("Bosnian"                    , "bs",            "3"  ),
    ("Bulgarian"                  , "bg",            "4"  ),
    ("Catalan"                    , "ca",            "5"  ),
    ("Chinese"                    , "zh",            "6"  ),
    ("Croatian"                   , "hr",            "7"  ),
    ("Czech"                      , "cs",            "8"  ),
    ("Danish"                     , "da",            "9"  ),
    ("Dutch"                      , "nl",            "10" ),
    ("English"                    , "en",            "11" ),
    ("Estonian"                   , "et",            "12" ),
    ("Persian"                    , "fa",            "13" ),
    ("Finnish"                    , "fi",            "14" ),
    ("French"                     , "fr",            "15" ),
    ("German"                     , "de",            "16" ),
    ("Greek"                      , "el",            "17" ),
    ("Hebrew"                     , "he",            "18" ),
    ("Hindi"                      , "hi",            "19" ),
    ("Hungarian"                  , "hu",            "20" ),
    ("Icelandic"                  , "is",            "21" ),
    ("Indonesian"                 , "id",            "22" ),
    ("Italian"                    , "it",            "23" ),
    ("Japanese"                   , "ja",            "24" ),
    ("Korean"                     , "ko",            "25" ),
    ("Latvian"                    , "lv",            "26" ),
    ("Lithuanian"                 , "lt",            "27" ),
    ("Macedonian"                 , "mk",            "28" ),
    ("Norwegian"                  , "no",            "29" ),
    ("Polish"                     , "pl",            "30" ),
    ("Portuguese"                 , "pt",            "31" ),
    ("PortugueseBrazil"           , "pb",            "32" ),
    ("Romanian"                   , "ro",            "33" ),
    ("Russian"                    , "ru",            "34" ),
    ("Serbian"                    , "sr",            "35" ),
    ("Slovak"                     , "sk",            "36" ),
    ("Slovenian"                  , "sl",            "37" ),
    ("Spanish"                    , "es",            "38" ),
    ("Swedish"                    , "sv",            "39" ),
    ("Thai"                       , "th",            "40" ),
    ("Turkish"                    , "tr",            "41" ),
    ("Ukrainian"                  , "uk",            "42" ),
    ("Vietnamese"                 , "vi",            "43" ),
    ("Farsi"                      , "fa",            "13" ),
    ("Portuguese (Brazil)"        , "pb",            "32" ),
    ("Portuguese-BR"              , "pb",            "32" ),
    ("Brazilian"                  , "pb",            "32" ) )

def log(txt):
    message = 'script.artistslideshow: %s' % txt.encode("utf-8")
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def checkDir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdir(path)

def getCacheThumbName(url, CachePath):
    thumb = xbmc.getCacheThumbName(url)
    thumbpath = os.path.join(CachePath, thumb)
    return thumbpath

def cleanText(text):
    text = re.sub('<(.|\n|\r)*?>','',text)
    text = re.sub('&quot;','"',text)
    text = re.sub('&amp;','&',text)
    text = re.sub('&gt;','>',text)
    text = re.sub('&lt;','<',text)
    text = re.sub('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.','',text)
    return text.strip()
        
def download(src, dst, dst2):
    if (not xbmc.abortRequested):
        tmpname = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % ( __addonname__ , xbmc.getCacheThumbName(src) )).decode("utf-8")
        if xbmcvfs.exists(tmpname):
            xbmcvfs.delete(tmpname)
        global __last_time__
        urllib.urlretrieve( src, tmpname )
        if os.path.getsize(tmpname) > 999:
            log( 'copying file to transition directory' )
            xbmcvfs.copy(tmpname, dst2)
            log( 'moving file to cache directory' )
            xbmcvfs.rename(tmpname, dst)
        else:
            xbmcvfs.delete(tmpname)


class Main:
    def __init__( self ):
        self._parse_argv()
        self._get_settings()
        self._init_vars()
        self._make_dirs()
        if xbmc.getInfoLabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
            log('script already running')
        else:
            self.LastCacheTrim = 0
            self.WINDOW.setProperty("ArtistSlideshowRunning", "True")
            if( xbmc.Player().isPlayingAudio() == False and xbmc.getInfoLabel( self.EXTERNALCALL ) == '' ):
                log('no music playing')
                if( self.DAEMON == "False" ):
                    self.WINDOW.clearProperty("ArtistSlideshowRunning")
            elif(not self.OVERRIDEPATH == ''):
                self.WINDOW.setProperty("ArtistSlideshow", self.OVERRIDEPATH)
            else:
                log('first song started')
                time.sleep(0.2) # it may take some time for xbmc to read tag info after playback started
                self._use_correct_artwork()
                self._trim_cache()
            while (not xbmc.abortRequested and self.OVERRIDEPATH == ''):
                time.sleep(0.5)
                if xbmc.getInfoLabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
                    if( xbmc.Player().isPlayingAudio() == True or xbmc.getInfoLabel( self.EXTERNALCALL ) != '' ):
                        #if self.NAME not in self._get_current_artist():
                        if set( self.ALLARTISTS ) <> set( self._get_current_artist() ):
                            self._clear_properties()
                            self.UsingFallback = False
                            self._use_correct_artwork()
                            self._trim_cache()
                        elif(not (self.DownloadedAllImages or self.UsingFallback)):
                            if(not (self.LocalImagesFound and self.PRIORITY == '1')):
                                log('same artist playing, continue download')
                                self._use_correct_artwork()
                    else:
                        time.sleep(1) # doublecheck if playback really stopped
                        if( xbmc.Player().isPlayingAudio() == False and xbmc.getInfoLabel( self.EXTERNALCALL ) == '' ):
                            if ( self.DAEMON == "False" ):
                                self._clean_dir( self.MergeDir )
                                self.WINDOW.clearProperty("ArtistSlideshowRunning")
                else:
                    self._clear_properties()
                    break


    def _use_correct_artwork( self ):
        self._clean_dir( self.MergeDir )
    	artists = self._get_current_artist()
    	self.ALLARTISTS = artists
    	self.ARTISTNUM = 0
    	self.TOTALARTISTS = len(artists)
    	self.MergedImagesFound = False
    	for artist in artists:
    	    log('current artist is %s' % artist.decode("utf-8"))
    	    self.ARTISTNUM += 1
            self.NAME = artist
            if(self.PRIORITY == '1' and not self.LOCALARTISTPATH == ''):
                log('looking for local artwork')
                self._get_local_images()
                if(not self.LocalImagesFound):
                    log('no local artist artwork found, start download')
                    self._start_download()
            elif(self.PRIORITY == '2' and not self.LOCALARTISTPATH == ''):
                log('looking for local artwork')
                self._get_local_images()
                log('start download')
                self._start_download()
            else:
                log('start download')
                self._start_download()
                if(not (self.CachedImagesFound or self.ImageDownloaded)):
                    log('no remote artist artwork found, looking for local artwork')
                    self._get_local_images()
        if(not (self.LocalImagesFound or self.CachedImagesFound or self.ImageDownloaded or self.MergedImagesFound)):
            if (not self.FALLBACKPATH == ''):
                log('no images found for artist, using fallback slideshow')
                log('fallbackdir = ' + self.FALLBACKPATH)
                self.UsingFallback = True
                self.WINDOW.setProperty("ArtistSlideshow", self.FALLBACKPATH)                            


    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        self.WINDOWID = params.get( "windowid", "12006")
        log( 'window id is set to %s' % self.WINDOWID )
        self.ARTISTFIELD = params.get( "artistfield", "" )
        log( 'artist field is set to %s' % self.ARTISTFIELD )
        self.TITLEFIELD = params.get( "titlefield", "" )
        log( 'title field is set to %s' % self.TITLEFIELD )
        self.DAEMON = params.get( "daemon", "False" )
        if self.DAEMON == "True":
            log('daemonizing')


    def _get_settings( self ):
        self.LASTFM = __addon__.getSetting( "lastfm" )
        self.HTBACKDROPS = __addon__.getSetting( "htbackdrops" )
        try:
            self.minwidth = int(__addon__.getSetting( "minwidth" ))
        except:
            self.minwidth = 0
        try:
            self.minheight = int(__addon__.getSetting( "minheight" ))
        except:
            self.minheight = 0
        self.HDASPECTONLY = __addon__.getSetting( "hd_aspect_only" )
        self.ARTISTINFO = __addon__.getSetting( "artistinfo" )
        self.LANGUAGE = __addon__.getSetting( "language" )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                log('language = %s' % self.LANGUAGE)
                break
        self.LOCALARTISTPATH = __addon__.getSetting( "local_artist_path" )
        self.PRIORITY = __addon__.getSetting( "priority" )
        self.FALLBACKPATH = __addon__.getSetting( "fallback_path" )
        self.OVERRIDEPATH = __addon__.getSetting( "slideshow_path" )
        self.RESTRICTCACHE = __addon__.getSetting( "restrict_cache" )
        try:
            self.maxcachesize = int(__addon__.getSetting( "max_cache_size" )) * 1000000
        except:
            self.maxcachesize = 1024 * 1000000
        self.NOTIFICATIONTYPE = __addon__.getSetting( "show_progress" )
        if self.NOTIFICATIONTYPE == "2":    
            self.PROGRESSPATH = __addon__.getSetting( "progress_path" )
            log('set progress path to %s' % self.PROGRESSPATH)
        else:
        	self.PROGRESSPATH = ''
        if len ( __addon__.getSetting( "fanart_folder" ) ) > 0:
            self.FANARTFOLDER = __addon__.getSetting( "fanart_folder" )
            log('set fanart folder to %s' % self.FANARTFOLDER)
        else:
        	self.FANARTFOLDER = 'extrafanart'


    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.WINDOW.clearProperty( "ArtistSlideshow.CleanupComplete" )
        if( self.ARTISTFIELD == '' ):
            self.SKINARTIST = ''
        else:
            self.SKINARTIST = "Window(%s).Property(%s)" % ( self.WINDOWID, self.ARTISTFIELD )
        if( self.TITLEFIELD == '' ):
            self.SKINTITLE = ''
        else:
            self.SKINTITLE = "Window(%s).Property(%s)" % ( self.WINDOWID, self.TITLEFIELD )
        self.ARTISTSLIDESHOW = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow" )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )
        self.EXTERNALCALLSTATUS = xbmc.getInfoLabel( self.EXTERNALCALL )
        log( 'external call is set to ' + xbmc.getInfoLabel( self.EXTERNALCALL ) )
        self.NAME = ''
        self.ALLARTISTS = []
        self.LocalImagesFound = False
        self.CachedImagesFound = False
        self.ImageDownloaded = False
        self.DownloadedAllImages = False
        self.UsingFallback = False
        self.BlankDir = xbmc.translatePath('special://profile/addon_data/%s/transition' % __addonname__ ).decode("utf-8")
        self.MergeDir = xbmc.translatePath('special://profile/addon_data/%s/merge' % __addonname__ ).decode("utf-8")
        self.InitDir = xbmc.translatePath('%s/resources/black' % __addonpath__ ).decode("utf-8")
        LastfmApiKey = 'fbd57a1baddb983d1848a939665310f6'
        HtbackdropsApiKey = '96d681ea0dcb07ad9d27a347e64b652a'
        self.LastfmURL = 'http://ws.audioscrobbler.com/2.0/?autocorrect=1&api_key=' + LastfmApiKey
        self.HtbackdropsQueryURL = 'http://htbackdrops.com/api/' + HtbackdropsApiKey + '/searchXML?default_operator=and&fields=title&aid=1'
        self.HtbackdropsDownloadURL = 'http://htbackdrops.com/api/' + HtbackdropsApiKey + '/download/'


    def _make_dirs( self ):
        checkDir(xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode("utf-8"))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/temp' % __addonname__ ).decode("utf-8"))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/ArtistSlideshow' % __addonname__ ).decode("utf-8"))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/transition' % __addonname__ ).decode("utf-8"))
        

    def _start_download( self ):
        self.CachedImagesFound = False
        self.DownloadedFirstImage = False
        self.DownloadedAllImages = False
        self.ImageDownloaded = False
        self.FirstImage = True
        cached_image_info = False
        min_refresh = 9.9
        if len(self.NAME) == 0:
            log('no artist name provided')
            return
        if(self.PRIORITY == '2' and self.LocalImagesFound):
            pass
            #self.CacheDir was successfully set in _get_local_images
        else:
            CacheName = xbmc.getCacheThumbName(self.NAME).replace('.tbn', '')
            self.CacheDir = xbmc.translatePath('special://profile/addon_data/%s/ArtistSlideshow/%s/' % ( __addonname__ , CacheName, )).decode("utf-8")
            checkDir(self.CacheDir)
        log('cachedir = %s' % self.CacheDir)

        files = os.listdir(self.CacheDir)
        for file in files:
            if file.endswith('tbn') or (self.PRIORITY == '2' and self.LocalImagesFound):
                self.CachedImagesFound = True

        if self.CachedImagesFound:
            log('cached images found')
            cached_image_info = True
            last_time = time.time()
            if self.ARTISTNUM == 1:
                self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
        else:
            last_time = 0
            if self.ARTISTNUM == 1:
                for cache_file in ['artistimageshtbackdrops.nfo', 'artistimageslastfm.nfo']:
                    filename = os.path.join( self.CacheDir, cache_file )
                    if xbmcvfs.exists( os.path.join( self.CacheDir, filename ) ):
                        if time.time() - os.path.getmtime(filename) < 1209600:
                            log('cached %s found' % filename)
                            cached_image_info = True
                        else:
                           log('outdated %s found' % filename)
                           cached_image_info = False
                if self.NOTIFICATIONTYPE == "1":
                    self.WINDOW.setProperty("ArtistSlideshow", self.InitDir)
                    if not cached_image_info:
                        xbmc.executebuiltin('XBMC.Notification("' + __language__(30300).encode("utf8") + '", "' + __language__(30301).encode("utf8") + '", 5000, ' + __addonicon__ + ')')
                elif self.NOTIFICATIONTYPE == "2":
                    if not cached_image_info:
                        self.WINDOW.setProperty("ArtistSlideshow", self.PROGRESSPATH)
                    else:
                        self.WINDOW.setProperty("ArtistSlideshow", self.InitDir)                    
                else:
                    self.WINDOW.setProperty("ArtistSlideshow", self.InitDir)

        if self.LASTFM == "true":
            lastfmlist = self._get_images('lastfm')
        else:
            lastfmlist = []

        if self.HTBACKDROPS == "true":
            htbackdropslist = self._get_images('htbackdrops')
        else:
            htbackdropslist = []
        lastfmlist.extend(htbackdropslist)

        log('downloading images')
        for url in lastfmlist:
            if( self._playback_stopped_or_changed() ):
                self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                self._clean_dir( self.BlankDir )
                return
            path = getCacheThumbName(url, self.CacheDir)
            path2 = getCacheThumbName(url, self.BlankDir)
            if not xbmcvfs.exists(path):
                try:
                    download(url, path, path2)
                except:
                    log ('site unreachable')
                else:
                    log('downloaded %s to %s' % (url, path) )
                    self.ImageDownloaded=True
            if self.ImageDownloaded:
                if( self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                    self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                    self._clean_dir( self.BlankDir )
                    return
                if not self.CachedImagesFound:
                    self.CachedImagesFound = True
                    if self.ARTISTINFO == "true" and self.ARTISTNUM == 1:
                        self._get_artistinfo()
                wait_elapsed = time.time() - last_time
                if( wait_elapsed > min_refresh ):
                    if( not (self.FirstImage and not self.CachedImagesFound) ):
                        self._wait( min_refresh - (wait_elapsed % min_refresh) )
                    if( not self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                        self._refresh_image_directory()
                    last_time = time.time()
                self.FirstImage = False
                
        if self.ImageDownloaded:
            log('finished downloading images')
            self.DownloadedAllImages = True
            if( self._playback_stopped_or_changed() ):
                self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                self._clean_dir( self.BlankDir )
                return
            log( 'cleaning up from refreshing slideshow' )
            wait_elapsed = time.time() - last_time
            if( wait_elapsed < min_refresh ):
                self._wait( min_refresh - wait_elapsed )
            if( not self._playback_stopped_or_changed() ):
                if self.ARTISTNUM == 1:
                    self._refresh_image_directory()
                    if self.NOTIFICATIONTYPE == "1" and not cached_image_info:
                        xbmc.executebuiltin('XBMC.Notification("' + __language__(30304).encode("utf8") + '", "' + __language__(30305).encode("utf8") + '", 5000, ' + __addonicon__ + ')')
                if self.TOTALARTISTS > 1:
                    self._merge_images()                
            if( xbmc.getInfoLabel( self.ARTISTSLIDESHOW ).decode("utf-8") == self.BlankDir and self.ARTISTNUM == 1):
                self._wait( min_refresh )
                if( not self._playback_stopped_or_changed() ):
                    self._refresh_image_directory()
            self._clean_dir( self.BlankDir )

        if not self.ImageDownloaded:
            log('no images downloaded')
            self.DownloadedAllImages = True
            if not self.CachedImagesFound:
                if self.ARTISTNUM == 1:
                    log('clearing ArtistSlideshow property')
                    self.WINDOW.setProperty("ArtistSlideshow", self.InitDir)
                    if self.NOTIFICATIONTYPE == "1" and not cached_image_info:
                        xbmc.executebuiltin('XBMC.Notification("' + __language__(30302).encode("utf8") + '", "' + __language__(30303).encode("utf8") + '", 10000, ' + __addonicon__ + ')')
                    if( self.ARTISTINFO == "true" and not self._playback_stopped_or_changed() ):
                        self._get_artistinfo()
            elif self.TOTALARTISTS > 1:
                self._merge_images()


    def _wait( self, wait_time ):
        waited = 0
        while( waited < wait_time ):
            time.sleep(0.1)
            waited = waited + 0.1
            if( self._playback_stopped_or_changed() ):
                self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                self.Abort = True
                return


    def _clean_dir( self, dir_path ):
        try:
            old_files = os.listdir( dir_path )
        except:
            old_files = []
        for old_file in old_files:
            xbmcvfs.delete( '%s/%s' % (dir_path, old_file) )
            log( 'deleting file %s/%s' % (dir_path, old_file) )


    def _refresh_image_directory( self ):
        if( xbmc.getInfoLabel( self.ARTISTSLIDESHOW ).decode("utf-8") == self.BlankDir):
            self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
            log( 'switching slideshow to ' + self.CacheDir )
        else:    
            self.WINDOW.setProperty("ArtistSlideshow", self.BlankDir)
            log( 'switching slideshow to ' + self.BlankDir )


    def _get_current_artist( self ):
        featured_artist = ''
        if( xbmc.Player().isPlayingAudio() == True ):
            artist = xbmc.Player().getMusicInfoTag().getArtist()
            if( artist == '' ):
                artist = xbmc.Player().getMusicInfoTag().getTitle()[0:(artist.find('-'))-1]
            featured_artist = xbmc.Player().getMusicInfoTag().getTitle().replace('ft.','feat.').split('feat.')
        elif( not xbmc.getInfoLabel( self.SKINARTIST ) == '' ):
            artist = xbmc.getInfoLabel( self.SKINARTIST )
            log('current song title from skin is %s' % xbmc.getInfoLabel( self.SKINTITLE ).decode("utf-8"))
            featured_artist = xbmc.getInfoLabel( self.SKINTITLE ).replace('ft.','feat.').split('feat.')
        else:
            artist = ''
        artists = artist.replace('ft.','/').replace('feat.','/').split('/')
        if len( featured_artist ) > 1:
            artists.append( featured_artist[-1] )
        return [a.strip(' ()') for a in artists]


    def _playback_stopped_or_changed( self ):
        if ( set(self.ALLARTISTS) <> set(self._get_current_artist()) or self.EXTERNALCALLSTATUS != xbmc.getInfoLabel(self.EXTERNALCALL) ):
            return True
        else:
            return False


    def _get_local_images( self ):
        self.LocalImagesFound = False
        if len(self.NAME) == 0:
            log('no artist name provided')
            return
        self.CacheDir = os.path.join( self.LOCALARTISTPATH, self.NAME, self.FANARTFOLDER ).decode("utf-8")
        log('cachedir = %s' % self.CacheDir)
        try:
            files = os.listdir(self.CacheDir)
        except OSError:
            files = []
        for file in files:
            if(file.endswith('tbn') or file.endswith('jpg') or file.endswith('jpeg') or file.endswith('gif') or file.endswith('png')):
                self.LocalImagesFound = True
        if self.LocalImagesFound:
            log('local images found')
            if self.ARTISTNUM == 1:
                self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
            if self.TOTALARTISTS > 1:
               self._merge_images()                


    def _merge_images( self ):
        self.MergedImagesFound = True                
        files = os.listdir(self.CacheDir)
        for file in files:
            if(file.endswith('tbn') or file.endswith('jpg') or file.endswith('jpeg') or file.endswith('gif') or file.endswith('png')):
                xbmcvfs.copy(os.path.join(self.CacheDir, file), os.path.join(self.MergeDir, file))
        if self.ARTISTNUM == self.TOTALARTISTS:
            self._wait( 9.8 )
            self.WINDOW.setProperty("ArtistSlideshow", self.MergeDir)


    def _trim_cache( self ):
        if( self.RESTRICTCACHE == 'true' and not self.PRIORITY == '2' ):
            now = time.time()
            cache_trim_delay = 0   #delay time is in seconds
            if( now - self.LastCacheTrim > cache_trim_delay ):
                log(' trimming the cache down to %s bytes' % self.maxcachesize )
                cache_root = xbmc.translatePath( 'special://profile/addon_data/%s/ArtistSlideshow/' % __addonname__ ).decode("utf-8")
                os.chdir( cache_root )
                folders = os.listdir( cache_root )
                folders.sort( key=lambda x: os.path.getmtime(x), reverse=True )
                cache_size = 0
                first_folder = True
                for folder in folders:
                    if( self._playback_stopped_or_changed() ):
                        break
                    cache_size = cache_size + self._get_folder_size( cache_root + folder )
                    log( 'looking at folder %s cache size is now %s' % (folder, cache_size) )
                    if( cache_size > self.maxcachesize and not first_folder ):
                        self._clean_dir( cache_root + folder )
                        log( 'deleted files in folder %s' % folder )
                    first_folder = False
                self.LastCacheTrim = now


    def _get_folder_size( self, start_path ):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk( start_path ):
            for f in filenames:
                fp = os.path.join( dirpath, f )
                total_size += os.path.getsize( fp )
        return total_size


    def _get_images( self, site ):
        if site == "lastfm":
            self.info = 'artist.getImages'
            self.url = self.LastfmURL + '&method=artist.getImages&artist=' + self.NAME.replace('&','%26').replace(' ','+')
            log( 'asking for images from: %s' %self.url.decode("utf-8") )
        elif site == "htbackdrops":
            self.url = self.HtbackdropsQueryURL + '&keywords=' + self.NAME.replace('&','%26').replace(' ','+') + '&dmin_w=' + str( self.minwidth ) + '&dmin_h=' + str( self.minheight )
            log( 'asking for images from: %s' %self.url.decode("utf-8") )
        images = self._get_data(site, 'images')
        return images


    def _get_artistinfo( self ):
        site = "lastfm"
        bio = self._get_local_data( 'bio' )
        if bio == []:
            self.url = self.LastfmURL + '&method=artist.getInfo&artist=' + self.NAME.replace('&','%26').replace(' ','+') + '&lang=' + self.LANGUAGE
            bio = self._get_data(site, 'bio')
        if bio == []:
            self.biography = ''
        else:
            self.biography = cleanText(bio[0])
        self.similar = self._get_local_data( 'similar' )
        if self.similar == []:
            self.url = self.LastfmURL + '&method=artist.getSimilar&artist=' + self.NAME.replace('&','%26').replace(' ','+')
            self.similar = self._get_data(site, 'similar')
        self.albums = self._get_local_data( 'albums' )
        if self.albums == []:
            self.url = self.LastfmURL + '&method=artist.getTopAlbums&artist=' + self.NAME.replace('&','%26').replace(' ','+')
            self.albums = self._get_data(site, 'albums')
        self._set_properties()


    def _get_local_data( self, item ):
        data = []
        local_path = os.path.join( self.LOCALARTISTPATH, self.NAME, 'override' )
        if item == "similar":
            filename = os.path.join( local_path, 'artistsimilar.nfo' )
        elif item == "albums":
            filename = os.path.join( local_path, 'artistsalbums.nfo' )
        elif item == "bio":
            filename = os.path.join( local_path, 'artistbio.nfo' )
        try:
            xmldata = xmltree.parse(filename).getroot()
        except:
            log('invalid or missing local xml file for %s' % item)
            return data
        if item == "bio":
            for element in xmldata.getiterator():
                if element.tag == "content":
                    bio = element.text
                    if not bio:
                        bio = ''
                    data.append(bio)
        elif( item == "similar" or item == "albums" ):
            for element in xmldata.getiterator():
                if element.tag == "name":
                    name = element.text
                    name.encode('ascii', 'ignore')
                elif element.tag == "image":
                    image_text = element.text
                    if not image_text:
                        image = ''
                    else:
                        image = os.path.join( local_path, item, image_text )
                    data.append( ( name , image ) )
        if data == '':
            log('no %s found in local xml file' % item)
        return data



    def _get_data( self, site, item ):
        data = []
        match = ''
        ForceUpdate = True
        if item == "images":
            if site == "lastfm":
                filename = os.path.join( self.CacheDir, 'artistimageslastfm.nfo')
            elif site == "htbackdrops":
                filename = os.path.join( self.CacheDir, 'artistimageshtbackdrops.nfo')
        elif item == "bio":
            filename = os.path.join( self.CacheDir, 'artistbio.nfo')
        elif item == "similar":
            filename = os.path.join( self.CacheDir, 'artistsimilar.nfo')
        elif item == "albums":
            filename = os.path.join( self.CacheDir, 'artistsalbums.nfo')
        if xbmcvfs.exists( filename ):
            if time.time() - os.path.getmtime(filename) < 1209600:
                log('cached artist %s info found' % item)
                ForceUpdate = False
            else:
                log('outdated cached artist %s info found' % item)
        if ForceUpdate:
            log('downloading artist %s info %s' % (item, site))
            try:
                urllib.urlretrieve( self.url, filename )
            except:
                log('site unreachable')
                return data
        try:
            xmldata = xmltree.parse(filename).getroot()
        except:
            log('invalid xml file')
            xbmcvfs.delete(filename)
            return data
        if item == "images":
            for element in xmldata.getiterator():
                if site == "lastfm":
                    if element.tag == "size":
                        if element.attrib.get('name') == "original":
                            width = element.attrib.get('width')
                            height = element.attrib.get('height')
                            if ( int(width) >= self.minwidth ) and ( int(height) >= self.minheight ):
                                if(self.HDASPECTONLY == 'true'):
                                    aspect_ratio = int(width)/int(height)
                                    if(aspect_ratio > 1.770 and aspect_ratio < 1.787):
                                        data.append(element.text)
                                else:
                                    data.append(element.text)
                elif site == "htbackdrops":
                    if element.tag == "id":
                        data.append(self.HtbackdropsDownloadURL + str( element.text ) + '/fullsize')
        elif item == "bio":
            for element in xmldata.getiterator():
                if element.tag == "content":
                    bio = element.text
                    if not bio:
                        bio = ''
                    data.append(bio)
        elif item == "similar":
            for element in xmldata.getiterator():
                if element.tag == "name":
                    name = element.text
                    name.encode('ascii', 'ignore')
                elif element.tag == "image":
                    if element.attrib.get('size') == "mega":
                        image = element.text
                        if not image:
                            image = ''
                        data.append( ( name , image ) )
        elif item == "albums":
            for element in xmldata.getiterator():
                if element.tag == "name":
                    if match:
                        match = ''
                    else:
                        name = element.text
                        name.encode('ascii', 'ignore')
                        match = 'true'
                elif element.tag == "image":
                    if element.attrib.get('size') == "extralarge":
                        image = element.text
                        if not image:
                            image = ''
                        data.append( ( name , image ) )
        if data == '':
            log('no %s found on %s' % (item, site))
        return data


    def _set_properties( self ):
        self.WINDOW.setProperty("ArtistSlideshow.ArtistBiography", self.biography)
        for count, item in enumerate( self.similar ):
            self.WINDOW.setProperty("ArtistSlideshow.%d.SimilarName" % ( count + 1 ), item[0])
            self.WINDOW.setProperty("ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ), item[1])
        for count, item in enumerate( self.albums ):
            self.WINDOW.setProperty("ArtistSlideshow.%d.AlbumName" % ( count + 1 ), item[0])
            self.WINDOW.setProperty("ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ), item[1])


    def _clear_properties( self ):
        if not xbmc.getInfoLabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
            self.WINDOW.clearProperty("ArtistSlideshow")
        self.WINDOW.clearProperty( "ArtistSlideshow.ArtistBiography" )
        for count in range( 50 ):
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ) )


if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        slideshow = Main()
        slideshow.WINDOW.setProperty("ArtistSlideshow.CleanupComplete", "True")
log('script stopped')
