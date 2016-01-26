# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, os, sys, subprocess, random

from variables import *
from shared_modules import *

def mode0(admin, name, printpoint):
	'''------------------------------
	---TEST--------------------------
	------------------------------'''
	#addon = ''
	#installaddon(admin, addon, update=False)
	#installaddonP(admin, addon, update=False)
	#returned = dialogyesno(localize(79516) + '[CR]blablablasssssssssssssssssss', localize(78,addon='script.featherence.service') + localize(75775)) #User settings
	#dialogok('asdasdsakdsalfd;gke;gwekfeaf[CR]asdasdsakdsalfd','dsafamlg;ewmfefsaf','dsafldmlemfwqfewfvasdfvdaf','sdafdglvnlerflqemfafcasfcaafasfsghgs')
	#option = localize(24056,[librarydatalocaldatestr]) #str24056.encode('utf-8') % (librarydatalocaldatestr)
	#print option
	#xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=31&value=header&value2=test&value3=Z:\kodi.log)')
	#xbmc.executebuiltin('Skin.ResetSettings')
	#xbmc.executebuiltin('ActivateWindow(videoplaylist)')
	#mode5('', admin, name, printpoint)
	#dp = xbmcgui.DialogProgress()
	#dp.create("featherence Texture-Cache-Removal", "Removing Datebase", "why are we here?[CR]test is here ssssssssssssssssssssssssssssssssssssssssssssssssssss ")
	#terminal('killall -9 kodi.bin',desc="", remote=True)
	#from debug2 import *
	#from debug3 import *
	#subject = 'test'
	#text = 'test2'
	file = 'C:\\Users\\gal\\AppData\\Roaming\\Kodi\\1941146-1920x1080-[DesktopNexus.com]_.jpg'
	#file = to_unicode(file)
	#file = ""
	#upload_file2(file)
	#sendMail(Debug_Email, Debug_Password, subject, text, file)
	#setSkin_UpdateLog(admin, Skin_Version, Skin_UpdateDate, datenowS, force=True)
	mode29('boris&natan mem', '0=TopInformationIcons', 'Choose an option from the list', '1', "", "")	
	
def mode5(value, admin, name, printpoint):
	'''------------------------------
	---demon-------------------------
	------------------------------'''
	AutoUpdate = getsetting('AutoUpdate')
	AutoUpdate2 = getsetting('AutoUpdate2')
	Library_On = getsetting('Library_On')
	
	if AutoUpdate == 'true':
		printpoint = printpoint + '1'
		try:
			test = int(AutoUpdate2) + 1
		except:
			AutoUpdate2 = '60'
			setsetting('AutoUpdate2','60')
		xbmc.executebuiltin('UpdateAddonRepos')
		xbmc.executebuiltin('UpdateLocalAddons')
	
	if xbmc.getCondVisibility('!IntegerGreaterThan(System.Uptime,5)'):
		'''one time at startup'''
		Remote_Name = getsetting('Remote_Name')
		Remote_Support = getsetting('Remote_Support')
		if Remote_Name != "" and Remote_Name != 'None' and Remote_Support == 'true':
			xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=27&value=0)')
		
		#mode101('1',admin, 'TotalMouse')
		
		try:
			VolumeLevel = int(xbmcaddon.Addon(addonID).getSetting('VolumeLevel'))
			xbmc.executebuiltin('SetVolume('+str(VolumeLevel)+')')
		except: pass
		
		addon = 'plugin.video.featherence.docu'
		if xbmc.getCondVisibility('System.HasAddon('+addon+')'): setsetting_custom1(addon, 'Addon_UpdateLog', "true")
			
		addon = 'plugin.video.featherence.kids'
		if xbmc.getCondVisibility('System.HasAddon('+addon+')'): setsetting_custom1(addon, 'Addon_UpdateLog', "true")

		addon = 'plugin.video.featherence.gopro'
		if xbmc.getCondVisibility('System.HasAddon('+addon+')'): setsetting_custom1(addon, 'Addon_UpdateLog', "true")

		addon = 'plugin.video.featherence.music'
		if xbmc.getCondVisibility('System.HasAddon('+addon+')'): setsetting_custom1(addon, 'Addon_UpdateLog', "true")
		
		installaddonP(admin, 'repository.featherence')
		
		if xbmc.getSkinDir() == 'skin.featherence':
			mode215('_',admin,'','')
			setsetting_custom1('script.featherence.service','Skin_UpdateLog',"true")
			Skin_UpdateLog = 'true'
			installaddonP(admin, 'script.module.simplejson')
			xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=23&value=)')
			setSkin_Update(admin, datenowS, Skin_Version, Skin_UpdateDate, Skin_UpdateLog)
			
			installaddonP(admin, 'resource.images.weathericons.outline')
			installaddonP(admin, 'resource.images.weatherfanart.single')
			
	else:
		'''multitime but not on startup'''
		if Library_On == 'true':
			printpoint = printpoint + '2'
			LibraryUpdate(admin, datenowS, Library_On, Library_CleanDate, Library_UpdateDate)

	if AutoUpdate == 'true' or Library_On == 'true':
		xbmc.executebuiltin('AlarmClock(demon,RunScript(script.featherence.service,,?mode=5),'+str(AutoUpdate2)+',silent)') #demon

def mode6(admin, name, printpoint):
	'''------------------------------
	---connectioncheck---------------
	------------------------------'''
	name = "?"
	connectioncheck(admin, name, printpoint)
	'''---------------------------'''

def mode7(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode7(admin, name, printpoint)
	'''---------------------------'''
	
def mode8(admin, name, printpoint):
	'''------------------------------
	---SMART-SUBTITLE-SEARCH---------
	------------------------------'''
	input = xbmc.getInfoLabel('Window(home).Property(VideoPlayer.Title)')
	if input != "":
		xbmc.executebuiltin('SendClick(160)')
		dialogkeyboard = xbmc.getCondVisibility('Window.IsVisible(DialogKeyboard.xml)')
		count = 0
		while count < 20 and not dialogkeyboard and not xbmc.abortRequested:
			count += 1
			xbmc.sleep(100)
			dialogkeyboard = xbmc.getCondVisibility('Window.IsVisible(DialogKeyboard.xml)')
			
		if count < 20: xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.SendText","id":976575931,"params":{"text":"'+ input +'","done":false}}')
	else: notification('...','','',1000)

def mode9(admin, name):
	'''------------------------------
	---SEMI-AUTO-SUBTITLE-FIND-------
	------------------------------'''
	property_subtitleservice = xbmc.getInfoLabel('Window(home).Property(Subtitle_Service)')
	property_dialogsubtitles = xbmc.getInfoLabel('Window(home).Property(DialogSubtitles)')
	property_dialogsubtitles2 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitles2)')
	property_dialogsubtitlesna1 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA1)')
	property_dialogsubtitlesna2 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA2)')
	property_dialogsubtitlesna3 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA3)')
	property_dialogsubtitlesna4 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA4)')
	property_dialogsubtitlesna5 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA5)')
	property_dialogsubtitlesna6 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA6)')
	property_dialogsubtitlesna7 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA7)')
	property_dialogsubtitlesna8 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA8)')
	property_dialogsubtitlesna9 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA9)')
	property_dialogsubtitlesna10 = xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA10)')
	subL = [property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10]
	listL = ['Subscenter.org', 'Subtitle.co.il', 'OpenSubtitles.org', 'Torec']
	dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
	controlgetlabel100 = xbmc.getInfoLabel('Control.GetLabel(100)')
	controlhasfocus120 = xbmc.getCondVisibility('Control.HasFocus(120)') #MAIN
	controlhasfocus150 = xbmc.getCondVisibility('Control.HasFocus(150)') #SIDE
	controlgetlabel100 = xbmc.getInfoLabel('Control.GetLabel(100)') #DialogSubtitles Service Name
	controlgroup70hasfocus0 = xbmc.getCondVisibility('ControlGroup(70).HasFocus(0)') #OSD BUTTONS
	container120listitemlabel2 = xbmc.getInfoLabel('Container(120).ListItem.Label2')
	container120numitems = 0
	tip = "true"
	count = 0
	count2 = 0 #container120numitems
	countidle = 0
	'''---------------------------'''
	while countidle < 40 and dialogsubtitlesW and not xbmc.abortRequested:
		'''------------------------------
		---VARIABLES---------------------
		------------------------------'''
		dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
		if dialogsubtitlesW:
			container120numitems2 = container120numitems
			container120numitems = xbmc.getInfoLabel('Container(120).NumItems') #DialogSubtitles
			try: container120numitems = int(container120numitems)
			except: container120numitems = ""
			'''---------------------------'''
			controlhasfocus120 = xbmc.getCondVisibility('Control.HasFocus(120)') #MAIN
			controlhasfocus150 = xbmc.getCondVisibility('Control.HasFocus(150)') #SIDE
			controlgetlabel100 = xbmc.getInfoLabel('Control.GetLabel(100)') #DialogSubtitles Service Name
			controlgroup70hasfocus0 = xbmc.getCondVisibility('ControlGroup(70).HasFocus(0)') #OSD BUTTONS
			'''---------------------------'''
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
			container120listitemlabel2 = xbmc.getInfoLabel('Container(120).ListItem.Label2')
			'''---------------------------'''
			
		property_dialogsubtitles = xbmc.getInfoLabel('Window(home).Property(DialogSubtitles)')
		dialogkeyboardW = xbmc.getCondVisibility('Window.IsVisible(DialogKeyboard.xml)')
		playerpaused = xbmc.getCondVisibility('Player.Paused')
		'''---------------------------'''
		systemidle1 = xbmc.getCondVisibility('System.IdleTime(1)')
		systemidle3 = xbmc.getCondVisibility('System.IdleTime(3)')
		systemidle7 = xbmc.getCondVisibility('System.IdleTime(7)')
		systemidle40 = xbmc.getCondVisibility('System.IdleTime(40)')
		'''---------------------------'''
		
		if controlhasfocus120 and container120numitems > 0 and count2 != 0: count2 = 0
		
		if not dialogkeyboardW and container120numitems != "" and controlgetlabel100 != "":
			
			if count == 0 and property_subtitleservice != "" and property_subtitleservice != controlgetlabel100 and controlgetlabel100 != "":
				'''------------------------------
				---Last_SubService---------------
				------------------------------'''
				if controlhasfocus120: xbmc.executebuiltin('Action(Left)')
				systemcurrentcontrol = findin_systemcurrentcontrol("0",property_subtitleservice,40,'Action(Down)','')
				systemcurrentcontrol = findin_systemcurrentcontrol("0",property_subtitleservice,40,'Action(Down)','')
				systemcurrentcontrol = findin_systemcurrentcontrol("0",property_subtitleservice,40,'Action(Down)','')
				systemcurrentcontrol = findin_systemcurrentcontrol("0",property_subtitleservice,40,'Action(Down)','')
				systemcurrentcontrol = findin_systemcurrentcontrol("0",property_subtitleservice,100,'Action(Down)','Action(Select)')
				'''---------------------------'''
					
			elif controlhasfocus120 and container120numitems > 0:
				if (container120listitemlabel2 in subL or container120listitemlabel2 == property_dialogsubtitles2):
					if container120numitems2 != container120numitems:
						'''------------------------------
						---Last_SubService---------------
						------------------------------'''
						count3 = 0
						while count3 < 5 and systemidle1 and not xbmc.abortRequested:
							count3 += 1
							container120listitemlabel2 = xbmc.getInfoLabel('Container(120).ListItem.Label2')
							systemidle1 = xbmc.getCondVisibility('System.IdleTime(1)')
							if (container120listitemlabel2 in subL or container120listitemlabel2 == property_dialogsubtitles2): xbmc.executebuiltin('Action(Down)')
							xbmc.sleep(100)
							'''---------------------------'''
							
					elif tip == "true" and countidle == 3:
						if container120listitemlabel2 == property_dialogsubtitles2: notification('$LOCALIZE[78947]',property_dialogsubtitles2,"",3000)
						elif container120listitemlabel2 in subL: notification('$LOCALIZE[78949]',property_dialogsubtitles2,"",3000)
						
						tip = "false"
						'''---------------------------'''
				
			elif controlhasfocus150 and container120numitems == 0:
				count2 += 1
				
				if countidle >= 1 and count2 == 1:
					'''------------------------------
					---LOOKING-FOR-SUBTITLE----------
					------------------------------'''
					notification('$LOCALIZE[78952]',"","",4000)
					'''---------------------------'''
				
				elif countidle > 3 and count2 == 10 and systemcurrentcontrol == controlgetlabel100:
					'''------------------------------
					---REFRESH-----------------------
					------------------------------'''
					if controlgetlabel100 == "Subtitle.co.il": xbmc.sleep(1000)
					notification('$LOCALIZE[78951]',"","",2000)
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("0",controlgetlabel100,100,'Action(Down)','Action(Select)')
					'''---------------------------'''
					
				elif countidle > 5 and count2 >= 20 and controlgetlabel100 != "":
					'''------------------------------
					---CHANGE-SUBTITLE-SERVICE-------
					------------------------------'''
					notification('$LOCALIZE[78950]',"","",2000)
					if controlgetlabel100 in listL: listL.remove(controlgetlabel100) #listL = 
					
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,100,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,200,'Action(Down)','Action(Select)')
					
					count2 = 0
					'''---------------------------'''
		
		dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
		if dialogsubtitlesW:
			if not controlgroup70hasfocus0 and not xbmc.getCondVisibility('System.GetBool(subtitles.pauseonsearch)'):
				if systemidle3 and playerpaused: xbmc.executebuiltin('Action(Play)')
				elif not systemidle3 and not playerpaused: xbmc.executebuiltin('Action(Pause)')
				'''---------------------------'''
			xbmc.sleep(1000)
			'''---------------------------'''
			count += 1
			if systemidle1: countidle += 1
			else: countidle = 0
			'''---------------------------'''
	
	systemidle1 = xbmc.getCondVisibility('System.IdleTime(1)')
	systemidle7 = xbmc.getCondVisibility('System.IdleTime(7)')
	
	if systemidle1 and not systemidle7:
		'''------------------------------
		---SET-NEW-SUBTITLE--------------
		------------------------------'''
		setProperty('TEMP2', localize(24110), type="home")
		property_dialogsubtitles = xbmc.getInfoLabel('Window(home).Property(DialogSubtitles)')
		setProperty('DialogSubtitles2', property_dialogsubtitles, type="home")
		if property_dialogsubtitles2 != "": setSubHisotry(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10)
		if property_subtitleservice != controlgetlabel100 and controlgetlabel100 != "": setProperty('Subtitle_Service', controlgetlabel100, type="home")
		'''---------------------------'''
		
	#if dialogsubtitlesW: xbmc.executebuiltin('Dialog.Close(subtitlesearch)')
	setProperty('DialogSubtitles', "", type="home")
	setProperty('TEMP2', "", type="home")
	
	playerpaused = xbmc.getCondVisibility('Player.Paused')
	if playerpaused: xbmc.executebuiltin('Action(Play)')
	'''---------------------------'''
	
	if property_dialogsubtitlesna6 and not property_dialogsubtitlesna7:
		'''------------------------------
		---SHOW-TIPS---------------------
		------------------------------'''
		playerpaused = xbmc.getCondVisibility('Player.Paused')
		if not playerpaused: xbmc.executebuiltin('Action(Pause)')
		header = '[COLOR=yellow]' + xbmc.getInfoLabel('$LOCALIZE[78946]') + '[/COLOR]'
		message2 = xbmc.getInfoLabel('$LOCALIZE[78945]')
		w = TextViewer_Dialog('DialogTextViewer.xml', "", header=header, text=message2)
		w.doModal()
		'''---------------------------'''
		
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "count/2" + space2 + str(count) + space4 + str(count2) + space + "countidle" + space2 + str(countidle) + space + "controlgetlabel100" + space2 + str(controlgetlabel100) + space + "controlhasfocus120" + space2 + str(controlhasfocus120) + space + "controlhasfocus150" + space2 + str(controlhasfocus150) + space + "container120numitems/2" + space2 + str(container120numitems) + space4 + str(container120numitems2) + newline + "listL" + space2 + str(listL) + space + "systemcurrentcontrol" + space2 + str(systemcurrentcontrol) + space + space + "container120listitemlabel2" + space2 + str(container120listitemlabel2) + space + "subL" + space2 + str(subL) + space + "playerpaused" + space2 + str(playerpaused)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

def setSubHisotry(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10):
	if property_dialogsubtitles != "":
		for i in range(1,11):
			if xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA'+str(i)+')') == "":
				setProperty('DialogSubtitlesNA' +str(i), property_dialogsubtitles, type="home")
				break
	
	xbmc.sleep(1000)
	setCurrent_Subtitle(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10)
	'''---------------------------'''
	
def setCurrent_Subtitle(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10):
	for i in range(0,11):
		if i == 0: setProperty('DialogSubtitles', property_dialogsubtitles, type="home")
		else: setProperty('DialogSubtitles' +str(i), xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA'+str(i)+')'), type="home")
		'''---------------------------'''
		
def setPlayerInfo(admin):
	type = None
	videoplayercontentEPISODE = xbmc.getCondVisibility('VideoPlayer.Content(episodes)')
	videoplayercontentMOVIE = xbmc.getCondVisibility('VideoPlayer.Content(movies)')
	videoplayercountry = xbmc.getInfoLabel('VideoPlayer.Country')
	videoplayerseason = xbmc.getInfoLabel('VideoPlayer.Season')
	videoplayerepisode = xbmc.getInfoLabel('VideoPlayer.Episode')
	videoplayertagline = xbmc.getInfoLabel('VideoPlayer.Tagline')
	videoplayertitle = xbmc.getInfoLabel('VideoPlayer.Title')
	videoplayertvshowtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
	videoplayeryear = xbmc.getInfoLabel('VideoPlayer.Year')
	
	if (videoplayertvshowtitle != "" and videoplayerseason != "" and videoplayerepisode != "" and videoplayertagline == ""): type = 1
	elif (videoplayertitle != "" and (videoplayeryear != "" or videoplayercountry != "" or videoplayertagline != "")): type = 2
	elif videoplayercontentEPISODE: type = 1
	elif videoplayercontentMOVIE: type = 0
	else: type = 2
	
	if type != "":
		if type == 0: input = str(videoplayertitle) + space + videoplayeryear # + space + videoplayervideoresolution #+ space + videoplayervideocodec
		elif type == 1:
			try: seasonN = int(videoplayerseason)
			except: seasonN = ""
			try: episodeN = int(videoplayerepisode)
			except: episodeN = ""
			if seasonN == "" or episodeN == "" or videoplayertvshowtitle == "": input = videoplayertitle
			elif seasonN < 10 and episodeN < 10: input = videoplayertvshowtitle + " " + 'S0' + videoplayerseason + 'E0' + videoplayerepisode
			elif seasonN > 10 and episodeN > 10: input = videoplayertvshowtitle + " " + 'S' + videoplayerseason + 'E' + videoplayerepisode
			elif seasonN > 10 and episodeN < 10: input = videoplayertvshowtitle + " " + 'S' + videoplayerseason + 'E0' + videoplayerepisode
			elif seasonN < 10 and episodeN > 10: input = videoplayertvshowtitle + " " + 'S0' + videoplayerseason + 'E' + videoplayerepisode
			'''---------------------------'''
		else: input = playertitle
		
		setProperty('VideoPlayer.Title', str(input), type="home")

def videostarttweak(admin):
	playercache = xbmc.getInfoLabel('Player.CacheLevel')
	playerpaused = xbmc.getCondVisibility('Player.Paused')
	count = 0
	try:
		while count < 10 and int(playercache) < 90 and not xbmc.abortRequested:
			if count == 0 and not playerpaused:
				xbmc.executebuiltin('Action(Pause)')
				notification('Cache Tweak','...','',2000)
			count += 1
			playercache = xbmc.getInfoLabel('Player.CacheLevel')
			playerpaused = xbmc.getCondVisibility('Player.Paused')
			xbmc.sleep(500)

		if count > 0 and count < 10:
			playerpaused = xbmc.getCondVisibility('Player.Paused')
			if playerpaused: xbmc.executebuiltin('Action(Play)')
	except: pass
	
def mode10(admin, name, printpoint):
	'''------------------------------
	---VideoPlayer demon-------------
	------------------------------'''
	#notification('mode10 start','','',2000)
	if property_mode10 == "":
		setProperty('mode10', 'true', type="home")
		playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
		setPlayerInfo(admin)
		videostarttweak(admin)
		if playerhasvideo and xbmc.getCondVisibility('Window.IsVisible(DialogFullScreenInfo.xml)'): xbmc.executebuiltin('Action(Info)')
		while playerhasvideo and not xbmc.abortRequested:
			xbmc.sleep(5000)
			videoplayertweak(admin, playerhasvideo)
			playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
			'''---------------------------'''
		for i in range(1,10):
			setProperty('TopVideoInformation' + str(i), "", type="home")
		if xbmc.getInfoLabel('Window(home).Property(VideoPlayer.Title)') != "":
			if xbmcaddon.Addon('script.featherence.service').getSetting('widget_enable') == 'true':
				if not xbmc.getCondVisibility('IntegerGreatherThan(VideoPlayer.PlaylistLength,1)'):
					printpoint = printpoint + "5"
		setProperty('mode10', "", type="home")
		setProperty('VideoPlayer.Title', "", type="home")
		if '5' in printpoint:
			'''refresh widget'''
			xbmc.sleep(3000)
			xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=23)')
		

def mode12(admin, name, printpoint):
	'''------------------------------
	---UPDATE-LIVE-TV-PVR------------
	------------------------------'''
	addon = 'plugin.video.israelive'
	if xbmc.getCondVisibility('System.HasAddon('+addon+')'):
		notification("UPDATE-LIVE-TV-PVR","","",1000)

		path = os.path.join(addondata_path, 'plugin.video.israelive', '')
		removefiles(path)
		path = os.path.join(database_path, 'Epg8.db')
		removefiles(path)
		xbmc.sleep(1000)
		xbmc.executebuiltin('RunScript(plugin.video.israelive,,mode=32)') #Update IPTVSimple settings
		xbmc.sleep(500)
		xbmc.executebuiltin('RunScript(plugin.video.israelive,,mode=34)') #REFRESH ALL SETTINGS
		'''---------------------------'''
	else: notification_common("5")
	'''---------------------------'''

def mode13(admin, name, printpoint):
	'''------------------------------
	---SubtitleButton_Country--------
	------------------------------'''
	videoplayersubtitleslanguage = xbmc.getInfoLabel('VideoPlayer.SubtitlesLanguage') ; videoplayersubtitleslanguage_ = ""
	if videoplayersubtitleslanguage != "":
		len_ = len(videoplayersubtitleslanguage)
		if str(len_) != '2':
			if str(len_) == '3':
				videoplayersubtitleslanguage_ = videoplayersubtitleslanguage[:-1]
				
		xbmc.executebuiltin('SetProperty(SubtitleButton.Country,'+videoplayersubtitleslanguage_+',home)')
		'''---------------------------'''
	text = "videoplayersubtitleslanguage" + space2 + str(videoplayersubtitleslanguage) + space + "videoplayersubtitleslanguage_" + space2 + str(videoplayersubtitleslanguage_)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def mode14(admin, name, printpoint):
	'''------------------------------
	---setUser_Name------------------
	------------------------------'''
	returned = dialogkeyboard(scriptfeatherencedebug_User_Name,localize(1014),0,"",'User_Name',"")
	if returned != 'skip':
		setsetting_custom1('script.featherence.service.debug','User_Name',str(returned))
		'''---------------------------'''
	
def mode15(value, admin, name, printpoint):
	'''------------------------------
	---CopyFiles-Tweak---------------
	------------------------------'''
	source = "" ; target = ""
	if '|' in value:
		source = find_string(value, "", '|')
		source = source.replace('|',"")
		target = find_string(value, '|', "")
		target = target.replace('|',"")

		copyfiles(source, target, chmod="", mount=False)
		
	else: pass
	
	text = 'source' + space2 + str(source) + newline + 'target' + space2 + str(target)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	'''---------------------------'''
	
def mode16(admin, name, printpoint, customasources, countrystr):
	'''------------------------------
	---setSources.xml----------------
	------------------------------'''
	if not customasources:
		pass

