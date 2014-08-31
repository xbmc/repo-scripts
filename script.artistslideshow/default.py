# *  Credits:
# *
# *  original Artist Slideshow code by ronie
# *  updates and additions since v1.3.0 by pkscout
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
import itertools, os, random, re, sys, time
import xml.etree.ElementTree as _xmltree
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json
from resources.dicttoxml.dicttoxml import dicttoxml
from resources.common.fix_utf8 import smartUTF8
from resources.common.fileops import checkPath, writeFile, readFile, deleteFile
from resources.common.url import URL
from resources.common.transforms import getImageType, itemHash, itemHashwithPath
from resources.common.xlogger import Logger

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path').decode('utf-8')
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ )
__language__     = __addon__.getLocalizedString
__preamble__     = '[Artist Slideshow]'
__logdebug__     = __addon__.getSetting( "logging" ) 

lw      = Logger( preamble=__preamble__, logdebug=__logdebug__ )
mbURL   = URL( 'json',{"User-Agent": __addonname__  + '/' + __addonversion__  + '( https://github.com/pkscout/artistslideshow )', "content-type":"text/html; charset=UTF-8"} )
JSONURL = URL( 'json' )
txtURL  = URL( 'text' )
imgURL  = URL( 'binary' )

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


class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_window()
        if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
            lw.log( ['script already running'] )
        else:
            self._get_settings()
            self._init_vars()
            self._make_dirs()
            self._upgrade()
            self.LastCacheTrim = 0
            self._set_property("ArtistSlideshowRunning", "True")
            if( xbmc.Player().isPlayingAudio() == False and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                lw.log( ['no music playing'] )
                if( self.DAEMON == "False" ):
                    self._set_property("ArtistSlideshowRunning")
            else:
                lw.log( ['first song started'] )
                time.sleep(1) # it may take some time for xbmc to read tag info after playback started
                self._use_correct_artwork()
                self._trim_cache()
            while (not xbmc.abortRequested):
                time.sleep(1)
                if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
                    if( xbmc.Player().isPlayingAudio() == True or self._get_infolabel( self.EXTERNALCALL ) != '' ):
                        if set( self.ALLARTISTS ) <> set( self._get_current_artists() ):
                            self._clear_properties()
                            self.UsingFallback = False
                            self._use_correct_artwork()
                            self._trim_cache()
                        elif(not (self.DownloadedAllImages or self.UsingFallback)):
                            if(not (self.LocalImagesFound and self.PRIORITY == '1')):
                                lw.log( ['same artist playing, continue download'] )
                                self._use_correct_artwork()
                    else:
                        time.sleep(2) # doublecheck if playback really stopped
                        if( xbmc.Player().isPlayingAudio() == False and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                            if ( self.DAEMON == "False" ):
                                self._set_property( "ArtistSlideshowRunning" )
                else:
                    self._clear_properties()
                    break
            try:
                slideshow._set_property("ArtistSlideshow.CleanupComplete", "True")
            except Exception, e:
                lw.log( ['unexpected error while setting property.', e] )


    def _clean_dir( self, dir_path ):
        try:
            dirs, old_files = xbmcvfs.listdir( dir_path )
        except Exception, e:
            lw.log( ['unexpected error while getting directory list', e] )
            old_files = []
        for old_file in old_files:
            if not old_file.endswith( '.nfo' ):
                success, loglines = deleteFile( os.path.join(dir_path, old_file) )


    def _clean_text( self, text ):
        text = re.sub('<a [^>]*>|</a>|<span[^>]*>|</span>','',text)
        text = re.sub('&quot;','"',text)
        text = re.sub('&amp;','&',text)
        text = re.sub('&gt;','>',text)
        text = re.sub('&lt;','<',text)
        text = re.sub('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.','',text)
        text = re.sub('Read more about .* on Last.fm.','',text)
        return text.strip()

    
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


    def _download( self, src, dst, dst2 ):
        if (not xbmc.abortRequested):
            tmpname = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % ( __addonname__ , xbmc.getCacheThumbName(src) ))
            lw.log( ['the tmpname is ' + tmpname] )
            if not self._excluded( dst ):
                if xbmcvfs.exists(tmpname):
                    success, loglines = deleteFile( tmpname )
                    lw.log( loglines )
                success, loglines, urldata = imgURL.Get( src, params=self.params )
                lw.log( loglines )
                if success:
                    success, loglines = writeFile( urldata, tmpname )
                    lw.log( loglines )
                if not success:
                    return False
                if os.path.getsize( tmpname ) > 999:
                    image_ext = getImageType( tmpname )
                    if not xbmcvfs.exists ( dst + image_ext ):
                        lw.log( ['copying %s to %s' % (tmpname, dst2 + image_ext)] )
                        xbmcvfs.copy( tmpname, dst2 + image_ext )
                        lw.log( ['moving %s to %s' % (tmpname, dst + image_ext)] )
                        xbmcvfs.rename( tmpname, dst + image_ext )
                        return True
                    else:
                        lw.log( ['image already exists, deleting temporary file'] )
                        success, loglines = deleteFile( tmpname )
                        lw.log( loglines )
                        return False
                else:
                    success, loglines = deleteFile( tmpname )
                    lw.log( loglines )
                    return False
            else:
                return False 
    

    def _excluded( self, item ):
        path, filename = os.path.split( item )
        exclusion_file = os.path.join( path, '_exclusions.nfo' )
        if xbmcvfs.exists( exclusion_file ):
            loglines, exclusions = readFile( exclusion_file )
            loglines.append( 'checking %s against %s' % (filename, exclusions) )
            lw.log( loglines )
            if filename in exclusions:
                lw.log( ['exclusion found'] )
                return True
            else:
                return False
        else:
            success, loglines = writeFile( '', exclusion_file )
            lw.log( loglines )
            return False

    
    def _get_artistinfo( self ):
        lw.log( ['checking for local artist bio data'] )
        bio = self._get_local_data( 'bio' )
        if bio == []:
            if self.MBID:
                self.url = self.theaudiodbARTISTURL
                self.params['i'] = self.MBID
                lw.log( ['trying to get artist bio from ' + self.url] )
                bio = self._get_data( 'theaudiodb', 'bio' )
        if bio == []:
            self.url = self.LastfmURL
            additionalparams = {'lang':self.LANGUAGE, 'method':'artist.getInfo', 'artist':self.NAME}  
            self.params = dict( self.LastfmPARAMS.items() + additionalparams.items() )
            lw.log( ['trying to get artist bio from ' + self.url] )
            bio = self._get_data('lastfm', 'bio')
        if bio == []:
            self.biography = ''
        else:
            self.biography = self._clean_text(bio[0])
        self.albums = self._get_local_data( 'albums' )
        if self.albums == []:
            loglines, theaudiodb_id = readFile( os.path.join(self.InfoDir, 'theaudiodbid.nfo') )
            lw.log( loglines )
            if theaudiodb_id:
                self.url = self.theaudiodbALBUMURL
                self.params['i'] = theaudiodb_id
                lw.log( ['trying to get artist albumns from ' + self.url] )
                self.albums = self._get_data('theaudiodb', 'albums')
        if self.albums == []:
            self.url = self.LastfmURL
            additionalparams = {'method':'artist.getTopAlbums', 'artist':self.NAME} 
            self.params = dict( self.LastfmPARAMS.items() + additionalparams.items() )
            lw.log( ['trying to get artist albums from ' + self.url] )
            self.albums = self._get_data('lastfm', 'albums')
        self.similar = self._get_local_data( 'similar' )
        if self.similar == []:
            self.url = self.LastfmURL
            additionalparams = {'method':'artist.getSimilar', 'artist':self.NAME} 
            self.params = dict( self.LastfmPARAMS.items() + additionalparams.items() )
            self.similar = self._get_data('lastfm', 'similar')
        self._set_properties()


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
                playing_file = xbmc.Player().getPlayingFile() + ' - ' + xbmc.Player().getMusicInfoTag().getArtist() + ' - ' + xbmc.Player().getMusicInfoTag().getTitle()
                lw.log( ['playing file is ' + playing_file] )
            except RuntimeError:
                return artists_info
            except Exception, e:
                lw.log( ['unexpected error getting playing file back from XBMC', e] )
                return artists_info
            if playing_file != self.LASTPLAYINGFILE:
                # if the same file is playing, use cached JSON response instead of doing a new query
                response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "musicbrainzartistid"]},"id":1}' )
                self.LASTPLAYINGFILE = playing_file
                self.LASTJSONRESPONSE = response
            else:
                response = self.LASTJSONRESPONSE
            try:
                artist_names = _json.loads(response)['result']['item']['artist']
            except (IndexError, KeyError, ValueError):
                artist_names = []
            except Exception, e:
                lw.log( ['unexpected error getting JSON back from XBMC', e] )
                artist_names = []
            try:
                mbids = _json.loads(response)['result']['item']['muiscbrainzartistid']
            except (IndexError, KeyError, ValueError):
                mbids = []
            except Exception, e:
                lw.log( ['unexpected error getting JSON back from XBMC', e] )
                mbids = []
            try:
                playing_song = xbmc.Player().getMusicInfoTag().getTitle()
            except RuntimeError:
                playing_song = ''
            except Exception, e:
                lw.log( ['unexpected error gettting playing song back from XBMC', e] )
                playing_song = ''
            if not artist_names:
                lw.log( ['No artist names returned from JSON call, assuming this is an internet stream'] )
                try:
                    playingartist = playing_song[0:(playing_song.find('-'))-1]
                except RuntimeError:
                    playingartist = ''
                    playing_song = ''
                except Exception, e:
                    lw.log( ['unexpected error gettting playing song back from XBMC', e] )
                    playingartist = ''
                    playing_song = ''
                artist_names = self._split_artists( playingartist )
            featured_artists = self._get_featured_artists( playing_song )
        elif self._get_infolabel( self.SKININFO['artist'] ):
            artist_names = self._split_artists( self._get_infolabel(self.SKININFO['artist']) )
            mbids = self._get_infolabel( self.SKININFO['mbid'] ).split( ',' )
            featured_artists = self._get_featured_artists( self._get_infolabel(self.SKININFO['title']) )
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
                lw.log( ['cached artist %s info found' % item] )
                ForceUpdate = False
            else:
                lw.log( ['outdated cached info found for %s ' % item] )
        if ForceUpdate:
            lw.log( ['downloading artist %s info from %s' % (item, site)] )
            if site == 'fanarttv' or site == 'theaudiodb':
                #converts the JSON response to XML
                success, loglines, json_data = JSONURL.Get( self.url, params=self.params )
                self.params = {}
                lw.log( loglines )
                if success:
                    if site == 'fanarttv':
                        try:
                            images = json_data['artistbackground']
                        except Exception, e:
                            lw.log( ['error getting artist backgrounds from fanart.tv', e] )
                            images = []
                        if self.FANARTTVALLIMAGES == 'true':
                            try:
                                thumbs = json_data['artistthumb']
                            except Exception, e:
                                lw.log( ['error getting artist thumbs from fanart.tv', e] )
                                thumbs = []
                            images = images + thumbs
                    else:
                        images = json_data
                    success, loglines = writeFile( dicttoxml( images ).encode('utf-8'), filename )
                    lw.log( loglines )
                    json_data = ''
                else:
                    return data
            else:
                success, loglines, urldata = txtURL.Get( self.url, params=self.params )
                self.params = {}
                lw.log( loglines )
                if success:
                    success, loglines = writeFile( urldata, filename )
                    lw.log( loglines )
                if not success:
                    return data
        try:
            xmldata = _xmltree.parse(filename).getroot()
        except Exception, e:
            lw.log( ['invalid or missing xml file', e] )
            deleteFile( filename )
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
                        success, loglines = writeFile( element.text, id_filename )
                        lw.log( loglines )
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
                        success, loglines = writeFile( element.text, id_filename )
                        lw.log( loglines )
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
            lw.log( ['no %s found on %s' % (item, site)] )
        return data


    def _get_featured_artists( self, data ):
        the_split = data.replace('ft.','feat.').split('feat.')
        if len( the_split ) > 1:
            return self._split_artists( the_split[-1] )
        else:
            return []


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
                self.url = self.fanarttvURL + self.MBID
                self.params = self.fanarttvPARAMS
                lw.log( ['asking for images from: %s' %self.url] )
            else:
                return []
        elif site == 'theaudiodb':
            if self.MBID:
                self.url = self.theaudiodbARTISTURL
                self.params['i'] = self.MBID
                lw.log( ['asking for images from: %s' %self.url] )
            else:
                return []
        elif site == "htbackdrops":
            self.url = self.HtbackdropsQueryURL
            additionalparams = {'keywords':self.NAME.replace('&','%26')}
            self.params = dict( self.HtbackdropsPARAMS.items() + additionalparams.items() )
            lw.log( ['asking for images from: %s' %self.url] )
        images = self._get_data(site, 'images')
        return images


    def _get_infolabel( self, item ):
        try:
            infolabel = xbmc.getInfoLabel( item )
        except:
            lw.log( ['problem reading information from %s, returning blank' % item] )
            infolabel = ''
        return infolabel


    def _get_local_data( self, item ):
        data = []
        filenames = []
        local_path = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8'), 'override' )
        if item == "similar":
            filenames.append( os.path.join( local_path, 'artistsimilar.nfo' ) )
        elif item == "albums":
            filenames.append( os.path.join( local_path, 'artistsalbums.nfo' ) )
        elif item == "bio":
            filenames.append( os.path.join( local_path, 'artistbio.nfo' ) )
        found_xml = True
        for filename in filenames:
            lw.log( ['checking filename ' + filename] )
            try:
                xmldata = _xmltree.parse(filename).getroot()
            except Exception, e:
                lw.log( ['invalid or missing local xml file for %s' % item, e] )
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
            lw.log( ['no %s found in local xml file' % item] )
        return data


    def _get_local_images( self ):
        self.LocalImagesFound = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        self.CacheDir = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8'), self.FANARTFOLDER )
        lw.log( ['cachedir = %s' % self.CacheDir] )
        try:
            dirs, files = xbmcvfs.listdir(self.CacheDir)
        except OSError:
            files = []
        except Exception, e:
            lw.log( ['unexpected error getting directory list', e] )
            files = []
        for file in files:
            if file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png'):
                self.LocalImagesFound = True
        if self.LocalImagesFound:
            lw.log( ['local images found'] )
            if self.ARTISTNUM == 1:
            	self._set_artwork_skininfo( self.CacheDir )
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
            if self.TOTALARTISTS > 1:
               self._merge_images()


    def _get_musicbrainz_id ( self, theartist ):
        mbid = ''
        lw.log( ['Looking for a musicbrainz ID for artist ' + theartist, 'Looking for musicbrainz ID in the musicbrainz.nfo file'] )
        self._set_infodir( theartist )
        filename = os.path.join( self.InfoDir, 'musicbrainz.nfo' )
        if xbmcvfs.exists( filename ):
            loglines, mbid = readFile( filename )
            lw.log( loglines )
            if not mbid:
                if time.time() - os.path.getmtime(filename) < 1209600:
                    lw.log( ['no musicbrainz ID found in musicbrainz.nfo file'] )
                    return ''
                else:
                    lw.log( ['no musicbrainz ID found in musicbrainz.nfo file, trying lookup again'] )
            else:
                lw.log( ['musicbrainz ID found in musicbrainz.nfo file'] )
                return mbid
        else:
            lw.log( ['no musicbrainz.nfo file found'] )
        if self._playback_stopped_or_changed():
            success, loglines = writeFile( '', filename )
            lw.log( loglines )
            return ''
        # this is here to account for songs or albums that have the artist 'Various Artists'
        # because AS chokes when trying to find this artist on MusicBrainz
        if theartist.lower() == 'various artists':
            success, loglines = writeFile( self.VARIOUSARTISTSMBID, filename)
            lw.log( loglines )
            return self.VARIOUSARTISTSMBID
        lw.log( ['querying musicbrainz.com for musicbrainz ID. This is about to get messy.'] )
        badSubstrings = ["the ", "The ", "THE ", "a ", "A ", "an ", "An ", "AN "]
        searchartist = theartist
        for badSubstring in badSubstrings:
            if theartist.startswith(badSubstring):
                searchartist = theartist.replace(badSubstring, "")
        mboptions = {"fmt":"json"} 
        mbsearch = 'artist:"%s"' % searchartist
        query_times = {'last':0, 'current':time.time()}
        lw.log( ['parsing musicbrainz response for muiscbrainz ID'] )
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
                lw.log( ['unexpected error getting JSON data from XBMC response', e] )
                all_names = []
            aliases = []
            if all_names:
                for one_name in all_names:
                    aliases.append( one_name['name'].lower() )
            if artist['name'].lower() == theartist.lower() or theartist.lower() in aliases:
                mbid = artist['id']
                lw.log( ['found a potential musicbrainz ID of %s for %s' % (mbid, theartist)] )
                playing_album = self._get_playing_item( 'album' )
                if playing_album:
                    lw.log( ['checking album name against releases in musicbrainz'] )
                    query_times = {'last':query_times['current'], 'current':time.time()}
                    cached_mb_info = self._parse_musicbrainz_info( 'release', mbid, playing_album, query_times )
                if not cached_mb_info:
                    playing_song = self._get_playing_item( 'title' )
                    if playing_song:
                        lw.log( ['checking song name against recordings in musicbrainz'] )
                        if smartUTF8( theartist ) == playing_song[0:(playing_song.find('-'))-1]:
                            playing_song = playing_song[(playing_song.find('-'))+2:]
                        query_times = {'last':query_times['current'], 'current':time.time()}
                        cached_mb_info = self._parse_musicbrainz_info( 'recording', mbid, playing_song, query_times )
                        if not cached_mb_info:
                            lw.log( ['checking song name against works in musicbrainz'] )
                            query_times = {'last':query_times['current'], 'current':time.time()}
                            cached_mb_info = self._parse_musicbrainz_info( 'work', mbid, playing_song, query_times )
                if cached_mb_info:
                    break
                else:
                    lw.log( ['No matching song/album found for %s. Trying the next artist.' % theartist] )
        if cached_mb_info:
            lw.log( ['Musicbrainz ID for %s is %s. writing out to cache file.' % (theartist, mbid)] )
        else:
            mbid = ''
            lw.log( ['No musicbrainz ID found for %s. writing empty cache file.' % theartist] )
        success, loglines = writeFile( mbid, filename )
        lw.log( loglines )
        return mbid

                                
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
                mbquery = mbbase + type
