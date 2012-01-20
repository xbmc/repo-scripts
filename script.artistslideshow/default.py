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

import urllib, re, os, sys, time, unicodedata, socket
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from elementtree import ElementTree as xmltree

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

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
    message = 'script.artistslideshow: %s' % txt
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
        
def download(src, dst):
    if (not xbmc.abortRequested):
        tmpname = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % ( __addonname__ , xbmc.getCacheThumbName(src) ))
        if xbmcvfs.exists(tmpname):
            xbmcvfs.delete(tmpname)
        urllib.urlretrieve(src, tmpname)
        if os.path.getsize(tmpname) > 999:
            xbmcvfs.rename(tmpname, dst)
        else:
            xbmcvfs.delete(tmpname)

class Main:
    def __init__( self ):
        self._parse_argv()
        self._get_settings()
        self._init_vars()
        self._make_dirs()
        if xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
            log('script already running')
        else:
            self.WINDOW.setProperty("ArtistSlideshowRunning", "True")
            if xbmc.Player().isPlayingAudio() == False:
                log('no music playing')
                if self.DAEMON == "False":
                    self.WINDOW.clearProperty("ArtistSlideshowRunning")
            else:
                log('first song started')
                time.sleep(0.2) # it may take some time for xbmc to read tag info after playback started
                self._start_download()
            while (not xbmc.abortRequested):
                time.sleep(0.5)
                if xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
                    if xbmc.Player().isPlayingAudio() == True:
                        currentname = xbmc.Player().getMusicInfoTag().getArtist()
                        if self.NAME != currentname:
                            log('new artist playing, start download')
                            self._clear_properties()
                            self._start_download()
                        elif not self.DownloadedAllImages:
                            log('same artist playing, continue download')
                            self._start_download()
                    else:
                        time.sleep(1) # doublecheck if playback really stopped
                        if xbmc.Player().isPlayingAudio() == False:
                            if self.DAEMON == "False":
                                self.WINDOW.clearProperty("ArtistSlideshowRunning")
                else:
                    self._clear_properties()
                    break

      
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        self.DAEMON = params.get( "daemon", "False" )
        if self.DAEMON == "True":
            log('daemonizing')


    def _get_settings( self ):
        try:
            self.minwidth = int(__addon__.getSetting( "minwidth" ))
        except:
            self.minwidth = 0
        try:
            self.minheight = int(__addon__.getSetting( "minheight" ))
        except:
            self.minheight = 0
        self.LASTFM = __addon__.getSetting( "lastfm" )
        self.HTBACKDROPS = __addon__.getSetting( "htbackdrops" )
        self.ARTISTINFO = __addon__.getSetting( "artistinfo" )
        self.LANGUAGE = __addon__.getSetting( "language" )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                log('language = %s' % self.LANGUAGE)
                break

    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( 12006 )
        self.NAME = ''
        LastfmApiKey = 'fbd57a1baddb983d1848a939665310f6'
        HtbackdropsApiKey = '96d681ea0dcb07ad9d27a347e64b652a'
        self.LastfmURL = 'http://ws.audioscrobbler.com/2.0/?autocorrect=1&api_key=' + LastfmApiKey
        self.HtbackdropsQueryURL = 'http://htbackdrops.com/api/' + HtbackdropsApiKey + '/searchXML?default_operator=and&fields=title&aid=1'
        self.HtbackdropsDownloadURL = 'http://htbackdrops.com/api/' + HtbackdropsApiKey + '/download/'


    def _make_dirs( self ):
        checkDir(xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/temp' % __addonname__ ))
        checkDir(xbmc.translatePath('special://profile/addon_data/%s/ArtistSlideshow' % __addonname__ ))
        

    def _start_download( self ):
        self.CachedImagesFound = False
        self.DownloadedFirstImage = False
        self.DownloadedAllImages = False
        self.ImageDownloaded = False
        self.NAME = xbmc.Player().getMusicInfoTag().getArtist()
        if len(self.NAME) == 0:
            log('no artist name provided')
            return
        CacheName = xbmc.getCacheThumbName(self.NAME).replace('.tbn', '')
        self.CacheDir = xbmc.translatePath('special://profile/addon_data/%s/ArtistSlideshow/%s/' % ( __addonname__ , CacheName, ))
        checkDir(self.CacheDir)
        log('cachedir = %s' % self.CacheDir)
        files = os.listdir(self.CacheDir)
        for file in files:
            if file.endswith('tbn'):
                self.CachedImagesFound = True

        if self.CachedImagesFound:
            log('cached images found')
            self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
            if self.ARTISTINFO == "true":
                self._get_artistinfo()

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
            if xbmc.Player().isPlayingAudio() == True:
                currentname = xbmc.Player().getMusicInfoTag().getArtist()
                if self.NAME != currentname:
                    return
            else:
                return

            path = getCacheThumbName(url, self.CacheDir)
            if not xbmcvfs.exists(path):
                download(url, path)
                log('downloaded %s to %s' % (url, path) )
                self.ImageDownloaded=True
            if self.ImageDownloaded:
                if not self.DownloadedFirstImage:
                    log('downloaded first image')
                    self.DownloadedFirstImage = True
                    if not self.CachedImagesFound:
                        self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
                        if self.ARTISTINFO == "true":
                            self._get_artistinfo()

        if self.ImageDownloaded:
            log('finished downloading images')
            self.DownloadedAllImages = True
            self.WINDOW.setProperty("ArtistSlideshowRefresh", "True")
            time.sleep(0.3)
            self.WINDOW.clearProperty("ArtistSlideshow")
            time.sleep(1)
            self.WINDOW.setProperty("ArtistSlideshow", self.CacheDir)
            self.WINDOW.clearProperty("ArtistSlideshowRefresh")

        if not self.ImageDownloaded:
            log('no images downloaded')
            self.DownloadedAllImages = True
            if not self.CachedImagesFound:
                self.WINDOW.clearProperty("ArtistSlideshow")
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()


    def _get_images( self, site ):
        if site == "lastfm":
            self.info = 'artist.getImages'
            self.url = self.LastfmURL + '&method=artist.getImages&artist=' + self.NAME.replace('&','%26').replace(' ','+')
        elif site == "htbackdrops":
            self.url = self.HtbackdropsQueryURL + '&keywords=' + self.NAME.replace('&','%26').replace(' ','+') + '&dmin_w=' + str( self.minwidth ) + '&dmin_h=' + str( self.minheight )
        images = self._get_data(site, 'images')
        return images


    def _get_artistinfo( self ):
        site = "lastfm"
        self.url = self.LastfmURL + '&method=artist.getInfo&artist=' + self.NAME.replace('&','%26').replace(' ','+') + '&lang=' + self.LANGUAGE
        bio = self._get_data(site, 'bio')
        if bio == []:
            self.biography = ''
        else:
            self.biography = cleanText(bio[0])
        self.url = self.LastfmURL + '&method=artist.getSimilar&artist=' + self.NAME.replace('&','%26').replace(' ','+')
        self.similar = self._get_data(site, 'similar')
        self.url = self.LastfmURL + '&method=artist.getTopAlbums&artist=' + self.NAME.replace('&','%26').replace(' ','+')
        self.albums = self._get_data(site, 'albums')
        self._set_properties()


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
        elif ForceUpdate:
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
        if not xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
            self.WINDOW.clearProperty("ArtistSlideshow")
            self.WINDOW.clearProperty("ArtistSlideshowRefresh")
        self.WINDOW.clearProperty( "ArtistSlideshow.ArtistBiography" )
        for count in range( 50 ):
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.SimilarName" % ( count ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.SimilarThumb" % ( count ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.AlbumName" % ( count ) )
            self.WINDOW.clearProperty( "ArtistSlideshow.%d.AlbumThumb" % ( count ) )


if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()
log('script stopped')
