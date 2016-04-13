# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, os, sys, subprocess, random

from variables import *
from shared_modules import *

def mode0(admin, name, printpoint):
	'''test'''
	pass
	#xbmc.executebuiltin('RunPlugin(resource.images.weathericons.outline)')
	#installaddon('resource.images.weathericons.outline')
	#installaddon('resource.images.weatherfanart.single')
	
	#DownloadFile('asd', 'asd', 'qwe', 'zxc', silent=False, percentinfo="")
	
def mode5(value, admin, name, printpoint):
	'''startup'''
	
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
	
	if xbmc.getSkinDir() == 'skin.featherence':
		mode215('_',admin,'','')
		setsetting_custom1('script.featherence.service','Skin_UpdateLog',"true")
		Skin_UpdateLog = 'true'
		xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=23&value=)')
		setSkin_Update(admin, datenowS, Skin_Version, Skin_UpdateDate, Skin_UpdateLog)
		
		#installaddon('resource.images.weathericons.outline')
		#installaddon('resource.images.weatherfanart.single')
		#xbmc.executebuiltin('RunPlugin(resource.images.weathericons.outline)')
	
def mode8(admin, name, printpoint):
	'''------------------------------
	---SMART-SUBTITLE-SEARCH---------
	------------------------------'''
	input = xbmc.getInfoLabel('Window(home).Property(VideoPlayer.Title)')
	if input == "":
		input = xbmc.getInfoLabel('VideoPlayer.Title')
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
						if container120listitemlabel2 == property_dialogsubtitles2: notification('$LOCALIZE[31858]',property_dialogsubtitles2,"",3000)
						elif container120listitemlabel2 in subL: notification('$LOCALIZE[31859]',property_dialogsubtitles2,"",3000)
						
						tip = "false"
						'''---------------------------'''
				
			elif controlhasfocus150 and container120numitems == 0:
				count2 += 1
				
				if countidle >= 1 and count2 == 1:
					'''------------------------------
					---LOOKING-FOR-SUBTITLE----------
					------------------------------'''
					notification('$LOCALIZE[31862]',"","",4000)
					'''---------------------------'''
				
				elif countidle > 3 and count2 == 10 and systemcurrentcontrol == controlgetlabel100:
					'''------------------------------
					---REFRESH-----------------------
					------------------------------'''
					if controlgetlabel100 == "Subtitle.co.il": xbmc.sleep(1000)
					notification('$LOCALIZE[31861]',"","",2000)
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
					notification('$LOCALIZE[31860]',"","",2000)
					if controlgetlabel100 in listL: listL.remove(controlgetlabel100) #listL = 
					
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,40,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,100,'Action(Down)','')
					systemcurrentcontrol = findin_systemcurrentcontrol("2",listL,200,'Action(Down)','Action(Select)')
					
					count2 = 0
					'''---------------------------'''
		
		dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
		if dialogsubtitlesW:
			xbmc.sleep(1000)
			'''---------------------------'''
			count += 1
			if systemidle1: countidle += 1
			else: countidle = 0
			'''---------------------------'''
	
	if xbmc.getCondVisibility('System.IdleTime(1)') and not xbmc.getCondVisibility('System.IdleTime(7)'):
		'''------------------------------
		---SET-NEW-SUBTITLE--------------
		------------------------------'''
		setProperty('TEMP2', localize(24110), type="home")
		property_dialogsubtitles = xbmc.getInfoLabel('Window(home).Property(DialogSubtitles)')
		if property_dialogsubtitles != "": setSubHisotry(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10, subL)
		if property_subtitleservice != controlgetlabel100 and controlgetlabel100 != "": setProperty('Subtitle_Service', controlgetlabel100, type="home")
		'''---------------------------'''
		
	#if dialogsubtitlesW: xbmc.executebuiltin('Dialog.Close(subtitlesearch)')
	setProperty('DialogSubtitles', "", type="home")
	setProperty('TEMP2', "", type="home")
	
	if xbmc.getCondVisibility('Player.Paused'): xbmc.executebuiltin('Action(Play)')
	'''---------------------------'''
	
	setProperty('DialogSubtitles',"",type="home")
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "count/2" + space2 + str(count) + space4 + str(count2) + space + "countidle" + space2 + str(countidle) + space + "controlgetlabel100" + space2 + str(controlgetlabel100) + space + "controlhasfocus120" + space2 + str(controlhasfocus120) + space + "controlhasfocus150" + space2 + str(controlhasfocus150) + space + "container120numitems/2" + space2 + str(container120numitems) + space4 + str(container120numitems2) + newline + "listL" + space2 + str(listL) + space + "systemcurrentcontrol" + space2 + str(systemcurrentcontrol) + space + space + "container120listitemlabel2" + space2 + str(container120listitemlabel2) + space + "subL" + space2 + str(subL) + space + "playerpaused" + space2 + str(playerpaused)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

