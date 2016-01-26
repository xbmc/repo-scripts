# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, os, sys, subprocess, random

from variables import *
from modules import *
from shared_modules3 import get_params

printpoint = ""

try: params=get_params()
except Exception, TypeError: xbmc.executebuiltin('Addon.OpenSettings('+addonID+')')
mode=None
value=None
value2=None
value3=None
value4=None

try: mode=int(params["mode"])
except: pass
try: value=str(params["value"])
except: value = ""
try: value2=str(params["value2"])
except: value2 = ""
try: value3=str(params["value3"])
except: value3 = ""
try: value4=str(params["value4"])
except: value4 = ""

if mode == 0:
	'''------------------------------
	---TEST--------------------------
	------------------------------'''
	name = 'TEST'
	mode0(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 1:
	'''------------------------------
	---SMART-KEYBOARD-SAVE-VALUE-----
	------------------------------'''
	name = 'SMART-KEYBOARD-SAVE-VALUE'
	mode1(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 2:
	'''------------------------------
	---SMART-KEYBOARD-COPY-----------
	------------------------------'''
	name = 'SMART-KEYBOARD-COPY'
	mode2(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 3:
	'''------------------------------
	---SMART-KEYBOARD-HISTORY--------
	------------------------------'''
	name = 'SMART-KEYBOARD-HISTORY'
	mode3(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 4:
	'''------------------------------
	---SMART-KEYBOARD-PASTE----------
	------------------------------'''
	name = 'SMART-KEYBOARD-PASTE'
	mode4(admin, name, printpoint)
	'''---------------------------'''

elif mode == 5:
	'''------------------------------
	---demon-------------------------
	------------------------------'''
	name = "demon"
	mode5(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 6:
	'''------------------------------
	---connectioncheck---------------
	------------------------------'''
	name = "connectioncheck"
	connectioncheck(admin)
	'''---------------------------'''

elif mode == 7:
	'''------------------------------
	---SEND-DEBUG--------------------
	------------------------------'''
	from debug import *
	from debug2 import *
	name = "SEND-DEBUG"
	SendDebug()
	'''---------------------------'''
	
elif mode == 8:
	'''------------------------------
	---SMART-SUBTITLE-SEARCH---------
	------------------------------'''
	import json
	name = 'SMART-SUBTITLE-SEARCH'
	mode8(admin, name, printpoint)
	'''---------------------------'''

elif mode == 9:
	'''------------------------------
	---SEMI-AUTO-SUBTITLE-FIND-------
	------------------------------'''
	name = 'SEMI-AUTO-SUBTITLE-FIND'
	mode9(admin, name)
	'''---------------------------'''
	
elif mode == 10:
	'''------------------------------
	---VideoPlayer demon-------------
	------------------------------'''
	name = "VideoPlayer demon"
	mode10(admin, name, printpoint)
	'''---------------------------'''

elif mode == 11:
	'''------------------------------
	---INSTALL-ADDON2----------------
	------------------------------'''
	name = "INSTALL-ADDON2"
	mode11(value, admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 12:
	'''------------------------------
	---UPDATE-LIVE-TV-PVR------------
	------------------------------'''
	name = 'UPDATE-LIVE-TV-PVR'
	mode12(admin, name, printpoint)
	'''---------------------------'''

elif mode == 13:
	'''------------------------------
	---SubtitleButton_Country--------
	------------------------------'''
	name = "SubtitleButton_Country"
	mode13(admin, name, printpoint)
	'''---------------------------'''

elif mode == 14:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode14(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 15:
	'''------------------------------
	---CopyFiles-Tweak---------------
	------------------------------'''
	name = "CopyFiles-Tweak"
	mode15(value, admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 16:
	'''------------------------------
	---setSources.xml----------------
	------------------------------'''
	name = "setSources.xml"
	mode16(admin, name, printpoint, customasources, countrystr)
	'''---------------------------'''

elif mode == 17:
	'''------------------------------
	---Random-Play-------------------
	------------------------------'''
	name = "Random-Play"
	import urllib
	value2 = str(scriptfeatherenceservice_randomL).replace('|',",")

	xbmc.executebuiltin("XBMC.RunPlugin(plugin://%s/?url=%s&mode=5&name=&iconimage=&descs&num=&viewtype=&fanart=)"% (value, urllib.quote_plus(value2)))
	
	for x in range(1,6):
		setProperty('script.featherence.service_random'+str(x), "", type="home")
	text = "value" + space2 + str(value) + newline + \
	'scriptfeatherenceservice_randomL' + space2 + str(scriptfeatherenceservice_randomL) + newline + \
	'value2' + space2 + str(value2)
	
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	#mode17(admin, name, printpoint)
	'''---------------------------'''

elif mode == 18:
	'''------------------------------
	---Generate-Files----------------
	------------------------------'''
	name = "Generate-Files"
	mode18(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 19:
	'''------------------------------
	---setAdvancedSettings-----------
	------------------------------'''
	name = 'setAdvancedSettings'
	Mode19(admin, name, printpoint, scriptfeatherencedebug_Info_TotalSpace, scriptfeatherencedebug_Info_TotalMemory, scriptfeatherencedebug_Info_Model, scriptfeatherencedebug_Info_Intel)
	'''---------------------------'''

elif mode == 20:
	'''------------------------------
	---DOWNLOADS---------------------
	------------------------------'''
	name = "DOWNLOADS"
	mode20(value, admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 21:
	'''------------------------------
	---setPath+----------------------
	------------------------------'''
	name = "SCRAPER-AUTO-SETUP"
	mode21(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 22:
	'''------------------------------
	---ScreenSaver_Music-------------
	------------------------------'''
	name = "ScreenSaver_Music"
	mode22(value, admin, name, printpoint, ScreenSaver_Music)
	'''---------------------------'''

elif mode == 23:
	'''------------------------------
	---Widget------------------------
	------------------------------'''
	name = "Widget"
	if xbmcaddon.Addon('script.featherence.service').getSetting('widget_enable') == 'true':
		if value == '1': xbmc.executebuiltin('ActivateWindow(0)') ; xbmc.sleep(200) ; xbmc.executebuiltin('Action(PageUp)')
		elif value == '2': pass
		from widget import *
		Main()
		'''---------------------------'''

elif mode == 24:
	'''------------------------------
	---Run-Widget--------------------
	------------------------------'''
	name = "Run-Widget"
	value_year = xbmc.getInfoLabel('Window(home).Property('+value+'.Year)')
	systemlanguage = xbmc.getInfoLabel('System.Language')
	value_file = xbmc.getInfoLabel('Window(home).Property('+value+'.File)')
	if 'Movie' in value:
		'''movies'''
		trailers = xbmc.getInfoLabel('Window(home).Property(Widget_Trailers)')
		trailers2 = xbmc.getInfoLabel('Skin.HasSetting(trailers2)')
		value_title = xbmc.getInfoLabel('Window(home).Property('+value+'.Title)')
		value_trailer = xbmc.getInfoLabel('Window(home).Property('+value+'.Trailer)')
		
		if trailers == 'true' or 'trailers' in value2:
			if value_trailer != "": 
				if not trailers2 and value2 != 'trailers2': xbmc.executebuiltin('PlayMedia('+value_trailer+'],1)')
				else: xbmc.executebuiltin('PlayMedia('+value_trailer+'])')
				'''---------------------------'''
			else:
				xbmc.executebuiltin('ActivateWindow(videos,plugin://plugin.video.youtube/?path=/root/search&amp;feed=search&amp;search='+value_title+' '+value_year+' Movie Trailer;,return)')
				notification(localize(79600), value_title, '', 3000)
		else:
			xbmc.executebuiltin('PlayMedia('+value_file+')')
				
	elif 'Episode' in value:
		'''tvshows'''
		value_tvshowtitle = xbmc.getInfoLabel('Window(home).Property('+value+'.TVshowTitle)')
		value_genre = xbmc.getInfoLabel('Window(home).Property('+value+'.Genre)')
		value_plot = xbmc.getInfoLabel('Window(home).Property('+value+'.Plot)')
		value_rating = xbmc.getInfoLabel('Window(home).Property('+value+'.Rating)')
		value_runtime = xbmc.getInfoLabel('Window(home).Property('+value+'.Runtime)')
		value_episode = xbmc.getInfoLabel('Window(home).Property('+value+'.Episode)')
		value_season = xbmc.getInfoLabel('Window(home).Property('+value+'.Season)')
		'''---------------------------'''
		setProperty('TopVideoInformation1', value_runtime, type="home")
		setProperty('TopVideoInformation2', value_year, type="home")
		setProperty('TopVideoInformation3', value_rating, type="home")
		setProperty('TopVideoInformation5', value_plot, type="home")
		setProperty('TopVideoInformation6', value_genre, type="home")
		if systemlanguage == 'Hebrew': setProperty('TopVideoInformation7', '[COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Episode)][/B][/COLOR] $LOCALIZE[20452]: [COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Season)][/B][/COLOR] $LOCALIZE[20373]: [COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Title)][/B][/COLOR] $LOCALIZE[21442]: )', type="home")
		else: setProperty('TopVideoInformation7', '$LOCALIZE[21442]: [COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Title)][/B][/COLOR] S: [COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Season)][/B][/COLOR] E: [COLOR yellow][B]$INFO[Window(Home).Property(RecentEpisode.1.Episode)][/B][/COLOR])', type="home")
		setProperty('TopVideoInformation8', value_tvshowtitle, type="home")
		xbmc.executebuiltin('PlayMedia('+value_file+')')
		xbmc.executebuiltin('AlarmClock(mode10,RunScript(script.featherence.service,,?mode=10&amp;value=),1,silent)')
		

elif mode == 25:
	'''------------------------------
	---Play-Random-Trailers----------
	------------------------------'''
	name = "Play-Random-Trailers"
	mode25(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 26:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode26(admin, name, printpoint)
	'''---------------------------'''

elif mode == 27:
	'''------------------------------
	---Remote-Control----------------
	------------------------------'''
	from remote import *
	name = "Remote-Control"
	
	Remote_Name = getsetting('Remote_Name')
	Remote_Name2 = getsetting('Remote_Name2')
	Remote_Support = getsetting('Remote_Support')
	Remote_TestingTime = getsetting('Remote_TestingTime')
	Remote_LastDate = getsetting('Remote_LastDate')
	remotes_path = os.path.join(addonPath, 'resources', 'remotes', '')
	
	Remote_Support = setRemote_Support(value, Remote_Name, Remote_Support)

	if Remote_Support != "true":
		if value != '0': dialogok(addonString(32032).encode('utf-8'), "- Make sure you have IR adapter!", "-Make sure your OS is supported!","For Support see Facebook page or related forum!")
		sys.exit()

	if Remote_Name == "":
		printpoint = printpoint + "1"
		setProperty('Remote_Name', "", type="home")
		returned = dialogyesno(addonString(32025).encode('utf-8'), addonString(32024).encode('utf-8') + '[CR]' + addonString(19194).encode('utf-8'))
		if returned == 'skip': printpoint = printpoint + "9"
	
	if not "9" in printpoint:
		if value != '0' or Remote_Name == "":
			printpoint = printpoint + "2"
			printpoint = setRemote_Name(Remote_Name, Remote_TestingTime, remotes_path)
			
		else:
			if Remote_Name != "":
				printpoint = printpoint + "3"
				Activate(Remote_Name, Remote_Name2, Remote_TestingTime, remotes_path)
				#if not systemplatformwindows: os.system('sh /storage/.kodi/addons/script.htpt.remote/remote.sh')
				#print printfirst + "remote.sh; remote type: " + Remote_Name
				if datenowS == Remote_LastDate:
					returned_Dialog, returned_Header, returned_Message = checkDialog(admin)
					if returned_Dialog == "": dialogok(addonString(32025).encode('utf-8'), addonString(32034).encode('utf-8'), "", addonString(32035).encode('utf-8'))
				
	setsetting('Remote_Name2',"")
	
	if not "9" in printpoint and 1 + 1 == 3:
		xbmc.sleep(1000)
		if systemplatformlinux or systemplatformlinuxraspberrypi:
			Remote_Name = getsetting('Remote_Name')
			if Remote_Name != "None": os.system('sh /storage/.kodi/addons/script.htpt.remote/remote.sh')
		
		Remote_Name2 = getsetting('Remote_Name')
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	print printfirst + "default.py_LV" + printpoint + space + "Remote_Name" + space2 + Remote_Name + space + "Remote_Name2" + space2 + Remote_Name2
	'''---------------------------'''

elif mode == 28:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "AutoView"
	mode28(value, value2, value3, name, printpoint)
	'''---------------------------'''

elif mode == 29:
	'''------------------------------
	---Dialog-Select-Skin------------
	------------------------------'''
	name = "Dialog-Select-Skin"
	mode29(value, value2, value3, value4, name, printpoint)
	'''---------------------------'''
	
elif mode == 30:
	'''------------------------------
	---------------------------------
	------------------------------'''
	pass
	mode30(admin, name)
	'''---------------------------'''	

elif mode == 31:
	'''------------------------------
	---diaogtextviewer---------------
	------------------------------'''
	name = "diaogtextviewer"
	mode31(value, value2, value3, value4, admin, name, printpoint)
	'''---------------------------'''

elif mode == 32:
	'''------------------------------
	---MISCS-------------------------
	------------------------------'''
	name = 'MISCS'
	mode32(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 33:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode33(admin, name, printpoint)
	'''---------------------------'''

elif mode == 34:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	from shared_modules3 import *
	setCustomFanart(value, value2, admin, 'setCustomFanart', printpoint)
	xbmc.executebuiltin('XBMC.Container.Update(%s)' % containerfolderpath )
	'''---------------------------'''

elif mode == 35:
	'''------------------------------
	---Remove-Custom-Fanart----------
	------------------------------'''
	setsetting_custom1(value, 'Fanart_Custom' + str(value2),"")
	xbmc.executebuiltin('XBMC.Container.Update(%s)' % containerfolderpath )
	'''---------------------------'''

elif mode == 36:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode36(admin, name, printpoint)
	'''---------------------------'''

elif mode == 37:
	'''------------------------------
	----------------------------
	------------------------------'''
	name = ""
	mode37(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 39:
	'''------------------------------
	---Reset-Network-Settings--------
	------------------------------'''
	name = "Reset-Network-Settings"
	mode39(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 40:
	'''------------------------------
	---Reset-Skin-Settings-----------
	------------------------------'''
	name = localize(79517)
	mode40(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 41:
	'''------------------------------
	---Network-Settings--------------
	------------------------------'''
	name = 'Network-Settings'
	mode41(admin, name, printpoint)
	'''---------------------------'''

elif mode == 43:
	'''------------------------------
	---CONFIGURATE-SCRAPERS----------
	------------------------------'''
	setsetting_custom1('script.featherence.service.fix','Fix_100',"true")
	setsetting_custom1('script.featherence.service.fix','Fix_101',"true")
	xbmc.executebuiltin('RunScript(script.featherence.service.fix,,?mode=3)')
	xbmc.executebuiltin('ActivateWindow(0)')
	'''---------------------------'''

elif mode == 44:
	'''------------------------------
	----OverClock-Your-PI------------
	------------------------------'''
	name = 'OverClock-Your-PI'
	mode44(admin, name)
	'''---------------------------'''

elif mode == 45:
	'''------------------------------
	---STABILITY-TEST----------------
	------------------------------'''
	name = 'STABILITY-TEST'
	mode45(admin, name)
	'''---------------------------'''

elif mode == 46:
	'''------------------------------
	---OVERCLOCKING------------------
	------------------------------'''
	name = 'OVERCLOCKING'
	mode46(admin,name)
	'''---------------------------'''

elif mode == 47:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode47(admin, name, printpoint)
	'''---------------------------'''

elif mode == 48:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode48(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 49:
	'''------------------------------
	---SCRAPER-FIX-------------------
	------------------------------'''
	name = 'SCRAPER-FIX'
	mode49(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 50:
	'''------------------------------
	---SOFT-RESTART------------------
	------------------------------'''
	name = 'SOFT-RESTART'
	mode50(admin, name, printpoint)
	'''---------------------------'''

elif mode == 51:
	'''------------------------------
	---RESTART-----------------------
	------------------------------'''
	name = 'RESTART'
	mode51(admin, name, printpoint)
	'''---------------------------'''

elif mode == 52:
	'''------------------------------
	---SUSPEND-----------------------
	------------------------------'''
	name = 'SUSPEND'
	mode52(admin, name, printpoint)
	'''---------------------------'''

elif mode == 53:
	'''------------------------------
	---POWEROFF----------------------
	------------------------------'''
	name = 'POWEROFF'
	mode53(admin, name, printpoint)
	'''---------------------------'''

elif mode == 54:
	'''------------------------------
	---QUIT--------------------------
	------------------------------'''
	name = 'QUIT'
	mode54(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 57:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode57(admin, name, printpoint)
	'''---------------------------'''

elif mode == 58:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode58(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 59:
	'''------------------------------
	---Choose-Country----------------
	------------------------------'''
	name = 'Choose-Country'
	mode59(admin, name, printpoint)
	'''---------------------------'''

elif mode == 61:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode61(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 62:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode62(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 63:
	'''------------------------------
	---Texture-Cache-Removal---------
	------------------------------'''
	name = 'Texture-Cache-Removal'
	mode63(admin, name)
	'''---------------------------'''

elif mode == 64:
	'''------------------------------
	---Extract from file-------------
	------------------------------'''
	name = 'Extract from file'
	mode64(value, admin, name, printpoint)
	'''---------------------------'''

elif mode == 65:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode65(admin, name, printpoint)
	'''---------------------------'''

elif mode == 66:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode66(admin, name, printpoint)
	'''---------------------------'''

elif mode == 67:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode67(admin, name, printpoint)
	'''---------------------------'''

elif mode == 68:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode68(admin, name, printpoint)
	'''---------------------------'''

elif mode == 69:
	'''------------------------------
	---TIPS--------------------------
	------------------------------'''
	name = "TIPS"
	mode69(value, admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 70:
	'''------------------------------
	---ExtendedInfo------------------
	------------------------------'''
	name = 'ExtendedInfo'
	mode70(value, admin, name, printpoint, property_temp)
	'''---------------------------'''

elif mode == 71:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode71(admin, name, printpoint)
	'''---------------------------'''

elif mode == 72:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode72(admin, name, printpoint)
	'''---------------------------'''

elif mode == 73:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode73(admin, name, printpoint)
	'''---------------------------'''

elif mode == 74:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode74(admin, name, printpoint)
	'''---------------------------'''

elif mode == 75:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode75(admin, name, printpoint)
	'''---------------------------'''

elif mode == 76:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode76(admin, name, printpoint)
	'''---------------------------'''

elif mode == 77:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode77(admin, name, printpoint)
	'''---------------------------'''

elif mode == 78:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode78(admin, name, printpoint)
	'''---------------------------'''

elif mode == 79:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode79(admin, name, printpoint)
	'''---------------------------'''

elif mode == 80:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode80(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 81:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode81(admin, name, printpoint)
	'''---------------------------'''

elif mode == 82:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode82(admin, name, printpoint)
	'''---------------------------'''

elif mode == 83:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode83(admin, name, printpoint)
	'''---------------------------'''

elif mode == 84:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode84(admin, name, printpoint)
	'''---------------------------'''

elif mode == 85:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode85(admin, name, printpoint)
	'''---------------------------'''

elif mode == 86:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode86(admin, name, printpoint)
	'''---------------------------'''

elif mode == 87:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode87(admin, name, printpoint)
	'''---------------------------'''

elif mode == 88:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode88(admin, name, printpoint)
	'''---------------------------'''

elif mode == 89:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode89(admin, name, printpoint)
	'''---------------------------'''

elif mode == 90:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode90(admin, name, printpoint)
	'''---------------------------'''
	
elif mode == 91:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode91(admin, name, printpoint)
	'''---------------------------'''

elif mode == 92:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode92(admin, name, printpoint)
	'''---------------------------'''

elif mode == 93:
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode93(admin, name, printpoint)
	'''---------------------------'''

elif mode >= 100 and mode <= 149:
	'''------------------------------
	---?-100-149---------------------
	------------------------------'''
	if mode == 100:
		'''------------------------------
		---STARTUP-TRIGGER---------------
		------------------------------'''
		name = "STARTUP-TRIGGER"
		mode100(admin, name)
		'''---------------------------'''
	
	elif mode == 101:
		'''------------------------------
		---TOTAL-MOUSE-------------------
		------------------------------'''
		name = "TOTAL-MOUSE"
		mode101(value, admin, name)
		'''---------------------------'''
	
	elif mode == 102:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode102(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 103:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode103(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 104:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode104(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 105:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode105(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 106:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode106(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 107:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode107(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 108:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode108(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 109:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode109(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 110:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode110(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 111:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode111(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 112:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode112(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 113:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode113(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 114:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode114(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 115:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode115(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 116:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode116(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 117:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode117(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 118:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode118(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 119:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode119(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 120:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode120(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 121:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode121(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 122:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode122(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 123:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode123(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 124:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode124(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 125:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode125(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 126:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode126(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 127:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode127(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 128:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode128(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 129:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode129(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 130:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode130(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 131:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode131(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 132:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode132(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 133:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode133(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 134:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode134(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 135:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode135(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 136:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode136(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 137:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode137(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 138:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode138(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 139:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode139(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 140:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode140(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 141:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode141(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 142:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode142(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 143:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode143(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 144:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode144(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 145:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode145(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 146:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode146(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 147:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode147(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 148:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode148(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 149:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode149(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 150 and mode <= 199:
	'''------------------------------
	---?-150-199---------------------
	------------------------------'''
	if mode == 150:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode150(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 151:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode151(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 152:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode152(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 153:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode153(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 154:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode154(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 155:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode155(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 156:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode156(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 157:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode157(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 158:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode158(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 159:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode159(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 160:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode160(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 161:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode161(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 162:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode162(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 163:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode163(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 164:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode164(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 165:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode165(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 166:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode166(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 167:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode167(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 168:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode168(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 169:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode169(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 170:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode170(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 171:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode171(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 172:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode172(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 173:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode173(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 174:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode174(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 175:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode175(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 176:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode176(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 177:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode177(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 178:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode178(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 179:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode179(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 180:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode180(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 181:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode181(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 182:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode182(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 183:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode183(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 184:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode184(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 185:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode185(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 186:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode186(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 187:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode187(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 188:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode188(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 189:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode189(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 190:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode190(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 191:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode191(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 192:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode192(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 193:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode193(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 194:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode194(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 195:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode195(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 196:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode196(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 197:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode197(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 198:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode198(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 199:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode199(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 200 and mode <= 249:
	'''------------------------------
	---CustomHomeCustomizer-200-249--
	------------------------------'''
	#from variables2 import *
	if mode == 200:
		'''------------------------------
		---DIALOG-SELECT-(10-100)--------
		------------------------------'''
		name = "DIALOG-SELECT-(10-100)"
		mode200(value, admin, name, printpoint)
		'''---------------------------'''	
	
	elif mode == 201:
		'''------------------------------
		---RESET-TO-DEFAULT--------------
		------------------------------'''
		name = "RESET-TO-DEFAULT"
		mode201(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 202:
		'''------------------------------
		---CHOOSE-COLORS-2---------------
		------------------------------'''
		name = "CHOOSE-COLORS-2"
		mode202(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 203:
		'''------------------------------
		---Save and Load your skin design
		------------------------------'''
		from variables2 import *
		name = "Save and Load your skin design"
		extra = "" ; formula = "" ; formula_ = "" ; path = "" ; filename = "" ; returned = "" ; returned2 = ""
		list = ['-> (Exit)', 'Save', 'Load', 'Templates'] ; list2 = [] ; custommediaL = []
		
		if list != []:
			returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
			
			if returned == -1: printpoint = printpoint + "9"
			elif returned == 0: printpoint = printpoint + "8"
			else: printpoint = printpoint + "7"
			'''---------------------------'''
			
		if ("7" in printpoint or value != "") and not "8" in printpoint and not "9" in printpoint:
			
			if returned == 1 or returned == 2: path = featherenceservice_addondata_path
			elif returned == 3 or (returned == "" and value == "Templates"): path = os.path.join(featherenceservice_path, 'resources', 'skin_templates', '')
			else: path = ""
			
			list2 = ['-> (Exit)'] ; list2_ = ['-> (Exit)']
			if returned == 1:
				list2.append('New')
				list2_.append('New')
			
			if path != "":
				'''read existing files'''
				filesT = {}
				for files in os.listdir(path):
					filesname = ""
					if '.zip' in files and not '.txt' in files:
						if 'Featherence_' in files:
							filesname = regex_from_to(files, "Featherence_", ".zip", excluding=True)
							if filesname != "" and filesname != None:
								filesT_ = { filesname: files }
								filesT.update(filesT_)
								list2.append(filesname)
								filedate = getFileAttribute(1, path + files, option="1")
								list2_.append(filesname + space + '-(' + str(filedate) + ')')
								extra = 'files' + space2 + to_utf8(files) + newline + 'filesname' + space2 + to_utf8(filesname)
								#print extra 
								'''---------------------------'''
			
			returned2, value2 = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list2_,0)
			
			if returned2 == -1: printpoint = printpoint + "9"
			elif returned2 == 0: printpoint = printpoint + "8"
			else: printpoint = printpoint + "7"
			
			if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
				if returned == 1: printpoint = printpoint + "A" #SAVE
				elif returned == 2 or (returned == "" and value == "Templates"): printpoint = printpoint + "B" #LOAD
				elif returned == 3: printpoint = printpoint + "C" #DEFAULT
				if "A" in printpoint:
					'''------------------------------
					---Save--------------------------
					------------------------------'''
					if returned2 > 1:
						yesno = dialogyesno('Overwrite' + space + str(list2[returned2]) + '?','Choose YES to continue')
						if yesno == 'skip': printpoint = printpoint + '9'
					if not '9' in printpoint:
						Custom1000(str(list[returned]),0,str(list2[returned2]),5)
						
						formula = ""
						formula = "Skin.Theme=2" + skincurrenttheme
						for i in range(18,20):
							x = labelT.get('label'+str(i))
							if x != "" and x != None:
								formula = formula + newline + 'label'+str(i)+'=0' + str(x)
								x = actionT.get('action'+str(i))
								formula = formula + newline + 'action'+str(i)+'=0' + str(x)
								x = offT.get('off'+str(i))
								formula = formula + newline + 'off'+str(i)+'=1' + str(x)
								x = colorT.get('color'+str(i))
								formula = formula + newline + 'color'+str(i)+'=0' + str(x)
								x = iconT.get('icon'+str(i))
								x2, x2_ = TranslatePath(x)
								formula, custommediaL, = GeneratePath('icon'+str(i)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
								x = backgroundT.get('background'+str(i))
								x2, x2_ = TranslatePath(x)
								formula, custommediaL, = GeneratePath('background'+str(i)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
						for i in range(90,120):
							x = idT.get('id'+str(i))
							if x != "" and x != None:
								formula = formula + newline + 'id'+str(i)+'=0' + str(x)
								x = labelT.get('label'+str(i))
								if x != "" and x != None:
									formula = formula + newline + 'label'+str(i)+'=0' + str(x)
									x = actionT.get('action'+str(i))
									formula = formula + newline + 'action'+str(i)+'=0' + str(x)
									x = offT.get('off'+str(i))
									formula = formula + newline + 'off'+str(i)+'=1' + str(x)
									x = colorT.get('color'+str(i))
									formula = formula + newline + 'color'+str(i)+'=0' + str(x)
									x = subT.get('sub'+str(i))
									formula = formula + newline + 'sub'+str(i)+'=1' + str(x)
									x = iconT.get('icon'+str(i))
									x2, x2_ = TranslatePath(x)
									formula, custommediaL, = GeneratePath('icon'+str(i)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
									x = backgroundT.get('background'+str(i))
									x2, x2_ = TranslatePath(x)
									formula, custommediaL, = GeneratePath('background'+str(i)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
									
									for i2 in range(100,110):
										x = label_T.get('label'+str(i)+'_'+str(i2))
										if x != "" and x != None:
											formula = formula + newline + 'label'+str(i)+'_'+str(i2)+'=0' + str(x)
											x = action_T.get('action'+str(i)+'_'+str(i2))
											formula = formula + newline + 'action'+str(i)+'_'+str(i2)+'=0' + str(x)
											x = off_T.get('off'+str(i)+'_'+str(i2))
											formula = formula + newline + 'off'+str(i)+'_'+str(i2)+'=1' + str(x)
											x = icon_T.get('icon'+str(i)+'_'+str(i2))
											x2, x2_ = TranslatePath(x)
											formula, custommediaL, = GeneratePath('icon'+str(i)+'_'+str(i2)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
								else: extra = extra + newline + 'label not exists!' + space + 'x' + space2 + str(x)
							else: extra = extra + newline + 'id not exists!' + space + 'x' + space2 + str(x)
						Custom1000(str(list[returned]),50,str(list2[returned2]),5)
						for y in list1:
							x = xbmc.getInfoLabel('Skin.HasSetting('+y+')')
							formula = formula + newline + y+'=1' + str(x)
							'''---------------------------'''
						
						for y in list0:
							x = xbmc.getInfoLabel('Skin.String('+y+')')
							formula = formula + newline + y+'=0' + str(x)
							'''---------------------------'''
							
						for y in list0c:
							x = xbmc.getInfoLabel('Skin.String('+y+')')
							x2 = xbmc.getInfoLabel('Skin.String('+y+'.name)')
							formula = formula + newline + y+'=0' + str(x)
							formula = formula + newline + y+'.name'+'=0' + str(x2)
							'''---------------------------'''
						
						Custom1000(str(list[returned]),70,str(list2[returned2]),5)
						for y in list0c2:
							x = xbmc.getInfoLabel('Skin.String('+y+')')
							formula = formula + newline + y+'=0' + str(x)
							'''---------------------------'''
						
						for y in list0o:
							x = xbmc.getInfoLabel('Skin.String('+y+')')
							formula = formula + newline + y+'=0' + str(x)
							'''---------------------------'''
						
						for y in list1l:
							x = xbmc.getInfoLabel('Skin.HasSetting('+y+')')
							formula = formula + newline + y+'=1' + str(x)
							'''---------------------------'''
						
						for y in list0l:
							x = xbmc.getInfoLabel('Skin.String('+y+')')
							formula = formula + newline + y+'=0' + str(x)
							'''---------------------------'''
							
						if returned2 == 1: filename = ""
						else:
							filename = str(list2[returned2])
						Custom1000(str(list[returned]),90,str(list2[returned2]),5)
						filename = dialogkeyboard(filename, localize(21821), 0, "", "", "") #Description
						
						if filename != 'skip' and filename != "":
							formula = to_utf8(formula)
							
							write_to_file(featherenceserviceaddondata_media_path + "Featherence_" + ".txt", str(formula), append=False, silent=True, utf8=False) ; xbmc.sleep(200)
							if not os.path.exists(featherenceserviceaddondata_media_path + "Featherence_" + ".txt"):
								notification_common('17')
								extra = extra + newline + featherenceserviceaddondata_media_path + "Featherence_" + ".txt" + space + 'Is not found!'
							else:
								removefiles(featherenceserviceaddondata_media_path + 'Featherence_' + to_unicode(list2[returned2]) + '.zip')
								zipname = featherenceservice_addondata_path + 'Featherence_' + str(filename).decode('utf-8')
								if custommediaL == []:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=['Featherence_.txt'], filteroff=[], level=0, append=False, ZipFullPath=False, temp=False)
								else:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=['Featherence_.txt'], filteroff=[], level=0, append=False, ZipFullPath=False, temp=True)
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=custommediaL, filteroff=[], level=3, append='End', ZipFullPath=False, temp=True)
									'''---------------------------'''
								Custom1000(str(list[returned]),100,str(list2[returned2]),4)
						else: notification_common('9')
				
				elif "B" in printpoint or "C" in printpoint:
					'''------------------------------
					---Load/Templates----------------
					------------------------------'''
					filename = str(list2[returned2])
					file = filesT.get(filename)
					
					if file == "" or file == None:
						notification("Invalid file!", "", "", 4000)
					elif not os.path.exists(path + file):
						'''nothing to load'''
						notification("There is no data to load!", "You should create a save session", "", 4000)
					else:
						#formula_ = formula_.split(',')
						#formula_ = CleanString(formula_, filter=[])
						if os.path.exists(featherenceserviceaddondata_media_path + 'Featherence_.txt'):
							removefiles(featherenceserviceaddondata_media_path + 'Featherence_.txt')
						Custom1000(str(list[returned]),10,str(list2[returned2]),5)
						ExtractAll(path + file, featherenceserviceaddondata_media_path) ; Custom1000(str(list[returned]),20,str(list2[returned2]),10)
						
						if not os.path.exists(featherenceserviceaddondata_media_path + 'Featherence_.txt'):
							notification("Featherence_.txt is missing!", "Check your zip file!", "", 4000)
						else:
							Custom1000(str(list[returned]),0,str(list2[returned2]),5)
							printpoint = printpoint + "V"
							mode201('9', admin, name, '') ; xbmc.sleep(1500) #Clear current strings #Give some time to finalise the cleaning
							
							import fileinput
							count = 0
							for line in fileinput.input(featherenceserviceaddondata_media_path + 'Featherence_.txt'):
								count += 1
								if count >= 10:
									count = 0
									property_1000progress = xbmc.getInfoLabel('Window(home).Property(1000progress)')
									try: test = int(property_1000progress) + 2
									except: property_1000progress = 20
									Custom1000(str(list[returned]),int(property_1000progress) + 2,str(list2[returned2]),5)
								x = "" ; x1 = "" ; x2 = "" ; x3 = ""
								if "=0" in line:
									'''Skin.String'''
									x = line.replace("=0","=",1)
									x1 = find_string(x, "", "=")
									x2 = find_string(x, "=", "")
									x1 = x1.replace("=","")
									x2 = x2.replace("=","",1)
									x2 = x2.replace("\n","")
									if x2 != None:
										setSkinSetting('0', str(x1), str(x2))
									
								elif "=1" in line:
									'''Skin.HasSetting'''
									x = line.replace("=1","=", 1)
									x1 = find_string(x, "", "=")
									x2 = find_string(x, "=", "")
									x1 = x1.replace("=","", 1)
									x2 = x2.replace("=","", 1)
									x2 = x2.replace("\n","")
									if x2 == "" or x2 == 'None' or x2 == None: x3 = "false"
									else:
										x3 = "true" ; x2 = "*" + x2 + "*"
									setSkinSetting('1', str(x1), str(x3))
								
								elif "=2" in line:
									'''xbmc.executebuiltin'''
									x = line.replace("=2","=")
									x1 = find_string(x, "", "=")
									x2 = find_string(x, "=", "")
									x1 = x1.replace("=","")
									x2 = x2.replace("=","")
									x2 = x2.replace("\n","")
									
									if x1 == "Skin.Theme":
										pass
										#xbmc.executebuiltin('Skin.Theme(SKINDEFAULT)')
										#xbmc.executehttpapi( "SetGUISetting(3;lookandfeel.skintheme;%s)"  % x2 )
										#if x2 == "SKINDEFAULT": xbmc.executebuiltin('Skin.Theme(SKINDEFAULT)')
										#else: notification(str(x2),"","",3000)
									#xbmc.executebuiltin(''+x1+'('+ x2 +')')
									#xbmc.executebuiltin('AlarmClock(delayskinupdate, '+x1+'('+ x2 +'), 00:02, silent)')
								else: pass
								
								#print "line" + space2 + str(line)
								#print "line" + space2 + str(line) + space + "x" + space2 + str(x) + space + "x1" + space2 + str(x1) + space + "x2" + space2 + str(x2) + space + "x3" + space2 + str(x3)
								extra = extra + newline + space + "line" + space2 + str(line) + space + "x" + space2 + str(x) + space + "x1" + space2 + str(x1) + space + "x2" + space2 + str(x2) + space + "x3" + space2 + str(x3) #Causing Error!
								'''---------------------------'''
							
							Custom1000(str(list[returned]),100,str(list2[returned2]),3)
				
				if "V" in printpoint:
					xbmc.sleep(500)
					xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value=_)')
					xbmc.executebuiltin('Action(Back)')
					xbmc.sleep(2000)
					returned_ = dialogyesno('Your current language is %s' % (systemlanguage), 'Are the buttons in %s?' % (systemlanguage))
					if returned_ == 'skip':
						xbmc.sleep(3000)
						xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value=LABEL)')
					#ReloadSkin(admin)
					#xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=32&value=5)')
					if filename == 'Classico Plus':
						dialogok("Kodi's Tweaks are avaialble!", "The loaded package %s contain tweaks to make your Kodi work better in overall." % (filename),"Choose YES to proceed with the tweaks or NO to finish the skin image loading.","")
						returned_ = dialogyesno('Would you like to use the tweak?',"")
						if returned_ == 'skip': pass
						else: mode18('4', admin, name, printpoint)
						'''---------------------------'''
				else:
					pass
					Custom1000(str(list[returned]),100,str(list2[returned2]),0)
				
		text = "path" + space2 + str(path) + newline + \
		"list" + space2 + str(list) + space + 'returned' + space2 + str(returned) + newline + \
		"list2" + space2 + str(list2) + space + 'returned2' + space2 + str(returned2) + newline + \
		"file" + space2 + to_utf8(str(file)) + newline + \
		"filename" + space2 + to_utf8(str(filename)) + newline + \
		"formula" + space2 + str(formula) + space + "formula_" + space2 + str(formula_) + newline + \
		"custommediaL" + space2 + str(custommediaL) + newline + \
		"extra" + space2 + to_utf8(extra)
		printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
		'''---------------------------'''
	
	elif mode == 204:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode204(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 205:
		'''------------------------------
		---SET-STARTUP-WINDOW------------
		------------------------------'''
		name = "SET-STARTUP-WINDOW"
		mode205(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 206:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode206(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 207:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode207(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 208:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode208(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 209:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode209(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 210:
		'''------------------------------
		---MOVE-ITEM---------------------
		------------------------------'''
		name = "MOVE-ITEM"
		mode210(value, admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 211:
		'''------------------------------
		---Create-New-Item---------------
		------------------------------'''
		name = "Create-New-Item"
		mode211(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 212:
		'''------------------------------
		---REMOVE-ITEM-------------------
		------------------------------'''
		name = "REMOVE-ITEM"
		mode212(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 213:
		'''------------------------------
		---Includes_HomeContent----------
		------------------------------'''
		name = "Includes_HomeContent"
		mode213(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 214:
		'''------------------------------
		---Create-New-Sub-Item-----------
		------------------------------'''
		name = "Create-New-Sub-Item"
		mode214(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 215:
		'''------------------------------
		---SET-DEFAULT-BUTTONS-----------
		------------------------------'''
		name = "SET-DEFAULT-BUTTONS"
		if property_reloadskin == "": mode215(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 216:
		'''------------------------------
		---REMOVE-SUB-ITEM---------------
		------------------------------'''
		name = "REMOVE-SUB-ITEM"
		mode216(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 217:
		'''------------------------------
		---setDefaultLabels--------------
		------------------------------'''
		name = "setDefaultLabels"
		mode217(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 218:
		'''------------------------------
		---editButtonProprties-----------
		------------------------------'''
		name = "editButtonProprties"
		mode218(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 219:
		'''------------------------------
		---SET-POSITION------------------
		------------------------------'''
		name = "SET-POSITION"
		mode219(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 220:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode220(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 221:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode221(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 222:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode222(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 223:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode223(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 224:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode224(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 225:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode225(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 226:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode226(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 227:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode227(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 228:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode228(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 229:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode229(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 230:
		'''------------------------------
		---COLOR-PICKER------------------
		------------------------------'''
		name = "COLOR-PICKER"
		mode230(value, admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 231:
		'''------------------------------
		---INSTALL-ADDON-----------------
		------------------------------'''
		name = "INSTALL-ADDON"
		mode231(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 232:
		'''------------------------------
		---ACTION-BUTTON-----------------
		------------------------------'''
		name = "ACTION-BUTTON"
		mode232(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 233:
		'''------------------------------
		---Add-Fanart--------------------
		------------------------------'''
		name = "Add-Fanart"
		mode233(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 235:
		'''------------------------------
		---Default-Icon/Background-------
		------------------------------'''
		name = "Default-Icon/Background"
		mode235(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 236:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode236(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 237:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode237(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 238:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode238(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 239:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode239(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 240:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode240(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 241:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode241(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 242:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode242(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 243:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode243(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 244:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode244(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 245:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode245(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 246:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode246(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 247:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode247(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 248:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode248(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 249:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode249(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 250 and mode <= 299:
	'''------------------------------
	---?-250-299---------------------
	------------------------------'''
	if mode == 250:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode250(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 251:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode251(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 252:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode252(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 253:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode253(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 254:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode254(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 255:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode255(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 256:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode256(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 257:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode257(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 258:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode258(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 259:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode259(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 260:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode260(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 261:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode261(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 262:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode262(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 263:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode263(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 264:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode264(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 265:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode265(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 266:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode266(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 267:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode267(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 268:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode268(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 269:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode269(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 270:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode270(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 271:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode271(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 272:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode272(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 273:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode273(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 274:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode274(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 275:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode275(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 276:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode276(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 277:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode277(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 278:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode278(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 279:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode279(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 280:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode280(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 281:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode281(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 282:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode282(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 283:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode283(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 284:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode284(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 285:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode285(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 286:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode286(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 287:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode287(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 288:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode288(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 289:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode289(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 290:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode290(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 291:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode291(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 292:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode292(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 293:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode293(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 294:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode294(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 295:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode295(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 296:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode296(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 297:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode297(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 298:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode298(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 299:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode299(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 300 and mode <= 349:
	'''------------------------------
	---LEFT-MENU-300-349-------------
	------------------------------'''
	if mode == 300:
		'''------------------------------
		---SEARCH-SDAROT-TV--------------
		------------------------------'''
		name = "SEARCH-SDAROT-TV"
		mode300(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 305:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode305(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 306:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode306(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 307:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode307(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 308:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode308(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 309:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode309(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 310:
		'''------------------------------
		---SPORT-1-LIVE------------------
		------------------------------'''
		name = "SPORT-1-LIVE"
		mode310(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 311:
		'''------------------------------
		---SPORT-2-LIVE------------------
		------------------------------'''
		name = "SPORT-2-LIVE"
		mode311(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 312:
		'''------------------------------
		---SPORT-LIVE-3------------------
		------------------------------'''
		name = "SPORT-LIVE-3"
		mode312(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 313:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode313(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 314:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode314(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 315:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode315(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 316:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode316(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 317:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode317(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 318:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode318(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 319:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode319(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 320:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode320(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 321:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode321(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 322:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode322(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 323:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode323(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 324:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode324(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 325:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode325(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 326:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode326(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 327:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode327(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 328:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode328(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 329:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode329(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 330:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode330(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 331:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode331(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 332:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode332(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 333:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode333(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 334:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode334(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 335:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode335(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 336:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode336(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 337:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode337(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 338:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode338(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 339:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode339(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 340:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode340(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 341:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode341(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 342:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode342(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 343:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode343(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 344:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode344(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 345:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode345(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 346:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode346(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 347:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode347(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 348:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode348(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 349:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode349(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 350 and mode <= 399:
	'''------------------------------
	---HELP-WINDOW-350-399-----------
	------------------------------'''
	if mode == 350:
		'''------------------------------
		---AIRPLAY-BUTTON----------------
		------------------------------'''
		pass
		'''---------------------------'''
	
	elif mode == 352:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode352(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 353:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode353(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 354:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode354(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 355:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode355(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 356:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode356(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 357:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode357(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 358:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode358(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 359:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode359(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 360:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode360(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 361:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode361(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 362:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode362(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 363:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode363(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 364:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode364(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 365:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode365(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 366:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode366(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 367:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode367(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 368:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode368(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 369:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode369(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 370:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode370(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 371:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode371(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 372:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode372(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 373:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode373(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 374:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode374(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 375:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode375(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 376:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode376(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 377:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode377(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 378:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode378(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 379:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode379(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 380:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode380(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 381:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode381(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 382:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode382(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 383:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode383(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 384:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode384(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 385:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode385(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 386:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode386(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 387:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode387(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 388:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode388(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 389:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode389(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 390:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode390(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 391:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode391(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 392:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode392(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 393:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode393(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 394:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode394(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 395:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode395(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 396:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode396(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 397:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode397(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 398:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode398(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 399:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode399(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 400 and mode <= 449:
	'''------------------------------
	---?-400-449---------------------
	------------------------------'''
	if mode == 400:
		'''------------------------------
		---?---------------
		------------------------------'''
		name = ""
		mode400(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 401:
		'''------------------------------
		---?-------------------
		------------------------------'''
		name = ""
		mode401(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 402:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode402(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 403:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode403(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 404:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode404(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 405:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode405(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 406:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode406(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 407:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode407(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 408:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode408(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 409:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode409(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 410:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode410(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 411:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode411(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 412:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode412(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 413:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode413(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 414:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode414(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 415:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode415(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 416:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode416(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 417:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode417(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 418:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode418(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 419:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode419(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 420:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode420(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 421:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode421(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 422:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode422(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 423:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode423(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 424:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode424(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 425:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode425(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 426:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode426(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 427:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode427(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 428:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode428(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 429:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode429(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 430:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode430(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 431:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode431(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 432:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode432(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 433:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode433(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 434:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode434(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 435:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode435(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 436:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode436(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 437:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode437(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 438:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode438(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 439:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode439(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 440:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode440(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 441:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode441(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 442:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode442(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 443:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode443(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 444:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode444(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 445:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode445(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 446:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode446(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 447:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode447(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 448:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode448(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 449:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode449(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 450 and mode <= 499:
	'''------------------------------
	---?-450-499---------------------
	------------------------------'''
	if mode == 450:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode450(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 451:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode451(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 452:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode452(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 453:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode453(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 454:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode454(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 455:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode455(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 456:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode456(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 457:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode457(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 458:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode458(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 459:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode459(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 460:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode460(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 461:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode461(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 462:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode462(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 463:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode463(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 464:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode464(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 465:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode465(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 466:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode466(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 467:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode467(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 468:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode468(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 469:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode469(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 470:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode470(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 471:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode471(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 472:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode472(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 473:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode473(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 474:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode474(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 475:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode475(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 476:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode476(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 477:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode477(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 478:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode478(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 479:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode479(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 480:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode480(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 481:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode481(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 482:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode482(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 483:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode483(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 484:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode484(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 485:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode485(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 486:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode486(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 487:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode487(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 488:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode488(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 489:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode489(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 490:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode490(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 491:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode491(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 492:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode492(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 493:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode493(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 494:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode494(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 495:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode495(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 496:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode496(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 497:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode497(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 498:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode498(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 499:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode499(admin, name, printpoint)
		'''---------------------------'''


elif mode >= 500 and mode <= 549:
	'''------------------------------
	---HOME-BUTTONS-(1)-500-549------
	------------------------------'''
	if custom1138W: xbmc.executebuiltin('Dialog.Close(1138)')
	if mode == 500:
		'''------------------------------
		---?----------------
		------------------------------'''
		name = ""
		mode500(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 510:
		'''------------------------------
		---GAMES-BUTTON------------------
		------------------------------'''
		name = "GAMES-BUTTON"
		mode510(value, admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 511:
		'''------------------------------
		---TRAILERS-BUTTON---------------
		------------------------------'''
		name = "TRAILERS-BUTTON"
		mode511(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 512:
		'''------------------------------
		---INTERNET-BUTTON---------------
		------------------------------'''
		name = "INTERNET-BUTTON"
		mode512(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 513:
		'''------------------------------
		---VIDEOS-BUTTON-----------------
		------------------------------'''
		name = "VIDEOS-BUTTON"
		mode513(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 514:
		'''------------------------------
		---MUSIC-BUTTON------------------
		------------------------------'''
		name = "MUSIC-BUTTON"
		mode514(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 515:
		'''------------------------------
		---KIDS-BUTTON-------------------
		------------------------------'''
		name = "KIDS-BUTTON"
		mode515(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 516:
		'''------------------------------
		---FAVOURITES-BUTTON-------------
		------------------------------'''
		name = "FAVOURITES-BUTTON"
		mode516(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 517:
		'''------------------------------
		---LIVE-TV-BUTTON----------------
		------------------------------'''
		name = "LIVE-TV-BUTTON"
		mode517(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 518:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode518(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 519:
		'''------------------------------
		---DOCU-BUTTON-------------------
		------------------------------'''
		name = "DOCU-BUTTON"
		mode519(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 520:
		'''------------------------------
		---ADULT-MOVIE-BUTTON------------
		------------------------------'''
		name = "ADULT-MOVIE-BUTTON"
		mode520(value, admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 521:
		'''------------------------------
		---SPORT-CHANNELS----------------
		------------------------------'''
		name = "SPORT-CHANNELS"
		mode521(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 522:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode522(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 523:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode523(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 524:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode524(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 525:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode525(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 526:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode526(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 527:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode527(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 528:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode528(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 529:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode529(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 530:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode530(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 531:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode531(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 532:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode532(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 533:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode533(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 534:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode534(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 535:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode535(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 536:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode536(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 537:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode537(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 538:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode538(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 539:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode539(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 540:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode540(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 541:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode541(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 542:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode542(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 543:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode543(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 544:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode544(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 545:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode545(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 546:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode546(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 547:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode547(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 548:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode548(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 549:
		'''------------------------------
		---MORE-BUTTON-------------------
		------------------------------'''
		name = "MORE-BUTTON"
		mode549(value, admin, name, printpoint)
		'''---------------------------'''

elif mode >= 550 and mode <= 599:
	'''------------------------------
	---HOME-BUTTONS-(2)-550-599------
	------------------------------'''
	if mode == 550:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode550(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 551:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode551(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 552:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode552(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 553:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode553(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 554:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode554(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 555:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode555(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 556:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode556(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 557:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode557(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 558:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode558(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 559:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode559(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 560:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode560(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 561:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode561(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 562:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode562(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 563:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode563(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 564:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode564(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 565:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode565(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 566:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode566(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 567:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode567(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 568:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode568(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 569:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode569(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 570:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode570(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 571:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode571(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 572:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode572(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 573:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode573(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 574:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode574(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 575:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode575(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 576:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode576(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 577:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode577(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 578:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode578(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 579:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode579(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 580:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode580(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 581:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode581(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 582:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode582(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 583:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode583(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 584:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode584(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 585:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode585(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 586:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode586(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 587:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode587(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 588:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode588(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 589:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode589(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 590:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode590(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 591:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode591(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 592:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode592(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 593:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode593(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 594:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode594(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 595:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode595(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 596:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode596(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 597:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode597(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 598:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode598(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 599:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode599(admin, name, printpoint)
		'''---------------------------'''
		
elif mode >= 600 and mode <= 649:
	'''------------------------------
	---?-600-649---------------------
	------------------------------'''
	if mode == 600:
		'''------------------------------
		---?---------------
		------------------------------'''
		name = ""
		mode600(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 601:
		'''------------------------------
		---?-------------------
		------------------------------'''
		name = ""
		mode601(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 602:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode602(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 603:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode603(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 604:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode604(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 605:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode605(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 606:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode606(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 607:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode607(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 608:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode608(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 609:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode609(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 610:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode610(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 611:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode611(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 612:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode612(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 613:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode613(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 614:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode614(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 615:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode615(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 616:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode616(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 617:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode617(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 618:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode618(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 619:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode619(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 620:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode620(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 621:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode621(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 622:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode622(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 623:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode623(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 624:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode624(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 625:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode625(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 626:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode626(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 627:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode627(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 628:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode628(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 629:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode629(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 630:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode630(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 631:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode631(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 632:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode632(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 633:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode633(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 634:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode634(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 635:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode635(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 636:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode636(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 637:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode637(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 638:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode638(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 639:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode639(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 640:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode640(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 641:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode641(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 642:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode642(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 643:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode643(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 644:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode644(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 645:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode645(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 646:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode646(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 647:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode647(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 648:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode648(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 649:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode649(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 650 and mode <= 699:
	'''------------------------------
	---?-650-699---------------------
	------------------------------'''
	if mode == 650:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode650(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 651:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode651(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 652:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode652(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 653:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode653(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 654:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode654(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 655:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode655(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 656:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode656(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 657:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode657(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 658:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode658(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 659:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode659(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 660:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode660(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 661:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode661(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 662:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode662(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 663:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode663(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 664:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode664(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 665:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode665(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 666:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode666(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 667:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode667(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 668:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode668(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 669:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode669(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 670:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode670(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 671:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode671(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 672:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode672(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 673:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode673(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 674:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode674(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 675:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode675(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 676:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode676(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 677:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode677(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 678:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode678(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 679:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode679(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 680:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode680(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 681:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode681(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 682:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode682(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 683:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode683(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 684:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode684(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 685:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode685(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 686:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode686(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 687:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode687(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 688:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode688(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 689:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode689(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 690:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode690(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 691:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode691(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 692:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode692(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 693:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode693(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 694:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode694(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 695:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode695(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 696:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode696(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 697:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode697(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 698:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode698(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 699:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode699(admin, name, printpoint)
		'''---------------------------'''
					
elif mode >= 700 and mode <= 749:
	'''------------------------------
	---?-700-749---------------------
	------------------------------'''
	if mode == 700:
		'''------------------------------
		---?---------------
		------------------------------'''
		name = ""
		mode700(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 701:
		'''------------------------------
		---?-------------------
		------------------------------'''
		name = ""
		mode701(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 702:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode702(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 703:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode703(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 704:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode704(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 705:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode705(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 706:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode706(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 707:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode707(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 708:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode708(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 709:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode709(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 710:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode710(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 711:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode711(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 712:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode712(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 713:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode713(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 714:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode714(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 715:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode715(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 716:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode716(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 717:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode717(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 718:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode718(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 719:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode719(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 720:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode720(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 721:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode721(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 722:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode722(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 723:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode723(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 724:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode724(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 725:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode725(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 726:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode726(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 727:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode727(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 728:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode728(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 729:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode729(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 730:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode730(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 731:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode731(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 732:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode732(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 733:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode733(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 734:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode734(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 735:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode735(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 736:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode736(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 737:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode737(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 738:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode738(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 739:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode739(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 740:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode740(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 741:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode741(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 742:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode742(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 743:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode743(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 744:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode744(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 745:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode745(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 746:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode746(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 747:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode747(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 748:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode748(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 749:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode749(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 750 and mode <= 799:
	'''------------------------------
	---?-750-799---------------------
	------------------------------'''
	if mode == 750:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode750(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 751:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode751(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 752:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode752(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 753:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode753(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 754:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode754(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 755:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode755(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 756:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode756(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 757:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode757(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 758:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode758(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 759:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode759(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 760:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode760(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 761:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode761(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 762:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode762(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 763:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode763(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 764:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode764(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 765:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode765(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 766:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode766(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 767:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode767(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 768:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode768(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 769:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode769(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 770:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode770(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 771:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode771(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 772:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode772(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 773:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode773(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 774:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode774(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 775:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode775(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 776:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode776(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 777:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode777(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 778:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode778(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 779:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode779(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 780:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode780(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 781:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode781(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 782:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode782(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 783:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode783(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 784:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode784(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 785:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode785(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 786:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode786(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 787:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode787(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 788:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode788(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 789:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode789(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 790:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode790(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 791:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode791(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 792:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode792(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 793:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode793(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 794:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode794(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 795:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode795(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 796:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode796(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 797:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode797(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 798:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode798(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 799:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode799(admin, name, printpoint)
		'''---------------------------'''
		
elif mode >= 800 and mode <= 849:
	'''------------------------------
	---?-800-849---------------------
	------------------------------'''
	if mode == 800:
		'''------------------------------
		---?---------------
		------------------------------'''
		name = ""
		mode800(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 801:
		'''------------------------------
		---?-------------------
		------------------------------'''
		name = ""
		mode801(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 802:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode802(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 803:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode803(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 804:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode804(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 805:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode805(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 806:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode806(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 807:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode807(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 808:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode808(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 809:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode809(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 810:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode810(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 811:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode811(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 812:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode812(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 813:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode813(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 814:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode814(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 815:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode815(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 816:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode816(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 817:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode817(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 818:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode818(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 819:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode819(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 820:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode820(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 821:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode821(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 822:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode822(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 823:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode823(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 824:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode824(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 825:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode825(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 826:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode826(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 827:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode827(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 828:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode828(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 829:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode829(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 830:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode830(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 831:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode831(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 832:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode832(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 833:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode833(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 834:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode834(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 835:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode835(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 836:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode836(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 837:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode837(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 838:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode838(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 839:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode839(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 840:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode840(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 841:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode841(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 842:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode842(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 843:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode843(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 844:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode844(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 845:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode845(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 846:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode846(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 847:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode847(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 848:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode848(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 849:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode849(admin, name, printpoint)
		'''---------------------------'''

elif mode >= 850 and mode <= 899:
	'''------------------------------
	---?-850-899---------------------
	------------------------------'''
	if mode == 850:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode850(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 851:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode851(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 852:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode852(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 853:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode853(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 854:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode854(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 855:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode855(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 856:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode856(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 857:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode857(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 858:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode858(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 859:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode859(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 860:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode860(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 861:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode861(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 862:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode862(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 863:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode863(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 864:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode864(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 865:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode865(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 866:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode866(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 867:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode867(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 868:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode868(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 869:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode869(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 870:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode870(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 871:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode871(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 872:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode872(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 873:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode873(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 874:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode874(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 875:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode875(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 876:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode876(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 877:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode877(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 878:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode878(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 879:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode879(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 880:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode880(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 881:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode881(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 882:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode882(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 883:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode883(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 884:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode884(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 885:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode885(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 886:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode886(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 887:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode887(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 888:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode888(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 889:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode889(admin, name, printpoint)
		'''---------------------------'''
		
	elif mode == 890:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = ""
		mode890(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 891:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode891(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 892:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode892(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 893:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode893(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 894:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode894(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 895:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode895(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 896:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode896(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 897:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode897(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 898:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode898(admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 899:
		'''------------------------------
		---?-----------------------------
		------------------------------'''
		name = "?"
		mode899(admin, name, printpoint)
		'''---------------------------'''
	
else: printpoint = printpoint + "9"

'''------------------------------
---PRINT-END---------------------
------------------------------'''
if TypeError != "": print printfirst + "Default.py" + space + "TypeError" + space2 + str(TypeError)
if admin: print printfirst + "default.py_LV" + printpoint + space + "mode" + space2 + str(mode) + space + "value" + space2 + str(value)
'''---------------------------'''
	