# -*- coding: utf-8 -*-
import sys, os, traceback, threading
import xbmcgui, xbmc, xbmcaddon, xbmcvfs
from urllib import quote_plus
from random import shuffle, random

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from download import download
from ce_playlist import _get_trailers
import utils

downloaded_trailers = []

def downloader( mpaa, genre, equivalent_mpaa ):
    movie = ""
    download_trailers = []
    utils.log( "Starting Trailer Downloader", xbmc.LOGNOTICE )
    genre = genre.replace( "_", " / " )
    download_trailers = _download_trailers( equivalent_mpaa, mpaa, genre, movie )
    utils.log( "Saving List of Downloaded Trailers", xbmc.LOGNOTICE )
    base_path = os.path.join( BASE_CURRENT_SOURCE_PATH, "downloaded_trailers.txt" )
    utils.save_list( base_path, download_trailers, "Downloaded Trailers" )

def _download_trailers( equivalent_mpaa, mpaa, genre, movie ):
    updated_trailers = []
    utils.log( "Downloading Trailers: %s Trailers" % trailer_settings[ "trailer_count" ], xbmc.LOGNOTICE )
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
        utils.log( "Attempting To Download Trailer: %s" % trailer[ 1 ], xbmc.LOGNOTICE )
        filename, ext = os.path.splitext( os.path.basename( (trailer[ 2 ].split("|")[0] ).replace( "?","" ) ) )
        filename = filename + "-trailer" + ext
        file_path = os.path.join( trailer_settings[ "trailer_download_folder" ], filename ).replace( "\\\\", "\\" )
        # check to see if trailer is already downloaded
        if xbmcvfs.exists( file_path ):
            success = True
            destination = file_path
            thumb = os.path.splitext( file_path )[0] + ".tbn"
        else:
            success, destination = download( trailer[ 2 ], temp_destination, file_tag="-trailer" )
            tsuccess, thumb = download( trailer[ 3 ], temp_destination, file_tag="-trailer", new_name=filename, extension=".tbn" )
        if success:
            utils.log( "Successfully Download Trailer: %s" % trailer[ 1 ], xbmc.LOGNOTICE )
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
            utils.log( "Failed to Download Trailer: %s" % ( logmessage, trailer[ 1 ] ), xbmc.LOGNOTICE )
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
    utils.log( "Creating Trailer NFO file", xbmc.LOGNOTICE )
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
    utils.log( "Saving Trailer NFO file", xbmc.LOGNOTICE )
    destination = os.path.splitext( trailer_nfopath )[0] + ".nfo"
    try:
        # open source path for writing
        file_object = xbmcvfs.File( destination.encode( "utf-8" ), "w" )
        # write xmlSource
        file_object.write( nfoSource.encode( "utf-8" ) )
        # close file object
        file_object.close()
        # return successful
        return True
    except Exception, e:
        # oops, notify user what error occurred
        utils.log( "%s" % str( e ), xbmc.LOGERROR )
        # return failed
        return False

if __name__ == "__main__":
    try:
        if sys.argv[1]:
            mpaa, genre = sys.argv[1].replace( "mpaa=", "" ).replace( "genre=", "").replace( "equivalent_mpaa=", "" ).split(";")
            _genre = genre.replace( "_", " / " )
            downloader( mpaa, _genre, equivalent_mpaa )
        else:
            utils.log( "No Arguments sent ", xbmc.LOGNOTICE )
    except:
        traceback.print_exc()
        utils.log( "No Arguments sent ", xbmc.LOGNOTICE )
 