def setSubHisotry(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10, subL):
	if property_dialogsubtitles != "" and not property_dialogsubtitles in subL:
		for i in range(1,11):
			if xbmc.getInfoLabel('Window(home).Property(DialogSubtitlesNA'+str(i)+')') == "":
				setProperty('DialogSubtitlesNA' +str(i), property_dialogsubtitles, type="home")
				break
	
	xbmc.sleep(1000)
	setCurrent_Subtitle(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10, subL)
	'''---------------------------'''
	
def setCurrent_Subtitle(admin, property_dialogsubtitles, property_dialogsubtitles2, property_dialogsubtitlesna1, property_dialogsubtitlesna2, property_dialogsubtitlesna3, property_dialogsubtitlesna4, property_dialogsubtitlesna5, property_dialogsubtitlesna6, property_dialogsubtitlesna7, property_dialogsubtitlesna8, property_dialogsubtitlesna9, property_dialogsubtitlesna10, subL):
	setProperty('DialogSubtitles2', property_dialogsubtitles, type="home")
	'''---------------------------'''

def ClearSubHisotry():
	setProperty('DialogSubtitles',"",type="home")
	setProperty('DialogSubtitles2',"",type="home")
	for i in range(1,11):
		setProperty('DialogSubtitlesNA'+str(i),"",type="home")
			
def setPlayerInfo(admin):
	type = None
	playertitle = xbmc.getInfoLabel('Player.Title')
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
			else: input = playertitle
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
					pass #printpoint = printpoint + "5"
		
		ClearSubHisotry()
		setProperty('mode10', "", type="home")
		setProperty('VideoPlayer.Title', "", type="home")
		if '5' in printpoint:
			'''refresh widget'''
			xbmc.sleep(3000)
			xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=23)')

def mode22(header, message, nolabel, yeslabel, skinstring, type='video'):
	skinstring_ = xbmc.getInfoLabel('Skin.String('+skinstring+')')
	returned = dialogyesno(header, message, nolabel=nolabel, yeslabel=yeslabel)
	if returned == 'ok': z = 0
	else: z = 1
	returned = setPath(z,type)
	notification(returned,skinstring,'',4000)
	if returned != "":
		if returned != skinstring_: setSkinSetting('0',skinstring,returned)
		else:
			returned2 = dialogyesno('Remove Current Path?',skinstring)
			if returned2 == 'ok': setSkinSetting('0',skinstring,"")
			'''---------------------------'''
			
def CheckExtensions(x, mask='video'):
	name = 'CheckExtensions' ; printpoint = "" ; returned = ""
	if mask =='video': list = ['mp4', 'mov', 'avi']
	elif mask =='picture': list = []
	elif mask =='music': list = ['mp3', 'flac', 'wav', 'm3u']
	else: list = []
	
	extension = os.path.splitext(x)[1][1:].strip().lower()
	if extension in list:
		returned = 'ok'
	
	text = 'mask' + space2 + str(mask) + newline + \
	'x' + space2 + str(x) + newline + \
	'list' + space2 + str(list) + newline + \
	'extension' + space2 + str(extension) + newline + \
	'returned' + space2 + str(returned)
	
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	return returned

def CreatePL2(x, type, playlist, level, levelmax):
	name = 'CreatePL2' ; printpoint = "" ; x2 = ""
	if os.path.isdir(x):
		for x2 in os.listdir(x):
			x2 = to_utf8(x2)
			x2 = os.path.join(x, x2)
			if os.path.isdir(x2) and level <= levelmax:
				playlist = CreatePL2(x + x2, type, playlist, level + 1, levelmax)
			else:
				returned = CheckExtensions(x2, type)
				if returned == 'ok': playlist.append(x2)
	else:
		returned = CheckExtensions(x, type)
		if returned == 'ok': playlist.append(x)
	
	text = 'level' + space2 + str(level) + space + 'levelmax' + space2 + str(levelmax) + newline + \
	'x' + space2 + str(x) + newline + \
	'x2' + space2 + str(x2) + newline + \
	'playlist' + space2 + str(playlist)
	
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	return playlist
	
def CreatePL(path, type='video', levelmax=10):
	name = 'CreatePL' ; printpoint = "" ; extra = "" ; notexistsL= []
	if type == 'music': pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
	else: pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	
	pl.clear()
	playlist = []
	for x in os.listdir(path):
		x = os.path.join(path, x)
		x = to_utf8(x)
		if os.path.exists(x):
			playlist = CreatePL2(x, type, playlist, 0, levelmax)
		else: notexistsL.append(x)
		
	if playlist != []:
		random.shuffle(playlist)
		for x in playlist:
			pl.add(x)
			extra = extra + newline + 'x' + space2 + str(x)
		xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(pl)
	
	text = 'type' + space2 + str(type) + newline + \
	'path' + space2 + str(path) + newline + \
	'pl' + space2 + str(pl) + newline + \
	'playlist' + space2 + str(playlist) + newline + \
	'notexistsL' + space2 + str(notexistsL) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
		
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

	returned, value2 = dialogselect(addonString_servicefeatherence(32423).encode('utf-8'),list,0)

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
		extra = extra + newline + 'y' + space2 + str(y)
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
	
