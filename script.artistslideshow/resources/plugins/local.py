#v.0.1.0

import os
import xml.etree.ElementTree as _xmltree
from ..common.fileops import readFile, checkPath
from ..common.fix_utf8 import smartUTF8


class objectConfig():
    def __init__( self ):
        self.loglines = []
        self.BIOFILEPATH = os.path.join( 'override', 'artistbio.nfo' )
        self.ALBUMFILEPATH = os.path.join( 'override', 'artistsalbums.nfo' )
        self.SIMILARFILEPATH = os.path.join( 'override', 'artistsimilar.nfo' )


    def provides( self ):
        return ['bio', 'albums', 'similar', 'mbid']
        

    def getAlbumList( self, album_params ):
        self.loglines = []
        albums = []
        filepath = os.path.join( album_params.get( 'localartistdir', '' ), self.ALBUMFILEPATH )
        local_path = os.path.join( album_params.get( 'localartistdir', ''), smartUTF8( album_params.get( 'artist', '' ) ).decode('utf-8'), 'override' )
        self.loglines.append( 'checking ' + filepath )
        rloglines, rawxml = readFile( filepath )
        self.loglines.extend( rloglines )
        if rawxml:
            xmldata = _xmltree.fromstring( rawxml )
        else:
            return [], self.loglines
        for element in xmldata.getiterator():
            if element.tag == "name":
                name = element.text
                name.encode('ascii', 'ignore')
            elif element.tag == "image":
                image_text = element.text
                if not image_text:
                    image = ''
                else:
                    image = os.path.join( local_path, 'albums', image_text )
                albums.append( ( name , image ) )
        if albums == []:
            self.loglines.append( 'no albums found in local xml file' )
            return [], self.loglines
        else:
            return albums, self.loglines
        
        
    def getBio( self, bio_params ):
        self.loglines = []
        bio = ''
        filepath = os.path.join( bio_params.get( 'localartistdir', '' ), self.BIOFILEPATH )
        self.loglines.append( 'checking ' + filepath )
        loglines, rawxml = readFile( filepath )
        self.loglines.extend( loglines )
        if rawxml:
            xmldata = _xmltree.fromstring( rawxml )
        else:
            return '', self.loglines
        for element in xmldata.getiterator():
            if element.tag == "content":
                bio = element.text
        if not bio:
            self.loglines.append( 'no %s found in local xml file' % item )
            return '', self.loglines
        else:
            return bio, self.loglines


    def getMBID( self, mbid_params ):
        self.loglines = []
        filename = os.path.join( mbid_params.get( 'infodir', '' ), 'musicbrainz.nfo' )
        exists, cloglines = checkPath( filename, False )
        self.loglines.extend( cloglines )
        if exists:
            cloglines, rawdata = readFile( filename )
            self.loglines.extend( cloglines )
            return rawdata.rstrip( '\n' ), self.loglines
        else:
            return '', self.loglines


    def getSimilarArtists( self, sim_params ):
        self.loglines = []
        similar_artists = []
        filepath = os.path.join( sim_params.get( 'localartistdir', '' ), self.SIMILARFILEPATH )
        local_path = os.path.join( sim_params.get( 'localartistdir', '' ), smartUTF8( sim_params.get( 'artist', '' ) ).decode( 'utf-8' ), 'override' )
        self.loglines.append( 'checking ' + filepath )
        rloglines, rawxml = readFile( filepath )
        self.loglines.extend( rloglines )
        if rawxml:
            xmldata = _xmltree.fromstring( rawxml )
        else:
            return [], self.loglines
        for element in xmldata.getiterator():
            if element.tag == "name":
                name = element.text
                name.encode('ascii', 'ignore')
            elif element.tag == "image":
                image_text = element.text
                if not image_text:
                    image = ''
                else:
                    image = os.path.join( local_path, 'similar', image_text )
                similar_artists.append( ( name , image ) )
        if similar_artists == []:
            self.loglines.append( 'no similar artists found in local xml file' )
            return [], self.loglines
        else:
            return similar_artists, self.loglines
