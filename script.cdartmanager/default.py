# -*- coding: utf-8 -*-

import sys
import os, traceback
import xbmcaddon, xbmc, xbmcgui

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
    
from os import remove as delete_file
exists = os.path.exists
 
__addon__         = xbmcaddon.Addon( "script.cdartmanager" )
__language__      = __addon__.getLocalizedString
__scriptname__    = __addon__.getAddonInfo('name')
__scriptID__      = __addon__.getAddonInfo('id')
__author__        = __addon__.getAddonInfo('author')
__version__       = __addon__.getAddonInfo('version')
__credits__       = "Ppic, Reaven, Imaginos, redje, Jair, "
__credits2__      = "Chaos_666, Magnatism, Kode"
__date__          = "9-1-11"
__dbversion__     = "1.3.2"
__dbversionold__  = "1.1.8"
__addon_path__    = __addon__.getAddonInfo('path')

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon_path__, 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "skins", "Default" ) )

notifyatfinish = __addon__.getSetting("notifyatfinish")

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))
addon_work_folder = xbmc.translatePath( __addon__.getAddonInfo('profile') )
addon_db = os.path.join(addon_work_folder, "l_cdart.db").replace("\\\\","\\")
addon_db_backup = os.path.join(addon_work_folder, "l_cdart.db.bak").replace("\\\\","\\")
addon_db_crash = os.path.join(addon_work_folder, "l_cdart.db-journal").replace("\\\\","\\")
settings_file = os.path.join(addon_work_folder, "settings.xml").replace("\\\\","\\")
script_fail = False
first_run = False
rebuild = False
soft_exit = False
background_db = False
image = xbmc.translatePath( os.path.join( __addon_path__, "icon.png") )

from utils import empty_tempxml_folder

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
    empty_tempxml_folder()
    try:
        if sys.argv[ 1 ]:
            if sys.argv[ 1 ] == "database":
                xbmcgui.Window( 10000 ).setProperty("cdartmanager_db", "True") 
                from database import refresh_db
                local_album_count, local_artist_count, local_cdart_count = refresh_db( True )
                if notifyatfinish=="true":
                    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( __language__(32042), __language__(32116), 2000, image) )
                xbmcgui.Window( 10000 ).setProperty("cdartmanager_db", "False")
            elif sys.argv[ 1 ] == "autocdart":
                pass
            elif sys.argv[ 1 ] == "autocover":
                pass
            else:
                xbmc.log( "[script.cdartmanager] - Error: Improper sys.argv[ 1 ]: %s" % sys.argv[ 1 ], xbmc.LOGNOTICE )
    except IndexError:
        xbmc.log( "[script.cdartmanager] - Addon Work Folder: %s" % addon_work_folder, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Addon Database: %s" % addon_db, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Addon settings: %s" % settings_file, xbmc.LOGNOTICE )
        query = "SELECT version FROM counts"    
        xbmc.log( "[script.cdartmanager] - Looking for settings.xml", xbmc.LOGNOTICE )
        if xbmc.getInfoLabel( "Window(10000).Property(cdartmanager_db)" ) == "True":
            if not os.environ.get( "OS", "win32" ) in ("win32", "Windows_NT"):
                background_db = False
                # message "cdART Manager, Stopping Background Database Building"
                xbmcgui.Dialog().ok( __language__(32042), __language__(32119) )
                xbmc.log( "[script.cdartmanager] - Background Database Was in Progress, Stopping, allowing script to continue", xbmc.LOGNOTICE )
                xbmcgui.Window( 10000 ).setProperty("cdartmanager_db", "False")
            else:
                background_db = True
                # message "cdART Manager, Background Database building in progress...  Exiting Script..."
                xbmcgui.Dialog().ok( __language__(32042), __language__(32118) )
                xbmc.log( "[script.cdartmanager] - Background Database Building in Progress, exiting", xbmc.LOGNOTICE )
                xbmcgui.Window( 10000 ).setProperty("cdartmanager_db", "False")
        if not exists(settings_file) and not background_db:
            xbmc.log( "[script.cdartmanager] - settings.xml File not found, opening settings", xbmc.LOGNOTICE )
            __addon__.openSettings()
            first_run = True
        elif not background_db:
            xbmc.log( "[script.cdartmanager] - Addon Work Folder Found, Checking For Database", xbmc.LOGNOTICE )
        if not exists(addon_db) and not background_db:
            xbmc.log( "[script.cdartmanager] - Addon Db not found, Must Be First Run", xbmc.LOGNOTICE )
            first_run = True
        elif not background_db:
            xbmc.log( "[script.cdartmanager] - Addon Db Found, Checking Database Version", xbmc.LOGNOTICE )
        if exists(addon_db_crash) and not first_run and not background_db:
            xbmc.log( "[script.cdartmanager] - Detected Database Crash, Trying to delete", xbmc.LOGNOTICE )
            try:
                delete_file(addon_db)
                delete_file(addon_db_crash)
            except StandardError, e:
                xbmc.log( "[script.cdartmanager] - Error Occurred: %s " % e.__class__.__name__, xbmc.LOGNOTICE )
                traceback.print_exc()
                script_fail = True
        elif not first_run and not background_db:
            xbmc.log( "[script.cdartmanager] - Looking for database version: %s" % __dbversion__, xbmc.LOGNOTICE )
            try:
                conn_l = sqlite3.connect(addon_db)
                c = conn_l.cursor()
                c.execute(query)
                version=c.fetchall()
                c.close
                for item in version:
                    if item[0] == __dbversion__:
                        xbmc.log( "[script.cdartmanager] - Database matched", xbmc.LOGNOTICE )
                        break
                    else:
                        xbmc.log( "[script.cdartmanager] - Database Not Matched - trying to delete" , xbmc.LOGNOTICE )
                        rebuild = xbmcgui.Dialog().yesno( __language__(32108) , __language__(32109) )
                        soft_exit = True
                        break
            except StandardError, e:
                traceback.print_exc()
                xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
                try:
                    xbmc.log( "[script.cdartmanager] - Trying To Delete Database" , xbmc.LOGNOTICE )
                    delete_file(addon_db)
                except StandardError, e:
                    traceback.print_exc()
                    xbmc.log( "[script.cdartmanager] - # unable to remove folder", xbmc.LOGNOTICE )
                    xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
                    script_fail = True
        path = __addon__.getAddonInfo('path')   
        if not script_fail and not background_db:
            if rebuild:
                from database import refresh_db
                local_album_count, local_artist_count, local_cdart_count = refresh_db( True )
            elif not rebuild and not soft_exit:
                import gui
                ui = gui.GUI( "script-cdartmanager.xml" , __addon__.getAddonInfo('path'), "Default")
                ui.doModal()
                del ui
        elif not background_db:
            xbmc.log( "[script.cdartmanager] - Problem accessing folder, exiting script", xbmc.LOGNOTICE )
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( __language__(32042), __language__(32110), 500, image) )
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
 