def mode30(input, header, option, action, set1, addon, name, printpoint):
	'''------------------------------
	---Dialog-Keyboard-Skin----------
	------------------------------'''
	if action != "":
		'''same time action (pre)'''
		xbmc.executebuiltin('AlarmClock(mode30,'+action+',00:01,silent)')
	try: option += 1
	except: option = 0
	dialogkeyboard(input, header, option, "", set1=set1, addon=addon, force=True)
	
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
		
		returned = dialogyesno(str(name), addonString_servicefeatherence(32423).encode('utf-8'), nolabel=nolabel, yeslabel=yeslabel)
		
		if returned != 'skip': text = listitemfolderpath ; printpoint = printpoint + '1'
		else: text = containerfolderpath ; printpoint = printpoint + '2'
		
		if text != "":
			printpoint = printpoint + '3'
			text = text.replace('&amp;','&')
			text = text.replace('&quot;',"")
			
			if '1' in printpoint: text = "list.append('&custom4=" + text + "')"
			elif '2' in printpoint: text = "list.append('&custom8=" + text + "')"
		
		if listitemthumb != "":
			text = text + newline + str(listitemthumb)
		
		dest = featherenceservice_addondata_path + "Container.FolderPath" + ".txt"
		write_to_file(dest, str(text), append=False, silent=True, utf8=False)
		notification(addonString(32130).encode('utf-8'),dest,'',2000)
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
		ReloadSkin(admin,force=False)
		#ReloadSkin(admin)
	elif value == '6':
		custom1170W_ = xbmc.getCondVisibility('Window.IsVisible(Custom1170.xml)')
		custom1173W_ = xbmc.getCondVisibility('Window.IsVisible(Custom1173.xml)')
		if custom1170W_: xbmc.executebuiltin('Dialog.Close(1170)')
		elif custom1173W_: xbmc.executebuiltin('Dialog.Close(1173)')
		
		xbmc.executebuiltin('Action(Close)')
		xbmc.executebuiltin('ActivateWindow(1117)') ; xbmc.sleep(1000)
		
		
		count = 0
		property_buttonid = xbmc.getInfoLabel('Window(home).Property(Button.ID)') #DYNAMIC
		property_buttonid_ = xbmc.getInfoLabel('Window(home).Property(Button.ID_)') #BASE
		while count < 20 and property_buttonid == "" and property_buttonid_ == "" and not xbmc.abortRequested:
			xbmc.sleep(50)
			property_buttonid = xbmc.getInfoLabel('Window(home).Property(Button.ID)') #DYNAMIC
			property_buttonid_ = xbmc.getInfoLabel('Window(home).Property(Button.ID_)') #BASE
			count += 1
		if count < 20:
			xbmc.executebuiltin('ActivateWindow(1173)')
			custom1173W = xbmc.getCondVisibility('Window.IsVisible(Custom1173.xml)')
			while count < 20 and not custom1173W and not xbmc.abortRequested:
				xbmc.sleep(50)
				custom1173W = xbmc.getCondVisibility('Window.IsVisible(Custom1173.xml)')
				count += 1
			if custom1173W:
				xbmc.executebuiltin('Action(Down)')
		
		setProperty('TEMP', '', type="home")
		
	elif value == '40':
		addon = 'plugin.video.featherence.kids'
		if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
			dialogok(addonString_servicefeatherence(32085).encode('utf-8'),addonString_servicefeatherence(32081).encode('utf-8'),"",addonString_servicefeatherence(32108).encode('utf-8'),line1c="yellow")
			General_Language2 = xbmcaddon.Addon(addon).getSetting('General_Language2') ; General_Language2 = str(General_Language2)
			dialogok(addonString_servicefeatherence(32086).encode('utf-8') % (General_Language2),addonString_servicefeatherence(32087).encode('utf-8'),"",addonString_servicefeatherence(32088).encode('utf-8'),line1c="yellow")
		
		
