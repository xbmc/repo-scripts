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

from __future__ import division
try:
    from itertools import izip_longest as _zip_longest
except ImportError:
    from itertools import zip_longest as _zip_longest
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import os, random, re, sys, threading, time
import json as _json
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from kodi_six.utils import py2_encode, py2_decode
from resources.common.fileops import checkPath, writeFile, readFile, deleteFile, deleteFolder, moveFile, naturalKeys
from resources.common.url import URL
from resources.common.xlogger import Logger
from resources.common.kodisettings import getSettingBool, getSettingInt, getSettingString
import resources.plugins

addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo('id')
addonversion = addon.getAddonInfo('version')
addonpath    = addon.getAddonInfo('path')
addonicon    = xbmc.translatePath('%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[Artist Slideshow]'
logdebug     = getSettingBool( addon, "logging" )

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
    except Exception as e:
        lw.log( ['unexpected error while parsing %s setting for %s' % (description, module), e] )
        active = 'false'
    if active == 'true':
        try:
            priority = int( addon.getSetting( preamble + "priority_" + module ) )
        except ValueError:
            priority = 10
        except Exception as e:
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


class Slideshow( threading.Thread ):

    def __init__( self, workqueue, queuelock, window, delay, fadetoblack ):
        super( Slideshow , self).__init__()
        self.WORKQUEUE = workqueue
        self.QUEUELOCK= queuelock
        self.WINDOW = window
        self.DELAY = delay
        self.IMAGES = []
        self.IMAGEADDED = False
        self.IMAGESCLEARED = False
        self.SHOW = True
        self.FADETOBLACK = fadetoblack
        lw.log( ['Slideshow thread started'] )


    def AddImage( self, path ):
        if path:
            self.IMAGES.append( path )
            lw.log( ['Added to image display group: ' + path] )
            self.IMAGEADDED = True
            return True
        else:
            lw.log( ['Image path was empty, nothing added'] )
            return False


    def ClearImages( self ):
        self.IMAGES = []
        if self.FADETOBLACK:
            self._set_property( 'ArtistSlideshow.Image', os.path.join( addonpath, 'resources', 'images', 'black-hd.png' ) )
        else:
            self._set_property( 'ArtistSlideshow.Image' )
        lw.log( ['images cleared'] )
        self.IMAGESCLEARED = True


    def run( self ):
        cmd = ''
        last_image = ''
        if self.FADETOBLACK:
            self._set_property( 'ArtistSlideshow.Image', os.path.join( addonpath, 'resources', 'images', 'black-hd.png' ) )
        while self.SHOW:
            outofimages = True
            with self.QUEUELOCK:
                if not self.WORKQUEUE.empty():
                    cmd = self.WORKQUEUE.get()
            if cmd == 'quit':
                break
            if self.IMAGEADDED or self.IMAGESCLEARED or outofimages:
                random.shuffle( self.IMAGES )
#                lw.log( ['the images available are', self.IMAGES] )
                self.IMAGEADDED = False
                self.IMAGESCLEARED = False
                outofimages = False
            for image in self.IMAGES:
                if self.IMAGEADDED or self.IMAGESCLEARED:
                    lw.log( ['image list changed, resetting loop'] )
                    break
                if not image == last_image:
                    self._set_property( 'ArtistSlideshow.Image', image )
                    lw.log( ['ArtistSlideshow.Image set to ' + image] )
                    self._wait( self.DELAY )
                    last_image = image
                if not self.SHOW:
                    break
        lw.log( ['Slideshow thread stopping'] )


    def _set_property( self, property_name, value="" ):
        try:
          self.WINDOW.setProperty( property_name, value )
          lw.log( ['%s set to %s' % (property_name, value)] )
        except Exception as e:
          lw.log( ["Exception: Couldn't set propery " + property_name + " value " + value , e])


    def _wait( self, wait_time ):
        cmd = ''
        waited = 0
        m_wait_time = wait_time*1000
        while( waited < m_wait_time ):
            xbmc.sleep(100)
            waited = waited + 100
            with self.QUEUELOCK:
                if not self.WORKQUEUE.empty():
                    cmd = self.WORKQUEUE.get()
            if cmd == 'quit':
                self.SHOW = False
                return
            if cmd == 'reset':
                return


class Main( object ):

    def __init__( self ):
        self._parse_argv()
        self._init_window()
        if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True" and not self.RUNFROMSETTINGS:
            lw.log( ['script already running'] )
        else:
            self._upgrade_settings()
            self._get_settings()
            self._init_vars()
            self._make_dirs()
            self._upgrade()
            if self._run_from_settings():
                return
            self._set_property( 'ArtistSlideshowRunning', 'True' )
            if self.FADETOBLACK:
                self._set_property( 'ArtistSlideshow.Image', os.path.join( addonpath, 'resources', 'images', 'black-hd.png' ) )
            self.SLIDESHOW.setDaemon(True)
            self.SLIDESHOW.start()
            if( not xbmc.Player().isPlayingAudio() and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                lw.log( ['no music playing'] )
                if( self.DAEMON == 'False' ):
                    self._set_property( 'ArtistSlideshowRunning' )
                    self._set_property( 'ArtistSlideshow.Image' )
            else:
                lw.log( ['first song started'] )
                xbmc.sleep(1000) # it may take some time for Kodi to read the tag info after playback started
                self._use_correct_artwork()
                self._trim_cache()
            while not xbmc.Monitor().abortRequested():
                xbmc.sleep(1000)
                if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
                    if( xbmc.Player().isPlayingAudio() or self._get_infolabel( self.EXTERNALCALL ) != '' ):
                        if set( self.ALLARTISTS ) != set( self._get_current_artists() ):
                            self._clear_properties()
                            self._use_correct_artwork()
                            self._trim_cache()
                    else:
                        xbmc.sleep(2000) # doublecheck if playback really stopped
                        if( not xbmc.Player().isPlayingAudio() and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                            if ( self.DAEMON == "False" ):
                                self._set_property( "ArtistSlideshowRunning" )
                else:
                    self._clear_properties()
                    break
            try:
                self._set_property("ArtistSlideshow.CleanupComplete", "True")
            except Exception as e:
                lw.log( ['unexpected error while setting property.', e] )
            with self.SLIDESHOWLOCK:
                self.SLIDESHOWCMD.put( 'quit' )
            self.SLIDESHOW.join()


    def _clean_dir( self, dir_path ):
        try:
            dirs, old_files = xbmcvfs.listdir( dir_path )
        except Exception as e:
            lw.log( ['unexpected error while getting directory list', e] )
            return
        for old_file in old_files:
            success, loglines = deleteFile( os.path.join (dir_path, py2_decode( old_file ) ) )
            lw.log( loglines )


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
        self.FANARTNUMBER = False
        self.SLIDESHOW.ClearImages()
        self.SLIDESHOWCMD.put('reset')
        self._set_property( "ArtistSlideshow.ArtistBiography" )
        for count in range( 50 ):
            self._set_property( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ) )


    def _delete_folder( self, folder ):
        success, loglines = deleteFolder( os.path.join( folder, '' ) )
        if success:
            lw.log( ['deleted folder ' + folder] )
        else:
            lw.log( loglines )


    def _download( self ):
        self.FANARTNUMBER = False
        image_downloaded = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        lw.log( ['downloading images'] )
        imgdb = os.path.join( self.INFODIR, self.IMGDB )
        lw.log( ['checking download cache file ' + imgdb] )
        loglines, cachelist_str = readFile( imgdb )
        lw.log( loglines )
        for url in self._get_image_list():
            lw.log( ['the url to check is ' + url] )
            if( self._playback_stopped_or_changed() ):
                return
            url_image_name = url.rsplit('/', 1)[-1]
            path = os.path.join( self.CACHEDIR, self._set_image_name( url, self.CACHEDIR, self.KODILOCALSTORAGE ) )
            lw.log( ['checking %s against %s' % (url_image_name, cachelist_str)] )
            if not (url_image_name in cachelist_str):
                if not xbmc.Monitor().abortRequested():
                    tmpname = os.path.join( self.DATAROOT, 'temp', url.rsplit('/', 1)[-1] )
                    lw.log( ['the tmpname is ' + tmpname] )
                    if xbmcvfs.exists( tmpname ):
                        success, loglines = deleteFile( tmpname )
                        lw.log( loglines )
                    success, loglines, urldata = imgURL.Get( url, params=self.PARAMS )
                    lw.log( loglines )
                    if success:
                        success, loglines = writeFile( bytearray( urldata ), tmpname )
                        lw.log( loglines )
                    if not success:
                        return False
                    if xbmcvfs.Stat( tmpname ).st_size() > 999:
                        if not xbmcvfs.exists ( path ):
                            success, loglines = moveFile( tmpname, path )
                            lw.log( loglines )
                            lw.log( ['downloaded %s to %s' % (url, path)]  )
                            lw.log( ['updating download database at ' + imgdb] )
                            cachelist_str = cachelist_str + url_image_name + '\r'
                            success, loglines = writeFile( cachelist_str, imgdb )
                            lw.log( loglines )
                            self.SLIDESHOW.AddImage( path )
                            self.IMAGESFOUND = True
                            image_downloaded = True
                        else:
                            lw.log( ['image already exists, deleting temporary file'] )
                            success, loglines = deleteFile( tmpname )
                            lw.log( loglines )
                    else:
                        success, loglines = deleteFile( tmpname )
                        lw.log( loglines )
        if not image_downloaded:
            lw.log( ['no new images downloaded'] )
        return image_downloaded


    def _get_artistinfo( self ):
        bio = ''
        bio_params = {}
        bio_params['mbid'] = self.MBID
        bio_params['infodir'] = self.INFODIR
        bio_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        bio_params['lang'] = self.LANGUAGE
        bio_params['artist'] = self.NAME
        bio = ''
        try:
            bio_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in bio_plugins['names']:
            lw.log( ['checking %s for bio' % plugin_name[1]] )
            bio_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
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
        album_params['infodir'] = self.INFODIR
        album_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        album_params['lang'] = self.LANGUAGE
        album_params['artist'] = self.NAME
        albums = []
        try:
            album_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in album_plugins['names']:
            lw.log( ['checking %s for album info' % plugin_name[1]] )
            album_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
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
        similar_params['infodir'] = self.INFODIR
        similar_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
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
        for artist_info in self._get_current_artists_info( ):
            current_artists.append( artist_info[0] )
        return current_artists


    def _get_current_artists_info( self ):
        featured_artists = ''
        artist_names = []
        artists_info = []
        mbids = []
        if xbmc.Player().isPlayingAudio():
            try:
                playing_file = xbmc.Player().getPlayingFile()
            except RuntimeError:
                return artists_info
            except Exception as e:
                lw.log( ['unexpected error getting playing file back from Kodi', e] )
                return artists_info
            if playing_file != self.LASTPLAYINGFILE:
                # if the same file is playing, use cached JSON response instead of doing a new query
                response = xbmc.executeJSONRPC (
                    '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "musicbrainzartistid"]},"id":1}' )
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
            except Exception as e:
                lw.log( ['unexpected error gettting playing song back from XBMC', e] )
                playing_song = ''
            if not artist_names:
                lw.log( ['No artist names returned from JSON call, assuming this is an internet stream'] )
                try:
                    playingartist = playing_song[0:(playing_song.find('-'))-1]
                except RuntimeError:
                    playingartist = ''
                    playing_song = ''
                except Exception as e:
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
        lw.log( ['disable multi artist is set to ' + str( self.DISABLEMULTIARTIST )] )
        if self.DISABLEMULTIARTIST:
            if len( artist_names ) > 1:
                lw.log( ['deleting extra artists'] )
                del artist_names[1:]
            if len( mbids ) > 1:
                lw.log( ['deleting extra MBIDs'] )
                del mbids[1:]
        lw.log( ['left with', artist_names] )
        for artist_name, mbid in _zip_longest( artist_names, mbids, fillvalue='' ):
            if artist_name:
                artists_info.append( (py2_encode( artist_name ), self._get_musicbrainz_id( py2_encode( artist_name ), mbid )) )
        self.ARTISTS_INFO = artists_info
        return artists_info


    def _get_file_list( self, path, do_filter=False ):
        lw.log( ['checking %s for artist images' % path] )
        try:
            dirs, files = xbmcvfs.listdir( path )
        except OSError:
            files = []
        except Exception as e:
            lw.log( ['unexpected error getting directory list', e] )
            files = []
        if files and self.KODILOCALSTORAGE and do_filter:
            filtered_files = []
            for file in files:
                if file.lower().startswith('fanart'):
                    filtered_files.append( file )
            files = filtered_files
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
        image_params['infodir'] = self.INFODIR
        for plugin_name in image_plugins['names']:
            image_list = []
            lw.log( ['checking %s for images' % plugin_name[1]] )
            image_params['getall'] = addon.getSetting( plugin_name[1] + "_all" )
            image_params['clientapikey'] = addon.getSetting( plugin_name[1] + "_clientapikey" )
            image_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
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


    def _get_musicbrainz_id( self, theartist, mbid ):
        self._set_infodir( theartist )
        lw.log( ['Looking for a musicbrainz ID for artist ' + theartist] )
        if mbid:
            lw.log( ['returning ' + mbid] )
            return mbid
        mbid_params = {}
        mbid_params['infodir'] = self.INFODIR
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
                got_item = False
            except Exception as e:
                got_item = False
                lw.log( ['unexpected error getting %s from Kodi' % item, e] )
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
        self.LANGUAGE = getSettingString( addon, 'language' )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                lw.log( ['language = %s' % self.LANGUAGE] )
                break
        self.USEFALLBACK = getSettingBool( addon, 'fallback' )
        self.FALLBACKPATH = getSettingString( addon, 'fallback_path' )
        self.USEOVERRIDE = getSettingBool( addon, 'slideshow' )
        self.OVERRIDEPATH = getSettingString( addon, 'slideshow_path' )
        self.INCLUDEARTISTFANART = getSettingBool( addon, 'include_artistfanart', default=True )
        self.INCLUDEALBUMFANART = getSettingBool( addon, 'include_albumfanart', default=False )
        self.DISABLEMULTIARTIST = getSettingBool( addon, 'disable_multiartist' )
        self.MAXCACHESIZE = getSettingInt( addon, 'max_cache_size', default=1024 ) * 1000000
        self.SLIDEDELAY = getSettingInt( addon, 'slide_delay', default=10 )
        self.FADETOBLACK = getSettingBool( addon, 'fadetoblack', default=True )
        artist_image_storage = getSettingInt( addon, 'artist_image_storage', default=0 )
        if artist_image_storage == 1:
            self.KODILOCALSTORAGE = True
            self.LOCALARTISTSTORAGE = False
            self.RESTRICTCACHE = False
            self.USEFANARTFOLDER = False
            self.FANARTFOLDER = ''
            response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"musiclibrary.artistsfolder"}, "id":1}')
            lw.log( ['got the following response back from Kodi for music artist folder', response] )
            try:
                self.LOCALARTISTPATH = _json.loads(response)['result']['value']
            except (IndexError, KeyError, ValueError):
                self.KODILOCALSTORAGE = False
                self.LOCALARTISTSTORAGE = False
                self.LOCALARTISTPATH = ''
                self.RESTRICTCACHE = getSettingBool( addon, 'restrict_cache' )
                self.USEFANARTFOLDER = False
                self.FANARTFOLDER = ''
        elif artist_image_storage == 2:
            self.KODILOCALSTORAGE = False
            self.LOCALARTISTSTORAGE = True
            self.LOCALARTISTPATH = getSettingString( addon, 'local_artist_path' )
            self.RESTRICTCACHE = False
            self.USEFANARTFOLDER = getSettingBool( addon, 'use_extrafanart_folder', default=True )
            if self.USEFANARTFOLDER:
                self.FANARTFOLDER = getSettingString( addon, 'fanart_folder', default='extrafanart' )
            else:
                self.FANARTFOLDER = ''
        else:
            self.KODILOCALSTORAGE = False
            self.LOCALARTISTSTORAGE = False
            self.LOCALARTISTPATH = ''
            self.USEFANARTFOLDER = False
            self.FANARTFOLDER = ''
            self.RESTRICTCACHE = getSettingBool( addon, 'restrict_cache' )
        if getSettingInt( addon, 'artist_info_storage' ) == 1:
            self.LOCALINFOSTORAGE = True
            self.LOCALINFOPATH = getSettingString( addon, 'local_info_path' )
        else:
            self.LOCALINFOSTORAGE = False
            self.LOCALINFOPATH = ''
        pl = getSettingInt( addon, "storage_target" )
        if pl == 0:
            self.ENDREPLACE = getSettingString( addon, "end_replace" )
            self.ILLEGALCHARS = list( '<>:"/\|?*' )
        elif pl == 2:
            self.ENDREPLACE = '.'
            self.ILLEGALCHARS = [':']
        else:
            self.ENDREPLACE = '.'
            self.ILLEGALCHARS = [os.path.sep]
        self.ILLEGALREPLACE = addon.getSetting( "illegal_replace" )


    def _init_vars( self ):
        self.FANARTNUMBER = False
        self.CACHEDIR = ''
        self.ARTISTS_INFO = []
        self.DATAROOT = xbmc.translatePath( addon.getAddonInfo('profile') )
        self.IMGDB = '_imgdb.nfo'
        self._set_property( 'ArtistSlideshow.CleanupComplete' )
        self._set_property( 'ArtistSlideshow', os.path.join( addonpath, 'resources', 'update-slide', '' ) )
        self.SKININFO = {}
        for item in self.FIELDLIST:
            if self.PASSEDFIELDS[item]:
                self.SKININFO[item[0:-5]] = 'Window(%s).Property(%s)' % ( self.WINDOWID, self.PASSEDFIELDS[item] )
            else:
                self.SKININFO[item[0:-5]] = ''
        self.EXTERNALCALLSTATUS = self._get_infolabel( self.EXTERNALCALL )
        lw.log( ['external call is set to ' + self._get_infolabel( self.EXTERNALCALL )] )
        self.NAME = ''
        self.ALLARTISTS = []
        self.MBID = ''
        self.VARIOUSARTISTSMBID = '89ad4ac3-39f7-470e-963a-56509c546377'
        self.LASTPLAYINGFILE = ''
        self.LASTJSONRESPONSE = ''
        self.LASTARTISTREFRESH = 0
        self.LASTCACHETRIM = 0
        self.PARAMS = {}
        self.SLIDESHOWLOCK = threading.Lock()
        self.SLIDESHOWCMD = Queue()
        self.SLIDESHOW = Slideshow( self.SLIDESHOWCMD, self.SLIDESHOWLOCK, self.WINDOW, self.SLIDEDELAY, self.FADETOBLACK )


    def _init_window( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )


    def _make_dirs( self ):
        exists, loglines = checkPath( os.path.join( self.DATAROOT, '' ) )
        lw.log( loglines )
        thedirs = ['temp', 'ArtistSlideshow', 'ArtistInformation']
        for onedir in thedirs:
            exists, loglines = checkPath( os.path.join( self.DATAROOT, onedir, '' ) )
            lw.log( loglines )


    def _move_to_kodi_storage( self ):
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno( language(32200) + ': ' + language(32201), language(32300) )
        if not ret:
            lw.log( ['Image move aborted by user'] )
            return
        if self.KODILOCALSTORAGE:
            lw.log( ['Kodi artist information storage already selected. Aborting.'] )
            dialog.ok( language(32200) + ': ' + language(32202), language(32302) )
            return
        response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"musiclibrary.artistsfolder"}, "id":1}')
        lw.log( ['Got the following response back from Kodi for artist information folder', response] )
        try:
            kodi_music_artist_path = _json.loads( response )['result']['value']
        except (IndexError, KeyError, ValueError):
            kodi_music_artist_path = ''
        if not kodi_music_artist_path:
            lw.log( ['No artist information folder setting found. Aborting.'] )
            dialog.ok( language(32200) + ': ' + language(32202), language(32301) )
            return
        lw.log( ['Artist information folder set to %s' % kodi_music_artist_path] )
        pdialog = xbmcgui.DialogProgress()
        if self.LOCALARTISTSTORAGE and self.LOCALARTISTPATH:
            pdialog.create( language(32200) + ': ' + language(32203), language(32303) )
            src = self.LOCALARTISTPATH
        else:
            pdialog.create( language(32200) + ': ' + language(32203), language(32304) )
            src = os.path.join( self.DATAROOT, 'ArtistSlideshow' )
        try:
            dirs, files = xbmcvfs.listdir( src )
        except OSError:
            dirs = []
        except Exception as e:
            lw.log( ['unexpected error getting directory list', e] )
            dirs = []
        if not dirs:
            pdialog.close()
            dialog.ok( language(32200) + ': ' + language(32203), language(32306) )
            return
        increment = 100/len( dirs )
        progress = 0.0
        for thedir in dirs:
            if (src == self.LOCALARTISTPATH) and self.USEFANARTFOLDER:
                image_src = os.path.join( self.LOCALARTISTPATH, py2_decode( thedir ), self.FANARTFOLDER )
            else:
                image_src = os.path.join( src, py2_decode( thedir ) )
            image_dest = os.path.join( kodi_music_artist_path, py2_decode( thedir ) )
            lw.log( ['moving images from %s to %s' % (image_src, image_dest)] )
            files = self._get_file_list( image_src )
            self.FANARTNUMBER = False
            for file in files:
                file_src = os.path.join( image_src, file )
                file_dst = os.path.join( image_dest, self._set_image_name( file, image_dest, True ) )
                success, loglines = moveFile( file_src, file_dst  )
                lw.log( loglines )
            self._delete_folder( image_src )
            if (src == self.LOCALARTISTPATH) and self.USEFANARTFOLDER:
                self._delete_folder( os.path.abspath( os.path.join( image_src, os.pardir ) ) )
            if pdialog.iscanceled():
                pdialog.close()
                return
            progress = progress + increment
            pdialog.update( int( progress ) )
            lw.log( ['using increment of %s updating progress to %s' % (str( increment ), str( progress ))] )
        pdialog.close()
        dialog.ok( language(32200) + ': ' + language(32203), language(32306) )


    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except IndexError:
            params = {}
        except Exception as e:
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
        self.RUNFROMSETTINGS = False
        self.MOVETOKODISTORAGE = False
        checkmove = params.get( "movetokodistorage", "False" )
        if checkmove.lower() == 'true':
            self.MOVETOKODISTORAGE = True
            self.RUNFROMSETTINGS = True


    def _playback_stopped_or_changed( self ):
        if set( self.ALLARTISTS ) != set( self._get_current_artists() ) or self.EXTERNALCALLSTATUS != self._get_infolabel( self.EXTERNALCALL ):
            self._clear_properties()
            return True
        else:
            return False


    def _remove_trailing_dot( self, thename ):
        if thename[-1] == '.' and len( thename ) > 1 and self.ENDREPLACE != '.':
            return self._remove_trailing_dot( thename[:-1] + self.ENDREPLACE )
        else:
            return thename


    def _run_from_settings( self ):
        if self.MOVETOKODISTORAGE:
            self._move_to_kodi_storage()
            return True
        return False


    def _set_artwork_from_dir( self, thedir, files ):
        for file in files:
            self.SLIDESHOW.AddImage( os.path.join( thedir, file ) )


    def _set_cachedir( self, theartist ):
        self.CACHEDIR = self._set_thedir( theartist, 'ArtistSlideshow' )


    def _set_fanart_number( self, thedir ):
        files = self._get_file_list( thedir, do_filter=True )
        files.sort( key=naturalKeys )
        lw.log( files )
        if files:
            lastfile = files[-1]
            try:
                tmpname = os.path.splitext( lastfile )[0]
            except IndexError:
                fanart_number = 1
            try:
                fanart_number = int( re.search('(\d+)$', tmpname).group(0) ) + 1
            except ValueError:
                fanart_number = 1
        else:
            fanart_number = 1
        return fanart_number


    def _set_image_name( self, url, thedir, kodi_storage ):
        if not kodi_storage:
            return url.rsplit('/', 1)[-1]
        ext = os.path.splitext( url )[1]
        if self.FANARTNUMBER:
            self.FANARTNUMBER += 1
        else:
            self.FANARTNUMBER = self._set_fanart_number( thedir )
        return "fanart" + str( self.FANARTNUMBER ) + ext


    def _set_infodir( self, theartist ):
        self.INFODIR = self._set_thedir( theartist, 'ArtistInformation' )


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


    def _set_property( self, property_name, value='' ):
        try:
          self.WINDOW.setProperty( property_name, value )
          lw.log( ['%s set to %s' % (property_name, value)] )
        except Exception as e:
          lw.log( ['Exception: Could not set property %s to value %s' % (property_name, value), e])


    def _set_safe_artist_name( self, theartist ):
        s_name = ''
        lw.log( ['the illegal characters are ', self.ILLEGALCHARS, 'the replacement is ' + self.ILLEGALREPLACE] )
        for c in list( self._remove_trailing_dot( theartist ) ):
            if c in self.ILLEGALCHARS:
                s_name = s_name + self.ILLEGALREPLACE
            else:
                s_name = s_name + c
        return py2_decode( s_name )


    def _set_thedir( self, theartist, dirtype ):
        CacheName = self._set_safe_artist_name( theartist )
        if dirtype == 'ArtistSlideshow' and (self.LOCALARTISTSTORAGE or self.KODILOCALSTORAGE) and self.LOCALARTISTPATH:
            if self.FANARTFOLDER:
                thedir = os.path.join( self.LOCALARTISTPATH, CacheName, self.FANARTFOLDER )
            else:
                thedir = os.path.join( self.LOCALARTISTPATH, CacheName )
        elif dirtype == 'ArtistInformation' and self.LOCALINFOSTORAGE and self.LOCALINFOPATH:
            thedir = os.path.join( self.LOCALINFOPATH, CacheName, 'information' )
        else:
            thedir = os.path.join( self.DATAROOT, dirtype, CacheName )
        exists, loglines = checkPath( os.path.join( thedir, '' ) )
        if exists:
            lw.log( loglines )
        return thedir


    def _split_artists( self, response):
        return response.replace(' ft. ',' / ').replace(' feat. ',' / ').split(' / ')


    def _trim_cache( self ):
        if self.RESTRICTCACHE:
            now = time.time()
            cache_trim_delay = 0
            if (now - self.LASTCACHETRIM > cache_trim_delay):
                lw.log( ['trimming the cache down to %s bytes' % self.MAXCACHESIZE]  )
                cache_root = os.path.join( self.DATAROOT, 'ArtistSlideshow', '')
                folders, fls = xbmcvfs.listdir( cache_root )
                try:
                    folders.sort( key=lambda x: os.path.getmtime( os.path.join( cache_root, x ) ), reverse=True )
                except Exception as e:
                    lw.log( ['unexpected error sorting cache directory', e] )
                    return
                cache_size = 0
                first_folder = True
                for folder in folders:
                    if( self._playback_stopped_or_changed() ):
                        break
                    cache_size = cache_size + self._get_folder_size( os.path.join (cache_root, folder ) )
                    lw.log( ['looking at folder %s cache size is now %s' % (folder, cache_size)] )
                    if( cache_size > self.MAXCACHESIZE and not first_folder ):
                        self._clean_dir( os.path.join( cache_root, folder ) )
                        lw.log( ['deleted files in folder %s' % folder] )
                        self._delete_folder( os.path.join( cache_root, folder ) )
                        if self.LOCALINFOSTORAGE and self.LOCALINFOPATH:
                            deleteFile( os.path.join( self.LOCALINFOPATH, py2_decode( folder ), 'information', self.IMGDB ) )
                        else:
                            deleteFile( os.path.join( self.DATAROOT, 'ArtistInformation', py2_decode( folder ), self.IMGDB ) )
                    first_folder = False
                self.LASTCACHETRIM = now


    def _use_correct_artwork( self ):
        self.ALLARTISTS = self._get_current_artists()
        self.ARTISTNUM = 0
        self.TOTALARTISTS = len( self.ALLARTISTS )
        self.IMAGESFOUND = False
        if self.USEOVERRIDE:
            lw.log( ['using override directory for images'] )
            self._set_artwork_from_dir( self.OVERRIDEPATH, self._get_file_list( self.OVERRIDEPATH ) )
            return
        if self.INCLUDEARTISTFANART:
            self.IMAGESFOUND = self.IMAGESFOUND or self.SLIDESHOW.AddImage( xbmc.getInfoLabel( 'Player.Art(artist.fanart)' ) )
        if self.INCLUDEALBUMFANART:
            self.IMAGESFOUND = self.IMAGESFOUND or self.SLIDESHOW.AddImage( xbmc.getInfoLabel( 'Player.Art(album.fanart)' ) )
        for artist, mbid in self._get_current_artists_info( ):
            got_one_artist_images = False
            self.ARTISTNUM += 1
            self.NAME = artist
            self.MBID = mbid
            self._set_infodir( py2_decode( self.NAME ) )
            self._set_cachedir( py2_decode( self.NAME ) )
            if(self.ARTISTNUM == 1):
                self._get_artistinfo()
            images = self._get_file_list( self.CACHEDIR, do_filter=True )
            if images:
                self._set_artwork_from_dir( self.CACHEDIR, images )
                self.IMAGESFOUND = True
                got_one_artist_images = True
            if not self._download() and not got_one_artist_images:
                self._delete_folder( os.path.join( self.INFODIR ) )
                self._delete_folder( os.path.join( self.CACHEDIR ) )
                self._delete_folder( os.path.abspath( os.path.join( self.INFODIR, os.pardir ) ) )
                self._delete_folder( os.path.abspath( os.path.join( self.CACHEDIR, os.pardir ) ) )
        if not self.IMAGESFOUND:
            lw.log( ['no images found for any currently playing artists'] )
            if self.USEFALLBACK:
                lw.log( ['using fallback slideshow'] )
                lw.log( ['fallbackdir = ' + self.FALLBACKPATH] )
                self._set_artwork_from_dir( self.FALLBACKPATH, self._get_file_list( self.FALLBACKPATH ) )
            else:
                self._set_property( 'ArtistSlideshow.Image' )


    def _update_check_file( self, path, text, message ):
        success, loglines = writeFile( text, path )
        lw.log( loglines )
        if success:
            lw.log( [message] )


    def _upgrade_settings( self ):
        #this is where any code goes for one time upgrade routines related to settings
        checkfile = os.path.join( xbmc.translatePath( addon.getAddonInfo('profile') ), 'migrationcheck.nfo' )
        loglines, data = readFile( checkfile )
        lw.log( loglines )
        if '3.0.0' not in data:
            if getSettingBool( addon, 'localstorageonly' ):
                addon.setSetting( 'artist_image_storage', '2' )
            if getSettingBool( addon, 'localinfostorage' ):
                addon.setSetting( 'artist_info_storage', '1')
                addon.setSetting( 'local_info_path', addon.getSetting( 'local_artist_path' ))


    def _upgrade( self ):
        #this is where any code goes for one time upgrade routines
        checkfile = os.path.join( xbmc.translatePath( addon.getAddonInfo('profile') ), 'migrationcheck.nfo' )
        loglines, data = readFile( checkfile )
        lw.log( loglines )
        if '3.0.0' not in data:
            src_root = os.path.join( self.DATAROOT, 'ArtistSlideshow' )
            dst_root = os.path.join( self.DATAROOT, 'ArtistInformation')
            exists, loglines = checkPath( os.path.join( src_root, '' ) )
            if exists:
                try:
                    dirs, files = xbmcvfs.listdir( src_root )
                except OSError:
                    dirs = []
                except Exception as e:
                    lw.log( ['unexpected error getting directory list', e] )
                    dirs = []
                if dirs:
                    for thedir in dirs:
                        src = os.path.join( src_root, py2_decode( thedir ), self.IMGDB )
                        dst = os.path.join( dst_root, py2_decode( thedir ), self.IMGDB )
                        success, loglines = moveFile( src, dst )
                        lw.log( loglines )
            src_root = getSettingString( addon, 'local_artist_path' )
            dst_root = src_root
            exists, loglines = checkPath( os.path.join( src_root, '' ) )
            if exists:
                try:
                    dirs, files = xbmcvfs.listdir( src_root )
                except OSError:
                    dirs = []
                except Exception as e:
                    lw.log( ['unexpected error getting directory list', e] )
                    dirs = []
                if dirs:
                    for thedir in dirs:
                        src = os.path.join( src_root, py2_decode( thedir ), self.FANARTFOLDER, self.IMGDB )
                        dst = os.path.join( dst_root, py2_decode( thedir ), 'information', self.IMGDB )
                        success, loglines = moveFile( src, dst )
                        lw.log( loglines )
            self._update_check_file( checkfile, '3.0.0', 'preference conversion complete' )


    def _wait( self, wait_time ):
        waited = 0
        m_wait_time = wait_time*1000
        while( waited < m_wait_time ):
            xbmc.sleep(100)
            waited = waited + 100
            if self._playback_stopped_or_changed():
                self._clear_properties()
                return


lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
lw.log( ['debug logging set to %s' % str( logdebug )], xbmc.LOGNOTICE )
slideshow = Main()
lw.log( ['script stopped'], xbmc.LOGNOTICE )
