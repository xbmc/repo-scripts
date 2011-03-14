__scriptname__    = "CDArt Manager Script"
__scriptID__      = "script.cdartmanager"
__author__        = "Giftie"
__version__       = "1.2.9"
__credits__       = "Ppic, Reaven, Imaginos, redje, Jair, "
__credits2__      = "Chaos_666, Magnatism"
__XBMC_Revision__ = "35415"
__date__          = "3-5-11"
__dbversion__     = "1.1.8"
import sys
import os, traceback
import xbmcaddon
import xbmc
from pysqlite2 import dbapi2 as sqlite3

__addon__ = xbmcaddon.Addon(__scriptID__)
__language__ = __addon__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "skins", "Default" ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))
addon_work_folder = xbmc.translatePath( __addon__.getAddonInfo('profile') )
addon_db = os.path.join(addon_work_folder, "l_cdart.db")
addon_db_crash = os.path.join(addon_work_folder, "l_cdart.db-journal")
settings_file = os.path.join(addon_work_folder, "settings.xml")
script_fail = False
first_run = False
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") )



if ( __name__ == "__main__" ):
    xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptname__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #        default.py module                                 #", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptID__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __author__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __version__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits2__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Thanks for the help guys...                           #", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - Addon Work Folder: %s" % addon_work_folder, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - Addon Database: %s" % addon_db, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - Addon settings: %s" % settings_file, xbmc.LOGNOTICE )
    query = "SELECT version FROM counts"    
    xbmc.log( "[script.cdartmanager] - Looking for settings.xml", xbmc.LOGNOTICE )
    if not os.path.isfile(settings_file):
        xbmc.log( "[script.cdartmanager] - settings.xml File not found, opening settings", xbmc.LOGNOTICE )
        __addon__.openSettings()
        first_run = True
    else:
        xbmc.log( "[script.cdartmanager] - Addon Work Folder Found, Checking For Database", xbmc.LOGNOTICE )
    if not os.path.isfile(addon_db):
        xbmc.log( "[script.cdartmanager] - Addon Db not found, Must Be First Run", xbmc.LOGNOTICE )
        first_run = True
    else:
        xbmc.log( "[script.cdartmanager] - Addon Db Found, Checking Database Version", xbmc.LOGNOTICE )
    if os.path.isfile(addon_db_crash) and not first_run:
        xbmc.log( "[script.cdartmanager] - Detected Database Crash, Trying to delete", xbmc.LOGNOTICE )
        try:
            os.remove(addon_db)
            os.remove(addon_db_crash)
            xbmc.log( "[script.cdartmanager] - Opening Settings" , xbmc.LOGNOTICE )
            __addon__.openSettings()
        except StandardError, e:
            xbmc.log( "[script.cdartmanager] - Error Occurred: %s " % e.__class__.__name__, xbmc.LOGNOTICE )
            traceback.print_exc()
            script_fail = True
    elif not first_run:
        xbmc.log( "[script.cdartmanager] - Looking for database version: %s" % __dbversion__, xbmc.LOGNOTICE )
        try:
            conn_l = sqlite3.connect(addon_db)
            c = conn_l.cursor()
            c.execute(query)
            version=c.fetchall()
            for item in version:
                if item[0]==__dbversion__:
                    xbmc.log( "[script.cdartmanager] - Database matched", xbmc.LOGNOTICE )
                else:
                    xbmc.log( "[script.cdartmanager] - Database Not Matched - trying to delete" , xbmc.LOGNOTICE )
                    os.remove(addon_db)
                    os.remove(settings_file)
                    xbmc.log( "[script.cdartmanager] - Opening Settings" , xbmc.LOGNOTICE )
                    __addon__.openSettings()
            c.close    
        except StandardError, e:
            traceback.print_exc()
            xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
            try:
                xbmc.log( "[script.cdartmanager] - Trying To Delete Database" , xbmc.LOGNOTICE )
                os.remove(addon_db)
                os.remove(settings_file)
                xbmc.log( "[script.cdartmanager] - Opening Settings" , xbmc.LOGNOTICE )
                __addon__.openSettings()
            except StandardError, e:
                traceback.print_exc()
                xbmc.log( "[script.cdartmanager] - # unable to remove folder", xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
                script_fail = True
    path = __addon__.getAddonInfo('path')   
    if not script_fail:
        import gui
        ui = gui.GUI( "script-cdartmanager.xml" , __addon__.getAddonInfo('path'), "Default")
        ui.doModal()
        del ui
    else:
        xbmc.log( "[script.cdartmanager] - Problem accessing folder, exiting script", xbmc.LOGNOTICE )
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("cdART Manager", "Problem Accessing Folder, Script Exiting", 500, image) )
    sys.modules.clear()