def mode40(value, admin, name, printpoint):
	'''------------------------------
	---Reset-Skin-Settings-----------
	------------------------------'''
	extra2 = "" ; TypeError = ""
	if value == '0': printpoint = printpoint + '1'
	elif value == '1':
		returned = dialogyesno(localize(31821) , localize(31822))
		if returned == 'ok': printpoint = printpoint + '1' ; xbmc.executebuiltin('Dialog.Close(1173)')
	
	if printpoint == '1':
		'''------------------------------
		---DELETE-USER-FILES-------------
		------------------------------'''
	
	if printpoint == '1':
		xbmc.executebuiltin('Skin.ResetSettings') ; xbmc.sleep(500)
		Custom1000(name,1,addonString_servicefeatherence(32131).encode('utf-8'),30) #This action may take a while.. be patient!
		playerhasmedia = xbmc.getCondVisibility('Player.HasMedia')
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
	if systemplatformandroid: pass
	elif systemplatformwindows: pass
	elif systemplatformlinux and xbmc.getCondVisibility('System.HasAddon(service.openelec.settings)'): xbmc.executebuiltin('RunScript(service.openelec.settings)')
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
						returned, value = dialogselect(addonString_servicefeatherence(32423).encode('utf-8'),list,0)
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
			dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
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
		installaddon(addon, update=True)
	
	text = "input" + space2 + input + newline + \
	"INFO" + space2 + "listitemlabel" + space2 + listitemlabel + newline + "listitemtvshowtitle" + space2 + listitemtvshowtitle + newline + \
	"listitemtitle" + space2 + listitemtitle + newline + "listitemdbid" + space2 + listitemdbid + newline + \
	'listitemseason' + space2 + str(listitemseason) + newline + \
	"containerfolderpath" + space2 + containerfolderpath + newline + "property_temp" + space2 + property_temp + space + "property_temp_" + space2 + str(property_temp_) + newline + \
	"listitemdirector" + space2 + listitemdirector + newline + \
	"listitemwriter" + space2 + listitemwriter
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
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
		returned, value2 = dialogselect(addonString_servicefeatherence(32423).encode('utf-8'),list,0)
	
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
	libraryisscanningvideo = xbmc.getCondVisibility('Library.IsScanningVideo')
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
	localize(31827) + space + "(" + localize(80,addon='script.featherence.service') + ")", localize(31827) + space + localize(590) + space + "(" + localize(80,addon='script.featherence.service') + ")", \
	localize(31827) + space + "(" + localize(593) + ")", localize(31827) + space + localize(590) + space + "(" + localize(593) + ")", \
	localize(10035) + space + localize(31849) + space + "(" + localize(593) + ")", localize(10035) + space + localize(31849) + space + localize(590) + space + "(" + localize(593) + ")", \
	localize(10035) + space + "(" + localize(31825) + ")"]
	
	if value == "" or container50hasfocus390:
		returned, value_ = dialogselect(addonString_servicefeatherence(32423).encode('utf-8'),list,0)
		
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
		xbmc.executebuiltin('SetProperty(1000comment,'+addonString_servicefeatherence(32131).encode('utf-8')+',home)')
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
					setSkinSetting('0','background'+x,str(backgroundT.get('background'+y)))
					
					#extra = extra + newline + label_T.get('label'+y)	
					#extra = extra + newline + 'label_' + space2 + label_
					#extra = extra + newline + action_T.get('action'+y)
					#extra = extra + newline + icon_T.get('icon'+y)
				else: printpoint = printpoint + "9" ; break
				
				extra2 = extra2 + newline + "i" + space2 + str(i) + space + "x" + space2 + str(x) + space + "y" + space2 + str(y) + space + "y2" + space2 + str(y2) + space
	#dp.close
	if "9" in printpoint: notification(localize(257) + space2 + '209', '', '', 2000)
	else:
		pass
		#ReloadSkin(admin)
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
	if not int(property_buttonid_) > 0: printpoint = printpoint + "1" ; notification(localize(257) + space2 + '211', "", "", 1000)
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

					
		if y == "": printpoint = printpoint + "9" ; notification(addonString_servicefeatherence(32132).encode('utf-8'),addonString_servicefeatherence(32133).encode('utf-8'),"",2000) #Cannot create new buttons, Delete some first!
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
			extra2 = extra2 + newline + addonString_servicefeatherence(32134).encode('utf-8') + space2 + str(property_buttonname2) + space + "(" + str(property_buttonid) + ")" #This action will also reset
		
		else:
			y = 'Remove item'
			x = property_buttonid_
			two = 1
			
	except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "9F"
	
	if not '9' in printpoint:
		if '0' in value:
			'''main menu item'''
			printpoint = printpoint + "0"
			xbmc.sleep(100) ; returned = dialogyesno(y + space2 + str(property_buttonname), localize(19194) + extra2)
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
				
			xbmc.sleep(100) ; returned = dialogyesno(y + space2 + str(property_subbuttonname), localize(19194))
			if returned == 'skip': printpoint = printpoint + "8"
			else:
				setSkinSetting('1','off' + x,"false")
				if not '_90' in property_subbuttonid_ and not 'B' in value: setSkinSetting('0','label' + x,"")
				else: setSkinSetting('0','label' + x,"...")
				#setSkinSetting('0','id' + x,"")
				setSkinSetting('0','icon' + x,"")
				setSkinSetting('0','action' + x,"")
				setSkinSetting('0','background' + x,"")
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

