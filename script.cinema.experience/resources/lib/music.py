# -*- coding: utf-8 -*-

import re, sys, os
import xbmcvfs

BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils
    
class parse():
    def __init__( self ):
        pass

    def load_file( self, path ):
        playlist_file = xbmcvfs.File( path, 'rb')
        _playlist = playlist_file.read()
        playlist_file.close()
        utils.log( "Finished Reading Music Playlist" )
    
    def parse_m3u( self, path, supported ):
        utils.log( "parse_m3u() Started" )
        file_list = []
        lines = self.load_file( path ).splitlines()
        if lines != None:
            for line in lines:
                if line == "#EXTM3U\n":
                    continue
                if re.search( ".*(%s)" % supported, line ):
                    file_list.append( line.replace("\n", "") )
        else:
            utils.log( "Playlist is empty" )
        return file_list

    def parse_pls( self, path, supported ):
        utils.log( "parse_pls() Started" )
        file_list = []
        lines = self.load_file( path ).splitlines()
        # parse lines
        if lines != None:
            for line in lines:
                # search for the file path
                match = re.match( "^[ \\t]*file[0-9]*[ \\t]*=[ \\t]*(.*$)", line, flags=re.IGNORECASE )
                if match != None:
                    if match.group( 1 ) != None:
                        # file path found, it's saved in the second match group
                        # output the file path to list
                        if re.search( ".*(%s)" % supported, match.group( 1 ) ):
                            file_list.append( match.group( 1 ).replace("\n", "") )
        else:
            utils.log( "Playlist is empty" )
        return file_list
        
    def parse_asf( self, path, supported ):
        utils.log( "parse_asf() Started" )
        lines = self.load_file( path ).split("\n")
        # parse lines
        if lines != None:
            for line in lines:
                # search for the file path
                if line.startswith( "Ref" ) == True:
                    list = line.split( "=", 1 )
                    tmp = list[ 1 ].strip()
                    if tmp.endswith( "?MSWMExt=.asf" ):
                        if re.search( ".*(%s)" % supported, tmp ):
                            file_list.append( tmp.replace( "http", "mms" ) )
                    else:
                        if re.search( ".*(%s)" % supported, tmp ):
                            file_list.append( tmp )
        else:
            utils.log( "Playlist is empty" )
        return file_list
        
    def parse_ram( self, path, supported ):
        utils.log( "parse_ram() Started" )
        file_list = []
        lines = self.load_file( path ).splitlines()
        # parse lines
        if lines != None:
            for line in lines:
                # search for the file path
                if not line.startswith("#") and len(line) > 0:
                    tmp = line.strip()
                    if( len( tmp ) > 0 ):
                        if re.search( ".*(%s)" % supported, line ):
                            file_list.append( line.replace("\n", "").strip() )
        else:
            utils.log( "Playlist is empty" )
        return file_list    
        

    
    