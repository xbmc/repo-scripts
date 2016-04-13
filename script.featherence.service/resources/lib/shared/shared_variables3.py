import xbmc, xbmcaddon, sys, os

from shared_variables import  space, space2, addondata_path

getsetting         = xbmcaddon.Addon().getSetting

setsetting         = xbmcaddon.Addon().setSetting
addonName          = xbmcaddon.Addon().getAddonInfo("name")
addonString        = xbmcaddon.Addon().getLocalizedString
addonID            = xbmcaddon.Addon().getAddonInfo("id")
addonPath          = xbmcaddon.Addon().getAddonInfo("path")
addonFanart        = xbmcaddon.Addon().getAddonInfo("fanart")
addonVersion       = xbmcaddon.Addon().getAddonInfo("version")

addonName2 = "Featherence"
printfirst = addonName + ": !@# "
try: pluginhandle = int(sys.argv[1])
except: pluginhandle = ""

templates2_path = os.path.join(addonPath, 'resources', 'templates2', '')

'''---------------------------'''
General_AutoView = getsetting('General_AutoView')
General_TVModeShuffle = getsetting('General_TVModeShuffle')
General_TVModeDialog = getsetting('General_TVModeDialog')
try:
	General_Language = getsetting('General_Language')
	General_Language2 = getsetting('General_Language2')
	General_Language3 = getsetting('General_Language3')
	General_LanguageL = [General_Language, General_Language2, General_Language3]
except:
	General_Language = systemlanguage
	General_Language2 = "English"
	General_Language3 = ""
	General_LanguageL = [systemlanguage, 'English']


try:
	Search_History = getsetting('Search_History')
	Search_Limit = getsetting('Search_Limit')
	General_TVModeQuality = getsetting('General_TVModeQuality')
except:
	Search_History = ""
	Search_Limit = ""
	General_TVModeQuality = "0"
Search_History_file = os.path.join(addondata_path, addonID, 'Search_History.txt')

Addon_ShowLog = getsetting('Addon_ShowLog')
Addon_ShowLog2 = getsetting('Addon_ShowLog2')
Addon_Update = getsetting('Addon_Update')
Addon_UpdateDate = getsetting('Addon_UpdateDate')
Addon_UpdateLog = getsetting('Addon_UpdateLog')
Addon_Version = getsetting('Addon_Version')
'''---------------------------'''

Fanart_Enable = getsetting('Fanart_Enable') #.lower
Fanart_EnableCustom = getsetting('Fanart_EnableCustom') #.lower
Fanart_Custom100 = getsetting('Fanart_Custom100')
Fanart_Custom101 = getsetting('Fanart_Custom101')
Fanart_Custom102 = getsetting('Fanart_Custom102')
Fanart_Custom103 = getsetting('Fanart_Custom103')
Fanart_Custom104 = getsetting('Fanart_Custom104')
Fanart_Custom105 = getsetting('Fanart_Custom105')
Fanart_Custom106 = getsetting('Fanart_Custom106')
Fanart_Custom107 = getsetting('Fanart_Custom107')
Fanart_Custom108 = getsetting('Fanart_Custom108')
Fanart_Custom109 = getsetting('Fanart_Custom109')
Fanart_Custom110 = getsetting('Fanart_Custom110')
Fanart_Custom111 = getsetting('Fanart_Custom111')
Fanart_Custom112 = getsetting('Fanart_Custom112')
Fanart_Custom113 = getsetting('Fanart_Custom113')
Fanart_Custom114 = getsetting('Fanart_Custom114')
Fanart_Custom115 = getsetting('Fanart_Custom115')
Fanart_Custom116 = getsetting('Fanart_Custom116')
Fanart_Custom117 = getsetting('Fanart_Custom117')
Fanart_Custom118 = getsetting('Fanart_Custom118')
Fanart_Custom119 = getsetting('Fanart_Custom119')