def mode214(value, admin, name, printpoint):
	text = "value" + space2 + str(value)
	
	if value == '0':
		returned = dialogkeyboard(property_buttonname,addonString_servicefeatherence(32110).encode('utf-8'),0,"",'label'+property_buttonid_,"")
		if returned != 'skip':
			if returned == "": setSkinSetting('0','label'+property_buttonid_, '...')
	
	if value == '1':
		returned = dialogkeyboard(property_subbuttonname,addonString_servicefeatherence(32109).encode('utf-8'),0,"",'label'+property_subbuttonid_,"")
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
		
		returned = dialogkeyboard(value2,addonString_servicefeatherence(32111).encode('utf-8'),0,"","","")
		if returned != 'skip':
			if returned != "":
				returned_len = len(returned) ; returned1 = returned[:2]
				if returned1 != "ff":
					if returned_len == 8: returned = returned.replace(returned1,"ff",1)
					elif returned_len == 7: returned = 'f' + returned
					elif returned_len == 6: returned = 'ff' + returned
				
				setProperty('SelectedColor', str(returned), type="home")
				notification(addonString_servicefeatherence(32135).encode('utf-8'), str(returned), '', 1000) #New color selected!
	
		text = text + newline + 'returned' + space2 + str(returned) + space + 'returned_len' + space2 + str(returned_len) + space + 'returned1' + space2 + str(returned1) + newline + \
		'path' + space2 + str(path) + newline + \
		'property_selectedcolor' + space2 + str(property_selectedcolor) + newline + \
		'currentbuttoncolor' + space2 + str(currentbuttoncolor) + newline + \
		'value2' + space2 + str(value2)

	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def mode215(value, admin, name, printpoint):
	from variables2 import *
	extra2 = "" ; id = ""
	exe = printlog(title="test", printpoint="", text="", level=0, option="")
	
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
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(Videos,MovieTitles,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/movies.png')		
			'''---------------------------'''
	
	'''סדרות'''
	if value != "":
		'''ראשי'''
		x = '91' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(20343))
			
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(VideoLibrary,TVShowTitles,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/tvshows.png')
			'''---------------------------'''

	'''ערוצי טלוויזיה'''
	if value != "":
		'''ראשי'''
		x = '92' ; id = idT2.get(x)
		if id != "" and id != None:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(19023))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(TVChannels)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/LiveTV.png')
			'''---------------------------'''
	
	'''ילדים'''
	if value != "":
		'''ראשי'''
		x = '93' ; id = idT2.get(x) ; background = backgroundT.get('icon'+x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(31814))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(10025,plugin://plugin.video.featherence.kids,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/kids.png')
			'''---------------------------'''	
			
	'''מוזיקה'''
	if value != "":
		'''ראשי'''
		x = '94' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(2))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(10025,plugin://plugin.video.featherence.music,return)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/music.png')
			'''---------------------------'''
	
	'''מעודפים'''
	if value != "":
		'''ראשי'''
		x = '95' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(1036))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(134)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/star.png')
			'''---------------------------'''	
	
	'''תמונות'''
	if value != "":
		'''ראשי'''
		x = '96' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(1))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(Pictures)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/pictures.png')
			'''---------------------------'''
	
	'''מזג אוויר'''
	if value != "":
		'''ראשי'''
		x = '97' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,localize(8))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(MyWeather.xml)')
			if icon == "" or value == 'RESET': setSkinSetting('0','icon'+id,'special://home/addons/script.featherence.service/resources/icons/weather.png')
			'''---------------------------'''
			
	''''''
	if value != "":
		'''ראשי'''
		x = '98' ; id = idT2.get(x)
		if id != "" and id != None and ( systemplatformwindows or systemplatformlinux and xbmc.getCondVisibility('System.HasAddon(service.openelec.settings)') ):
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			setSkinSetting('0','label'+id,"")
			setSkinSetting('0','action'+id,'')
			setSkinSetting('0','icon'+id,'')
			'''---------------------------'''	

	'''דוקו'''
	if value != "":
		'''ראשי'''
		x = '99' ; id = idT2.get(x)
		if id != "" and id != None and 1 + 1 == 2:	
			label = labelT.get('label'+str(id)) ; icon = iconT.get('icon'+str(id))
			if label == "" or label == "..." or value == 'RESET' or value == 'LABEL': setSkinSetting('0','label'+id,addonString(32803).encode('utf-8'))
			if not defaultactionbuttons: setSkinSetting('0','action'+id,'ActivateWindow(10025,plugin://plugin.video.featherence.docu,return)')
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
		dialogfullscreeninfoW = xbmc.getCondVisibility('Window.IsVisible(DialogFullScreenInfo.xml)')
		dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
		myweatherW = xbmc.getCondVisibility('Window.IsVisible(MyWeather.xml)')
		playerpaused = xbmc.getCondVisibility('Player.Paused')
		if dialogfullscreeninfoW and playerpaused:
			message = message + newline + "VideoPlayer.Duration" + space2 + xbmc.getInfoLabel('VideoPlayer.Duration')
			message = message + newline + "TopVideoInformation1" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation1)')
			message = message + newline + "VideoPlayer.Year" + space2 + xbmc.getInfoLabel('VideoPlayer.Year')
			message = message + newline + "TopVideoInformation2" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation2)')
			message = message + newline + "VideoPlayer.Rating" + space2 + xbmc.getInfoLabel('VideoPlayer.Rating')
			message = message + newline + "TopVideoInformation3" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation3)')
			message = message + newline + "VideoPlayer.Plot" + space2 + xbmc.getInfoLabel('VideoPlayer.Plot')
			message = message + newline + "TopVideoInformation5" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation5)')
			
			message = message + newline + "VideoPlayer.Genre" + space2 + xbmc.getInfoLabel('VideoPlayer.Genre')
			message = message + newline + "TopVideoInformation6" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation6)')
			message = message + newline + "VideoPlayer.Tagline" + space2 + xbmc.getInfoLabel('VideoPlayer.Tagline')
			message = message + newline + "TopVideoInformation7" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation7)')
			message = message + newline + "VideoPlayer.Title" + space2 + xbmc.getInfoLabel('VideoPlayer.Title')
			message = message + newline + "TopVideoInformation8" + space2 + xbmc.getInfoLabel('Window(home).Property(TopVideoInformation8)')
			
		elif myweatherW:
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
			#message = message + newline + "ListItem.Property(id)" + space2 + xbmc.getInfoLabel('Container(9000).ListItemNoWrap(0).Property(id)')
			#message = message + newline + "ListItem.Property(id)" + space2 + xbmc.getInfoLabel('ListItem.Property(id)')
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
			message = message + newline + "HomeLastPos" + space2 + xbmc.getInfoLabel('Window(home).Property(HomeLastPos)')
			message = message + newline + "HomeLastPos2" + space2 + xbmc.getInfoLabel('Window(home).Property(HomeLastPos2)')
			message = message + newline + '---------------------------'
			message = message + newline + "SelectedColor" + space2 + xbmc.getInfoLabel('Window(home).Property(SelectedColor)')
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
			message = message + newline + "ListItem.Property(TotalEpisodes)" + space2 + str(xbmc.getInfoLabel('ListItem.Property(TotalEpisodes)')) #CUSTOM TEST
			
			

		header = name
		diaogtextviewer(header,message)
							
