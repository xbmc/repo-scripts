#v.0.1.0

import os, time, sys, random, xbmc
from ..common.url import URL
from ..common.fileops import readFile, writeFile, deleteFile, checkPath
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json
try:
    import fanarttv_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''

class objectConfig():
    def __init__( self ):
        secsinweek = int( 7*24*60*60 )
        self.URL = 'http://webservice.fanart.tv/v3/music/'
        self.FILENAME = 'fanarttvartistimages.nfo'
        self.CACHETIMEFILENAME = 'fanarttvcachetime.nfo'
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int( 12*secsinweek )
        self.CACHEEXPIRE['high'] = int( 24*secsinweek )
        self.loglines = []
        self.JSONURL = URL( 'json' )


    def provides( self ):
        return ['images']
        
        
    def getImageList( self, img_params ):
        self.loglines = []
        url_params = {}
        images = []
        filepath = os.path.join( img_params.get( 'infodir', '' ), self.FILENAME )
        cachefilepath = os.path.join( img_params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        url = self.URL + img_params.get( 'mbid', '' )
        url_params['api_key'] = clowncar.decode( 'base64' )
        if img_params.get( 'clientapikey', False ):
            url_params['client_key'] = img_params.get( 'clientapikey', '' )
        json_data = self._get_data( filepath, cachefilepath, url, url_params )
        if json_data:
            image_list = json_data.get( 'artistbackground', [] )
            if img_params.get( 'getall', 'false' ) == 'true':
                image_list.extend( json_data.get( 'artistthumb', [] ) )
            for image in image_list:
                url = image.get( 'url', '' )
                if url:
                    images.append( url )
        if images == []:
            return [], self.loglines
        else: 
            return self._remove_exclusions( images, img_params.get( 'exclusionsfile' ) ), self.loglines


    def _get_cache_time( self, cachefilepath ):
        rawdata = ''
        self.loglines.append( 'getting the cache timeout information for fanarttv' )
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
        cachetime = random.randint( self.CACHEEXPIRE.get( 'low' ), self.CACHEEXPIRE.get( 'high' ) )
        success, wloglines = writeFile( str( cachetime ), cachefilepath )
        self.loglines.append( wloglines)
        return success


    def _remove_exclusions( self, image_list, exclusionfilepath ):
        images = []
        rloglines, rawdata = readFile( exclusionfilepath )
        self.loglines.extend( rloglines )
        if not rawdata:
            return image_list
        exclusionlist = rawdata.split()
        for image in image_list:
            for exclusion in exclusionlist:
                if not exclusion.startswith( xbmc.getCacheThumbName( image ) ):
                    images.append( image )
        return images


    def _update_cache( self, filepath, cachefilepath ):
        exists, cloglines = checkPath( filepath, False )
        self.loglines.extend( cloglines )
        if exists:
            if time.time() - os.path.getmtime( filepath ) < self._get_cache_time( cachefilepath ):
                self.loglines.append( 'cached artist info found for fanarttv' )
                return False
            else:
                self.loglines.append( 'outdated cached artist info found for fanarttv' )
                return self._put_cache_time( cachefilepath )
        else:
            self.loglines.append( 'no fanarttv cachetime file found, creating it' )
            return self._put_cache_time( cachefilepath )
