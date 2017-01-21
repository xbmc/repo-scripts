import xbmc
import xbmcgui
import xbmcvfs
import resources.lib.utils as utils

#triggered from settings.xml - asks if user wants to delete OAuth token information
shouldDelete = xbmcgui.Dialog().yesno(utils.getString(30093),utils.getString(30094),utils.getString(30095),autoclose=7000)

if(shouldDelete):
    #delete any of the known token file types
    xbmcvfs.delete(xbmc.translatePath(utils.data_dir() + "tokens.txt")) #dropbox
    xbmcvfs.delete(xbmc.translatePath(utils.data_dir() + "google_drive.dat")) #google drive
    
