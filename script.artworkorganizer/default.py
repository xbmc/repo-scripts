import os, shutil, re, unicodedata
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString


def log(txt):
    message = 'script.artworkorganizer: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def clean_filename(tmp_filename):
    illegal_char = '<>:"/\|?*'
    for char in illegal_char:
        filename = tmp_filename.replace( char , '' )
    return filename


class Main:
    def __init__ ( self ):
        self._load_settings()
        self._init_variables()
        self._delete_directories()
        self._create_directories()
        if self.directoriescreated == 'true':
            self._copy_artwork()


    def _load_settings( self ):
        self.moviefanart = __addon__.getSetting( "moviefanart" )
        self.tvshowfanart = __addon__.getSetting( "tvshowfanart" )
        self.musicvideofanart = __addon__.getSetting( "musicvideofanart" )
        self.artistfanart = __addon__.getSetting( "artistfanart" )
        self.moviethumbs = __addon__.getSetting( "moviethumbs" )
        self.tvshowthumbs = __addon__.getSetting( "tvshowthumbs" )
        self.seasonthumbs = __addon__.getSetting( "seasonthumbs" )
        self.episodethumbs = __addon__.getSetting( "episodethumbs" )
        self.musicvideothumbs = __addon__.getSetting( "musicvideothumbs" )
        self.artistthumbs = __addon__.getSetting( "artistthumbs" )
        self.albumthumbs = __addon__.getSetting( "albumthumbs" )
        self.directory = __addon__.getSetting( "directory" )


    def _init_variables( self ):
        self.moviefanartdir = 'MovieFanart'
        self.tvshowfanartdir = 'TVShowFanart'
        self.musicvideofanartdir = 'MusicVideoFanart'
        self.artistfanartdir = 'ArtistFanart'
        self.moviethumbsdir = 'MovieThumbs'
        self.tvshowthumbsdir = 'TVShowThumbs'
        self.seasonthumbsdir = 'SeasonThumbs'
        self.episodethumbsdir = 'EpisodeThumbs'
        self.musicvideothumbsdir = 'MusicVideoThumbs'
        self.artistthumbsdir = 'ArtistThumbs'
        self.albumthumbsdir = 'AlbumThumbs'
        self.directoriescreated = 'true'
        self.dialog = xbmcgui.DialogProgress()
        if self.directory == '':
            self.directory = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ), __addonid__ )
        self.artworklist = []
        if self.moviefanart != '':
            self.moviefanartpath = os.path.join( self.directory, self.moviefanartdir )
            self.artworklist.append( self.moviefanartpath )
        if self.tvshowfanart != '':
            self.tvshowfanartpath = os.path.join( self.directory, self.tvshowfanartdir )
            self.artworklist.append( self.tvshowfanartpath )
        if self.musicvideofanart != '':
            self.musicvideofanartpath = os.path.join( self.directory, self.musicvideofanartdir )
            self.artworklist.append( self.musicvideofanartpath )
        if self.artistfanart != '':
            self.artistfanartpath = os.path.join( self.directory, self.artistfanartdir )
            self.artworklist.append( self.artistfanartpath )
        if self.moviethumbs != '':
            self.moviethumbspath = os.path.join( self.directory, self.moviethumbsdir )
            self.artworklist.append( self.moviethumbspath )
        if self.tvshowthumbs != '':
            self.tvshowthumbspath = os.path.join( self.directory, self.tvshowthumbsdir )
            self.artworklist.append( self.tvshowthumbspath )
        if self.seasonthumbs != '':
            self.seasonthumbspath = os.path.join( self.directory, self.seasonthumbsdir )
            self.artworklist.append( self.seasonthumbspath )
        if self.episodethumbs != '':
            self.episodethumbspath = os.path.join( self.directory, self.episodethumbsdir )
            self.artworklist.append( self.episodethumbspath )
        if self.musicvideothumbs != '':
            self.musicvideothumbspath = os.path.join( self.directory, self.musicvideothumbsdir )
            self.artworklist.append( self.musicvideothumbspath )
        if self.artistthumbs != '':
            self.artistthumbspath = os.path.join( self.directory, self.artistthumbsdir )
            self.artworklist.append( self.artistthumbspath )
        if self.albumthumbs != '':
            self.albumthumbspath = os.path.join( self.directory, self.albumthumbsdir )
            self.artworklist.append( self.albumthumbspath )


    def _delete_directories( self ):
        for path in self.artworklist:
            if xbmcvfs.exists( path ):
                try:
                    shutil.rmtree( path )
                except:
                    pass


    def _create_directories( self ):
        if not xbmcvfs.exists( self.directory ):
            try:
                xbmcvfs.mkdir( self.directory )
            except:
                self.directoriescreated = 'false'
                log( 'failed to create artwork directory' )
        for path in self.artworklist:
            try:
                xbmcvfs.mkdir( path )
            except:
                self.directoriescreated = 'false'
                log( 'failed to create directories' )


    def _copy_artwork( self ):
        self.dialog.create( __addonname__ )
        self.dialog.update(0)
        if not self.dialog.iscanceled():
            if self.moviefanart == 'true':
                self._copy_moviefanart()
        if not self.dialog.iscanceled():
            if self.tvshowfanart == 'true':
                self._copy_tvshowfanart()
        if not self.dialog.iscanceled():
            if self.musicvideofanart == 'true':
                self._copy_musicvideofanart()
        if not self.dialog.iscanceled():
            if self.artistfanart == 'true':
                self._copy_artistfanart()
        if not self.dialog.iscanceled():
            if self.moviethumbs == 'true':
                self._copy_moviethumbs()
        if not self.dialog.iscanceled():
            if self.tvshowthumbs == 'true':
                self._copy_tvshowthumbs()
        if not self.dialog.iscanceled():
            if self.seasonthumbs == 'true':
                self._copy_seasonthumbs()
        if not self.dialog.iscanceled():
            if self.episodethumbs == 'true':
                self._copy_episodethumbs()
        if not self.dialog.iscanceled():
            if self.musicvideothumbs == 'true':
                self._copy_musicvideothumbs()
        if not self.dialog.iscanceled():
            if self.artistthumbs == 'true':
                self._copy_artistthumbs()
        if not self.dialog.iscanceled():
            if self.albumthumbs == 'true':
                self._copy_albumthumbs()
        self.dialog.close()


    def _copy_moviefanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["fanart", "year"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32001) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findyear = re.search( '"year": ?(.*)', item )
            if findyear:
                year = (findyear.group(1))
            else:
                year = ""
            findartwork = re.search( '"fanart": ?"(.*?)",["\n]', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name + ' (' + year + ')'
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.moviefanartpath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy moviefanart' )
        log( 'moviefanart copied: %s' % count )


    def _copy_tvshowfanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["fanart"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32002) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartwork = re.search( '"fanart": ?"(.*?)",["\n]', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.tvshowfanartpath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy tvshowfanart' )
        log( 'tvshowfanart copied: %s' % count )


    def _copy_musicvideofanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["fanart", "artist"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32003) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartist = re.search( '"artist": ?"(.*?)",["\n]', item )
            if findartist:
                artist = (findartist.group(1))
            else:
                artist = ""
            findartwork = re.search( '"fanart": ?"(.*?)",["\n]', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = artist + ' - ' + name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.musicvideofanartpath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy musicvideofanart' )
        log( 'musicvideofanart copied: %s' % count )


    def _copy_artistfanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["fanart"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32004) + ': ' + str( count + 1 ) )
            findname = re.search( '"artist": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartwork = re.search( '"fanart": ?"(.*?)"', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.artistfanartpath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy artistfanart' )
        log( 'artistfanart copied: %s' % count )


    def _copy_moviethumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["thumbnail", "year"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32005) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findyear = re.search( '"year": ?(.*)', item )
            if findyear:
                year = (findyear.group(1))
            else:
                year = ""
            findartwork = re.search( '"thumbnail": ?"(.*?)",["\n]', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name + ' (' + year + ')'
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.moviethumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy moviethumb' )
        log( 'moviethumbs copied: %s' % count )


    def _copy_tvshowthumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["thumbnail"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32006) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.tvshowthumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy tvshowthumb' )
        log( 'tvshowthumbs copied: %s' % count )


    def _copy_seasonthumbs( self ):
        count = 0
        tvshowids = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            findid = re.search( '"tvshowid": ?(.*)', item )
            if findid:
                tvshowid = (findid.group(1))
                tvshowids.append(tvshowid)
        for tvshowid in tvshowids:
            processeditems = 0
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["thumbnail", "showtitle"], "tvshowid":%s }, "id": 1}' % tvshowid)
            json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
            totalitems = len( json_response )
            for item in json_response:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32006) + ': ' + str( count + 1 ) )
                findname = re.search( '"label": ?"(.*?)",["\n]', item )
                if findname:
                    name = (findname.group(1))
                else:
                    continue
                findtvshow = re.search( '"showtitle": ?"(.*?)",["\n]', item )
                if findtvshow:
                    tvshow = (findtvshow.group(1))
                else:
                    tvshow = ""
                findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
                if findartwork:
                    artwork = (findartwork.group(1))[:-4]
                    tmp_filename = tvshow + ' - ' + name
                    filename = clean_filename( tmp_filename )
                    for ext in (".dds", ".tbn"):
                        if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                            try:
                                count += 1
                                xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.seasonthumbspath, '%s%s' % (filename, ext) ) )
                                break
                            except:
                                count -= 1
                                log( 'failed to copy seasonthumb' )
        log( 'seasonthumbs copied: %s' % count )


    def _copy_episodethumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["thumbnail", "season", "episode", "showtitle"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32006) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findtvshow = re.search( '"showtitle": ?"(.*?)",["\n]', item )
            if findtvshow:
                tvshow = (findtvshow.group(1))
            else:
                tvshow = ""
            findseason = re.search( '"season": ?(.*?),["\n]', item )
            if findseason:
                season = (findseason.group(1))
            else:
                season = ""
            findepisode = re.search( '"episode": ?(.*?),["\n]', item )
            if findepisode:
                episode = (findepisode.group(1))
            else:
                episode = ""
            findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
            episodenumber = "s%.2d%.2d" % (int( season ), int( episode ))
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = tvshow + ' - ' + episodenumber + ' - ' + name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.episodethumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy episodethumb' )
        log( 'episodethumbs copied: %s' % count )


    def _copy_musicvideothumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["thumbnail", "artist"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32007) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartist = re.search( '"artist": ?"(.*?)",["\n]', item )
            if findartist:
                artist = (findartist.group(1))
            else:
                artist = ""
            findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = artist + ' - ' + name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.musicvideothumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy musicvideothumb' )
        log( 'musicvideothumbs copied: %s' % count )


    def _copy_artistthumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["thumbnail"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32008) + ': ' + str( count + 1 ) )
            findname = re.search( '"artist": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.artistthumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy artistthumb' )
        log( 'artistthumbs copied: %s' % count )


    def _copy_albumthumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["thumbnail", "artist"] }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        totalitems = len( json_response )
        for item in json_response:
            if self.dialog.iscanceled():
                log('script cancelled')
                return
            processeditems = processeditems + 1
            self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), __language__(32009) + ': ' + str( count + 1 ) )
            findname = re.search( '"label": ?"(.*?)",["\n]', item )
            if findname:
                name = (findname.group(1))
            else:
                continue
            findartist = re.search( '"artist": ?"(.*?)",["\n]', item )
            if findartist:
                artist = (findartist.group(1))
            else:
                artist = ""
            findartwork = re.search( '"thumbnail": ?"(.*?)"', item )
            if findartwork:
                artwork = (findartwork.group(1))[:-4]
                tmp_filename = artist + ' - ' + name
                filename = clean_filename( tmp_filename )
                for ext in (".dds", ".tbn"):
                    if xbmcvfs.exists( xbmc.translatePath( artwork + ext ) ):
                        try:
                            count += 1
                            xbmcvfs.copy( xbmc.translatePath( artwork + ext ), os.path.join( self.albumthumbspath, '%s%s' % (filename, ext) ) )
                            break
                        except:
                            count -= 1
                            log( 'failed to copy albumthumb' )
        log( 'albumthumbs copied: %s' % count )


if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()
log('script stopped')
