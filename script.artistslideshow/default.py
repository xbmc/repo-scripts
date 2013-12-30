# *  Credits:
# *
# *  original Artist Slideshow code by ronie
# *  updates and additions since v1.3.0 by pkscuot
# *
# *  divingmule for script.image.lastfm.slideshow
# *  grajen3 for script.ImageCacher
# *  sfaxman for smartUnicode
# *
# *  code from all scripts/examples are used in script.artistslideshow
# *
# *  Musicbrainz python library by Kenneth Reitz
# *  see resource/musicbrainzngs/copying for copyright and use restrictions
# *  
# *  Last.fm:      http://www.last.fm/
# *  fanart.tv:    http://www.fanart.tv
# *  theaudiodb:   http://www.theaudiodb.com
# *  htbackdrops:  http://www.htbackdrops.org

import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import codecs, itertools, ntpath, os, random, re, shutil, socket, sys, time
import unicodedata, urllib, urllib2, urlparse
import xml.etree.ElementTree as xmltree
from resources.dicttoxml.dicttoxml import dicttoxml
from resources.fix_utf8.fix_utf8 import smartUTF8
if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path').decode('utf-8')
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ )
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

def log(msg, level=xbmc.LOGDEBUG):
    plugin = "Artist Slideshow"
    if type(msg).__name__=='unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s" % (plugin, msg.__str__()), level)

def checkDir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdir(path)

def getCacheThumbName(url, CachePath):
    thumb = xbmc.getCacheThumbName(url)
    thumbpath = os.path.join(CachePath, thumb.encode('utf-8'))
    return thumbpath

def saveURL( url, filename, *args, **kwargs ):
    data = grabURL( url, *args, **kwargs )
    if data:
        if writeFile( data, filename ):
            return True
        else:
            return False
    else:
        return False

def grabURL( url, *args, **kwargs ):
    req = urllib2.Request(url=url)
    for key, value in kwargs.items():
        req.add_header(key.replace('_', '-'), value)
    for header, value in req.headers.items():
        log('url header %s is %s' % (header, value) )
    try:
        url_data = urllib2.urlopen( req ).read()
    except urllib2.URLError, urllib2.HTTPError:
        log( 'site unreachable at ' + url )
        return ''
    except socket.error:
        log( 'timeout error while downloading from ' + url )
        return ''
    except Exception, e:
        log( 'unknown error while downloading from ' + url )
        log( e )
        return ''
    return url_data

def cleanText(text):
    text = re.sub('<a [^>]*>|</a>|<span[^>]*>|</span>','',text)
    text = re.sub('&quot;','"',text)
    text = re.sub('&amp;','&',text)
    text = re.sub('&gt;','>',text)
    text = re.sub('&lt;','<',text)
    text = re.sub('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.','',text)
    text = re.sub('Read more about .* on Last.fm.','',text)
    return text.strip()

def path_leaf(path):
    path, filename = ntpath.split(path)
    return {"path":path, "filename":filename}

def excluded(item):
    item_split = path_leaf(item)
    exclusion_file = os.path.join(item_split['path'], '_exclusions.nfo')
    if xbmcvfs.exists( exclusion_file ):
        exclusions = readFile( exclusion_file )
        if item_split['filename'] in exclusions:
            return True
        else:
            return False
    else:
        writeFile( '', exclusion_file )

def download(src, dst, dst2):
    if (not xbmc.abortRequested):
        tmpname = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % ( __addonname__ , xbmc.getCacheThumbName(src) ))
        if not excluded( dst ):
            if xbmcvfs.exists(tmpname):
                xbmcvfs.delete(tmpname)
            if not saveURL( src, tmpname ):
                return False
            if os.path.getsize(tmpname) > 999:
                log( 'copying file to transition directory' )
                xbmcvfs.copy(tmpname, dst2)
                log( 'moving file to cache directory' )
                xbmcvfs.rename(tmpname, dst)
                return True
            else:
                xbmcvfs.delete(tmpname)
                return False
        else:
            return False 

def writeFile( data, filename ):
    try:
        thefile = open( filename, 'wb' )
        thefile.write( data )
        thefile.close()
    except IOError:
        log( 'unable to write data to ' + filename )
        return False
    except Exception, e:
        log( 'unknown error while writing data to ' + filename )
        log( e )
        return False
    return True

def readFile( filename ):
    if xbmcvfs.exists( filename):
        try:
            the_file = open (filename, 'r')
            data = the_file.read()
            the_file.close()
        except IOError:
            log( 'unable to rea data from ' + filename )
            return ''
        except Exception, e:
            log( 'unknown error while reading data from ' + filename )
            log( e )
            return ''
        return data
    else:
        return ''


