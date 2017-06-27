#v.0.1.1

import os, time, sys, random, xbmc
from ..common.url import URL
from ..common.fileops import readFile, writeFile, deleteFile, checkPath
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json
try:
    import theaudiodb_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''



class objectConfig():
    def __init__( self ):
        url = 'http://www.theaudiodb.com/api/v1/json/%s/' % clowncar.decode( 'base64' )
        secsinweek = int( 7*24*60*60 )
        self.ARTISTMBIDURL = url + 'artist-mb.php'
        self.ARTISTSEARCHURL = url + 'search.php'
        self.ARTISTTADBIDURL = url + 'artist.php'
        self.ALBUMURL = url + 'album.php'
        self.ALBUMSEARCHURL = url + 'searchalbum.php'
        self.ARTISTFILENAME = 'theaudiodbartistbio.nfo'
        self.ALBUMFILENAME = 'theaudiodbartistsalbums.nfo'
        self.IDFILENAME = 'theaudiodbid.nfo'
        self.CACHETIMEFILENAME = 'theaudiodbcachetime.nfo'
        self.ALBUMCACHETIMEFILENAME = 'theaudiodbalbumcachetime.nfo'
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int( 12*secsinweek )
        self.CACHEEXPIRE['high'] = int( 24*secsinweek )
        self.loglines = []
        self.JSONURL = URL( 'json' )


    def provides( self ):
        return ['bio', 'albums', 'images', 'mbid']


    def getAlbumList( self, album_params ):
        self.loglines = []
        self._set_filepaths( album_params )
        url_params = {}
        albums = []
        json_data = ''
        url, url_params = self._determine_url( album_params, '', self.ALBUMURL, self.ALBUMSEARCHURL )
        if url:
            json_data = self._get_data( self.ALBUMFILEPATH, self.ALBUMCACHEFILEPATH, url, url_params )
        if json_data:
            rawalbums = json_data.get( 'album' )
            if rawalbums is not None:
                for album in rawalbums:
                    albums.append( ( album.get( 'strAlbum', '' ), album.get( 'strAlbumThumb', '' ) ) )
        return albums, self.loglines

        
    def getBio( self, bio_params ):
        self.loglines = []
        self._set_filepaths( bio_params )
        url_params = {}
        bio = ''
        json_data = ''
        url, url_params = self._determine_url( bio_params, self.ARTISTMBIDURL, self.ARTISTTADBIDURL, self.ARTISTSEARCHURL )
        if url:
            json_data = self._get_data( self.ARTISTFILEPATH, self.CACHEFILEPATH, url, url_params )
            self.loglines.extend( ['the json data is:', json_data] )
        if json_data:
            artist = json_data.get( 'artists' )
            if artist is not None:
                bio = artist[0].get( 'strBiography' + bio_params.get( 'lang', '' ).upper(), '' )
        return bio, self.loglines
        
        
    def getImageList( self, img_params ):
        self.loglines = []
        self._set_filepaths( img_params )
        url_params = {}
        images = []
        json_data = ''
        url, url_params = self._determine_url( img_params, self.ARTISTMBIDURL, self.ARTISTTADBIDURL, self.ARTISTSEARCHURL )
        if url:
            json_data = self._get_data( self.ARTISTFILEPATH, self.CACHEFILEPATH, url, url_params )
        if json_data:
            artist = json_data.get( 'artists' )
            if artist is not None:
                for i in range( 1, 3 ):
                    if i == 1:
                        num = ''
                    else:
                        num = str( i )
                    image = artist[0].get( 'strArtistFanart' + num, '' )
                    if image:
                        images.append( image )
        if images == []:
            return [], self.loglines
        else: 
            return self._remove_exclusions( images ), self.loglines


    def getMBID( self, mbid_params ):
        self.loglines = []
        self._set_filepaths( mbid_params )
        exists, cloglines = checkPath( self.ARTISTFILEPATH, False )
        self.loglines.extend( cloglines )
        if exists:
            cloglines, rawdata = readFile( self.ARTISTFILEPATH )
            self.loglines.extend( cloglines )
            try:
                json_data = _json.loads( rawdata )
            except ValueError:
                self.loglines.append( 'no valid JSON data returned from ' + self.ARTISTFILEPATH )
                return '', self.loglines
            self.loglines.append( 'musicbrainz ID found in %s file' % self.ARTISTFILEPATH )
            try:
                return json_data.get( 'artists' )[0].get( 'strMusicBrainzID', '' ), self.loglines
            except TypeError:
                self.loglines.append( 'error reading musicbrainz ID from ' + self.ARTISTFILEPATH )
                return '', self.loglines
        else:
            return '', self.loglines
        

    def _determine_url( self, params, mbidurl, tadbidurl, nameurl ):
        url_params = {}
        if mbidurl:
            mbid = params.get( 'mbid', '' )
            if mbid:
                url_params['i'] = params.get( 'mbid', '' )
                self.loglines.append( 'found mbid, using mbidurl to get information from theaudiodb' )
                return mbidurl, url_params
        if tadbidurl:
            tadbid = self._get_audiodbid( )
            if tadbid:
                url_params['i'] = tadbid
                self.loglines.append( 'found tadbid, using tadbidurl to get information from theaudiodb' )
                return tadbidurl, url_params
        if nameurl:
            url_params['s'] = params.get( 'artist', '' ) 
            self.loglines.append( 'no mbid or tadbid found, using artist name to get information from theaudiodb' )
            return nameurl, url_params
        return '', ''


    def _get_audiodbid( self ):
        audiodbid = ''
        exists, cloglines = checkPath( self.IDFILEPATH, False )
        self.loglines.extend( cloglines )
        if not exists:
            exists, cloglines = checkPath( self.ARTISTFILEPATH, False )
            self.loglines.extend( cloglines )
            if exists:
                rloglines, rawdata = readFile( self.ARTISTFILEPATH )
                self.loglines.extend( rloglines )
                try:
                    gotData = True
                    json_data = _json.loads( rawdata )
                except ValueError:
                    self.loglines.append( 'no valid JSON data returned from theaudiodb.com, setting artist to None' )
                    gotData = False
                if gotData:
                    artist = json_data.get( 'artists' )
                else:
                    artist = None
                if artist is not None:
                    audiodbid = artist[0].get( 'idArtist', '' )
                if audiodbid:
                    success, wloglines = writeFile( audiodbid, self.IDFILEPATH )
                    self.loglines.extend( wloglines )
        rloglines, audiodbid = readFile( self.IDFILEPATH )
        self.loglines.extend( rloglines )
        return audiodbid    


    def _get_cache_time( self, cachefilepath ):
        rawdata = ''
        self.loglines.append( 'getting the cache timeout information for theaudiodb' )
        exists, cloglines = checkPath( cachefilepath, False )
        self.loglines.extend( cloglines )
        if exists:
            success = True
        else:
            success = self._put_cache_time( cachefilepath )
        if success:
            rloglines, rawdata = readFile( cachefilepath ) 
            self.loglines.extend( rloglines )
        try:
            cachetime = int( rawdata )
        except ValueError:
            cachetime = 0
        return cachetime


    def _get_data( self, filepath, cachefilepath, url, url_params ):
        json_data = ''
        if self._update_cache( filepath, cachefilepath ):
            success, uloglines, json_data = self.JSONURL.Get( url, params=url_params )
            self.loglines.extend( uloglines )
            if success:
                success, wloglines = writeFile( _json.dumps( json_data ).encode( 'utf-8' ), filepath )
                self.loglines.extend( wloglines )
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            self._get_audiodbid( ) # this is to generate the id file if it doesn't exist
            rloglines, rawdata = readFile( filepath )
            self.loglines.extend( rloglines )
            try:
                json_data = _json.loads( rawdata )
            except ValueError:
                success, dloglines = deleteFile( filepath )
                self.loglines.extend( dloglines )
                self.loglines.append( 'Deleted old cache file. New file will be download on next run.' )
                json_data = ''
        return json_data


    def _put_cache_time( self, cachefilepath ):
        cachetime = random.randint( self.CACHEEXPIRE['low'], self.CACHEEXPIRE['high'] )
        success, wloglines = writeFile( str( cachetime ), cachefilepath )
        self.loglines.append( wloglines)
        return success


    def _remove_exclusions( self, image_list ):
        images = []
        rloglines, rawdata = readFile( self.EXCLUSIONFILEPATH )
        self.loglines.extend( rloglines )
        if not rawdata:
            return image_list
        exclusionlist = rawdata.split()
        for image in image_list:
            for exclusion in exclusionlist:
                if not exclusion.startswith( xbmc.getCacheThumbName( image ) ):
                    images.append( image )
        return images


    def _set_filepaths( self, params ):
        self.ARTISTFILEPATH = os.path.join( params.get( 'infodir', '' ), self.ARTISTFILENAME )
        self.CACHEFILEPATH = os.path.join( params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        self.ALBUMCACHEFILEPATH = os.path.join( params.get( 'infodir', '' ), self.ALBUMCACHETIMEFILENAME )
        self.ALBUMFILEPATH = os.path.join( params.get( 'infodir', '' ), self.ALBUMFILENAME )
        self.IDFILEPATH = os.path.join( params.get( 'infodir', '' ), self.IDFILENAME )
        self.EXCLUSIONFILEPATH = params.get( 'exclusionsfile', '' )


    def _update_cache( self, filepath, cachefilepath ):
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            if time.time() - os.path.getmtime( filepath ) < self._get_cache_time( cachefilepath ):
                self.loglines.append( 'cached info found for theaudiodb' )
                return False
            else:
                self.loglines.append( 'outdated cached info found for theaudiodb' )
                return self._put_cache_time( cachefilepath )
        else:
            self.loglines.append( 'no theaudiodb cachetime file found, creating it' )
            return self._put_cache_time( cachefilepath )