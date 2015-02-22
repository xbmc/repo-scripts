import xbmcaddon
import os

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

import MainModule
import BackupRestore

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
elif action == "SETVIEW":
    MainModule.setView(argument1, argument2)
elif action == "SHOWSUBMENU":
    MainModule.showSubmenu(argument1,argument2)
elif action == "SHOWINFO":
    MainModule.showInfoPanel()
elif action == "SETWIDGET":
    MainModule.setWidget(argument1)
elif action == "UPDATEPLEXLINKS":   
    MainModule.updatePlexlinks()
elif action == "SHOWWIDGET":   
    MainModule.showWidget()
elif action == "SETCUSTOM":
    MainModule.setCustomContent(argument1)
elif action == "DEFAULTSETTINGS":
    MainModule.defaultSettings()
elif action == "MUSICSEARCH":
    MainModule.musicSearch()
elif action == "BACKUP":
    BackupRestore.backup()
elif action == "RESTORE":
    BackupRestore.restore()
elif action == "RESET":
    BackupRestore.reset()
elif action == "CHECKNOTIFICATIONS":
    MainModule.checkNotifications(argument1)
