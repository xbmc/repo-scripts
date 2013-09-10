# -*- coding: utf-8 -*-

__script__ = "Cinema Experience"
__scriptID__ = "script.cinema.experience"
__modname__ = "trailer_downloader.py"

import sys
import os
import xbmcgui
import xbmc
import xbmcaddon
import traceback, threading
import xbmcvfs

logmessage = "[ " + __scriptID__ + " ] - [ " + __modname__ + " ]"
_A_ = xbmcaddon.Addon( __scriptID__ )
# language method
_L_ = _A_.getLocalizedString
trailer_settings   = sys.modules["__main__"].trailer_settings

from urllib import quote_plus
from random import shuffle, random

BASE_CURRENT_SOURCE_PATH = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ), os.path.basename( _A_.getAddonInfo('path') ) )
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( _A_.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from download import download
from ce_playlist import _get_trailers

downloaded_trailers = []

def downloader( mpaa, genre, equivalent_mpaa ):
    movie = ""
    trailer_list = []
    xbmc.log( "%s - Starting Trailer Downloader" % logmessage, level=xbmc.LOGNOTICE )
    genre = genre.replace( "_", " / " )
    trailer_list = _download_trailers( equivalent_mpaa, mpaa, genre, movie )
    save_download_list( trailer_list )

def save_download_list( download_trailers ):
    xbmc.log( "%s - Saving List of Downloaded Trailers" % logmessage, level=xbmc.LOGNOTICE )
    success = False
    try:
        # base path to watched file
        base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloaded_trailers.txt" )
        # if the path to the source file does not exist create it
        if ( not os.path.isdir( os.path.dirname( base_path ) ) ):
            os.makedirs( os.path.dirname( base_path ) )
        # open source path for writing
        file_object = open( base_path, "w" )
        if download_trailers:
            for trailer in download_trailers:
                try:# write list
                    file_object.write( repr( trailer[ 2 ] ) )
                    success = True
                except:
                    file_object.write( "" )
                    success = False
        else:
            file_object.write( "" )
        # close file object
        file_object.close()
    except:
        traceback.print_exc()
    if not success:
        try:
            xbmc.log( "%s - Removing List of Downloaded Trailers" % logmessage, level=xbmc.LOGNOTICE )
            if ( os.path.isfile( base_path ) ):
                os.remove( base_path )
        except:
            xbmc.log( "%s - Error Trying to Remove List of Downloaded Trailers" % logmessage, level=xbmc.LOGNOTICE )
    
def _download_trailers( equivalent_mpaa, mpaa, genre, movie ):
    updated_trailers = []
    xbmc.log( "%s - Downloading Trailers: %s Trailers" % ( logmessage, trailer_settings[ "trailer_count" ] ), level=xbmc.LOGNOTICE )
    temp_destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "temp_trailers" ).replace( "\\\\", "\\" )
    if not xbmcvfs.exists( temp_destination ):
        xbmcvfs.mkdir( temp_destination )
    trailers = _get_trailers(  items=trailer_settings[ "trailer_count" ],
                     equivalent_mpaa=equivalent_mpaa,
                                mpaa=mpaa,
                               genre=genre,
                               movie=movie,
                                mode="download"
                            )
    for trailer in trailers:
        updated_trailer = {}
        success = False
        destination = ""   
        thumb = ""
        xbmc.log( "%s - Attempting To Download Trailer: %s" % ( logmessage, trailer[ 1 ] ), level=xbmc.LOGNOTICE )
        filename, ext = os.path.splitext( os.path.basename( (trailer[ 2 ].split("|")[0] ).replace( "?","" ) ) )
        filename = filename + "-trailer" + ext
        file_path = os.path.join( trailer_settings[ "trailer_download_folder" ], filename ).replace( "\\\\", "\\" )
        # check to see if trailer is already downloaded
        if os.path.isfile( file_path ):
            success = True
            destination = file_path
            thumb = os.path.splitext( file_path )[0] + ".tbn"
        else:
            success, destination = download( trailer[ 2 ], temp_destination, file_tag="-trailer" )
            tsuccess, thumb = download( trailer[ 3 ], temp_destination, file_tag="-trailer", new_name=filename, extension=".tbn" )
        if success:
            xbmc.log( "%s - Successfully Download Trailer: %s" % ( logmessage, trailer[ 1 ] ), level=xbmc.LOGNOTICE )
            updated_trailer[ 0 ] = trailer[ 0 ]
            updated_trailer[ 1 ] = trailer[ 1 ]
            updated_trailer[ 2 ] = destination
            updated_trailer[ 3 ] = thumb
            updated_trailer[ 4 ] = trailer[ 4 ]
            updated_trailer[ 5 ] = trailer[ 5 ]
            updated_trailer[ 6 ] = trailer[ 6 ]
            updated_trailer[ 7 ] = trailer[ 7 ]
            updated_trailer[ 8 ] = trailer[ 8 ]
            updated_trailer[ 9 ] = trailer[ 9 ]
            updated_trailer[ 10 ] = trailer[ 10 ]
            updated_trailer[ 11 ] = trailer[ 11 ]
            _create_nfo_file( updated_trailer, os.path.join( temp_destination, filename).replace( "\\\\", "\\" ) )
        else:
            xbmc.log( "%s - Failed to Download Trailer: %s" % ( logmessage, trailer[ 1 ] ), level=xbmc.LOGNOTICE )
            updated_trailer=[]
        xbmcvfs.copy( os.path.join( temp_destination, filename ).replace( "\\\\", "\\"), os.path.join( trailer_settings[ "trailer_download_folder" ], filename ).replace( "\\\\", "\\" ) )
        xbmcvfs.copy( os.path.join( temp_destination, os.path.splitext( filename )[0] + ".tbn" ).replace( "\\\\", "\\"), os.path.join( trailer_settings[ "trailer_download_folder" ], os.path.splitext( filename )[0] + ".tbn"  ).replace( "\\\\", "\\" ) )
        xbmcvfs.copy( os.path.join( temp_destination, os.path.splitext( filename )[0] + ".nfo" ).replace( "\\\\", "\\"), os.path.join( trailer_settings[ "trailer_download_folder" ], os.path.splitext( filename )[0] + ".nfo" ).replace( "\\\\", "\\" ) )
        xbmcvfs.delete( os.path.join( temp_destination, filename ).replace( "\\\\", "\\") )
        xbmcvfs.delete( os.path.join( temp_destination, os.path.splitext( filename )[0] + ".tbn" ).replace( "\\\\", "\\") )
        xbmcvfs.delete( os.path.join( temp_destination, os.path.splitext( filename )[0] + ".nfo" ).replace( "\\\\", "\\") )
        updated_trailers += [ updated_trailer ]
    return updated_trailers