Fanart_Custom10100 = getsetting('Fanart_Custom10100')
Fanart_Custom10101 = getsetting('Fanart_Custom10101')
Fanart_Custom10102 = getsetting('Fanart_Custom10102')
Fanart_Custom10103 = getsetting('Fanart_Custom10103')
Fanart_Custom10104 = getsetting('Fanart_Custom10104')
Fanart_Custom10105 = getsetting('Fanart_Custom10105')
Fanart_Custom10106 = getsetting('Fanart_Custom10106')
Fanart_Custom10107 = getsetting('Fanart_Custom10107')
Fanart_Custom10108 = getsetting('Fanart_Custom10108')
Fanart_Custom10109 = getsetting('Fanart_Custom10109')
Fanart_Custom10200 = getsetting('Fanart_Custom10200')
Fanart_Custom10201 = getsetting('Fanart_Custom10201')
Fanart_Custom10202 = getsetting('Fanart_Custom10202')
Fanart_Custom10203 = getsetting('Fanart_Custom10203')
Fanart_Custom10204 = getsetting('Fanart_Custom10204')
Fanart_Custom10205 = getsetting('Fanart_Custom10205')
Fanart_Custom10206 = getsetting('Fanart_Custom10206')
Fanart_Custom10207 = getsetting('Fanart_Custom10207')
Fanart_Custom10208 = getsetting('Fanart_Custom10208')
Fanart_Custom10209 = getsetting('Fanart_Custom10209')

Fanart_Custom11100 = getsetting('Fanart_Custom11100')
Fanart_Custom11101 = getsetting('Fanart_Custom11101')
Fanart_Custom11102 = getsetting('Fanart_Custom11102')
Fanart_Custom11103 = getsetting('Fanart_Custom11103')
Fanart_Custom11104 = getsetting('Fanart_Custom11104')
Fanart_Custom11105 = getsetting('Fanart_Custom11105')
Fanart_Custom11106 = getsetting('Fanart_Custom11106')
Fanart_Custom11107 = getsetting('Fanart_Custom11107')
Fanart_Custom11108 = getsetting('Fanart_Custom11108')
Fanart_Custom11109 = getsetting('Fanart_Custom11109')