def mode231(value, admin, name, printpoint):
	'''------------------------------
	---INSTALL-ADDON-----------------
	------------------------------'''
	notification_common("24")
	installaddon(value, update=True)
	'''---------------------------'''

def mode232(value, admin, name, printpoint):
	'''------------------------------
	---ACTION-BUTTON-----------------
	------------------------------'''
	id1 = "" ; id2 = "" ; extra = "" ; TypeError = ""
	if printpoint != "": printpoint = printpoint + "_"
	
	if not os.path.exists(addons_path + 'script.module.unidecode'):
		installaddon('script.module.unidecode', update=True)
	if not xbmc.getCondVisibility('System.HasAddon(script.skinshortcuts)'):
		addon1 = installaddon('script.skinshortcuts', update=True)
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
			if not xbmc.getInfoLabel('Skin.HasSetting(Action_Thumbnail)'):
				Action_Thumbnail = '&skinThumbnail=icon'+id1
				Action_Label = '&skinLabel=label'+id1
			else:
				Action_Thumbnail = ""
				Action_Label = ""
			
			if custom1175W and not custom1138W:
				'''Main Action'''
				printpoint = printpoint + "x1"
				xbmc.executebuiltin('RunScript(script.skinshortcuts,type=shortcuts&custom=True&showNone=True&skinAction=action'+id1+'&skinList=[skinList]&skinType=[skinType]'+Action_Thumbnail+Action_Label+')')
			elif custom1138W:	
				'''Sub Action'''
				printpoint = printpoint + "x2"
				xbmc.executebuiltin('RunScript(script.skinshortcuts,type=shortcuts&custom=True&showNone=True&skinAction=action'+id1+'&skinList=[skinList]&skinType=[skinType]'+Action_Thumbnail+Action_Label+')')
				'''---------------------------'''
			else: printpoint = printpoint + "8"	
			
			if "x" in printpoint:
				'''wait'''
				xbmc.sleep(5000)
				dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
				dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
				while (dialogselectW or dialogprogressW) and not xbmc.abortRequested:
					xbmc.sleep(1000)
					dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
					dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
					'''---------------------------'''
				xbmc.sleep(500) ; xlabel = xbmc.getInfoLabel('Skin.String(label'+id1+')')
				if xlabel == "":
					setSkinSetting('0','label'+id1,'...')
					if 'x1' in printpoint and not '_' in id1: setSkinSetting('0','label'+id1,'...')
				else:
					if 'x1' in printpoint and not '_' in id1: setSkinSetting('0','label'+id1,str(xlabel))
				
				xicon = xbmc.getInfoLabel('Skin.String(icon'+id1+')')
				x, x_ = TranslatePath(xicon, filename=True, urlcheck_=False)
				setSkinSetting('0','icon'+id1,x_)
					
	text = "value" + space2 + str(value) + space + "property_buttonid" + space2 + str(property_buttonid) + newline + \
	"id1" + space2 + str(id1) + space + "id2" + space2 + str(id2) + newline + \
	extra
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
			