#                mboptions['query'] = urllib.quote_plus( smartUTF8(mbsearch), ':!"' )
                mboptions['query'] = mbsearch
            else:
                mbquery = mbbase + type[:-1]
                mboptions['offset'] = str(offset)
            lw.log( ['getting results from musicbrainz using: ' + mbquery] )
            for x in range(1, 5):
                success, loglines, json_data = mbURL.Get( mbquery, params=mboptions )
                lw.log( loglines )
                if self._playback_stopped_or_changed():
                    return []       
                if not success:
                    wait_time = random.randint(2,5)
                    lw.log( ['site unreachable, waiting %s seconds to try again.' % wait_time] )
                    self._wait( wait_time )
                else:
                    try:
                        mb_data.extend( json_data[type] )
                    except KeyError:
                        lw.log( ['no valid value for %s found in JSON data' % type] )
                        offset = -100
                    except Exception, e:
                        lw.log( ['unexpected error while parsing JSON data', e] )
                        offset = -100
                    break
            offset = offset + 100
            try:
                total_items = int(json_data[type[:-1] + '-count'])
            except KeyError:
                total_items = 0
            except Exception, e:
                lw.log( ['unexpected error getting JSON data from ' + mbquery, e] )
                total_items = 0
            if (not mbsearch) and (total_items - offset > 0):
                lw.log( ['getting more data from musicbrainz'] )
                query_elapsed = time.time() - query_start
                if query_elapsed < 1:
                    self._wait(1 - query_elapsed)
                elif self._playback_stopped_or_changed():
                    return []        
            else:
                do_loop = False
        return mb_data


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
                lw.log( ['unexpected error getting %s from XBMC' % item, e] )
            if num_trys > max_trys:
                break
            else:
                num_trys = num_trys + 1
                self._wait(1)
                if self._playback_stopped_or_changed():
                    break
        #if nothing is playing, assume the information was passed by another add-on
        if not playing_item:
            playing_item = self._get_infolabel( self.SKININFO[item] )
        return playing_item


    def _get_settings( self ):
        self.FANARTTV = __addon__.getSetting( "fanarttv" )
        self.FANARTTVALLIMAGES = __addon__.getSetting( "fanarttv_all" )
        self.FANARTTVCLIENTAPIKEY = __addon__.getSetting( "fanarttv_clientapikey" )
        self.THEAUDIODB = __addon__.getSetting( "theaudiodb" )
        self.HTBACKDROPS = __addon__.getSetting( "htbackdrops" )
        self.HTBACKDROPSALLIMAGES = __addon__.getSetting( "htbackdrops_all" )
        self.ARTISTINFO = __addon__.getSetting( "artistinfo" )
        self.LANGUAGE = __addon__.getSetting( "language" )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                lw.log( ['language = %s' % self.LANGUAGE] )
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
            lw.log( ['unexpected error while parsing maxcachesize setting', e] )
            self.maxcachesize = 1024 * 1000000
        self.NOTIFICATIONTYPE = __addon__.getSetting( "show_progress" )
        if self.NOTIFICATIONTYPE == "2":
            self.PROGRESSPATH = __addon__.getSetting( "progress_path" ).decode('utf-8')
            lw.log( ['set progress path to %s' % self.PROGRESSPATH] )
        else:
            self.PROGRESSPATH = ''
        if __addon__.getSetting( "fanart_folder" ):
            self.FANARTFOLDER = __addon__.getSetting( "fanart_folder" ).decode('utf-8')
            lw.log( ['set fanart folder to %s' % self.FANARTFOLDER] )
        else:
            self.FANARTFOLDER = 'extrafanart'


    def _init_vars( self ):
        self.DATAROOT = xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode('utf-8')
        self.CHECKFILE = os.path.join( self.DATAROOT, 'migrationcheck.nfo' )
        self._set_property( "ArtistSlideshow.CleanupComplete" )
        self._set_property( "ArtistSlideshow.ArtworkReady" )
        self.SKININFO = {}
        for item in self.FIELDLIST:
            if self.PASSEDFIELDS[item]:
                self.SKININFO[item[0:-5]] = "Window(%s).Property(%s)" % ( self.WINDOWID, self.PASSEDFIELDS[item] )
            else:
                self.SKININFO[item[0:-5]] = ''
        self.EXTERNALCALLSTATUS = self._get_infolabel( self.EXTERNALCALL )
        lw.log( ['external call is set to ' + self._get_infolabel( self.EXTERNALCALL )] )
        if __addon__.getSetting( "transparent" ) == 'true':
            self._set_property("ArtistSlideshowTransparent", 'true')
            self.InitDir = xbmc.translatePath('%s/resources/transparent' % __addonpath__ ).decode('utf-8')
        else:
            self._set_property("ArtistSlideshowTransparent", '')
            self.InitDir = xbmc.translatePath('%s/resources/black' % __addonpath__ ).decode('utf-8')
        self._set_property("ArtistSlideshow", self.InitDir)
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
        LastfmApiKey = 'afe7e856e4f4089fc90f841980ea1ada'
        fanarttvApiKey = '7a93c84fe1c9999e6f0fec206a66b0f5'
        theaudiodbApiKey = '193621276b2d731671156g'
        HtbackdropsApiKey = '96d681ea0dcb07ad9d27a347e64b652a'
        self.params = {}
        self.LastfmURL = 'http://ws.audioscrobbler.com/2.0/'
        self.LastfmPARAMS = {'autocorrect':'1', 'api_key':LastfmApiKey}
        self.fanarttvURL = 'https://webservice.fanart.tv/v3/music/'
        self.fanarttvPARAMS = {'api_key': fanarttvApiKey}
        if self.FANARTTVCLIENTAPIKEY:
            self.fanarttvPARAMS.update( {'client_key': self.FANARTTVCLIENTAPIKEY} )
        theaudiodbURL = 'http://www.theaudiodb.com/api/v1/json/%s/' % theaudiodbApiKey
        self.theaudiodbARTISTURL = theaudiodbURL + 'artist-mb.php'
        self.theaudiodbALBUMURL = theaudiodbURL + 'album.php'
        self.HtbackdropsQueryURL = 'http://htbackdrops.org/api/%s/searchXML' % HtbackdropsApiKey
        self.HtbackdropsPARAMS = {'default_operator':'and', 'fields':'title'}
        if self.HTBACKDROPSALLIMAGES == 'true':
            self.HtbackdropsPARAMS.update( {'cid':'5'} )
        else:
            self.HtbackdropsPARAMS.update( {'aid':'1'} )
        self.HtbackdropsDownloadURL = 'http://htbackdrops.org/api/' + HtbackdropsApiKey + '/download/'


    def _init_window( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.ARTISTSLIDESHOW = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow" )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )


    def _make_dirs( self ):
        exists, loglines = checkPath( self.InitDir )
        lw.log( loglines )
        exists, loglines = checkPath( self.DATAROOT )
        lw.log( loglines )
        thedirs = ['temp', 'ArtistSlideshow', 'ArtistInformation', 'transition', 'merge']
        for onedir in thedirs:
            exists, loglines = checkPath( os.path.join( self.DATAROOT, onedir ) )
            lw.log( loglines )


    def _merge_images( self ):
        lw.log( ['merging files from primary directory %s into merge directory %s' % (self.CacheDir, self.MergeDir)] )
        self.MergedImagesFound = True
        dirs, files = xbmcvfs.listdir(self.CacheDir)
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
                lw.log( ['switching slideshow to merge directory'] )
                self._set_artwork_skininfo( self.MergeDir )


    def _migrate_info_files( self ):
        #this is a one time process to move and rename all the .nfo files to the new location
        new_loc = os.path.join( self.DATAROOT, 'ArtistInformation' )
        self._move_info_files( os.path.join(self.DATAROOT, 'ArtistSlideshow'), new_loc, 'cache' )
        if self.LOCALARTISTPATH:
            self._move_info_files( self.LOCALARTISTPATH, new_loc, 'local' )
        self._update_check_file( '1.5.4', 'migration of artist info files complete' )


    def _migrate_tbn_files( self ):
        #one time process to rename all the tbn files to the appropriate extensions based on image type
        self._rename_tbn_files( os.path.join( self.DATAROOT, 'ArtistSlideshow' ), 'cache' )
        if self.LOCALARTISTPATH:
            self._rename_tbn_files( self.LOCALARTISTPATH, 'local' )
        self._update_check_file( '1.6.0', 'renaming of tbn files compete' )


    def _move_info_files( self, old_loc, new_loc, type ):
        lw.log( ['attempting to move from %s to %s' % (old_loc, new_loc)] )
        try:
            folders, fls = xbmcvfs.listdir( old_loc )
        except OSError:
            lw.log( ['no directory found: ' + old_loc] )
            return
        except Exception, e:
            lw.log( ['unexpected error while getting directory list', e] )
            return
        for folder in folders:
            if type == 'cache':
                old_folder = os.path.join( old_loc, folder )
                new_folder = os.path.join( new_loc, folder )
            elif type == 'local':
                old_folder = os.path.join( old_loc, smartUTF8(folder).decode('utf-8'), self.FANARTFOLDER )
                new_folder = os.path.join( new_loc, itemHash(folder) )
            try:
                dirs, old_files = xbmcvfs.listdir( old_folder )
            except Exception, e:
                lw.log( ['unexpected error while getting directory list', e] )
                old_files = []
            exclude_path = os.path.join( old_folder, '_exclusions.nfo' )
            if old_files and type == 'cache' and not xbmcvfs.exists(exclude_path):
                success, loglines = writeFile( '', exclude_path )
                lw.log( loglines )
            for old_file in old_files:
                if old_file.endswith( '.nfo' ) and not old_file == '_exclusions.nfo':
                    exists, loglines = checkPath( new_folder )
                    lw.log( loglines )
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
                    lw.log( ['moving %s to %s' % (old_file, os.path.join(new_folder, new_file))] )


    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except IndexError:
            params = {}        
        except Exception, e:
            lw.log( ['unexpected error while parsing arguments', e] )
            params = {}
        self.WINDOWID = params.get( "windowid", "12006")
        lw.log( ['window id is set to %s' % self.WINDOWID] )
        self.PASSEDFIELDS = {}
        self.FIELDLIST = ['artistfield', 'titlefield', 'albumfield', 'mbidfield']
        for item in self.FIELDLIST:
            self.PASSEDFIELDS[item] = params.get( item, '' )
            lw.log( ['%s is set to %s' % (item, self.PASSEDFIELDS[item])] )
        self.DAEMON = params.get( "daemon", "False" )
        if self.DAEMON == "True":
            lw.log( ['daemonizing'] )


    def _parse_musicbrainz_info( self, type, mbid, playing_thing, query_times ):
        if self._playback_stopped_or_changed():
            return False
        lw.log( ["checking this artist's " + type + "s against currently playing " + type] )
#        mboptions = type + '?artist=' + mbid + '&limit=100&fmt=json'
        mboptions = {"artist":mbid, "limit":"100", "fmt":"json"}
        for thing in self._get_musicbrainz_info( mboptions, '', type + 's', query_times ):
            title = smartUTF8( thing['title'] )
            if playing_thing.rfind('(') > 0:
                playing_title = smartUTF8( playing_thing[:playing_thing.rfind('(')-2] )
            else:
                playing_title = smartUTF8( playing_thing )
            lw.log( ['comparing musicbrainz %s: %s with local %s: %s' % (type, title, type, playing_title)] )
            if title.lower().startswith( playing_title.lower() ) or playing_title.lower().startswith( title.lower() ):
                lw.log( ['found matching %s, this should be the right artist' % type] )
                return True
        return False


    def _playback_stopped_or_changed( self ):
        if set( self.ALLARTISTS ) <> set( self._get_current_artists() ) or self.EXTERNALCALLSTATUS != self._get_infolabel( self.EXTERNALCALL ):
            self._clear_properties()
            return True
        else:
            return False


    def _refresh_image_directory( self ):
        if( self._get_infolabel( self.ARTISTSLIDESHOW ).decode('utf-8') == self.TransitionDir):
            self._set_artwork_skininfo( self.CacheDir )
            lw.log( ['switching slideshow to ' + self.CacheDir] )
        else:
            self._set_artwork_skininfo( self.TransitionDir )
            lw.log( ['switching slideshow to ' + self.TransitionDir] )
        self.LASTARTISTREFRESH = time.time()
        lw.log( ['Last slideshow refresh time is ' + str(self.LASTARTISTREFRESH)] )


    def _rename_tbn_files( self, loc, type ):
        lw.log( ['attempting to rename .tbn files with correct extension', 'from location: ' + loc] )
        try:
            folders, fls = xbmcvfs.listdir( loc )
        except OSError:
            lw.log( ['no directory found: ' + loc] )
            return
        except Exception, e:
            lw.log( ['unexpected error while getting directory list', e] )
            return
        for folder in folders:
            lw.log( ['checking ' + folder] )
            if type == 'cache':
                thepath = os.path.join( loc, smartUTF8(folder).decode('utf-8') )
            elif type == 'local':
                thepath = os.path.join( loc, smartUTF8(folder).decode('utf-8'), self.FANARTFOLDER )
            try:
                dirs, files = xbmcvfs.listdir( thepath )
            except Exception, e:
                lw.log( ['unexpected error while getting file list', e] )
                files = []
            for file in files:
                if file.endswith( '.tbn' ):
                    old_path = os.path.join( thepath, file )
                    new_file = file.replace( '.tbn', getImageType( old_path ) )
                    new_path = os.path.join( thepath, new_file )
                    xbmcvfs.rename( old_path, new_path )
                    lw.log( ['renaming %s to %s' % (old_path, new_path)] )
        lw.log( ['finished renaming .tbn files with correct extension'] )
    

    def _set_artwork_skininfo( self, dir ):
        self._set_property("ArtistSlideshow", dir)
        self._set_property("ArtistSlideshow.ArtworkReady", "true")
    

    def _set_cachedir( self, theartist ):
        self.CacheDir = self._set_thedir( theartist, "ArtistSlideshow" )


    def _set_infodir( self, theartist ):
        self.InfoDir = self._set_thedir( theartist, "ArtistInformation" )


    def _set_properties( self ):
      self._set_property("ArtistSlideshow.ArtistBiography", self.biography)
      for count, item in enumerate( self.similar ):
          self._set_property("ArtistSlideshow.%d.SimilarName" % ( count + 1 ), item[0])
          self._set_property("ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ), item[1])
      for count, item in enumerate( self.albums ):
          self._set_property("ArtistSlideshow.%d.AlbumName" % ( count + 1 ), item[0])
          self._set_property("ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ), item[1])


    def _set_property( self, property_name, value=""):
        #sets a property (or clears it if no value is supplied)
        #does not crash if e.g. the window no longer exists.
        try:
          self.WINDOW.setProperty(property_name, value)
          lw.log( ['%s set to %s' % (property_name, value)] )
        except Exception, e:
          lw.log( ["Exception: Couldn't set propery " + property_name + " value " + value , e])


    def _set_thedir(self, theartist, dirtype):
        CacheName = itemHash(theartist)
        thedir = xbmc.translatePath('special://profile/addon_data/%s/%s/%s/' % ( __addonname__ , dirtype, CacheName, )).decode('utf-8')
        exists, loglines = checkPath( thedir )
        lw.log( loglines )
        return thedir


    def _split_artists( self, response):
        return response.replace('ft.',' / ').replace('feat.',' / ').split(' / ')


    def _start_download( self ):
        self.CachedImagesFound = False
        self.DownloadedFirstImage = False
        self.DownloadedAllImages = False
        self.ImageDownloaded = False
        self.FirstImage = True
        cached_image_info = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        if self.PRIORITY == '2' and self.LocalImagesFound:
            pass
            #self.CacheDir was successfully set in _get_local_images
        else:
            self._set_cachedir( self.NAME )
        lw.log( ['cachedir = %s' % self.CacheDir] )

        dirs, files = xbmcvfs.listdir(self.CacheDir)
        for file in files:
            if (file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')) or (self.PRIORITY == '2' and self.LocalImagesFound):
                self.CachedImagesFound = True

        if self.CachedImagesFound:
            lw.log( ['cached images found'] )
            cached_image_info = True
            self.LASTARTISTREFRESH = time.time()
            if self.ARTISTNUM == 1:
                self._set_artwork_skininfo( self.CacheDir )
                if self.ARTISTINFO == "true":
                    self._get_artistinfo()
        else:
            self.LASTARTISTREFRESH = 0
            if self.ARTISTNUM == 1:
                for cache_file in ['fanarttvartistimages.nfo', 'theaudiodbartistbio.nfo', 'htbackdropsartistimages.nfo']:
                    filename = os.path.join( self.InfoDir, cache_file.decode('utf-8') )
                    if xbmcvfs.exists( filename ):
                        if time.time() - os.path.getmtime(filename) < 1209600:
                            lw.log( ['cached %s found' % filename] )
                            cached_image_info = True
                        else:
                           lw.log( ['outdated %s found' % filename] )
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
            lw.log( ['checking the source %s with a value of %s.' % (source[0], source[1])] )
            if source[1] == "true":
                imagelist.extend( self._get_images(source[0]) )
        lw.log( ['downloading images'] )
        folders, cachelist = xbmcvfs.listdir( self.CacheDir )
        cachelist_str = ''.join(str(e) for e in cachelist)
        for url in imagelist:
            if( self._playback_stopped_or_changed() ):
                return
            path = itemHashwithPath( url, self.CacheDir )
            path2 = itemHashwithPath( url, self.TransitionDir )
            checkpath, checkfilename = os.path.split( path )
            if not (checkfilename in cachelist_str):
                if self._download(url, path, path2):
                    lw.log( ['downloaded %s to %s' % (url, path)]  )
                    self.ImageDownloaded = True
            elif self._excluded( path ):
                indicies = [i for i, elem in enumerate(cachelist) if checkfilename in elem]
                success, loglines = deleteFile( os.path.join( checkpath, cachelist[indicies[0]] ) )
                lw.log( loglines )
            if self.ImageDownloaded:
                if( self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                    self._set_artwork_skininfo( self.CacheDir )
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
            lw.log( ['finished downloading images'] )
            self.DownloadedAllImages = True
            if( self._playback_stopped_or_changed() ):
                self._set_artwork_skininfo( self.CacheDir )
                self.LASTARTISTREFRESH = time.time()
                self._clean_dir( self.TransitionDir )
                return
            lw.log( ['cleaning up from refreshing slideshow'] )
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
            if( self._get_infolabel( self.ARTISTSLIDESHOW ).decode('utf-8') == self.TransitionDir and self.ARTISTNUM == 1):
                self._wait( self.MINREFRESH )
                if( not self._playback_stopped_or_changed() ):
                    self._refresh_image_directory()
            self._clean_dir( self.TransitionDir )
        if not self.ImageDownloaded:
            lw.log( ['no images downloaded'] )
            self.DownloadedAllImages = True
            if not self.CachedImagesFound:
                if self.ARTISTNUM == 1:
                    lw.log( ['setting slideshow directory to blank directory'] )
                    self._set_property("ArtistSlideshow", self.InitDir)
                    if self.NOTIFICATIONTYPE == "1" and not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30302)), smartUTF8(__language__(30303)), 10000, smartUTF8(__addonicon__))
                        xbmc.executebuiltin(command)
                    if( self.ARTISTINFO == "true" and not self._playback_stopped_or_changed() ):
                        self._get_artistinfo()
            elif self.TOTALARTISTS > 1:
                self._merge_images()


    def _trim_cache( self ):
        if( self.RESTRICTCACHE == 'true' and not self.PRIORITY == '2' ):
            now = time.time()
            cache_trim_delay = 0   #delay time is in seconds
            if( now - self.LastCacheTrim > cache_trim_delay ):
                lw.log( ['trimming the cache down to %s bytes' % self.maxcachesize]  )
                cache_root = xbmc.translatePath( 'special://profile/addon_data/%s/ArtistSlideshow/' % __addonname__ ).decode('utf-8')
                folders, fls = xbmcvfs.listdir( cache_root )
                folders.sort( key=lambda x: os.path.getmtime( os.path.join ( cache_root, x ) ), reverse=True )
                cache_size = 0
                first_folder = True
                for folder in folders:
                    if( self._playback_stopped_or_changed() ):
                        break
                    cache_size = cache_size + self._get_folder_size( os.path.join (cache_root, folder ) )
                    lw.log( ['looking at folder %s cache size is now %s' % (folder, cache_size)] )
                    if( cache_size > self.maxcachesize and not first_folder ):
                        self._clean_dir( os.path.join(cache_root, folder) )
                        lw.log( ['deleted files in folder %s' % folder] )
                    first_folder = False
                self.LastCacheTrim = now


    def _use_correct_artwork( self ):
        self.ALLARTISTS = self._get_current_artists()
        self.ARTISTNUM = 0
        self.TOTALARTISTS = len( self.ALLARTISTS )
        self.MergedImagesFound = False
        for artist, mbid in self._get_current_artists_info( 'withmbid' ):
            lw.log( ['current artist is %s with a mbid of %s' % (artist, mbid)] )
            self.ARTISTNUM += 1
            self.NAME = artist
            self.MBID = mbid
            self._set_infodir( self.NAME )
            if self.USEOVERRIDE == 'true':
                lw.log( ['using override directory for images'] )
                self._set_property("ArtistSlideshow", self.OVERRIDEPATH)
                self._set_artwork_skininfo( self.OVERRIDEPATH )
                if(self.ARTISTNUM == 1):
                    self._get_artistinfo()
            elif self.PRIORITY == '1' and self.LOCALARTISTPATH:
                lw.log( ['looking for local artwork'] )
                self._get_local_images()
                if not self.LocalImagesFound:
                    lw.log( ['no local artist artwork found, start download'] )
                    self._start_download()
            elif self.PRIORITY == '2' and self.LOCALARTISTPATH:
                lw.log( ['looking for local artwork'] )
                self._get_local_images()
                lw.log( ['start download'] )
                self._start_download()
            else:
                lw.log( ['start download'] )
                self._start_download()
                if not (self.CachedImagesFound or self.ImageDownloaded):
                    lw.log( ['no remote artist artwork found, looking for local artwork'] )
                    self._get_local_images()
        if not (self.LocalImagesFound or self.CachedImagesFound or self.ImageDownloaded or self.MergedImagesFound):
            if (self.USEFALLBACK == 'true'):
                lw.log( ['no images found for artist, using fallback slideshow'] )
                lw.log( ['fallbackdir = ' + self.FALLBACKPATH] )
                self.UsingFallback = True
                self._set_property("ArtistSlideshow", self.FALLBACKPATH)
                self._set_artwork_skininfo( self.FALLBACKPATH )


    def _update_check_file( self, version, message ):
        success, loglines = writeFile( version, self.CHECKFILE )
        lw.log( loglines )
        if success:
            lw.log( [message] )


    def _upgrade( self ):
        #this is where any code goes for one time upgrade routines
        loglines, data = readFile( self.CHECKFILE )
        lw.log( loglines )
        if not data:
            self._migrate_info_files()
        loglines, data = readFile( self.CHECKFILE )
        if data == '1.5.4':
            self._migrate_tbn_files()


    def _wait( self, wait_time ):
        waited = 0
        while( waited < wait_time ):
            time.sleep(0.1)
            waited = waited + 0.1
            if self._playback_stopped_or_changed():
                self._set_property( "ArtistSlideshow", self.InitDir )
                self._set_property( "ArtistSlideshow.ArtworkReady" )
                self.Abort = True
                return


if ( __name__ == "__main__" ):
    lw.log( ['script version %s started' % __addonversion__], xbmc.LOGNOTICE )
    lw.log( ['debug logging set to %s' % __logdebug__], xbmc.LOGNOTICE )
    slideshow = Main()
lw.log( ['script stopped'], xbmc.LOGNOTICE )
