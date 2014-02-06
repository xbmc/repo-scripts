# -*- coding: utf-8 -*-

import re, sys, os
import xbmcvfs

BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils

def parse_m3u( path, supported ):
    """ 
        Simple m3u playlist parser
        finds all Artist - Title and File path information from a m3u playlist
        Returns a list for Artist - Title and one for File path
    """
    playlist_file = xbmcvfs.File( path, 'rb')
    saved_playlist = playlist_file.read().splitlines()
    playlist_file.close()
    utils.log( "Finished Reading Music Playlist" )
    track_info = []
    track_location = []
    for line in saved_playlist:
        if line == "#EXTM3U\n":
            continue
        if re.search("#EXTINF:",line):
            s=re.search("#EXTINF:(.*?). (.*?$)",line, re.DOTALL)
            track_info.append( s.group(2).replace("\n", "") )
        elif re.search(".*(%s)" % supported, line):
            track_location.append( line.replace("\n", "") )
    return track_info, track_location

def parse_pls( path, supported ):
    utils.log( "parse_pls() Started" )
    file_list = []
    playlist_file = xbmcvfs.File( path, 'rb')
    lines = playlist_file.read().splitlines()
    utils.log( "Finished Reading Playlist" )
    # parse lines
    if lines != None:
        for line in lines:
            # search for the file path
            match = re.match( "^[ \\t]*file[0-9]*[ \\t]*=[ \\t]*(.*$)", line, flags=re.IGNORECASE )
            if match != None:
                if match.group( 1 ) != None:
                    # file path found, it's saved in the second match group
                    # output the file path to list
                    if re.search(".*(%s)" % supported, match.group( 1 ) ):
                        file_list.append( match.group( 1 ) )
    else:
        utils.log( "Playlist is empty" )
    return file_list