class Main:
    def __init__( self ):
        self._parse_argv()
        self._get_settings()
        self._init_vars()
        self._make_dirs()
        self._migrate()
        if xbmc.getInfoLabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
            log('script already running')
        else:
            self.LastCacheTrim = 0
            self._set_property("ArtistSlideshowRunning", "True")
            if( xbmc.Player().isPlayingAudio() == False and xbmc.getInfoLabel( self.EXTERNALCALL ) == '' ):
                log('no music playing')
                if( self.DAEMON == "False" ):
                    self._set_property("ArtistSlideshowRunning")
            else:
                log('first song started')
                time.sleep(1) # it may take some time for xbmc to read tag info after playback started
                self._use_correct_artwork()
                self._trim_cache()
            while (not xbmc.abortRequested):
                time.sleep(1)
                if xbmc.getInfoLabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
                    if( xbmc.Player().isPlayingAudio() == True or xbmc.getInfoLabel( self.EXTERNALCALL ) != '' ):
                        if set( self.ALLARTISTS ) <> set( self._get_current_artists() ):
                            self._clear_properties()
                            self.UsingFallback = False
                            self._use_correct_artwork()
                            self._trim_cache()
                        elif(not (self.DownloadedAllImages or self.UsingFallback)):
                            if(not (self.LocalImagesFound and self.PRIORITY == '1')):
                                log('same artist playing, continue download')
                                self._use_correct_artwork()
                    else:
                        time.sleep(2) # doublecheck if playback really stopped
                        if( xbmc.Player().isPlayingAudio() == False and xbmc.getInfoLabel( self.EXTERNALCALL ) == '' ):
                            if ( self.DAEMON == "False" ):
                                self._set_property( "ArtistSlideshowRunning" )
                else:
                    self._clear_properties()
                    break


    def _use_correct_artwork( self ):
        self.ALLARTISTS = self._get_current_artists()
        self.ARTISTNUM = 0
        self.TOTALARTISTS = len( self.ALLARTISTS )
        self.MergedImagesFound = False
        for artist, mbid in self._get_current_artists_info( 'withmbid' ):
            log( 'current artist is %s with a mbid of %s' % (artist, mbid) )
            self.ARTISTNUM += 1
            self.NAME = artist
            self.MBID = mbid
            self._set_infodir( self.NAME )
            if self.USEOVERRIDE == 'true':
                log('using override directory for images')
                self._set_property("ArtistSlideshow", self.OVERRIDEPATH)
                if(self.ARTISTNUM == 1):
                    self._get_artistinfo()
            elif self.PRIORITY == '1' and self.LOCALARTISTPATH:
                log('looking for local artwork')
                self._get_local_images()
                if(not self.LocalImagesFound):
                    log('no local artist artwork found, start download')
                    self._start_download()
            elif self.PRIORITY == '2' and self.LOCALARTISTPATH:
                log('looking for local artwork')
                self._get_local_images()
                log('start download')
                self._start_download()
            else:
                log('start download')
                self._start_download()
                if not (self.CachedImagesFound or self.ImageDownloaded):
                    log('no remote artist artwork found, looking for local artwork')
                    self._get_local_images()
        if not (self.LocalImagesFound or self.CachedImagesFound or self.ImageDownloaded or self.MergedImagesFound):
            if (self.USEFALLBACK == 'true'):
                log('no images found for artist, using fallback slideshow')
                log('fallbackdir = ' + self.FALLBACKPATH)
                self.UsingFallback = True
                self._set_property("ArtistSlideshow", self.FALLBACKPATH)


    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except IndexError:
            params = {}        
        except Exception, e:
            log( 'unexpected error while parsing arguments' )
            log( e )
            params = {}
        self.WINDOWID = params.get( "windowid", "12006")
        log( 'window id is set to %s' % self.WINDOWID )
        self.PASSEDFIELDS = {}
        self.FIELDLIST = ['artistfield', 'titlefield', 'albumfield', 'mbidfield']
        for item in self.FIELDLIST:
            self.PASSEDFIELDS[item] = params.get( item, '' )
            log( '%s is set to %s' % (item, self.PASSEDFIELDS[item]) )
        self.DAEMON = params.get( "daemon", "False" )
        if self.DAEMON == "True":
            log('daemonizing')


    def _get_settings( self ):
        self.FANARTTV = __addon__.getSetting( "fanarttv" )
        self.THEAUDIODB = __addon__.getSetting( "theaudiodb" )
        self.HTBACKDROPS = __addon__.getSetting( "htbackdrops" )
        self.ARTISTINFO = __addon__.getSetting( "artistinfo" )
        self.LANGUAGE = __addon__.getSetting( "language" )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                log('language = %s' % self.LANGUAGE)
                break
        self.LOCALARTISTPATH = __addon__.getSetting( "local_artist_path" ).decode('utf-8')
        self.PRIORITY = __addon__.getSetting( "priority" )
        self.USEFALLBACK = __addon__.getSetting( "fallback" )
        self.FALLBACKPATH = __addon__.getSetting( "fallback_path" ).decode('utf-8')
        self.USEOVERRIDE = __addon__.getSetting( "slideshow" )
        self.OVERRIDEPATH = __addon__.getSetting( "slideshow_path" ).decode('utf-8')
        self.RESTRICTCACHE = __addon__.getSetting( "restrict_cache" )
        try:
            self.maxcachesize = int(__addon__.getSetting( "max_cache_size" )) * 1000000
        except ValueError:
            self.maxcachesize = 1024 * 1000000
        except Exception, e:
            log( 'unexpected error while parsing maxcachesize setting' )
            log( e )
            self.maxcachesize = 1024 * 1000000
        self.NOTIFICATIONTYPE = __addon__.getSetting( "show_progress" )
        if self.NOTIFICATIONTYPE == "2":
            self.PROGRESSPATH = __addon__.getSetting( "progress_path" ).decode('utf-8')
            log('set progress path to %s' % self.PROGRESSPATH)
        else:
            self.PROGRESSPATH = ''
        if __addon__.getSetting( "fanart_folder" ):
            self.FANARTFOLDER = __addon__.getSetting( "fanart_folder" ).decode('utf-8')
            log('set fanart folder to %s' % self.FANARTFOLDER)
        else:
            self.FANARTFOLDER = 'extrafanart'


    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.SKININFO = {}
        self._set_property( "ArtistSlideshow.CleanupComplete" )
        for item in self.FIELDLIST:
            if self.PASSEDFIELDS[item]:
                self.SKININFO[item[0:-5]] = "Window(%s).Property(%s)" % ( self.WINDOWID, self.PASSEDFIELDS[item] )
            else:
                self.SKININFO[item[0:-5]] = ''
        self.ARTISTSLIDESHOW = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow" )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )
        self.EXTERNALCALLSTATUS = xbmc.getInfoLabel( self.EXTERNALCALL )
        log( 'external call is set to ' + xbmc.getInfoLabel( self.EXTERNALCALL ) )
        self.NAME = ''
        self.ALLARTISTS = []
        self.MBID = ''
        self.VARIOUSARTISTSMBID = '89ad4ac3-39f7-470e-963a-56509c546377'
        self.LASTPLAYINGFILE = ''
        self.LASTJSONRESPONSE = ''
        self.LASTARTISTREFRESH = 0
        self.LocalImagesFound = False
        self.CachedImagesFound = False
        self.ImageDownloaded = False
        self.DownloadedAllImages = False
        self.UsingFallback = False
        self.MINREFRESH = 9.9
        self.TransitionDir = xbmc.translatePath('special://profile/addon_data/%s/transition' % __addonname__ ).decode('utf-8')
        self.MergeDir = xbmc.translatePath('special://profile/addon_data/%s/merge' % __addonname__ ).decode('utf-8')
        self.InitDir = xbmc.translatePath('%s/resources/black' % __addonpath__ ).decode('utf-8')
        LastfmApiKey = 'afe7e856e4f4089fc90f841980ea1ada'
        fanarttvApiKey = '7a93c84fe1c9999e6f0fec206a66b0f5'
        theaudiodbApiKey = '193621276b2d731671156g'
        HtbackdropsApiKey = '96d681ea0dcb07ad9d27a347e64b652a'
        self.LastfmURL = 'http://ws.audioscrobbler.com/2.0/?autocorrect=1&api_key=' + LastfmApiKey
        self.fanarttvURL = 'http://api.fanart.tv/webservice/artist/%s/' % fanarttvApiKey
        self.fanarttvOPTIONS = '/json/artistbackground/'
        self.theaudiodbURL = 'http://www.theaudiodb.com/api/v1/json/%s/' % theaudiodbApiKey
        self.theaudiodbARTISTURL = 'artist-mb.php?i='
        self.theaudiodbALBUMURL = 'album.php?i='
        self.HtbackdropsQueryURL = 'http://htbackdrops.org/api/' + HtbackdropsApiKey + '/searchXML?default_operator=and&fields=title&aid=1'
        self.HtbackdropsDownloadURL = 'http://htbackdrops.org/api/' + HtbackdropsApiKey + '/download/'


    def _move_info_files( self, old_loc, new_loc, type ):
        log( 'attempting to move from %s to %s' % (old_loc, new_loc) )
        try:
            os.chdir( old_loc )
            folders = os.listdir( old_loc )
        except OSError:
            log( 'no directory found: ' + old_loc )
            return
        except Exception, e:
            log( 'unexpected error while getting directory list' )
            log( e )
            return
        for folder in folders:
            if type == 'cache':
                old_folder = os.path.join( old_loc, folder )
                new_folder = os.path.join( new_loc, folder )
            elif type == 'local':
                old_folder = os.path.join( old_loc, folder, self.FANARTFOLDER )
                new_folder = os.path.join( new_loc, xbmc.getCacheThumbName(folder).replace('.tbn', '') )
            try:
                old_files = os.listdir( old_folder )
            except Exception, e:
                log( 'unexpected error while getting directory list' )
                log( e )
                old_files = []
            exclude_path = os.path.join( old_folder, '_exclusions.nfo' )
            if old_files and type == 'cache' and not xbmcvfs.exists(exclude_path):
                writeFile( '', exclude_path )
            for old_file in old_files:
                if old_file.endswith( '.nfo' ) and not old_file == '_exclusions.nfo':
                    checkDir( new_folder )
                    new_file = old_file.strip('_')
                    if new_file == 'artistimagesfanarttv.nfo':
                        new_file = 'fanarttvartistimages.nfo'
                    elif new_file == 'artistimageshtbackdrops.nfo':
                        new_file = 'htbackdropsartistimages.nfo'
                    elif new_file == 'artistimageslastfm.nfo':
                        new_file = 'lastfmartistimages.nfo'
                    elif new_file == 'artistbio.nfo':
                        new_file = 'lastfmartistbio.nfo'
                    elif new_file == 'artistsalbums.nfo':
                        new_file = 'lastfmartistalbums.nfo'
                    elif new_file == 'artistsimilar.nfo':
                        new_file = 'lastfmartistsimilar.nfo'
                    xbmcvfs.rename( os.path.join(old_folder, old_file), os.path.join(new_folder, new_file) )
                    log( 'moving %s to %s' % (old_file, os.path.join(new_folder, new_file)) )


    def _migrate( self ):
        #this is a one time process to move and rename all the .nfo files to the new location
        root_path = xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode('utf-8')
        new_loc = os.path.join( root_path, 'ArtistInformation' )
        check_file = os.path.join( root_path, 'migrationcheck.nfo' )
        if not readFile( check_file ):
            self._move_info_files( os.path.join(root_path, 'ArtistSlideshow'), new_loc, 'cache' )
            if self.LOCALARTISTPATH:
                self._move_info_files( self.LOCALARTISTPATH, new_loc, 'local' )
            writeFile( '1.5.4', check_file )

    def _make_dirs( self ):
        checkDir(xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode('utf-8'))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/temp' % __addonname__ ).decode('utf-8'))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/ArtistSlideshow' % __addonname__ ).decode('utf-8'))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/ArtistInformation' % __addonname__ ).decode('utf-8'))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/transition' % __addonname__ ).decode('utf-8'))


    def _set_thedir(self, theartist, dirtype):
        CacheName = xbmc.getCacheThumbName(theartist).replace('.tbn', '')
        thedir = xbmc.translatePath('special://profile/addon_data/%s/%s/%s/' % ( __addonname__ , dirtype, CacheName, )).decode('utf-8')
        checkDir(thedir)
        return thedir


    def _set_cachedir( self, theartist ):
        self.CacheDir = self._set_thedir( theartist, "ArtistSlideshow" )


    def _set_infodir( self, theartist ):
        self.InfoDir = self._set_thedir( theartist, "ArtistInformation" )


    def _start_download( self ):
        self.CachedImagesFound = False
        self.DownloadedFirstImage = False
        self.DownloadedAllImages = False
        self.ImageDownloaded = False
        self.FirstImage = True
        cached_image_info = False
        if not self.NAME:
            log('no artist name provided')
            return
        if self.PRIORITY == '2' and self.LocalImagesFound:
            pass
            #self.CacheDir was successfully set in _get_local_images
        else:
            self._set_cachedir( self.NAME )
        log('cachedir = %s' % self.CacheDir)

        files = os.listdir(self.CacheDir)
        for file in files:
            if file.lower().endswith('tbn') or (self.PRIORITY == '2' and self.LocalImagesFound):
                self.CachedImagesFound = True

        if self.CachedImagesFound:
            log('cached images found')
            cached_image_info = True
            self.LASTARTISTREFRESH = time.time()
            if self.ARTISTNUM == 1:
                self._set_property("ArtistSlideshow", self.CacheDir)
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
        else:
            self.LASTARTISTREFRESH = 0
            if self.ARTISTNUM == 1:
                for cache_file in ['fanarttvartistimages.nfo', 'theaudiodbartistbio.nfo', 'htbackdropsartistimages.nfo']:
                    filename = os.path.join( self.InfoDir, cache_file.decode('utf-8') )
                    if xbmcvfs.exists( filename ):
                        if time.time() - os.path.getmtime(filename) < 1209600:
                            log('cached %s found' % filename)
                            cached_image_info = True
                        else:
                           log('outdated %s found' % filename)
                           cached_image_info = False
                if self.NOTIFICATIONTYPE == "1":
                    self._set_property("ArtistSlideshow", self.InitDir)
                    if not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30300)), smartUTF8(__language__(30301)), 5000, smartUTF8(__addonicon__))
                        xbmc.executebuiltin(command)
                elif self.NOTIFICATIONTYPE == "2":
                    if not cached_image_info:
                        self._set_property("ArtistSlideshow", self.PROGRESSPATH)
                    else:
                        self._set_property("ArtistSlideshow", self.InitDir)
                else:
                      self._set_property("ArtistSlideshow", self.InitDir)
        sourcelist = []
        sourcelist.append( ['fanarttv', self.FANARTTV] )
        sourcelist.append( ['theaudiodb', self.THEAUDIODB] )
        sourcelist.append( ['htbackdrops', self.HTBACKDROPS] )
        imagelist = []
        for source in sourcelist:
            log( ' checking the source %s with a value of %s.' % (source[0], source[1]) )
            if source[1] == "true":
                imagelist.extend( self._get_images(source[0]) )
        log('downloading images')
        for url in imagelist:
            if( self._playback_stopped_or_changed() ):
                return
            path = getCacheThumbName(url, self.CacheDir)
            path2 = getCacheThumbName(url, self.TransitionDir)
            if not xbmcvfs.exists(path):
                if download(url, path, path2):
                    log('downloaded %s to %s' % (url, path) )
                    self.ImageDownloaded=True
            elif excluded( path ):
                xbmcvfs.delete( path )
            if self.ImageDownloaded:
                if( self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                    self._set_property("ArtistSlideshow", self.CacheDir)
                    self.LASTARTISTREFRESH = time.time()
                    self._clean_dir( self.TransitionDir )
                    return
                if not self.CachedImagesFound:
                    self.CachedImagesFound = True
                    if self.ARTISTINFO == "true" and self.ARTISTNUM == 1:
                        self._get_artistinfo()
                wait_elapsed = time.time() - self.LASTARTISTREFRESH
                if( wait_elapsed > self.MINREFRESH ):
                    if( not (self.FirstImage and not self.CachedImagesFound) ):
                        self._wait( self.MINREFRESH - (wait_elapsed % self.MINREFRESH) )
                    if( not self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                        self._refresh_image_directory()
                self.FirstImage = False

        if self.ImageDownloaded:
            log('finished downloading images')
            self.DownloadedAllImages = True
            if( self._playback_stopped_or_changed() ):
                self._set_property("ArtistSlideshow", self.CacheDir)
                self.LASTARTISTREFRESH = time.time()
                self._clean_dir( self.TransitionDir )
                return
            log( 'cleaning up from refreshing slideshow' )
            wait_elapsed = time.time() - self.LASTARTISTREFRESH
            if( wait_elapsed < self.MINREFRESH ):
                self._wait( self.MINREFRESH - wait_elapsed )
            if( not self._playback_stopped_or_changed() ):
                if self.ARTISTNUM == 1:
                    self._refresh_image_directory()
                    if self.NOTIFICATIONTYPE == "1" and not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30304)), smartUTF8(__language__(30305)), 5000, smartUTF8(__addonicon__))
                        xbmc.executebuiltin(command)
                if self.TOTALARTISTS > 1:
                    self._merge_images()
            if( xbmc.getInfoLabel( self.ARTISTSLIDESHOW ).decode('utf-8') == self.TransitionDir and self.ARTISTNUM == 1):
                self._wait( self.MINREFRESH )
                if( not self._playback_stopped_or_changed() ):
                    self._refresh_image_directory()
            self._clean_dir( self.TransitionDir )

        if not self.ImageDownloaded:
            log('no images downloaded')
            self.DownloadedAllImages = True
            if not self.CachedImagesFound:
                if self.ARTISTNUM == 1:
                    log('clearing ArtistSlideshow property')
                    self._set_property("ArtistSlideshow", self.InitDir)
                    if self.NOTIFICATIONTYPE == "1" and not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30302)), smartUTF8(__language__(30303)), 10000, smartUTF8(__addonicon__))
                        xbmc.executebuiltin(command)
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
                self._set_property("ArtistSlideshow", self.InitDir)
                self.Abort = True
                return


    def _clean_dir( self, dir_path ):
        try:
            old_files = os.listdir( dir_path )
        except Exception, e:
            log( 'unexpected error while getting directory list' )
            log( e )
            old_files = []
        for old_file in old_files:
            if not old_file.endswith( '.nfo' ):
                xbmcvfs.delete( os.path.join(dir_path, old_file) )
                log( 'deleting file ' + old_file )


    def _refresh_image_directory( self ):
        if( xbmc.getInfoLabel( self.ARTISTSLIDESHOW ).decode('utf-8') == self.TransitionDir):
            self._set_property("ArtistSlideshow", self.CacheDir)
            log( 'switching slideshow to ' + self.CacheDir )
        else:
            self._set_property("ArtistSlideshow", self.TransitionDir)
            log( 'switching slideshow to ' + self.TransitionDir )
        self.LASTARTISTREFRESH = time.time()
        log( 'Last slideshow refresh time is ' + str(self.LASTARTISTREFRESH) )


    def _split_artists( self, response):
        return response.replace('ft.',' / ').replace('feat.',' / ').split(' / ')


    def _get_featured_artists( self, data ):
        the_split = data.replace('ft.','feat.').split('feat.')
        if len( the_split ) > 1:
            return self._split_artists( the_split[-1] )
        else:
            return []


    def _get_current_artists( self ):
        current_artists = []
        for artist, mbid in self._get_current_artists_info( 'withoutmbid'):
            current_artists.append( artist )
        return current_artists


    def _get_current_artists_info( self, type ):
        featured_artists = ''
        artist_names = []
        artists_info = []
        mbids = []
        if( xbmc.Player().isPlayingAudio() == True ):
            try:
                #playing_file = xbmc.Player().getPlayingFile()
                playing_file = xbmc.Player().getPlayingFile() + ' - ' + xbmc.Player().getMusicInfoTag().getArtist() + ' - ' + xbmc.Player().getMusicInfoTag().getTitle()
                log( 'playing file is ' + playing_file )
            except RuntimeError:
                return artists_info
            except Exception, e:
                log( 'unexpected error getting playing file back from XBMC' )
                log( e )
                return artists_info
            if playing_file != self.LASTPLAYINGFILE:
                # if the same file is playing, use cached JSON response instead of doing a new query
                response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "musicbrainzartistid"]},"id":1}' )
                self.LASTPLAYINGFILE = playing_file
                self.LASTJSONRESPONSE = response
            else:
                response = self.LASTJSONRESPONSE
            try:
                artist_names = json.loads(response)['result']['item']['artist']
            except (IndexError, KeyError, ValueError):
                artist_names = []
            except Exception, e:
                log( 'unexpected error getting JSON back from XBMC' )
                log( e )
                artist_names = []
            try:
                mbids = json.loads(response)['result']['item']['muiscbrainzartistid']
            except (IndexError, KeyError, ValueError):
                mbids = []
            except Exception, e:
                log( 'unexpected error getting JSON back from XBMC' )
                log( e )
                mbids = []
            try:
                playing_song = xbmc.Player().getMusicInfoTag().getTitle()
            except RuntimeError:
                playing_song = ''
            except Exception, e:
                log( 'unexpected error gettting playing song back from XBMC' )
                log( e )
                playing_song = ''
            if not artist_names:
                log( 'No artist names returned from JSON call, assuming this is an internet stream' )
                try:
                    playingartist = playing_song[0:(playing_song.find('-'))-1]
                except RuntimeError:
                    playingartist = ''
                    playing_song = ''
                except Exception, e:
                    log( 'unexpected error gettting playing song back from XBMC' )
                    log( e )
                    playingartist = ''
                    playing_song = ''
                artist_names = self._split_artists( playingartist )
            featured_artists = self._get_featured_artists( playing_song )
        elif xbmc.getInfoLabel( self.SKININFO['artist'] ):
            artist_names = self._split_artists( xbmc.getInfoLabel(self.SKININFO['artist']) )
            mbids = xbmc.getInfoLabel( self.SKININFO['mbid'] ).split( ',' )
            featured_artists = self._get_featured_artists( xbmc.getInfoLabel(self.SKININFO['title']) )
        if featured_artists:
            for one_artist in featured_artists:
                artist_names.append( one_artist.strip(' ()') )            
        for artist_name, mbid in itertools.izip_longest( artist_names, mbids, fillvalue='' ):
            if artist_name:
                if not mbid and type == 'withmbid':
                    mbid = self._get_musicbrainz_id( artist_name )
                else:
                    mbid = ''
                artists_info.append( (artist_name, mbid) )
        return artists_info


    def _playback_stopped_or_changed( self ):
        if set( self.ALLARTISTS ) <> set( self._get_current_artists() ) or self.EXTERNALCALLSTATUS != xbmc.getInfoLabel( self.EXTERNALCALL ):
            self._clear_properties()
            return True
        else:
            return False


    def _get_local_images( self ):
        self.LocalImagesFound = False
        if not self.NAME:
            log('no artist name provided')
            return
        self.CacheDir = os.path.join( self.LOCALARTISTPATH, self.NAME, self.FANARTFOLDER )
        log('cachedir = %s' % self.CacheDir)
        try:
            files = os.listdir(self.CacheDir)
        except OSError:
            files = []
        except Exception, e:
            log( 'unexpected error getting directory list' )
            log( e )
            files = []
        for file in files:
            if(file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')):
                self.LocalImagesFound = True
        if self.LocalImagesFound:
            log('local images found')
            if self.ARTISTNUM == 1:
                self._set_property("ArtistSlideshow", self.CacheDir)
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
            if self.TOTALARTISTS > 1:
               self._merge_images()


    def _merge_images( self ):
        log( 'merging files from primary directory %s into merge directory %s' % (self.CacheDir, self.MergeDir) )
        self.MergedImagesFound = True
        files = os.listdir(self.CacheDir)
        for file in files:
            if(file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')):
                xbmcvfs.copy(os.path.join(self.CacheDir, file), os.path.join(self.MergeDir, file))
        if self.ARTISTNUM == self.TOTALARTISTS:
            wait_elapsed = time.time() - self.LASTARTISTREFRESH
            if( wait_elapsed > self.MINREFRESH ):
                self._wait( self.MINREFRESH - (wait_elapsed % self.MINREFRESH) )
            else:
                self._wait( self.MINREFRESH - (wait_elapsed + 2) )  #not sure why there needs to be a manual adjustment here
            if not self._playback_stopped_or_changed():
                log( 'switching slideshow to merge directory' )
                self._set_property("ArtistSlideshow", self.MergeDir)


    def _trim_cache( self ):
        if( self.RESTRICTCACHE == 'true' and not self.PRIORITY == '2' ):
            now = time.time()
            cache_trim_delay = 0   #delay time is in seconds
            if( now - self.LastCacheTrim > cache_trim_delay ):
                log(' trimming the cache down to %s bytes' % self.maxcachesize )
                cache_root = xbmc.translatePath( 'special://profile/addon_data/%s/ArtistSlideshow/' % __addonname__ ).decode('utf-8')
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
                        self._clean_dir( os.path.join(cache_root, folder) )
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
        if site == 'fanarttv':
            if self.MBID:
                self.url = self.fanarttvURL + self.MBID + self.fanarttvOPTIONS
                log( 'asking for images from: %s' %self.url )
            else:
                return []
        elif site == 'theaudiodb':
            if self.MBID:
                self.url = self.theaudiodbURL + self.theaudiodbARTISTURL + self.MBID
                log( 'asking for images from: %s' %self.url )
            else:
                return []
        elif site == "htbackdrops":
            self.url = self.HtbackdropsQueryURL + '&keywords=' + self.NAME.replace('&','%26').replace(' ', '+')
            log( 'asking for images from: %s' %self.url )
        images = self._get_data(site, 'images')
        return images


    def _get_playing_item( self, item ):
        got_item = False
        playing_item = ''
        max_trys = 3
        num_trys = 1
        while not got_item:
            try:
                if item == 'album':
                    playing_item = xbmc.Player().getMusicInfoTag().getAlbum()
                elif item == 'title':
                    playing_item = xbmc.Player().getMusicInfoTag().getTitle()                
                got_item = True
            except RuntimeError:
                got_title = False
            except Exception, e:
                got_title = False
                log( 'unexpected error getting %s from XBMC' % item )
                log( e )
            if num_trys > max_trys:
                break
            else:
                num_trys = num_trys + 1
                self._wait(1)
                if self._playback_stopped_or_changed():
                    break
        #if nothing is playing, assume the information was passed by another add-on
        if not playing_item:
            playing_item = xbmc.getInfoLabel( self.SKININFO[item] )
        return playing_item


    def _get_musicbrainz_info( self, mboptions, mbsearch, type, query_times ):
        mbbase = 'http://www.musicbrainz.org/ws/2/'
        theartist = self.NAME
        mb_data = []
        offset = 0
        do_loop = True
        elapsed_time = query_times['current'] - query_times['last']
        if elapsed_time < 1:
            self._wait( 1 - elapsed_time )
        elif self._playback_stopped_or_changed():
            return []        
        query_start = time.time()
        while do_loop:
            if mbsearch:
                mbquery = mbbase + mboptions + urllib.quote_plus( smartUTF8(mbsearch), ':!"' )
            else:
                mbquery = mbbase + mboptions + '&offset=' + str(offset)
            log( 'getting results from musicbrainz using: ' + mbquery)
            for x in range(1, 5):
                try:
                    json_data = json.loads( grabURL(mbquery, User_Agent=__addonname__  + '/' + __addonversion__  + '( https://github.com/pkscout/artistslideshow )') )
                except ValueError:
                    json_data = []
                except Exception, e:
                    log( 'unexpected error getting JSON data from ' + mbquery )
                    log( e )
                    json_data = []
                if self._playback_stopped_or_changed():
                    return []       
                if not json_data:
                    wait_time = random.randint(2,5)
                    log('site unreachable, waiting %s seconds to try again.' % wait_time)
                    self._wait( wait_time )
                else:
                    try:
                        mb_data.extend( json_data[type] )
                    except KeyError:
                        log( 'no valid value for %s found in JSON data' % type )
                        offset = -100
                    except Exception, e:
                        log( 'unexpected error while parsing JSON data' )
                        log( e )
                        offset = -100
                    break
            offset = offset + 100
            try:
                total_items = int(json_data[type[:-1] + '-count'])
            except KeyError:
                total_items = 0
            except Exception, e:
                log( 'unexpected error getting JSON data from ' + mbquery )
                log( e )
                total_items = 0
            if (not mbsearch) and (total_items - offset > 0):
                log( 'getting more data from musicbrainz' )
                query_elapsed = time.time() - query_start
                if query_elapsed < 1:
                    self._wait(1 - query_elapsed)
                elif self._playback_stopped_or_changed():
                    return []        
            else:
                do_loop = False
        return mb_data


    def _parse_musicbrainz_info( self, type, mbid, playing_thing, query_times ):
        if self._playback_stopped_or_changed():
            return False
        log( "checking this artist's " + type + "s against currently playing " + type )
        mboptions = type + '?artist=' + mbid + '&limit=100&fmt=json'
        for thing in self._get_musicbrainz_info( mboptions, '', type + 's', query_times ):
            title = smartUTF8( thing['title'] )
            if playing_thing.rfind('(') > 0:
                playing_title = smartUTF8( playing_thing[:playing_thing.rfind('(')-2] )
            else:
                playing_title = smartUTF8( playing_thing )
            log( 'comparing musicbrainz %s: %s with local %s: %s' % (type, title, type, playing_title) )
            if title.lower().startswith( playing_title.lower() ) or playing_title.lower().startswith( title.lower() ):
                log( 'found matching %s, this should be the right artist' % type )
                return True
        return False


    def _get_musicbrainz_id ( self, theartist ):
        mbid = ''
        log( 'Looking for a musicbrainz ID for artist ' + theartist )
        log( 'Looking for musicbrainz ID in the musicbrainz.nfo file' )
        self._set_infodir( theartist )
        filename = os.path.join( self.InfoDir, 'musicbrainz.nfo' )
        if xbmcvfs.exists( filename ):
            mbid = readFile( filename )
            if not mbid:
                if time.time() - os.path.getmtime(filename) < 1209600:
                    log( 'no musicbrainz ID found in musicbrainz.nfo file' )
                    return ''
                else:
                    log( 'no musicbrainz ID found in musicbrainz.nfo file, trying lookup again' )
            else:
                log( 'musicbrainz ID found in musicbrainz.nfo file' )
                return mbid
        else:
            log( 'no musicbrainz.nfo file found' )
        if self._playback_stopped_or_changed():
            writeFile( '', filename )
            return ''
        # this is here to account for songs or albums that have the artist 'Various Artists'
        # because AS chokes when trying to find this artist on MusicBrainz
        if theartist.lower() == 'various artists':
            writeFile( self.VARIOUSARTISTSMBID, filename)
            return self.VARIOUSARTISTSMBID
        log( 'querying musicbrainz.com for musicbrainz ID. This is about to get messy.' )
        badSubstrings = ["the ", "The ", "THE ", "a ", "A ", "an ", "An ", "AN "]
        searchartist = theartist
        for badSubstring in badSubstrings:
            if theartist.startswith(badSubstring):
                searchartist = theartist.replace(badSubstring, "")
        mboptions = 'artist/?fmt=json&query=' 
        mbsearch = 'artist:"%s"' % searchartist
        query_times = {'last':0, 'current':time.time()}
        log( 'parsing musicbrainz response for muiscbrainz ID' )
        cached_mb_info = False
        for artist in self._get_musicbrainz_info( mboptions, mbsearch, 'artist', query_times ):
            mbid = ''
            if self._playback_stopped_or_changed():
                return ''
            try:
                all_names = artist['aliases']
            except KeyError:
                all_names = []
            except Exception, e:
                log( 'unexpected error getting JSON data from XBMC response' )
                log( e )
                all_names = []
            aliases = []
            if all_names:
                for one_name in all_names:
                    aliases.append( one_name['name'].lower() )
            if artist['name'].lower() == theartist.lower() or theartist.lower() in aliases:
                mbid = artist['id']
                log( 'found a potential musicbrainz ID of %s for %s' % (mbid, theartist) )
                playing_album = self._get_playing_item( 'album' )
                if playing_album:
                    log( 'checking album name against releases in musicbrainz' )
                    query_times = {'last':query_times['current'], 'current':time.time()}
                    cached_mb_info = self._parse_musicbrainz_info( 'release', mbid, playing_album, query_times )
                if not cached_mb_info:
                    playing_song = self._get_playing_item( 'title' )
                    if playing_song:
                        log( 'checking song name against recordings in musicbrainz' )
                        if smartUTF8( theartist ) == playing_song[0:(playing_song.find('-'))-1]:
                            playing_song = playing_song[(playing_song.find('-'))+2:]
                        query_times = {'last':query_times['current'], 'current':time.time()}
                        cached_mb_info = self._parse_musicbrainz_info( 'recording', mbid, playing_song, query_times )
                        if not cached_mb_info:
                            log( 'checking song name against works in musicbrainz' )
                            query_times = {'last':query_times['current'], 'current':time.time()}
                            cached_mb_info = self._parse_musicbrainz_info( 'work', mbid, playing_song, query_times )
                if cached_mb_info:
                    break
                else:
                    log( 'No matching song/album found for %s. Trying the next artist.' % theartist )
        if cached_mb_info:
            log( 'Musicbrainz ID for %s is %s. writing out to cache file.' % (theartist, mbid) )
        else:
            mbid = ''
            log( 'No musicbrainz ID found for %s. writing empty cache file.' % theartist )
        writeFile( mbid, filename )
        return mbid

                                
    def _get_artistinfo( self ):
        log( 'checking for local artist bio data' )
        bio = self._get_local_data( 'bio' )
        if bio == []:
            if self.MBID:
                self.url = self.theaudiodbURL + self.theaudiodbARTISTURL + self.MBID
                log( 'trying to get artist bio from ' + self.url )
                bio = self._get_data( 'theaudiodb', 'bio' )
        if bio == []:
            self.url = self.LastfmURL + '&lang=' + self.LANGUAGE + '&method=artist.getInfo&artist=' + urllib.quote_plus( smartUTF8(self.NAME) )
            log( 'trying to get artist bio from ' + self.url )
            bio = self._get_data('lastfm', 'bio')
        if bio == []:
            self.biography = ''
        else:
            self.biography = cleanText(bio[0])
        self.albums = self._get_local_data( 'albums' )
        if self.albums == []:
            theaudiodb_id = readFile( os.path.join(self.InfoDir, 'theaudiodbid.nfo') )
            if theaudiodb_id:
                self.url = self.theaudiodbURL + self.theaudiodbALBUMURL + theaudiodb_id
                log( 'trying to get artist albumns from ' + self.url )
                self.albums = self._get_data('theaudiodb', 'albums')
        if self.albums == []:
            self.url = self.LastfmURL + '&method=artist.getTopAlbums&artist=' + urllib.quote_plus( smartUTF8(self.NAME) )
            log( 'trying to get artist albums from ' + self.url )
            self.albums = self._get_data('lastfm', 'albums')
        self.similar = self._get_local_data( 'similar' )
        if self.similar == []:
            self.url = self.LastfmURL + '&method=artist.getSimilar&artist=' + urllib.quote_plus( smartUTF8(self.NAME) )
            self.similar = self._get_data('lastfm', 'similar')
        self._set_properties()


    def _get_local_data( self, item ):
        data = []
        filenames = []
        local_path = os.path.join( self.LOCALARTISTPATH, self.NAME, 'override' )
        if item == "similar":
            filenames.append( os.path.join( local_path, 'artistsimilar.nfo' ) )
        elif item == "albums":
            filenames.append( os.path.join( local_path, 'artistsalbums.nfo' ) )
        elif item == "bio":
            filenames.append( os.path.join( local_path, 'artistbio.nfo' ) )
        found_xml = True
        for filename in filenames:
            log( 'checking filename ' + filename )
            try:
                xmldata = xmltree.parse(filename).getroot()
            except Exception, e:
                log('invalid or missing local xml file for %s' % item)
                log( e )
                found_xml = False
            if found_xml:
                break
        if not found_xml:
            return []
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
        ForceUpdate = True
        if item == "images":
            if site == "fanarttv":
                filename = os.path.join( self.InfoDir, 'fanarttvartistimages.nfo')
            elif site == "theaudiodb":
                filename = os.path.join( self.InfoDir, 'theaudiodbartistbio.nfo')
                id_filename = os.path.join( self.InfoDir, 'theaudiodbid.nfo')
            elif site == "htbackdrops":
                filename = os.path.join( self.InfoDir, 'htbackdropsartistimages.nfo')
        elif item == "bio":
            if site == "theaudiodb":
                filename = os.path.join( self.InfoDir, 'theaudiodbartistbio.nfo')
                id_filename = os.path.join( self.InfoDir, 'theaudiodbid.nfo')
            elif site == "lastfm":
                filename = os.path.join( self.InfoDir, 'lastfmartistbio.nfo')
        elif item == "similar":
            filename = os.path.join( self.InfoDir, 'lastfmartistsimilar.nfo')
        elif item == "albums":
            if site == "theaudiodb":
                filename = os.path.join( self.InfoDir, 'theaudiodbartistsalbums.nfo')
            elif site == "lastfm":
                filename = os.path.join( self.InfoDir, 'lastfmartistalbums.nfo')
        if xbmcvfs.exists( filename ):
            if time.time() - os.path.getmtime(filename) < 1209600:
                log('cached artist %s info found' % item)
                ForceUpdate = False
            else:
                log('outdated cached info found for %s ' % item)
        if ForceUpdate:
            log('downloading artist %s info from %s' % (item, site))
            if site == 'fanarttv' or site == 'theaudiodb':
                #converts the JSON response to XML
                try:
                    json_data = json.loads( grabURL( self.url ) )
                except ValueError:
                    json_data = []
                except Exception, e:
                    log( 'unexpected error parsing JSON data' )
                    log( e )
                if json_data:
                    if site == 'fanarttv':
                        try:
                            json_data = dict(map(lambda (key, value): ('artistImages', value), json_data.items()))
                        except AttributeError:
                            return data
                        except Exception, e:
                            log( 'unexpected error fixing fanart.tv JSON data' )
                            log( e )
                            return data
                    writeFile( dicttoxml( json_data ).encode('utf-8'), filename )
                    json_data = ''
                else:
                    return data
            elif not saveURL( self.url, filename ):
                return data
        try:
            xmldata = xmltree.parse(filename).getroot()
        except Exception, e:
            log('invalid or missing xml file')
            log( e )
            xbmcvfs.delete(filename)
            return data
        if item == "images":
            if site == "fanarttv":
                for element in xmldata.getiterator():
                    if element.tag == "url":
                        data.append(element.text)
            elif site == "theaudiodb":
                for element in xmldata.getiterator():
                    if element.tag.startswith( "strArtistFanart" ):
                        if element.text:
                            data.append(element.text)
                    if element.tag == 'idArtist' and not xbmcvfs.exists( id_filename ):
                        writeFile( element.text, id_filename )
            elif site == "htbackdrops":
                for element in xmldata.getiterator():
                    if element.tag == "id":
                        data.append(self.HtbackdropsDownloadURL + str( element.text ) + '/fullsize')
        elif item == "bio":
            if site == "theaudiodb":
                for element in xmldata.getiterator():
                    if element.tag == "strBiography" + self.LANGUAGE.upper():
                        bio = element.text
                        if not bio:
                            bio = ''
                        data.append(bio)            
                    if element.tag == 'idArtist' and not xbmcvfs.exists( id_filename ):
                        writeFile( element.text, id_filename )
            if site == "lastfm":
                for element in xmldata.getiterator():
                    if element.tag == "content":
                        bio = element.text
                        if not bio:
                            bio = ''
                        data.append(bio)
        elif item == "similar":
            if site == "lastfm":
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
            if site == "theaudiodb":
                match = False
                for element in xmldata.getiterator():
                    if element.tag == "strAlbum":
                        name = element.text
                        name.encode('ascii', 'ignore')
                        match = True
                    elif element.tag == "strAlbumThumb" and match:
                        image = element.text
                        if not image:
                            image = ''
                        data.append( ( name , image ) )            
                        match = False
            if site == "lastfm":
                match = False
                for element in xmldata.getiterator():
                    if element.tag == "name":
                        if match:
                            match = False
                        else:
                            name = element.text
                            name.encode('ascii', 'ignore')
                            match = True
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
      self._set_property("ArtistSlideshow.ArtistBiography", self.biography)
      for count, item in enumerate( self.similar ):
          self._set_property("ArtistSlideshow.%d.SimilarName" % ( count + 1 ), item[0])
          self._set_property("ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ), item[1])
      for count, item in enumerate( self.albums ):
          self._set_property("ArtistSlideshow.%d.AlbumName" % ( count + 1 ), item[0])
          self._set_property("ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ), item[1])


    def _clear_properties( self ):
        self.MBID = ''
        self._set_property( "ArtistSlideshow", self.InitDir )
        self._clean_dir( self.MergeDir )
        self._clean_dir( self.TransitionDir )
        self._set_property( "ArtistSlideshow.ArtistBiography" )
        for count in range( 50 ):
            self._set_property( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ) )

    #sets a property (or clears it if no value is supplied)
    #does not crash if e.g. the window no longer exists.
    def _set_property( self, property_name, value=""):
      try:
        self.WINDOW.setProperty(property_name, value)
      except Exception, e:
        log(" *************** Exception: Couldn't set propery " + property_name + " value " + value)
        log( e )


if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    slideshow = Main()
    try:
        slideshow._set_property("ArtistSlideshow.CleanupComplete", "True")
    except Exception, e:
        log( 'unexpected error while setting property.' )
        log( e )

log('script stopped')