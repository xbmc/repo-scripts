#====================================================================
#  PyDev Predefined Completions Creator
#  Copyright (C) 2010 James F. Carroll
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#====================================================================

import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import resources.lib.pypredefcom as pypredefcomp

#REMOTE_DBG = False
#
## append pydev remote debugger
#if REMOTE_DBG:
#    # Make pydev debugger works for auto reload.
#    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
#    try:
#        import pydevd
#    # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
#        pydevd.settrace('127.0.0.1', stdoutToServer=True, stderrToServer=True)
#    except ImportError:
#        sys.stderr.write("Error: " +
#            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
#        sys.exit(1)

def _get_browse_dialog( default="", heading="", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False ):
    """ shows a browse dialog and returns a value
        - 0 : ShowAndGetDirectory
        - 1 : ShowAndGetFile
        - 2 : ShowAndGetImage
        - 3 : ShowAndGetWriteableDirectory
    """
    dialog = xbmcgui.Dialog()
    value = dialog.browse( dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default )
    return value

if ( __name__ == "__main__" ):
    # get Addon object
    Addon = xbmcaddon.Addon( id=os.path.basename( os.getcwd() ) )
    # get user prefered save location
    doc_path = Addon.getSetting( "doc_path" )
    # get location if none set
    # TODO: do we want to ask this each time? (i think not, user can set in settings)
    if ( not doc_path ):
        doc_path = _get_browse_dialog( doc_path, Addon.getLocalizedString( 30110 ) )
    # if doc_path create html docs
    if ( doc_path ):
        # show feedback
        pDialog = xbmcgui.DialogProgress()
        pDialog.create( Addon.getAddonInfo( "name" ) )
        # set the doc_path setting incase the browse dialog was used
        Addon.setSetting( "doc_path", doc_path )
        # modules
        modules = [ "xbmc", "xbmcgui", "xbmcplugin", "xbmcaddon" ]
        # enumerate thru and print our help docs
        for count, module in enumerate( modules ):
            # set correct path
            predefcompath = xbmc.validatePath( xbmc.translatePath( os.path.join( doc_path, "%s.pypredef" % ( module, ) ) ) )
            # update dialog
            pDialog.update( count * 25, Addon.getLocalizedString( 30711 ) % ( module + ".pypredef", ), Addon.getLocalizedString( 30712 ) % ( predefcompath, ) )
            # print document
            predefcomf = open ( predefcompath, "w" )
            pypredefcomp.pypredefmodule(predefcomf, eval( module ))
            predefcomf.close();
        #close dialog
        pDialog.update( 100 )
        pDialog.close()
