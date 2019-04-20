#v.0.1.0

import os, time, random
import xml.etree.ElementTree as _xmltree
from ..common.url import URL
from ..common.fileops import readFile, writeFile, checkPath
try:
    import lastfm_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''


class objectConfig():
    def __init__( self ):
        secsinweek = int( 7*24*60*60 )
        self.ARTISTPARAMS = {'autocorrect':'1', 'api_key':clowncar.decode( 'base64' ), 'method':'artist.getInfo'}
        self.ALBUMPARAMS = {'autocorrect':'1', 'api_key':clowncar.decode( 'base64' ), 'method':'artist.getTopAlbums'}
        self.SIMILARPARAMS = {'autocorrect':'1', 'api_key':clowncar.decode( 'base64' ), 'limit':'50', 'method':'artist.getSimilar'}
        self.URL = 'http://ws.audioscrobbler.com/2.0/'
        self.BIOFILENAME = 'lastfmartistbio.nfo'
        self.ALBUMFILENAME = 'lastfmartistalbums.nfo'
        self.SIMILARFILENAME = 'lastfmartistsimilar.nfo'
        self.CACHETIMEFILENAME = 'lastfmcachetime.nfo'
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int( 12*secsinweek )
        self.CACHEEXPIRE['high'] = int( 24*secsinweek )
        self.loglines = []
        self.TEXTURL = URL( 'text' )


    def provides( self ):
        return ['bio', 'albums', 'similar', 'mbid']


    def getAlbumList( self, album_params ):
        self.loglines = []
        url_params = {}
        albums = []
        filepath = os.path.join( album_params.get( 'infodir', '' ), self.ALBUMFILENAME )
        cachefilepath = os.path.join( album_params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        additionalparams = {'artist': album_params.get( 'artist', '' )}  
        url_params = dict( self.ALBUMPARAMS.items() + additionalparams.items() )
        self.loglines.append( 'trying to get artist albums from ' + self.URL )
        try:
           xmldata = _xmltree.fromstring( self._get_data( filepath, cachefilepath, url_params ) )
        except:
          return [], self.loglines
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
                    albums.append( ( name , image ) )
                    match = False
        if albums == []:
            self.loglines.append( 'no album info found in lastfm xml file' )
            return [], self.loglines
        else:
            return albums, self.loglines

        
    def getBio( self, bio_params ):
        self.loglines = []
        url_params = {}
        bio = ''
        filepath = os.path.join( bio_params.get( 'infodir', '' ), self.BIOFILENAME )
        cachefilepath = os.path.join( bio_params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        additionalparams = {'artist': bio_params.get( 'artist', '' ), 'lang':bio_params.get( 'lang', '' )}  
        url_params = dict( self.ARTISTPARAMS.items() + additionalparams.items() )
        self.loglines.append( 'trying to get artist bio from ' + self.URL )
        try:
           xmldata = _xmltree.fromstring( self._get_data( filepath, cachefilepath, url_params ) )
        except:
          return '', self.loglines
        for element in xmldata.getiterator():
            if element.tag == "content":
                bio = element.text
        if not bio:
            self.loglines.append( 'no bio found in lastfm xml file' )
            return '', self.loglines
        else:
            return bio, self.loglines
        

    def getSimilarArtists( self, sim_params ):
        self.loglines = []
        url_params = {}
        similar_artists = []
        filepath = os.path.join( sim_params.get( 'infodir', '' ), self.SIMILARFILENAME )
        cachefilepath = os.path.join( sim_params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        additionalparams = {'artist': sim_params.get( 'artist', '' )}  
        url_params = dict( self.SIMILARPARAMS.items() + additionalparams.items() )
        self.loglines.append( 'trying to get similar artists from ' + self.URL )
        try:
           xmldata = _xmltree.fromstring( self._get_data( filepath, cachefilepath, url_params ) )
        except:
          return [], self.loglines
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
                    similar_artists.append( ( name , image ) )
                    match = False
        if similar_artists == []:
            self.loglines.append( 'no similar artists info found in lastfm xml file' )
            return [], self.loglines
        else:
            return similar_artists, self.loglines


    def getMBID( self, mbid_params ):
        self.loglines = []
        filepath = os.path.join( mbid_params.get( 'infodir', '' ), self.BIOFILENAME )
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            rloglines, rawxml = readFile( filepath )
            self.loglines.extend( rloglines )
            try:
                xmldata = _xmltree.fromstring( rawxml )
            except:
                self.loglines.append( 'error reading musicbrainz ID from ' + filepath )
                return '', self.loglines
            for element in xmldata.getiterator():
                if element.tag == "mbid":
                    return element.text, self.loglines
            self.loglines.append( 'no mbid found in' + filepath )
            return '', self.loglines
        else:
            return '', self.loglines


    def _get_cache_time( self, cachefilepath ):
        rawdata = ''
        self.loglines.append( 'getting the cache timeout information for last.fm' )
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


    def _get_data( self, filepath, cachefilepath, url_params ):
        rawxml = ''
        if self._update_cache( filepath, cachefilepath ):
            success, uloglines, data = self.TEXTURL.Get( self.URL, params=url_params )
            self.loglines.extend( uloglines )
            if success:
                success, wloglines = writeFile( data.encode( 'utf-8' ), filepath )
                self.loglines.extend( wloglines )
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            rloglines, rawxml = readFile( filepath )
            self.loglines.extend( rloglines )
        return rawxml


    def _put_cache_time( self, cachefilepath ):
        self.loglines.append( 'writing out the cache timeout information for last.fm' )
        cachetime = random.randint( self.CACHEEXPIRE['low'], self.CACHEEXPIRE['high'] )
        success, wloglines = writeFile( str( cachetime ), cachefilepath )
        self.loglines.append( wloglines)
        return success


    def _update_cache( self, filepath, cachefilepath ):
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            if time.time() - os.path.getmtime( filepath ) < self._get_cache_time( cachefilepath ):
                self.loglines.append( 'cached artist info found for last.fm' )
                return False
            else:
                self.loglines.append( 'outdated cached artist info found for last.fm' )
                return self._put_cache_time( cachefilepath )
        else:
            self.loglines.append( 'no last.fm cachetime file found, creating it' )
            return self._put_cache_time( cachefilepath )