def _create_nfo_file( trailer, trailer_nfopath ):
    '''
                path=trailer[ 2 ],
                genre=trailer[ 9 ],
                title=trailer[ 1 ],
                thumbnail=trailer[ 3 ],
                plot=trailer[ 4 ],
                runtime=trailer[ 5 ],
                mpaa=trailer[ 6 ],
                release_date=trailer[ 7 ],
                studio=trailer[ 8 ],
                director=trailer[ 11 ]
    '''
    xbmc.log( "%s - Creating Trailer NFO file" % logmessage, level=xbmc.LOGNOTICE )
    # set quality, we do this since not all resolutions have trailers
    quality = trailer_settings[ "trailer_quality" ]
    # set movie info
    nfoSource = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<movieinfo id="%s">
    <title>%s</title>
    <quality>%s</quality>
    <runtime>%s</runtime>
    <releasedate>%s</releasedate>
    <mpaa>%s</mpaa>
    <genre>%s</genre>
    <studio>%s</studio>
    <director>%s</director>
    <cast>%s</cast>
    <plot>%s</plot>
    <thumb>%s</thumb>
</movieinfo>
""" % ( trailer[ 0 ], trailer[ 1 ], quality, trailer[ 5 ], trailer[ 7 ], trailer[ 6 ], trailer[ 9 ], trailer[ 8 ], trailer[ 11 ], "", trailer[ 4 ], trailer[ 3 ] )
    # save nfo file
    return _save_nfo_file( nfoSource, trailer_nfopath )

def _save_nfo_file( nfoSource, trailer_nfopath ):
    xbmc.log( "%s - Saving Trailer NFO file" % logmessage, level=xbmc.LOGNOTICE )
    destination = os.path.splitext( trailer_nfopath )[0] + ".nfo"
    try:
        # open source path for writing
        file_object = open( destination.encode( "utf-8" ), "w" )
        # write xmlSource
        file_object.write( nfoSource.encode( "utf-8" ) )
        # close file object
        file_object.close()
        # return successful
        return True
    except Exception, e:
        # oops, notify user what error occurred
        xbmc.log( "%s - %s" % ( logmessage, str( e ) ), xbmc.LOGERROR )
        # return failed
        return False

if __name__ == "__main__":
    try:
        if sys.argv[1]:
            mpaa, genre = sys.argv[1].replace( "mpaa=", "" ).replace( "genre=", "").replace( "equivalent_mpaa=", "" ).split(";")
            _genre = genre.replace( "_", " / " )
            downloader( mpaa, _genre, equivalent_mpaa )
        else:
            xbmc.log( "%s - No Arguments sent " % logmessage, level=xbmc.LOGNOTICE )
    except:
        traceback.print_exc()
        xbmc.log( "%s - No Arguments sent " % logmessage, level=xbmc.LOGNOTICE )
 