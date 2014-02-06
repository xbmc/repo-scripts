# -*- coding: utf-8 -*-
import sys, os, re, traceback
import xbmc, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils

def absolute_listdir( path, media_type = "files", recursive = False, contains = "" ):
    absolute_files = []
    absolute_folders = []
    path = utils.smart_unicode( path )
    folders, files = xbmcvfs.listdir( path )
    for f in files:
        f = utils.smart_unicode( f )
        if media_type == "files":
            if not contains or ( contains and ( contains in f ) ):
                try:
                    absolute_files.append( os.path.join( path, f ) )
                except UnicodeError:
                    utils.log( "Problem with path, skipping" )
                    utils.log( "Path: %s" % repr( path ) )
                    utils.log( "Filename: %s" % repr( path ) )
                except:
                    utils.log( "Problem with path, skipping" )
                    traceback.print_exc()
        else:
            if os.path.splitext( f )[ 1 ] in xbmc.getSupportedMedia( media_type ):
                if not contains or ( contains and ( contains in f ) ):
                    absolute_files.append( os.path.join( path, f ) )
    if folders:
        absolute_folders = absolute_folder_paths( folders, path )
        if recursive:
            for folder in absolute_folders:
                absolute_files.extend( absolute_listdir( folder, recursive = recursive, contains = contains ) )
    return absolute_files

def absolute_folder_paths( folders, root_path ):
    actual_folders = []
    root_path = utils.smart_unicode( root_path )
    for folder in folders:
        folder = utils.smart_unicode( folder )
        try:
            actual_folders.append( os.path.join( root_path, folder ).replace("\\\\","\\") )
        except UnicodeError:
            utils.log( "Problem with path, skipping" )
            utils.log( "Path: %s" % repr( root_path ) )
            utils.log( "Folder: %s" % repr( folder ) )
        except:
            utils.log( "Problem with path, skipping" )
            traceback.print_exc()
    return actual_folders
        
