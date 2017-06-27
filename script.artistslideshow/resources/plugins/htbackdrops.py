#v.0.1.0

import os, time, sys, random, xbmc
import xml.etree.ElementTree as _xmltree
from ..common.url import URL
from ..common.fileops import readFile, writeFile, deleteFile, checkPath
try:
    import htbackdrops_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''


class objectConfig():
    def __init__( self ):
        self.QUERYURL = 'http://htbackdrops.org/api/%s/searchXML' % clowncar.decode( 'base64' )
        self.DOWNLOADURL = 'http://htbackdrops.org/api/%s/download/' % clowncar.decode( 'base64' )
        secsinweek = int( 7*24*60*60 )
        self.FILENAME = 'htbackdropsartistimages.nfo'
        self.CACHETIMEFILENAME = 'htbackdropscachetime.nfo'
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int( 12*secsinweek )
        self.CACHEEXPIRE['high'] = int( 24*secsinweek )
        self.loglines = []
        self.TEXTURL = URL( 'text' )


    def provides( self ):
        return ['images']
        
        
    def getImageList( self, img_params ):
        self.loglines = []
        url_params = {}
        images = []
        filepath = os.path.join( img_params.get( 'infodir', '' ), self.FILENAME )
        cachefilepath = os.path.join( img_params.get( 'infodir', '' ), self.CACHETIMEFILENAME )
        url_params['cid'] = '5'
        if img_params.get( 'mbid', False ):
            url_params['mbid'] = img_params.get( 'mbid', '' )
        elif img_params.get( 'artist', False ):
            url_params['default_operator'] = 'and'
            url_params['fields'] = 'title'
            url_params['keywords'] = img_params.get( 'artist', '').replace( '&','%26' ) 
        try:
           xmldata = _xmltree.fromstring( self._get_data( filepath, cachefilepath, url_params ) )
        except:
          return [], self.loglines
        match = False
        for element in xmldata.getiterator():
            if element.tag == "id":
                if match:
                    match = False
                else:
                    name = element.text
                    match = True
            elif element.tag == "aid" and match:
                if element.text == '1' or img_params.get( 'getall', 'false' ) == 'true':
                    images.append(self.DOWNLOADURL + name + '/fullsize')
                match = False
        if images == []:
            return [], self.loglines
        else: 
            return self._remove_exclusions( images, img_params.get( 'exclusionsfile', '' ) ), self.loglines


    def _get_cache_time( self, cachefilepath ):
        rawdata = ''
        self.loglines.append( 'getting the cache timeout information for htbackdrops' )
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
            success, uloglines, data = self.TEXTURL.Get( self.QUERYURL, params=url_params )
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
                self.loglines.append( 'cached artist info found for htbackdrops' )
                return False
            else:
                self.loglines.append( 'outdated cached artist info found for htbackdrops' )
                return self._put_cache_time( cachefilepath )
        else:
            self.loglines.append( 'no htbackdrops cachetime file found, creating it' )
            return self._put_cache_time( cachefilepath )