def mode233(value, admin, name, printpoint):
	printpoint = "" ; returned_ = ""
	x = "" ; y = property_buttonid_ ; path = "" ; x2_ = ""
	customiconspath = to_unicode(xbmc.getInfoLabel('Skin.String(CustomIconsPath)'))
	custombackgroundspath = to_unicode(xbmc.getInfoLabel('Skin.String(CustomBackgroundsPath)'))
	property_temp2 = xbmc.getInfoLabel('Window(home).Property(TEMP2)')
	
	if '0' in value:
		printpoint = printpoint + '0'
		y = property_subbuttonid_
		value = value.replace('0',"",1)
	
	if '1' in value:
		'''Add-Fanart'''
		name = localize(20441)
		x = 'background'
		if not '0' in printpoint: y = property_buttonid
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
		returned = dialogyesno(str(name), addonString_servicefeatherence(32423).encode('utf-8'), nolabel=nolabel, yeslabel=yeslabel)
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
					notification(localize(2102, s=[addonString_servicefeatherence(32436).encode('utf-8')]), addonString_servicefeatherence(32801).encode('utf-8') + space + '..', "", 2000)
					header = localize(2102, s=[addonString_servicefeatherence(32436).encode('utf-8')]) #"URL Error"
					message = addonString_servicefeatherence(32802).encode('utf-8') + space2 + newline + '[B]' + str(value) + '[/B]'
					diaogtextviewer(header,message)
				else:
					setSkinSetting('0',x+y,str(url))
		else:
			printpoint = printpoint + '3'
			
			'''local'''
			if '1' in value:
				if xbmc.getCondVisibility('Skin.HasSetting(MultiFanart)'):
					returned = dialogyesno(str(name), addonString_servicefeatherence(32423).encode('utf-8'), nolabel=localize(20428), yeslabel=addonString_servicefeatherence(32112).encode('utf-8'))
					if returned == 'ok': type = 0
					else: type = 2
				else: type = 2
				printpoint = printpoint + '4'
				
				x_ = xbmc.getInfoLabel('Skin.String(background'+y+')')
				x2, x2_ = TranslatePath(x_, filename=False)
				
				if os.path.exists(custombackgroundspath): path = custombackgroundspath
				elif os.path.exists(x2_): path = x2_
				elif os.path.exists(x2): path = x2
				
				else: path = featherenceserviceicons_path_
				#xbmc.executebuiltin('Skin.SetImage(background'+y+',,'+path+')')
				returned_ = setPath(type=type,mask="pic", folderpath=path, original=False) ; xbmc.sleep(500) ; property_temp2 = xbmc.getInfoLabel('Window(home).Property(TEMP2)')
				if property_temp2 == 'ok': setSkinSetting('0','background'+y,to_unicode(returned_))
				
			elif '2' in value:
				printpoint = printpoint + '5'
				
				x_ = xbmc.getInfoLabel('Skin.String(icon'+y+')')
				x2, x2_ = TranslatePath(x_, filename=False)
				
				if os.path.exists(customiconspath): path = customiconspath
				elif os.path.exists(x2_): path = x2_
				elif os.path.exists(x2): path = x2
				
				else: path = featherenceserviceicons_path_
				#xbmc.executebuiltin('Skin.SetImage(icon'+y+',,'+path+')')
				returned_ = setPath(type=2,mask="pic", folderpath=path, original=False) ; xbmc.sleep(500) ; property_temp2 = xbmc.getInfoLabel('Window(home).Property(TEMP2)')
				if property_temp2 == 'ok': setSkinSetting('0','icon'+y,to_unicode(returned_))
			else: printpoint = printpoint + '9'
			
			setProperty('TEMP', '', type="home")
			setProperty('TEMP2', '', type="home")
			
	text = 'value' + space2 + to_utf8(value) + space + 'path' + space2 + to_utf8(path) + newline + \
	'name' + space2 + to_utf8(name) + newline + \
	'x2_' + space2 + to_utf8(x2_) + newline + \
	'customiconspath' + space2 + to_utf8(customiconspath) + newline + \
	'custombackgroundspath' + space2 + to_utf8(custombackgroundspath) + newline + \
	'property_temp2' + space2 + to_utf8(property_temp2)
	printlog(title='mode233', printpoint=printpoint, text=text, level=0, option="")

