# -*- coding: utf-8 -*-

import re

def parse_playlist( playlist, supported ):
    """ 
        Simple m3u playlist parser
        finds all Artist - Title and File path information from a m3u playlist
        Returns a list for Artist - Title and one for File path
    """
    track_info = []
    track_location = []
    for line in playlist:
        if line == "#EXTM3U\n":
            continue
        if re.search("#EXTINF:",line):
            s=re.search("#EXTINF:(.*?). (.*?$)",line, re.DOTALL)
            track_info.append( s.group(2).replace("\n", "") )
        elif re.search(".*(%s)" % supported, line):
            track_location.append( line.replace("\n", "") )
    return track_info, track_location
