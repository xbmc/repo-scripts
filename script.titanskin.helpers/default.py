import xbmcaddon
import xbmcplugin
import os

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

import MainModule

#script init
action = ""
argument1 = ""
argument2 = ""
argument3 = ""

# get arguments
try:
    action = str(sys.argv[1])
except: 
    pass

try:
    argument1 = str(sys.argv[2])
except:
    pass

try:
    argument2 = str(sys.argv[3])
except:
    pass

try:
    argument3 = str(sys.argv[4])
except: 
    pass  
    
# select action
if action == "SENDCLICK":
    MainModule.sendClick(argument1)

elif action =="ADDSHORTCUT":
    MainModule.addShortcutWorkAround()

elif action == "SHOWINFO":
    MainModule.showInfoPanel()

#setwidget is called from window other then home    
elif action == "SETWIDGET":
    if (xbmc.getCondVisibility("!Window.IsActive(home)")):
        from HomeMonitor import HomeMonitor
        HomeMonitor().setWidget(argument1)
elif action == "DEFAULTSETTINGS":
    MainModule.defaultSettings()
elif action == "MUSICSEARCH":
    MainModule.musicSearch()
elif action == "SETVIEW":
    MainModule.setView()
elif action == "SEARCHTRAILER":
    MainModule.searchTrailer(argument1)
elif action == "SETFORCEDVIEW":
    MainModule.setForcedView(argument1)    
elif action == "ENABLEVIEWS":
    MainModule.enableViews()
elif action == "VIDEOSEARCH":
    from SearchDialog import SearchDialog
    searchDialog = SearchDialog("script-titanskin_helpers-CustomSearch.xml", __cwd__, "default", "1080i")
    searchDialog.doModal()
    del searchDialog
elif action == "COLORPICKER":
    from ColorPicker import ColorPicker
    colorPicker = ColorPicker("script-titanskin_helpers-ColorPicker.xml", __cwd__, "default", "1080i")
    colorPicker.skinString = argument1
    colorPicker.doModal()
    del colorPicker
elif action == "COLORTHEMES":
    from ColorThemes import ColorThemes
    colorThemes = ColorThemes("script-titanskin_helpers-ColorThemes.xml", __cwd__, "default", "1080i")
    colorThemes.doModal()
    del colorThemes
elif action == "CREATECOLORTHEME":
    import ColorThemes as colorThemes
    colorThemes.createColorTheme()
elif action == "RESTORECOLORTHEME":
    import ColorThemes as colorThemes
    colorThemes.restoreColorTheme()
elif action == "COLORTHEMETEXTURE":    
    MainModule.selectOverlayTexture()
elif action == "BUSYTEXTURE":    
    MainModule.selectBusyTexture()     
elif action == "BACKUP":
    import BackupRestore
    BackupRestore.backup()
elif action == "RESTORE":
    import BackupRestore
    BackupRestore.restore()
elif action == "RESET":
    import BackupRestore
    BackupRestore.reset()
elif action == "SETSKINVERSION":
    import Utils as utils
    utils.setSkinVersion()
elif "NEXTEPISODES" in argument1:
    MainModule.getNextEpisodes()
elif "RECOMMENDEDMOVIES" in argument1:
    MainModule.getRecommendedMovies()
elif "RECOMMENDEDMEDIA" in argument1:
    MainModule.getRecommendedMedia(False)
elif "RECENTMEDIA" in argument1:
    MainModule.getRecentMedia()
elif "SIMILARMOVIES" in argument1:
    MainModule.getSimilarMovies()
elif "INPROGRESSMEDIA" in argument1:
    MainModule.getRecommendedMedia(True)      
elif "FAVOURITEMEDIA" in argument1:
    MainModule.getFavouriteMedia() 
elif argument1 == "?FAVOURITES":
    MainModule.getFavourites()
elif "?LAUNCHAPP" in argument1:
    try:
        app = argument1.split("&&&")[-1]
        xbmc.executebuiltin(app)
    except: pass


    
    