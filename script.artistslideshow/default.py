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
from resources.common.fix_utf8 import smartUTF8
from resources.common.fileops import checkPath, writeFile, readFile, deleteFile
from resources.common.url import URL
from resources.common.transforms import getImageType, itemHash, itemHashwithPath
from resources.common.xlogger import Logger
import resources.plugins

addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo('id')
addonversion = addon.getAddonInfo('version')
addonpath    = addon.getAddonInfo('path').decode('utf-8')
addonicon    = xbmc.translatePath('%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[Artist Slideshow]'
logdebug     = addon.getSetting( "logging" ) 

lw      = Logger( preamble=preamble, logdebug=logdebug )
JSONURL = URL( 'json' )
txtURL  = URL( 'text' )
imgURL  = URL( 'binary' )

# this section imports all the scraper plugins, initializes, and sorts them
def _get_plugin_settings( preamble, module, description ):
    if module == 'local':
        return 'true', 0
    try:
        active = addon.getSetting( preamble + module )
    except ValueError:
        active = 'false'
    except Exception, e:
        lw.log( ['unexpected error while parsing %s setting for %s' % (description, module), e] )
        active = 'false'        
    if active == 'true':
        try:
            priority = int( addon.getSetting( preamble + "priority_" + module ) )
        except ValueError:
            priority = 10
        except Exception, e:
            lw.log( ['unexpected error while parsing %s priority for %s' % (description, module), e] )
            priority = 10
    else:
        priority = 10
    return active, priority

bio_plugins = {'names':[], 'objs':{}}
image_plugins = {'names':[], 'objs':{}}
album_plugins = {'names':[], 'objs':{}}
similar_plugins = {'names':[], 'objs':{}}
mbid_plugins = {'names':[], 'objs':{}} 
for module in resources.plugins.__all__:
    full_plugin = 'resources.plugins.' + module
    __import__( full_plugin )
    imp_plugin = sys.modules[ full_plugin ]
    lw.log( ['loaded plugin ' + module] )
    plugin = imp_plugin.objectConfig()
    scrapers = plugin.provides()
    if 'bio' in scrapers:
        bio_active, bio_priority = _get_plugin_settings( 'ab_', module, 'artist bio' )
        if bio_active == 'true':
            bio_plugins['objs'][module] = plugin
            bio_plugins['names'].append( [bio_priority, module] )
            lw.log( ['added %s to bio plugins' % module] )
    if 'images' in scrapers:
        img_active, img_priority = _get_plugin_settings( '', module, 'artist images' )
        if img_active == 'true':
            image_plugins['objs'][module] = plugin
            image_plugins['names'].append( [img_priority, module] )
            lw.log( ['added %s to image plugins' % module] )
    if 'albums' in scrapers:
        ai_active, ai_priority = _get_plugin_settings( 'ai_', module, 'artist albums' )
        if ai_active == 'true':
            album_plugins['objs'][module] = plugin
            album_plugins['names'].append( [ai_priority, module] )
            lw.log( ['added %s to album info plugins' % module] )
    if 'similar' in scrapers:
        sa_active, sa_priority = _get_plugin_settings( 'sa_', module, 'similar artists' )
        if sa_active == 'true':
            similar_plugins['objs'][module] = plugin
            similar_plugins['names'].append( [ai_priority, module] )
            lw.log( ['added %s to similar artist plugins' % module] )
    if 'mbid' in scrapers:
        mbid_plugins['objs'][module] = plugin
        mbid_plugins['names'].append( [1, module] )
        lw.log( ['added %s to mbid plugins' % module] )


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
                self._set_property("ArtistSlideshow.CleanupComplete", "True")
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
                success, loglines = deleteFile( os.path.join(dir_path, old_file.decode('utf-8')) )


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
            tmpname = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % ( addonname , xbmc.getCacheThumbName(src) ))
            lw.log( ['the tmpname is ' + tmpname] )
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
            if xbmcvfs.Stat( tmpname ).st_size() > 999:
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
    

    def _get_artistinfo( self ):
        bio = ''
        bio_params = {}
        bio_params['mbid'] = self.MBID
        bio_params['infodir'] = self.InfoDir
        bio_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8') )
        bio_params['lang'] = self.LANGUAGE
        bio_params['artist'] = self.NAME
        bio = ''
        try:
            bio_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in bio_plugins['names']:
            lw.log( ['checking %s for bio' % plugin_name[1]] )
            bio, loglines = bio_plugins['objs'][plugin_name[1]].getBio( bio_params )
            lw.log( loglines )
            if bio:
                lw.log( ['got a bio from %s, so stop looking' % plugin_name] )
                break
        if bio:
            self.biography = self._clean_text(bio)
        else:
            self.biography = ''
        album_params = {}
        album_params['infodir'] = self.InfoDir
        album_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8') )
        album_params['lang'] = self.LANGUAGE
        album_params['artist'] = self.NAME
        albums = []
        try:
            album_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in album_plugins['names']:
            lw.log( ['checking %s for album info' % plugin_name[1]] )
            albums, loglines = album_plugins['objs'][plugin_name[1]].getAlbumList( album_params )
            lw.log( loglines )
            if not albums == []:
                lw.log( ['got album list from %s, so stop looking' % plugin_name] )
                break
        if albums == []:
            self.albums = []
        else:
            self.albums = albums
        similar_params = {}
        similar_params['infodir'] = self.InfoDir
        similar_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8') )
        similar_params['lang'] = self.LANGUAGE
        similar_params['artist'] = self.NAME
        similar_artists = []
        try:
            similar_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in similar_plugins['names']:
            lw.log( ['checking %s for similar artist info' % plugin_name[1]] )
            similar_artists, loglines = similar_plugins['objs'][plugin_name[1]].getSimilarArtists( similar_params )
            lw.log( loglines )
            if not similar_artists == []:
                lw.log( ['got similar artist list from %s, so stop looking' % plugin_name] )
                break
        if  similar_artists == []:
            self.similar = []
        else:
            self.similar = similar_artists
        self._set_properties()


    def _get_current_artists( self ):
        current_artists = []
        for artist, mbid in self._get_current_artists_info( ):
            current_artists.append( artist )
        return current_artists


    def _get_current_artists_info( self ):
        featured_artists = ''
        artist_names = []
        artists_info = []
        mbids = []
        if( xbmc.Player().isPlayingAudio() == True ):
            try:
                playing_file = xbmc.Player().getPlayingFile() + ' - ' + xbmc.Player().getMusicInfoTag().getArtist() + ' - ' + xbmc.Player().getMusicInfoTag().getTitle()
            except RuntimeError:
                return artists_info
            except Exception, e:
                lw.log( ['unexpected error getting playing file back from XBMC', e] )
                return artists_info
            if playing_file != self.LASTPLAYINGFILE:
                # if the same file is playing, use cached JSON response instead of doing a new query
                response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "musicbrainzartistid"]},"id":1}' )
                self.LASTPLAYINGFILE = playing_file
            else:
                lw.log( ['same file playing, returning cached artists_info'] )
                return self.ARTISTS_INFO
            artist_names = _json.loads(response).get( 'result', {} ).get( 'item', {} ).get( 'artist', [] )
            mbids = _json.loads(response).get( 'result', {} ).get( 'item', {} ).get( 'musicbrainzartistid', [] )
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
                    lw.log( ['unexpected error gettting playing song back from Kodi', e] )
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
        lw.log( ['starting with the following artists', artist_names] )
        lw.log( ['disable multi artist is set to ' + self.DISABLEMULTIARTIST] )
        if self.DISABLEMULTIARTIST == 'true':
            if len( artist_names ) > 1:
                lw.log( ['deleting extra artists'] )
                del artist_names[1:]
            if len( mbids ) > 1:
                lw.log( ['deleting extra MBIDs'] )
                del mbids[1:]
        lw.log( ['left with', artist_names] )
        for artist_name, mbid in itertools.izip_longest( artist_names, mbids, fillvalue='' ):
            if artist_name:
                artists_info.append( (artist_name, self._get_musicbrainz_id( artist_name, mbid )) )
        self.ARTISTS_INFO = artists_info
        return artists_info


    def _get_directory_list( self, trynum='first' ):
        lw.log( ['checking %s for artist images' % self.CacheDir] )
        try:
            dirs, files = xbmcvfs.listdir( self.CacheDir )
        except OSError:
            files = []
        except Exception, e:
            lw.log( ['unexpected error getting directory list', e] )
            files = []
        if not files and trynum == 'first' and self.ENABLEFUZZYSEARCH == 'true':
            s_name = ''
            lw.log( ['the illegal characters are ', self.ILLEGALCHARS, 'the replacement is ' + self.ILLEGALREPLACE] )
            for c in list( self._remove_trailing_dot( self.NAME ) ):
                if c in self.ILLEGALCHARS:
                    s_name = s_name + self.ILLEGALREPLACE
                else:
                    s_name = s_name + c  
            lw.log( ['did not work with %s, trying %s' % (self.NAME, s_name)] )           
            self.CacheDir = os.path.join( self.LOCALARTISTPATH, smartUTF8(s_name).decode('utf-8'), self.FANARTFOLDER )
            files = self._get_directory_list( 'second' )
        return files
        

    def _get_featured_artists( self, data ):
        replace_regex = re.compile( r"ft\.", re.IGNORECASE )
        split_regex = re.compile( r"feat\.", re.IGNORECASE )
        the_split = split_regex.split( replace_regex.sub( 'feat.', data ) )
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


    def _get_image_list( self ):
        images = []
        image_params = {}
        image_params['mbid'] = self._get_musicbrainz_id( self.NAME, self.MBID )
        image_params['lang'] = self.LANGUAGE
        image_params['artist'] = self.NAME
        image_params['infodir'] = self.InfoDir
        image_params['exclusionsfile'] = os.path.join( self.CacheDir, "_exclusions.nfo" )
        for plugin_name in image_plugins['names']:
            image_list = []
            lw.log( ['checking %s for images' % plugin_name[1]] )
            image_params['getall'] = addon.getSetting( plugin_name[1] + "_all" )
            image_params['clientapikey'] = addon.getSetting( plugin_name[1] + "_clientapikey" )
            image_list, loglines = image_plugins['objs'][plugin_name[1]].getImageList( image_params )
            lw.log( loglines )
            images.extend( image_list )
            image_params['mbid'] = self._get_musicbrainz_id( self.NAME, self.MBID ) 
        return images


    def _get_infolabel( self, item ):
        try:
            infolabel = xbmc.getInfoLabel( item )
        except:
            lw.log( ['problem reading information from %s, returning blank' % item] )
            infolabel = ''
        return infolabel


    def _get_local_images( self ):
        self.LocalImagesFound = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        artist_path = os.path.join( self.LOCALARTISTPATH, smartUTF8(self.NAME).decode('utf-8') )
        self.CacheDir = os.path.join( artist_path, self.FANARTFOLDER )
        lw.log( ['cachedir = %s' % self.CacheDir] )
        artist_path_exists, loglines = checkPath( os.path.join( artist_path, '' ), False )
        copy_files = []
        if self.INCLUDEFANARTJPG == 'true' and artist_path_exists:
           copy_files.append( 'fanart.jpg' )
           copy_files.append( 'fanart.png' )
        if self.INCLUDEFOLDERJPG == 'true' and artist_path_exists:
            copy_files.append( 'folder.jpg' )
            copy_files.append( 'folder.png' )
        for one_file in copy_files:
            result, loglines = checkPath( self.CacheDir )
            lw.log( loglines )
            xbmcvfs.copy( os.path.join( artist_path, one_file ), os.path.join( self.CacheDir, one_file ) )
        files = self._get_directory_list()
        for file in files:
            if file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png'):
                self.LocalImagesFound = True
        if self.LocalImagesFound:
            lw.log( ['local images found'] )
            if self.ARTISTNUM == 1:
            	self._set_artwork_skininfo( self.CacheDir )
                self._get_artistinfo()
            if self.TOTALARTISTS > 1:
               self._merge_images()


    def _get_musicbrainz_id( self, theartist, mbid ):
        self._set_infodir( theartist )
        lw.log( ['Looking for a musicbrainz ID for artist ' + theartist] )
        if mbid:
            lw.log( ['returning ' + mbid] )
            return mbid
        mbid_params = {}
        mbid_params['infodir'] = self.InfoDir
        for plugin_name in mbid_plugins['names']:
            lw.log( ['checking %s for mbid' % plugin_name[1]] )
            mbid, loglines = mbid_plugins['objs'][plugin_name[1]].getMBID( mbid_params )
            lw.log( loglines )
            if mbid:
                lw.log( ['returning ' + mbid] )
                return mbid
        lw.log( ['no musicbrainz ID found for artist ' + theartist] )
        return ''


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
        self.LANGUAGE = addon.getSetting( "language" )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                lw.log( ['language = %s' % self.LANGUAGE] )
                break
        self.LOCALARTISTPATH = addon.getSetting( "local_artist_path" ).decode('utf-8')
        self.PRIORITY = addon.getSetting( "priority" )
        self.USEFALLBACK = addon.getSetting( "fallback" )
        self.FALLBACKPATH = addon.getSetting( "fallback_path" ).decode('utf-8')
        self.USEOVERRIDE = addon.getSetting( "slideshow" )
        self.OVERRIDEPATH = addon.getSetting( "slideshow_path" ).decode('utf-8')
        self.RESTRICTCACHE = addon.getSetting( "restrict_cache" )
        self.DISABLEMULTIARTIST = addon.getSetting( "disable_multiartist" )
        self.INCLUDEFANARTJPG = addon.getSetting( "include_fanartjpg" )
        self.INCLUDEFOLDERJPG = addon.getSetting( "include_folderjpg" )
        try:
            self.maxcachesize = int( addon.getSetting( "max_cache_size" ) ) * 1000000
        except ValueError:
            self.maxcachesize = 1024 * 1000000
        except Exception, e:
            lw.log( ['unexpected error while parsing maxcachesize setting', e] )
            self.maxcachesize = 1024 * 1000000
        self.NOTIFICATIONTYPE = addon.getSetting( "show_progress" )
        if self.NOTIFICATIONTYPE == "2":
            self.PROGRESSPATH = addon.getSetting( "progress_path" ).decode('utf-8')
            lw.log( ['set progress path to %s' % self.PROGRESSPATH] )
        else:
            self.PROGRESSPATH = ''
        if addon.getSetting( "fanart_folder" ):
            self.FANARTFOLDER = addon.getSetting( "fanart_folder" ).decode('utf-8')
            lw.log( ['set fanart folder to %s' % self.FANARTFOLDER] )
        else:
            self.FANARTFOLDER = 'extrafanart'
        self.ENABLEFUZZYSEARCH = addon.getSetting( "enable_fuzzysearch" )
        lw.log( ['fuzzy search is ' + self.ENABLEFUZZYSEARCH] )
        if self.ENABLEFUZZYSEARCH == 'true':
            pl = addon.getSetting( "storage_target" )
            lw.log( ['the target is ' + pl] )
            if pl == "0":
                self.ENDREPLACE = addon.getSetting( "end_replace" )
                self.ILLEGALCHARS = list( '<>:"/\|?*' )
            elif pl == "2":
                self.ENDREPLACE = '.'
                self.ILLEGALCHARS = [':']
            else:
                self.ENDREPLACE = '.'
                self.ILLEGALCHARS = [os.path.sep]
            self.ILLEGALREPLACE = addon.getSetting( "illegal_replace" )


    def _init_vars( self ):
        self.DATAROOT = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
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
        if addon.getSetting( "transparent" ) == 'true':
            self._set_property("ArtistSlideshowTransparent", 'true')
            self.InitDir = xbmc.translatePath('%s/resources/transparent' % addonpath ).decode('utf-8')
        else:
            self._set_property("ArtistSlideshowTransparent", '')
            self.InitDir = xbmc.translatePath('%s/resources/black' % addonpath ).decode('utf-8')
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
        self.TransitionDir = xbmc.translatePath('special://profile/addon_data/%s/transition' % addonname ).decode('utf-8')
        self.MergeDir = xbmc.translatePath('special://profile/addon_data/%s/merge' % addonname ).decode('utf-8')
        self.params = {}


    def _init_window( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.ARTISTSLIDESHOW = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow" )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )


    def _make_dirs( self ):
        exists, loglines = checkPath( os.path.join( self.InitDir, '' ) )
        lw.log( loglines )
        exists, loglines = checkPath( os.path.join( self.DATAROOT, '' ) )
        lw.log( loglines )
        thedirs = ['temp', 'ArtistSlideshow', 'ArtistInformation', 'transition', 'merge']
        for onedir in thedirs:
            exists, loglines = checkPath( os.path.join( self.DATAROOT, onedir, '' ) )
            lw.log( loglines )


    def _merge_images( self ):
        lw.log( ['merging files from primary directory %s into merge directory %s' % (self.CacheDir, self.MergeDir)] )
        self.MergedImagesFound = True
        dirs, files = xbmcvfs.listdir(self.CacheDir)
        for file in files:
            if(file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')):
                img_source = os.path.join( self.CacheDir, smartUTF8( file ).decode( 'utf-8' ) )
                img_dest = os.path.join( self.MergeDir, itemHash( img_source ) + getImageType( img_source ) )               
                xbmcvfs.copy( img_source, img_dest )                
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


    def _remove_trailing_dot( self, thename ):
        if thename[-1] == '.' and len( thename ) > 1 and self.ENDREPLACE <> '.':
            return self._remove_trailing_dot( thename[:-1] + self.ENDREPLACE )
        else:
            return thename


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
        similar_total = ''
        album_total = ''
        self._set_property( "ArtistSlideshow.ArtistBiography", self.biography )
        for count, item in enumerate( self.similar ):
            self._set_property( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ), item[0] )
            self._set_property( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ), item[1] )
            similar_total = str( count )
        for count, item in enumerate( self.albums ):
            self._set_property( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ), item[0] )
            self._set_property( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ), item[1] )
            album_total = str( count )
        self._set_property( "ArtistSlideshow.SimilarCount", similar_total )
        self._set_property( "ArtistSlideshow.AlbumCount", album_total )
        

    def _set_property( self, property_name, value=""):
        #sets a property (or clears it if no value is supplied)
        #does not crash if e.g. the window no longer exists.
        try:
          self.WINDOW.setProperty( property_name, value )
          lw.log( ['%s set to %s' % (property_name, value)] )
        except Exception, e:
          lw.log( ["Exception: Couldn't set propery " + property_name + " value " + value , e])


    def _set_thedir(self, theartist, dirtype):
        CacheName = itemHash(theartist)
        thedir = xbmc.translatePath('special://profile/addon_data/%s/%s/%s/' % ( addonname , dirtype, CacheName, )).decode('utf-8')
        exists, loglines = checkPath( thedir )
        lw.log( loglines )
        return thedir


    def _split_artists( self, response):
        return response.replace(' ft. ',' / ').replace(' feat. ',' / ').split(' / ')


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
        if self.ARTISTNUM == 1:
            self._get_artistinfo()
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
        else:
            self.LASTARTISTREFRESH = 0
            if self.ARTISTNUM == 1:
                if self.NOTIFICATIONTYPE == "1":
                    self._set_property("ArtistSlideshow", self.InitDir)
                    command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30300)), smartUTF8(language(30301)), 5000, smartUTF8(addonicon))
                    xbmc.executebuiltin(command)
                elif self.NOTIFICATIONTYPE == "2":
                    self._set_property("ArtistSlideshow", self.PROGRESSPATH)
                else:
                    self._set_property("ArtistSlideshow", self.InitDir)
        lw.log( ['downloading images'] )
        folders, cachelist = xbmcvfs.listdir( self.CacheDir )
        cachelist_str = ''.join(str(e) for e in cachelist)
        for url in self._get_image_list():
            lw.log( ['the url to check is ' + url] )
            if( self._playback_stopped_or_changed() ):
                return
            path = itemHashwithPath( url, self.CacheDir )
            path2 = itemHashwithPath( url, self.TransitionDir )
            checkpath, checkfilename = os.path.split( path )
            if not (checkfilename in cachelist_str):
                if self._download(url, path, path2):
                    lw.log( ['downloaded %s to %s' % (url, path)]  )
                    self.ImageDownloaded = True
            if self.ImageDownloaded:
                if( self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                    self._set_artwork_skininfo( self.CacheDir )
                    self.LASTARTISTREFRESH = time.time()
                    self._clean_dir( self.TransitionDir )
                    return
                if not self.CachedImagesFound:
                    self.CachedImagesFound = True
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
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30304)), smartUTF8(language(30305)), 5000, smartUTF8(addonicon))
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
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30302)), smartUTF8(language(30303)), 10000, smartUTF8(addonicon))
                        xbmc.executebuiltin(command)
            elif self.TOTALARTISTS > 1:
                self._merge_images()


    def _trim_cache( self ):
        if( self.RESTRICTCACHE == 'true' and not self.PRIORITY == '2' ):
            now = time.time()
            cache_trim_delay = 0   #delay time is in seconds
            if( now - self.LastCacheTrim > cache_trim_delay ):
                lw.log( ['trimming the cache down to %s bytes' % self.maxcachesize]  )
                cache_root = xbmc.translatePath( 'special://profile/addon_data/%s/ArtistSlideshow/' % addonname ).decode('utf-8')
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
        for artist, mbid in self._get_current_artists_info( ):
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
    lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
    lw.log( ['debug logging set to %s' % logdebug], xbmc.LOGNOTICE )
    slideshow = Main()
lw.log( ['script stopped'], xbmc.LOGNOTICE )
