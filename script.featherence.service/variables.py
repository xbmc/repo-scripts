'''------------------------------
---shared_variables--------------
------------------------------'''
import xbmcaddon, sys, os
servicefeatherencePath          = xbmcaddon.Addon('script.featherence.service').getAddonInfo("path")
sharedlibDir = os.path.join(servicefeatherencePath, 'resources', 'lib', 'shared')
sys.path.insert(0, sharedlibDir)

from shared_variables import *
'''---------------------------'''

'''------------------------------
---script.featherence.service------------------
------------------------------'''
getsetting            = xbmcaddon.Addon().getSetting
setsetting            = xbmcaddon.Addon().setSetting
addonName             = xbmcaddon.Addon().getAddonInfo("name")
addonString           = xbmcaddon.Addon().getLocalizedString
addonID               = xbmcaddon.Addon().getAddonInfo("id")
addonPath             = xbmcaddon.Addon().getAddonInfo("path")
addonFanart           = os.path.join(addonPath, "fanart.jpg")
addonIcon           = os.path.join(addonPath, "icon.png")
addonVersion          = xbmcaddon.Addon().getAddonInfo("version")

libDir = os.path.join(addonPath, 'resources', 'lib')
sys.path.insert(1, libDir)
libDir2 = os.path.join(addonPath, 'resources', 'lib', 'pastebin_python')
sys.path.insert(2, libDir2)


printfirst = addonName + ": !@# "
'''---------------------------'''

Skin_UpdateDate = getsetting('Skin_UpdateDate')
Skin_UpdateLog = getsetting('Skin_UpdateLog')
Skin_Version = getsetting('Skin_Version')

ScreenSaver_Music = getsetting('ScreenSaver_Music')
'''---------------------------'''
A10 = [0, 10, 20, 30, 40, 50 , 60]
'''---------------------------'''

'''------------------------------
---OTHERS------------------------
------------------------------'''
output = ""
printpoint = ""

customhomecustomizerW = xbmc.getCondVisibility('Window.IsVisible(CustomHomeCustomizer.xml)')
customhomecustomizer2W = xbmc.getCondVisibility('Window.IsVisible(CustomHomeCustomize2.xml)')
custom1000W = xbmc.getCondVisibility('Window.IsVisible(Custom1000.xml)')
custom1138W = xbmc.getCondVisibility('Window.IsVisible(Custom1138.xml)')
custom1139W = xbmc.getCondVisibility('Window.IsVisible(Custom1139.xml)')
custom1175W = xbmc.getCondVisibility('Window.IsVisible(Custom1175.xml)')
custom1173W = xbmc.getCondVisibility('Window.IsVisible(Custom1173.xml)')

property_mode10 = xbmc.getInfoLabel('Window(home).Property(mode10)')
property_temp = xbmc.getInfoLabel('Window(home).Property(TEMP)')
property_temp2 = xbmc.getInfoLabel('Window(home).Property(TEMP2)')
property_1000progress = xbmc.getInfoLabel('Window(home).Property(1000progress)')
property_1000title = xbmc.getInfoLabel('Window(home).Property(1000title)')
property_1000comment = xbmc.getInfoLabel('Window(home).Property(1000comment)')

property_buttonid = xbmc.getInfoLabel('Window(home).Property(Button.ID)') #DYNAMIC
property_buttonid_ = xbmc.getInfoLabel('Window(home).Property(Button.ID_)') #BASE
property_buttonname = xbmc.getInfoLabel('Window(home).Property(Button.Name)')

property_subbuttonid_ = xbmc.getInfoLabel('Window(home).Property(SubButton.ID_)')
property_subbuttonname = xbmc.getInfoLabel('Window(home).Property(SubButton.Name)')
property_previoussubbuttonid_ = xbmc.getInfoLabel('Window(home).Property(Previous_SubButton.ID_)')
property_nextsubbuttonid_ = xbmc.getInfoLabel('Window(home).Property(Next_SubButton.ID_)')

property_reloadskin = xbmc.getInfoLabel('Window(home).Property(ReloadSkin)')
reloadskin_check = xbmc.getInfoLabel('Control.GetLabel(700105)')

property_submenutip = xbmc.getInfoLabel('Window(home).Property(SubMenuTip)')
property_submenu2tip = xbmc.getInfoLabel('Window(home).Property(SubMenu2Tip)')
property_addonisrunning_smartbuttons = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_RUNNING)')
'''Prevent error'''
try: property_buttonid = property_buttonid.replace('"',"")
except: pass
try: property_buttonid_ = property_buttonid_.replace('"',"")
except: pass
try: property_temp = property_temp.replace('"',"")
except: pass
try: property_temp2 = property_temp2.replace('"',"")
except: pass

if not os.path.exists(featherenceserviceaddondata_media_path):
	try: os.mkdir(featherenceserviceaddondata_media_path)
	except: pass