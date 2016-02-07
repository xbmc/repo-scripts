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
value5=None
value6=None

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
try: value5=str(params["value5"])
except: value5 = ""
try: value6=str(params["value6"])
except: value6 = ""

if mode == 0:
	'''------------------------------
	---TEST--------------------------
	------------------------------'''
	name = 'TEST'
	mode0(admin, name, printpoint)
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
					dialogok(addonString(32025).encode('utf-8'), addonString(32034).encode('utf-8'), "", addonString(32035).encode('utf-8'))
				
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
	---Dialog-Keyboard-Skin----------
	------------------------------'''
	name = "Dialog-Keyboard-Skin"
	mode30(value, value2, value3, value4, value5, value6, name, printpoint)
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
								filedate = getFileAttribute(1, path + files, option="")
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
						printpoint = printpoint + 'o'
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
											x = backgroundT.get('background'+str(i)+'_'+str(i2))
											x2, x2_ = TranslatePath(x)
											formula, custommediaL, = GeneratePath('background'+str(i)+'_'+str(i2)+'=0', formula, custommediaL, x2, x2_, ignoreL=["special://home/addons/", "special://skin/"])
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
								zipname = featherenceservice_addondata_path + 'Featherence_' + str(filename).decode('utf-8')
								if custommediaL == []:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=['Featherence_.txt'], filteroff=[], level=0, append=False, ZipFullPath=False, temp=False)
								else:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=['Featherence_.txt'], filteroff=[], level=0, append=False, ZipFullPath=False, temp=True)
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=custommediaL, filteroff=[], level=3, append='End', ZipFullPath=False, temp=True)
									'''---------------------------'''
								
								if 'o' in printpoint:
									if filename != str(list2[returned2]):
										returned_ = dialogyesno('%s has been successfully saved!' % (filename), 'Would you like to remove %s save?' % (str(list2[returned2])))
										if returned_ != 'skip':
											removefiles(featherenceservice_addondata_path + 'Featherence_' + to_unicode(list2[returned2]) + '.zip')
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
					xbmc.sleep(500)
					returned_ = dialogyesno('Your current language is %s' % (systemlanguage), 'Are the buttons in %s?' % (systemlanguage))
					if returned_ == 'skip':
						xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=215&value=LABEL)')
					if filename == 'Classico Plus':
						folder_ = 'Featherence'
						path_ = os.path.join(featherenceserviceaddondata_media_path, folder_, '')
						if os.path.exists(path_):
							returned_ = dialogyesno('Extras folder found!', 'Choose YES to proceed (Optional)')
							if returned_ != 'skip':
								copyfiles(path_, home_path)
								removefiles(path_)
				    
					ReloadSkin(admin, force=True)
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
		---Add-Thumb/Fanart--------------
		------------------------------'''
		name = "Add-Thumb/Fanart"
		mode233(value, admin, name, printpoint)
		'''---------------------------'''
	
	elif mode == 235:
		'''------------------------------
		---Default-Icon/Background-------
		------------------------------'''
		name = "Default-Icon/Background"
		mode235(value, admin, name, printpoint)
		'''---------------------------'''


elif mode >= 500 and mode <= 549:
	'''------------------------------
	---HOME-BUTTONS-(1)-500-549------
	------------------------------'''
	if custom1138W: xbmc.executebuiltin('Dialog.Close(1138)')
	
	if mode == 512:
		'''------------------------------
		---INTERNET-BUTTON---------------
		------------------------------'''
		name = "INTERNET-BUTTON"
		mode512(value, admin, name, printpoint)
		'''---------------------------'''
	
else: printpoint = printpoint + "9"

'''------------------------------
---PRINT-END---------------------
------------------------------'''
if TypeError != "": print printfirst + "Default.py" + space + "TypeError" + space2 + str(TypeError)
if admin: print printfirst + "default.py_LV" + printpoint + space + "mode" + space2 + str(mode) + space + "value" + space2 + str(value)
'''---------------------------'''
	