def mode17(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode17(admin, name, printpoint)
	'''---------------------------'''

def mode18(value, admin, name, printpoint):
	'''Generate-Files'''
	#copyfiles(os.path.join(featherenceservicecopy_path, 'manual', 'addon_data', 'screensaver.randomtrailers', '*'), os.path.join(addondata_path, 'screensaver.randomtrailers'))
	#if not os.path.exists(flash_path + '/oemsplash.png'): copyfiles(os.path.join(featherenceservicecopy_path, 'manual', 'flash', '*'), flash_path, mount=True) ; printpoint = printpoint + "4"
	if value == '1':
		'''------------------------------
		---Keymaps-----------------------
		------------------------------'''
		returned = dialogyesno('Would you like to continue?','This action will overwrite your current related files!')
		if returned == 'ok':
			keymaps_path = os.path.join(userdata_path,'keymaps', '')
			copyfiles(os.path.join(featherenceservicecopy_path, 'manual', 'keymaps', '', '*'), keymaps_path)
			xbmc.executebuiltin('Action(reloadkeymaps)')
			dialogok('Keymaps copied!', 'keyboard.xml[CR]remote.xml[CR]joystick.Sony.PLAYSTATION(R)3.Controller[CR]joystick.PS4.Controller', '', '')
			'''---------------------------'''
	elif value == '2':
		'''------------------------------
		---Samba-------------------------
		------------------------------'''
		returned = dialogyesno('Would you like to continue?','This action will overwrite your current related files!')
		if returned == 'ok':
			copyfiles(os.path.join(featherenceservicecopy_path, 'manual', 'config', '*'), config_path, chmod='+x')
			'''---------------------------'''
	elif value == '3':
		'''------------------------------
		---service.openelec.settings-----
		------------------------------'''
		returned = dialogyesno('Would you like to continue?','This action will overwrite your current related files!')
		if returned == 'ok':
			copyfiles(os.path.join(featherenceservicecopy_path, 'manual', 'addon_data', 'service.openelec.settings', '*'), os.path.join(addondata_path,'service.openelec.settings'))
			'''---------------------------'''
	elif value == '4':
		'''------------------------------
		---plus-build--------------------
		------------------------------'''
		returned = dialogyesno('Would you like to continue?','This action will overwrite your current related files!')
		if returned == 'ok':
			removeaddons('repository.htpt', '123')
			removeaddons('script.htpt.remote', '123')
			removeaddons('script.htpt.refresh', '123')
			removeaddons('script.htpt.install', '123')
			removeaddons('resource.uisounds.htpt', '123')
			removeaddons('repository.htpt', '123')
			removeaddons('resource.images.htpt', '123')
			removeaddons('script.htpt.smartbuttons', '123')
			removeaddons('script.htpt.widgets', '123')
			removeaddons('service.htpt', '123')
			removeaddons('service.htpt.debug', '123')
			removeaddons('service.htpt.fix', '123')
			removeaddons('skin.htpt', '123')
			
			addon = 'script.pulsar.kickass-mc'
			installaddonP(admin, addon, update=False)
			
			addon = 'script.pulsar.thepiratebay-mc'
			installaddonP(admin, addon, update=False)
			
			addon = 'script.pulsar.torrentz-mc'
			installaddonP(admin, addon, update=False)

			fileID = getfileID('addondata_path'+".zip")
			DownloadFile("https://www.dropbox.com/s/"+fileID+"/"+addon+".zip?dl=1", addon + ".zip", temp_path, addondata_path, silent=False)
			'''---------------------------'''
	

def Mode19(admin, name, printpoint, scriptfeatherencedebug_Info_TotalSpace, scriptfeatherencedebug_Info_TotalMemory, scriptfeatherencedebug_Info_Model, scriptfeatherencedebug_Info_Intel):
	'''------------------------------
	---setAdvancedSettings-----------
	------------------------------'''
	copyfiles(os.path.join(featherenceservicecopy_path,'manual','advancedsettings.xml'), userdata_path)

	xbmc.sleep(1000)
	if os.path.exists(userdata_path + "advancedsettings.xml"):
		printpoint = printpoint + "7"
		try: scriptfeatherencedebug_Info_TotalSpaceN = int(scriptfeatherencedebug_Info_TotalSpace)
		except: scriptfeatherencedebug_Info_TotalSpaceN = 0
		
		try: scriptfeatherencedebug_Info_TotalMemoryN = int(scriptfeatherencedebug_Info_TotalMemory)
		except: scriptfeatherencedebug_Info_TotalMemoryN = 0
		
		infile = os.path.join(userdata_path,'advancedsettings.xml')
		infile_ = read_from_file(infile, silent=False)
		
		'''---------------------------'''
		x = 'enablerssfeeds' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if xbmc.getSkinDir() != 'skin.featherence': new_word = '<'+x+'>true</'+x+'>'
		else: new_word = '<'+x+'>false</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'loglevel'
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if scriptfeatherencedebug_Info_TotalMemoryN < 2000 and scriptfeatherencedebug_General_AllowDebug != "true": new_word = '<'+x+'>-1</'+x+'>'
		else: new_word = '<'+x+'>0</'+x+'>'
		#elif admin3 and admin and admin2: new_word = '<'+x+'>1</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'cachemembuffersize' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		new_word = '<'+x+'>0</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'readbufferfactor' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		new_word = '<'+x+'>4.0</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'fanartres' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if scriptfeatherencedebug_Info_TotalSpaceN > 250: new_word = '<'+x+'>1080</'+x+'>'
		else: new_word = '<'+x+'>720</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'imageres' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if scriptfeatherencedebug_Info_TotalSpaceN > 250: new_word = '<'+x+'>1080</'+x+'>'
		else: new_word = '<'+x+'>480</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'packagefoldersize' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if scriptfeatherencedebug_Info_TotalSpaceN > 250: new_word = '<'+x+'>250</'+x+'>'
		else: new_word = '<'+x+'>40</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
		
		'''---------------------------'''
		x = 'skiploopfilter' 
		old_word = regex_from_to(infile_, '<'+x+'>', '</'+x+'>', excluding=False)
		if ('i3' in scriptfeatherencedebug_Info_Model or 'i5' in scriptfeatherencedebug_Info_Model or 'i7' in scriptfeatherencedebug_Info_Model) and scriptfeatherencedebug_Info_TotalMemoryN > 2000: new_word = '<'+x+'>0</'+x+'>'
		else: new_word = '<'+x+'>8</'+x+'>'
		replace_word(infile,old_word,new_word)
		'''---------------------------'''
	else: printpoint = printpoint + "9"
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = ""
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	
def mode21(value, admin, name, printpoint):
	'''------------------------------
	---SCRAPER-AUTO-SETUP------------
	------------------------------'''
	returned = setPath(0)
	if returned != "":
		if value == '1':
			'''------------------------------
			---MOVIES------------------------
			------------------------------'''
			#printpoint2 = "" ; printpoint2 = doFix_100_0(printpoint2, "100")
			printpoint2 = "" ; printpoint2 = doFix_100_0(printpoint2, "100")
			
			if not "9" in printpoint2 and "0" in printpoint2:
				dialogok(localize(78985) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (localize(342)) + '[/COLOR]', '$LOCALIZE[78983]', '$LOCALIZE[78982]',"")
				returned = dialogyesno(localize(78985), '[COLOR=yellow]' + str74550.encode('utf-8') % (localize(342)) + '[/COLOR]' + '[CR]' + localize(78981)) #Manual fix is available ,
				if returned == 'ok': printpoint2 = doFix_100(admin, "100", TEMP)
				else: printpoint2 = printpoint2 + "8"
				'''---------------------------'''
				if "7" in printpoint2:
					dialogok(localize(78986) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (localize(342)) + '[/COLOR]',localize(75209,s=[localize(342)]), '$LOCALIZE[75208]', "")
					'''---------------------------'''
				elif "9" in printpoint2: dialogok(localize(78974) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (localize(342)) + '[/COLOR]',"", '$LOCALIZE[75210]', "") #Fix failed, Add movies to library
				'''---------------------------'''
		elif value == '2':
			'''------------------------------
			---TVSHOWS-----------------------
			------------------------------'''
			printpoint2 = "" ; printpoint2 = doFix_100_0(printpoint2, "101")
			addon = 'metadata.tvdb.com'
			if not xbmc.getCondVisibility('System.HasAddon('+ addon +')'): installaddon(admin, addon, "")
			printpoint2 = "" ; printpoint2 = doFix_100_0(printpoint2, "101", TEMP)
			'''---------------------------'''
			if not "9" in printpoint2 and "0" in printpoint2:
				dialogok(localize(78985) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (str20343.encode('utf-8')) + '[/COLOR]', '$LOCALIZE[78983]', '$LOCALIZE[78982]',"")
				returned = dialogyesno(localize(78985), '[COLOR=yellow]' + str74550.encode('utf-8') % (str20343.encode('utf-8')) + '[/COLOR]' + '[CR]' + localize(78981)) #Manual fix is available ,
				if returned == 'ok': printpoint2 = doFix_100(admin, "101")
				else: printpoint2 = printpoint2 + "8"
				'''---------------------------'''
				if "7" in printpoint2:
					dialogok(localize(78986) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (str20343.encode('utf-8')) + '[/COLOR]',localize(75209,s=[localize(20343)]), '$LOCALIZE[75208]', "")
					'''---------------------------'''
				elif "9" in printpoint2: dialogok(localize(78974) + '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (str20343.encode('utf-8')) + '[/COLOR]',"", '$LOCALIZE[75210]', "") #Fix failed, Add movies to library
				'''---------------------------'''
def mode22(value, admin, name, printpoint, ScreenSaver_Music):
	'''------------------------------
	---ScreenSaver_Music-------------
	------------------------------'''
	screensavermusic = xbmc.getInfoLabel('Skin.String(screensavermusic)')
	returned = setPath(1,'.mp3|.flac|.wav|.m3u')
	notification(returned,screensavermusic,'',4000)
	if returned != "":
		if returned != screensavermusic: setSkinSetting('0','screensavermusic',returned)
		else:
			returned2 = dialogyesno('Remove Current Path?',screensavermusic)
			if returned2 == 'ok': setSkinSetting('0','screensavermusic',"")
			'''---------------------------'''

def mode24(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode24(admin, name, printpoint)
	'''---------------------------'''

def mode25(value, admin, name, printpoint):
	'''------------------------------
	---Play-Random-Trailers----------
	------------------------------'''
	
	pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	pl.clear()
	playlist = []
	for i in range(1,11):
		value_trailer = xbmc.getInfoLabel('Window(home).Property(RecentMovie.'+str(i)+'.Trailer)')
		value_trailer2 = xbmc.getInfoLabel('Window(home).Property(RandomMovie.'+str(i)+'.Trailer)')
		if value_trailer != "": playlist.append(value_trailer)
		if value_trailer2 != "": playlist.append(value_trailer2)
		'''---------------------------'''
	if playlist != []:
		random.shuffle(playlist)
		for x in playlist:
			pl.add(x)
		xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(pl)
		

def mode26(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode26(admin, name, printpoint)
	'''---------------------------'''


def mode28(value, admin, name, printpoint):
	'''------------------------------
	---AutoView----------------------
	------------------------------'''
	extra = "" ; TypeError = "" ; value2 = "" ; returned = ""
	list = ['-> (Exit)', 'None', 'Default', localize(31010), localize(31011)] #Center List, Side List
	if value == 'AutoView.episodes' or value == 'AutoView.seasons': list.append(localize(31012)) #Small List
	list.append(localize(31013)) #Wall
	list.append(localize(31014)) #Poster
	list.append(localize(31015)) #List

	returned, value2 = dialogselect('$LOCALIZE[74433]',list,0)

	if returned == -1: printpoint = printpoint + "9"
	elif returned == 0: printpoint = printpoint + "8"
	else: printpoint = printpoint + "7"
	
	if "7" in printpoint:
		if value2 == 'None': setSkinSetting('0', str(value), "None")
		elif value2 == 'Default': setSkinSetting('0', str(value), "")
		elif value2 != "": setSkinSetting('0', str(value), value2)
		else: printpoint = printpoint + "8"
		'''---------------------------'''

def mode29(value, command, header, exit, name, printpoint):
	'''------------------------------
	---Dialog-Select-Skin------------
	------------------------------
	value = list ; output = Skin.String/Setting ; header='''
	extra = "" ; TypeError = "" ; returned2 = "" ; returned = "" ; commandL = [] ; list = [] ; list2 = []
	
	if command == "":
		printpoint = printpoint + '9'
		notification_common('3')
		
	commandL = command.split('|')
	
	if header == "":
		header = 'Choose an option from the list'
	
	if exit != '0':
		list.append('-> (Exit)')
		list2.append('-> (Exit)')
	
	valueL = value.split('|')
	for x in valueL:
		#x = to_utf8(x)
		y = find_string(x, '-[', ']-')
		print y
		if y != "":
			y_ = x.replace(y, "")
			list.append(y_)
			y__ = y.replace('-[',"",1)
			y__ = y__.replace(']-',"",1)
			list2.append(y__)
		else:	
			list.append(x)
			list2.append(x)

	returned, returned2 = dialogselect(header,list,0)

	if returned == -1: printpoint = printpoint + "9"
	elif returned == 0 and exit != '0': printpoint = printpoint + "8"
	else: printpoint = printpoint + "7"
	
	if "7" in printpoint:
		for x in commandL:
			if x[:2] == '0.':
				x_ = x.replace(x[:2],"",1)
				if '_name' in x:
					setSkinSetting('0', x_, list[returned], force=True)
				else:
					setSkinSetting('0', x_, list2[returned], force=True)
			elif x[:2] == '1.':
				setSkinSetting('1', str(returned2), list2[returned], force=True)
			else:
				xbmc.executebuiltin(x) ; xbmc.sleep(10)
	
	text2 = newline + 'value' + space2 + str(value) + newline + \
	'list ' + space2 + str(list) + newline + \
	'list2 ' + space2 + str(list2) + newline + \
	'returned' + space2 + str(returned) + space + 'returned2' + space2 + str(returned2) + newline + \
	'command  ' + space2 + str(command) + newline + \
	'commandL ' + space2 + str(commandL) + newline + extra
	printlog(title=name, printpoint=printpoint, text=text2, level=0, option="")
	
def mode30(admin, name):
	pass

def mode31(value, value2, value3, value4, admin, name, printpoint):
	'''------------------------------
	---diaogtextviewer---------------
	------------------------------'''
	header = "" ; message = ""
	try: header = str(value).encode('utf-8')
	except: pass
	try: message = str(value2).encode('utf-8')
	except: pass
	if value == 'Custom':
		value3 = setPath(type=1,mask="", folderpath="")
		if value3 != "":
			'''get file name only'''
			header = os.path.basename(value3)
	
	if value3 != "" and value3 != None:
		value3 = read_from_file(value3, silent=True, lines=False, retry=True, createlist=True, printpoint="", addlines="")
		message = message + newline + str(value3)
	message = message + newline + str(value4).encode('utf-8')
	diaogtextviewer(header, message)
	'''---------------------------'''
	
def mode32(value, admin, name, printpoint):
	'''------------------------------
	---MISCS-------------------------
	------------------------------'''
	
	if value == '0':
		if admin == 'false':
			setsetting('admin','true')
			#setsetting_custom1('script.featherence.service','admin',"true")
			#notification(admin,'','',1000)
			setSkinSetting('1','Admin','true')
		else:
			setsetting('admin','false')
			setSkinSetting('1','Admin','false')
	elif value == '1':
		text = "" ; extra = ""
		listitemfolderpath = xbmc.getInfoLabel('ListItem.FolderPath')
		containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
		listitemthumb = xbmc.getInfoLabel('ListItem.Thumb')
		
		nolabel = 'Container.FolderPath'
		yeslabel = 'ListItem.Path'
		if containerfolderpath == "": nolabel = nolabel + space + '[Empty]'
		if listitemfolderpath == "": yeslabel = yeslabel + space + '[Empty]'
		
		returned = dialogyesno(str(name), addonString_servicefeatherence(31).encode('utf-8'), nolabel=nolabel, yeslabel=yeslabel)
		
		if returned != 'skip': text = listitemfolderpath ; printpoint = printpoint + '1'
		else: text = containerfolderpath ; printpoint = printpoint + '2'
		
		if text != "":
			printpoint = printpoint + '3'
			text = text.replace('&amp;','&')
			text = text.replace('&quot;',"")
			if 'plugin://plugin.video.sdarot.tv/?' in text:
				printpoint = printpoint + '4'
				text = text.replace('plugin://plugin.video.sdarot.tv/?',"")
				list = []
				list.append('mode=')
				list.append('image=')
				list.append('summary')
				list.append('name=')
				for x in list:
					text_ = regex_from_to(text, x, '&', excluding=False)
					text = text.replace(text_,"",1)
					extra = extra + 'x' + space2 + str(x) + space + 'text_' + space2 + str(text_) + newline
				text = "list.append('&sdarot=" + text + "')"
			
			elif 'plugin://plugin.video.wallaNew.video/?' in text and 1 + 1 == 3:
				printpoint = printpoint + '4'
				text = text.replace('plugin://plugin.video.wallaNew.video/?',"")
				list = []
				list.append('mode=')
				list.append('module=')
				list.append('name=')
				for x in list:
					text_ = regex_from_to(text, x, '&', excluding=False)
					text = text.replace(text_,"",1)
					extra = extra + 'x' + space2 + str(x) + space + 'text_' + space2 + str(text_) + newline
				text = "list.append('&wallaNew=" + text + "')"
			
			else:
				if '1' in printpoint: text = "list.append('&custom4=" + text + "')"
				elif '2' in printpoint: text = "list.append('&custom8=" + text + "')"
		
		if listitemthumb != "":
			text = text + newline + str(listitemthumb)
		write_to_file(featherenceservice_addondata_path + "Container.FolderPath" + ".txt", str(text), append=False, silent=True, utf8=False)
		notification('url saved!','Container.FolderPath.txt','',2000)
		'''---------------------------'''
		
		text2 = newline + 'text' + space2 + str(text) + newline + \
		'containerfolderpath ' + space2 + str(xbmc.getInfoLabel('Container.FolderPath')) + newline + \
		'containerfolderpath2' + space2 + containerfolderpath + newline + \
		'listitemfolderpath  ' + space2 + str(xbmc.getInfoLabel('ListItem.FolderPath')) + newline + \
		'listitemfolderpath2 ' + space2 + listitemfolderpath + newline + extra
		printlog(title='MISCS (mode32) value: ' + str(value), printpoint=printpoint, text=text2, level=0, option="")
		
	elif value == '2':
		returned, value = getRandom(0, min=0, max=3, percent=50)
		if value == 0:
			returned = dialogyesno('F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e')
		elif value == 1:
			dialogok('F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e')
		else:
			dp = xbmcgui.DialogProgress()
			dp.create('F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e')
			count = 0
			while count < 10 and not dp.iscanceled() and not xbmc.abortRequested:
				count += 1
				xbmc.sleep(500)
				dp.update(count * 10,'F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e','F--e--a--t--h--e--r--e--n--c--e[CR]F--e--a--t--h--e--r--e--n--c--e')
			xbmc.sleep(500)
			dp.close
	
	elif value == '3':
		'''Featherence YouTube channel'''
		xbmc.executebuiltin('ActivateWindow(10025,plugin://plugin.video.youtube/user/finalmakerr/),returned')			
		setSkin_UpdateLog(admin, Skin_Version, Skin_UpdateDate, datenowS, force=True)
	elif value == '4':
		pass
		
	elif value == '5':
		ReloadSkin(admin)
	
	elif value == '40':
		addon = 'plugin.video.featherence.kids'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			dialogok(addonString_servicefeatherence(32085).encode('utf-8'),addonString_servicefeatherence(32081).encode('utf-8'),"",'[B][COLOR=blue]Website[/COLOR][/B]: www.facebook.com/groups/featherence[CR]',line1c="yellow")
			General_Language2 = xbmcaddon.Addon(addon).getSetting('General_Language2') ; General_Language2 = str(General_Language2)
			dialogok(addonString_servicefeatherence(32086).encode('utf-8') % (General_Language2),addonString_servicefeatherence(32087).encode('utf-8'),"",addonString_servicefeatherence(32088).encode('utf-8'),line1c="yellow")
		
def mode33(admin, name, printpoint):
	'''------------------------------
	---?--------------------
	------------------------------'''
	pass
	'''---------------------------'''

def mode34(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode34(admin, name, printpoint)
	'''---------------------------'''

def mode35(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode35(admin, name, printpoint)
	'''---------------------------'''

def mode36(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode36(admin, name, printpoint)
	'''---------------------------'''

def mode37(admin, name, printpoint):
	pass
		
def mode40(value, admin, name, printpoint):
	'''------------------------------
	---Reset-Skin-Settings-----------
	------------------------------'''
	extra2 = "" ; TypeError = ""
	if value == '0': printpoint = printpoint + '1'
	elif value == '1':
		returned = dialogyesno(localize(74554) , localize(74556))
		if returned == 'ok': printpoint = printpoint + '1' ; xbmc.executebuiltin('Dialog.Close(1173)')
	
	if printpoint == '1':
		'''------------------------------
		---DELETE-USER-FILES-------------
		------------------------------'''
	
	if printpoint == '1':
		xbmc.executebuiltin('Skin.ResetSettings') ; xbmc.sleep(500)
		Custom1000(name,1,'This action may take a while.. be patient!',30)
		if playerhasmedia: xbmc.executebuiltin('Action(Stop)')
		
		count = 0

	if printpoint == '1':
		xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value=RESET)') ; xbmc.sleep(7000)
		xbmc.executebuiltin('Action(Back)') ; xbmc.sleep(500) ; customhomecustomizerW = xbmc.getCondVisibility('Window.IsVisible(CustomHomeCustomizer.xml)')
		if not customhomecustomizerW: xbmc.executebuiltin('ActivateWindow(1171)')
	
	text = ''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
			
def mode41(admin, name, printpoint):
	'''------------------------------
	---Network-Settings--------------
	------------------------------'''
	if systemplatformandroid: terminal('am start -a android.intent.action.MAIN -n com.android.settings/.Settings',name)
	elif systemplatformwindows: terminal('rundll32.exe van.dll,RunVAN',name)
	else: oewindow('Network')
	'''---------------------------'''

def mode43(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode43(admin, name, printpoint)
	'''---------------------------'''

def mode44(admin, name):
	'''------------------------------
	---OVERCLOCK---------------------
	------------------------------'''
	if not systemplatformlinuxraspberrypi: notification_common("22")
	else:
		printpoint = ""
		list = ['-> (Exit)','Status','OverClocking'] #,'Stability Test'
		
		returned, value = dialogselect('$LOCALIZE[74433]',list,0)

		if returned == -1:
			printpoint = printpoint + "9"
			#notification_common("9")
		elif returned == 0: printpoint = printpoint + "8"
		elif returned == 1:
			'''------------------------------
			---STATUS------------------------
			------------------------------'''
			config_file = '/flash/config.txt'
			if not os.path.exists(config_file): dialogok("config.txt is missing!", "" ,"" ,"")
			else:
				output = catfile('/flash/config.txt')
				diaogtextviewer(config_file, output)
				'''---------------------------'''
		elif returned == 2: mode46(admin, 'OVERCLOCKING')

def mode45(admin, name):
	'''------------------------------
	---STABILITY-TEST----------------
	------------------------------'''
	path = os.path.join(addonPath, 'specials', 'scripts', 'stabilitytest.sh')
	os.system('sh '+path+'')
	#xbmc

def mode46(admin,name):
	'''------------------------------
	---OVERCLOCKING------------------
	------------------------------'''
	printpoint = ""
	addon = 'script.openelec.rpi.config'
	if not xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
		installaddon(admin, addon, update=True)
	else: xbmc.executebuiltin('RunScript('+addon+')')
	
def mode47(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode47(admin, name, printpoint)
	'''---------------------------'''

def mode48(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode48(admin, name, printpoint)
	'''---------------------------'''
	
def mode49(admin, name, printpoint):
	'''------------------------------
	---SCRAPER-FIX-------------------
	------------------------------'''
	setsetting_custom1('script.featherence.service.fix','Fix_100',"true")
	setsetting_custom1('script.featherence.service.fix','Fix_101',"true")
	
	xbmc.executebuiltin('ActivateWindow(0)')
	xbmc.sleep(500)
	notification_common("2")
	xbmc.executebuiltin('RunScript(script.featherence.service.fix,,?mode=3)')	
	
	
def mode50(admin, name, printpoint):
	'''------------------------------
	---SOFT-RESTART------------------
	------------------------------'''
	custom = 'f1'
	killall(admin, custom)
	'''---------------------------'''

def mode51(admin, name, printpoint):
	'''------------------------------
	---RESTART-----------------------
	------------------------------'''
	custom = 'r1'
	killall(admin, custom)
	'''---------------------------'''

def mode52(admin, name, printpoint):
	'''------------------------------
	---SUSPEND-----------------------
	------------------------------'''
	xbmc.sleep(1000)
	xbmc.executebuiltin('XBMC.Suspend()')
	'''---------------------------'''

def mode53(admin, name, printpoint):
	'''------------------------------
	---POWEROFF----------------------
	------------------------------'''
	#notification(startupmessage2,id1str,"",5000)
	custom = 's1'
	killall(admin, custom)
	'''---------------------------'''

def mode54(admin, name, printpoint):
	'''------------------------------
	---QUIT--------------------------
	------------------------------'''
	if xbmc.getSkinDir() == 'skin.featherence': custom = 'q1'
	else: custom = 'q'
	xbmc.sleep(500)
	killall(admin, custom)
	#notification(startupmessage2,id1str,"",5000)
	'''---------------------------'''

def mode57(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode57(admin, name, printpoint)
	'''---------------------------'''

def mode58(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode58(admin, name, printpoint)
	'''---------------------------'''

def mode60(admin, name, printpoint):
	'''------------------------------
	---?--------------------
	------------------------------'''
	pass
	'''---------------------------'''

def mode61(admin, name, printpoint):
	'''------------------------------
	---?--------------------
	------------------------------'''
	pass
	'''---------------------------'''
	
def mode62(admin, name, printpoint):
	'''------------------------------
	---?--------------------
	------------------------------'''
	pass
	'''---------------------------'''
	

def mode63(admin, name):
	'''------------------------------
	---Texture-Cache-Removal---------
	------------------------------'''
	returned = dialogyesno("Are you sure?", "Doing so will delete your database and thumbnails folder!")
	if returned == "ok":
		dp = xbmcgui.DialogProgress()
		dp.create("featherence Texture-Cache-Removal", "Removing Datebase", " ")
		removefiles(database_path)
		dp.update(20,"Removing Thumbnails"," ")
		removefiles(thumbnails_path,dialogprogress=20)
		if os.path.exists(thumbnails_path): message = 'Error'
		else: message = addonString(33300).encode('utf-8')
		dp.update(90,message," ")
		xbmc.sleep(1000)
		dp.update(100,message," ")
		dp.close
		if not os.path.exists(thumbnails_path) and not os.path.exists(database_path): dialogok("Reboot Required!", "Click OK", "", "")
		else: dialogok("Couldn't remove thumbnails / database folder", "You should remove them manualy or reboot and retry!", "", "")
		#xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=50)')
		
	else: notification_common("9")

def mode64(value, admin, name, printpoint):
	'''------------------------------
	---Extract from file-------------
	------------------------------'''
	pass

def mode65(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode65(admin, name, printpoint)
	'''---------------------------'''

def mode66(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode66(admin, name, printpoint)
	'''---------------------------'''

def mode67(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode67(admin, name, printpoint)
	'''---------------------------'''

def mode68(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode68(admin, name, printpoint)
	'''---------------------------'''

def mode69(value, admin, name, printpoint):
	'''------------------------------
	---TIPS--------------------------
	------------------------------'''
	if value == 'SubMenu2Tip': SubMenu2Tip(admin)
	else: pass
	'''---------------------------'''

def mode70(value, admin, name, printpoint, property_temp):
	'''------------------------------
	---ExtendedInfo------------------
	------------------------------'''
	listitemlabel = xbmc.getInfoLabel('ListItem.Label')
	listitemdbid = xbmc.getInfoLabel('ListItem.DBID')
	listitemtitle = xbmc.getInfoLabel('ListItem.Title')
	listitemseason = xbmc.getInfoLabel('ListItem.Season')
	listitemdirector = xbmc.getInfoLabel('ListItem.Director')
	listitemyear = xbmc.getInfoLabel('ListItem.Year')
	listitemwriter = xbmc.getInfoLabel('ListItem.Writer')
	property_listitemyear = xbmc.getInfoLabel('Window(home).Property(ListItemYear)')
	property_listitemtvshowtitle = xbmc.getInfoLabel('Window(home).Property(ListItemTVShowTitle)')
	listitemtvshowtitle = xbmc.getInfoLabel('ListItem.TVShowTitle')
	
	addon = 'script.extendedinfo' ; input0 = "" ; input = "" ; input2 = "" ; container50listitemlabel2 = "" ; property_temp_ = ""
	if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
		if value == '0':
			'''movie info'''
			if listitemtitle != "":
				input = 'info=extendedinfo,name=%s' % (listitemtitle)
		elif value == '1':
			if localize(20373) in listitemlabel and listitemseason != "":
				'''seasoninfo'''
				printpoint = printpoint + "1"
				input = 'info=seasoninfo,tvshow=%s,season=%s' % (listitemtvshowtitle,listitemseason)
			elif listitemtvshowtitle != "":
				'''extendedtvinfo'''
				printpoint = printpoint + "2"
				input = 'info=extendedtvinfo,name=%s' % (listitemtvshowtitle)

		elif value == '3':
			if '&actor=' in property_temp:
				'''Actor info'''
				printpoint = printpoint + "1"
				property_temp = property_temp.replace('&actor=',"")
				if localize(20347) in property_temp:
					printpoint = printpoint + "2"
					property_temp_ = find_string(property_temp, property_temp[:1], xbmc.getInfoLabel('$LOCALIZE[20347]'))
					str20347_len = len(localize(20347))
					property_temp_ = property_temp_[:-str20347_len]
					property_temp = property_temp_
				else: pass
				input = 'info=extendedactorinfo,name=%s' % (property_temp)
			elif '&director=' in property_temp:
				printpoint = printpoint + "3"
				property_temp = property_temp.replace('&director=',"")
				input = 'info=extendedactorinfo,name=%s' % (property_temp)
				#input = 'info=directormovies,director=%s' % (property_temp)
				#input = 'info=extendedinfo,director=%s' % (property_temp)
				

		elif value == '5':
			'''Write info'''
			input0 = 'writermovies'
			input2 = 'writer'
			#input = 'info=extendedinfo,writer=%s,writer=%s' % (listitemwriter)
			#input = 'info=writermovies,writer=%s' % (listitemwriter)
			input = 'info=extendedactorinfo,name=%s' % (listitemwriter)
			if listitemwriter != "" and 1 + 1 == 3:
				if ' / ' in listitemwriter and 1 + 1 == 3:
					listitemwriter_ = listitemwriter.split(' / ')
					list = []
					for x in listitemwriter_:
						list.append(x)
					
					if len(list) > 1:
						returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
						if returned == -1: printpoint = printpoint + "9"
						else:
							printpoint = printpoint + "7"
							input = 'info=writermovies,writer=%s' % (value)
							input = 'info=extendedinfo,writer=%s' % (value)
							'''---------------------------'''
				else:
					pass
					#input = 'info=writermovies,writer=%s' % (listitemwriter)
					#input = 'info=extendedinfo,writer=%s,writer=%s' % (listitemwriter)
					'''---------------------------'''
		elif value == '10':
			'''Rate Movie/TVshow'''
			input = 'info=ratedialog,name=%s' % (str(listitemlabel))
		elif value == '20':
			#xbmc.executebuiltin('RunScript(script.extendedinfo,info=seasoninfo,tvshow='+listitemtvshowtitle+',season='+listitemseason+')')
			xbmc.executebuiltin('RunScript(script.extendedinfo,info=extendedinfo,director='+listitemdirector+')')
			#input0 = 'similartvshowstrakt'
			#input2 = 'id'
			#input = listitemdbid
		
		elif value == '40':
			input0 = 'comingsoon'
			
		else: pass
		
		if input != "":
			if dialogselectW:
				xbmc.executebuiltin('dialog.close(selectdialog)') ; xbmc.sleep(500)
			
			xbmc.executebuiltin('RunScript('+addon+','+input+')')
			count = 0 ; dialogvideonfoEW = xbmc.getCondVisibility('Window.IsVisible(script-ExtendedInfo Script-DialogVideoInfo.xml)')
			while count < 10 and not dialogvideonfoEW and not xbmc.abortRequested:
				count += 1
				xbmc.sleep(500)
				dialogvideonfoEW = xbmc.getCondVisibility('Window.IsVisible(script-ExtendedInfo Script-DialogVideoInfo.xml)')
			if count < 10: printpoint = printpoint + "7"
			else: printpoint = printpoint + "Q"
		else:
			printpoint = printpoint + "8"
			notification_common("17")
			'''---------------------------'''
	else:
		printpoint = printpoint + "9"
		installaddon(admin, addon, update=True)
	
	text = "input" + space2 + input + newline + \
	"INFO" + space2 + "listitemlabel" + space2 + listitemlabel + newline + "listitemtvshowtitle" + space2 + listitemtvshowtitle + newline + \
	"listitemtitle" + space2 + listitemtitle + newline + "listitemimdbnumber" + space2 + listitemimdbnumber + newline + "listitemdbid" + space2 + listitemdbid + newline + \
	'listitemseason' + space2 + str(listitemseason) + newline + \
	"containerfolderpath" + space2 + containerfolderpath + newline + "property_temp" + space2 + property_temp + space + "property_temp_" + space2 + str(property_temp_) + newline + \
	"listitemdirector" + space2 + listitemdirector + newline + \
	"listitemwriter" + space2 + listitemwriter
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
	'''---------------------------'''

def mode71(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode71(admin, name, printpoint)
	'''---------------------------'''

def mode72(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode72(admin, name, printpoint)
	'''---------------------------'''

def mode73(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode73(admin, name, printpoint)
	'''---------------------------'''

def mode74(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode74(admin, name, printpoint)
	'''---------------------------'''

def mode75(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode75(admin, name, printpoint)
	'''---------------------------'''

def mode76(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode76(admin, name, printpoint)
	'''---------------------------'''

def mode77(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode77(admin, name, printpoint)
	'''---------------------------'''

def mode78(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode78(admin, name, printpoint)
	'''---------------------------'''

def mode79(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode79(admin, name, printpoint)
	'''---------------------------'''
	
def mode80(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode80(admin, name, printpoint)
	'''---------------------------'''

def mode81(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode81(admin, name, printpoint)
	'''---------------------------'''

def mode82(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode82(admin, name, printpoint)
	'''---------------------------'''

def mode83(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode83(admin, name, printpoint)
	'''---------------------------'''

def mode84(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode84(admin, name, printpoint)
	'''---------------------------'''

def mode85(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode85(admin, name, printpoint)
	'''---------------------------'''

def mode86(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode86(admin, name, printpoint)
	'''---------------------------'''

def mode87(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode87(admin, name, printpoint)
	'''---------------------------'''

def mode88(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode88(admin, name, printpoint)
	'''---------------------------'''

def mode89(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode89(admin, name, printpoint)
	'''---------------------------'''
	
def mode90(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode90(admin, name, printpoint)
	'''---------------------------'''

def mode91(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode91(admin, name, printpoint)
	'''---------------------------'''

def mode92(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode92(admin, name, printpoint)
	'''---------------------------'''

def mode93(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode93(admin, name, printpoint)
	'''---------------------------'''

def mode101(value, admin, name):
	'''------------------------------
	---TOTAL-MOUSE-------------------
	------------------------------'''
	xbmc.sleep(200)
	TotalMouse = getsetting('TotalMouse')
	path = os.path.join(featherenceservice_path, 'specials', 'tools', 'EAT_gil900.exe')
	if '0' in value:
		if TotalMouse == 'true':
			setsetting('TotalMouse','false')
			TotalMouse = 'false'
		else:
			setsetting('TotalMouse','true')
			TotalMouse = "true"
		xbmc.sleep(100)
		
	if systemplatformwindows:
		if os.path.exists(path):
			terminal('TASKKILL /im EAT_gil900.exe /f',"EAT-end") ; xbmc.sleep(200) ; terminal('TASKKILL /im EAT_gil900.exe /f',"EAT-end") ; xbmc.sleep(200)
			if TotalMouse == "true":
				terminal('"'+path+'"', 'EAT-start')
				if '0' in value: notification("TotalMouse by gil900", "Enabled!", "", 2000) ; xbmc.sleep(1000)
			else:
				if '0' in value: notification('Total Mouse is not active!','','',1000)
				'''---------------------------'''
		else: notification_common("26")
	else: notification('OS not supported!','','',1000)

def mode102(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode102(admin, name, printpoint)
	'''---------------------------'''
	
def mode103(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode103(admin, name, printpoint)
	'''---------------------------'''

def mode104(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode104(admin, name, printpoint)
	'''---------------------------'''

def mode105(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode105(admin, name, printpoint)
	'''---------------------------'''

def mode106(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode106(admin, name, printpoint)
	'''---------------------------'''

def mode107(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode107(admin, name, printpoint)
	'''---------------------------'''

def mode108(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode108(admin, name, printpoint)
	'''---------------------------'''

def mode109(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode109(admin, name, printpoint)
	'''---------------------------'''

def mode110(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode110(admin, name, printpoint)
	'''---------------------------'''
	
def mode111(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode111(admin, name, printpoint)
	'''---------------------------'''

def mode112(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode112(admin, name, printpoint)
	'''---------------------------'''

def mode113(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode113(admin, name, printpoint)
	'''---------------------------'''

def mode114(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode114(admin, name, printpoint)
	'''---------------------------'''

def mode115(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode115(admin, name, printpoint)
	'''---------------------------'''

def mode116(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode116(admin, name, printpoint)
	'''---------------------------'''

def mode117(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode117(admin, name, printpoint)
	'''---------------------------'''

def mode118(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode118(admin, name, printpoint)
	'''---------------------------'''

def mode119(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode119(admin, name, printpoint)
	'''---------------------------'''

def mode120(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode120(admin, name, printpoint)
	'''---------------------------'''
	
def mode121(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode121(admin, name, printpoint)
	'''---------------------------'''

def mode122(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode122(admin, name, printpoint)
	'''---------------------------'''

def mode123(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode123(admin, name, printpoint)
	'''---------------------------'''

def mode124(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode124(admin, name, printpoint)
	'''---------------------------'''

def mode125(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode125(admin, name, printpoint)
	'''---------------------------'''

def mode126(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode126(admin, name, printpoint)
	'''---------------------------'''

def mode127(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode127(admin, name, printpoint)
	'''---------------------------'''

def mode128(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode128(admin, name, printpoint)
	'''---------------------------'''

def mode129(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode129(admin, name, printpoint)
	'''---------------------------'''

def mode130(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode130(admin, name, printpoint)
	'''---------------------------'''
	
def mode131(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode131(admin, name, printpoint)
	'''---------------------------'''

def mode132(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode132(admin, name, printpoint)
	'''---------------------------'''

def mode133(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode133(admin, name, printpoint)
	'''---------------------------'''

def mode134(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode134(admin, name, printpoint)
	'''---------------------------'''

def mode135(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode135(admin, name, printpoint)
	'''---------------------------'''

def mode136(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode136(admin, name, printpoint)
	'''---------------------------'''

def mode137(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode137(admin, name, printpoint)
	'''---------------------------'''

def mode138(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode138(admin, name, printpoint)
	'''---------------------------'''

def mode139(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode139(admin, name, printpoint)
	'''---------------------------'''

def mode140(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode140(admin, name, printpoint)
	'''---------------------------'''
	
def mode141(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode141(admin, name, printpoint)
	'''---------------------------'''

def mode142(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode142(admin, name, printpoint)
	'''---------------------------'''

def mode143(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode143(admin, name, printpoint)
	'''---------------------------'''

def mode144(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode144(admin, name, printpoint)
	'''---------------------------'''

def mode145(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode145(admin, name, printpoint)
	'''---------------------------'''

def mode146(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode146(admin, name, printpoint)
	'''---------------------------'''

def mode147(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode147(admin, name, printpoint)
	'''---------------------------'''

def mode148(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode148(admin, name, printpoint)
	'''---------------------------'''

def mode149(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode149(admin, name, printpoint)
	'''---------------------------'''

def mode150(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode150(admin, name, printpoint)
	'''---------------------------'''

def mode151(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode151(admin, name, printpoint)
	'''---------------------------'''

def mode152(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode152(admin, name, printpoint)
	'''---------------------------'''

def mode153(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode153(admin, name, printpoint)
	'''---------------------------'''

def mode154(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode154(admin, name, printpoint)
	'''---------------------------'''

def mode155(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode155(admin, name, printpoint)
	'''---------------------------'''

def mode156(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode156(admin, name, printpoint)
	'''---------------------------'''

def mode157(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode157(admin, name, printpoint)
	'''---------------------------'''

def mode158(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode158(admin, name, printpoint)
	'''---------------------------'''

def mode159(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode159(admin, name, printpoint)
	'''---------------------------'''

def mode160(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode160(admin, name, printpoint)
	'''---------------------------'''

def mode161(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode161(admin, name, printpoint)
	'''---------------------------'''

def mode162(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode162(admin, name, printpoint)
	'''---------------------------'''

def mode163(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode163(admin, name, printpoint)
	'''---------------------------'''

def mode164(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode164(admin, name, printpoint)
	'''---------------------------'''

def mode165(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode165(admin, name, printpoint)
	'''---------------------------'''

def mode166(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode166(admin, name, printpoint)
	'''---------------------------'''

def mode167(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode167(admin, name, printpoint)
	'''---------------------------'''

def mode168(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode168(admin, name, printpoint)
	'''---------------------------'''

def mode169(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode169(admin, name, printpoint)
	'''---------------------------'''

def mode170(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode170(admin, name, printpoint)
	'''---------------------------'''

def mode171(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode171(admin, name, printpoint)
	'''---------------------------'''

def mode172(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode172(admin, name, printpoint)
	'''---------------------------'''

def mode173(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode173(admin, name, printpoint)
	'''---------------------------'''

def mode174(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode174(admin, name, printpoint)
	'''---------------------------'''

def mode175(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode175(admin, name, printpoint)
	'''---------------------------'''

def mode176(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode176(admin, name, printpoint)
	'''---------------------------'''

def mode177(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode177(admin, name, printpoint)
	'''---------------------------'''

def mode178(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode178(admin, name, printpoint)
	'''---------------------------'''

def mode179(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode179(admin, name, printpoint)
	'''---------------------------'''
	
def mode180(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode180(admin, name, printpoint)
	'''---------------------------'''

def mode181(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode181(admin, name, printpoint)
	'''---------------------------'''

def mode182(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode182(admin, name, printpoint)
	'''---------------------------'''

def mode183(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode183(admin, name, printpoint)
	'''---------------------------'''

def mode184(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode184(admin, name, printpoint)
	'''---------------------------'''

def mode185(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode185(admin, name, printpoint)
	'''---------------------------'''

def mode186(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode186(admin, name, printpoint)
	'''---------------------------'''

def mode187(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode187(admin, name, printpoint)
	'''---------------------------'''

def mode188(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode188(admin, name, printpoint)
	'''---------------------------'''

def mode189(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode189(admin, name, printpoint)
	'''---------------------------'''
	
def mode190(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode190(admin, name, printpoint)
	'''---------------------------'''

def mode191(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode191(admin, name, printpoint)
	'''---------------------------'''

def mode192(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode192(admin, name, printpoint)
	'''---------------------------'''

def mode193(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode193(admin, name, printpoint)
	'''---------------------------'''

def mode194(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode194(admin, name, printpoint)
	'''---------------------------'''

def mode195(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode195(admin, name, printpoint)
	'''---------------------------'''

def mode196(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode196(admin, name, printpoint)
	'''---------------------------'''

def mode197(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode197(admin, name, printpoint)
	'''---------------------------'''

def mode198(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode198(admin, name, printpoint)
	'''---------------------------'''

def mode199(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode199(admin, name, printpoint)
	'''---------------------------'''
	
def mode200(value, admin, name, printpoint):
	'''------------------------------
	---DIALOG-SELECT-(10-100)--------
	------------------------------'''
	extra = "" ; TypeError = "" ; value2 = "" ; returned = ""
	list = ['-> (Exit)', 'default', '10', '20', '30', '40', '50', '60', '70', '80', '90', '100']
	
	if value != "":
		try:
			test = xbmc.getInfoLabel('Skin.String('+value+')')
			if test != None: printpoint = printpoint + "1"
		except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)
	else: pass
	
	if "1" in printpoint:
		returned, value2 = dialogselect('$LOCALIZE[74433]',list,0)
	
		if returned == -1: printpoint = printpoint + "9"
		elif returned == 0: printpoint = printpoint + "8"
		else: printpoint = printpoint + "7"
		
		if "7" in printpoint:
			if value2 == 'default': setSkinSetting('0', str(value), "")
			elif value2 != "": setSkinSetting('0', str(value), value2)
			else: printpoint = printpoint + "8"
			
			if not "8" in printpoint:
				notification(".","","",1000)
				xbmc.sleep(200)
				xbmc.executebuiltin('Action(Back)')
				xbmc.sleep(200)
				ReloadSkin(admin)
	
	text = "list" + space2 + str(list) + space + "returned" + space2 + str(returned) + space + "value" + space2 + str(value) + space + "value2" + space2 + str(value2) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

def Custom1000(title="", progress="", comment="", autoclose=""):
	if libraryisscanningvideo: xbmc.executebuiltin('UpdateLibrary(video)')
	xbmc.executebuiltin('SetProperty(1000title,'+title+',home)')
	xbmc.executebuiltin('SetProperty(1000progress,'+str(progress)+',home)')
	xbmc.executebuiltin('SetProperty(1000comment,'+comment+',home)')
	custom1000W = xbmc.getCondVisibility('Window.IsVisible(Custom1000.xml)')
	xbmc.executebuiltin('Dialog.Close(all,true)')
	if not custom1000W:
		notification_common("2")
		xbmc.executebuiltin('ActivateWindow(1000)') ; xbmc.sleep(100)
	
	if autoclose != "": xbmc.executebuiltin('AlarmClock(timeout,Action(Back),'+str(autoclose)+',silent)')
	
	
	text = 'title' + space2 + str(title)
	printlog(title='Custom1000', printpoint=printpoint, text=text, level=0, option="")
	
def getRandomColors(admin):
	#colors_file = os.path.join(skin_path, 'media', 'buttons', 'colors', 'colors.xml')
	#infile_colors_ = read_from_file(colors_file, silent=True)
	
	returned, value1 = getRandom("0", min=0, max=70, percent=50)
	returned, value2 = getRandom("0", min=0, max=70, percent=50)
	returned, value3 = getRandom("0", min=0, max=70, percent=50)
	returned, value4 = getRandom("0", min=0, max=70, percent=50)
	returned, value5 = getRandom("0", min=0, max=70, percent=50)
	listL = [value1, value2, value3, value4, value5]
	count = 0
	for value in listL:
		count += 1
		if value > 0 and value <= 5: value = '' ; value_ = ""
		elif value > 5 and value <= 10: value = 'ff000000' ; value_ = 'black'
		elif value > 10 and value <= 15: value = 'ff00a693' ; value_ = 'persian green'
		elif value > 15 and value <= 20: value = 'ff00cccc' ; value_ = 'robin egg blue'
		elif value > 20 and value <= 25: value = 'ffffc40c' ; value_ = 'mikado yellow'
		elif value > 25 and value <= 30: value = 'ff00ffff' ; value_ = 'aqua'
		elif value > 30 and value <= 35: value = 'ff1e4d2b' ; value_ = 'cal poly pomona green'
		elif value > 35 and value <= 40: value = 'ff2f4f4f' ; value_ = 'dark slate gray'
		elif value > 40 and value <= 45: value = 'ff4cbb17' ; value_ = 'kelly green'
		elif value > 45 and value <= 50: value = 'ff5d8aa8' ; value_ = 'air force blue'
		elif value > 50 and value <= 55: value = 'ff8b4513' ; value_ = 'saddle brown'
		elif value > 55 and value <= 60: value = 'ff89cff0' ; value_ = 'baby blue'
		elif value > 60 and value <= 65: value = 'fff5f5f5' ; value_ = 'white smoke'
		elif value > 65 and value <= 70: value = 'ffffd1dc' ; value_ = 'pastel pink'
		
		if count == 1: value1 = value ; value1_ = value_
		elif count == 2: value2 = value ; value2_ = value_
		elif count == 3: value3 = value ; value3_ = value_
		elif count == 4: value4 = value ; value4_ = value_
		elif count == 5: value5 = value ; value5_ = value_
	
	return value1, value1_, value2, value2_, value3, value3_, value4, value4_, value5, value5_
			
def mode201(value, admin, name, printpoint):
	'''------------------------------
	---RESET-TO-DEFAULT--------------
	------------------------------'''
	#from variables2 import *
	returned = ""
	container50hasfocus390 = xbmc.getCondVisibility('Container(50).HasFocus(390)') #BUTTONS

	list = ['-> (Exit)', localize(10035) + space + "(" + localize(593) + ")", localize(590) + space + "(" + localize(593) + ")", \
	localize(74840) + space + "(" + localize(80,addon='script.featherence.service') + ")", localize(74840) + space + localize(590) + space + "(" + localize(80,addon='script.featherence.service') + ")", \
	localize(74840) + space + "(" + localize(593) + ")", localize(74840) + space + localize(590) + space + "(" + localize(593) + ")", \
	localize(10035) + space + localize(78215) + space + "(" + localize(593) + ")", localize(10035) + space + localize(78215) + space + localize(590) + space + "(" + localize(593) + ")", \
	localize(10035) + space + "(" + localize(74614) + ")"]
	
	if value == "" or container50hasfocus390:
		returned, value_ = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
		
		if returned == -1: printpoint = printpoint + "9"
		elif returned == 0: printpoint = printpoint + "8"
		else: printpoint = printpoint + "7"
		
	if ("7" in printpoint or value != "") and not "8" in printpoint and not "9" in printpoint:
		if (returned == 1 or value == "1"): printpoint = printpoint + "ACEG" #RESET-ALL
		elif returned == 2: printpoint = printpoint + "BDFH" #RANDOM-ALL
		elif returned == 3: printpoint = printpoint + "C" #RESET-BUTTONS-COLORS
		elif returned == 4: printpoint = printpoint + "D" #RANDOM-BUTTONS-COLORS
		elif returned == 5: printpoint = printpoint + "CE" #RESET-ALL-COLORS
		elif returned == 6: printpoint = printpoint + "DF" #RANDOM-ALL-COLORS
		elif returned == 7: printpoint = printpoint + "G" #RESET-ALL-TRANSPERANCY
		elif returned == 8: printpoint = printpoint + "H" #RANDOM-ALL-TRANSPERANCY
		elif (returned == 9 or value == "9"): returned = 9 ; printpoint = printpoint + "I" #RESET BUTTONS PROPERTIES
		
		from variables2 import labelT, list1, list0, list0c, list0c2, list0o
		Custom1000(name,0,str(list[returned]),20)
		'''---------------------------'''
	if "A" in printpoint:
		Custom1000(name,20,str(list[returned]),20)
		xbmc.executebuiltin('SetProperty(1000title,'+name+',home)')
		xbmc.executebuiltin('SetProperty(1000comment,This action may take a while be patient!,home)')
		for x in list0: setSkinSetting('0',x,"")
		for x in list1: setSkinSetting('1',x,"false")
		'''---------------------------'''
	
	if "B" in printpoint:
		Custom1000(name,30,str(list[returned]),20)
		for x in list1:
			returned1, value1 = getRandom("0", min=0, max=100, percent=50)
			if returned1 == 'ok': value1 = "true"
			else: value1 = "false"
			setSkinSetting('1',x,value1)
		
	if "C" in printpoint:
		Custom1000(name,40,str(list[returned]),20)
		'''RESET-BUTTONS-COLORS'''
		for i in range(18,20):
			setSkinSetting('0','color'+str(i),"")
			setSkinSetting('0','color'+str(i)+'.name',"")
			'''---------------------------'''
		for i in range(90,120):
			setSkinSetting('0','color'+str(i),"")
			setSkinSetting('0','color'+str(i)+'.name',"")
			'''---------------------------'''
	
	if "D" in printpoint:
		Custom1000(name,50,str(list[returned]),20)
		value1, value1_, value2, value2_, value3, value3_, value4, value4_, value5, value5_ = getRandomColors(admin)
		for i in range(18,20):
			x = labelT.get('label'+str(i))
			if x != "":
				returnedx, count = getRandom("0", min=1, max=5, percent=50)
				if count == 1: value = value1 ; value_ = value1_
				elif count == 2: value = value2 ; value_ = value2_
				elif count == 3: value = value3 ; value_ = value3_
				elif count == 4: value = value4 ; value_ = value4_
				elif count == 5: value = value5 ; value_ = value5_
				setSkinSetting('0','color'+str(i),value)
				setSkinSetting('0','color'+str(i)+'.name',value_)
				'''---------------------------'''
		for i in range(90,120):
			x = labelT.get('label'+str(i))
			if x != "":
				returnedx, count = getRandom("0", min=1, max=5, percent=50)
				if count == 1: value = value1 ; value_ = value1_
				elif count == 2: value = value2 ; value_ = value2_
				elif count == 3: value = value3 ; value_ = value3_
				elif count == 4: value = value4 ; value_ = value4_
				elif count == 5: value = value5 ; value_ = value5_
				setSkinSetting('0','color'+str(i),value)
				setSkinSetting('0','color'+str(i)+'.name',value_)
				'''---------------------------'''
	
	if "E" in printpoint:
		Custom1000(name,60,str(list[returned]),15)
		'''RESET-ALL-COLORS'''
		for x in list0c: setSkinSetting('0',x,"")
		for x in list0c: setSkinSetting('0',x,"")
		'''---------------------------'''
		
	if "F" in printpoint:
		Custom1000(name,70,str(list[returned]),15)
		value1, value1_, value2, value2_, value3, value3_, value4, value4_, value5, value5_ = getRandomColors(admin)
		'''RANDOM-ALL-COLORS'''
		returnedx, count = getRandom("0", min=1, max=5, percent=50)
		for x in list0c:
			if count == 1: value = value1 ; value_ = value1_
			elif count == 2: value = value2 ; value_ = value2_
			elif count == 3: value = value3 ; value_ = value3_
			elif count == 4: value = value4 ; value_ = value4_
			elif count == 5: value = value5 ; value_ = value5_
			setSkinSetting('0',x,value)
			setSkinSetting('0',x+'.name',value_)
			'''---------------------------'''
		
	if "G" in printpoint:
		Custom1000(name,90,str(list[returned]),10)
		'''RESET-ALL-TRANSPERANCY'''
		for x in list0o: setSkinSetting('0',x,"")
		'''---------------------------'''
		
	if "H" in printpoint:
		Custom1000(name,90,str(list[returned]),10)
		'''RANDOM-ALL-TRANSPERANCY'''
		returnedx, value1 = getRandom("0", min=0, max=55, percent=50)
		returnedx, value2 = getRandom("0", min=0, max=55, percent=50)
		returnedx, value3 = getRandom("0", min=0, max=55, percent=50)
		returnedx, value4 = getRandom("0", min=0, max=55, percent=50)
		returnedx, value5 = getRandom("0", min=0, max=55, percent=50)
		listL = [value1, value2, value3, value4, value5]
		count = 0
		for value in listL:
			count += 1
			if value > 0 and value <= 5: value = ''
			elif value > 5 and value <= 10: value = ''
			elif value > 10 and value <= 15: value = '20'
			elif value > 15 and value <= 20: value = '30'
			elif value > 20 and value <= 25: value = '40'
			elif value > 25 and value <= 30: value = '50'
			elif value > 30 and value <= 35: value = '60'
			elif value > 35 and value <= 40: value = '70'
			elif value > 40 and value <= 45: value = '80'
			elif value > 45 and value <= 50: value = '90'
			elif value > 50 and value <= 55: value = '100'
			
			if count == 1: value1 = str(value)
			elif count == 2: value2 = str(value)
			elif count == 3: value3 = str(value)
			elif count == 4: value4 = str(value)
			elif count == 5: value5 = str(value)
			'''---------------------------'''
		
		for x in list0o:
			returnedx, count = getRandom("0", min=1, max=5, percent=50)
			if count == 1: y = str(value1)
			elif count == 2: y = str(value2)
			elif count == 3: y = str(value3)
			elif count == 4: y = str(value4)
			elif count == 5: y = str(value5)
			setSkinSetting('0',x,y)
			'''---------------------------'''
	
	if "I" in printpoint:
		Custom1000(name,20,str(list[returned]),10)
		'''RESET BUTTONS PROPERTIES'''
		count = 0
		for i in range(18,20):
			setSkinSetting('0','label'+str(i),"")
			setSkinSetting('0','color'+str(i),"")
			setSkinSetting('0','icon'+str(i),"")
			setSkinSetting('0','background'+str(i),"")
			setSkinSetting('1','off'+str(i),"")
		for i in range(90,120):
			count += 2
			i_ = xbmc.getInfoLabel('Skin.String(label'+str(i)+')')
			if i_ != "" and i_ != None:
				setSkinSetting('0','id'+str(i),"")
				setSkinSetting('0','label'+str(i),"")
				setSkinSetting('0','action'+str(i),"")
				setSkinSetting('0','color'+str(i),"")
				setSkinSetting('0','icon'+str(i),"")
				setSkinSetting('0','background'+str(i),"")
				setSkinSetting('1','off'+str(i),"")
				setSkinSetting('1','sub'+str(i),"")
				'''---------------------------'''
			for i2 in range(100,110):
				i2_ = xbmc.getInfoLabel('Skin.String(label'+str(i)+'_'+str(i2)+')')
				if i2_ != "" and i_ != None:
					#setSkinSetting('0','id'+str(i)+'_'+str(i2),"")
					setSkinSetting('0','label'+str(i)+'_'+str(i2),"")
					setSkinSetting('0','action'+str(i)+'_'+str(i2),"")
					setSkinSetting('1','off'+str(i)+'_'+str(i2),"")
					setSkinSetting('0','icon'+str(i)+'_'+str(i2),"")
					'''---------------------------'''
		
	if ("7" in printpoint or value != "") and not "8" in printpoint and not "9" in printpoint:
		if value != "9":
			Custom1000(name,90,str(list[returned]),3)
			notification(".","","",1000)
			ReloadSkin(admin)
			Custom1000(name,100,str(list[returned]),1) ; xbmc.sleep(1500)
			xbmc.executebuiltin('ActivateWindow(1117)') ; xbmc.sleep(2000) ; xbmc.executebuiltin('ActivateWindow(1173)')
		
	text = "list" + space2 + str(list) + newline + \
	"returned" + space2 + str(returned)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

def mode202(value, admin, name, printpoint):
	'''------------------------------
	---CHOOSE-COLORS-2---------------
	------------------------------'''
		
	#x = xbmc.getInfoLabel('Container(9003).ListItem(0).Label')
	#x2 = xbmc.getInfoLabel('Container(9003).ListItemNoWrap(0).Property(colorID)')
	#y = xbmc.getInfoLabel('Container(9003).ListItemNoWrap(0).Property(color)')
	#listitempropertycolor = xbmc.getInfoLabel('ListItem.Property(color)')
	
	if property_temp != "":
		if value == "30110":
			'''DEFAULT COLOR'''
			printpoint = printpoint + "2"
			setSkinSetting('0', property_temp, "")
			setSkinSetting('0', property_temp + '.name', "")
			notification("...","","",1000)
			xbmc.executebuiltin('Dialog.Close(1175)')
			if custom1173W: xbmc.executebuiltin('Dialog.Close(1173)')
			xbmc.executebuiltin('Dialog.Close(1117)')
			xbmc.executebuiltin('Action(Close)')
			xbmc.executebuiltin('ActivateWindow(1117)')
			if custom1173W: xbmc.executebuiltin('ActivateWindow(1173)')
			'''---------------------------'''
		else: printpoint = printpoint + "9"
		
	else: printpoint = printpoint + "9"
	xbmc.executebuiltin('ClearProperty(TEMP,home)')
	text = "value" + space2 + str(value) + space + "property_buttonid" + space2 + str(property_buttonid) + newline + \
	'property_temp' + space2 + str(property_temp)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
		
def mode204(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode204(admin, name, printpoint)
	'''---------------------------'''

def mode206(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode206(admin, name, printpoint)
	'''---------------------------'''

def mode207(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode207(admin, name, printpoint)
	'''---------------------------'''

def mode208(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode208(admin, name, printpoint)
	'''---------------------------'''

def mode209(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode209(admin, name, printpoint)
	'''---------------------------'''

def mode210(value, admin, name, printpoint):
	'''------------------------------
	---MOVE-ITEM---------------------
	------------------------------'''
	extra = "" ; extra2 = "" ; TypeError = "" ; x = "" ; y = "" ; y2 = ""
	
	xbmc.executebuiltin('Action(Close)')
	'''---------------------------'''

	if not int(property_buttonid) > 0 or not int(property_buttonid_) > 0: printpoint = printpoint + "9A"
	if '0' in value:
		printpoint = printpoint + "0"
		if property_temp == property_buttonid or property_temp2 == property_buttonid_: printpoint = printpoint + "9B"
		if property_temp2 == "": printpoint = printpoint + "9C"
		else:
			try:
				if not int(property_temp2) > 0: printpoint = printpoint + "9D"
			except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "9E"

	if not '9' in printpoint:
		notification_common("2")
		from variables2 import *
		if '0' in value:
			for i in range(0,2):
				x = "" ; y = "" ; y2 = ""
				extra = extra + "i" + space2 + str(i)
				if i == 0:
					'''property_buttonid -> property_temp'''
					x = property_temp2
					x2 = property_temp
					y = property_buttonid_
					y2 = property_buttonid
					'''---------------------------'''
				elif i == 1:
					'''property_temp -> property_buttonid'''
					x = property_buttonid_
					x2 = property_buttonid_
					y = property_temp2
					y2 = property_temp
					'''---------------------------'''
				else: pass	
				if x != "" and y != "":
					'''continue'''
					notification("...", str(labelT.get('label'+x)) + ' -> ' + str(labelT.get('label'+y)), "", 1000)
					setSkinSetting('0','id'+x,str(idT.get('id'+y)))
					setSkinSetting('0','label'+x,str(labelT.get('label'+y)))
					setSkinSetting('0','action'+x,str(actionT.get('action'+y)))
					setSkinSetting('1','off'+x,str(offT.get('off'+y)))
					setSkinSetting('0','color'+x,str(colorT.get('color'+y)))
					setSkinSetting('0','icon'+x,str(iconT.get('icon'+y)))
					#setSkinSetting('0','background'+y,str(backgroundT.get('background'+x)))
					setSkinSetting('1','sub'+x,str(subT.get('sub'+y)))
					'''---------------------------'''
				else: notification("Error","","",2000) ; printpoint = printpoint + "8"
		elif '1' in value or '2' in value:
			for i in range(0,2):
				x = "" ; y = ""
				if i == 0:
					if '1' in value:
						'''property_subbuttonid_ -> property_previoussubbuttonid_'''
						x = property_previoussubbuttonid_
						y = property_subbuttonid_
						'''---------------------------'''
					elif '2' in value:
						'''property_subbuttonid_ -> property_nextsubbuttonid_'''
						x = property_nextsubbuttonid_
						y = property_subbuttonid_
						'''---------------------------'''
					
				elif i == 1:
					'''property_previoussubbuttonid_ -> property_subbuttonid_'''
					if '1' in value:
						'''property_previoussubbuttonid_ -> property_subbuttonid_'''
						x = property_subbuttonid_
						y = property_previoussubbuttonid_
						'''---------------------------'''
					elif '2' in value:
						'''property_nextsubbuttonid_ -> property_subbuttonid_'''
						x = property_subbuttonid_
						y = property_nextsubbuttonid_
						'''---------------------------'''
					
				else: pass
				
				if x != "" and y != "":
					'''continue'''
					label_ = xbmc.getInfoLabel('$VAR['+label_T.get('label'+y)+']')
					notification("...", "", "", 1000)
					setSkinSetting('1','off'+x,str(off_T.get('off'+y)))
					setSkinSetting('0','label'+x,label_T.get('label'+y))
					setSkinSetting('0','action'+x,str(action_T.get('action'+y)))
					setSkinSetting('0','icon'+x,str(icon_T.get('icon'+y)))
					
					#extra = extra + newline + label_T.get('label'+y)
					#extra = extra + newline + 'label_' + space2 + label_
					#extra = extra + newline + action_T.get('action'+y)
					#extra = extra + newline + icon_T.get('icon'+y)
				else: printpoint = printpoint + "9" ; break
				
				extra2 = extra2 + newline + "i" + space2 + str(i) + space + "x" + space2 + str(x) + space + "y" + space2 + str(y) + space + "y2" + space2 + str(y2) + space
	#dp.close
	if "9" in printpoint: notification("Error Occured!", '', '', 2000)
	else:
		pass#ReloadSkin(admin)
		xbmc.sleep(500) ; xbmc.executebuiltin('Action(Down)') ; xbmc.sleep(500) ; xbmc.executebuiltin('Action(Up)')
	
	text = "value" + space2 + str(value) + newline + \
	"property_buttonid" + space2 + str(property_buttonid) + space + "property_buttonid_" + space2 + str(property_buttonid_) + newline + \
	"property_temp" + space2 + str(property_temp) + space + "property_temp2" + space2 + str(property_temp2) + newline + \
	"property_subbuttonid_" + space2 + str(property_subbuttonid_) + newline + \
	"property_previoussubbuttonid_" + space2 + str(property_previoussubbuttonid_) + newline + \
	"property_nextsubbuttonid_" + space2 + str(property_nextsubbuttonid_) + newline + \
	extra + extra2
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def mode211(value, admin, name, printpoint):
	'''------------------------------
	---Create-New-Item---------------
	------------------------------'''
	from variables2 import *
	extra = "" ; TypeError = "" ; x = "" ; y = ""
	
	#xbmc.executebuiltin('Action(Close)')
	if not int(property_buttonid_) > 0: printpoint = printpoint + "1" ; notification("Error No.1", "", "", 1000)
	else:
		'''Get new control ID'''
		if '0' in value:
			'''main menu item'''
			xbmc.executebuiltin('Dialog.Close(1175)')
			for i in range(100,109):
				x = xbmc.getInfoLabel('Skin.String(label'+str(i)+')')
				if x == "":
					y = str(i)
					setSkinSetting('0','label'+y,"...")
					setSkinSetting('1','off'+y,"false")
					break
				else: pass
		
		elif '1' in value:
			'''sub menu item'''
			#xbmc.executebuiltin('Dialog.Close(1138)')
			for i in range(100,109):
				x = xbmc.getInfoLabel('Skin.String(label'+property_buttonid+'_'+str(i)+')')
				if x == "":
					y = property_buttonid+'_'+str(i)
					#setSkinSetting('0','id'+y,y)
					setSkinSetting('0','label'+y,"...")
					setSkinSetting('1','off'+y,"false")
					break
				else: pass

					
		if y == "": printpoint = printpoint + "9" ; notification("Cannot create new buttons","Delete some first","",2000)
		else:
			notification("...", "", "", 1000)
			mode232(y, admin, 'ACTION-BUTTON', printpoint)
			'''---------------------------'''
				
	text = "value" + space2 + str(value) + newline + \
	"property_buttonid" + space2 + str(property_buttonid) + space + "property_buttonid_" + space2 + str(property_buttonid_) + newline + \
	"property_temp" + space2 + str(property_temp) + space + "property_temp2" + space2 + str(property_temp2) + newline + \
	"x" + space2 + str(x) + newline + \
	"y" + space2 + str(y) + newline + \
	extra
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def mode212(value, admin, name, printpoint):
	'''------------------------------
	---REMOVE-ITEM-------------------
	------------------------------'''
	extra = "" ; extra2 = "" ; TypeError = "" ; x = "" ; two = 1 ; property_buttonname2 = ""

	try:
		if property_buttonid == "": printpoint = printpoint + "9A"
		else: test = int(property_buttonid_) + 1
		if '0' in value:
			if int(property_buttonid) < 100 and not 'B' in value: printpoint = printpoint + "9B"
		if '1' in value:
			if not "_" in property_subbuttonid_: printpoint = printpoint + "9C"
			if not "_" in property_subbuttonid_: printpoint = printpoint + "9D"
			if not property_buttonid in property_subbuttonid_: printpoint = printpoint + "9E"
		if 'B' in value and property_buttonid != property_buttonid_:
			from variables2 import idT, labelT
			two = 2
			y = 'Reset item'
			x = property_buttonid_
			property_buttonname2 = labelT.get('label'+property_buttonid)
			extra2 = extra2 + newline + "This action will also reset" + space2 + str(property_buttonname2) + space + "(" + str(property_buttonid) + ")"
		
		else:
			y = 'Remove item'
			x = property_buttonid_
			two = 1
			
	except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "9F"
	
	if not '9' in printpoint:
		if '0' in value:
			'''main menu item'''
			printpoint = printpoint + "0"
			xbmc.sleep(100) ; returned = dialogyesno(y + space2 + str(property_buttonname), "Choose YES to proceed!" + extra2)
			if returned == 'skip': printpoint = printpoint + "8"
			else:
				for i in range(0,two):
					if i == 1: x = str(property_buttonid)
					setSkinSetting('1','off' + x,"false")
					if int(property_buttonid) > 99 and not 'B' in value: setSkinSetting('0','label' + x,"")
					else: setSkinSetting('0','label' + x,"...")
					setSkinSetting('1','sub' + x,"false")
					setSkinSetting('0','id' + x,"")
					setSkinSetting('0','color' + x,"")
					setSkinSetting('0','icon' + x,"")
					setSkinSetting('0','action' + x,"")

					if '2' in value:
						'''sub menu items'''
						printpoint = printpoint + "2"
						if x == "": printpoint = printpoint + "9L"
						else:
							for i in range(90,109):
								if i > 99 : setSkinSetting('0','label'+x+'_'+str(i),"")
								else: setSkinSetting('0','label'+x+'_'+str(i),"")
								setSkinSetting('1','off'+x+'_'+str(i),"false")
								#setSkinSetting('0','id'+x+'_'+str(i),"")
								setSkinSetting('0','action'+x+'_'+str(i),"")
								setSkinSetting('0','icon'+x+'_'+str(i),"")
								'''---------------------------'''			
				printpoint = printpoint + "7"
					
		if '1' in value:
			'''sub menu item'''
			printpoint = printpoint + "1"
			if 'B' in value:
				y = 'Reset item'
				x = property_subbuttonid_
			else:
				y = 'Remove item'
				x = property_subbuttonid_
				
			xbmc.sleep(100) ; returned = dialogyesno(y + space2 + str(property_subbuttonname), "Choose YES to proceed!")
			if returned == 'skip': printpoint = printpoint + "8"
			else:
				setSkinSetting('1','off' + x,"false")
				if not '_90' in property_subbuttonid_ and not 'B' in value: setSkinSetting('0','label' + x,"")
				else: setSkinSetting('0','label' + x,"...")
				#setSkinSetting('0','id' + x,"")
				setSkinSetting('0','icon' + x,"")
				setSkinSetting('0','action' + x,"")
				printpoint = printpoint + "7"
		
	
	if not "7" in printpoint and not "8" in printpoint:
		'''Error'''
		notification("Error...","","",1000)
	else:
		xbmc.executebuiltin('Action(Close)') ; xbmc.sleep(500)
		xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value='+property_buttonid_+')')
		if two == 2: xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value='+property_buttonid+')')
	
	
	
	text = "value" + space2 + str(value) + newline + \
	"property_buttonid" + space2 + str(property_buttonid) + space + "property_buttonid_" + space2 + str(property_buttonid_) + space + "property_buttonname" + space2 + str(property_buttonname) + newline + \
	"property_buttonname2" + space2 + str(property_buttonname2) + newline + \
	"property_subbuttonid_" + space2 + str(property_subbuttonid_) + space + "property_subbuttonname" + space2 + str(property_subbuttonname) + newline + \
	extra
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def mode213(value, admin, name, printpoint):
	'''------------------------------
	---Includes_HomeContent----------
	------------------------------'''
	list = [] ; i = 0 ; x = 0
	
	returned_Dialog, returned_Header, returned_Message = checkDialog(admin)
	if returned_Dialog != "": printpoint = printpoint + "9"
	
	elif value == '1' or value == '2':
		'''homeW/customhomecustomizerW'''
		if custom1138W or custom1139W or custom1175W or custom1173W or homeW: printpoint = printpoint + "9"
		x = xbmc.getInfoLabel('Container(9000).ListItem('+str(i)+').Label')
		y = xbmc.getInfoLabel('Container(9000).NumItems')

	elif value == '3':
		'''customhomecustomizer2W'''
		if custom1138W or custom1139W or custom1175W or custom1173W: printpoint = printpoint + "9"
		x = xbmc.getInfoLabel('Container(51).ListItem('+str(i)+').Label')
		y = xbmc.getInfoLabel('Container(51).NumItems')
	
	elif value == '4':
		'''Home'''
		x = 'N/A'
		y = 'N/A'
		
	try: test = int(y)
	except: y = 0
	
	if value == '1':
		if int(y) < 2:
			'''set default buttons'''
			printpoint = printpoint + "5"
			mode215('_', admin, name, "")
	
	if "9" in printpoint: pass
	elif (value == '1' or value == '2' or value == '3') and xbmc.getInfoLabel('$VAR[background]') == "" and reloadskin_check == "": printpoint = printpoint + "7A"
	elif value == '4' and xbmc.getCondVisibility('IsEmpty(Control.GetLabel(111))') and xbmc.getCondVisibility('!Control.IsVisible(7021)') and reloadskin_check == "": printpoint = printpoint + "7B"
	elif (x == "" or y == ""):
		'''ReloadSkin - Fix Bug'''
		count = 0
		for i in range(-5,5):
			count += 1
			x = xbmc.getInfoLabel('Container(9000).ListItem('+str(i)+').Label') + xbmc.getInfoLabel('Container(51).ListItem('+str(i)+').Label') + xbmc.getInfoLabel('Container(50).ListItem('+str(i)+').Label')
			list.append(x)
			if x != '' and x != 'Test': break
	
		if count > 7:
			printpoint = printpoint + "7D"
	
	else:
		pass
	
	if "7" in printpoint and not playerhasvideo: ReloadSkin(admin)
	
	text = "value" + space2 + str(value) + space + newline + \
	"x" + space2 + str(x) + space + "y" + space2 + str(y) + space + newline + \
	"list" + space2 + str(list) + newline + \
	"$VAR[background]" + space2 + str(xbmc.getInfoLabel('$VAR[background]')) + space + "$VAR[MainBackgroundTexture]" + space2 + str(xbmc.getInfoLabel('$VAR[MainBackgroundTexture]')) + newline + \
	"$VAR[Button9093]" + space2 + str(xbmc.getInfoLabel('$VAR[Button9093]')) + space + "reloadskin_check" + space2 + str(reloadskin_check)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def mode214(value, admin, name, printpoint):
	text = "value" + space2 + str(value)
	
	if value == '0':
		returned = dialogkeyboard(property_buttonname,'Button Name',0,"",'label'+property_buttonid_,"")
		if returned != 'skip':
			if returned == "": setSkinSetting('0','label'+property_buttonid_, '...')
	
	if value == '1':
		returned = dialogkeyboard(property_subbuttonname,'Sub Button Name',0,"",'label'+property_subbuttonid_,"")
		if returned != 'skip':
			if returned == "": setSkinSetting('0','label'+property_subbuttonid_, '...')
	
	if value == '5':
		'''SelectedColor'''
		returned_len = "" ; returned1 = "" ; path = ""
		property_selectedcolor = xbmc.getInfoLabel('Window(home).Property(SelectedColor)')
		currentbuttoncolor = xbmc.getInfoLabel('Skin.String(color'+property_buttonid_+')')
		notification(currentbuttoncolor,'Skin.String(color'+property_buttonid_+')','',2000)
		if property_selectedcolor == "" and property_buttonid_ != "": value2 = currentbuttoncolor
		else: value2 = property_selectedcolor
		
		returned = dialogkeyboard(value2,'Choose manual color code',0,"","","")
		if returned != 'skip':
			if returned != "":
				returned_len = len(returned) ; returned1 = returned[:2]
				if returned1 != "ff":
					if returned_len == 8: returned = returned.replace(returned1,"ff",1)
					elif returned_len == 7: returned = 'f' + returned
					elif returned_len == 6: returned = 'ff' + returned
				
				path = os.path.join(skin_path, 'media', 'buttons', 'colors', str(returned) + '.png')
				if os.path.exists(path):
					if str(returned) == currentbuttoncolor: pass
					else:
						setProperty('SelectedColor', str(returned), type="home")
						notification('New color selected!', str(returned), '', 1000)
				else: notification('Color is not available!', str(path), '', 6000)
	
		text = text + newline + 'returned' + space2 + str(returned) + space + 'returned_len' + space2 + str(returned_len) + space + 'returned1' + space2 + str(returned1) + newline + \
		'path' + space2 + str(path) + newline + \
		'property_selectedcolor' + space2 + str(property_selectedcolor) + newline + \
		'currentbuttoncolor' + space2 + str(currentbuttoncolor) + newline + \
		'value2' + space2 + str(value2)

	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def mode215(value, admin, name, printpoint):
	from variables2 import *
	extra2 = "" ; id = ""
				
	if value != "": notification_common("2")
	
	'''הגדרות'''
	if value != "":
		'''ראשי'''
		x = '18' ; id = x
		if id != "" and id != None:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(5))
			if value == 'RESET': setSkinSetting('0','icon'+id,'')		
			'''---------------------------'''
	
	'''כיבוי'''
	if value != "":
		'''ראשי'''
		x = '19' ; id = x
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(13005))
			if value == 'RESET': setSkinSetting('0','icon'+id,'')
			'''---------------------------'''
			
	'''סרטים'''
	if value != "":
		'''ראשי'''
		x = '90' ; id = idT2.get(x)
		if id != "" and id != None:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(342))
			setSkinSetting('0','action'+id,'ActivateWindow(Videos,MovieTitles,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/movies.png')		
			'''---------------------------'''
	
	'''סדרות'''
	if value != "":
		'''ראשי'''
		x = '91' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(20343))
			
			setSkinSetting('0','action'+id,'ActivateWindow(VideoLibrary,TVShowTitles,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/tvshows.png')
			'''---------------------------'''

	'''ערוצי טלוויזיה'''
	if value != "":
		'''ראשי'''
		x = '92' ; id = idT2.get(x)
		if id != "" and id != None:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(19023))
			setSkinSetting('0','action'+id,'RunScript(script.featherence.service,,?mode=517&value=0)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/LiveTV.png')
			'''---------------------------'''
	
	'''ילדים'''
	if value != "":
		'''ראשי'''
		x = '93' ; id = idT2.get(x) ; background = backgroundT.get('icon'+x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(73220))
			setSkinSetting('0','action'+id,'RunScript(script.featherence.service,,?mode=515&value=0)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/kids.png')
			'''---------------------------'''	
			
	'''מוזיקה'''
	if value != "":
		'''ראשי'''
		x = '94' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(2))
			setSkinSetting('0','action'+id,'RunScript(script.featherence.service,,?mode=514&value=0)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/music.png')
			'''---------------------------'''
	
	'''מעודפים'''
	if value != "":
		'''ראשי'''
		x = '95' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(1036))
			setSkinSetting('0','action'+id,'ActivateWindow(134)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/star.png')
			'''---------------------------'''	
	
	'''תמונות'''
	if value != "":
		'''ראשי'''
		x = '96' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(1))
			setSkinSetting('0','action'+id,'ActivateWindow(Pictures)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/pictures.png')
			'''---------------------------'''
	
	'''מזג אוויר'''
	if value != "":
		'''ראשי'''
		x = '97' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(8))
			setSkinSetting('0','action'+id,'ActivateWindow(MyWeather.xml)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/weather.png')
			'''---------------------------'''
			
	'''משחקים'''
	if value != "":
		'''ראשי'''
		x = '98' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 3:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(15016))
			setSkinSetting('0','action'+id,'RunScript(script.featherence.service,,?mode=510&value=0)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/games.png')
			'''---------------------------'''	

	'''דוקו'''
	if value != "":
		'''ראשי'''
		x = '99' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(78942))
			#setSkinSetting('0','action'+id,'RunScript(script.featherence.service,,?mode=519&value=0)')
			setSkinSetting('0','action'+id,'RunAddon(plugin.video.featherence.docu)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/animals.png')
			'''---------------------------'''
	
	text = "value" + space2 + str(value) + space + "id" + space2 + str(id) + newline + \
	"idT" + space2 + str(idT) + newline + \
	extra2
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")

def mode218(value, admin, name, printpoint):
	'''------------------------------
	---editButtonProprties-----------
	------------------------------'''	
	message = ""
	if "view" in value:
		myweatherW = xbmc.getCondVisibility('Window.IsVisible(MyWeather.xml)')
		dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
		if myweatherW:
			message = message + newline + "Day0 Title" + space2 + xbmc.getInfoLabel('Window.Property(Day0.Title)')
			message = message + newline + "Day1 Title" + space2 + xbmc.getInfoLabel('Window.Property(Day1.Title)')
			message = message + newline + "Day2 Title" + space2 + xbmc.getInfoLabel('Window.Property(Day2.Title)')
			message = message + newline + "Day3 Title" + space2 + xbmc.getInfoLabel('Window.Property(Day3.Title)')
			message = message + newline + "Day4 Title" + space2 + xbmc.getInfoLabel('Window.Property(Day4.Title)')
			
			message = message + newline + "Current day label (31)" + space2 + xbmc.getInfoLabel('Control.GetLabel(31)')
		
		elif dialogsubtitlesW:
			message = message + newline + "Subtitle_Service" + space2 + xbmc.getInfoLabel('Window(home).Property(Subtitle_Service)')
			message = message + newline + "DialogSubtitles" + space2 + xbmc.getInfoLabel('Window(home).Property(DialogSubtitles)')
			message = message + newline + "DialogSubtitles2" + space2 + xbmc.getInfoLabel('Window(home).Property(DialogSubtitles2)')
			for i in range(1,11):
				message = message + newline + 'DialogSubtitlesNA'+str(i) + space2 + xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA'+str(i)+')')
		else:
			message = message + newline + "Current XML" + space2 + xbmc.getInfoLabel('Window.Property(xmlfile)')
			message = message + newline + "TEMP" + space2 + property_temp
			message = message + newline + "TEMP2" + space2 + property_temp2
			message = message + newline + "scriptfeatherenceservice_random" + space2 + scriptfeatherenceservice_random
			message = message + newline + "scriptfeatherenceservice_random1" + space2 + scriptfeatherenceservice_random1
			message = message + newline + "scriptfeatherenceservice_random2" + space2 + scriptfeatherenceservice_random2
			message = message + newline + "scriptfeatherenceservice_random3" + space2 + scriptfeatherenceservice_random3
			message = message + newline + "scriptfeatherenceservice_random4" + space2 + scriptfeatherenceservice_random4
			message = message + newline + "scriptfeatherenceservice_random5" + space2 + scriptfeatherenceservice_random5
			message = message + newline + "scriptfeatherenceservice_randomL" + space2 + str(scriptfeatherenceservice_randomL)
			message = message + newline + '---------------------------'
			message = message + newline + "Button.ID" + space2 + property_buttonid
			message = message + newline + "Button.ID_" + space2 + property_buttonid_
			message = message + newline + "Button.Name" + space2 + property_buttonname
			message = message + newline + '---------------------------'
			message = message + newline + "SubButton.ID_" + space2 + property_subbuttonid_
			message = message + newline + "SubButton.Name" + space2 + property_subbuttonname
			message = message + newline + '---------------------------'
			message = message + newline + "Previous_SubButton.ID_" + space2 + property_previoussubbuttonid_
			message = message + newline + "Next_SubButton.ID_" + space2 + property_nextsubbuttonid_
			message = message + newline + '---------------------------'
			message = message + newline + "ReloadSkin" + space2 + property_reloadskin
			message = message + newline + '---------------------------'
			message = message + newline + "1000progress" + space2 + property_1000progress
			message = message + newline + "1000title" + space2 + property_1000title
			message = message + newline + "1000comment" + space2 + property_1000comment
			message = message + newline + '---------------------------'
			message = message + newline + "property_mode10" + space2 + property_mode10
			message = message + newline + "ViewsSettings" + space2 + xbmc.getInfoLabel('Window(home).Property(ViewsSettings)')
			message = message + newline + '---------------------------'
			message = message + newline + "ListItemYear" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemYear)')
			message = message + newline + "ListItemGenre" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemGenre)')
			message = message + newline + "ListItemRating" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemRating)')
			message = message + newline + "ListItemUnWatchedEpisodes" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemUnWatchedEpisodes)')
			message = message + newline + "ListItemTVShowTitle" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemTVShowTitle)')
			message = message + newline + "ListItemDuration" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemDuration)')
			message = message + newline + "ListItemPoster" + space2 + xbmc.getInfoLabel('Window(home).Property(ListItemPoster)')
			message = message + newline + '---------------------------'
			for i in range(1,9):
				message = message + newline + "TopVideoInformation" + str(i) + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation'+str(i)+')')
			message = message + newline + '---------------------------'
			message = message + newline + "tips" + space2 + xbmc.getInfoLabel('Window(home).Property(tips)')
			message = message + newline + "ListItem.Path" + space2 + xbmc.getInfoLabel('ListItem.Path')
			message = message + newline + "Container.FolderPath" + space2 + xbmc.getInfoLabel('Container.FolderPath')
			message = message + newline + "Container.FolderName" + space2 + xbmc.getInfoLabel('Container.FolderName')
			message = message + newline + "ListItem.Overlay" + space2 + xbmc.getInfoLabel('ListItem.Overlay')
			message = message + newline + "VAR-11156label" + space2 + xbmc.getInfoLabel('$VAR[11156label]')
			message = message + newline + "ListItem.Duration" + space2 + xbmc.getInfoLabel('ListItem.Duration')
			message = message + newline + "Container.Viewmode" + space2 + xbmc.getInfoLabel('Container.Viewmode')
			message = message + newline + '---------------------------'
			message = message + newline + "custom" + space2 + xbmc.getInfoLabel('ListItem.Art(Poster)') #CUSTOM TEST
			message = message + newline + "custom2" + space2 + xbmc.getInfoLabel('ListItem.IsCollection') #CUSTOM TEST
			message = message + newline + "custom3" + space2 + str(xbmc.getInfoLabel('System.InternetState')) #CUSTOM TEST
			
			

		header = name
		diaogtextviewer(header,message)
							
def mode220(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode220(admin, name, printpoint)
	'''---------------------------'''
	
def mode221(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode221(admin, name, printpoint)
	'''---------------------------'''

def mode222(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode222(admin, name, printpoint)
	'''---------------------------'''

def mode223(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode223(admin, name, printpoint)
	'''---------------------------'''

def mode224(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode224(admin, name, printpoint)
	'''---------------------------'''

def mode225(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode225(admin, name, printpoint)
	'''---------------------------'''

def mode226(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode226(admin, name, printpoint)
	'''---------------------------'''

def mode227(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode227(admin, name, printpoint)
	'''---------------------------'''

def mode228(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode228(admin, name, printpoint)
	'''---------------------------'''

def mode229(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode229(admin, name, printpoint)
	'''---------------------------'''
	
def mode231(value, admin, name, printpoint):
	'''------------------------------
	---INSTALL-ADDON-----------------
	------------------------------'''
	notification_common("24")
	addon = value
	installaddon(admin, addon, update=True)
	'''---------------------------'''

def mode232(value, admin, name, printpoint):
	'''------------------------------
	---ACTION-BUTTON-----------------
	------------------------------'''
	id1 = "" ; id2 = "" ; extra = "" ; TypeError = ""
	if printpoint != "": printpoint = printpoint + "_"

	addon1 = installaddonP(admin, 'script.skinshortcuts', update=True)
	addon2 = installaddonP(admin, 'script.module.unidecode', update=True)
	
	if '9' in addon1 or '9' in addon2:
		notification_common("24") ; xbmc.sleep(3000)
		if '9' in addon1: notification('script.skinshortcuts','','',2000)
		elif '9' in addon2: notification('script.module.unidecode','','',2000)
	else:
		printpoint = printpoint + "0"
		try:
			if value != "":
				if '_' in value: pass
				else: test = int(value) + 1
				id1 = value
			elif custom1175W and not custom1138W:
				if property_buttonid_ == "": printpoint = printpoint + "9B"
				else: test = int(property_buttonid) + 1 ; id1 = property_buttonid_
			elif custom1138W:
				if property_subbuttonid_ == "" or (not property_buttonid in property_subbuttonid_): printpoint = printpoint + "9C"
				else: id1 = property_subbuttonid_
		except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "9D"
		
		if id1 != "":			
			if custom1175W and not custom1138W:
				'''Main Action'''
				printpoint = printpoint + "x1"
				xbmc.executebuiltin('RunScript(script.skinshortcuts,type=shortcuts&custom=False&showNone=True&skinLabel=label'+id1+'&skinAction=action'+id1+'&skinList=[skinList]&skinType=[skinType]&skinThumbnail=icon'+id1+')')
			elif custom1138W:	
				'''Sub Action'''
				printpoint = printpoint + "x2"
				xbmc.executebuiltin('RunScript(script.skinshortcuts,type=shortcuts&custom=True&showNone=True&skinLabel=label'+id1+'&skinAction=action'+id1+'&skinList=[skinList]&skinType=[skinType]&skinThumbnail=icon'+id1+')')
				'''---------------------------'''
			else: printpoint = printpoint + "8"	
			
			if "x" in printpoint:
				'''wait'''
				xbmc.sleep(4000)
				dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
				while dialogselectW and not xbmc.abortRequested:
					xbmc.sleep(1000)
					dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
					'''---------------------------'''
				xbmc.sleep(500) ; xlabel = xbmc.getInfoLabel('Skin.String(label'+id1+')')
				if xlabel == "":
					setSkinSetting('0','label'+id1,'...')
					if 'x1' in printpoint and not '_' in id1: setSkinSetting('0','label'+id1+'_90','...')
				else:
					if 'x1' in printpoint and not '_' in id1: setSkinSetting('0','label'+id1+'_90',str(xlabel))
					
	text = "value" + space2 + str(value) + space + "property_buttonid" + space2 + str(property_buttonid) + newline + \
	"id1" + space2 + str(id1) + space + "id2" + space2 + str(id2) + newline + \
	extra
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
			
def mode233(value, admin, name, printpoint):
	printpoint = ""
	x = "" ; y = property_buttonid_ ; path = "" ; x2_ = ""
	if '0' in value:
		y = property_subbuttonid_
		value = value.replace('0',"",1)
	
	if '1' in value:
		'''Add-Fanart'''
		name = localize(20441)
		x = 'background'
		y = property_buttonid
		nolabel=localize(20438)
		yeslabel=localize(20441)
	
	elif '2' in value:
		'''Add-Thumb'''
		name = localize(20017)
		x = 'icon'
		nolabel=localize(20017)
		yeslabel=localize(20015)
	
	if x != "":
		printpoint = printpoint + '1'
		returned = dialogyesno(str(name), addonString_servicefeatherence(31).encode('utf-8'), nolabel=nolabel, yeslabel=yeslabel)
		if returned == 'ok':
			printpoint = printpoint + '2'
			returned2, value2 = getRandom(0, min=0, max=100, percent=40)
			if returned2 == 'ok': notification('O_o???','Copy & Paste an image URL','',4000)
			'''remote'''
			url = dialogkeyboard("", yeslabel, 0, "1", "", "")
			if url != "skip":
				from shared_modules3 import urlcheck
				returned2 = urlcheck(url, ping=False)
				if returned2 != "ok":
					notification("URL Error", "Try again..", "", 2000)
					header = "URL Error"
					message = "Examine your URL for errors:" + newline + '[B]' + str(url) + '[/B]'
					diaogtextviewer(header,message)
				else:
					setSkinSetting('0',x+y,str(url))
		else:
			printpoint = printpoint + '3'
			'''local'''
			if '1' in value:
				printpoint = printpoint + '4'
				custombackgroundspath = xbmc.getInfoLabel('Skin.String(CustomBackgroundsPath)')
				x_ = xbmc.getInfoLabel('Skin.String(background'+y+')')
				x2, x2_ = TranslatePath(x_, filename=False)
				
				if os.path.exists(x2): path = x2
				elif os.path.exists(custombackgroundspath): path = custombackgroundspath
				else: path = featherenceserviceicons_path
				xbmc.executebuiltin('Skin.SetImage(background'+y+',,'+path+')')
				
			elif '2' in value:
				printpoint = printpoint + '5'
				customiconspath = xbmc.getInfoLabel('Skin.String(CustomIconsPath)')
				x_ = xbmc.getInfoLabel('Skin.String(icon'+y+')')
				x2, x2_ = TranslatePath(x_, filename=False)
				
				if os.path.exists(x2): path = x2
				elif os.path.exists(customiconspath): path = customiconspath
				else: path = featherenceserviceicons_path
				xbmc.executebuiltin('Skin.SetImage(icon'+y+',,'+path+')')
				
			else: printpoint = printpoint + '9'
			
	text = 'value' + space2 + str(value) + space + 'path' + space2 + str(path) + newline + \
	'name' + space2 + str(name) + newline + \
	'x2_' + space2 + str(x2_)
	printlog(title='mode233', printpoint=printpoint, text=text, level=0, option="")

def mode235(value, admin, name, printpoint):
	'''------------------------------
	---Default-Icon/Background-------
	------------------------------'''
	if property_temp == 'background':
		printpoint = printpoint + '1'
		if property_buttonid != "":
			setSkinSetting('0',property_temp+str(property_buttonid),"")
			printpoint = printpoint + '2'
			'''---------------------------'''
	elif property_temp == 'icon':
		printpoint = printpoint + '3'
		if property_subbuttonid_ != "":
			printpoint = printpoint + '4'
			setSkinSetting('0',property_temp+str(property_buttonid_)+'_'+str(property_subbuttonid_),"")
			mode215(property_subbuttonid_, admin, '', '')
		elif property_buttonid_ != "":
			printpoint = printpoint + '5'
			setSkinSetting('0',property_temp+str(property_buttonid_),"")
			mode215(property_buttonid_, admin, '', '')
	
	else: printpoint = printpoint + '6'
	
	xbmc.executebuiltin('Dialog.Close(filebrowser)')
	
	text = 'property_temp' + space2 + str(property_temp) + space + 'property_buttonid' + space2 + str(property_buttonid)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def mode236(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode236(admin, name, printpoint)
	'''---------------------------'''

def mode237(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode237(admin, name, printpoint)
	'''---------------------------'''

def mode238(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode238(admin, name, printpoint)
	'''---------------------------'''

def mode239(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode239(admin, name, printpoint)
	'''---------------------------'''

def mode240(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode240(admin, name, printpoint)
	'''---------------------------'''
	
def mode241(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode241(admin, name, printpoint)
	'''---------------------------'''

def mode242(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode242(admin, name, printpoint)
	'''---------------------------'''

def mode243(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode243(admin, name, printpoint)
	'''---------------------------'''

def mode244(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode244(admin, name, printpoint)
	'''---------------------------'''

def mode245(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode245(admin, name, printpoint)
	'''---------------------------'''

def mode246(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode246(admin, name, printpoint)
	'''---------------------------'''

def mode247(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode247(admin, name, printpoint)
	'''---------------------------'''

def mode248(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode248(admin, name, printpoint)
	'''---------------------------'''

def mode249(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode249(admin, name, printpoint)
	'''---------------------------'''

def mode250(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode250(admin, name, printpoint)
	'''---------------------------'''

def mode251(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode251(admin, name, printpoint)
	'''---------------------------'''

def mode252(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode252(admin, name, printpoint)
	'''---------------------------'''

def mode253(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode253(admin, name, printpoint)
	'''---------------------------'''

def mode254(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode254(admin, name, printpoint)
	'''---------------------------'''

def mode255(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode255(admin, name, printpoint)
	'''---------------------------'''

def mode256(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode256(admin, name, printpoint)
	'''---------------------------'''

def mode257(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode257(admin, name, printpoint)
	'''---------------------------'''

def mode258(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode258(admin, name, printpoint)
	'''---------------------------'''

def mode259(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode259(admin, name, printpoint)
	'''---------------------------'''

def mode260(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode260(admin, name, printpoint)
	'''---------------------------'''

def mode261(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode261(admin, name, printpoint)
	'''---------------------------'''

def mode262(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode262(admin, name, printpoint)
	'''---------------------------'''

def mode263(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode263(admin, name, printpoint)
	'''---------------------------'''

def mode264(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode264(admin, name, printpoint)
	'''---------------------------'''

def mode265(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode265(admin, name, printpoint)
	'''---------------------------'''

def mode266(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode266(admin, name, printpoint)
	'''---------------------------'''

def mode267(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode267(admin, name, printpoint)
	'''---------------------------'''

def mode268(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode268(admin, name, printpoint)
	'''---------------------------'''

def mode269(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode269(admin, name, printpoint)
	'''---------------------------'''

def mode270(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode270(admin, name, printpoint)
	'''---------------------------'''

def mode271(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode271(admin, name, printpoint)
	'''---------------------------'''

def mode272(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode272(admin, name, printpoint)
	'''---------------------------'''

def mode273(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode273(admin, name, printpoint)
	'''---------------------------'''

def mode274(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode274(admin, name, printpoint)
	'''---------------------------'''

def mode275(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode275(admin, name, printpoint)
	'''---------------------------'''

def mode276(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode276(admin, name, printpoint)
	'''---------------------------'''

def mode277(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode277(admin, name, printpoint)
	'''---------------------------'''

def mode278(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode278(admin, name, printpoint)
	'''---------------------------'''

def mode279(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode279(admin, name, printpoint)
	'''---------------------------'''
	
def mode280(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode280(admin, name, printpoint)
	'''---------------------------'''

def mode281(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode281(admin, name, printpoint)
	'''---------------------------'''

def mode282(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode282(admin, name, printpoint)
	'''---------------------------'''

def mode283(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode283(admin, name, printpoint)
	'''---------------------------'''

def mode284(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode284(admin, name, printpoint)
	'''---------------------------'''

def mode285(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode285(admin, name, printpoint)
	'''---------------------------'''

def mode286(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode286(admin, name, printpoint)
	'''---------------------------'''

def mode287(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode287(admin, name, printpoint)
	'''---------------------------'''

def mode288(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode288(admin, name, printpoint)
	'''---------------------------'''

def mode289(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode289(admin, name, printpoint)
	'''---------------------------'''
	
def mode290(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode290(admin, name, printpoint)
	'''---------------------------'''

def mode291(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode291(admin, name, printpoint)
	'''---------------------------'''

def mode292(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode292(admin, name, printpoint)
	'''---------------------------'''

def mode293(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode293(admin, name, printpoint)
	'''---------------------------'''

def mode294(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode294(admin, name, printpoint)
	'''---------------------------'''

def mode295(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode295(admin, name, printpoint)
	'''---------------------------'''

def mode296(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode296(admin, name, printpoint)
	'''---------------------------'''

def mode297(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode297(admin, name, printpoint)
	'''---------------------------'''

def mode298(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode298(admin, name, printpoint)
	'''---------------------------'''

def mode299(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode299(admin, name, printpoint)
	'''---------------------------'''

def mode300(admin, name, printpoint):
	'''------------------------------
	---SEARCH-SDAROT-TV--------------
	------------------------------'''
	xbmc.executebuiltin('Control.SetFocus(50)')
	url = 'plugin://plugin.video.sdarot.tv/?mode=6&name=%5bCOLOR%20red%5d%20%d7%97%d7%a4%d7%a9%20%20%5b%2fCOLOR%5d&url=http%3a%2f%2fwww.sdarot.wf%2fsearch'
	ActivateWindow("1", 'plugin.video.sdarot.tv', url, 'return0', wait=False)
	'''---------------------------'''

def mode305(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode305(admin, name, printpoint)
	'''---------------------------'''

def mode306(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode306(admin, name, printpoint)
	'''---------------------------'''

def mode307(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode307(admin, name, printpoint)
	'''---------------------------'''

def mode308(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode308(admin, name, printpoint)
	'''---------------------------'''

def mode309(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode309(admin, name, printpoint)
	'''---------------------------'''

def mode310(admin, name, printpoint):
	pass

def mode313(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	pass
	'''---------------------------'''

def mode314(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode314(admin, name, printpoint)
	'''---------------------------'''

def mode315(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode315(admin, name, printpoint)
	'''---------------------------'''

def mode316(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode316(admin, name, printpoint)
	'''---------------------------'''

def mode317(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode317(admin, name, printpoint)
	'''---------------------------'''

def mode318(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode318(admin, name, printpoint)
	'''---------------------------'''

def mode319(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode319(admin, name, printpoint)
	'''---------------------------'''

def mode320(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode320(admin, name, printpoint)
	'''---------------------------'''
	
def mode321(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode321(admin, name, printpoint)
	'''---------------------------'''

def mode322(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode322(admin, name, printpoint)
	'''---------------------------'''

def mode323(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode323(admin, name, printpoint)
	'''---------------------------'''

def mode324(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode324(admin, name, printpoint)
	'''---------------------------'''

def mode325(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode325(admin, name, printpoint)
	'''---------------------------'''

def mode326(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode326(admin, name, printpoint)
	'''---------------------------'''

def mode327(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode327(admin, name, printpoint)
	'''---------------------------'''

def mode328(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode328(admin, name, printpoint)
	'''---------------------------'''

def mode329(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode329(admin, name, printpoint)
	'''---------------------------'''

def mode330(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode330(admin, name, printpoint)
	'''---------------------------'''
	
def mode331(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode331(admin, name, printpoint)
	'''---------------------------'''

def mode332(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode332(admin, name, printpoint)
	'''---------------------------'''

def mode333(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode333(admin, name, printpoint)
	'''---------------------------'''

def mode334(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode334(admin, name, printpoint)
	'''---------------------------'''

def mode335(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode335(admin, name, printpoint)
	'''---------------------------'''

def mode336(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode336(admin, name, printpoint)
	'''---------------------------'''

def mode337(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode337(admin, name, printpoint)
	'''---------------------------'''

def mode338(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode338(admin, name, printpoint)
	'''---------------------------'''

def mode339(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode339(admin, name, printpoint)
	'''---------------------------'''

def mode340(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode340(admin, name, printpoint)
	'''---------------------------'''
	
def mode341(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode341(admin, name, printpoint)
	'''---------------------------'''

def mode342(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode342(admin, name, printpoint)
	'''---------------------------'''

def mode343(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode343(admin, name, printpoint)
	'''---------------------------'''

def mode344(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode344(admin, name, printpoint)
	'''---------------------------'''

def mode345(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode345(admin, name, printpoint)
	'''---------------------------'''

def mode346(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode346(admin, name, printpoint)
	'''---------------------------'''

def mode347(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode347(admin, name, printpoint)
	'''---------------------------'''

def mode348(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode348(admin, name, printpoint)
	'''---------------------------'''

def mode349(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode349(admin, name, printpoint)
	'''---------------------------'''
	
def mode352(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode352(admin, name, printpoint)
	'''---------------------------'''

def mode353(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode353(admin, name, printpoint)
	'''---------------------------'''

def mode354(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode354(admin, name, printpoint)
	'''---------------------------'''

def mode355(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode355(admin, name, printpoint)
	'''---------------------------'''

def mode356(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode356(admin, name, printpoint)
	'''---------------------------'''

def mode357(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode357(admin, name, printpoint)
	'''---------------------------'''

def mode358(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode358(admin, name, printpoint)
	'''---------------------------'''

def mode359(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode359(admin, name, printpoint)
	'''---------------------------'''

def mode360(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode360(admin, name, printpoint)
	'''---------------------------'''

def mode361(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode361(admin, name, printpoint)
	'''---------------------------'''

def mode362(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode362(admin, name, printpoint)
	'''---------------------------'''

def mode363(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode363(admin, name, printpoint)
	'''---------------------------'''

def mode364(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode364(admin, name, printpoint)
	'''---------------------------'''

def mode365(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode365(admin, name, printpoint)
	'''---------------------------'''

def mode366(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode366(admin, name, printpoint)
	'''---------------------------'''

def mode367(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode367(admin, name, printpoint)
	'''---------------------------'''

def mode368(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode368(admin, name, printpoint)
	'''---------------------------'''

def mode369(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode369(admin, name, printpoint)
	'''---------------------------'''

def mode370(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode370(admin, name, printpoint)
	'''---------------------------'''

def mode371(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode371(admin, name, printpoint)
	'''---------------------------'''

def mode372(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode372(admin, name, printpoint)
	'''---------------------------'''

def mode373(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode373(admin, name, printpoint)
	'''---------------------------'''

def mode374(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode374(admin, name, printpoint)
	'''---------------------------'''

def mode375(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode375(admin, name, printpoint)
	'''---------------------------'''

def mode376(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode376(admin, name, printpoint)
	'''---------------------------'''

def mode377(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode377(admin, name, printpoint)
	'''---------------------------'''

def mode378(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode378(admin, name, printpoint)
	'''---------------------------'''

def mode379(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode379(admin, name, printpoint)
	'''---------------------------'''
	
def mode380(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode380(admin, name, printpoint)
	'''---------------------------'''

def mode381(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode381(admin, name, printpoint)
	'''---------------------------'''

def mode382(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode382(admin, name, printpoint)
	'''---------------------------'''

def mode383(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode383(admin, name, printpoint)
	'''---------------------------'''

def mode384(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode384(admin, name, printpoint)
	'''---------------------------'''

def mode385(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode385(admin, name, printpoint)
	'''---------------------------'''

def mode386(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode386(admin, name, printpoint)
	'''---------------------------'''

def mode387(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode387(admin, name, printpoint)
	'''---------------------------'''

def mode388(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode388(admin, name, printpoint)
	'''---------------------------'''

def mode389(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode389(admin, name, printpoint)
	'''---------------------------'''
	
def mode390(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode390(admin, name, printpoint)
	'''---------------------------'''

def mode391(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode391(admin, name, printpoint)
	'''---------------------------'''

def mode392(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode392(admin, name, printpoint)
	'''---------------------------'''

def mode393(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode393(admin, name, printpoint)
	'''---------------------------'''

def mode394(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode394(admin, name, printpoint)
	'''---------------------------'''

def mode395(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode395(admin, name, printpoint)
	'''---------------------------'''

def mode396(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode396(admin, name, printpoint)
	'''---------------------------'''

def mode397(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode397(admin, name, printpoint)
	'''---------------------------'''

def mode398(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode398(admin, name, printpoint)
	'''---------------------------'''

def mode399(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode399(admin, name, printpoint)
	'''---------------------------'''

def mode400(admin, name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode400(admin, name, printpoint)
	'''---------------------------'''

def mode401(admin,name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode401(admin, name, printpoint)
	'''---------------------------'''

def mode402(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode402(admin, name, printpoint)
	'''---------------------------'''
	
def mode403(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode403(admin, name, printpoint)
	'''---------------------------'''

def mode404(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode404(admin, name, printpoint)
	'''---------------------------'''

def mode405(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode405(admin, name, printpoint)
	'''---------------------------'''

def mode406(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode406(admin, name, printpoint)
	'''---------------------------'''

def mode407(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode407(admin, name, printpoint)
	'''---------------------------'''

def mode408(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode408(admin, name, printpoint)
	'''---------------------------'''

def mode409(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode409(admin, name, printpoint)
	'''---------------------------'''

def mode410(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode440(admin, name, printpoint)
	'''---------------------------'''
	
def mode411(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode411(admin, name, printpoint)
	'''---------------------------'''

def mode412(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode412(admin, name, printpoint)
	'''---------------------------'''

def mode413(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode413(admin, name, printpoint)
	'''---------------------------'''

def mode414(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode414(admin, name, printpoint)
	'''---------------------------'''

def mode415(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode415(admin, name, printpoint)
	'''---------------------------'''

def mode416(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode416(admin, name, printpoint)
	'''---------------------------'''

def mode417(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode417(admin, name, printpoint)
	'''---------------------------'''

def mode418(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode418(admin, name, printpoint)
	'''---------------------------'''

def mode419(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode419(admin, name, printpoint)
	'''---------------------------'''

def mode420(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode420(admin, name, printpoint)
	'''---------------------------'''
	
def mode421(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode421(admin, name, printpoint)
	'''---------------------------'''

def mode422(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode422(admin, name, printpoint)
	'''---------------------------'''

def mode423(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode423(admin, name, printpoint)
	'''---------------------------'''

def mode424(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode424(admin, name, printpoint)
	'''---------------------------'''

def mode425(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode425(admin, name, printpoint)
	'''---------------------------'''

def mode426(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode426(admin, name, printpoint)
	'''---------------------------'''

def mode427(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode427(admin, name, printpoint)
	'''---------------------------'''

def mode428(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode428(admin, name, printpoint)
	'''---------------------------'''

def mode429(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode429(admin, name, printpoint)
	'''---------------------------'''

def mode430(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode430(admin, name, printpoint)
	'''---------------------------'''
	
def mode431(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode431(admin, name, printpoint)
	'''---------------------------'''

def mode432(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode432(admin, name, printpoint)
	'''---------------------------'''

def mode433(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode433(admin, name, printpoint)
	'''---------------------------'''

def mode434(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode434(admin, name, printpoint)
	'''---------------------------'''

def mode435(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode435(admin, name, printpoint)
	'''---------------------------'''

def mode436(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode436(admin, name, printpoint)
	'''---------------------------'''

def mode437(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode437(admin, name, printpoint)
	'''---------------------------'''

def mode438(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode438(admin, name, printpoint)
	'''---------------------------'''

def mode439(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode439(admin, name, printpoint)
	'''---------------------------'''

def mode440(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode440(admin, name, printpoint)
	'''---------------------------'''
	
def mode441(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode441(admin, name, printpoint)
	'''---------------------------'''

def mode442(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode442(admin, name, printpoint)
	'''---------------------------'''

def mode443(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode443(admin, name, printpoint)
	'''---------------------------'''

def mode444(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode444(admin, name, printpoint)
	'''---------------------------'''

def mode445(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode445(admin, name, printpoint)
	'''---------------------------'''

def mode446(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode446(admin, name, printpoint)
	'''---------------------------'''

def mode447(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode447(admin, name, printpoint)
	'''---------------------------'''

def mode448(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode448(admin, name, printpoint)
	'''---------------------------'''

def mode449(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode449(admin, name, printpoint)
	'''---------------------------'''

def mode450(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode450(admin, name, printpoint)
	'''---------------------------'''

def mode451(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode451(admin, name, printpoint)
	'''---------------------------'''

def mode452(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode452(admin, name, printpoint)
	'''---------------------------'''

def mode453(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode453(admin, name, printpoint)
	'''---------------------------'''

def mode454(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode454(admin, name, printpoint)
	'''---------------------------'''

def mode455(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode455(admin, name, printpoint)
	'''---------------------------'''

def mode456(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode456(admin, name, printpoint)
	'''---------------------------'''

def mode457(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode457(admin, name, printpoint)
	'''---------------------------'''

def mode458(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode458(admin, name, printpoint)
	'''---------------------------'''

def mode459(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode459(admin, name, printpoint)
	'''---------------------------'''

def mode460(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode460(admin, name, printpoint)
	'''---------------------------'''

def mode461(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode461(admin, name, printpoint)
	'''---------------------------'''

def mode462(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode462(admin, name, printpoint)
	'''---------------------------'''

def mode463(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode463(admin, name, printpoint)
	'''---------------------------'''

def mode464(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode464(admin, name, printpoint)
	'''---------------------------'''

def mode465(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode465(admin, name, printpoint)
	'''---------------------------'''

def mode466(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode466(admin, name, printpoint)
	'''---------------------------'''

def mode467(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode467(admin, name, printpoint)
	'''---------------------------'''

def mode468(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode468(admin, name, printpoint)
	'''---------------------------'''

def mode469(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode469(admin, name, printpoint)
	'''---------------------------'''

def mode470(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode470(admin, name, printpoint)
	'''---------------------------'''

def mode471(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode471(admin, name, printpoint)
	'''---------------------------'''

def mode472(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode472(admin, name, printpoint)
	'''---------------------------'''

def mode473(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode473(admin, name, printpoint)
	'''---------------------------'''

def mode474(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode474(admin, name, printpoint)
	'''---------------------------'''

def mode475(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode475(admin, name, printpoint)
	'''---------------------------'''

def mode476(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode476(admin, name, printpoint)
	'''---------------------------'''

def mode477(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode477(admin, name, printpoint)
	'''---------------------------'''

def mode478(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode478(admin, name, printpoint)
	'''---------------------------'''

def mode479(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode479(admin, name, printpoint)
	'''---------------------------'''
	
def mode480(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode480(admin, name, printpoint)
	'''---------------------------'''

def mode481(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode481(admin, name, printpoint)
	'''---------------------------'''

def mode482(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode482(admin, name, printpoint)
	'''---------------------------'''

def mode483(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode483(admin, name, printpoint)
	'''---------------------------'''

def mode484(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode484(admin, name, printpoint)
	'''---------------------------'''

def mode485(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode485(admin, name, printpoint)
	'''---------------------------'''

def mode486(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode486(admin, name, printpoint)
	'''---------------------------'''

def mode487(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode487(admin, name, printpoint)
	'''---------------------------'''

def mode488(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode488(admin, name, printpoint)
	'''---------------------------'''

def mode489(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode489(admin, name, printpoint)
	'''---------------------------'''
	
def mode490(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode490(admin, name, printpoint)
	'''---------------------------'''

def mode491(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode491(admin, name, printpoint)
	'''---------------------------'''

def mode492(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode492(admin, name, printpoint)
	'''---------------------------'''

def mode493(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode493(admin, name, printpoint)
	'''---------------------------'''

def mode494(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode494(admin, name, printpoint)
	'''---------------------------'''

def mode495(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode495(admin, name, printpoint)
	'''---------------------------'''

def mode496(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode496(admin, name, printpoint)
	'''---------------------------'''

def mode497(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode497(admin, name, printpoint)
	'''---------------------------'''

def mode498(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode498(admin, name, printpoint)
	'''---------------------------'''

def mode499(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	pass
	'''---------------------------'''

def mode500(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	pass
	'''---------------------------'''
			
def mode510(value, admin, name, printpoint):
	'''------------------------------
	---GAMES-BUTTON------------------
	------------------------------'''
	if value == '0':
		name2 = localize(15016)

		#returned = supportcheck(name2, [], 70, platform="13456")
		returned = 'ok'
		if returned == "ok":
			addon = 'plugin.program.advanced.launcher'
			if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
				printpoint = printpoint + "7"
				'''---------------------------'''
			else:
				installaddonP(admin, addon)
				'''---------------------------'''
			
			addon = 'script.featherence.emu'
			if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
				printpoint = printpoint + "7"
				'''---------------------------'''
			else:
				installaddon(admin, addon, update=True)
				'''---------------------------'''
			
			if "77" in printpoint:
				if not os.path.exists(os.path.join(addons_path,'emulator.retroarch')) and admin3 != 'true':
					file = "emu_featherence.zip"
					fileID = getfileID(file)
					DownloadFile("https://www.dropbox.com/s/"+fileID+"/emu_featherence.zip?dl=1", file, temp_path, addons_path)
					if os.path.exists(os.path.join(addons_path,'emulator.retroarch')): dialogok("Reboot required", "In order to start playing games, you should reboot your device", "", "")
				else: xbmc.executebuiltin('RunScript(script.featherence.emu,,?mode=7)')
				'''---------------------------'''
	elif value == '1':
		'''------------------------------
		---GAMER-TV----------------------
		------------------------------'''
		addon = 'plugin.video.g4tv'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			xbmc.executebuiltin('RunAddon('+ addon +')')
			'''---------------------------'''
		else: installaddon(admin, addon, update=True)
		
def mode511(admin, name, printpoint):
	'''------------------------------
	---TRAILERS-BUTTON---------------
	------------------------------'''
	pass
	'''---------------------------'''

def mode512(value, admin, name, printpoint):
	'''------------------------------
	---INTERNET-BUTTON---------------
	------------------------------'''
	url = ""
	if value == '0': url = 'www.google.co.il'
	elif value == '1': url = 'www.facebook.com/groups/featherence'
	elif value == '2': url = 'www.github.com/finalmakerr/featherence'
	elif value == '3': url = 'www.youtube.com'
	elif value == '4': url = 'https://www.google.co.il/imghp?hl=iw&tab=wi' #Thumbnail
	elif value == '5': url = 'https://www.google.co.il/imghp?hl=iw&tab=wi' #Fanart
	
	name = localize(443)
	if systemplatformwindows: terminal('start /max '+url+'','')
	elif systemplatformandroid: terminal('adb shell am start -a android.intent.action.VIEW -d '+url+'','')
	elif systemplatformlinux:
		#returned = supportcheck(name, ["A","B"], 1, Intel=True, platform="456")
		returned = 'ok'
		if returned == "ok":
			returned = dialogyesno(addonString(32715).encode('utf-8'),addonString(32716).encode('utf-8'))
			if returned == "ok":
				addon = 'browser.chromium'
				if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
					notification(addonString(32717).encode('utf-8'), addonString(32718).encode('utf-8').encode('utf-8'), "", 4000)
					settingschange('SystemSettings','input.enablemouse','1','no',localize(14094),localize(21369))
					xbmc.sleep(1000)
					xbmc.executebuiltin('RunAddon(browser.chromium)')
					'''---------------------------'''
				else: installaddon(admin, addon, update=True)
			else:
				notification_common("8")
	else: notification_common('25')
		
def mode513(value, admin, name, printpoint):
	'''------------------------------
	---VIDEOS-BUTTON-----------------
	------------------------------'''
	if value == '0':
		name2 = str3
		path2 = "videos" 
		pictures_videos(admin, name, printpoint, 513, name2, path2)
		'''---------------------------'''

def mode514(value, admin, name, printpoint):
	'''------------------------------
	---MUSIC-BUTTON------------------
	------------------------------'''
	if value == "0":
		'''------------------------------
		---featherence-MUSIC--------------------
		------------------------------'''
		addon = 'plugin.video.featherence.music'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			xbmc.executebuiltin('RunAddon('+ addon +',,)')
			'''---------------------------'''
		else: installaddon(admin, addon, update=True)		
def mode515(value, admin, name, printpoint):
	'''------------------------------
	---KIDS-BUTTON-------------------
	------------------------------'''
	if value == "0":
		'''------------------------------
		---featherence-KIDS---------------------
		------------------------------'''
		addon = 'plugin.video.featherence.kids'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			xbmc.executebuiltin('RunAddon('+ addon +',,)')
			'''---------------------------'''
		else: installaddon(admin, addon, update=True)

def mode516(value, admin, name, printpoint):
	'''------------------------------
	---FAVOURITES-BUTTON-------------
	------------------------------'''
	if value == '0':
		xbmc.executebuiltin('ActivateWindow(134)')
		'''---------------------------'''

def mode517(value, admin, name, printpoint):
	'''------------------------------
	---LIVE-TV-BUTTON----------------
	------------------------------'''
	if '0' in value:
		extra = "" ; TypeError = ""
		containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
		if xbmc.getCondVisibility('System.GetBool(pvrmanager.enabled)'):
			printoint = printpoint + "1"
			xbmc.executebuiltin('ActivateWindow(TVChannels)')
			xbmc.sleep(1000)
			mypvrchannels = xbmc.getCondVisibility('Window.IsVisible(MyPVRChannels.xml)')
			count = 0
			while count < 10 and not mypvrchannels and not xbmc.abortRequested:
				xbmc.sleep(100)
				count += 1
				mypvrchannels = xbmc.getCondVisibility('Window.IsVisible(MyPVRChannels.xml)')
				xbmc.sleep(100)
			if mypvrchannels:
				containerfoldername = xbmc.getInfoLabel('Container.FolderName')
				containernumitems = xbmc.getInfoLabel('Container.NumItems')
				try:
					if int(containernumitems) < 2: printpoint = printpoint + "8"
					elif containerfoldername != localize(19287): pass #dialogok('[COLOR=yellow]' + '$LOCALIZE[19051]' + '[/COLOR]', localize(79548, s=[containernumitems]), localize(79549), "")
				except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)

			else: printpoint = printpoint + "9"
			if "8" in printpoint or "9" in printpoint:
				xbmc.executebuiltin('RunAddon(plugin.video.israelive)')
				dialogkaitoastW = xbmc.getCondVisibility('Window.IsVisible(DialogKaiToast.xml)')
				count = 0
				while count < 10 and not dialogkaitoastW and not xbmc.abortRequested:
					count += 1
					xbmc.sleep(200)
					dialogkaitoastW = xbmc.getCondVisibility('Window.IsVisible(DialogKaiToast.xml)')
				if count == 10:
					xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=12)')		
		else:
			printpoint = printpoint + "2"
			returned = ActivateWindow("0", 'plugin.video.israelive', 'plugin://plugin.video.israelive/', 1, wait=True)
			if not "ok" in returned:
				printpoint = printpoint + "6"
				returned = ActivateWindow("1", 'plugin.video.israelive', 'plugin://plugin.video.israelive/', 1, wait=True)
			if "ok" in returned:
				printpoint = printpoint + "7"
				pass
			containernumitems = xbmc.getInfoLabel('Container.NumItems')
			containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')

		text = "containernumitems" + space2 + str(containernumitems) + space + "containerfolderpath" + space2 + containerfolderpath + extra
		printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
		'''---------------------------'''
	elif '1' in value: mode521('0', admin, name, printpoint)
	elif '6' in value:
		'''ערוץ הטיולים'''
		addon = 'plugin.video.travel'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		xbmc.executebuiltin('RunAddon('+ addon +')')
	
def mode518(value, admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode518(admin, name, printpoint)
	'''---------------------------'''

def mode519(value, admin, name, printpoint):
	'''------------------------------
	---NATURE/SCIENCE-BUTTON---------
	------------------------------'''
	if value == '0':
		addon = 'plugin.video.featherence.docu'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			xbmc.executebuiltin('RunAddon('+ addon +',,)')
			'''---------------------------'''
		else: installaddon(admin, addon, update=True)

	elif value == '2':
		''''''
		addon = 'plugin.video.marvin'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin://plugin.video.marvin/?description&iconimage=http%3a%2f%2fthebeastkodi.uk%2faddon%2fDocs.jpg&mode=1&name=%5bCOLOR%20blue%5dDocumentaries%5b%2fCOLOR%5d&url=http%3a%2f%2fthebeastkodi.uk%2faddon%2fDocs.txt'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
	elif value == '3':
		'''נשיונל גאוגרפיק'''
		addon = 'plugin.video.seretil'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin://plugin.video.seretil/?iconimage=http%3a%2f%2fimages.nationalgeographic.com%2fwpf%2fsites%2fcommon%2fi%2fpresentation%2fNGLogo560x430-cb1343821768.png&mode=4&name=%d7%a0%d7%a9%d7%99%d7%95%d7%a0%d7%9c%20%d7%92%d7%90%d7%95%d7%92%d7%a8%d7%a4%d7%99%d7%a7&url=http%3a%2f%2fseretil.me%2fcategory%2f%25D7%25A0%25D7%25A9%25D7%2599%25D7%2595%25D7%25A0%25D7%259C-%25D7%2592%25D7%2599%25D7%2590%25D7%2595%25D7%2592%25D7%25A8%25D7%25A4%25D7%2599%25D7%25A7%2fpage1%2f)'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
	elif value == '4':
		'''היסטוריה (סרטים)'''
		addon = 'plugin.video.movixws'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin://plugin.video.movixws/?description&iconimage=http%3a%2f%2ficons.iconarchive.com%2ficons%2faaron-sinuhe%2ftv-movie-folder%2f512%2fDocumentaries-National-Geographic-icon.png&mode=2&name=Documentary%20-%20%d7%93%d7%95%d7%a7%d7%95%d7%9e%d7%a0%d7%98%d7%a8%d7%99&url=http%3a%2f%2fwww.movix.me%2fgenres%2fDocumentary'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''

	elif value == '11':
		'''הרצאות TED'''
		addon = 'plugin.video.ted.talks'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		xbmc.executebuiltin('RunAddon('+ addon +')')
		'''---------------------------'''
	
def mode521(value, admin, name, printpoint):
	'''------------------------------
	---SPORT-CHANNELS----------------
	------------------------------'''
	if value == '0':
		xbmc.executebuiltin('SetProperty(Button.ID,N/A,home)')
		xbmc.executebuiltin('SetProperty(SubButton.ID,79_91,home)')
		xbmc.executebuiltin('ActivateWindow(1138)')
		xbmc.executebuiltin('SetProperty(Button.ID,'+property_buttonid+',home)')
		'''---------------------------'''
	elif value == '1':
		'''------------------------------
		---vdubt25-----------------------
		------------------------------'''
		if connected:
			count = ""
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
			returned = ActivateWindow("1", 'plugin.video.vdubt', 'plugin://plugin.video.vdubt/', 0, wait=True)
			if "ok" in returned and 1 + 1 == 3:
				printpoint = printpoint + "1"
				systemcurrentcontrol = findin_systemcurrentcontrol("0","[..]",0,'Action(PageUp)','')
				systemcurrentcontrol = findin_systemcurrentcontrol("0","[..]",100,'Action(PageUp)','Action(Down)')
				xbmc.sleep(100)
				notification(systemcurrentcontrol, "", "" ,2000)
				systemcurrentcontrol = findin_systemcurrentcontrol("1","Live",40,'Action(Down)','Action(Select)')
				systemcurrentcontrol = findin_systemcurrentcontrol("1","Live Sports",40,'Action(Down)','Action(Select)')
				xbmc.sleep(500)
				dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
				containernumitems = xbmc.getInfoLabel('Container.NumItems')
				count = 0
				while count < 10 and (dialogbusyW or containernumitems != "0") and not xbmc.abortRequested:
					count += 1
					xbmc.sleep(200)
					dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
					containernumitems = xbmc.getInfoLabel('Container.NumItems')
					systemidle1 = xbmc.getCondVisibility('System.IdleTime(1)')
					if dialogbusyW and systemidle1: xbmc.sleep(500)
					'''---------------------------'''
				systemcurrentcontrol = findin_systemcurrentcontrol("0","[..]",100,'','Action(Down)')
				if systemcurrentcontrol == "[..]":
					container50listitem2label = xbmc.getInfoLabel('Container(50).ListItem(1).Label')
					if not "LIVE Sports 24/7" in container50listitem2label:
						'''------------------------------
						---NO-LIVE-MATCHS----------------
						------------------------------'''
						dialogok(localize(78918), localize(78916) + space2, localize(78920),"")
						'''---------------------------'''
					else:
						'''------------------------------
						---LIVE-MATCHS-FOUND!------------
						------------------------------'''
						dialogok(localize(78917), localize(78919) + '[CR]' + '[COLOR=yellow]' + "LIVE FOOTBALL" + '[/COLOR]',"","")
						'''---------------------------'''
			text = "systemcurrentcontrol" + space2 + systemcurrentcontrol + space + "count" + space2 + str(count)
			printlog(title='mode15', printpoint=printpoint, text=text, level=0, option="")
		elif not connected: notification_common("5")
		'''---------------------------'''
	
	elif value == '2':
		'''------------------------------
		---P2P-Sport---------------------
		------------------------------'''
		if connected:
			installaddonP(admin, 'repository.natko1412', update=True)
			installaddonP(admin, 'program.plexus', update=True)
			addon = 'plugin.video.p2psport'
			if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
				'''------------------------------
				---plugin.video.p2p-streams------
				------------------------------'''
				printpoint = printpoint + "1"
				countrystr = xbmc.getInfoLabel('Skin.String(Country)')
				if countrystr == "Israel": setsetting_custom1('plugin.video.p2psport','timezone_new','Israel')
				
				if systemplatformwindows:
					programplexus_path = os.path.join(addondata_path, 'program.plexus', '')
					ace_engine = os.path.join(programplexus_path, 'acestream', 'ace_engine.exe')
					ace_player = os.path.join(programplexus_path, 'player', 'ace_player.exe')
					if not os.path.exists(ace_engine) or not os.path.exists(ace_player):
						notification("downloading AceEngine...", "Please wait", "", 7000)
						file = "AceEngine.zip"
						fileID = getfileID(file)
						DownloadFile("https://www.dropbox.com/s/"+fileID+"/AceEngine.zip?dl=1", file, temp_path, programplexus_path, silent=True)
					else: printpoint = printpoint + "A"
				
				returned = ActivateWindow("0", addon, '', 0, wait=True)
				
			else:
				#if "A" in id10str or "B" in id10str:
				printpoint = printpoint + "8"
				installaddon(admin, addon, update=True)
				'''---------------------------'''
			
		else: notification_common("5")
		'''---------------------------'''
		text = ""
		printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	elif value == '3':
		'''------------------------------
		---BBTS--------------------------
		------------------------------'''
		addon = 'plugin.video.bbts'
		installaddon(admin, addon, update=True)
		url = 'plugin://plugin.video.bbts/?folder=%2fSPORTS'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		'''---------------------------'''
		
	elif value == '4':
		'''ליגה אנגלית'''
		addon = 'plugin.video.OperationRobocopUltimate'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		xbmc.executebuiltin('RunAddon('+ addon +')')
		
	elif value == '5':
		'''ליגה ספרדית'''
		addon = 'plugin.video.adryanlist'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin://plugin.video.adryanlist/?fanart=http%3a%2f%2fi.imgur.com%2fGyK9PGj.jpg&mode=1&name=%5bCOLOR%20lime%5d%e2%80%a2%5b%2fCOLOR%5d%5bCOLOR%20deepskyblue%5d%20%20%5bB%5dSports%5b%2fB%5d%20%20%20%5b%2fCOLOR%5d%5bCOLOR%20skyblue%5d%5bAcestreams%20Channels%5d%20%5b%2fCOLOR%5d&url=http%3a%2f%2fadrian.kodistream.info%2fadryan%2face.xml'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
		
	elif value == '6':
		'''NJMSoccer'''
		addon = 'repository.NJMSoccer'
		installaddonP(admin, addon, update=True)
		addon = 'plugin.video.NJMSoccer'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin.video.NJMSoccer'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
	
	elif value == '7':
		'''Phoenix'''
		addon = 'plugin.video.phstreams'
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = 'plugin://plugin.video.phstreams/?action=ndmode&audio=0&content=0&fanart=http%3a%2f%2fs20.postimg.org%2fw4r6o7t3x%2fPhoenix_Fanart.png&image=http%3a%2f%2fs20.postimg.org%2fy47sfmnfh%2fSports.png&name=Sports&playable=false&tvshow=0&url=http%3a%2f%2fshanghai.watchkodi.com%2fDirectories%2fSports.xml'
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
	
	elif value == '8':
		''''''
		addon = ''
		installaddon(admin, addon, update=True)
		'''---------------------------'''
		url = ''
		returned = ActivateWindow("1", addon, url, 0, wait=True)
		if not 'ok' in returned:
			returned = ActivateWindow("0", addon, url, 0, wait=True)
			'''---------------------------'''
		
def mode522(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode522(admin, name, printpoint)
	'''---------------------------'''

def mode523(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode523(admin, name, printpoint)
	'''---------------------------'''

def mode524(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode524(admin, name, printpoint)
	'''---------------------------'''

def mode525(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode525(admin, name, printpoint)
	'''---------------------------'''

def mode526(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode526(admin, name, printpoint)
	'''---------------------------'''

def mode527(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode527(admin, name, printpoint)
	'''---------------------------'''

def mode528(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode528(admin, name, printpoint)
	'''---------------------------'''

def mode529(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode529(admin, name, printpoint)
	'''---------------------------'''

def mode530(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode530(admin, name, printpoint)
	'''---------------------------'''
	
def mode531(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode531(admin, name, printpoint)
	'''---------------------------'''

def mode532(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode532(admin, name, printpoint)
	'''---------------------------'''

def mode533(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode533(admin, name, printpoint)
	'''---------------------------'''

def mode534(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode534(admin, name, printpoint)
	'''---------------------------'''

def mode535(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode535(admin, name, printpoint)
	'''---------------------------'''

def mode536(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode536(admin, name, printpoint)
	'''---------------------------'''

def mode537(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode537(admin, name, printpoint)
	'''---------------------------'''

def mode538(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode538(admin, name, printpoint)
	'''---------------------------'''

def mode539(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode539(admin, name, printpoint)
	'''---------------------------'''

def mode540(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode540(admin, name, printpoint)
	'''---------------------------'''
	
def mode541(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode541(admin, name, printpoint)
	'''---------------------------'''

def mode542(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode542(admin, name, printpoint)
	'''---------------------------'''

def mode543(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode543(admin, name, printpoint)
	'''---------------------------'''

def mode544(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode544(admin, name, printpoint)
	'''---------------------------'''

def mode545(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode545(admin, name, printpoint)
	'''---------------------------'''

def mode546(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode546(admin, name, printpoint)
	'''---------------------------'''

def mode547(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode547(admin, name, printpoint)
	'''---------------------------'''

def mode548(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode548(admin, name, printpoint)
	'''---------------------------'''

def mode549(value, admin, name, printpoint):
	'''------------------------------
	---MORE-BUTTON-------------------
	------------------------------'''
	pass

def mode550(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode550(admin, name, printpoint)
	'''---------------------------'''

def mode551(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode551(admin, name, printpoint)
	'''---------------------------'''

def mode552(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode552(admin, name, printpoint)
	'''---------------------------'''

def mode553(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode553(admin, name, printpoint)
	'''---------------------------'''

def mode554(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode554(admin, name, printpoint)
	'''---------------------------'''

def mode555(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode555(admin, name, printpoint)
	'''---------------------------'''

def mode556(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode556(admin, name, printpoint)
	'''---------------------------'''

def mode557(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode557(admin, name, printpoint)
	'''---------------------------'''

def mode558(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode558(admin, name, printpoint)
	'''---------------------------'''

def mode559(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode559(admin, name, printpoint)
	'''---------------------------'''

def mode560(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode560(admin, name, printpoint)
	'''---------------------------'''

def mode561(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode561(admin, name, printpoint)
	'''---------------------------'''

def mode562(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode562(admin, name, printpoint)
	'''---------------------------'''

def mode563(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode563(admin, name, printpoint)
	'''---------------------------'''

def mode564(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode564(admin, name, printpoint)
	'''---------------------------'''

def mode565(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode565(admin, name, printpoint)
	'''---------------------------'''

def mode566(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode566(admin, name, printpoint)
	'''---------------------------'''

def mode567(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode567(admin, name, printpoint)
	'''---------------------------'''

def mode568(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode568(admin, name, printpoint)
	'''---------------------------'''

def mode569(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode569(admin, name, printpoint)
	'''---------------------------'''

def mode570(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode570(admin, name, printpoint)
	'''---------------------------'''

def mode571(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode571(admin, name, printpoint)
	'''---------------------------'''

def mode572(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode572(admin, name, printpoint)
	'''---------------------------'''

def mode573(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode573(admin, name, printpoint)
	'''---------------------------'''

def mode574(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode574(admin, name, printpoint)
	'''---------------------------'''

def mode575(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode575(admin, name, printpoint)
	'''---------------------------'''

def mode576(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode576(admin, name, printpoint)
	'''---------------------------'''

def mode577(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode577(admin, name, printpoint)
	'''---------------------------'''

def mode578(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode578(admin, name, printpoint)
	'''---------------------------'''

def mode579(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode579(admin, name, printpoint)
	'''---------------------------'''
	
def mode580(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode580(admin, name, printpoint)
	'''---------------------------'''

def mode581(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode581(admin, name, printpoint)
	'''---------------------------'''

def mode582(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode582(admin, name, printpoint)
	'''---------------------------'''

def mode583(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode583(admin, name, printpoint)
	'''---------------------------'''

def mode584(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode584(admin, name, printpoint)
	'''---------------------------'''

def mode585(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode585(admin, name, printpoint)
	'''---------------------------'''

def mode586(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode586(admin, name, printpoint)
	'''---------------------------'''

def mode587(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode587(admin, name, printpoint)
	'''---------------------------'''

def mode588(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode588(admin, name, printpoint)
	'''---------------------------'''

def mode589(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode589(admin, name, printpoint)
	'''---------------------------'''
	
def mode590(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode590(admin, name, printpoint)
	'''---------------------------'''

def mode591(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode591(admin, name, printpoint)
	'''---------------------------'''

def mode592(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode592(admin, name, printpoint)
	'''---------------------------'''

def mode593(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode593(admin, name, printpoint)
	'''---------------------------'''

def mode594(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode594(admin, name, printpoint)
	'''---------------------------'''

def mode595(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode595(admin, name, printpoint)
	'''---------------------------'''

def mode596(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode596(admin, name, printpoint)
	'''---------------------------'''

def mode597(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode597(admin, name, printpoint)
	'''---------------------------'''

def mode598(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode598(admin, name, printpoint)
	'''---------------------------'''

def mode599(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode599(admin, name, printpoint)
	'''---------------------------'''

def mode600(admin, name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode600(admin, name, printpoint)
	'''---------------------------'''

def mode601(admin,name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode601(admin, name, printpoint)
	'''---------------------------'''

def mode602(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode602(admin, name, printpoint)
	'''---------------------------'''
	
def mode603(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode603(admin, name, printpoint)
	'''---------------------------'''

def mode604(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode604(admin, name, printpoint)
	'''---------------------------'''

def mode605(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode605(admin, name, printpoint)
	'''---------------------------'''

def mode606(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode606(admin, name, printpoint)
	'''---------------------------'''

def mode607(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode607(admin, name, printpoint)
	'''---------------------------'''

def mode608(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode608(admin, name, printpoint)
	'''---------------------------'''

def mode609(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode609(admin, name, printpoint)
	'''---------------------------'''

def mode610(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode640(admin, name, printpoint)
	'''---------------------------'''
	
def mode611(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode611(admin, name, printpoint)
	'''---------------------------'''

def mode612(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode612(admin, name, printpoint)
	'''---------------------------'''

def mode613(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode613(admin, name, printpoint)
	'''---------------------------'''

def mode614(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode614(admin, name, printpoint)
	'''---------------------------'''

def mode615(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode615(admin, name, printpoint)
	'''---------------------------'''

def mode616(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode616(admin, name, printpoint)
	'''---------------------------'''

def mode617(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode617(admin, name, printpoint)
	'''---------------------------'''

def mode618(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode618(admin, name, printpoint)
	'''---------------------------'''

def mode619(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode619(admin, name, printpoint)
	'''---------------------------'''

def mode620(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode620(admin, name, printpoint)
	'''---------------------------'''
	
def mode621(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode621(admin, name, printpoint)
	'''---------------------------'''

def mode622(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode622(admin, name, printpoint)
	'''---------------------------'''

def mode623(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode623(admin, name, printpoint)
	'''---------------------------'''

def mode624(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode624(admin, name, printpoint)
	'''---------------------------'''

def mode625(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode625(admin, name, printpoint)
	'''---------------------------'''

def mode626(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode626(admin, name, printpoint)
	'''---------------------------'''

def mode627(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode627(admin, name, printpoint)
	'''---------------------------'''

def mode628(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode628(admin, name, printpoint)
	'''---------------------------'''

def mode629(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode629(admin, name, printpoint)
	'''---------------------------'''

def mode630(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode630(admin, name, printpoint)
	'''---------------------------'''
	
def mode631(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode631(admin, name, printpoint)
	'''---------------------------'''

def mode632(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode632(admin, name, printpoint)
	'''---------------------------'''

def mode633(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode633(admin, name, printpoint)
	'''---------------------------'''

def mode634(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode634(admin, name, printpoint)
	'''---------------------------'''

def mode635(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode635(admin, name, printpoint)
	'''---------------------------'''

def mode636(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode636(admin, name, printpoint)
	'''---------------------------'''

def mode637(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode637(admin, name, printpoint)
	'''---------------------------'''

def mode638(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode638(admin, name, printpoint)
	'''---------------------------'''

def mode639(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode639(admin, name, printpoint)
	'''---------------------------'''

def mode640(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode640(admin, name, printpoint)
	'''---------------------------'''
	
def mode641(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode641(admin, name, printpoint)
	'''---------------------------'''

def mode642(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode642(admin, name, printpoint)
	'''---------------------------'''

def mode643(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode643(admin, name, printpoint)
	'''---------------------------'''

def mode644(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode644(admin, name, printpoint)
	'''---------------------------'''

def mode645(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode645(admin, name, printpoint)
	'''---------------------------'''

def mode646(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode646(admin, name, printpoint)
	'''---------------------------'''

def mode647(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode647(admin, name, printpoint)
	'''---------------------------'''

def mode648(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode648(admin, name, printpoint)
	'''---------------------------'''

def mode649(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode649(admin, name, printpoint)
	'''---------------------------'''

def mode650(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode650(admin, name, printpoint)
	'''---------------------------'''

def mode651(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode651(admin, name, printpoint)
	'''---------------------------'''

def mode652(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode652(admin, name, printpoint)
	'''---------------------------'''

def mode653(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode653(admin, name, printpoint)
	'''---------------------------'''

def mode654(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode654(admin, name, printpoint)
	'''---------------------------'''

def mode655(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode655(admin, name, printpoint)
	'''---------------------------'''

def mode656(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode656(admin, name, printpoint)
	'''---------------------------'''

def mode657(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode657(admin, name, printpoint)
	'''---------------------------'''

def mode658(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode658(admin, name, printpoint)
	'''---------------------------'''

def mode659(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode659(admin, name, printpoint)
	'''---------------------------'''

def mode660(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode660(admin, name, printpoint)
	'''---------------------------'''

def mode661(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode661(admin, name, printpoint)
	'''---------------------------'''

def mode662(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode662(admin, name, printpoint)
	'''---------------------------'''

def mode663(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode663(admin, name, printpoint)
	'''---------------------------'''

def mode664(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode664(admin, name, printpoint)
	'''---------------------------'''

def mode665(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode665(admin, name, printpoint)
	'''---------------------------'''

def mode666(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode666(admin, name, printpoint)
	'''---------------------------'''

def mode667(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode667(admin, name, printpoint)
	'''---------------------------'''

def mode668(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode668(admin, name, printpoint)
	'''---------------------------'''

def mode669(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode669(admin, name, printpoint)
	'''---------------------------'''

def mode670(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode670(admin, name, printpoint)
	'''---------------------------'''

def mode671(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode671(admin, name, printpoint)
	'''---------------------------'''

def mode672(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode672(admin, name, printpoint)
	'''---------------------------'''

def mode673(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode673(admin, name, printpoint)
	'''---------------------------'''

def mode674(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode674(admin, name, printpoint)
	'''---------------------------'''

def mode675(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode675(admin, name, printpoint)
	'''---------------------------'''

def mode676(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode676(admin, name, printpoint)
	'''---------------------------'''

def mode677(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode677(admin, name, printpoint)
	'''---------------------------'''

def mode678(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode678(admin, name, printpoint)
	'''---------------------------'''

def mode679(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode679(admin, name, printpoint)
	'''---------------------------'''
	
def mode680(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode680(admin, name, printpoint)
	'''---------------------------'''

def mode681(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode681(admin, name, printpoint)
	'''---------------------------'''

def mode682(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode682(admin, name, printpoint)
	'''---------------------------'''

def mode683(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode683(admin, name, printpoint)
	'''---------------------------'''

def mode684(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode684(admin, name, printpoint)
	'''---------------------------'''

def mode685(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode685(admin, name, printpoint)
	'''---------------------------'''

def mode686(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode686(admin, name, printpoint)
	'''---------------------------'''

def mode687(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode687(admin, name, printpoint)
	'''---------------------------'''

def mode688(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode688(admin, name, printpoint)
	'''---------------------------'''

def mode689(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode689(admin, name, printpoint)
	'''---------------------------'''
	
def mode690(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode690(admin, name, printpoint)
	'''---------------------------'''

def mode691(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode691(admin, name, printpoint)
	'''---------------------------'''

def mode692(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode692(admin, name, printpoint)
	'''---------------------------'''

def mode693(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode693(admin, name, printpoint)
	'''---------------------------'''

def mode694(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode694(admin, name, printpoint)
	'''---------------------------'''

def mode695(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode695(admin, name, printpoint)
	'''---------------------------'''

def mode696(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode696(admin, name, printpoint)
	'''---------------------------'''

def mode697(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode697(admin, name, printpoint)
	'''---------------------------'''

def mode698(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode698(admin, name, printpoint)
	'''---------------------------'''

def mode699(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode699(admin, name, printpoint)
	'''---------------------------'''

def mode700(admin, name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode700(admin, name, printpoint)
	'''---------------------------'''

def mode701(admin,name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode701(admin, name, printpoint)
	'''---------------------------'''

def mode702(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode702(admin, name, printpoint)
	'''---------------------------'''
	
def mode703(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode703(admin, name, printpoint)
	'''---------------------------'''

def mode704(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode704(admin, name, printpoint)
	'''---------------------------'''

def mode705(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode705(admin, name, printpoint)
	'''---------------------------'''

def mode706(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode706(admin, name, printpoint)
	'''---------------------------'''

def mode707(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode707(admin, name, printpoint)
	'''---------------------------'''

def mode708(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode708(admin, name, printpoint)
	'''---------------------------'''

def mode709(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode709(admin, name, printpoint)
	'''---------------------------'''

def mode710(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode740(admin, name, printpoint)
	'''---------------------------'''
	
def mode711(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode711(admin, name, printpoint)
	'''---------------------------'''

def mode712(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode712(admin, name, printpoint)
	'''---------------------------'''

def mode713(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode713(admin, name, printpoint)
	'''---------------------------'''

def mode714(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode714(admin, name, printpoint)
	'''---------------------------'''

def mode715(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode715(admin, name, printpoint)
	'''---------------------------'''

def mode716(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode716(admin, name, printpoint)
	'''---------------------------'''

def mode717(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode717(admin, name, printpoint)
	'''---------------------------'''

def mode718(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode718(admin, name, printpoint)
	'''---------------------------'''

def mode719(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode719(admin, name, printpoint)
	'''---------------------------'''

def mode720(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode720(admin, name, printpoint)
	'''---------------------------'''
	
def mode721(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode721(admin, name, printpoint)
	'''---------------------------'''

def mode722(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode722(admin, name, printpoint)
	'''---------------------------'''

def mode723(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode723(admin, name, printpoint)
	'''---------------------------'''

def mode724(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode724(admin, name, printpoint)
	'''---------------------------'''

def mode725(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode725(admin, name, printpoint)
	'''---------------------------'''

def mode726(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode726(admin, name, printpoint)
	'''---------------------------'''

def mode727(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode727(admin, name, printpoint)
	'''---------------------------'''

def mode728(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode728(admin, name, printpoint)
	'''---------------------------'''

def mode729(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode729(admin, name, printpoint)
	'''---------------------------'''

def mode730(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode730(admin, name, printpoint)
	'''---------------------------'''
	
def mode731(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode731(admin, name, printpoint)
	'''---------------------------'''

def mode732(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode732(admin, name, printpoint)
	'''---------------------------'''

def mode733(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode733(admin, name, printpoint)
	'''---------------------------'''

def mode734(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode734(admin, name, printpoint)
	'''---------------------------'''

def mode735(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode735(admin, name, printpoint)
	'''---------------------------'''

def mode736(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode736(admin, name, printpoint)
	'''---------------------------'''

def mode737(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode737(admin, name, printpoint)
	'''---------------------------'''

def mode738(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode738(admin, name, printpoint)
	'''---------------------------'''

def mode739(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode739(admin, name, printpoint)
	'''---------------------------'''

def mode740(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode740(admin, name, printpoint)
	'''---------------------------'''
	
def mode741(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode741(admin, name, printpoint)
	'''---------------------------'''

def mode742(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode742(admin, name, printpoint)
	'''---------------------------'''

def mode743(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode743(admin, name, printpoint)
	'''---------------------------'''

def mode744(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode744(admin, name, printpoint)
	'''---------------------------'''

def mode745(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode745(admin, name, printpoint)
	'''---------------------------'''

def mode746(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode746(admin, name, printpoint)
	'''---------------------------'''

def mode747(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode747(admin, name, printpoint)
	'''---------------------------'''

def mode748(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode748(admin, name, printpoint)
	'''---------------------------'''

def mode749(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode749(admin, name, printpoint)
	'''---------------------------'''

def mode750(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode750(admin, name, printpoint)
	'''---------------------------'''

def mode751(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode751(admin, name, printpoint)
	'''---------------------------'''

def mode752(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode752(admin, name, printpoint)
	'''---------------------------'''

def mode753(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode753(admin, name, printpoint)
	'''---------------------------'''

def mode754(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode754(admin, name, printpoint)
	'''---------------------------'''

def mode755(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode755(admin, name, printpoint)
	'''---------------------------'''

def mode756(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode756(admin, name, printpoint)
	'''---------------------------'''

def mode757(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode757(admin, name, printpoint)
	'''---------------------------'''

def mode758(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode758(admin, name, printpoint)
	'''---------------------------'''

def mode759(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode759(admin, name, printpoint)
	'''---------------------------'''

def mode760(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode760(admin, name, printpoint)
	'''---------------------------'''

def mode761(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode761(admin, name, printpoint)
	'''---------------------------'''

def mode762(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode762(admin, name, printpoint)
	'''---------------------------'''

def mode763(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode763(admin, name, printpoint)
	'''---------------------------'''

def mode764(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode764(admin, name, printpoint)
	'''---------------------------'''

def mode765(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode765(admin, name, printpoint)
	'''---------------------------'''

def mode766(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode766(admin, name, printpoint)
	'''---------------------------'''

def mode767(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode767(admin, name, printpoint)
	'''---------------------------'''

def mode768(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode768(admin, name, printpoint)
	'''---------------------------'''

def mode769(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode769(admin, name, printpoint)
	'''---------------------------'''

def mode770(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode770(admin, name, printpoint)
	'''---------------------------'''

def mode771(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode771(admin, name, printpoint)
	'''---------------------------'''

def mode772(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode772(admin, name, printpoint)
	'''---------------------------'''

def mode773(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode773(admin, name, printpoint)
	'''---------------------------'''

def mode774(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode774(admin, name, printpoint)
	'''---------------------------'''

def mode775(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode775(admin, name, printpoint)
	'''---------------------------'''

def mode776(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode776(admin, name, printpoint)
	'''---------------------------'''

def mode777(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode777(admin, name, printpoint)
	'''---------------------------'''

def mode778(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode778(admin, name, printpoint)
	'''---------------------------'''

def mode779(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode779(admin, name, printpoint)
	'''---------------------------'''
	
def mode780(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode780(admin, name, printpoint)
	'''---------------------------'''

def mode781(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode781(admin, name, printpoint)
	'''---------------------------'''

def mode782(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode782(admin, name, printpoint)
	'''---------------------------'''

def mode783(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode783(admin, name, printpoint)
	'''---------------------------'''

def mode784(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode784(admin, name, printpoint)
	'''---------------------------'''

def mode785(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode785(admin, name, printpoint)
	'''---------------------------'''

def mode786(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode786(admin, name, printpoint)
	'''---------------------------'''

def mode787(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode787(admin, name, printpoint)
	'''---------------------------'''

def mode788(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode788(admin, name, printpoint)
	'''---------------------------'''

def mode789(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode789(admin, name, printpoint)
	'''---------------------------'''
	
def mode790(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode790(admin, name, printpoint)
	'''---------------------------'''

def mode791(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode791(admin, name, printpoint)
	'''---------------------------'''

def mode792(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode792(admin, name, printpoint)
	'''---------------------------'''

def mode793(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode793(admin, name, printpoint)
	'''---------------------------'''

def mode794(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode794(admin, name, printpoint)
	'''---------------------------'''

def mode795(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode795(admin, name, printpoint)
	'''---------------------------'''

def mode796(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode796(admin, name, printpoint)
	'''---------------------------'''

def mode797(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode797(admin, name, printpoint)
	'''---------------------------'''

def mode798(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode798(admin, name, printpoint)
	'''---------------------------'''

def mode799(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode799(admin, name, printpoint)
	'''---------------------------'''

def mode800(admin, name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode800(admin, name, printpoint)
	'''---------------------------'''

def mode801(admin,name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode801(admin, name, printpoint)
	'''---------------------------'''

def mode802(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode802(admin, name, printpoint)
	'''---------------------------'''
	
def mode803(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode803(admin, name, printpoint)
	'''---------------------------'''

def mode804(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode804(admin, name, printpoint)
	'''---------------------------'''

def mode805(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode805(admin, name, printpoint)
	'''---------------------------'''

def mode806(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode806(admin, name, printpoint)
	'''---------------------------'''

def mode807(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode807(admin, name, printpoint)
	'''---------------------------'''

def mode808(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode808(admin, name, printpoint)
	'''---------------------------'''

def mode809(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode809(admin, name, printpoint)
	'''---------------------------'''

def mode810(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode840(admin, name, printpoint)
	'''---------------------------'''
	
def mode811(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode811(admin, name, printpoint)
	'''---------------------------'''

def mode812(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode812(admin, name, printpoint)
	'''---------------------------'''

def mode813(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode813(admin, name, printpoint)
	'''---------------------------'''

def mode814(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode814(admin, name, printpoint)
	'''---------------------------'''

def mode815(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode815(admin, name, printpoint)
	'''---------------------------'''

def mode816(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode816(admin, name, printpoint)
	'''---------------------------'''

def mode817(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode817(admin, name, printpoint)
	'''---------------------------'''

def mode818(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode818(admin, name, printpoint)
	'''---------------------------'''

def mode819(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode819(admin, name, printpoint)
	'''---------------------------'''

def mode820(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode820(admin, name, printpoint)
	'''---------------------------'''
	
def mode821(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode821(admin, name, printpoint)
	'''---------------------------'''

def mode822(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode822(admin, name, printpoint)
	'''---------------------------'''

def mode823(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode823(admin, name, printpoint)
	'''---------------------------'''

def mode824(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode824(admin, name, printpoint)
	'''---------------------------'''

def mode825(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode825(admin, name, printpoint)
	'''---------------------------'''

def mode826(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode826(admin, name, printpoint)
	'''---------------------------'''

def mode827(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode827(admin, name, printpoint)
	'''---------------------------'''

def mode828(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode828(admin, name, printpoint)
	'''---------------------------'''

def mode829(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode829(admin, name, printpoint)
	'''---------------------------'''

def mode830(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode830(admin, name, printpoint)
	'''---------------------------'''
	
def mode831(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode831(admin, name, printpoint)
	'''---------------------------'''

def mode832(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode832(admin, name, printpoint)
	'''---------------------------'''

def mode833(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode833(admin, name, printpoint)
	'''---------------------------'''

def mode834(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode834(admin, name, printpoint)
	'''---------------------------'''

def mode835(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode835(admin, name, printpoint)
	'''---------------------------'''

def mode836(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode836(admin, name, printpoint)
	'''---------------------------'''

def mode837(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode837(admin, name, printpoint)
	'''---------------------------'''

def mode838(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode838(admin, name, printpoint)
	'''---------------------------'''

def mode839(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode839(admin, name, printpoint)
	'''---------------------------'''

def mode840(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode840(admin, name, printpoint)
	'''---------------------------'''
	
def mode841(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode841(admin, name, printpoint)
	'''---------------------------'''

def mode842(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode842(admin, name, printpoint)
	'''---------------------------'''

def mode843(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode843(admin, name, printpoint)
	'''---------------------------'''

def mode844(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode844(admin, name, printpoint)
	'''---------------------------'''

def mode845(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode845(admin, name, printpoint)
	'''---------------------------'''

def mode846(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode846(admin, name, printpoint)
	'''---------------------------'''

def mode847(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode847(admin, name, printpoint)
	'''---------------------------'''

def mode848(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode848(admin, name, printpoint)
	'''---------------------------'''

def mode849(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode849(admin, name, printpoint)
	'''---------------------------'''

def mode850(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode850(admin, name, printpoint)
	'''---------------------------'''

def mode851(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode851(admin, name, printpoint)
	'''---------------------------'''

def mode852(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode852(admin, name, printpoint)
	'''---------------------------'''

def mode853(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode853(admin, name, printpoint)
	'''---------------------------'''

def mode854(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode854(admin, name, printpoint)
	'''---------------------------'''

def mode855(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode855(admin, name, printpoint)
	'''---------------------------'''

def mode856(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode856(admin, name, printpoint)
	'''---------------------------'''

def mode857(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode857(admin, name, printpoint)
	'''---------------------------'''

def mode858(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode858(admin, name, printpoint)
	'''---------------------------'''

def mode859(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode859(admin, name, printpoint)
	'''---------------------------'''

def mode860(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode860(admin, name, printpoint)
	'''---------------------------'''

def mode861(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode861(admin, name, printpoint)
	'''---------------------------'''

def mode862(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode862(admin, name, printpoint)
	'''---------------------------'''

def mode863(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode863(admin, name, printpoint)
	'''---------------------------'''

def mode864(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode864(admin, name, printpoint)
	'''---------------------------'''

def mode865(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode865(admin, name, printpoint)
	'''---------------------------'''

def mode866(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode866(admin, name, printpoint)
	'''---------------------------'''

def mode867(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode867(admin, name, printpoint)
	'''---------------------------'''

def mode868(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode868(admin, name, printpoint)
	'''---------------------------'''

def mode869(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode869(admin, name, printpoint)
	'''---------------------------'''

def mode870(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode870(admin, name, printpoint)
	'''---------------------------'''

def mode871(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode871(admin, name, printpoint)
	'''---------------------------'''

def mode872(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode872(admin, name, printpoint)
	'''---------------------------'''

def mode873(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode873(admin, name, printpoint)
	'''---------------------------'''

def mode874(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode874(admin, name, printpoint)
	'''---------------------------'''

def mode875(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode875(admin, name, printpoint)
	'''---------------------------'''

def mode876(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode876(admin, name, printpoint)
	'''---------------------------'''

def mode877(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode877(admin, name, printpoint)
	'''---------------------------'''

def mode878(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode878(admin, name, printpoint)
	'''---------------------------'''

def mode879(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode879(admin, name, printpoint)
	'''---------------------------'''
	
def mode880(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode880(admin, name, printpoint)
	'''---------------------------'''

def mode881(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode881(admin, name, printpoint)
	'''---------------------------'''

def mode882(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode882(admin, name, printpoint)
	'''---------------------------'''

def mode883(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode883(admin, name, printpoint)
	'''---------------------------'''

def mode884(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode884(admin, name, printpoint)
	'''---------------------------'''

def mode885(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode885(admin, name, printpoint)
	'''---------------------------'''

def mode886(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode886(admin, name, printpoint)
	'''---------------------------'''

def mode887(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode887(admin, name, printpoint)
	'''---------------------------'''

def mode888(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode888(admin, name, printpoint)
	'''---------------------------'''

def mode889(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode889(admin, name, printpoint)
	'''---------------------------'''
	
def mode890(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode890(admin, name, printpoint)
	'''---------------------------'''

def mode891(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode891(admin, name, printpoint)
	'''---------------------------'''

def mode892(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode892(admin, name, printpoint)
	'''---------------------------'''

def mode893(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode893(admin, name, printpoint)
	'''---------------------------'''

def mode894(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode894(admin, name, printpoint)
	'''---------------------------'''

def mode895(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode895(admin, name, printpoint)
	'''---------------------------'''

def mode896(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode896(admin, name, printpoint)
	'''---------------------------'''

def mode897(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode897(admin, name, printpoint)
	'''---------------------------'''

def mode898(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode898(admin, name, printpoint)
	'''---------------------------'''

def mode899(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode899(admin, name, printpoint)
	'''---------------------------'''

def mode900(admin, name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode900(admin, name, printpoint)
	'''---------------------------'''

def mode901(admin,name):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode901(admin, name, printpoint)
	'''---------------------------'''

def mode902(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode902(admin, name, printpoint)
	'''---------------------------'''
	
def mode903(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode903(admin, name, printpoint)
	'''---------------------------'''

def mode904(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode904(admin, name, printpoint)
	'''---------------------------'''

def mode905(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode905(admin, name, printpoint)
	'''---------------------------'''

def mode906(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode906(admin, name, printpoint)
	'''---------------------------'''

def mode907(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode907(admin, name, printpoint)
	'''---------------------------'''

def mode908(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode908(admin, name, printpoint)
	'''---------------------------'''

def mode909(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode909(admin, name, printpoint)
	'''---------------------------'''

def mode910(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode940(admin, name, printpoint)
	'''---------------------------'''
	
def mode911(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode911(admin, name, printpoint)
	'''---------------------------'''

def mode912(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode912(admin, name, printpoint)
	'''---------------------------'''

def mode913(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode913(admin, name, printpoint)
	'''---------------------------'''

def mode914(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode914(admin, name, printpoint)
	'''---------------------------'''

def mode915(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode915(admin, name, printpoint)
	'''---------------------------'''

def mode916(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode916(admin, name, printpoint)
	'''---------------------------'''

def mode917(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode917(admin, name, printpoint)
	'''---------------------------'''

def mode918(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode918(admin, name, printpoint)
	'''---------------------------'''

def mode919(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode919(admin, name, printpoint)
	'''---------------------------'''

def mode920(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode920(admin, name, printpoint)
	'''---------------------------'''
	
def mode921(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode921(admin, name, printpoint)
	'''---------------------------'''

def mode922(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode922(admin, name, printpoint)
	'''---------------------------'''

def mode923(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode923(admin, name, printpoint)
	'''---------------------------'''

def mode924(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode924(admin, name, printpoint)
	'''---------------------------'''

def mode925(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode925(admin, name, printpoint)
	'''---------------------------'''

def mode926(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode926(admin, name, printpoint)
	'''---------------------------'''

def mode927(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode927(admin, name, printpoint)
	'''---------------------------'''

def mode928(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode928(admin, name, printpoint)
	'''---------------------------'''

def mode929(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode929(admin, name, printpoint)
	'''---------------------------'''

def mode930(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode930(admin, name, printpoint)
	'''---------------------------'''
	
def mode931(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode931(admin, name, printpoint)
	'''---------------------------'''

def mode932(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode932(admin, name, printpoint)
	'''---------------------------'''

def mode933(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode933(admin, name, printpoint)
	'''---------------------------'''

def mode934(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode934(admin, name, printpoint)
	'''---------------------------'''

def mode935(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode935(admin, name, printpoint)
	'''---------------------------'''

def mode936(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode936(admin, name, printpoint)
	'''---------------------------'''

def mode937(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode937(admin, name, printpoint)
	'''---------------------------'''

def mode938(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode938(admin, name, printpoint)
	'''---------------------------'''

def mode939(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode939(admin, name, printpoint)
	'''---------------------------'''

def mode940(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode940(admin, name, printpoint)
	'''---------------------------'''
	
def mode941(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode941(admin, name, printpoint)
	'''---------------------------'''

def mode942(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode942(admin, name, printpoint)
	'''---------------------------'''

def mode943(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode943(admin, name, printpoint)
	'''---------------------------'''

def mode944(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode944(admin, name, printpoint)
	'''---------------------------'''

def mode945(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode945(admin, name, printpoint)
	'''---------------------------'''

def mode946(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode946(admin, name, printpoint)
	'''---------------------------'''

def mode947(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode947(admin, name, printpoint)
	'''---------------------------'''

def mode948(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode948(admin, name, printpoint)
	'''---------------------------'''

def mode949(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode949(admin, name, printpoint)
	'''---------------------------'''

def mode950(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode950(admin, name, printpoint)
	'''---------------------------'''

def mode951(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode951(admin, name, printpoint)
	'''---------------------------'''

def mode952(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode952(admin, name, printpoint)
	'''---------------------------'''

def mode953(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode953(admin, name, printpoint)
	'''---------------------------'''

def mode954(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode954(admin, name, printpoint)
	'''---------------------------'''

def mode955(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode955(admin, name, printpoint)
	'''---------------------------'''

def mode956(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode956(admin, name, printpoint)
	'''---------------------------'''

def mode957(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode957(admin, name, printpoint)
	'''---------------------------'''

def mode958(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode958(admin, name, printpoint)
	'''---------------------------'''

def mode959(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode959(admin, name, printpoint)
	'''---------------------------'''

def mode960(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode960(admin, name, printpoint)
	'''---------------------------'''

def mode961(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode961(admin, name, printpoint)
	'''---------------------------'''

def mode962(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode962(admin, name, printpoint)
	'''---------------------------'''

def mode963(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode963(admin, name, printpoint)
	'''---------------------------'''

def mode964(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode964(admin, name, printpoint)
	'''---------------------------'''

def mode965(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode965(admin, name, printpoint)
	'''---------------------------'''

def mode966(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode966(admin, name, printpoint)
	'''---------------------------'''

def mode967(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode967(admin, name, printpoint)
	'''---------------------------'''

def mode968(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode968(admin, name, printpoint)
	'''---------------------------'''

def mode969(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode969(admin, name, printpoint)
	'''---------------------------'''

def mode970(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode970(admin, name, printpoint)
	'''---------------------------'''

def mode971(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode971(admin, name, printpoint)
	'''---------------------------'''

def mode972(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode972(admin, name, printpoint)
	'''---------------------------'''

def mode973(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode973(admin, name, printpoint)
	'''---------------------------'''

def mode974(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode974(admin, name, printpoint)
	'''---------------------------'''

def mode975(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode975(admin, name, printpoint)
	'''---------------------------'''

def mode976(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode976(admin, name, printpoint)
	'''---------------------------'''

def mode977(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode977(admin, name, printpoint)
	'''---------------------------'''

def mode978(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode978(admin, name, printpoint)
	'''---------------------------'''

def mode979(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode979(admin, name, printpoint)
	'''---------------------------'''
	
def mode980(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode980(admin, name, printpoint)
	'''---------------------------'''

def mode981(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode981(admin, name, printpoint)
	'''---------------------------'''

def mode982(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode982(admin, name, printpoint)
	'''---------------------------'''

def mode983(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode983(admin, name, printpoint)
	'''---------------------------'''

def mode984(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode984(admin, name, printpoint)
	'''---------------------------'''

def mode985(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode985(admin, name, printpoint)
	'''---------------------------'''

def mode986(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode986(admin, name, printpoint)
	'''---------------------------'''

def mode987(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode987(admin, name, printpoint)
	'''---------------------------'''

def mode988(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode988(admin, name, printpoint)
	'''---------------------------'''

def mode989(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode989(admin, name, printpoint)
	'''---------------------------'''
	
def mode990(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = ""
	mode990(admin, name, printpoint)
	'''---------------------------'''

def mode991(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode991(admin, name, printpoint)
	'''---------------------------'''

def mode992(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode992(admin, name, printpoint)
	'''---------------------------'''

def mode993(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode993(admin, name, printpoint)
	'''---------------------------'''

def mode994(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode994(admin, name, printpoint)
	'''---------------------------'''

def mode995(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode995(admin, name, printpoint)
	'''---------------------------'''

def mode996(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode996(admin, name, printpoint)
	'''---------------------------'''

def mode997(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode997(admin, name, printpoint)
	'''---------------------------'''

def mode998(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode998(admin, name, printpoint)
	'''---------------------------'''

def mode999(admin, name, printpoint):
	'''------------------------------
	---?-----------------------------
	------------------------------'''
	name = "?"
	mode999(admin, name, printpoint)
	'''---------------------------'''

def LibraryUpdate(admin, datenowS, Library_On, Library_CleanDate, Library_UpdateDate):
	name = 'LibraryUpdate' ; extra = "" ; printpoint = "" ; TypeError = ""

	libraryisscanningvideo = xbmc.getCondVisibility('Library.IsScanningVideo')
	'''---------------------------'''
	if Library_On == "true":
		systemidle3600 = xbmc.getCondVisibility('System.IdleTime(3600)')
		if not systemidle3600: printpoint = printpoint + '9'
		else:
			'''---------------------------'''
			if Library_CleanDate != "" and datenowS != "":
				import datetime as dt
				datenowD = stringtodate(datenowS,'%Y-%m-%d')
				Library_CleanDateD = stringtodate(Library_CleanDate,'%Y-%m-%d')
				Library_CleanDate2D = Library_CleanDateD + dt.timedelta(days=7)
				'''---------------------------'''
				if datenowD > Library_CleanDate2D: printpoint = printpoint + "7"
				'''---------------------------'''
			else: printpoint = printpoint + "7"
			
			if "7" in printpoint:
				xbmc.executebuiltin('CleanLibrary(video)')
				setsetting('Library_CleanDate',datenowS)
				'''---------------------------'''

			elif Library_CleanDate == datenowS: printpoint = printpoint + "1"
			
			else:
				if libraryisscanningvideo: printpoint = printpoint + "6"
				elif datenowS != Library_UpdateDate:
					printpoint = printpoint + "7"
					setsetting('Library_UpdateDate',datenowS)
					xbmc.executebuiltin('UpdateLibrary(video)')
					'''---------------------------'''
				else:
					printpoint = printpoint + "9"
					'''---------------------------'''
			
		'''------------------------------
		---PRINT-END---------------------
		------------------------------'''
		text = "Library_UpdateDate" + space2 + str(Library_UpdateDate) + space + "Library_CleanDate" + space2 + str(Library_CleanDate) + space + extra
		printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
		'''---------------------------'''

def videoplayertweak(admin,playerhasvideo):
	if playerhasvideo:
		#if admin: xbmc.executebuiltin('Notification(Admin,fix bug with subtitles (1),1000)')
		playerfolderpath = xbmc.getInfoLabel('Player.FolderPath')
		videoplayersubtitlesenabled = xbmc.getInfoLabel('VideoPlayer.SubtitlesEnabled')
		videoplayerhassubtitles = xbmc.getInfoLabel('VideoPlayer.HasSubtitles')
		'''fix bug with subtitles'''
		if videoplayerhassubtitles and videoplayersubtitlesenabled:
			fix = 'no'
			if '.sdarot.w' in playerfolderpath: fix = 'yes'
			elif xbmc.getCondVisibility('!VideoPlayer.Content(Movies)') and xbmc.getCondVisibility('!VideoPlayer.Content(Episodes)') and xbmc.getCondVisibility('IsEmpty(VideoPlayer.Year)') and xbmc.getCondVisibility('IsEmpty(VideoPlayer.Plot)') and xbmc.getCondVisibility('!SubString(Player.Title,S0)') and xbmc.getCondVisibility('!SubString(Player.Title,S1)') and xbmc.getCondVisibility('!SubString(VideoPlayer.Title,TNPB)') and xbmc.getCondVisibility('!SubString(VideoPlayer.Title,Staael)') and xbmc.getCondVisibility('!SubString(Player.Filename,YIFY)'): fix = 'yes'
			if fix == 'yes':
				#if admin: xbmc.executebuiltin('Notification(Admin,fix bug with subtitles,1000)')
				xbmc.executebuiltin('Action(ShowSubtitles)')
				'''---------------------------'''
				
		'''video osd auto close'''
		videoosd = xbmc.getCondVisibility('Window.IsVisible(VideoOSD.xml)')
		systemidle10 = xbmc.getCondVisibility('System.IdleTime(10)')
		videoosdsettingsW = xbmc.getCondVisibility('Window.IsVisible(VideoOSDSettings.xml)')
		if videoosd and systemidle10 and not videoosdsettingsW:
			subtitleosdbutton = xbmc.getCondVisibility('Control.HasFocus(703)') #subtitleosdbutton
			volumeosdbutton = xbmc.getCondVisibility('Control.HasFocus(707)') #volumeosdbutton
			dialogpvrchannelsosd = xbmc.getCondVisibility('Window.IsVisible(DialogPVRChannelsOSD.xml)')
			'''---------------------------'''
			if (not subtitleosdbutton or not videoplayerhassubtitles) and not volumeosdbutton and not dialogpvrchannelsosd:
				#if admin: xbmc.executebuiltin('Notification(Admin,videoosdauto,1000)')
				xbmc.executebuiltin('Dialog.Close(VideoOSD.xml)')
				'''---------------------------'''
			else:
				systemidle20 = xbmc.getCondVisibility('System.IdleTime(20)')
				if systemidle20: xbmc.executebuiltin('Dialog.Close(VideoOSD.xml)')
				'''---------------------------'''

def getPing(output):
	'''------------------------------
	---setPing-ms--------------------
	------------------------------'''
	output2 = output
	output2len = len(output2)
	output2lenS = str(output2len)
	
	if systemplatformlinux or systemplatformlinuxraspberrypi: start_len = output2.find("min/avg/max =", 0, output2len)
	elif systemplatformwindows: start_len = output2.find("Average =", 0, output2len)
	elif systemplatformandroid: start_len = output2.find("min/avg/max/mdev =", 0, output2len)
	
	start_lenS = str(start_len)
	if systemplatformlinux or systemplatformlinuxraspberrypi: start_lenN = int(start_lenS) + 14
	elif systemplatformwindows: start_lenN = int(start_lenS) + 10
	elif systemplatformandroid: start_lenN = int(start_lenS) + 19
	
	if systemplatformlinux or systemplatformlinuxraspberrypi: end_len = output2.find("/", start_lenN, output2len)
	elif systemplatformwindows: end_len = output2.find("ms", start_lenN, output2len)
	elif systemplatformandroid: end_len = output2.find("/", start_lenN, output2len)
	
	end_lenS = str(end_len)
	end_lenN = int(end_lenS)
	found = output2[start_lenN:end_lenN]
	foundS = str(found)
	try: foundF = float(foundS)
	except: foundF = ""
	'''---------------------------'''
	if not systemplatformwindows:
		mid_len = output2.find(".", start_lenN, end_lenN)
		mid_lenS = str(mid_len)
		mid_lenN = int(mid_lenS)
		totalnumN = mid_lenN - start_lenN
		totalnumS = str(start_lenN)
		'''---------------------------'''
		if foundF != "":
			found2 = round(foundF)
			found2S = str(found2)
		else:
			found2S = foundS
		if ".0" in found2S: found2S = found2S.replace(".0","",1)
		'''---------------------------'''
	else:
		found2S = foundS
		mid_lenS = ""
		'''---------------------------'''
	if admin: extra = newline + "output2len" + space2 + output2lenS + space + "start_len" + space2 + start_lenS + space + "end_len" + space2 + end_lenS + space + "found/2" + space2 + foundS + "/" + found2S + space + "mid_len" + space2 + mid_lenS
	'''---------------------------'''
	return found2S
			
def connectioncheck(admin):
	'''------------------------------
	---NETWORK-STATUS----------------
	------------------------------'''
	name = 'connectioncheck' ; printpoint = ""
	list = ['-> (Exit)', 'Internet', 'Router'] ; returned = "" ; returned2 = "" ; totalL = []
	
	returned, type = dialogselect('Choose ping type',list,0)
	if returned == -1: pass
	elif returned == 0: pass
	else:
		if returned == 1:
			'''Internet'''
			list = ['-> (Exit)', 'www.google.com', 'www.google.co.il', 'en.wikipedia.org', 'www.facebook.com']
			returned2, target = dialogselect('Choose ping target',list,0)
			if returned == -1: pass
			elif returned == 0: pass
			else: printpoint = printpoint + '7'
		
		elif returned == 2:
			'''Router'''
			list = ['-> (Exit)', xbmc.getInfoLabel('Network.GatewayAddress'), 'Manual']
			returned2, target = dialogselect('Choose ping target',list,0)
			if returned2 == -1: pass
			elif returned2 == 0: pass
			elif returned2 == 1: printpoint = printpoint + '7'
			elif returned2 == 2:
				target = dialogkeyboard(xbmc.getInfoLabel('Network.GatewayAddress'), 'Choose local IP address', 0, '0', "", "")
				if target != 'skip': printpoint = printpoint + '7'
		
		if '7' in printpoint:
			dp = xbmcgui.DialogProgress() ; count = 0
			dp.create('Pinging type: ' + str(type), 'target: ' + str(target), " ")
			while count < 100 and not dp.iscanceled() and not xbmc.abortRequested:
				if returned == 1 or returned == 2:
					if systemplatformwindows: output = terminal('ping '+str(target)+' -n 1',"Connected")
					elif systemplatformlinux or systemplatformlinuxraspberrypi: output = terminal('ping -W 1 -w 1 -4 -q '+str(target)+'',"Connected")
					elif systemplatformandroid: output = terminal('ping -W 1 -w 1 -c 1 '+str(target)+'',"Connected")
					else: output = ""

					ping = getPing(output)
					totalL.append(ping)
					
				count += 1
				dp.update(count,'','Ping: ' + str(ping))
				xbmc.sleep(1000)
				
			dp.close
			message = 'Pinging type: ' + str(type) + newline + 'target: ' + str(target) + newline + 'pings: ' + str(totalL)
			diaogtextviewer('Pinging summary',message)
	
	text = "returned" + space2 + str(returned) + space + space + "returned2" + space2 + str(returned2) + newline + \
	'totalL' + space2 + str(totalL)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def setSkin_Update(admin, datenowS, Skin_Version, Skin_UpdateDate, Skin_UpdateLog):
	'''------------------------------
	---CHECK-FOR-SKIN-UPDATE---------
	------------------------------'''
	name = 'setSkin_Update' ; printpoint = "" ; returned_Dialog = ""
	Skin_Version2 = xbmc.getInfoLabel('System.AddonVersion(skin.featherence)')
	
	if datenowS == "" or datenowS == None: printpoint = printpoint + '9'
	else:
		
		if Skin_Version != Skin_Version2:
			printpoint = printpoint + '1'
			setsetting('Skin_UpdateLog',"true")
			setsetting('Skin_UpdateDate',datenowS)
			setsetting('Skin_Version',Skin_Version2)
			#xbmc.executebuiltin('RunScript(script.featherence.service.debug,,?mode=19)')
			Skin_UpdateLog = 'true'
			
		else: printpoint = printpoint + '2'
		
		if Skin_UpdateLog == 'true':
			printpoint = printpoint + '3'
			returned_Dialog, returned_Header, returned_Message = checkDialog(admin)
			if returned_Dialog == "":
				printpoint = printpoint + '7'
				setsetting('Skin_UpdateLog',"false")
				setSkin_UpdateLog(admin, Skin_Version2, Skin_UpdateDate, datenowS)
		else:
			printpoint = printpoint + '8'
			
	text = "Skin_Version" + space2 + str(Skin_Version) + newline + \
	"Skin_Version2" + space2 + str(Skin_Version2) + newline + \
	"datenowS" + space2 + str(datenowS) + newline + \
	"Skin_UpdateDate" + space2 + str(Skin_UpdateDate) + newline + \
	"Skin_UpdateLog" + space2 + str(Skin_UpdateLog) + newline + \
	"returned_Dialog" + space2 + str(returned_Dialog)
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def setSkin_UpdateLog(admin, Skin_Version, Skin_UpdateDate, datenowS, force=False):	
	'''------------------------------
	---VARIABLES---------------------
	------------------------------'''
	name = 'setSkin_UpdateLog' ; printpoint = "" ; number2S = "" ; extra = "" ; TypeError = ""
	datenowD = stringtodate(datenowS,'%Y-%m-%d')
	datedifferenceD = stringtodate(Skin_UpdateDate, '%Y-%m-%d')
	if "error" in [datenowD, datedifferenceD]: printpoint = printpoint + "9"
	try:
		number2 = datenowD - datedifferenceD
		number2S = str(number2)
		printpoint = printpoint + "2"
		'''---------------------------'''
	except Exception, TypeError:
		extra = extra + newline + 'TypeError' + space2 + str(TypeError)
		printpoint = printpoint + "9"
		'''---------------------------'''
	if (not "9" in printpoint or force == True) and xbmc.getSkinDir() == 'skin.featherence':
		printpoint = printpoint + "4"
		if "day," in number2S: number2S = number2S.replace(" day, 0:00:00","",1)
		elif "days," in number2S: number2S = number2S.replace(" days, 0:00:00","",1)
		else: number2S = "0"
		number2N = int(number2S)
		'''---------------------------'''
		if number2N == 0: header = '[COLOR=yellow]' + localize(79201) + space + localize(33006) + " - " + Skin_Version + '[/COLOR]'
		elif number2N == 1: header = '[COLOR=green]' + localize(79201) + space + addonString_servicefeatherence(5).encode('utf-8') + " - " + Skin_Version + '[/COLOR]'
		elif number2N <= 7: header = '[COLOR=purple]' + localize(79201) + space + addonString_servicefeatherence(6).encode('utf-8') + " - " + Skin_Version + '[/COLOR]'
		elif force == True: header = addonString(32091).encode('utf-8') + space + space5 + Skin_Version
		else: header = ""
		'''---------------------------'''
		if os.path.exists(skinlog_file):
			printpoint = printpoint + "5"
			log = open(skinlog_file, 'r')
			message2 = log.read()
			log.close()
			message2S = str(message2)
			message3 = message2[70:8000]
			message3 = '"' + message3 + '"'
			message3S = str(message3)
			if header != "":
				printpoint = printpoint + "6"
				if number2N == 0 or xbmc.getCondVisibility('System.IdleTime(5)'):
					printpoint = printpoint + "7"
					diaogtextviewer(header, message2)
					'''---------------------------'''
		else: printpoint = printpoint + '9'
			
	setsetting('Skin_UpdateLog',"false")
	
	text = "Skin_Version" + space2 + str(Skin_Version) + newline + \
	"force" + space2 + str(force) + newline + \
	"datenowS" + space2 + str(datenowS) + newline + \
	"Skin_UpdateDate" + space2 + str(Skin_UpdateDate) + newline + \
	"Skin_UpdateLog" + space2 + str(Skin_UpdateLog) + newline + \
	"number2S" + space2 + str(number2S)
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def doFix_100(admin, custom, TEMP):
	'''---------------------------'''
	if custom == "100": dialogok(localize(78971)+ '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (localize(342)) + '[/COLOR]', '$LOCALIZE[78972]', '$LOCALIZE[78973]', '$LOCALIZE[78980]')
	elif custom == "101": dialogok(localize(78971)+ '[CR]' + '[COLOR=yellow]' + str74550.encode('utf-8') % (str36903.encode('utf-8')) + '[/COLOR]', '$LOCALIZE[78972]', '$LOCALIZE[78973]', '$LOCALIZE[78980]')
	libraryisscanningvideo = xbmc.getCondVisibility('Library.IsScanningVideo')
	if libraryisscanningvideo: xbmc.executebuiltin('UpdateLibrary(video)')
	#if not systemplatformwindows: UserBlock("ON")
	setSkinSetting("1",'Admin',"true")
	printpoint = "" ; extra = ""
	'''---------------------------'''
	xbmc.executebuiltin('ActivateWindow(10025,'+TEMP+',return)')
	xbmc.sleep(500)
	xbmc.executebuiltin('Container.SetViewMode(50)')
	notification_common(custom)
	printpoint = doFix_100A(printpoint, custom, TEMP)
	'''---------------------------'''
	if not "9" in printpoint: printpoint = doFix_100I(printpoint, custom)
	'''---------------------------'''	
	if not "9" in printpoint: printpoint = doFix_100M(printpoint, custom)
	'''---------------------------'''
	if not "9" in printpoint and "C" in printpoint: printpoint = doFix_100A(printpoint, custom, TEMP)
	'''---------------------------'''
	if not "9" in printpoint and "C" in printpoint: printpoint = doFix_100I(printpoint, custom)
	'''---------------------------'''	
	if not "9" in printpoint and "C" in printpoint: printpoint = doFix_100M(printpoint, custom)
	'''---------------------------'''
	if not "9" in printpoint: 
		xbmc.sleep(1000)
		dialogkaitoastW = xbmc.getCondVisibility('Window.IsVisible(DialogKaiToast.xml)')
		count = 0
		count2 = 0
		while count < 10 and dialogkaitoastW and count2 > -2 and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			xbmc.sleep(500)
			dialogkaitoastW = xbmc.getCondVisibility('Window.IsVisible(DialogKaiToast.xml)')
			xbmc.sleep(500)
			if count == 1: printpoint = printpoint + "6"
			if dialogkaitoastW: count2 += 1
			elif count2 > 0: count2 += -1
			if count == 10:
				printpoint = printpoint + "9"
				extra = extra + "error_count=10"
				'''---------------------------'''
	if not "9" in printpoint: printpoint = printpoint + "7"
	
	'''---------------------------'''
	dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
	if dialogcontentsettingsW: xbmc.executebuiltin('Action(Close)')
	xbmc.sleep(500)
	xbmc.executebuiltin('ReplaceWindow(Home)')
	setSkinSetting("1",'Admin',"false")
	#if not systemplatformwindows: UserBlock("OFF")
	'''---------------------------'''
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	#extra = newline + "localize(107)" + space2 + localize(107) + space + "localize107" + space2 + localize(107) + space + "xbmc.getInfoLabel('$LOCALIZE[107]')" + space2 + xbmc.getInfoLabel('$LOCALIZE[107]')
	text = "systemcurrentcontrol" + space2 + systemcurrentcontrol + space + "custom" + space2 + str(custom) + extra
	printlog(title='doFix_100', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return printpoint

def doFix_100_0(printpoint, custom):
	'''---------------------------'''
	xbmc.executebuiltin("UpdateLocalAddons") ; xbmc.sleep(2000)
	if custom == "100": x = xbmc.getCondVisibility('System.HasAddon(metadata.universal)')
	elif custom == "101": x = xbmc.getCondVisibility('System.HasAddon(metadata.tvdb.com)')
	connected = xbmc.getInfoLabel('Skin.HasSetting(Connected)')
	xbmc.sleep(500)
	'''---------------------------'''
	if custom == "100": list = [os.path.exists(addons_path + 'metadata.universal'), os.path.exists(addons_path + 'metadata.common.impa.com'), os.path.exists(addons_path + 'metadata.common.port.hu'), os.path.exists(addons_path + 'metadata.common.movieposterdb.com'), os.path.exists(addons_path + 'metadata.common.rt.com'), os.path.exists(addons_path + 'metadata.common.trakt.tv')]
	elif custom == "101": list = [os.path.exists(addons_path + 'metadata.common.imdb.com')]
	listS = str(list)
	'''---------------------------'''
	if printpoint == "remove" or ("False" in listS and "True" in listS):
		'''------------------------------
		---metadata.universal------------
		------------------------------'''
		printpoint = printpoint + "9"
		if admin: notification_common(custom)
		addonsL = []
		if custom == "100":
			addonsL.append('metadata.common.impa.com')
			addonsL.append('metadata.common.movieposterdb.com')
			addonsL.append('metadata.common.ofdb.de')
			addonsL.append('metadata.common.port.hu')
			addonsL.append('metadata.common.rt.com')
			addonsL.append('metadata.common.trakt.tv')
			addonsL.append('metadata.universal')
			'''---------------------------'''
		elif custom == "101":
			#addonsL.append('metadata.tvdb.com')
			addonsL.append('metadata.common.imdb.com')
			'''---------------------------'''
		removeaddons(addonsL,"13")
		#xbmc.executebuiltin("UpdateLocalAddons")
		#xbmc.executebuiltin("UpdateAddonRepos")
		xbmc.sleep(4000)
		
	elif connected and not "False" in listS and x:
		printpoint = printpoint + "0"
		'''---------------------------'''
	text = "listS" + space2 + listS	 + space + "custom" + space2 + str(custom) + space
	printlog(title='doFix_100_0', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return printpoint

def doFix_100A(printpoint, custom, TEMP):
	xbmc.sleep(200)
	containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
	count = 0
	while count < 10 and containerfolderpath != TEMP and not "9" in printpoint and not xbmc.abortRequested:
		'''------------------------------
		---containerfolderpath-----------
		------------------------------'''
		xbmc.sleep(100)
		count += 1
		if count > 5 and TEMP in containerfolderpath: xbmc.executebuiltin('Action(Back)') ; xbmc.sleep(200)
		containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
		xbmc.sleep(100)
		if count == 1: printpoint = printpoint + "A"
		if count == 10: printpoint = printpoint + "9"
		'''---------------------------'''
		
	if not "9" in printpoint:
		'''------------------------------
		---ContextMenu-------------------
		------------------------------'''
		xbmc.executebuiltin('Action(PageUp)')
		xbmc.sleep(200)
		systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
		if custom == "100": x = "[movies]"
		elif custom == "101": x = "[tvshows]"
		else:
			x = "" ; printpoint = printpoint + "9"
		
		count = 0
		while count < 10 and systemcurrentcontrol != x and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			systemcurrentcontrol = findin_systemcurrentcontrol("0",x,100,'Action(Down)','Action(ContextMenu)')
			if count == 1: printpoint = printpoint + "B"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
		if not "9" in printpoint:
			count = 0
			while count < 10 and not xbmc.abortRequested: 
				count += 1
				xbmc.sleep(40)
				if count <= 7: xbmc.executebuiltin('Action(Up)')
				else:
					if count == 8: printpoint = printpoint + "8"
					xbmc.executebuiltin('Action(Down)')
					'''---------------------------'''
			
		xbmc.sleep(200)
		systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
		count = 0
		while count < 10 and systemcurrentcontrol != str20442 and not "9" in printpoint and not xbmc.abortRequested:
			'''------------------------------
			---Change-content----------------
			------------------------------'''
			count += 1
			countS = str(count)
			'''---------------------------'''
			systemcurrentcontrol = findin_systemcurrentcontrol("0",str20442,100,'Action(Down)','Action(Select)') #Change content
			'''---------------------------'''
			if systemcurrentcontrol == str20442: printpoint = printpoint + "C"
			'''---------------------------'''
			
		if count == 10:
			count = 0
			while count < 10 and not xbmc.abortRequested: 
				count += 1
				if count <= 7: xbmc.executebuiltin('Action(Up)')
				else: xbmc.executebuiltin('Action(Down)')
				'''---------------------------'''
			
			xbmc.sleep(200)
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
			count = 0
			while count < 10 and systemcurrentcontrol != str20333 and not "9" in printpoint and not xbmc.abortRequested:
				'''------------------------------
				---Set-content-------------------
				------------------------------'''
				count += 1
				countS = str(count)
				'''---------------------------'''
				systemcurrentcontrol = findin_systemcurrentcontrol("0",str20333,100,'Action(Down)','Action(Select)') #Set content
				'''---------------------------'''
				if systemcurrentcontrol == str20333: printpoint = printpoint + "D"
				if count == 10: printpoint = printpoint + "9" + space3 + systemcurrentcontrol
				'''---------------------------'''
		
		dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
		count = 0
		while count < 10 and not dialogcontentsettingsW and not "9" in printpoint and not xbmc.abortRequested:
			'''------------------------------
			---dialogcontentsettingsW--------
			------------------------------'''
			count += 1
			xbmc.sleep(100)
			dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
			xbmc.sleep(100)
			if count == 1: printpoint = printpoint + "E"
			if count == 10: printpoint = printpoint + "9" + space3 + systemcurrentcontrol
			'''---------------------------'''
		
		controlhasfocus20 = xbmc.getCondVisibility('Control.HasFocus(20)')
		count = 0
		while count < 10 and not controlhasfocus20 and not "9" in printpoint and not xbmc.abortRequested:
			'''------------------------------
			---controlhasfocus20-------------
			------------------------------'''
			count += 1
			controlhasfocus20 = findin_controlhasfocus("0",20,100,'Control.SetFocus(20)',"")
			if count == 1: printpoint = printpoint + "F"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
				
	'''---------------------------'''
	return printpoint

def doFix_100I(printpoint, custom):
	xbmc.sleep(500)
	systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
	if "C" in printpoint and not "M" in printpoint:
		'''------------------------------
		---Change-content----------------
		------------------------------'''
		count = 0
		while count < 10 and (not localize(231) in systemcurrentcontrol or not localize(16018) in systemcurrentcontrol) and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			if count < 5: systemcurrentcontrol = findin_systemcurrentcontrol("1",localize(231),100,'Action(Select)','Action(Down)')
			elif count >=5: systemcurrentcontrol = findin_systemcurrentcontrol("1",localize(16018),100,'Action(Select)','Action(Down)')
			if count == 1: printpoint = printpoint + "I"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
		
	elif "D" in printpoint or "M" in printpoint:
		'''------------------------------
		---Set-content-------------------
		------------------------------'''
		count = 0
		if custom == "100": x = localize(342) ; y = str36901.encode('utf-8') ; z = "Universal Movie Scraper"
		elif custom == "101": x = str36903.encode('utf-8') ; y = str36903.encode('utf-8') ; z = "The TVDB"
		else: x = "" ; y = "" ; z = ""
		while count < 10 and (not x in systemcurrentcontrol and not y in systemcurrentcontrol) and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			if count < 5: systemcurrentcontrol = findin_systemcurrentcontrol("1",x,100,'Action(Select)','Action(Down)')
			elif count >=5: systemcurrentcontrol = findin_systemcurrentcontrol("1",y,100,'Action(Select)','Action(Down)')
			if count == 1: printpoint = printpoint + "Q"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''

		'''---------------------------'''
		xbmc.executebuiltin('Control.SetFocus(20)')
		xbmc.sleep(200)
		systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
		count = 0
		while count < 10 and not z in systemcurrentcontrol and not "9" in printpoint and not xbmc.abortRequested:
			'''------------------------------
			---SCRAPER-NAME------------------
			------------------------------'''
			count += 1
			systemcurrentcontrol = findin_systemcurrentcontrol("1",z,300,'Action(Down)','Action(Select)')
			if z in systemcurrentcontrol: xbmc.executebuiltin('Action(Select)')
			if count == 5: xbmc.executebuiltin('Control.SetFocus(20)')
			if count == 1: printpoint = printpoint + "R"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
		
		if custom == "100":
			xbmc.sleep(400)
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
			count = 0
			while count < 10 and (not str20329 in systemcurrentcontrol or not "(*)" in systemcurrentcontrol) and not "9" in printpoint and not xbmc.abortRequested:
				'''------------------------------
				---Movies are in separate folders that match the movie title - ON
				------------------------------'''
				count += 1
				systemcurrentcontrol = findin_systemcurrentcontrol("1",str20329,400,'Action(Down)','')
				if count == 1: printpoint = printpoint + "S"
				if count == 10: printpoint = printpoint + "9"
				if str20329 in systemcurrentcontrol: systemcurrentcontrol = findin_systemcurrentcontrol("1","(*)",400,'Action(Select)','')
				'''---------------------------'''
				
			xbmc.sleep(400)
			systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
			count = 0
			while count < 10 and (not str20346.encode('utf-8') in systemcurrentcontrol or "(*)" in systemcurrentcontrol) and not "9" in printpoint and not xbmc.abortRequested:
				'''------------------------------
				---Scan recursively - OFF--------
				------------------------------'''
				count += 1
				systemcurrentcontrol = findin_systemcurrentcontrol("1",str20346.encode('utf-8'),400,'Action(Down)','')
				if count == 1: printpoint = printpoint + "T"
				if count == 10: printpoint = printpoint + "9"
				if str20346.encode('utf-8') in systemcurrentcontrol: systemcurrentcontrol = findin_systemcurrentcontrol("1","( )",400,'Action(Select)','')
				'''---------------------------'''
				
			'''count = 0
			while count < 10 and (systemcurrentcontrol != localize(186) or systemcurrentcontrol != localize(12321)) and not "9" in printpoint and not xbmc.abortRequested:
				count += 1
				if count < 4: xbmc.executebuiltin('Action(Down)')
				if count < 5: systemcurrentcontrol = findin_systemcurrentcontrol("0",localize(186),100,'Action(Left)','Action(Select)')
				elif count >=5: systemcurrentcontrol = findin_systemcurrentcontrol("0",localize(12321),100,'Action(Left)','Action(Select)')
				if count == 1: printpoint = printpoint + "J"
				if count == 10: printpoint = printpoint + "9"'''

	if not "9" in printpoint:
		dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
		controlhasfocus28 = xbmc.getCondVisibility('Control.HasFocus(28)')
		count = 0
		while count < 10 and not controlhasfocus28 and dialogcontentsettingsW and not "9" in printpoint and not xbmc.abortRequested:
			'''------------------------------
			---controlhasfocus28-------------
			------------------------------'''
			count += 1
			dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
			controlhasfocus28 = findin_controlhasfocus("0",28,400,'Control.SetFocus(28)','Action(Select)')
			if count == 1: printpoint = printpoint + "J"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
		
	'''---------------------------'''
	return printpoint
	
def doFix_100M(printpoint, custom):
	systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
	xbmc.sleep(1000)
	dialogyesnoW = xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)')
	if dialogyesnoW:
		controlhasfocus11 = xbmc.getCondVisibility('Control.HasFocus(11)')
		count = 0
		while count < 10 and (count == 0 or not controlhasfocus11) and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			#systemcurrentcontrol = findin_systemcurrentcontrol("0",localize(107),100,'Action(Down)','Action(Select)')
			controlhasfocus11 = findin_controlhasfocus("0",11,100,'Action(Down)','Action(Select)')
			if count == 1: printpoint = printpoint + "M"
			if count == 10: printpoint = printpoint + "9"
			'''---------------------------'''
		xbmc.sleep(1000)
		dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
		count = 0
		count2 = 0
		while count < 500 and dialogprogressW and count2 > -2 and not "9" in printpoint and not xbmc.abortRequested:
			count += 1
			xbmc.sleep(1000)
			dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
			xbmc.sleep(1000)
			if count == 1:
				printpoint = printpoint + "N"
				notification_common(custom)
			if not dialogprogressW: count2 += -1
			elif count2 < 0: count2 += 1
			if count == 500:
				printpoint = printpoint + "9"
				extra = extra + "error_count=500"
				'''---------------------------'''
			
	'''---------------------------'''
	return printpoint