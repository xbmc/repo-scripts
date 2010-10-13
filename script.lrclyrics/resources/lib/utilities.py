import sys
import os
import re
import xbmc
import xbmcgui

DEBUG_MODE = 4

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__language__ = sys.modules[ "__main__" ].__language__

# comapatble versions
SETTINGS_VERSIONS = ( "1.7", )
# base paths
BASE_DATA_PATH = os.path.join( xbmc.translatePath( "special://profile/" ), "addon_data", os.path.basename( os.getcwd() ) )
BASE_RESOURCE_PATH = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
# special button codes
SELECT_ITEM = ( 11, 256, 61453, )
EXIT_SCRIPT = ( 247, 275, 61467, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )
GET_EXCEPTION = ( 216, 260, 61448, )
SETTINGS_MENU = ( 229, 259, 261, 61533, )
SHOW_CREDITS = ( 195, 274, 61507, )
MOVEMENT_UP = ( 166, 270, 61478, )
MOVEMENT_DOWN = ( 167, 271, 61480, )
# special action codes
ACTION_SELECT_ITEM = ( 7, )
ACTION_EXIT_SCRIPT = ( 10, )
ACTION_CANCEL_DIALOG = ACTION_EXIT_SCRIPT + ( 9, )
ACTION_GET_EXCEPTION = ( 0, 11 )
ACTION_SETTINGS_MENU = ( 117, )
ACTION_SHOW_CREDITS = ( 122, )
ACTION_MOVEMENT_UP = ( 3, )
ACTION_MOVEMENT_DOWN = ( 4, )
# Log status codes
LOG_INFO, LOG_ERROR, LOG_NOTICE, LOG_DEBUG = range( 1, 5 )

def _create_base_paths():
    """ creates the base folders """
    if ( not os.path.isdir( BASE_DATA_PATH ) ):
        os.makedirs( BASE_DATA_PATH )
_create_base_paths()

def get_xbmc_revision():
    try:
        rev = int(re.search("r([0-9]+)",  xbmc.getInfoLabel( "System.BuildVersion" ), re.IGNORECASE).group(1))
    except:
        rev = 0
    return rev

def get_keyboard( default="", heading="", hidden=False ):
    """ shows a keyboard and returns a value """
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    if ( keyboard.isConfirmed() ):
        return keyboard.getText()
    return default

def get_numeric_dialog( default="", heading="", dlg_type=3 ):
    """ shows a numeric dialog and returns a value
        - 0 : ShowAndGetNumber		(default format: #)
        - 1 : ShowAndGetDate			(default format: DD/MM/YYYY)
        - 2 : ShowAndGetTime			(default format: HH:MM)
        - 3 : ShowAndGetIPAddress	(default format: #.#.#.#)
    """
    dialog = xbmcgui.Dialog()
    value = dialog.numeric( type, heading, default )
    return value

def get_browse_dialog( default="", heading="", dlg_type=1, shares="files", mask="", use_thumbs=False, treat_as_folder=False ):
    """ shows a browse dialog and returns a value
        - 0 : ShowAndGetDirectory
        - 1 : ShowAndGetFile
        - 2 : ShowAndGetImage
        - 3 : ShowAndGetWriteableDirectory
    """
    dialog = xbmcgui.Dialog()
    value = dialog.browse( dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default )
    return value

def LOG( status, format, *args ):
    if ( DEBUG_MODE >= status ):
        xbmc.output( "%s: %s\n" % ( ( "INFO", "ERROR", "NOTICE", "DEBUG", )[ status - 1 ], format % args, ) )

def make_legal_filepath( path, compatible=False, extension=True ):
    environment = os.environ.get( "OS", "xbox" )
    path = path.replace( "\\", "/" )
    drive = os.path.splitdrive( path )[ 0 ]
    parts = os.path.splitdrive( path )[ 1 ].split( "/" )
    if ( not drive and parts[ 0 ].endswith( ":" ) and len( parts[ 0 ] ) == 2 and compatible ):
        drive = parts[ 0 ]
        parts[ 0 ] = ""
    if ( environment == "xbox" or environment == "win32" or compatible ):
        illegal_characters = """,*=|<>?;:"+"""
        for count, part in enumerate( parts ):
            tmp_name = ""
            for char in part:
                if ( char in illegal_characters ): char = ""
                tmp_name += char
            if ( environment == "xbox" or compatible ):
                if ( len( tmp_name ) > 42 ):
                    if ( count == len( parts ) - 1 and extension == True ):
                        ext = os.path.splitext( tmp_name )[ 1 ]
                        tmp_name = "%s%s" % ( os.path.splitext( tmp_name )[ 0 ][ : 42 - len( ext ) ].strip(), ext, )
                    else:
                        tmp_name = tmp_name[ : 42 ].strip()
            parts[ count ] = tmp_name
    filepath = drive + "/".join( parts )
    if ( environment == "win32" ):
        return filepath.encode( "utf-8" )
    else:
        return filepath

def get_settings():
    settings = {}
    settings[ "scraper" ] = __settings__.getSetting( "scraper" )
    settings[ "save_lyrics" ] = __settings__.getSetting( "save_lyrics" ) == "true"
    settings[ "lyrics_path" ] = __settings__.getSetting( "lyrics_path" )
    if ( settings[ "lyrics_path" ] == "" ):
        settings[ "lyrics_path" ] = os.path.join( BASE_DATA_PATH, "lyrics" )
        __settings__.setSetting(id="lyrics_path", value=settings[ "lyrics_path" ])
    settings[ "smooth_scrolling" ] = __settings__.getSetting( "smooth_scrolling" ) == "true"
    settings[ "use_filename" ] = __settings__.getSetting( "use_filename" ) == "true"
    settings[ "filename_format" ] = __settings__.getSetting( "filename_format" )
    settings[ "compatible" ] = __settings__.getSetting( "compatible" ) == "true"
    settings[ "artist_folder" ] = __settings__.getSetting( "artist_folder" ) == "true"
    settings[ "subfolder" ] = __settings__.getSetting( "subfolder" ) == "true"
    settings[ "subfolder_name" ] = __settings__.getSetting( "subfolder_name" )
    return settings