Custom_Playlist1_ID = getsetting('Custom_Playlist1_ID')
Custom_Playlist1_Name = getsetting('Custom_Playlist1_Name')
Custom_Playlist1_Thumb = getsetting('Custom_Playlist1_Thumb')
Custom_Playlist1_Description = getsetting('Custom_Playlist1_Description')
Custom_Playlist1_Fanart = getsetting('Custom_Playlist1_Fanart')
Custom_Playlist2_ID = getsetting('Custom_Playlist2_ID')
Custom_Playlist2_Name = getsetting('Custom_Playlist2_Name')
Custom_Playlist2_Thumb = getsetting('Custom_Playlist2_Thumb')
Custom_Playlist2_Description = getsetting('Custom_Playlist2_Description')
Custom_Playlist2_Fanart = getsetting('Custom_Playlist2_Fanart')
Custom_Playlist3_ID = getsetting('Custom_Playlist3_ID')
Custom_Playlist3_Name = getsetting('Custom_Playlist3_Name')
Custom_Playlist3_Thumb = getsetting('Custom_Playlist3_Thumb')
Custom_Playlist3_Description = getsetting('Custom_Playlist3_Description')
Custom_Playlist3_Fanart = getsetting('Custom_Playlist3_Fanart')
Custom_Playlist4_ID = getsetting('Custom_Playlist4_ID')
Custom_Playlist4_Name = getsetting('Custom_Playlist4_Name')
Custom_Playlist4_Thumb = getsetting('Custom_Playlist4_Thumb')
Custom_Playlist4_Description = getsetting('Custom_Playlist4_Description')
Custom_Playlist4_Fanart = getsetting('Custom_Playlist4_Fanart')
Custom_Playlist5_ID = getsetting('Custom_Playlist5_ID')
Custom_Playlist5_Name = getsetting('Custom_Playlist5_Name')
Custom_Playlist5_Thumb = getsetting('Custom_Playlist5_Thumb')
Custom_Playlist5_Description = getsetting('Custom_Playlist5_Description')
Custom_Playlist5_Fanart = getsetting('Custom_Playlist5_Fanart')
Custom_Playlist6_ID = getsetting('Custom_Playlist6_ID')
Custom_Playlist6_Name = getsetting('Custom_Playlist6_Name')
Custom_Playlist6_Thumb = getsetting('Custom_Playlist6_Thumb')
Custom_Playlist6_Description = getsetting('Custom_Playlist6_Description')
Custom_Playlist6_Fanart = getsetting('Custom_Playlist6_Fanart')
Custom_Playlist7_ID = getsetting('Custom_Playlist7_ID')
Custom_Playlist7_Name = getsetting('Custom_Playlist7_Name')
Custom_Playlist7_Thumb = getsetting('Custom_Playlist7_Thumb')
Custom_Playlist7_Description = getsetting('Custom_Playlist7_Description')
Custom_Playlist7_Fanart = getsetting('Custom_Playlist7_Fanart')
Custom_Playlist8_ID = getsetting('Custom_Playlist8_ID')
Custom_Playlist8_Name = getsetting('Custom_Playlist8_Name')
Custom_Playlist8_Thumb = getsetting('Custom_Playlist8_Thumb')
Custom_Playlist8_Description = getsetting('Custom_Playlist8_Description')
Custom_Playlist8_Fanart = getsetting('Custom_Playlist8_Fanart')
Custom_Playlist9_ID = getsetting('Custom_Playlist9_ID')
Custom_Playlist9_Name = getsetting('Custom_Playlist9_Name')
Custom_Playlist9_Thumb = getsetting('Custom_Playlist9_Thumb')
Custom_Playlist9_Description = getsetting('Custom_Playlist9_Description')
Custom_Playlist9_Fanart = getsetting('Custom_Playlist9_Fanart')
Custom_Playlist10_ID = getsetting('Custom_Playlist10_ID')
Custom_Playlist10_Name = getsetting('Custom_Playlist10_Name')
Custom_Playlist10_Thumb = getsetting('Custom_Playlist10_Thumb')
Custom_Playlist10_Description = getsetting('Custom_Playlist10_Description')
Custom_Playlist10_Fanart = getsetting('Custom_Playlist10_Fanart')
'''---------------------------'''
Custom_PlaylistL = [Custom_Playlist1_ID, Custom_Playlist2_ID, Custom_Playlist3_ID, Custom_Playlist4_ID, Custom_Playlist5_ID, Custom_Playlist6_ID, Custom_Playlist7_ID, Custom_Playlist8_ID, Custom_Playlist9_ID, Custom_Playlist10_ID]
Custom_Playlist_NameT = { Custom_Playlist1_ID: Custom_Playlist1_Name, Custom_Playlist2_ID: Custom_Playlist2_Name, Custom_Playlist3_ID: Custom_Playlist3_Name, Custom_Playlist4_ID: Custom_Playlist4_Name, Custom_Playlist5_ID: Custom_Playlist5_Name, Custom_Playlist6_ID: Custom_Playlist6_Name, Custom_Playlist7_ID: Custom_Playlist7_Name, Custom_Playlist8_ID: Custom_Playlist8_Name, Custom_Playlist9_ID: Custom_Playlist9_Name, Custom_Playlist10_ID: Custom_Playlist10_Name }
Custom_Playlist_NameT2 = { Custom_Playlist1_Name: Custom_Playlist1_ID, Custom_Playlist2_Name: Custom_Playlist2_ID, Custom_Playlist3_Name: Custom_Playlist3_ID, Custom_Playlist4_Name: Custom_Playlist4_ID, Custom_Playlist5_Name: Custom_Playlist5_ID, Custom_Playlist6_Name: Custom_Playlist6_ID, Custom_Playlist7_Name: Custom_Playlist7_ID, Custom_Playlist8_Name: Custom_Playlist8_ID, Custom_Playlist9_Name: Custom_Playlist9_ID, Custom_Playlist10_Name: Custom_Playlist10_ID }
sefilter = []