def mode235(value, admin, name, printpoint):
	'''------------------------------
	---Default-Icon/Background-------
	------------------------------'''
	setProperty('TEMP2', 'default', type="home") ; xbmc.executebuiltin('Dialog.Close(filebrowser)')
	if property_temp == 'background':
		printpoint = printpoint + '1'
		if property_subbuttonid_ != "":
			printpoint = printpoint + '4'
			setSkinSetting('0',property_temp+str(property_subbuttonid_),"")
		elif property_buttonid != "":
			setSkinSetting('0',property_temp+str(property_buttonid),"")
			printpoint = printpoint + '2'
			'''---------------------------'''
	elif property_temp == 'icon':
		printpoint = printpoint + '3'
		if property_subbuttonid_ != "":
			printpoint = printpoint + '4'
			setSkinSetting('0',property_temp+str(property_subbuttonid_),"")
		elif property_buttonid_ != "":
			printpoint = printpoint + '5'
			setSkinSetting('0',property_temp+str(property_buttonid_),"")
			mode215(property_buttonid_, admin, '', '')
	
	else: printpoint = printpoint + '6'
	
	xbmc.sleep(500)
	
	text = 'property_temp' + space2 + str(property_temp) + newline + \
	'property_buttonid' + space2 + str(property_buttonid) + newline + \
	'property_temp2' + space2 + str(property_temp2)
	
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def mode512(value):
	'''------------------------------
	---INTERNET-BUTTON---------------
	------------------------------'''
	import webbrowser
	name = 'INTERNET-BUTTON' ; TypeError = "" ; extra = "" ; printpoint = ""
	xbmc.executebuiltin('ActivateWindow(busydialog)')
	try:
		url = ""
		if value == '0': url = 'www.google.com'
		elif value == '1': url = 'www.facebook.com/groups/featherence'
		elif value == '2': url = 'www.github.com/finalmakerr/featherence'
		elif value == '3': url = 'www.youtube.com'
		elif value == '4': url = 'https://www.google.co.il/imghp?hl=iw&tab=wi' #Thumbnail
		elif value == '5': url = 'https://www.google.co.il/imghp?hl=iw&tab=wi' #Fanart
		else: url = value
		
		name = localize(443)
		
		
		

		if systemplatformwindows: webbrowser.open(url)
		elif systemplatformandroid:
			webbrowser.open(url)
			#StartAndroidActivity('start -a', 'action', 'VIEW')
			#terminal('adb shell am start -a android.intent.action.VIEW -d '+url+'','')
		elif systemplatformlinux:
			if xbmc.getCondVisibility('System.HasAddon(service.openelec.settings)'): xbmc.executebuiltin('RunAddon(browser.chromium)')
			else: webbrowser.open(url)
		elif systemplatformosx: webbrowser.open(url)
		elif systemplatformios: webbrowser.open(url)
		else: notification_common('25')

	except Exception, TypeError:
		extra = extra + 'TypeError' + space2 + str(TypeError)
	
	xbmc.sleep(1000)
	xbmc.executebuiltin('Dialog.Close(busydialog)')
	
	text = 'value' + space2 + str(value) + space + extra
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")

def videoplayertweak(admin,playerhasvideo):
	if playerhasvideo:
		
		videoplayersubtitlesenabled = xbmc.getInfoLabel('VideoPlayer.SubtitlesEnabled')
		videoplayerhassubtitles = xbmc.getInfoLabel('VideoPlayer.HasSubtitles')
				
		
		videoosd = xbmc.getCondVisibility('Window.IsVisible(VideoOSD.xml)')
		systemidle10 = xbmc.getCondVisibility('System.IdleTime(10)')
		videoosdsettingsW = xbmc.getCondVisibility('Window.IsVisible(VideoOSDSettings.xml)')
		if videoosd and systemidle10 and not videoosdsettingsW:
			'''video osd auto close'''
			subtitleosdbutton = xbmc.getCondVisibility('Control.HasFocus(703)') #subtitleosdbutton
			volumeosdbutton = xbmc.getCondVisibility('Control.HasFocus(707)') #volumeosdbutton
			dialogpvrchannelsosd = xbmc.getCondVisibility('Window.IsVisible(DialogPVRChannelsOSD.xml)')
			'''---------------------------'''
			if (not subtitleosdbutton or not videoplayerhassubtitles) and not volumeosdbutton and not dialogpvrchannelsosd:
				#if admin: xbmc.executebuiltin('Notification(Admin,videoosdauto,1000)')
				xbmc.executebuiltin('Dialog.Close(VideoOSD.xml)')
				'''---------------------------'''
			else:
				if xbmc.getCondVisibility('System.IdleTime(20)'): xbmc.executebuiltin('Dialog.Close(VideoOSD.xml)')
				'''---------------------------'''

	
def setSkin_Update(admin, datenowS, Skin_Version, Skin_UpdateDate, Skin_UpdateLog):
	'''------------------------------
	---CHECK-FOR-SKIN-UPDATE---------
	------------------------------'''
	name = 'setSkin_Update' ; printpoint = ""
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
			printpoint = printpoint + '7'
			setsetting('Skin_UpdateLog',"false")
			setSkin_UpdateLog(admin, Skin_Version2, Skin_UpdateDate, datenowS)
		else:
			printpoint = printpoint + '8'
			
	text = "Skin_Version" + space2 + str(Skin_Version) + newline + \
	"Skin_Version2" + space2 + str(Skin_Version2) + newline + \
	"datenowS" + space2 + str(datenowS) + newline + \
	"Skin_UpdateDate" + space2 + str(Skin_UpdateDate) + newline + \
	"Skin_UpdateLog" + space2 + str(Skin_UpdateLog)
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
		if number2N == 0: header = '[COLOR=yellow]' + localize(31418) + space + localize(33006) + " - " + Skin_Version + '[/COLOR]'
		elif number2N == 1: header = '[COLOR=green]' + localize(31418) + space + addonString_servicefeatherence(32410).encode('utf-8') + " - " + Skin_Version + '[/COLOR]'
		elif number2N <= 7: header = '[COLOR=purple]' + localize(31418) + space + addonString_servicefeatherence(32411).encode('utf-8') + " - " + Skin_Version + '[/COLOR]'
		elif force == True: header = addonString(32091).encode('utf-8') + space + space5 + Skin_Version
		else: header = ""
		'''---------------------------'''
		skinlog_file = os.path.join(addons_path,'skin.featherence','changelog.txt')
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
