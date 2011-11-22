import sys
import os
import urllib

import xbmc
import xbmcgui
import xbmcaddon

__scriptID__ = "weather.weatherplus"
# get the language and settings objects
_A_ = xbmcaddon.Addon( __scriptID__ )
# language method
_L_ = _A_.getLocalizedString
# settings method
#_S_ = _A_.getSetting

__plugin__ = "weather.com plus"
__pluginname__ = "weather.com+"
__author__ = "nuka1195"


class Main:
    def __init__( self, package=None ):
        # class wide progress dialog, maybe smoother
        self.pDialog = xbmcgui.DialogProgress()
        # set initial message to successful
        self.message = 32220
        # select correct url for package
        if ( package == "mappack" ):
            package_url = self._get_package_version()
            # this is used to add extra info to settings
            include_package_name = True
        # check for previous package download
        self._check_previous_download_info( package=package )
        # now get the path to download to
        installation_path = self._get_installation_path()
        # only proceed if download path was set
        if ( installation_path == "" ):
            self.message = 32223
        else:
            # download package
            self._download_package( url=package_url, path=installation_path )
            # write message to settings to inform user unless cancelled by user
            if ( self.message != 32223 ):
                self._save_setting( setting=package, path=installation_path, filename=os.path.basename( package_url ), include=include_package_name )
        # inform user of success or failer
        self._inform_user( url=package_url, path=installation_path )

    def _save_setting( self, setting, path, filename, include ):
        # set proper setting value
        value = ( _L_( 32230 ), _L_( 32231 ), )[ self.message == 32220 ]
        # set proper path
        path = ( "", path, )[ self.message == 32220 ]
        # we add packages filename to value if include`and successful
        if ( include and self.message == 32220 ):
            value += " - %s" % ( filename, )
        # mark package as installed or failed
        _A_.setSetting( "install_%s" % ( setting, ), value )
        _A_.setSetting( "install_%s_path" % ( setting, ), path )
        # set TWC.MapIconPath skin setting, so icons work immediately
        if ( path ):
            xbmc.executebuiltin( "Skin.SetString(TWC.MapIconPath,%s)" % ( path, ) ) 

    def _inform_user( self, url, path ):
        # set filename
        filename = os.path.basename( url )
        # do not display if message is user cancelled
        path = ( "", path )[ self.message != 32223 ]
        # inform user of result
        ok = xbmcgui.Dialog().ok( _L_( 32000 ) % ( __pluginname__, ), _L_( self.message ) % ( filename, ), path )

    def _get_package_version( self ):
        # ask user which pack
        package = xbmcgui.Dialog().yesno( _L_( 32000 ) % ( __pluginname__, ),_L_( 32207 ),  _L_( 32208 ), _L_( 32209 ), _L_( 32211 ), _L_( 32210 ), )
        # set proper url
        url = "http://xbmc-addons.googlecode.com/svn/packages/plugins/weather/weather.com%%20plus/%s" % ( ( "MapIconPack-small.zip", "MapIconPack-large.zip", )[ package == True ], )
        # return result
        return url

    # TODO: determine what to do with this
    def _check_previous_download_info( self, package ):
        # get path and date of download
        path = _A_.getSetting( "install_%s_path" % ( package, ) )
        date = _A_.getSetting( "install_%s_date" % ( package, ) )

    def _get_installation_path( self ):
        # get user input
        value = xbmcgui.Dialog().browse( 3, _L_( 32200 ), "files", "", False, False, "" )
        # return value
        return value

    def _download_package( self, url, path ):
        # set filename
        filename = os.path.basename( url )
        # temporary download path
        tmp_path = os.path.join( "special://temp", filename )
        try:
            # create dialog
            self.pDialog.create( _L_( 32000 ) % ( __pluginname__, ), _L_( 32202 ) % ( filename, ), os.path.dirname( tmp_path ) )
            self.pDialog.update( 0 )
            # fetch package
            urllib.urlretrieve( url , xbmc.translatePath( tmp_path ), self._report_hook )
            # close dialog
            self.pDialog.close()
            # extract package
            self._extract_package( tmp_path=tmp_path, path=path, filename=filename )
        except:
            # set error message
            self.message = ( self.message, 32222, )[ self.message == 32220 ]
            # close dialog
            self.pDialog.close()

    def _report_hook( self, count, blocksize, totalsize ):
        # calculate percentage
        percent = int( float( count * blocksize * 100) / totalsize )
        # update dialog
        self.pDialog.update( percent )
        # if cancelled raise an error to abort
        if ( self.pDialog.iscanceled() ):
            # set error message
            self.message = 32223
            # raise the error
            raise

    def _extract_package( self, tmp_path, path, filename ):
        try:
            # extract if zip or rar file
            if ( filename.endswith( ".zip" ) or filename.endswith( ".rar" ) ):
                # create dialog
                self.pDialog.create( _L_( 32000 ) % ( __pluginname__, ), _L_( 32204 ) % filename, os.path.dirname( path ) )
                self.pDialog.update( 0 )
                # extract package
                xbmc.executebuiltin( "XBMC.Extract(%s,%s)" % ( tmp_path, path, ) )
        except: 
            # set error message
            self.message = 32221
        try:
            # close dialog
            self.pDialog.close()
        except:
            pass


if ( __name__ == "__main__" ):
    Main( package=sys.argv[ 1 ].split( "=" )[ 1 ] )
