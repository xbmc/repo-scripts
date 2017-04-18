# -*- coding: utf-8 -*-
import urllib,urllib2,sys,re,xbmcplugin,xbmcgui,xbmcaddon,xbmc,os,random
import json
from random import shuffle

from variables import *
#from modules import *
from shared_modules import *

'''plugins'''
def addDir(name, url, mode, iconimage, desc, num, viewtype, fanart=""):
	url2 = url ; printpoint = "" ; returned = "" ; extra = "" ; name2 = "" ; iconimage2 = "" ; desc2 = ""
	if '$LOCALIZE' in name or '$ADDON' in name: name = xbmc.getInfoLabel(name)
	if '$LOCALIZE' in desc or '$ADDON' in desc: desc = xbmc.getInfoLabel(desc)
	
	if num == None: num = ""
	if '&getAPIdata=' in num:
		finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(num, name, iconimage, desc, fanart, playlist=[], onlydata=True)
		if 'getAPIdata' in name and title_L != []: name = title_L[0]
		if 'getAPIdata' in iconimage and thumb_L != []: iconimage = thumb_L[0]
		if 'getAPIdata' in desc and desc_L != []: desc = desc_L[0]
		if 'getAPIdata' in fanart and fanart_L != []: fanart = fanart_L[0]
		
	if desc == None or desc == "" or desc == "None": desc = ""
	else:
		try: desc = str(desc).encode('utf-8')
		except:
			try: desc = str(desc)
			except Exception, TypeError:
				extra = extra + newline + "TypeError" + space2 + "desc Error" + space + "name" + space2 + str(name)
				desc = ""
	if iconimage == None or iconimage == "": iconimage = "" #iconimage = "None" #"None"
	
	
	if url == None or url == "": url = "None"
	else:
		returned = get_types(url)
		url_ = []
		if 'list' in returned:
			printpoint = printpoint + '3'
			i = 0
			for x in url:
				x_ = "" ; q = ""
				if '&' in x and '=' in x:
					x_ = find_string(x, "&", '=')
					if x != x_:
						pass
					else:
						url_.append(x)
				else: q = 'skipped'
				#print 'i' + space2 + str(i) + space + 'x' + space2 + str(x) + space + 'x_' + space2 + str(x_) + space + 'q' + space2 + str(q) + space + 'url_' + space2 + str(url_)
				i += 1
			for x in url_:
				url.remove(x)
				#print 'x' + space2 + str(x) + space + 'x_' + space2 + str(x_) + space + 'url' + space2 + str(url) + space + 'url_' + space2 + str(url_)
		elif 'str' in returned:
			if '&' in url and '=' in url:
				url_ = find_string(url, "&", '=')
				if url == url_:
					printpoint = printpoint = '9s'
					
		if url == []: printpoint = printpoint + '9'
		else:
			printpoint = printpoint + '4'
			url = str(url)
	
	if name == None or name == "": name = "" #name = "None" #"None"
	else:
		try: name = name.encode('utf-8')
		except: pass
	if fanart == None: fanart = ""
	
	#if mode == 17: name = '[COLOR=green]' + name + '[/COLOR]'
	#elif mode == 5: name = '[COLOR=yellow]' + name + '[/COLOR]'
	#elif mode == 8: name = '[COLOR=white2]' + name + '[/COLOR]'
	
	if '9' in printpoint: pass
	else:
		if mode >= 100 and 1 + 1 == 3:
			#if url == "": url = "1"
			u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&desc="+urllib.quote_plus(desc)+"&num="+urllib.quote_plus(num)+"&viewtype="+str(viewtype)+"&fanart="+str(fanart)
		else:
			u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&desc="+urllib.quote_plus(desc)+"&num="+urllib.quote_plus(num)+"&viewtype="+str(viewtype)+"&fanart="+str(fanart)
		
		
		
		liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
		liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": desc} )
		try:
			if Fanart_Enable != "" and Fanart_EnableCustom != "": pass
		except:
			Fanart_Enable = "true"
			Fanart_EnableCustom = "false"
			
		fanart2 = setaddonFanart(fanart, Fanart_Enable, Fanart_EnableCustom)
		if fanart2 != "": liz.setProperty('Fanart_Image', fanart2)
			
		menu = []
		#ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
		
		text = "addonID" + space2 + str(addonID) + newline + "name" + space2 + str(name) + newline + "url " + space2 + str(url) + newline + "url2" + space2 + str(url2) + newline + "mode" + space2 + str(mode) + newline + "iconimage" + space2 + str(iconimage) + newline + "desc" + space2 + str(desc) + newline + "num" + space2 + str(num)
		printlog(title='addDir_test1', printpoint=printpoint, text=text, level=0, option="")
		
		if addonID == 'script.featherence.install':
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
		elif mode >= 100 and mode <= 139 or mode >= 10001:
			menu.append(('Set Custom Fanart', 'RunScript(script.featherence.service,,?mode=34&value='+str(addonID)+'&value2='+str(mode)+')'))
			if getsetting('Fanart_Custom'+str(mode)) != "": menu.append(('Remove Custom Fanart', 'RunScript(script.featherence.service,,?mode=35&value='+str(addonID)+'&value2='+str(mode)+')'))
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
		elif mode == 1:
			'''random'''
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''	
		elif mode == 3:
			'''search'''
			if num == 'Custom':
				menu.append(("Remove", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=31&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), 'Delete', viewtype, urllib.quote_plus(fanart)))) #Move Up
				menu.append(("Remove All", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=31&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), 'Delete All', viewtype, urllib.quote_plus(fanart)))) #Move Up
			
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			
		elif mode == 2 or mode == 4 or mode == 7:
			'''------------------------------
			---play_video/2------------------
			------------------------------'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 5:
			'''------------------------------
			---PlayMultiVideos-(list)--------
			------------------------------'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 6:
			'''------------------------------
			---ListMultiVideos-(play)--------
			------------------------------'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			'''---------------------------'''
		elif mode == 12:
			'''TEMP'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 9:
			'''------------------------------
			---View-Channel------------------
			------------------------------'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 8 or mode == 10:
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz)
			returned = ok
			'''---------------------------'''
		elif mode == 11 or mode == 15:
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 13:
			'''List Playlist'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			if '&dailymotion_pl' in url: ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			else: ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 17:
			'''------------------------------
			---TV-MODE-2---------------------
			------------------------------'''
			menu = menu_list(1, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart)
			liz.addContextMenuItems(items=menu, replaceItems=False)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			'''---------------------------'''
		elif mode == 18:
			'''------------------------------
			---TV-MODE-2+CUSTOM--------------
			------------------------------'''
			up, down = CheckMoveCustom(name, num)
			
			if up != "": menu.append(("Move Up", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=23&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num + "__" + up, viewtype, urllib.quote_plus(fanart)))) #Move Up
			if down != "": menu.append(("Move Down", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=23&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num + "__" + down, viewtype, fanart))) #Move Down
			#u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&desc="+urllib.quote_plus(desc)+"&num="+urllib.quote_plus(num)+"&viewtype="+str(viewtype)
			
			#menu.append((localize(16106), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=21&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, url, name, iconimage, desc, num, viewtype, fanart))) #Manage....
			
			menu.append((localize(16106), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=21&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Manage....
			menu.append((localize(33063), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=22&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Options....
			liz.addContextMenuItems(items=menu, replaceItems=True)
			if url == "None": ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			else: ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			'''---------------------------'''
		elif mode == 20:
			'''------------------------------
			---New-Custom-Playlist-----------
			------------------------------'''
			menu.append((localize(33063), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=22&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Options....
			liz.addContextMenuItems(items=menu, replaceItems=True)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
			returned = ok
			'''---------------------------'''
		elif mode == 21:
			'''------------------------------
			---Manage...---------------------
			------------------------------'''
			liz.addContextMenuItems(items=menu, replaceItems=True)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			'''---------------------------'''
		elif mode == 22:
			'''------------------------------
			---AdvancedCustom...-------------
			------------------------------'''
			liz.addContextMenuItems(items=menu, replaceItems=True)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			'''---------------------------'''
		elif mode == 200 or mode == 90:
			liz.addContextMenuItems(items=menu, replaceItems=True)
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
			
		else:
			ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
			returned = ok
		
		#scriptfeatherenceservice_random = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)')
		checkRandom(url)
		
	text = "name" + space2 + str(name) + newline + \
	"desc" + space2 + str(desc) + space + "addonID" + space2 + str(addonID) + newline + \
	"iconimage" + space2 + str(iconimage) + newline + \
	"num" + space2 + str(num) + newline + \
	"fanart" + space2 + str(fanart) + extra
	printlog(title='addDir', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	if not '9' in printpoint: return returned

def menu_list(custom, menu, addonID, url, name, iconimage, desc, num, viewtype, fanart):
	if '1' in str(custom):
		'''Add to favourites [Featherence]'''
		menu.append((localize(14076) + space + '[Featherence]', "XBMC.RunPlugin(plugin://%s/?url=%s&mode=24&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart)))
	
	return menu
	
def checkRandom(url):
	printpoint = "" ; i = "" ; returned = ""
	#extra = extra + newline + 'scriptfeatherenceservice_random' + space2 + str(xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)'))
	if xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)') != "":
		printpoint = printpoint + '0'
		url = CleanString2(url)
		if xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)') == "true":
			printpoint = printpoint + '1'
			i = 1
			setProperty('script.featherence.service_random', str(i), type="home")
			setProperty('script.featherence.service_randomL', "", type="home")
			for x in range(1,6):
				setProperty('script.featherence.service_random'+str(x), "", type="home")
			
		else:
			printpoint = printpoint + '2'
			i = int(xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)'))
		
		if i != "":
			if xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random'+str(i)+')') == "":
				printpoint = printpoint + '3'
				returned = str(url)
				setProperty('script.featherence.service_random'+str(i), returned, type="home")
			else:
				printpoint = printpoint + '4'
				returned = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random'+str(i)+')') + '|' + str(url)
				setProperty('script.featherence.service_random'+str(i), returned, type="home")

			if i == 5: setProperty('script.featherence.service_random', '1', type="home")
			else: setProperty('script.featherence.service_random', str(i + 1), type="home")
				
				
		text = 'i' + space2 + str(i) + newline + \
		"url" + space2 + str(url) + newline + \
		'returned' + space2 + str(returned) + newline + \
		"scriptfeatherenceservice_randomL" + space2 + str(xbmc.getInfoLabel('Window(home).Property(script.featherence.service_randomL)'))
		printlog(title='checkRandom', printpoint=printpoint, text=text, level=0, option="")
		
def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
				params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
					param[splitparams[0]]=splitparams[1]
							
	return param
	
def ListLive(url, mode, num, viewtype, fanart):
	#addDir('[COLOR=yellow]' + str79520.encode('utf-8') + '[/COLOR]',url,12,addonMediaPath + "190.png",str79526.encode('utf-8'),'1',"") #Quick-Play
	link = OPEN_URL(url)
	link=unescape(link)
	print printfirst + "link" + space2 + link
	matches1=re.compile('pe=(.*?)#',re.I+re.M+re.U+re.S).findall(link)
	#print str(matches1[0]) + '\n'
	for match in matches1 :
		#print "match=" + str(match)
		match=match+'#'
		if match.find('playlist') != 0 :
			'''------------------------------
			---url---------------------------
			------------------------------'''
			regex='name=(.*?)URL=(.*?)#'
			matches=re.compile(regex,re.I+re.M+re.U+re.S).findall(match)
			#print str(matches)
			for name,url in matches:
				thumb = "" ; description = ""
				i=name.find('thumb')
				i2=name.find('description')
				if i>0:
					thumb=name[i+6:]
					name=name[0:i]
					description = name[i2+11:]
					#print printfirst + "name" + space2 + name + space + "thumb" + space2 + thumb + space + "description" + space2 + description
		
				addDir(name, url, mode, thumb, description, num, viewtype, fanart)
		else:
			'''------------------------------
			---.plx--------------------------
			------------------------------'''
			regex='name=(.*?)URL=(.*?).plx'
			matches=re.compile(regex,re.I+re.M+re.U+re.S).findall(match)
			for name,url in matches:
				thumb=''
				i=name.find('thumb')
				i2=name.find('description')
				if i>0:
					thumb=name[i+6:]
					name=name[0:i]
					description = name[i2+11:]
				url=url+'.plx'
				if name.find('Radio') < 0 :
					addDir('[COLOR blue]'+name+'[/COLOR]',url,7,thumb,description,'1',"")
					
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "matches1" + space2 + str(matches1)
	printlog(title='ListLive', printpoint="", text=text, level=0, option="")
	'''---------------------------'''

def clean_commonsearch(x):
	y = x ; printpoint = ""
	if "commonsearch" in y:
		printpoint = printpoint + '1'
		if addonID == 'plugin.video.featherence.music':
			y = y.replace("commonsearch101", space + commonsearch101)
			y = y.replace("commonsearch102", space + commonsearch102)
			y = y.replace("commonsearch104", space + commonsearch104)
			y = y.replace("commonsearch106", space + commonsearch106)
			y = y.replace("commonsearch107", space + commonsearch107)
			y = y.replace("commonsearch108", space + commonsearch108)
			y = y.replace("commonsearch109", space + commonsearch109)
			
			y = y.replace("commonsearch111", space + commonsearch111)
			y = y.replace("commonsearch112", space + commonsearch112)
			y = y.replace("commonsearch114", space + commonsearch114)
			
		elif addonID == 'plugin.video.featherence.kids':
			y = y.replace("commonsearch101", space + commonsearch101)
		if 'commonsearch' in y:
			y = y.replace('commonsearch',"",1)
	
	count = 0
	while count < 10 and not xbmc.abortRequested:
		if count == 0:
			y = y.replace('[Search]',"")
			y = y.replace('[Video]',"")
			y = y.replace('[Playlist]',"")
			y = y.replace('[Channel]',"")
			y = y.replace('[Sdarot-TV]',"")
		elif '[COLOR=' in y:
			printpoint = printpoint + '4'
			y_ = regex_from_to(y, '[COLOR=', ']', excluding=False)
			y = y.replace(y_,"", 1)
			y = y.replace('[/COLOR]',"", 1)
			
		elif '[' in y and ']' in y:
			printpoint = printpoint + '5'
			y_ = regex_from_to(y, '[', ']', excluding=False)
			#print 'wwwoot ' + y_
			y = y.replace(y_,"", 1)
		
		elif y.count('&') > 1 and '=' in y:
			y_ = find_string(y, "&", '&')
			#print 'wwwww ' + str(y_)
			y = y.replace(y_,"",1)
			
		else: count = 40
		count += 1
	
	y = y.replace("  "," ")
	y = y.replace("[","")
	y = y.replace("]","")
	y = y.replace(" ","%20")
	y = y.replace("#","%23")
	
	text = "x" + space2 + str(x) + space + "y" + space2 + str(y)
	printlog(title='clean_commonsearch', printpoint=printpoint, text=text, level=0, option="")
	return y

def LocalSearch(mode, name, url, iconimage, desc, num, viewtype, fanart):
	printpoint = "" ; admin = xbmc.getInfoLabel('Skin.HasSetting(Admin)') ; value = "" ; url2 = ""
	url2 = read_from_file(url, silent=True, lines=True, retry=True, printpoint="", addlines='&custom_se=', createlist=False)
	text = 'url2' + space2 + str(url2)
	printlog(title='LocalSearch' + space + name, printpoint=printpoint, text=text, level=0, option="")
	TvMode2(addonID, mode, name, url2, iconimage, desc, num, viewtype, fanart)
		
def YoutubeSearch(name, url, desc, num, viewtype):
	printpoint = "" ; value = ""
	#print 'blablabla ' + str(name)
	if url == None or url == 'None': url = ""
	name = clean_commonsearch(name)
	try: name = str(name).encode('utf-8')
	except: pass
	
	if name == localize(137) or name == '-' + localize(137):
		'''search'''
		printpoint = printpoint + "1"
		x = desc
		returned = dialogkeyboard("", x, 0, '1', "", "")
		if returned != 'skip':
			printpoint = printpoint + "2"
			value = returned + space + url
			if Search_History == 'true':
				if os.path.exists(Search_History_file): printpoint = printpoint + 'A' ; append = True ; value = '\n' + value
				else: printpoint = printpoint + 'B' ; append = False
				write_to_file(Search_History_file, value, append=append, silent=True , utf8=False)
				
					
		else:
			notification_common("8")
	elif 'commonsearch' in url:
		'''commonsearch'''
		printpoint = printpoint + "3"
		url = clean_commonsearch(url)
		value = name + space + url
	else:
		printpoint = printpoint + '4'
		value = url
	
	if value != "":
		printpoint = printpoint + "7"
		value = clean_commonsearch(value)
		try: value = str(value).encode('utf-8')
		except: pass
		update_view('plugin://plugin.video.youtube/search/?q=' + value, num, viewtype)
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = 'name' + space2 + str(name) + newline + \
	"desc" + space2 + str(desc) + newline + \
	"value" + space2 + str(value) + newline + \
	"url" + space2 + str(url) + newline
	printlog(title='YoutubeSearch', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	
def ListPlaylist2(name, url, iconimage, desc, num, viewtype, fanart):
	printpoint = "" ; extra = "" ; TypeError = ""
	if '&dailymotion_pl=' in url:
		finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(url, name, iconimage, desc, fanart, playlist=[], onlydata=False)
		#except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
		x__count = 0
		for x__ in range(0,len(playlist_L)):
			x__ = '&dailymotion_id=' + str(playlist_L[x__count])
			x__ = x__.replace('plugin://plugin.video.dailymotion_com/?url=',"")
			x__ = x__.replace('&mode=playVideo',"")
			addDir(str(title_L[x__count]), str(x__), 4, str(thumb_L[x__count]), str(desc_L[x__count]), num, viewtype, fanart)
			
			x__count += 1
			print 'x__' + space2 + str(url)
		#update_view('plugin://plugin.video.dailymotion_com/?url='+url+'&mode=listVideos', num, viewtype)
	else:
		default = 'plugin://plugin.video.youtube/'
		update_view('plugin://plugin.video.youtube/playlist/' + url + '/', num, viewtype)
		'''---------------------------'''
	
def OPEN_URL(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib2.urlopen(req)
    link=response.read()
    response.close()
    '''---------------------------'''
    return link

def PlayVideos(name, mode, url, iconimage, desc, num, fanart):
	x = url
	playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
	if playerhasvideo: xbmc.executebuiltin('Action(Stop)')
	playlist = [] ; returned = ""
	pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	pl.clear()
	General_TVModeShuffle = getsetting('General_TVModeShuffle')
	
	printpoint = "" ; extra = "" ; TypeError = ""
	if 'plugin.' in num:
		if not xbmc.getCondVisibility('System.HasAddon('+ num +')') or not os.path.exists(os.path.join(addons_path, num)):
			notification_common("24")
			installaddon(admin, num, update=True)
			xbmc.sleep(2000)
	
	if '&dailymotion_id=' in url:
		if 1 + 1 == 3:
			url = url.replace("&dailymotion_id=","")
			returned = dailymotion_test(url)
		else:
			addon = "plugin.video.dailymotion_com"
			if not xbmc.getCondVisibility('System.HasAddon('+ addon +')') or not os.path.exists(os.path.join(addons_path, addon)):
				installaddonP(admin, addon) ; xbmc.sleep(1000)
				
			url = url.replace("&dailymotion_id=","")
			xbmc.executebuiltin('PlayMedia(plugin://plugin.video.dailymotion_com/?url='+url+'&mode=playVideo)')
			
			if 1 + 1 == 3:
				url = 'https://api.dailymotion.com/video/'+ url +''
				link = OPEN_URL(url)
				prms=json.loads(link)
				
				title = str(prms['title'].encode('utf-8'))#.decode('utf-8')
				id = str(prms['id'].encode('utf-8'))#.decode('utf-8')
				channel = str(prms['channel'].encode('utf-8'))#.decode('utf-8')
				#name = str(prms['feed'][u'entry'][i][ u'media$group'][u'media$title'][u'$t'].encode('utf-8')).decode('utf-8')
				finalurl='http://www.dailymotion.com/video/'+id+'_'+title+'_'+channel
				finalurl = finalurl.replace(space,"-")
				finalurl = 'http://www.dailymotion.com/video/x3bik3i_atlas-unfolded-new-york-city_music'
				print 'link :' + str(link) + newline + 'prms:' + str(prms) + newline + 'title:' + str(title) + newline + 'id' + space2 + str(id) + newline + 'finalurl' + space2 + str(finalurl)
				
	elif '&youtube_id=' in url:
		url = url.replace("&youtube_id=","")
		xbmc.executebuiltin('PlayMedia(plugin://plugin.video.youtube/play/?video_id='+ url +')')
	elif '&youtube_pl=' in url or '&dailymotion_pl=' in url:
		#xbmc.executebuiltin('PlayMedia(plugin://plugin.video.youtube/play/?playlist_id='+ url +')')
		#try:
		finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, name, iconimage, desc, fanart, playlist=playlist, onlydata=False)
		pl, playlist, printpoint = MultiVideos_play(playlist_L, pl, playlist, printpoint, General_TVModeShuffle, mode)
		#except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
		
	else: xbmc.executebuiltin('PlayMedia('+ url +')')
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "PlayVideos" + space + 'returned' + space2 + str(returned) + space + "url" + space2 + str(url)
	printlog(title='PlayVideos', printpoint="", text=text, level=0, option="")
	'''---------------------------'''
	return returned
	
def YOULink(mname, url, thumb, desc):
	if not "UKY3scPIMd8" in url or admin:
		ok=True
		url = "plugin://plugin.video.youtube/play/?video_id="+url
		#url='https://gdata.youtube.com/feeds/api/videos/'+url+'?alt=json&max-results=50' #TEST
		liz=xbmcgui.ListItem(mname, iconImage="DefaultVideo.png", thumbnailImage=thumb)
		liz.setInfo( type="Video", infoLabels={ "Title": mname, "Plot": desc } )
		liz.setProperty("IsPlayable","true")
		ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz,isFolder=False)
		text = "url" + space2 + str(url) + space + "mname" + space2 + mname
		printlog(title='YOULink', printpoint="", text=text, level=0, option="")
		return ok
		
def MultiVideos(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart):
	printpoint = "" ; i = 0 ; i2 = 0 ; extra = "" ; desc = str(desc)
	#print 'testtt ' + fanart
	pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	playlist = []
	playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
	if mode == 5 or mode == 2:
		if playerhasvideo:
			xbmc.executebuiltin('Action(Stop)')
		pl.clear()
	
	url2 = url.replace("['","")
	url2 = url2.replace("']","")
	url2 = url2.replace("'","")
	url2 = url2.replace("' ","'")
	url2 = url2.replace("'',","")
	
	url2 = url2.replace("&amp;", "&")
	
	url2 = url2.replace(" &custom_se=","&custom_se=")
	url2 = url2.replace(" &custom4=","&custom4=")
	url2 = url2.replace(" &custom8=","&custom8=")
	url2 = url2.replace(" &dailymotion_id=","&dailymotion_id=")
	url2 = url2.replace(" &dailymotion_pl=","&dailymotion_pl=")
	url2 = url2.replace(" &hotVOD=","&hotVOD=")
	url2 = url2.replace(" &sdarot=","&sdarot=")
	url2 = url2.replace(" &seretil=","&seretil=")
	url2 = url2.replace(" &wallaNew2=","&wallaNew2=")
	url2 = url2.replace(" &wallaNew=","&wallaNew=")
	
	url2 = url2.replace(" &youtube_ch=","&youtube_ch=")
	url2 = url2.replace(" &youtube_pl=","&youtube_pl=")
	url2 = url2.replace(" &youtube_id=","&youtube_id=")
	url2 = url2.replace(" &youtube_se2=","&youtube_se2=")
	url2 = url2.replace(" &youtube_se=","&youtube_se=")
	
	url2a = url2
	url2 = url2.split(',')
	if General_TVModeShuffle == "true" and mode == 5: random.shuffle(url2) ; printpoint = printpoint + "0"
		
		
	text = "url " + space2 + str(url) + newline + "url2a" + space2 + str(url2a) + newline + "url2" + space2 + str(url2)
	printlog(title='url_first_check', printpoint="", text=text, level=0, option="")
	#returned = get_types(url)
	counturl2 = 0
	for x in url2:
		x = str(x) ; finalurl = "" ; finalurlL = [] ; numOfItems2 = 0 ; name2 = ""
		x = url2[counturl2]
		if len(url2) < 2: printpoint = printpoint + 'O'
		counturl2 += 1
		text = "x" + space2 + str(x) + newline + "playlist" + space + str(playlist) + newline + "finalurl" + space2 + str(finalurl) + space + "finalurlL" + space2 + str(finalurlL)
		printlog(title='MultiVideos_test', printpoint=printpoint, text=text, level=0, option="")
		x = x.replace("[","")
		x = x.replace(",","")
		x = x.replace("'","")
		x = x.replace("]","")
		
		if '&' in x and '=' in x:
			x_ = find_string(x, "&", '=')
			if x == x_:
				printpoint = printpoint = 's' ; continue
		if '&name_=' in x:
			name2 = find_string(x, '&name_=', '&')
			x = x.replace(name2,"",1)
			name2 = name2.replace('&name_=',"",1)
			name2 = name2.replace('&',"")
			if name2 != "":
				if name2 == 'default': name2 = name
				else: name = name2
			
		if x not in playlist and x != "":
			i += 1
			if mode == 5:
				if "&custom4=" in x:
					x = x.replace("&custom4=","")
					finalurl=x
					'''---------------------------'''
				elif "&hotVOD=" in x:
					x = x.replace("&hotVOD=","")
					if "FCmmAppVideoApi_AjaxItems" in x:
						finalurl="plugin://plugin.video.hotVOD.video/?url="+x+"&mode=4"
						'''---------------------------'''
				elif "&sdarot=" in x:
					x, z, summary, mode_, series_name, season_id = sdarot_(x)
					if mode_ == 10:
						finalurl="plugin://plugin.video.sdarot.tv/?mode=4&"+x
				elif "&seretil=" in x:
					x = x.replace("&seretil=","")
					#finalurl="plugin://plugin.video.sdarot.tv/?mode=4&"+x
					'''---------------------------'''
				elif "&wallaNew=" in x:
					x = x.replace("&wallaNew=","")
					if "item_id" in x: finalurl="plugin://plugin.video.wallaNew.video/?url="+x+"&mode=10&module=wallavod"
					'''---------------------------'''
				elif "&wallaNew2=" in x:
					x = x.replace("&wallaNew2=","")
					#z = '1'
					#addDir(name + space + str(i), "plugin://plugin.video.wallaNew.video/?url="+x+"&mode="+z+"&module=nickjr", 8, iconimage, desc, num, viewtype)
					'''---------------------------'''
				elif "&youtube_ch=" in x:
					#try:
					if 1 + 1 == 2:
						finalurl, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, name, iconimage, desc, fanart, playlist=playlist, onlydata=False)
						finalurl = playlist_L
					#except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
					'''---------------------------'''
				elif "&youtube_pl=" in x:
					#x = x.replace("&youtube_pl=","")
					#try:
					if 1 + 1 == 2:
						finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, name, iconimage, desc, fanart, playlist=playlist, onlydata=False)
						finalurl = playlist_L
					#except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
					'''---------------------------'''
				elif "&youtube_id=" in x:
					x = x.replace("&youtube_id=","")
					finalurl="plugin://plugin.video.youtube/play/?video_id="+x+"&hd=1"
					'''---------------------------'''
				elif "&youtube_se2=" in x or "&youtube_se=" in x or "&custom_se=" in x:
					if 'commonsearch' in x: x = x + space + str(name)
					#try:
					if 1 + 1 == 2:
						finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, name, iconimage, desc, fanart, playlist=playlist, onlydata=False)
						finalurl = playlist_L
					#except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
					
				elif "&dailymotion_id=" in x:
					x = x.replace("&dailymotion_id=","")
					finalurl='plugin://plugin.video.dailymotion_com/?url='+x+'&mode=playVideo'
				elif "&dailymotion_pl=" in x:
					try:
						finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, playlist=playlist, onlydata=False)
						finalurl = playlist_L
					except Exception, TypeError: extra = extra + newline + "apimaster_TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "6"
				else: printpoint = printpoint + "Z"
				extra = extra + newline + str(i) + space2 + str(finalurl)
				'''---------------------------'''
				#title= str(prms['feed'][u'entry'][i][ u'media$group'][u'media$title'][u'$t'].encode('utf-8')).decode('utf-8')
				#thumb =str(prms['feed'][u'entry'][i][ u'media$group'][u'media$thumbnail'][2][u'url'])
				#description = str(prms['feed'][u'entry'][i][ u'media$group'][u'media$description'][u'$t'].encode('utf-8')).decode('utf-8')
				
				#notification(str(int(len(playlist))),'','',5000)
				pl, playlist, printpoint = MultiVideos_play(finalurl, pl, playlist, printpoint, General_TVModeShuffle, mode)
				
				if 'x' in printpoint: break
				
			elif mode == 6:
				finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L = apimaster(x, name, iconimage, desc, fanart, playlist=playlist, onlydata=True)
				#except: pass
				for y in title_L:
					if name2 != "":
						y = y.replace(y, name)
					y = y.replace(y,str(i) + '. ' + y, 1)
					
					
					
				if finalurl_ == "": pass
				elif "&custom4=" in x:
					x = x.replace("&custom4=","")
					addDir(str(i) + '.' + space + title_L[0], x, 4, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
					'''---------------------------'''
				elif "&custom8=" in x:
					x = x.replace("&custom8=","")
					addDir(str(i) + '.' + space + title_L[0], x, 8, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
					'''---------------------------'''
				elif "&dailymotion_id=" in x:
					#x = x.replace("&dailymotion_id=","")
					if 'O' in printpoint:
						PlayVideos(title_L[0], 4, x, thumb_L[0], desc_L[0], num, fanart_L[0])
						mode = 4
					else:
						addDir(str(i) + '.' + space + title_L[0], x, 4, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
						'''---------------------------'''
				elif "&dailymotion_pl=" in x:
					if 'O' in printpoint:
						ListPlaylist2(name, x, iconimage, desc, num, viewtype, fanart)
						#mode = 13
					else: addDir(str(i) + '.' + space + title_L[0], x, 17, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
				elif "&youtube_ch=" in x:
					#x = x.replace("&youtube_ch=","")
					#if "/playlists" in x: x = x.replace("/playlists","")
					if 'O' in printpoint:
						YOUList2(name, url, iconimage, desc, num, viewtype)
						mode = 9
					else: mode_ = addDir(str(i) + '.' + space + title_L[0], x, 17, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0]) #addonString(192).encode('utf-8')
					
					'''---------------------------'''
				elif "&youtube_pl=" in x:
					#x = x.replace("&youtube_pl=","")
					if 'O' in printpoint:
						ListPlaylist2(name, url, iconimage, desc, num, viewtype, fanart)
						mode = 13
					else: addDir(str(i) + '.' + space + title_L[0], x, 17, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0]) #addonString(192).encode('utf-8')
					'''---------------------------'''
				elif "&youtube_id=" in x:
					#x = x.replace("&youtube_id=","")
					addDir(str(i) + '.' + space + title_L[0], x, 4, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
					'''---------------------------'''
				elif "&youtube_se2" in x or "&youtube_se=" in x or "&custom_se=" in x:
					#try: str(name).encode('utf-8')
					#except: str(name)
					x = x.replace("&youtube_se2=","")
					x = x.replace("&youtube_se=","")
					x = x.replace("&custom_se=","")
					#x = x + space + str(name)
					#x = clean_commonsearch(x)
					#print 'testme ' + str(x)
					if 'O' in printpoint:
						YoutubeSearch(name, url, desc, num, viewtype)
						mode = 3
					else:
						addDir(str(i) + '.' + space + title_L[0], x, 3, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
				else:
					if "&wallaNew=" in x:
						x = x.replace("&wallaNew=","")
						if "item_id" in x: z = '10' ; m = 4
						elif "seriesId" in x: z = '5' ; m = 8
						elif "seasonId" in x: z = '3' ; m = 8
						elif "genreId" in x: z = '2' ; m = 8
						else: z = '10' ; m = 8
						
						addDir(str(i) + '.' + space + title_L[0] + space + '[Walla]', "plugin://plugin.video.wallaNew.video/?url="+x+"&mode="+z+"&module=wallavod", m, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
						'''---------------------------'''
					elif "&wallaNew2=" in x:
						x = x.replace("&wallaNew2=","")
						z = '1'
						addDir(str(i) + '.' + space + title_L[0] + space + '[Walla]', "plugin://plugin.video.wallaNew.video/?url="+x+"&mode="+z+"&module=nickjr", 8, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
						'''---------------------------'''
					elif "&sdarot=" in x:
						x, z, summary, mode_, series_name, season_id = sdarot_(x)
						addDir(str(i) + '.' + space + title_L[0] + space + '[Sdarot-TV]', "plugin://plugin.video.sdarot.tv/?mode="+z+summary+series_name+"&image="+thumb_L[0]+"&name="+season_id+title_L[0]+"&"+x, int(mode_), thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
					elif "&seretil=" in x:
						x = x.replace("&seretil=","")
						if "?mode=211&url=http%3a%2f%2fseretil.me" in x: name2 = '[COLOR=red]' + title_L[0] + space + str(i) + '[/COLOR]'
						else: name2 = title_L[0] + space + str(i)
						addDir(name2, "plugin://plugin.video.seretil/"+x, 8, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
						'''---------------------------'''
					elif "&hotVOD=" in x:
						x = x.replace("&hotVOD=","")
						if "TopSeriesPlayer" in x: z = '3&module=%2fCmn%2fApp%2fVideo%2fCmmAppVideoApi_AjaxItems%2f0%2c13776%2c'
						elif "FCmmAppVideoApi_AjaxItems" in x: z = '4'
						else: z = '3&module=%2fCmn%2fApp%2fVideo%2fCmmAppVideoApi_AjaxItems%2f0%2c13776%2c'
						addDir(str(i) + '.' + space + title_L[0], "plugin://plugin.video.hotVOD.video/?mode="+z+"&url="+x, 8, thumb_L[0], desc_L[0], num, viewtype, fanart_L[0])
						'''---------------------------'''	
					
					else: pass
			else: printpoint = printpoint + 'y'
		else: extra = extra + newline + 'x' + space2 + str(x) + space + 'is in playlist or empty!'
		
	if mode == 5:
		playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
		if playlist == []: notification(addonString_servicefeatherence(1).encode('utf-8'), addonString_servicefeatherence(2).encode('utf-8'), "", 2000)
		#xbmc.executebuiltin('RunScript('+addonID+'/?mode=6&name='+name+'&url='+url+'&iconimage='+str(iconimage)+'&desc='+desc+'&num='+str(num)+'&viewtype='+str(viewtype)+')')
		#MultiVideos(6, name, url, iconimage, desc, num, viewtype, fanart)
		
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "mode" + space2 + str(mode) + space + "i" + space2 + str(i) + space + newline + \
	"url " + space2 + str(url) + newline + \
	"url2" + space2 + str(url2) + newline + \
	"fanart" + space2 + str(fanart) + newline + \
	"pl" + space2 + str(pl) + space + "playlist" + space2 + str(len(playlist)) + space + str(playlist) + newline + \
	"finalurl" + space2 + str(finalurl) + space + "finalurlL" + space2 + str(finalurlL) + space + newline + extra
	printlog(title="MultiVideos", printpoint=printpoint, text=text, level=2, option="")
	'''---------------------------'''
	return mode

def MultiVideos_play(finalurl, pl, playlist, printpoint, General_TVModeShuffle, mode):
	count = 0 ; finalurlN = 0 ; printpoint2 = ""
	playlistN = int(len(playlist))
	if finalurl != "" and finalurl != []:
		printpoint2 = printpoint2 + '0'
		returned = get_types(finalurl)
		if 'list' in returned:
			printpoint2 = printpoint2 + '1'
			finalurlN = int(len(finalurl))
			if General_TVModeShuffle == "true": random.shuffle(finalurl) ; printpoint = printpoint + "0"
			
		elif 'str' in returned:
			printpoint2 = printpoint2 + '2'
			finalurlN = 1
		else: printpoint2 = printpoint2 + '9'
		
		if finalurlN > 0:
			if '1' in printpoint2:
				for y in finalurl:
					pl, playlist, printpoint = MultiVideos_play2(y, pl, playlist, printpoint)
					count += 1
					playlistN = int(len(playlist))
					if count > finalurlN: break
					elif playlistN >= 40:
						printpoint = printpoint + 'x'
						break
					elif '3' in printpoint:
						playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
						playlistlength = xbmc.getInfoLabel('Playlist.Length(video)')
						if not playerhasvideo or int(playlistlength) >= 40:
							printpoint = printpoint + 'x_'
							#print 'playlistlength' + space2 + str(playlistlength)
							break
							
			elif '2' in printpoint2:
				pl, playlist, printpoint = MultiVideos_play2(finalurl, pl, playlist, printpoint)
	
	text = 'finalurl' + space2 + str(finalurl) + newline + \
	'pl' + space2 + str(pl) + newline + \
	'playlist' + space2 + str(playlist) + newline + \
	'count' + space2 + str(count) + space + 'playlistN' + space2 + str(playlistN) + space + 'finalurlN' + space2 + str(finalurlN)
	printlog(title="MultiVideos_play", printpoint=printpoint + space + 'printpoint2' + space2 + str(printpoint2), text=text, level=0, option="")
	return pl, playlist, printpoint

def MultiVideos_play2(finalurl, pl, playlist, printpoint):
	count = 0 ; printpoint2 = "" ; numOfItems2 = 0
	
	pl.add(finalurl)
	playlist.append(finalurl)
	if '606' in printpoint or '66' in printpoint:
		notification_common('8')
		sys.exit(0)
	elif not "3" in printpoint:
		if 'plugin://' in finalurl:
			printpoint2 = printpoint2 + '3'
			plugin = regex_from_to(finalurl, 'plugin://', '/', excluding=True)
			installaddon(admin, plugin, update=True)
		xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(pl) ; xbmc.sleep(2000)
		playerhasvideo = xbmc.getCondVisibility('Player.HasVideo') ; dialogokW = xbmc.getCondVisibility('Window.IsVisible(DialogOK.xml)') ; dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)') ; dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
		while count < 20 and not playerhasvideo and not dialogokW and not xbmc.abortRequested:
			xbmc.sleep(200)
			playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
			dialogokW = xbmc.getCondVisibility('Window.IsVisible(DialogOK.xml)')
			dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
			dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
			if not dialogbusyW and not dialogprogressW: count += 2
			else: count += 1
			
		if playerhasvideo and not dialogokW: printpoint = printpoint + "3"
		else:
			dialogokW = xbmc.getCondVisibility('Window.IsVisible(DialogOK.xml)')
			if dialogokW or count == 10:
				printpoint = printpoint + '6'
				xbmc.executebuiltin('Dialog.Close(okdialog)')
				#xbmc.executebuiltin('Action(Close)') ; xbmc.sleep(100)
				x = finalurl.replace('plugin://plugin.video.youtube/play/?video_id=',"")
				x = x.replace('&hd=1',"")
				notification('Video error: ' + str(x),'Trying to play next video','',2000)
				'''---------------------------'''
			
	text = 'finalurl' + space2 + str(finalurl) + newline + \
	'pl' + space2 + str(pl) + newline + \
	'playlist' + space2 + str(playlist) + newline + \
	'count' + space2 + str(count)
	printlog(title="MultiVideos_play2", printpoint=printpoint, text=text, level=0, option="")
	return pl, playlist, printpoint
	
def sdarot_(x):
	'''get required data for &sdarot='''
	x = x.replace("&sdarot=","")
	if "episode_id=" in x: z = '4'
	elif "season_id" in x: z = '5'
	elif "series_id=" in x: z = '3'
	else: z = '2'

	if 1 + 1 == 2:
		if not "summary=" in x:
			if z == '3':
				if not "summary" in x: summary = "&summary"
				else: summary = ''
			else: summary = "&summary="
			#elif desc_ != "": summary = "&summary="+desc_
		else: summary = ''
	else: summary = ''

	if not "series_name=" in x: series_name = "&series_name="
	else: series_name = ''
	if 'series_id' in x:
		if not "season_id=" in x: season_id = "&season_id="
		else: season_id = ''
	else: season_id = ''
	
	if z == '4': mode_ = 10
	else: mode_ = 8
	
	text = 'x' + space2 + str(x) + newline + \
	'z' + space2 + str(z) + space + 'summary' + space2 + str(summary) + newline + \
	'mode_' + space2 + str(mode_) + newline + \
	'series_name' + space2 + str(series_name) + newline + \
	'season_id' + space2 + str(season_id)
	printlog(title='sdarot_', printpoint="", text=text, level=0, option="")
	return x, z, summary, mode_, series_name, season_id

def getStreamUrl_DailyMotion(url):
	printpoint = "" ; returned = "" ; cc = "" ; get_json_code = ""
	url = 'http://www.dailymotion.com/embed/video/' + url
	link = OPEN_URL(url)
	if link.find('"statusCode":410') > 0 or link.find('"statusCode":403') > 0:
		notification('Video is not available!','DailyMotion','',2000)
	else:
		get_json_code = re.compile(r'dmp\.create\(document\.getElementById\(\'player\'\),\s*([^;]+)').findall(link)[0]
		get_json_code = get_json_code[:len(get_json_code)-1]
		cc = json.loads(get_json_code)['metadata']['qualities']
		
		if '1080' in cc.keys():
			returned = cc['1080'][0]['url']
		elif '720' in cc.keys():
			returned = cc['720'][0]['url']
		elif '480' in cc.keys():
			returned = cc['480'][0]['url']
		elif '380' in cc.keys():
			returned = cc['380'][0]['url']
		elif '240' in cc.keys():
			returned = cc['240'][0]['url']
		elif 'auto' in cc.keys():
			returned = cc['auto'][0]['url']
		else: notification('No Playable link found!','DailyMotion','',2000)

	text = 'returned' + space2 + str(returned) + newline + \
	'get_json_code' + space2 + str(get_json_code) + newline + \
	'cc' + space2 + str(cc) + newline + \
	'url' + space2 + str(url) + newline + \
	'link' + space2 + str(link)
	
	printlog(title="getStreamUrl_DailyMotion", printpoint=printpoint, text=text, level=0, option="")
	
	return returned
	
def dailymotion_test(url):
	#url = 'x3iijfg'
	url2 = getStreamUrl_DailyMotion(url)
	listitem = xbmcgui.ListItem(path=url2)
	
	if listitem != "": xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)
	
	#xbmc.executebuiltin('PlayMedia(str(listitem))')
	print 'int(sys.argv[1]) ' + str(int(sys.argv[1])) + newline + 'listitem' + space2 + str(listitem)
	return listitem
	#
	#link = OPEN_URL(url)
	#prms=json.loads(link)
	#http://www.dailymotion.com/services/oembed?url=<VIDEO_URL>
	
	#xbmc.executebuiltin('PlayMedia(http://www.dailymotion.com/services/oembed?url='+str(url)+')')
	
def apimaster(x, title="", thumb="", desc="", fanart="", playlist=[], addonID=addonID, onlydata=True):
	'''Error may occured at anytime'''
	'''Make sure to use exception upon running this module'''
	
	'''playlist_L = store new videos from x'''
	'''playlist = store up to date videos for comparision'''
	#addonID=addonID
	printpoint = "" ; TypeError = "" ; extra = "" ; page = 1 ; count = 0 ; count_ = 0 ; i = 0 ; totalResults = 0 ; pagesize = 40
	id_L = [] ; playlist_L = [] ; title_L = [] ; thumb_L = [] ; desc_L = [] ; fanart_L = []
	id_ = ""   ; finalurl_ = ""   ; title_ = "" ; thumb_ = ""  ; desc_ = ""  ; fanart_ = ""
	valid_ = "" ; invalid__ = "" ; duplicates__ = "" ; except__ = "" ; url = "" ; title2 = "" ; prms = "" ;  link = ""
	resultsPerPage = pagesize
	
	finalurl_ = x
	
	if onlydata == True:
		maxResults = '5'
		thumbnails = u'medium'
		if '&getAPIdata=' in x:
			printpoint = printpoint + 'A'
			if x[:1] == '[': x = x.replace('[',"",1)
			if x[-1:] == ']': x = x.replace(']',"")
			if x[:1] == "'": x = x.replace("'","",1)
			if x[-1:] == "'": x = x.replace("'","")
			#x = find_string(title, "getAPIdata=", "")
			x = x.replace('&getAPIdata=',"")
			#print 'blabla' + space2 + str(x)
	
	else:
		maxResults = '40'
		thumbnails = u'default'
		returned = get_types(playlist)
		if not 'list' in returned:
			printpoint = printpoint + '0'
			playlist = []
		try:
			count_ = int(len(playlist))
			#count = 0 + int(count_)
		except Exception, TypeError: extra = extra + newline + 'count_ TypeError: ' + str(TypeError)
	
	x2 = x
	videoDuration = 'any'
	videoDefinition = 'any'
	safeSearch = 'moderate'

	if '&videoDuration=' in x:
		videoDuration = regex_from_to(x, '&videoDuration=', '&', excluding=True)
		x = x.replace('&videoDuration='+videoDuration+'&',"")
		#notification(x,videoDuration,'',2000)
	
	if General_TVModeQuality == '1':
		videoDefinition = 'high'
		
	if '&videoDefinition=' in x:
		videoDefinition = regex_from_to(x, '&videoDefinition=', '&', excluding=True)
		x = x.replace('&videoDefinition='+videoDefinition+'&',"")
		#notification(x,videoDefinition,'',2000)
		
	if addonID == 'plugin.video.featherence.docu':
		pass
		#videoDefinition = 'high'
	
	if addonID == 'plugin.video.featherence.kids':
		safeSearch = 'strict'
	
	
	if "&youtube_pl=" in x:
		printpoint = printpoint + "1"
		title2 = '[Playlist]'
		x2 = x.replace("&youtube_pl=","")
		if onlydata == True:
			url = 'https://www.googleapis.com/youtube/v3/playlists?id='+x2+'&key='+api_youtube_featherence+'&part=snippet&maxResults=1&pageToken='
		else:
			url = 'https://www.googleapis.com/youtube/v3/playlistItems?playlistId='+x2+'&key='+api_youtube_featherence+'&part=snippet&maxResults='+maxResults+'&pageToken='
	elif '&youtube_id=' in x:
		title2 = '[Video]'
		x2 = x.replace('&youtube_id=',"")
		url = 'https://www.googleapis.com/youtube/v3/videos?id='+x2+'&key='+api_youtube_featherence+'&part=snippet'
	elif "&youtube_se=" in x:
		title2 = '[Search]'
		printpoint = printpoint + "2"
		x2 = x.replace("&youtube_se=","")
		if 'commonsearch' in x:
			x_ = clean_commonsearch(title)
			x2 = x_ + space + x2
		x2 = clean_commonsearch(x2)
			
		#notification(x2,'','',2000)
		url = 'https://www.googleapis.com/youtube/v3/search?q='+x2+'&key='+api_youtube_featherence+'&videoDuration='+videoDuration+'&videoDefinition='+videoDefinition+'&safeSearch='+safeSearch+'&type=video&part=snippet&maxResults='+maxResults+'&pageToken='
	elif "&youtube_se2=" in x:
		'''WIP'''
		printpoint = printpoint + "5"
		title2 = '[Search]'
		x2 = x.replace("&youtube_se2=","")
		#x = clean_commonsearch(x)
		#url = 'https://www.googleapis.com/youtube/v3/search?q='+x+'&key='+api_youtube_featherence+'&safeSearch='+safeSearch+'&type=channel&part=snippet&maxResults='+maxResults+'&pageToken='
		#url = 'https://www.googleapis.com/youtube/v3/search?channelId='+id+'&key='+api_youtube_featherence+'&videoDefinition='+videoDefinition+'&type=video&part=snippet&maxResults='+maxResults
		#url = 'https://www.googleapis.com/youtube/v3/search?q='+x2+'&key='+api_youtube_featherence+'&safeSearch=moderate&type=channel&part=snippet&maxResults=1&pageToken='
	elif "&custom_se=" in x:
		text = 'xxx' + space2 + str(x)
		title2 = '[Search2]'
		printlog(title='apimaster_test1', printpoint=printpoint, text=text, level=0, option="")
		printpoint = printpoint + "3"
		x2 = x.replace("&custom_se=","")
		x2 = clean_commonsearch(x2)
		url = 'https://www.googleapis.com/youtube/v3/search?q='+x2+'&key='+api_youtube_featherence+'&videoDuration='+videoDuration+'&videoDefinition='+videoDefinition+'&safeSearch='+safeSearch+'&type=video&part=snippet&maxResults=1&pageToken='
	elif "&youtube_ch=" in x:
		printpoint = printpoint + "4"
		title2 = '[Channel]'
		x2 = x2.replace('&youtube_ch=',"")
		if '/playlists' in x:
			x2 = x2.replace('/playlists',"")
		
		url = 'https://www.googleapis.com/youtube/v3/channels?forUsername='+x2+'&key='+api_youtube_featherence+'&part=snippet&maxResults='+maxResults
		link = OPEN_URL(url)
		#print 'link__' + space2 + str(link)
		if '"totalResults": 0' in link or '"items": []' in link:
			printpoint = printpoint + '2'
			url = 'https://www.googleapis.com/youtube/v3/channels?id='+x2+'&key='+api_youtube_featherence+'&part=snippet&maxResults='+maxResults
			
		if onlydata == True: pass
		else:
			link = OPEN_URL(url)
			prms=json.loads(link)
			print url
			try: id_ = str(prms['items'][i][u'id'])
			except: id_ = str(prms['items'][i][u'snippet'][u'channelId'])
			url = 'https://www.googleapis.com/youtube/v3/search?channelId='+id_+'&key='+api_youtube_featherence+'&part=snippet&maxResults='+maxResults
				
			
	elif '&dailymotion_id=' in x:
		title2 = '[Video]'
		x2 = x.replace('&dailymotion_id=',"")
		url = 'https://api.dailymotion.com/video/'+x2+'/?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&family_filter=1&localization=en'
		print 'url: ' + url
	elif '&dailymotion_pl=' in x:
		printpoint = printpoint + '7'
		title2 = '[Playlist]'
		x2 = x.replace('&dailymotion_pl=',"")
		url = 'https://api.dailymotion.com/playlist/'+x2+'/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit=40&family_filter=1&localization=en&page=1'
		#url = 'https://api.dailymotion.com/playlist/'+x2
	
	
	else: printpoint = printpoint + "8"
	
	text = 'x' + space2 + str(x) + newline + \
	'x2' + space2 + str(x2) +newline + \
	'url' + space2 + str(url) + newline + \
	'onlydata' + space2 + str(onlydata)
	printlog(title='apimaster_test2', printpoint=printpoint, text=text, level=0, option="")
	
	if url != "":
		try: link = OPEN_URL(url)
		except Exception, TypeError:
			printpoint = printpoint + '9'
			extra = extra + newline + 'TypeError' + space2 + str(TypeError)
			print printfirst + '***The following video ID is broken!' + space + str(title) + space + str(x) + space + 'Please report to Featherence in order to fix it!***'
			title_L.append('[COLOR=red]' + title + space + '[Deleted!]' + '[/COLOR]')
		if not '9' in printpoint:
			prms=json.loads(link)
			text = "url" + space2 + str(url) + newline + \
			"link" + space2 + str(link) + newline + \
			"prms" + space2 + str(prms) + newline #+ \ + "totalResults" + space2 + str(totalResults)
			'''---------------------------'''
			printlog(title='apimaster_test2', printpoint=printpoint, text=text, level=0, option="")
		
			if '&dailymotion_pl=' in x:
				if prms[u'has_more']:
					totalResults = int(prms[u'limit'])
				else: totalResults = prms[u'total']
			elif '&dailymotion_id=' in x:
				if prms[u'id']:
					totalResults = len(prms[u'id'])
			else:
				totalResults=int(prms['pageInfo'][u'totalResults']) #if bigger than pagesize needs to add more result
				resultsPerPage = int(prms['pageInfo'][u'resultsPerPage'])
			totalpagesN = (totalResults / pagesize) + 1
			'''---------------------------'''

			i = 0
			while i < pagesize and i < totalResults and i < resultsPerPage and not "8" in printpoint and ((count + count_) < pagesize) and not xbmc.abortRequested: #h<totalResults
				
				#try:
				if 1 + 1 == 2:
					id_ = "" ; id2_ = "" ; playlistid_ = ""
					finalurl_ = "" ; title_ = "" ; thumb_ = "" ; desc_ = "" ; fanart_ = ""
					
					if "&youtube_pl=" in x or "&youtube_ch=" in x or '&youtube_id=' in x:
						if onlydata == True:
							id_ = str(prms['items'][i][u'id'])
						else:
							try: id_ = str(prms['items'][i][u'snippet'][u'resourceId'][u'videoId']) #Video ID (Playlist)
							except:
								try: playlistid_ = str(prms['items'][i][u'id'][u'playlistId'])
								except:
									try: id_ = str(prms['items'][i][u'id'][u'videoId'])
									except: id_ = str(prms['items'][i][u'id'])
									
					elif "&youtube_se=" in x or '&custom_se=' in x:
						if onlydata == True:
							id_ = str(prms['items'][i][u'id'][u'videoId']) #Video ID (Search)
						else:
							#print str(i)
							id_ = str(prms['items'][i][u'id'][u'videoId']) #Video ID (Search)		
					elif '&youtube_se2=' in x:
						id_ = str(prms['items'][i][u'snippet'][u'channelId']) #Video ID (Search)
					elif '&dailymotion_id=' in x:
						id2_ = str(prms[u'id'])
					elif '&dailymotion_pl=' in x:
						#if onlydata == True:
						id2_ = str(prms[u'list'][i][u'id'])
							
					
					if id_ != "":
						#if '&youtube_pl=' in x: finalurl_ = "plugin://plugin.video.youtube/playlist/"+id_+"/"
						finalurl_ = "plugin://plugin.video.youtube/play/?video_id="+id_+"&hd=1"
						title_ = str(prms['items'][i][u'snippet'][u'title'].encode('utf-8'))
						try:
							thumb_ = str(prms['items'][i][u'snippet'][u'thumbnails'][thumbnails][u'url'])
							fanart_ = str(prms['items'][i][u'snippet'][u'thumbnails'][u'high'][u'url'])
						except Exception, TypeError: extra = extra + newline + 'thumb TypeError: ' + str(TypeError) + space + 'i' + space2 + str(i) + space + 'id_' + space2 + str(id_)
						desc_ = str(prms['items'][i][u'snippet'][u'description'].encode('utf-8'))
						
						
						id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L, count, invalid__, duplicates__ = apimaster2(playlist, id_, id_L, finalurl_, playlist_L, title_, title_L, title2, thumb_, thumb_L, desc_, desc_L, fanart, fanart_, fanart_L, count, invalid__, duplicates__, i, i_='i')
						
					elif playlistid_ != "":
						url2 = 'https://www.googleapis.com/youtube/v3/playlistItems?playlistId='+playlistid_+'&key='+api_youtube_featherence+'&part=snippet&maxResults=20&pageToken='
						link2 = OPEN_URL(url2)
						prms2 = json.loads(link2)
						totalResults2 = int(prms2['pageInfo'][u'totalResults']) #if bigger than pagesize needs to add more result
						totalpagesN = (totalResults2 / pagesize) + 1
						
						text = "url2" + space2 + str(url2) + newline + \
						"link2" + space2 + str(link2) + newline + \
						"prms2" + space2 + str(prms2) + newline + \
						"totalResults2" + space2 + str(totalResults2)
						printlog(title='apimaster_test3', printpoint=printpoint, text=text, level=0, option="")
						
						
						i2 = 0
						while i2 < pagesize and i2 < totalResults2 and i2 < 20 and not "8" in printpoint and ((count + count_) < pagesize) and not xbmc.abortRequested:
							id_ = "" ; finalurl_ = ""
							title_ = "" ; thumb_ = "" ; desc_ = "" ; fanart_ = ""
							try: id_ = str(prms2['items'][i2][u'snippet'][u'resourceId'][u'videoId']) #Video ID (Playlist)
							except Exception, TypeError:
								extra = extra + newline + 'TypeError' + space2 + str(TypeError)
							if id_ != "":
								finalurl_ = "plugin://plugin.video.youtube/play/?video_id="+id_+"&hd=1"
								title_ = str(prms2['items'][i2][u'snippet'][u'title'].encode('utf-8'))
								try:
									thumb_ = str(prms2['items'][i2][u'snippet'][u'thumbnails'][u'default'][u'url'])
									fanart_ = str(prms['items'][i2][u'snippet'][u'thumbnails'][u'high'][u'url'])
								except Exception, TypeError: extra = extra + newline + 'thumb TypeError: ' + str(TypeError) + space + 'i2' + space2 + str(i2) + space + 'id' + space2 + str(id_)
								desc_ = str(prms2['items'][i2][u'snippet'][u'description'].encode('utf-8')) #.decode('utf-8')
								
								id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L, count, invalid__, duplicates__ = apimaster2(playlist, id_, id_L, finalurl_, playlist_L, title_, title_L, title2, thumb_, thumb_L, desc_, desc_L, fanart, fanart_, fanart_L, count, invalid__, duplicates__, i2, i_='i2')
							
							#print 'i2' + space2 + str(i2) + space + 'id' + space2 + str(id)
							i2 += 1
					
					elif id2_ != "":
						id_ = id2_
						finalurl_ = 'plugin://plugin.video.dailymotion_com/?url='+id_+'&mode=playVideo'
						if '&dailymotion_id=' in x: #if onlydata == True:
							title_ = to_utf8(prms[u'title'])
							try: thumb_ = str(prms[u'thumbnail_large_url'])
							except Exception, TypeError: pass
							try: desc_ = str(prms[u'description']).encode('utf-8')
							except Exception, TypeError: pass
							try: fanart_ = str(prms[u'thumbnail_large_url'])
							except Exception, TypeError: pass
						elif '&dailymotion_pl=' in x:
							title_ = str(prms[u'list'][i][u'title'].encode('utf-8'))
							thumb_ = str(prms[u'list'][i][u'thumbnail_large_url'])
							desc_ = str(prms[u'list'][i][u'description'].encode('utf-8'))
							fanart_ = str(prms[u'list'][i][u'thumbnail_large_url'])
						
							
						id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L, count, invalid__, duplicates__ = apimaster2(playlist, id_, id_L, finalurl_, playlist_L, title_, title_L, title2, thumb_, thumb_L, desc_, desc_L, fanart, fanart_, fanart_L, count, invalid__, duplicates__, i, i_='i')
				
				#except Exception, TypeError:
					#except__ = except__ + newline + "i" + space2 + str(i) + space + "id" + space2 + str(id)
					#if not 'list index out of range' in TypeError: extra = extra + newline + "i" + space2 + str(i) + space + "TypeError" + space2 + str(TypeError)
					#else: printpoint = printpoint + "8"
					
				
				i += 1
				if "&custom_se=" in x2 and count > 0 and playlist_L != []: printpoint = printpoint + "8"
				elif onlydata == True and count > 0 and playlist_L != []: printpoint = printpoint + "8"
		
	#numOfItems2 = len(playlist_L)
	numOfItems2 = count
	#numOfItems2 = int(len(playlist_L)) / 2 #TEST THIS NEW !
	#numOfItems2 = totalResults - invalid_ - duplicates_ - except_
	#if numOfItems2 > pagesize: numOfItems2 = 40
	totalpages = (numOfItems2 / pagesize) + 1
	nextpage = page + 1
	
	#if totalpages > page: addDir('[COLOR=yellow]' + localize(33078) + '[/COLOR]',x,13,"special://skin/media/DefaultVideo2.png",str79528.encode('utf-8'),str(nextpage),50) #Next Page
	if onlydata == True and not '9' in printpoint:
		if id_L == []:
			pass
			#id_L.append(id_)
		if playlist_L == []:
			pass
			#playlist_L.append(finalurl)
		if title_L == []:
			if title == None: title = ""
			title_L.append(title)
		if thumb_L == []:
			thumb_L.append(thumb)
		if desc_L == []:
			if desc == None: desc = ""
			desc_L.append(desc)
		if fanart_L == []:
			if fanart == None: fanart = ""
			fanart_L.append(fanart)
			
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	if duplicates__ != "": extra = "duplicates__" + space2 + str(duplicates__) + "(" + str(len(duplicates__)) + ")" + newline + extra
	if invalid__ != "": extra = "invalid__" + space2 + str(invalid__) + "(" + str(len(invalid__)) + ")" + newline + extra
	if except__ != "": extra = "except__" + space2 + str(except__) + "(" + str(len(except__)) + ")" + newline + extra
	if playlist != []: extra = "playlist" + space2 + str(playlist) + newline + extra
	
	#'link' + space2 + str(link) + newline + \
	text = "i" + space2 + str(i) + space + "totalResults" + space2 + str(totalResults) + space + "numOfItems2" + space2 + str(numOfItems2) + newline + \
	'onlydata' + space2 + str(onlydata) + newline + \
	"x" + space2 + str(x) + newline + \
	'url' + space2 + str(url) + newline + \
	'prms' + space2 + str(prms) + newline + \
	'finalurl_' + space2 + str(finalurl_) + newline + \
	'id_L' + space2 + str(id_L) + newline + \
	'title' + space2 + str(title) + space + 'title2' + space2 + str(title2) + space + 'title_L' + space2 + str(title_L) + newline + \
	'thumb' + space2 + str(thumb) + space + 'thumb_L' + space2 + str(thumb_L) + newline + \
	'desc' + space2 + str(desc) + space + 'desc_L' + space2 + str(desc_L) + newline + \
	'fanart' + space2 + str(fanart) + space + 'fanart_L' + space2 + str(fanart_L) + newline + \
	"page" + space2 + str(page) + " / " + str(totalpages) + space + "pagesize" + space2 + str(pagesize) + newline + \
	'count' + space2 + str(count) + space + 'count_' + space2 + str(count_) + newline + \
	"playlist" + space2 + str(len(playlist)) + space + str(playlist) + newline + \
	"playlist_L" + space2 + str(len(playlist_L)) + space + str(playlist_L) + newline + \
	"extra" + space2 + str(extra)
	printlog(title='apimaster_id', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	
	if '9' in printpoint:
		return "", [], [], [], [], [], []
	else:
		return finalurl_, id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L

def apimaster2(playlist, id_, id_L, finalurl_, playlist_L, title_, title_L, title2, thumb_, thumb_L, desc_, desc_L, fanart, fanart_, fanart_L, count, invalid__, duplicates__, i, i_='i'):
	if not finalurl_ in playlist and not "Deleted video" in title_ and not "Private video" in title_ and finalurl_ != "":
		#if onlydata == True:
		if title2 != "":
			title_ = title_ + space + title2
		id_L.append(id_)
		playlist_L.append(finalurl_)
		title_L.append(title_)
		if thumb_L != "": thumb_L.append(thumb_)
		if desc_ != "": desc_L.append(desc_)
		if fanart == "": fanart_L.append(fanart_)
		
		count += 1
	else:
		if "Deleted video" in title_ or "Private video" in title_:
			invalid__ = invalid__ + newline + i_ + space2 + str(i) + space + "id_" + space2 + str(id_)
		elif finalurl_ in playlist:
			duplicates__ = duplicates__ + newline + i_ + space2 + str(i) + space + "id_" + space2 + str(id_)
	
	text = "i" + space2 + str(i) + space + "count" + space2 + str(count) + newline + \
	'title_' + space2 + str(title_) + newline + \
	"id_" + space2 + str(id_)

	printlog(title='apimaster2', printpoint="", text=text, level=0, option="")
	
	return id_L, playlist_L, title_L, thumb_L, desc_L, fanart_L, count, invalid__, duplicates__

def RanFromPlayList(playlistid):
	random.seed()
	url='https://gdata.youtube.com/feeds/api/playlists/'+playlistid+'?alt=json&max-results=50'
	link = OPEN_URL(url)
	prms=json.loads(link)
	numOfItems=int(prms['feed'][u'openSearch$totalResults'][u'$t']) #if bigger than 50 needs  to add more result
	if numOfItems >1 :
		link = OPEN_URL(url)
		prms=json.loads(link)
		if numOfItems>49:
			numOfItems=49
		i=random.randint(1, numOfItems-1)
		#print str (len(prms['feed'][u'entry']))  +"and i="+ str(i)
		try:
			urlPlaylist= str(prms['feed'][u'entry'][i][ u'media$group'][u'media$player'][0][u'url'])
			match=re.compile('www.youtube.com/watch\?v\=(.*?)\&f').findall(urlPlaylist)
			finalurl="plugin://plugin.video.youtube/play/?video_id="+match[0]+"&hd=1" #finalurl="plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid="+match[0]+"&hd=1"
			title= str(prms['feed'][u'entry'][i][ u'media$group'][u'media$title'][u'$t'].encode('utf-8')).decode('utf-8')
			thumb =str(prms['feed'][u'entry'][i][ u'media$group'][u'media$thumbnail'][2][u'url'])
			desc= str(prms['feed'][u'entry'][i][ u'media$group'][u'media$description'][u'$t'].encode('utf-8')).decode('utf-8')
		except :
			 return "","","",""  # private video from youtube
		'''liz = xbmcgui.ListItem(title, iconImage="DefaultVideo.png", thumbnailImage=thumb)
		liz.setInfo( type="Video", infoLabels={ "Title": title} )
		liz.setProperty("IsPlayable","true")
		pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
		pl.clear()
		pl.add(finalurl, liz)'''
		#xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(pl)
		return finalurl,title,thumb,desc
	else:
		return "","","",""

def myView(type):
	name = 'myView' ; value = ""
	admin = xbmc.getInfoLabel('Skin.HasSetting(Admin)')
	if type == "A":
		if xbmc.getSkinDir() != "skin.featherence":
			try: value = int(General_AutoView_A)
			except: value = ""
		else: value = "50"
		
	elif type == "B":
		if xbmc.getSkinDir() != "skin.featherence":
			try: value = int(General_AutoView_B)
			except: value = ""
	elif type == "C":
		if xbmc.getSkinDir() != "skin.featherence":
			try: value = int(General_AutoView_C)
			except: value = ""

	text = "type" + space2 + str(type) + space + "value" + space2 + str(value)
	printlog(title=name, printpoint="", text=text, level=0, option="")
	return value

def setView(content, viewType, containerfolderpath2):
	'''set content type so library shows more views and info'''
	name = 'setView' ; printpoint = ""
	
	if content:
		printpoint = printpoint + "1"
		xbmcplugin.setContent(int(sys.argv[1]), content)
	if viewType == None:
		printpoint = printpoint + "2"
		if containerfolderpath2 == 'plugin://' + addonID + "/": viewType = 50
		elif viewType == None: pass
		elif content == 'episodes': viewType = 50
		elif content == 'seasons': viewType = 50
		elif viewType == 1: content = 'movies'
		elif viewType == 2: content = 'tvshows'
		

	if General_AutoView == "true" and viewType != None and 1 + 1 == 3:
		if xbmc.getSkinDir() == 'skin.featherence':
			xbmc.executebuiltin("Container.SetViewMode(%s)" % str(viewType) )
			printpoint = printpoint + "7"
			'''---------------------------'''
		else: printpoint = printpoint + "8"
	else: printpoint = printpoint + "9"

	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "content" + space2 + str(content) + space + "viewType" + space2 + str(viewType) + newline + \
	"containerfolderpath2" + space2 + containerfolderpath2
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

def ShowFromUser(user):
	'''reads  user names from my subscriptions'''
	murl='https://gdata.youtube.com/feeds/api/users/'+user+'/shows?alt=json&start-index=1&max-results=50&v=2'
	resultJSON = json.loads(OPEN_URL(murl))
	shows=resultJSON['feed']['entry']
	#print shows[1]
	hasNext= True
	while hasNext:
		shows=resultJSON['feed']['entry']
		for  i in range (0, len(shows)) :
			showApiUrl=shows[i]['link'][1]['href']
			showApiUrl=showApiUrl[:-4]+'/content?v=2&alt=json'
			showName=shows[i]['title']['$t'].encode('utf-8')
			image= shows[i]['media$group']['media$thumbnail'][-1]['url']
			addDir(showName,showApiUrl,14,image,'','1',"")
		hasNext= resultJSON['feed']['link'][-1]['rel'].lower()=='next'
		if hasNext:
			resultJSON = json.loads(OPEN_URL(resultJSON['feed']['link'][-1]['href']))
			
def TVMode_check(admin, url, playlists):
	printpoint = ""
	returned = ""
	if General_TVModeDialog == "true":
		printpoint = printpoint + "1"
		printpoint = printpoint + "3"
		countl = 0
		for space in playlists:
			countl += 1
		countlS = str(countl)
		if playlists==[] or countl > 1:  #no playlists on  youtube channel
			'''------------------------------
			---PLAYLIST->-1------------------
			------------------------------'''
			printpoint = printpoint + "5"
			returned = dialogyesno(addonString_servicefeatherence(7).encode('utf-8'), addonString_servicefeatherence(8).encode('utf-8'))
			if returned == "ok": returned = TvMode(url)
			'''---------------------------'''
		else: printpoint = printpoint + "8"
				
	printlog(title='TVMode_check', printpoint=printpoint, text="", level=0, option="")
	'''---------------------------'''
	return returned

def TvMode2(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart):
	returned = ""
	if url == "None":
		'''Empty button'''
		notification("no valid URL founds!", "...", "", 2000)
	else:
		if General_TVModeDialog == "true" or mode == 2:
			if General_TVModeShuffle == "true": extra = addonString_servicefeatherence(8).encode('utf-8')
			else: extra = addonString_servicefeatherence(61).encode('utf-8') + '[CR]' + addonString_servicefeatherence(62).encode('utf-8')
			if mode == 2: returned = 'ok'
			else: returned = dialogyesno(addonString_servicefeatherence(7).encode('utf-8'), extra)
			
		if returned == 'ok': mode = 5
		else: mode = 6
		
		mode = MultiVideos(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart)
		
		return mode

def getAddonInfo(addon):
	name = 'getAddonInfo' ; printpoint = ""
	thumb = "" ; fanart = "" ; summary = "" ; description = ""
	
	thumb = os.path.join(addons_path, addon, 'icon.png')
	fanart = os.path.join(addons_path, addon, 'fanart.jpg')
	addoninfo = os.path.join(addons_path, addon, 'addon.xml')
	addoninfo_ = read_from_file(addoninfo, silent=True, lines=False, retry=False, printpoint="", addlines="")
	systemlanguage = xbmc.getInfoLabel('System.Language')
	systemlanguage_ = systemlanguage[:2].lower()
	
	if addoninfo_ != "":
		i = 0
		for i in range(0,3):
			if i == 0: summary = regex_from_to(addoninfo_, '<summary lang="'+systemlanguage_+'">', '</summary>', excluding=True)
			elif i == 1: summary = regex_from_to(addoninfo_, '<summary>', '</summary>', excluding=True)
			elif i == 2: summary = regex_from_to(addoninfo_, '<summary lang="en">', '</summary>', excluding=True)
			if summary != "": break
		
		i = 0
		for i in range(0,3):
			if i == 0: description = regex_from_to(addoninfo_, '<description lang="'+systemlanguage_+'">', '</description>', excluding=True)
			elif i == 1: description = regex_from_to(addoninfo_, '<description>', '</description>', excluding=True)
			elif i == 2: description = regex_from_to(addoninfo_, '<description lang="en">', '</description>', excluding=True)
			if description != "": break
	
	text = 'systemlanguage' + space2 + str(systemlanguage) + space + 'systemlanguage[:2]' + space2 + str(systemlanguage_) + newline + \
	'thumb' + space2 + str(thumb) + newline + \
	'fanart' + space2 + str(fanart) + newline + \
	'summary' + space2 + str(summary) + newline + \
	'description' + space2 + str(description)
	
	try: summary = summary.encode('utf-8')
	except: pass
	try: description = description.encode('utf-8')
	except: pass
	plot = '[COLOR=yellow]'+summary+'[/COLOR]'+'[CR][CR]'+description
	
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return thumb, fanart, summary, description, plot
	
def update_view(url, num, viewtype, ok=True):
	printpoint = ""
	if 'plugin.' in num:
		if not xbmc.getCondVisibility('System.HasAddon('+ num +')') or not os.path.exists(os.path.join(addons_path, num)):
			notification_common("24")
			installaddon(admin, num, update=True)
			xbmc.sleep(2000)
	
	if '&activatewindow=' in url:
		printpoint = printpoint + '2'
	if '&' in url and '=' in url:
		url_ = find_string(url, "&", '=')
		list = ['&youtube_pl=', '&youtube_id=', '&youtube_ch=', '&youtube_se=', '&sdarot=', '&activatewindow=']
		if url_ in list:
			url = url.replace(url_,"",1)
	
	url = url.replace('[',"",1)
	url = url.replace(']',"",1)
	url = url.replace("'","",1)
	url = url.replace("'","",1)
	
	if '2' in printpoint:
		xbmc.executebuiltin('XBMC.Container.Update(%s)' % url ) ; xbmc.sleep(500)
	xbmc.executebuiltin('XBMC.Container.Update(%s)' % url )
		
	text = "url" + space2 + str(url) + space + 'viewtype' + space2 + str(viewtype)
	printlog(title='update_view', printpoint=printpoint, text=text, level=0, option="")
	
	return ok

def play_view(url, num, viewtype):
	if 'plugin.' in num:
		if not xbmc.getCondVisibility('System.HasAddon('+ num +')') or not os.path.exists(os.path.join(addons_path, num)):
			notification_common("24")
			installaddon(admin, num, update=True)
			xbmc.sleep(2000)
	ok = True
	xbmc.executebuiltin('PlayMedia(%s)' % url )
	text = "url" + space2 + str(url) + space + 'viewtype' + space2 + str(viewtype)
	printlog(title='update_view', printpoint="", text=text, level=0, option="")
	return ok	

def unescape(text):
	try:            
		rep = {"&nbsp;": " ",
			   "\n": "",
			   "\t": "",
			   "\r":"",
			   "&#39;":"",
			   "&quot;":"\""
			   }
		for s, r in rep.items():
			text = text.replace(s, r)
			
		# remove html comments
		text = re.sub(r"<!--.+?-->", "", text)    
			
	except TypeError:
		pass

	return text

def urlcheck(url, ping=False, timeout=7):
	import urllib2
	name = "urlcheck" ; printpoint = "" ; returned = "" ; extra = "" ; TypeError = "" ; response_ = ""
	
	
	try:
		#urllib2.urlopen(url)
		request = urllib2.Request(url)
		response = urllib2.urlopen(request, timeout=timeout)
		response_ = response
		#content = response.read()
		#f = urllib2.urlopen(url)
		#f.fp._sock.recv=None # hacky avoidance
		response.close()
		del response
		printpoint = printpoint + "7"
		
	except urllib2.HTTPError, e: 
		extra = extra + newline + str(e.code) + space + str(e)
		printpoint = printpoint + "8"
	except urllib2.URLError, e:
		extra = extra + newline + str(e.args) + space + str(e)
		printpoint = printpoint + "9"
	except Exception, TypeError:
		printpoint = printpoint + "9"
		extra = extra + newline + "TypeError" + space2 + str(TypeError)
		if 'The read operation timed out' in TypeError: returned = 'timeout'
			
	if not "7" in printpoint:
		if ping == True:
			if systemplatformwindows: output = terminal('ping '+url+' -n 1',"Connected2")
			else: output = terminal('ping -W 1 -w 1 -4 -q '+url+'',"Connected")
			if (not systemplatformwindows and ("1 packets received" in output or not "100% packet loss" in output)) or (systemplatformwindows and ("Received = 1" in output or not "100% loss" in output)): printpoint = printpoint + "7"
			
		elif 'Forbidden' in extra:
			printpoint = printpoint + '7'
			
	if "UKY3scPIMd8" in url: printpoint = printpoint + "6"
	elif "7" in printpoint: returned = "ok" # or 'Forbidden' in extra
	else: returned = 'error'
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "url" + space2 + url + space + "ping" + space2 + str(ping) + space + 'returned' + space2 + str(returned) + newline + \
	'response_' + space2 + str(response_) + extra
	printlog(title='urlcheck', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return returned
	
def YOUList2(name, url, iconimage, desc, num, viewtype):
	returned = "" ; printpoint = "" ; i = 0 ; urlL = ['channel', 'user'] #, 'show'
	url = CleanString2(url)
	if '&youtube_ch=' in url or (not '&' in url and not '=' in url):
		printpoint = printpoint + '1'
		if '&youtube_ch=' in url:
			printpoint = printpoint + '2'
			url = url.replace("&youtube_ch=","")
		
		if "/playlists" in url:
			printpoint = printpoint + '3'
			url = url.replace("/playlists","")		
			
		default = 'http://www.youtube.com/'
		default2 = 'plugin://plugin.video.youtube/'
		
		for x in urlL:
			returned = urlcheck(default + urlL[i] + '/' + url + '/')
			if returned == "ok": break
			else:
				i += 1

		if returned == 'ok':
			printpoint = printpoint + '7'
			update_view(default2 + urlL[i] + '/' + url + '/', num, viewtype, ok=False)
	else:
		printpoint = printpoint + '9'
	text = "name" + space2 + str(name) + newline + \
	"url" + space2 + url + newline + \
	"i" + space2 + str(i) + space + "returned" + space2 + str(returned)
	printlog(title='YOUList2', printpoint=printpoint, text=text, level=0, option="")

def setCustomFanart(addon, mode, admin, name, printpoint):
	x = "" ; printpoint = ""
	if not '.' in addon: addon = ""
	try: test = int(mode) + 1
	except: mode = ""
	
	if mode != "" and addon != "":
		'''Add-Fanart'''
		name = localize(20441)
		x = 'background'
		nolabel=localize(20438)
		yeslabel=localize(20441)
	
	if x != "":
		returned = dialogyesno(str(name), addonString_servicefeatherence(31).encode('utf-8'), nolabel=nolabel, yeslabel=yeslabel)
		if returned == 'ok':
			returned2, value = getRandom(0, min=0, max=100, percent=40)
			if returned2 == 'ok': notification('O_o???','Copy & Paste an image URL','',4000)
			'''remote'''
			value = dialogkeyboard("", yeslabel, 0, "1", "", "")
			if value != "skip":
				from shared_modules3 import urlcheck
				returned2 = urlcheck(value, ping=False)
				if returned2 != "ok":
					notification("URL Error", "Try again..", "", 2000)
					header = "URL Error"
					message = "Examine your URL for errors:" + newline + '[B]' + str(value) + '[/B]'
					diaogtextviewer(header,message)
				else:
					setsetting_custom1(addon, 'Fanart_Custom' + str(mode),str(value))
		else:
			'''local'''
			value = setPath(type=1,mask='pic', folderpath="")
			setsetting_custom1(addon, 'Fanart_Custom' + str(mode),str(value))
	
	text = 'addon' + space2 + str(addon) + space + 'mode' + space2 + str(mode) + space + 'x' + space2 + str(x) + newline
	printlog(title='setCustomFanart', printpoint=printpoint, text=text, level=0, option="")
	
def setaddonFanart(fanart, Fanart_Enable, Fanart_EnableCustom): #Fanart_EnableExtra
	#admin = xbmc.getInfoLabel('Skin.HasSetting(Admin)')
	#admin2 = xbmc.getInfoLabel('Skin.HasSetting(Admin2)')
	#admin3 = xbmc.getInfoLabel('Skin.HasSetting(Admin3)')
	returned = "" ; printpoint = "" ; TypeError = "" ; extra = ""
	try:
		Fanart_Enable = getsetting('Fanart_Enable')
		Fanart_EnableCustom = getsetting('Fanart_EnableCustom')
	except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)
	
	if Fanart_Enable == "true" and extra == "":
		printpoint = printpoint + "1"
		if fanart != "":
			printpoint = printpoint + "2"
			try:
				if os.path.exists(fanart):
					printpoint = printpoint + "3"
					returned = fanart
				elif "http://" in fanart or "www." in fanart or "https://" in fanart:
					printpoint = printpoint + "4"
					returned = fanart
				else: pass
			except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)
	
		else: printpoint = printpoint + "8"
	else: printpoint = printpoint + "9"
	
	text =  "Fanart_Enable" + space2 + str(Fanart_Enable) + space + "Fanart_EnableCustom" + space2 + str(Fanart_EnableCustom) + newline + \
	"fanart" + space2 + str(fanart) + extra
	printlog(title='setaddonFanart', printpoint=printpoint, text=text, level=0, option="")
	return returned

def getAddonFanart(category, custom="", default="", urlcheck_=False):
	#admin = xbmc.getInfoLabel('Skin.HasSetting(Admin)')
	#admin2 = xbmc.getInfoLabel('Skin.HasSetting(Admin2)')
	#admin3 = xbmc.getInfoLabel('Skin.HasSetting(Admin3)')
	returned = "" ; category_path = "" ; printpoint = "" ; extra = "" ; 
	
	if custom != "":
		valid = ""
		if urlcheck_ == True: 
			valid = urlcheck(custom, ping=False, timeout=1)
		
		if 'ok' in valid or urlcheck_ != True:
			printpoint = printpoint + "7"
			returned = custom
			
	if returned == "" and not '7' in printpoint:
		if Fanart_EnableCustom != "true" and default == "":
			returned = addonFanart
			printpoint = printpoint + "8"
		elif category == 100: category_path = Fanart_Custom100
		elif category == 101: category_path = Fanart_Custom101
		elif category == 102: category_path = Fanart_Custom102
		elif category == 103: category_path = Fanart_Custom103
		elif category == 104: category_path = Fanart_Custom104
		elif category == 105: category_path = Fanart_Custom105
		elif category == 106: category_path = Fanart_Custom106
		elif category == 107: category_path = Fanart_Custom107
		elif category == 108: category_path = Fanart_Custom108
		elif category == 109: category_path = Fanart_Custom109
		elif category == 110: category_path = Fanart_Custom110
		elif category == 111: category_path = Fanart_Custom111
		elif category == 112: category_path = Fanart_Custom112
		elif category == 113: category_path = Fanart_Custom113
		elif category == 114: category_path = Fanart_Custom114
		elif category == 115: category_path = Fanart_Custom115
		elif category == 116: category_path = Fanart_Custom116
		elif category == 117: category_path = Fanart_Custom117
		elif category == 118: category_path = Fanart_Custom118
		elif category == 119: category_path = Fanart_Custom119
		
		elif category == 10000: category_path = Fanart_Custom10000
		elif category == 10001: category_path = Fanart_Custom10001
		elif category == 10002: category_path = Fanart_Custom10002
		elif category == 10003: category_path = Fanart_Custom10003
		elif category == 10004: category_path = Fanart_Custom10004
		elif category == 10005: category_path = Fanart_Custom10005
		elif category == 10006: category_path = Fanart_Custom10006
		elif category == 10007: category_path = Fanart_Custom10007
		elif category == 10008: category_path = Fanart_Custom10008
		elif category == 10009: category_path = Fanart_Custom10009
		
		elif category == 10100: category_path = Fanart_Custom10100
		elif category == 10101: category_path = Fanart_Custom10101
		elif category == 10102: category_path = Fanart_Custom10102
		elif category == 10103: category_path = Fanart_Custom10103
		elif category == 10104: category_path = Fanart_Custom10104
		elif category == 10105: category_path = Fanart_Custom10105
		elif category == 10106: category_path = Fanart_Custom10106
		elif category == 10107: category_path = Fanart_Custom10107
		elif category == 10108: category_path = Fanart_Custom10108
		elif category == 10109: category_path = Fanart_Custom10109
		elif category == 10200: category_path = Fanart_Custom10200
		elif category == 10201: category_path = Fanart_Custom10201
		elif category == 10202: category_path = Fanart_Custom10202
		elif category == 10203: category_path = Fanart_Custom10203
		elif category == 10204: category_path = Fanart_Custom10204
		elif category == 10205: category_path = Fanart_Custom10205
		elif category == 10206: category_path = Fanart_Custom10206
		elif category == 10207: category_path = Fanart_Custom10207
		elif category == 10208: category_path = Fanart_Custom10208
		elif category == 10209: category_path = Fanart_Custom10209
		
		elif category == 11100: category_path = Fanart_Custom11100
		elif category == 11101: category_path = Fanart_Custom11101
		elif category == 11102: category_path = Fanart_Custom11102
		elif category == 11103: category_path = Fanart_Custom11103
		elif category == 11104: category_path = Fanart_Custom11104
		elif category == 11105: category_path = Fanart_Custom11105
		elif category == 11106: category_path = Fanart_Custom11106
		elif category == 11107: category_path = Fanart_Custom11107
		elif category == 11108: category_path = Fanart_Custom11108
		elif category == 11109: category_path = Fanart_Custom11109
		
		else:
			try:
				if "Custom_Playlist" in category:
					if category == "Custom_Playlist1": category_path = Custom_Playlist1_Fanart
					elif category == "Custom_Playlist2": category_path = Custom_Playlist2_Fanart
					elif category == "Custom_Playlist3": category_path = Custom_Playlist3_Fanart
					elif category == "Custom_Playlist4": category_path = Custom_Playlist4_Fanart
					elif category == "Custom_Playlist5": category_path = Custom_Playlist5_Fanart
					elif category == "Custom_Playlist6": category_path = Custom_Playlist6_Fanart
					elif category == "Custom_Playlist7": category_path = Custom_Playlist7_Fanart
					elif category == "Custom_Playlist8": category_path = Custom_Playlist8_Fanart
					elif category == "Custom_Playlist9": category_path = Custom_Playlist9_Fanart
					elif category == "Custom_Playlist10": category_path = Custom_Playlist10_Fanart
					else: printpoint = printpoint + "8"
			except Exception, TypeError:
				extra = extra + newline + "TypeError" + space2 + str(TypeError)
				printpoint = printpoint + "8"
	
	
		if category_path != "":
			if "http://" in category_path or "www." in category_path:
				printpoint = printpoint + "7a"
				returned = category_path
				#valid = urlcheck(value, ping=False)
			else:
				try:
					category_path = os.path.join(xbmc.translatePath(category_path).decode("utf-8"))
					category_path = category_path.encode('utf-8')
				except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError).encode('utf-8')
				if os.path.exists(category_path):
					printpoint = printpoint + "7b"
					
					if 1 + 1 == 3:
						category_path = os.path.join(xbmc.translatePath(category_path).decode("utf-8"))
						try: category_path = category_path.encode('utf-8')
						except: pass
					
				else:
					setsetting('Fanart_Custom'+str(category),"")
					printpoint = printpoint + "9d"
		
		elif default != "" and not '7' in printpoint:
			valid = urlcheck(default, ping=False, timeout=1)
			
			if 'ok' in valid:
				printpoint = printpoint + "7"
				returned = default
		else:
			printpoint = printpoint + "9"
			
	if "9" in printpoint or "8" in printpoint:
		try:
			if os.path.exists(addonFanart): returned = addonFanart
		except Exception, TypeError:
			extra = extra + newline + "TypeError" + space2 + str(TypeError)
			returned = ""
	
	elif "7" in printpoint:
		if default == "" and custom == "" or '7b' in printpoint: returned = category_path
	
	text = "category" + space2 + str(category) + newline + \
	"custom" + space2 + str(custom) + newline + \
	"default" + space2 + str(default) + newline + \
	"returned" + space2 + str(returned) + newline + \
	"category_path" + space2 + str(category_path) + extra
	printlog(title='getAddonFanart', printpoint=printpoint, text=text, level=0, option="")
	return returned
	
def pluginend(admin):
	try: from modules import *
	except: pass
	try: from modulesp import *
	except: pass
	printpoint = "" ; TypeError = "" ; extra = ""
	
	'''------------------------------
	---params------------------------
	------------------------------'''
	params=get_params()
	url=None
	name=None
	mode=None
	iconimage=None
	desc=None
	num=None
	viewtype=None
	fanart=None
	#value=None
	'''---------------------------'''
	try: url=urllib.unquote_plus(params["url"])
	except: pass
	try: name=urllib.unquote_plus(params["name"])
	except: pass
	try: iconimage=urllib.unquote_plus(params["iconimage"])
	except: pass
	try: mode=int(params["mode"])
	except: pass
	try: desc=urllib.unquote_plus(params["desc"])
	except: pass
	
	try: num=urllib.unquote_plus(params["num"])
	except: pass
	try: viewtype=int(params["viewtype"])
	except: pass
	try: fanart=urllib.unquote_plus(params["fanart"])
	except: pass
	#try: value=urllib.unquote_plus(params["value"])
	#except: pass
	'''---------------------------'''

	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	try: IconImageS = str(IconImage)
	except: IconImageS = "None"
	'''---------------------------'''
	text = "mode" + space2 + str(mode) + newline + \
	"url" + space2 + str(url) + newline + \
	"name" + space2 + str(name) + space + "IconImage" + space2 + IconImageS + newline + \
	"desc" + space2 + str(desc) + newline + \
	"viewtype" + space2 + str(viewtype) + space + "fanart" + space2 + str(fanart) + newline + \
	"params" + space2 + str(params)
	printlog(title='pluginend', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

	'''------------------------------
	---MODES-LIST--------------------
	------------------------------'''
	if mode == None or ((url == None or len(url)<1) and mode < 100) or 1 + 1 == 3:
		if addonID == 'plugin.video.featherence.kids' and General_Language == "":
			CATEGORIES200()
			xbmc.executebuiltin('AlarmClock(firstrun,RunScript(script.featherence.service,,?mode=32&value=40),00:01,silent)')
			
		else: CATEGORIES()
		
		systemlanguage = xbmc.getInfoLabel('System.Language')
		
		if 1 + 1 == 2:
			getsetting('Addon_Update')
			getsetting('Addon_Version')
			getsetting('Addon_UpdateDate')
			getsetting('Addon_UpdateLog')
			getsetting('Addon_ShowLog')
			getsetting('Addon_ShowLog2')
			
			VerReset = ""
			#if addonID == 'plugin.video.featherence.music' and Addon_Version == '0.0.17': VerReset = "true"
			checkAddon_Update(admin, Addon_Update, Addon_Version, addonVersion, Addon_UpdateDate, Addon_UpdateLog, Addon_ShowLog, Addon_ShowLog2, VerReset)
			if Addon_UpdateLog == "true" or 1 + 1 == 3:
				if addonID == 'plugin.video.featherence.kids':
					if systemlanguage != "Hebrew" and systemlanguage != "English": notification("This addon does not support "+str(systemlanguage)+" yet","...","",2000)
					else: pass
					if systemlanguage == "Hebrew":
						installaddonP(admin, 'repository.xbmc-israel', update=True)
						'''---------------------------'''
				if addonID == 'plugin.video.featherence.docu':
					if systemlanguage != "Hebrew" and systemlanguage != "English": notification("This addon does not support "+str(systemlanguage)+" yet","...","",2000)
					else: pass
					if systemlanguage == "Hebrew":
						installaddonP(admin, 'repository.xbmc-israel', update=True)
						'''---------------------------'''
				elif addonID == 'plugin.video.featherence.music':
					if systemlanguage != "Hebrew" and systemlanguage != "English": notification("This addon does not support "+str(systemlanguage)+" yet","...","",2000)
					else: pass
				
				list = []
				list.append(addonString_servicefeatherence(32060).encode('utf-8')) #Would you like thanks us? Would love to hear you!
				list.append(addonString_servicefeatherence(32061).encode('utf-8')) #Do you want to contribute?
				list.append(addonString_servicefeatherence(32062).encode('utf-8')) #Have an idea for new addon?
				list.append(addonString_servicefeatherence(32063).encode('utf-8')) #Looking for support?
				list.append(addonString_servicefeatherence(32064).encode('utf-8')) #Having a question?
				returned, value = getRandom(0, min=0, max=len(list), percent=50)
				
				notification(list[int(value)],'www.facebook.com/groups/featherence','',4000)
				
		#except Exception, TypeError:
			#extra = extra + newline + "TypeError" + space2 + str(TypeError)
			#printpoint = printpoint + "2"
			'''---------------------------'''
		
	#1-99 = COMMANDS
	elif mode == 1:
		getLists(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 2:
		LocalSearch(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 3:
		YoutubeSearch(name, url, desc, num, viewtype)
	elif mode == 4:
		PlayVideos(name, mode, url, iconimage, desc, num, fanart)
	elif mode == 5:
		mode = MultiVideos(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 6:
		mode = MultiVideos(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 7:
		ListLive(url, mode, num, viewtype, fanart)
	elif mode == 8:
		update_view(url, num, viewtype)
	elif mode == 9:
		YOUList2(name, url, iconimage, desc, num, viewtype)
	elif mode == 10:
		mode = 4
		PlayVideos(name, mode, url, iconimage, desc, num, fanart)
	elif mode == 11:
		pass #YOULinkAll(url)
	elif mode == 12:
		PlayVideos(name, mode, url, iconimage, desc, num, fanart)
	elif mode == 13:
		#ListPlaylist(url, num)
		ListPlaylist2(name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 14:       
		pass #SeasonsFromShow(url)
	elif mode == 15:
		pass
	elif mode == 16:       
		ShowFromUser(url)
	elif mode == 17:
		mode = TvMode2(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 18:
		'''Custom Playlist'''
		mode = TvMode2(addonID, mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 20:
		AddCustom(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 21:
		ManageCustom(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 22:
		AdvancedCustom(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 23:
		MoveCustom(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 24:
		AddCustom(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 30:
		CATEGORIES_SEARCH2(mode, name, url, iconimage, desc, num, viewtype, fanart)
	elif mode == 31:
		Search_Menu(mode, name, url, iconimage, desc, num, viewtype, fanart)
	
	elif mode == 40:
		pass
	elif mode == 90:
		if General_Language != url and url != "":
			setsetting('General_Language',url)
			notification(addonString_servicefeatherence(32080).encode('utf-8'),str(url),'',2000)
			xbmc.sleep(500)
		CATEGORIES()
	elif mode == 100:
		CATEGORIES100(name, iconimage, desc, fanart)
	elif mode == 101:
		CATEGORIES101(name, iconimage, desc, fanart)
	elif mode == 102: 
		CATEGORIES102(name, iconimage, desc, fanart)
	elif mode == 103:       
		CATEGORIES103(name, iconimage, desc, fanart)
	elif mode == 104:       
		CATEGORIES104(name, iconimage, desc, fanart)
	elif mode == 105:    
		CATEGORIES105(name, iconimage, desc, fanart)
	elif mode == 106:       
		CATEGORIES106(name, iconimage, desc, fanart)
	elif mode == 107:       
		CATEGORIES107(name, iconimage, desc, fanart)
	elif mode == 108:       
		CATEGORIES108(name, iconimage, desc, fanart)
	elif mode == 109:
		CATEGORIES109(name, iconimage, desc, fanart)
	elif mode == 110:       
		CATEGORIES110(name, iconimage, desc, fanart)
	elif mode == 111:
		CATEGORIES111(name, iconimage, desc, fanart)
	elif mode == 112: 
		CATEGORIES112(name, iconimage, desc, fanart)
	elif mode == 113:       
		CATEGORIES113(name, iconimage, desc, fanart)
	elif mode == 114:       
		CATEGORIES114(name, iconimage, desc, fanart)
	elif mode == 115:    
		CATEGORIES115(name, iconimage, desc, fanart)
	elif mode == 116:       
		CATEGORIES116(name, iconimage, desc, fanart)
	elif mode == 117:       
		CATEGORIES117(name, iconimage, desc, fanart)
	elif mode == 118:       
		CATEGORIES118(name, iconimage, desc, fanart)
	elif mode == 119:       
		CATEGORIES119(name, iconimage, desc, fanart)
	
	elif mode == 120:       
		CATEGORIES120(name, iconimage, desc, fanart)	
	elif mode == 121:
		CATEGORIES121(name, iconimage, desc, fanart)
	elif mode == 122: 
		CATEGORIES122(name, iconimage, desc, fanart)
	elif mode == 123:       
		CATEGORIES123(name, iconimage, desc, fanart)
	elif mode == 124:       
		CATEGORIES124(name, iconimage, desc, fanart)
	elif mode == 125:    
		CATEGORIES125(name, iconimage, desc, fanart)
	elif mode == 126:       
		CATEGORIES126(name, iconimage, desc, fanart)
	elif mode == 127:       
		CATEGORIES127(name, iconimage, desc, fanart)
	elif mode == 128:       
		CATEGORIES128(name, iconimage, desc, fanart)
	elif mode == 129:       
		CATEGORIES129(name, iconimage, desc, fanart)
	
	elif mode == 130:
		CATEGORIES130(name, iconimage, desc, fanart)
	elif mode == 131:
		CATEGORIES131(name, iconimage, desc, fanart)
	elif mode == 132: 
		CATEGORIES132(name, iconimage, desc, fanart)
	elif mode == 133:       
		CATEGORIES133(name, iconimage, desc, fanart)
	elif mode == 134:       
		CATEGORIES134(name, iconimage, desc, fanart)
	elif mode == 135:    
		CATEGORIES135(name, iconimage, desc, fanart)
	elif mode == 136:       
		CATEGORIES136(name, iconimage, desc, fanart)
	elif mode == 137:       
		CATEGORIES137(name, iconimage, desc, fanart)
	elif mode == 138:       
		CATEGORIES138(name, iconimage, desc, fanart)
	elif mode == 139:       
		CATEGORIES139(name, iconimage, desc, fanart)
	elif mode == 200:
		CATEGORIES200()
	
	#10101+ = SUB-CATEGORIES2
	elif mode == 10001:
		CATEGORIES10001(name, iconimage, desc, fanart)
	elif mode == 10002:
		CATEGORIES10002(name, iconimage, desc, fanart)
	elif mode == 10003:
		CATEGORIES10003(name, iconimage, desc, fanart)
	elif mode == 10004:
		CATEGORIES10004(name, iconimage, desc, fanart)
	elif mode == 10005:
		CATEGORIES10005(name, iconimage, desc, fanart)
	elif mode == 10006:
		CATEGORIES10006(name, iconimage, desc, fanart)
	elif mode == 10007:
		CATEGORIES10007(name, iconimage, desc, fanart)
	elif mode == 10008:
		CATEGORIES10008(name, iconimage, desc, fanart)
	elif mode == 10009:
		CATEGORIES10009(name, iconimage, desc, fanart)
		
	elif mode == 10101:
		CATEGORIES10101(name, iconimage, desc, fanart)
	elif mode == 10102:
		CATEGORIES10102(name, iconimage, desc, fanart)
	elif mode == 10103:
		CATEGORIES10103(name, iconimage, desc, fanart)
	elif mode == 10104:
		CATEGORIES10104(name, iconimage, desc, fanart)
	elif mode == 10105:
		CATEGORIES10105(name, iconimage, desc, fanart)
	elif mode == 10106:
		CATEGORIES10106(name, iconimage, desc, fanart)
	elif mode == 10107:
		CATEGORIES10107(name, iconimage, desc, fanart)
	elif mode == 10108:
		CATEGORIES10108(name, iconimage, desc, fanart)
	elif mode == 10109:
		CATEGORIES10109(name, iconimage, desc, fanart)
		
	elif mode == 10201:
		CATEGORIES10201(name, iconimage, desc, fanart)
	elif mode == 10202:
		CATEGORIES10202(name, iconimage, desc, fanart)
	elif mode == 10203:
		CATEGORIES10203(name, iconimage, desc, fanart)
	elif mode == 10204:
		CATEGORIES10204(name, iconimage, desc, fanart)
	elif mode == 10205:
		CATEGORIES10205(name, iconimage, desc, fanart)
	elif mode == 10206:
		CATEGORIES10206(name, iconimage, desc, fanart)
	elif mode == 10207:
		CATEGORIES10207(name, iconimage, desc, fanart)
	elif mode == 10208:
		CATEGORIES10208(name, iconimage, desc, fanart)
	elif mode == 10209:
		CATEGORIES10209(name, iconimage, desc, fanart)
	
	elif mode == 10301:
		CATEGORIES10301(name, iconimage, desc, fanart)
	elif mode == 10302:
		CATEGORIES10302(name, iconimage, desc, fanart)
	elif mode == 10303:
		CATEGORIES10303(name, iconimage, desc, fanart)
	elif mode == 10304:
		CATEGORIES10304(name, iconimage, desc, fanart)
	elif mode == 10305:
		CATEGORIES10305(name, iconimage, desc, fanart)
	elif mode == 10306:
		CATEGORIES10306(name, iconimage, desc, fanart)
	elif mode == 10307:
		CATEGORIES10307(name, iconimage, desc, fanart)
	elif mode == 10308:
		CATEGORIES10308(name, iconimage, desc, fanart)
	elif mode == 10309:
		CATEGORIES10309(name, iconimage, desc, fanart)
	
	elif mode == 10401:
		CATEGORIES10401(name, iconimage, desc, fanart)
	elif mode == 10402:
		CATEGORIES10402(name, iconimage, desc, fanart)
	elif mode == 10403:
		CATEGORIES10403(name, iconimage, desc, fanart)
	elif mode == 10404:
		CATEGORIES10405(name, iconimage, desc, fanart)
	elif mode == 10406:
		CATEGORIES10406(name, iconimage, desc, fanart)
	elif mode == 10407:
		CATEGORIES10407(name, iconimage, desc, fanart)
	elif mode == 10408:
		CATEGORIES10408(name, iconimage, desc, fanart)
	elif mode == 10409:
		CATEGORIES10409(name, iconimage, desc, fanart)
	elif mode == 10410:
		CATEGORIES10410(name, iconimage, desc, fanart)
	elif mode == 10411:
		CATEGORIES10411(name, iconimage, desc, fanart)
	elif mode == 10412:
		CATEGORIES10412(name, iconimage, desc, fanart)
	elif mode == 10413:
		CATEGORIES10413(name, iconimage, desc, fanart)
	elif mode == 10414:
		CATEGORIES10414(name, iconimage, desc, fanart)
	elif mode == 10415:
		CATEGORIES10415(name, iconimage, desc, fanart)
	elif mode == 10416:
		CATEGORIES10416(name, iconimage, desc, fanart)
	elif mode == 10417:
		CATEGORIES10417(name, iconimage, desc, fanart)
	elif mode == 10418:
		CATEGORIES10418(name, iconimage, desc, fanart)
	elif mode == 10419:
		CATEGORIES10419(name, iconimage, desc, fanart)
	elif mode == 10420:
		CATEGORIES10420(name, iconimage, desc, fanart)
	elif mode == 10421:
		CATEGORIES10421(name, iconimage, desc, fanart)
	elif mode == 10422:
		CATEGORIES10422(name, iconimage, desc, fanart)
	elif mode == 10423:
		CATEGORIES10423(name, iconimage, desc, fanart)
	elif mode == 10424:
		CATEGORIES10424(name, iconimage, desc, fanart)
	elif mode == 10425:
		CATEGORIES10425(name, iconimage, desc, fanart)
	elif mode == 10426:
		CATEGORIES10426(name, iconimage, desc, fanart)
	elif mode == 10427:
		CATEGORIES10427(name, iconimage, desc, fanart)
	elif mode == 10428:
		CATEGORIES10428(name, iconimage, desc, fanart)
	elif mode == 10429:
		CATEGORIES10429(name, iconimage, desc, fanart)
	elif mode == 10430:
		CATEGORIES10430(name, iconimage, desc, fanart)
	
	elif mode == 10501:
		CATEGORIES10501(name, iconimage, desc, fanart)
	elif mode == 10502:
		CATEGORIES10502(name, iconimage, desc, fanart)
	elif mode == 10503:
		CATEGORIES10503(name, iconimage, desc, fanart)
	elif mode == 10504:
		CATEGORIES10504(name, iconimage, desc, fanart)
	elif mode == 10505:
		CATEGORIES10505(name, iconimage, desc, fanart)
	elif mode == 10506:
		CATEGORIES10506(name, iconimage, desc, fanart)
	elif mode == 10507:
		CATEGORIES10507(name, iconimage, desc, fanart)
	elif mode == 10508:
		CATEGORIES10508(name, iconimage, desc, fanart)
	elif mode == 10509:
		CATEGORIES10509(name, iconimage, desc, fanart)
	
	elif mode == 10601:
		CATEGORIES10601(name, iconimage, desc, fanart)
	elif mode == 10602:
		CATEGORIES10602(name, iconimage, desc, fanart)
	elif mode == 10603:
		CATEGORIES10603(name, iconimage, desc, fanart)
	elif mode == 10604:
		CATEGORIES10604(name, iconimage, desc, fanart)
	elif mode == 10605:
		CATEGORIES10605(name, iconimage, desc, fanart)
	elif mode == 10606:
		CATEGORIES10606(name, iconimage, desc, fanart)
	elif mode == 10607:
		CATEGORIES10607(name, iconimage, desc, fanart)
	elif mode == 10608:
		CATEGORIES10608(name, iconimage, desc, fanart)
	elif mode == 10609:
		CATEGORIES10609(name, iconimage, desc, fanart)
	
	elif mode == 10701:
		CATEGORIES10701(name, iconimage, desc, fanart)
	elif mode == 10702:
		CATEGORIES10702(name, iconimage, desc, fanart)
	elif mode == 10703:
		CATEGORIES10703(name, iconimage, desc, fanart)
	elif mode == 10704:
		CATEGORIES10704(name, iconimage, desc, fanart)
	elif mode == 10705:
		CATEGORIES10705(name, iconimage, desc, fanart)
	elif mode == 10706:
		CATEGORIES10706(name, iconimage, desc, fanart)
	elif mode == 10707:
		CATEGORIES10707(name, iconimage, desc, fanart)
	elif mode == 10708:
		CATEGORIES10708(name, iconimage, desc, fanart)
	elif mode == 10709:
		CATEGORIES10709(name, iconimage, desc, fanart)
	
	elif mode == 10801:
		CATEGORIES10801(name, iconimage, desc, fanart)
	elif mode == 10802:
		CATEGORIES10802(name, iconimage, desc, fanart)
	elif mode == 10803:
		CATEGORIES10803(name, iconimage, desc, fanart)
	elif mode == 10804:
		CATEGORIES10804(name, iconimage, desc, fanart)
	elif mode == 10805:
		CATEGORIES10805(name, iconimage, desc, fanart)
	elif mode == 10806:
		CATEGORIES10806(name, iconimage, desc, fanart)
	elif mode == 10807:
		CATEGORIES10807(name, iconimage, desc, fanart)
	elif mode == 10808:
		CATEGORIES10808(name, iconimage, desc, fanart)
	elif mode == 10809:
		CATEGORIES10809(name, iconimage, desc, fanart)
		
	elif mode == 10901:
		CATEGORIES10901(name, iconimage, desc, fanart)
	elif mode == 10902:
		CATEGORIES10902(name, iconimage, desc, fanart)
	elif mode == 10903:
		CATEGORIES10903(name, iconimage, desc, fanart)
	elif mode == 10904:
		CATEGORIES10904(name, iconimage, desc, fanart)
	elif mode == 10905:
		CATEGORIES10905(name, iconimage, desc, fanart)
	elif mode == 1090504:
		CATEGORIES1090504(name, iconimage, desc, fanart)
	elif mode == 10906:
		CATEGORIES10906(name, iconimage, desc, fanart)
	elif mode == 10907:
		CATEGORIES10907(name, iconimage, desc, fanart)
	elif mode == 10908:
		CATEGORIES10908(name, iconimage, desc, fanart)
	elif mode == 10909:
		CATEGORIES10909(name, iconimage, desc, fanart)
	elif mode == 10910:
		CATEGORIES10910(name, iconimage, desc, fanart)
	elif mode == 10911:
		CATEGORIES10911(name, iconimage, desc, fanart)
	elif mode == 10912:
		CATEGORIES10912(name, iconimage, desc, fanart)
	elif mode == 10913:
		CATEGORIES10913(name, iconimage, desc, fanart)
	elif mode == 10914:
		CATEGORIES10914(name, iconimage, desc, fanart)
	elif mode == 10915:
		CATEGORIES10915(name, iconimage, desc, fanart)
	elif mode == 10916:
		CATEGORIES10916(name, iconimage, desc, fanart)
	elif mode == 10917:
		CATEGORIES10917(name, iconimage, desc, fanart)
	elif mode == 10918:
		CATEGORIES10918(name, iconimage, desc, fanart)
	elif mode == 10919:
		CATEGORIES10919(name, iconimage, desc, fanart)
	elif mode == 10920:
		CATEGORIES10920(name, iconimage, desc, fanart)
	elif mode == 10921:
		CATEGORIES10921(name, iconimage, desc, fanart)
	elif mode == 10922:
		CATEGORIES10922(name, iconimage, desc, fanart)
	elif mode == 10923:
		CATEGORIES10923(name, iconimage, desc, fanart)
	elif mode == 10924:
		CATEGORIES10924(name, iconimage, desc, fanart)
	elif mode == 10925:
		CATEGORIES10925(name, iconimage, desc, fanart)
	elif mode == 10926:
		CATEGORIES10926(name, iconimage, desc, fanart)
	elif mode == 10927:
		CATEGORIES10927(name, iconimage, desc, fanart)
	elif mode == 10928:
		CATEGORIES10928(name, iconimage, desc, fanart)
	elif mode == 10929:
		CATEGORIES10929(name, iconimage, desc, fanart)
	elif mode == 10930:
		CATEGORIES10930(name, iconimage, desc, fanart)
	
	elif mode == 11101:
		CATEGORIES11101(name, iconimage, desc, fanart)
	elif mode == 11102:
		CATEGORIES11102(name, iconimage, desc, fanart)
	elif mode == 11103:
		CATEGORIES11103(name, iconimage, desc, fanart)
	elif mode == 11104:
		CATEGORIES11104(name, iconimage, desc, fanart)
	elif mode == 11105:
		CATEGORIES11105(name, iconimage, desc, fanart)
	elif mode == 11106:
		CATEGORIES11106(name, iconimage, desc, fanart)
	elif mode == 11107:
		CATEGORIES11107(name, iconimage, desc, fanart)
	elif mode == 11108:
		CATEGORIES11108(name, iconimage, desc, fanart)
	elif mode == 11109:
		CATEGORIES11109(name, iconimage, desc, fanart)
		
	else: notification("?","","",1000)
	
	if mode != "" and mode != None and mode != 100:
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DURATION)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
		#xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL, name)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_NONE)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
		xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
		xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE, name)
		
		#xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE, name)
		printpoint = printpoint + "S"
	if mode != 17 and mode != 5 and mode != 21 and mode != 4 and mode != 9 and mode != 13 and mode != 3: # and mode != 20
		xbmcplugin.endOfDirectory(int(sys.argv[1]))
		printpoint = printpoint + "7"
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	printlog(title='pluginend', printpoint=printpoint, text=extra, level=0, option="")
	'''---------------------------'''
	return url, name, mode, iconimage, desc, num, viewtype, fanart
	
	
def pluginend2(admin, url, containerfolderpath, viewtype):
	printpoint = "" ; count = 0 ; countmax = 10 ; url = str(url) ; containerfolderpath2 = ""
	returned_Dialog, returned_Header, returned_Message = checkDialog(admin)
	
	#xbmc.sleep(1000) #TIME FOR DIALOGBUSY
	'''------------------------------
	---countmax-ADJUST---------------
	------------------------------'''
	if "plugin.video.10qtv" in url: countmax = 40
	'''---------------------------'''
	
	while (count < countmax and (returned_Dialog == "dialogbusyW" or returned_Dialog == "dialogprogressW")) or (count < 2 and returned_Dialog == "") and not xbmc.abortRequested:
		count += 1
		if count == 1: printpoint = printpoint + "1"
		xbmc.sleep(500)
		returned_Dialog, returned_Header, returned_Message = checkDialog(admin)
		'''---------------------------'''
		
	if count < countmax:
		printpoint = printpoint + "2"
		if count == 0: xbmc.sleep(1000)
		else: xbmc.sleep(500)
		containerfolderpath2 = xbmc.getInfoLabel('Container.FolderPath')
		if viewtype == None:
			'''------------------------------
			---viewtype-ADJUST---------------
			------------------------------'''
			printpoint = printpoint + "3"
			if containerfolderpath2 == 'plugin://'+addonID+'/?&': printpoint = printpoint + "4" ; viewtype = 50
			elif "http://nickjr.walla.co.il/" in url: viewtype = 50
			elif ("plugin.video.gozlan.me" in url or "plugin.video.seretil" in url or "plugin.video.supercartoons" in url or "plugin.video.sdarot.tv" in url or "seretil.me" in url): viewtype = 58
			'''---------------------------'''
		if containerfolderpath != containerfolderpath2 or "4" in printpoint: #GAL CHECK THIS! #containerfolderpath2 == "plugin://"+addonID+"/"
			printpoint = printpoint + "5"
			setView('', viewtype, containerfolderpath2)
			'''---------------------------'''
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "count" + space2 + str(count) + space + "returned_Dialog" + space2 + returned_Dialog + space + "containerfolderpath/2" + newline + \
	str(containerfolderpath) + newline + \
	str(containerfolderpath2) + newline + \
	"url" + space2 + str(url)
	printlog(title='pluginend2', printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''

	
def getCustom_Playlist(admin):
	'''Get the next new Item ID'''
	returned = "" ; printpoint = ""
	if Custom_Playlist1_ID  == "": returned = 'Custom_Playlist1_ID'
	elif Custom_Playlist2_ID  == "": returned = 'Custom_Playlist2_ID'
	elif Custom_Playlist3_ID  == "": returned = 'Custom_Playlist3_ID'
	elif Custom_Playlist4_ID  == "": returned = 'Custom_Playlist4_ID'
	elif Custom_Playlist5_ID  == "": returned = 'Custom_Playlist5_ID'
	elif Custom_Playlist6_ID  == "": returned = 'Custom_Playlist6_ID'
	elif Custom_Playlist7_ID  == "": returned = 'Custom_Playlist7_ID'
	elif Custom_Playlist8_ID  == "": returned = 'Custom_Playlist8_ID'
	elif Custom_Playlist9_ID  == "": returned = 'Custom_Playlist9_ID'
	elif Custom_Playlist10_ID  == "": returned = 'Custom_Playlist10_ID'
	'''---------------------------'''
	text = "returned" + space2 + str(returned) + space + "Custom_Playlist1_ID" + space2 + str(Custom_Playlist1_ID)
	printlog(title="getCustom_Playlist", printpoint=printpoint, text=text, level=2, option="")
	return returned

def getCustom_Playlist2(value):
	'''Get the current item ID'''
	returned = "" ; printpoint = "" ; TypeError = "" ; extra = ""
	
	if Custom_Playlist1_ID  == "": returned = 'Custom_Playlist1_ID'
	
	try:
		returned = Custom_PlaylistL.index(value)
		returned += 1
		returned = 'Custom_Playlist' + str(returned) + '_ID'
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	
	text = "returned" + space2 + str(returned) + newline + \
	"value" + space2 + str(value)
	printlog(title="getCustom_Playlist2", printpoint=printpoint, text=text, level=2, option="")
	return returned

def setCustom_Playlist_ID(Custom_Playlist_ID, New_ID, mode, url, name, num, viewtype):
	printpoint = "" ; extra = "" ; extra2 = "" ; New_Type = "" ; New_ID_ = "" ; New_IDL = "" ; DuplicatedL = [] ; IgnoredL = []
	Custom_Playlist_ID_ = getsetting(Custom_Playlist_ID)
	Custom_Playlist_ID_L = Custom_Playlist_ID_.split(',')
	
	if "list=" in New_ID:
		'''Playlist'''
		New_Type = localize(559) #Playlist
		extra = addonString_servicefeatherence(47).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(49).encode('utf-8') #New %s, Update Succesfully!
		New_ID = find_string(New_ID, "list=", "")
		New_ID = New_ID.replace("list=","&youtube_pl=")
		New_ID_ = New_ID.replace("&youtube_pl=","")
		'''---------------------------'''
	elif "/user/" in New_ID or "/channel/" in New_ID:
		'''Channel'''
		New_Type = localize(19029) #Channel
		extra = addonString_servicefeatherence(46).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(48).encode('utf-8') #New %s, Update Succesfully!
		if "/channel/" in New_ID:
			New_ID = find_string(New_ID, "/channel/", "")
			New_ID = New_ID.replace("/channel/", "&youtube_ch=")
		elif "/user/"    in New_ID:
			New_ID = find_string(New_ID, "/user/", "")
			New_ID = New_ID.replace("/user/", "&youtube_ch=")
			
		New_ID_ = New_ID.replace("&youtube_ch=","")
		'''---------------------------'''
	elif "watch?v=" in New_ID:
		'''Single Video'''
		New_Type = localize(157) #Video
		extra = addonString_servicefeatherence(46).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(48).encode('utf-8') #New %s, Update Succesfully!
		New_ID = find_string(New_ID, "watch?v=", "")
		New_ID = New_ID.replace("watch?v=", "&youtube_id=")
		New_ID_ = New_ID.replace("&youtube_id=","")
		'''---------------------------'''
	
	elif mode == 24:
		if New_ID == 'Custom':
			New_Type = 'New Custom'
		else:
			New_Type = 'Custom'
		New_ID = url
		New_ID_ = url
		extra = addonString_servicefeatherence(47).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(49).encode('utf-8') #New %s, Update Succesfully!
		
	elif New_ID == "None":
		New_Type = localize(2080) #Empty list
		extra = addonString_servicefeatherence(47).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(49).encode('utf-8') #New %s, Update Succesfully!
		New_ID_ = ""
		
	if New_Type != "":
		printpoint = printpoint + "1"
		New_IDL = CleanString2(New_ID, comma=True)
		New_IDL = New_IDL.split(',')
		for x in New_IDL:
			
			if 'commonsearch' in x:
				IgnoredL.append(x)
			elif x in Custom_Playlist_ID_L and x != "":
				DuplicatedL.append(x)
				if mode == 20 or mode == 21:
					check = dialogyesno(addonString_servicefeatherence(93).encode('utf-8'), localize(19194)) # Duplicated URL found!, Continue?
					if check == "ok": pass				
					else: notification_common("9") ; printpoint = printpoint + "8"
					break
				else:
					pass
					
			
		
		if mode == 24:
			for x in IgnoredL:
				New_IDL.remove(x)
			for x in DuplicatedL:
				New_IDL.remove(x)
			
				
			New_ID = CleanString2(New_IDL, comma=True)
			New_ID_ = New_ID
		
		if not "8" in printpoint and New_ID != "":
			printpoint = printpoint + "2"
			if mode == 20 or mode == 24 and New_Type == 'New Custom':
				setsetting(Custom_Playlist_ID, New_ID)
			elif mode == 21:
				setsetting(Custom_Playlist_ID, str(url) + "," + New_ID)
				#extra = "Previous ID: " + str(url)
			elif mode == 24:
				setsetting(Custom_Playlist_ID, Custom_Playlist_ID_ + "," + New_ID)
				
			else: notification_common("17") ; printpoint = printpoint + "9"
			#extra = addonString_servicefeatherence(46).encode('utf-8') % (New_Type) + space + addonString_servicefeatherence(48).encode('utf-8')
			if 'Custom' in New_Type: ID_Info = "" #'Source: ' + name
			else: ID_Info = "ID: " + str(New_ID_)
			
			if DuplicatedL != []:
				extra2 = 'Duplicated ID Ignored:[CR]' + str(DuplicatedL)
			dialogok(extra, str(name), ID_Info, extra2, line1c="yellow", line2c="yellow") ; xbmc.sleep(100)
			update_view(url, num, viewtype)
			'''---------------------------'''
		elif DuplicatedL != []: notification('Already exists in favourites!','','',2000)
		elif New_ID == "": notification('NO valid url has been detected!','','',2000)
		
	else: notification_common("17") ; printpoint = printpoint + "9"
	
	text = "name" + space2 + str(name) + space + 'mode' + space2 + str(mode) + newline + \
	"New_Type" + space2 + str(New_Type) + newline + \
	"New_ID" + space2 + str(New_ID) + newline + \
	"New_ID_" + space2 + str(New_ID_) + newline + \
	"New_IDL" + space2 + str(New_IDL) + newline + \
	"DuplicatedL" + space2 + str(DuplicatedL) + newline + \
	"IgnoredL" + space2 + str(IgnoredL) + newline + \
	"Custom_Playlist_ID_L" + space2 + str(Custom_Playlist_ID_L) + newline + \
	"Custom_Playlist_ID" + space2 + str(Custom_Playlist_ID) + newline
	printlog(title="setCustom_Playlist_ID", printpoint=printpoint, text=text, level=2, option="")
	'''---------------------------'''

def AdvancedCustom(mode, name, url, thumb, desc, num, viewtype, fanart):
	'''------------------------------
	---Save and Load your addon-design
	------------------------------'''
	printpoint = "" ; extra = "" ; formula = "" ; formula_ = "" ; path = "" ; file = "" ; returned = "" ; returned2 = ""; returned3 = "" ; y = "s" ; custommediaL = [] ; list2_ = [] ; list2 = [] ; filesT_ = []
	
	if num == 's':
		list = ['-> (Exit)']
		list.append(localize(190) + space + localize(593)) #Save All
		list.append(addonString_servicefeatherence(51).encode('utf-8') + space + localize(593) + space + "[LOCAL]") #Load All [LOCAL]
		list.append(addonString_servicefeatherence(51).encode('utf-8') + space + localize(593) + space + "[REMOTE]") #Load All [REMOTE] 
		list.append('Remove all buttons') #Remove-All-Buttons
		
		y = "s"
		'''---------------------------'''
	else:
		list = ['-> (Exit)']
		list.append(localize(190) + space + addonString_servicefeatherence(57).encode('utf-8')) #Save One
		list.append(addonString_servicefeatherence(51).encode('utf-8') + space + addonString_servicefeatherence(57).encode('utf-8') + space + "[LOCAL]") #Load One [LOCAL]
		list.append(addonString_servicefeatherence(51).encode('utf-8') + space + addonString_servicefeatherence(57).encode('utf-8') + space + "[REMOTE]") #Load One [REMOTE]
		y = ""
		
		Custom_Playlist_ID = "Custom_Playlist" + num + "_ID"
		if Custom_Playlist_ID == "": notification("Error ID", "Use featherence Debug addon for support", "", 2000) ; printpoint = printpoint + "9"
		Custom_Playlist_Name = "Custom_Playlist" + num + "_Name"
		Custom_Playlist_Thumb = "Custom_Playlist" + num + "_Thumb"
		Custom_Playlist_Description = "Custom_Playlist" + num + "_Description"
		Custom_Playlist_Fanart = "Custom_Playlist" + num + "_Fanart"
		'''---------------------------'''
	returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
	
	if returned == -1: printpoint = printpoint + "9"
	elif returned == 0: printpoint = printpoint + "8"
	else: printpoint = printpoint + "7"
		
	if ("7" in printpoint or value != "") and not "8" in printpoint and not "9" in printpoint:
		
		if returned == 1 or returned == 2: path = os.path.join(addondata_path, addonID, '') #SAVE /LOAD [LOCAL]
		elif returned == 3: path = os.path.join(addonPath, 'resources', 'templates', '') #LOAD [REMOTE]
		elif returned == 4: pass #REMOVE ALL
		else: path = ""
		
		list2 = ['-> (Exit)'] ; list2_ = ['-> (Exit)']
		if returned == 1:
			list2.append('New')
			list2_.append('New')
		elif returned == 3:
			check = dialogyesno(addonString_servicefeatherence(96).encode('utf-8') % addonString(100).encode('utf-8'), addonString_servicefeatherence(99).encode('utf-8')) #Share My Music buttons, Choose YES to learn how to share Your Music button
			if check == 'ok':
				header = addonString_servicefeatherence(96).encode('utf-8') % addonString(100).encode('utf-8')
				msg1 = localize(190) + space + localize(592) ; msg1.decode('utf-8').encode('utf-8') #; msg1 = '[B]' + msg1 + '[/B]'
				msg2 = os.path.join(addondata_path, addonID) ; msg2 = msg2.decode('utf-8').encode('utf-8')
				message = "1. " + addonString_servicefeatherence(95).encode('utf-8') % (msg1) + ".[CR]" + "2. " + addonString_servicefeatherence(97).encode('utf-8') + "[CR]" + msg2 + ".[CR]" + "3. " + addonString_servicefeatherence(52).encode('utf-8') + "[CR]" + "4. " + addonString_servicefeatherence(53).encode('utf-8') % ("templates") + "[CR]" + "5. " + addonString_servicefeatherence(54).encode('utf-8') + ".[CR]" + "6. " + addonString_servicefeatherence(98).encode('utf-8') + ".[CR]" + "7. " + addonString_servicefeatherence(55).encode('utf-8') + ".[CR]" + "8. " + addonString_servicefeatherence(56).encode('utf-8') % ("Commit") + ".[CR][CR]" + "*You should now wait for the next addon update."
				diaogtextviewer(header,message)
				
		if path != "":
			'''read existing files'''
			filesT = {}
			AddonName = addonID.replace('plugin.video.', "", 1)
			AddonName = AddonName + str(y) + '_'
			for files in os.listdir(path):
				filesname = ""
				if '.zip' in files and not '.txt' in files:
					if AddonName in files:
						filesname = regex_from_to(files, AddonName, ".zip", excluding=True)
						if filesname != "" and filesname != None:
							filesT_ = { filesname: files }
							filesT.update(filesT_)
							filedate = getFileAttribute(1, path + files, option="1")
							list2_.append(filesname + space + '-(' + str(filedate) + ')')
							list2.append(filesname)
							extra = 'files' + space2 + to_utf8(files) + newline + 'filesname' + space2 + to_utf8(filesname)
							#print extra 
							'''---------------------------'''
			
			returned2, value2 = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list2_,0)
			
			if returned2 == -1: printpoint = printpoint + "9"
			elif returned2 == 0: printpoint = printpoint + "8"
			else: printpoint = printpoint + "7"
				
			if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
				if returned == 1: printpoint = printpoint + "A" #SAVE
				elif returned == 2: printpoint = printpoint + "B" #LOAD
				elif returned == 3: printpoint = printpoint + "C" #TEMPLATES
		
				if "A" in printpoint:
					if returned2 > 1:
						yesno = dialogyesno('Overwrite' + space + str(list2[returned2]) + '?','Choose YES to continue')
						if yesno == 'skip': printpoint = printpoint + '9'
					if not '9' in printpoint:
						formula = ""
						if y == "s":
							'''save all'''
							min = 1
							max = 11
						else:
							'''save one'''
							min = int(num)
							max = int(num) + 1
							
						for i in range(min,max):

							Custom_Playlist_ID_ = "Custom_Playlist" + str(i) + "_ID"
							Custom_Playlist_Name_ = "Custom_Playlist" + str(i) + "_Name"
							Custom_Playlist_Thumb_ = "Custom_Playlist" + str(i) + "_Thumb"
							Custom_Playlist_Description_ = "Custom_Playlist" + str(i) + "_Description"
							Custom_Playlist_Fanart_ = "Custom_Playlist" + str(i) + "_Fanart"
							
							Custom_Playlist_ID__ = getsetting(Custom_Playlist_ID_)
							Custom_Playlist_Name__ = getsetting(Custom_Playlist_Name_)
							Custom_Playlist_Thumb__ = getsetting(Custom_Playlist_Thumb_)
							Custom_Playlist_Description__ = getsetting(Custom_Playlist_Description_)
							Custom_Playlist_Fanart__ = getsetting(Custom_Playlist_Fanart_)
							
							if Custom_Playlist_ID__ == "":
								
								formula = formula + newline + Custom_Playlist_ID_ + "=5" + ""
								formula = formula + newline + Custom_Playlist_Name_ + "=5" + ""
								formula = formula + newline + Custom_Playlist_Thumb_ + "=5" + ""
								formula = formula + newline + Custom_Playlist_Description_ + "=5" + ""
								formula = formula + newline + Custom_Playlist_Fanart_ + "=5" + ""
							
							else:
								formula = formula + newline + Custom_Playlist_ID_ + "=5" + Custom_Playlist_ID__
								formula = formula + newline + Custom_Playlist_Name_ + "=5" + Custom_Playlist_Name__
								x2, x2_ = TranslatePath(Custom_Playlist_Thumb__)
								formula, custommediaL, = GeneratePath(Custom_Playlist_Thumb_ + "=5", formula, custommediaL, x2, x2_, ignoreL=[])
										
								formula = formula + newline + Custom_Playlist_Description_ + "=5" + Custom_Playlist_Description__
								x2, x2_ = TranslatePath(Custom_Playlist_Fanart__)
								formula, custommediaL, = GeneratePath(Custom_Playlist_Fanart_ + "=5", formula, custommediaL, x2, x2_, ignoreL=[])
							
							extra = extra + newline + 'i' + space2 + str(i) + space + 'Custom_Playlist_ID_' + space2 + str(Custom_Playlist_ID_) + space + 'Custom_Playlist_ID__' + space2 + str(Custom_Playlist_ID__)
							
						if returned2 == 1: filename = ""
						else: filename = str(list2[returned2])
						
						filename = dialogkeyboard(filename, localize(21821), 0, "", "", "") #Description
						if filename != 'skip' and filename != "":
							formula = to_utf8(formula)
						
							write_to_file(featherenceserviceaddondata_media_path + AddonName + ".txt", str(formula), append=False, silent=True, utf8=False) ; xbmc.sleep(200)
							if not os.path.exists(featherenceserviceaddondata_media_path + AddonName + ".txt"):
								notification_common('17')
								extra = extra + newline + featherenceserviceaddondata_media_path + AddonName + ".txt" + space + 'Is not found!'
							else:
								removefiles(path + AddonName + to_unicode(list2[returned2]) + '.zip')
								zipname = path + AddonName + str(filename).decode('utf-8')
								if custommediaL == []:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=[AddonName + '.txt'], filteroff=[], level=10000, append=False, ZipFullPath=False, temp=False)
								else:
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=[AddonName + '.txt'], filteroff=[], level=10000, append=False, ZipFullPath=False, temp=True)
									CreateZip(featherenceserviceaddondata_media_path, zipname, filteron=custommediaL, filteroff=[], level=10000, append='End', ZipFullPath=False, temp=True)
								notification(addonString_servicefeatherence(58).encode('utf-8'), str(filename), "", 4000) #Saved Succesfully!, 
								'''---------------------------'''
						else: notification_common('9') ; extra = extra + newline + 'filename is empty!'
						
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
						if os.path.exists(featherenceservice_addondata_path + AddonName + '.txt'):
							removefiles(featherenceservice_addondata_path + AddonName + '.txt')
							
						ExtractAll(path + file, featherenceservice_addondata_path) ; xbmc.sleep(200)
						
						if not os.path.exists(featherenceservice_addondata_path + AddonName + '.txt'):
							notification(AddonName + ".txt is missing!", "Check your zip file!", "", 4000)
						else:
							if y == 's':
								yesno = dialogyesno('Overwrite All buttons?' + '?','Choose YES to continue')
								if yesno == 'skip': printpoint = printpoint + '9'
							else:
								yesno = dialogyesno('Overwrite' + space + xbmc.getInfoLabel('ListItem.Label') + '?','Choose YES to continue')
								if yesno == 'skip': printpoint = printpoint + '9'
								
							if not '9' in printpoint:
								printpoint = printpoint + "V"
								#print file
								import fileinput
								for line in fileinput.input(featherenceservice_addondata_path + AddonName + '.txt'):
									x = "" ; x1 = "" ; x2 = "" ; x3 = ""
									if "=5" in line:
										'''setsetting'''
										x1 = regex_from_to(line, 'Custom_Playlist', '=5', excluding=False)
										x2 = line.replace(x1,"")
										x2 = x2.replace('\n', '')
										x1 = x1.replace('=5',"")
										
										
										if y == "":
											x1_ = regex_from_to(x1, 'Custom_Playlist', '_', excluding=True) #count
											x1__ = x1.replace('Custom_Playlist' + x1_ + '_','Custom_Playlist' + str(num) + '_')
											setsetting(str(x1__), str(x2))
										else:
											setsetting(str(x1), str(x2))
										
									extra = extra + newline + space + "line" + space2 + str(line) + space + "x " + space2 + str(x) + space + "x1" + space2 + str(x1) + space + "x2" + space2 + str(x2) + space + "x3" + space2 + str(x3)
									'''---------------------------'''	
		elif returned == 4:
			'''------------------------------
			---Remove-All-Buttons------------
			------------------------------'''
			Custom_Playlist_NameL = [Custom_Playlist1_Name, Custom_Playlist2_Name, Custom_Playlist3_Name, Custom_Playlist4_Name, Custom_Playlist5_Name, Custom_Playlist6_Name, Custom_Playlist7_Name, Custom_Playlist8_Name, Custom_Playlist9_Name, Custom_Playlist10_Name]
			returned = dialogyesno('Remove ALL buttons' + '[CR]' + str(Custom_Playlist_NameL),localize(19194)) #Remove Button, Continue?
			if returned == "ok":
				for x in range(1,11):
					setsetting('Custom_Playlist' + str(x) + '_ID', "")
					setsetting('Custom_Playlist' + str(x) + '_Name', "")
					setsetting('Custom_Playlist' + str(x) + '_Thumb', "")
					setsetting('Custom_Playlist' + str(x) + '_Description', "")
					setsetting('Custom_Playlist' + str(x) + '_Fanart', "")
					'''---------------------------'''
				if desc != "": extra1 = localize(21821) + space2 + str(desc)
				else: extra1 = ""
				dialogok(localize(50) + space + addonString_servicefeatherence(43).encode('utf-8') + '[CR]' + str(name), "ID" + space2 + str(url), "", extra1)
				'''---------------------------'''
		else: printpoint = printpoint + '9'	
				
	if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
		if not "Q" in printpoint and not "A" in printpoint:
			notification(".","","",1000)
			xbmc.sleep(500)
			notification("..","","",1000)
			update_view(url, num, viewtype)
			'''---------------------------'''
	
	text = 'name_' + space2 + name + "_LV" + printpoint + space + newline + \
	"path" + space2 + str(path) + newline + \
	"list" + space2 + str(list) + space + 'returned' + space2 + str(returned) + newline + \
	"list2" + space2 + str(list2) + space + 'returned2' + space2 + str(returned2) + newline + \
	"list2_" + space2 + str(list2) + space + 'returned2_' + newline + \
	"file" + space2 + str(file) + newline + \
	"filesT_" + space2 + str(filesT_) + newline + \
	"formula" + space2 + str(formula) + space + "formula_" + space2 + str(formula_) + newline + \
	"extra" + space2 + str(extra)
	printlog(title="AdvancedCustom", printpoint=printpoint, text=text, level=2, option="")
		
def AddCustom(mode, name, url, iconimage, desc, num, viewtype, fanart):
	'''------------------------------
	---New-Button--------------------
	------------------------------'''
	printpoint = "" ; New_Type = "" ; New_ID = "" ; New_Name = "" ; value = "" ; value2 = ""
	Custom_Playlist_ID = getCustom_Playlist(admin)
	Custom_Playlist_Name = Custom_Playlist_ID.replace("_ID","_Name")
	if Custom_Playlist_ID == "": notification("Playlist limit reached!", "You may delete some playlists and try again!", "", 4000)
	elif mode == 24:
		'''from Menu'''
		#Custom_Playlist_ID = "Custom_Playlist" + num + "_ID"
		#if Custom_Playlist_ID == "": notification("Error ID", "Use featherence Debug addon for support", "", 2000) ; printpoint = printpoint + "9"
		#Custom_Playlist_Name = "Custom_Playlist" + num + "_Name"
		#Custom_Playlist_Thumb = "Custom_Playlist" + num + "_Thumb"
		#Custom_Playlist_Description = "Custom_Playlist" + num + "_Description"
		#Custom_Playlist_Fanart = "Custom_Playlist" + num + "_Fanart"
		
		list = ['-> (Exit)', 'New']
		for x in Custom_PlaylistL:
			if x != "":
				x2 = Custom_Playlist_NameT.get(x)
				x2 = to_utf8(x2)
				list.append(x2) #NAME
		returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
		
		if returned == -1: pass
		elif returned == 0: pass
		elif returned == 1:
			printpoint = printpoint + "1"
			New_Name = dialogkeyboard('My Button', "Button Name", 0, "",Custom_Playlist_Name, "0")
			setCustom_Playlist_ID(Custom_Playlist_ID, 'New Custom', mode, url, New_Name, num, viewtype)
		else:
			printpoint = printpoint + "2"
			New_Name = value
			value2 = Custom_Playlist_NameT2.get(value) #ID
			Custom_Playlist_ID = getCustom_Playlist2(value2)
			setCustom_Playlist_ID(Custom_Playlist_ID, url, mode, url, New_Name, num, viewtype)
			
	else:
		New_ID = dialogkeyboard("", "Enter YouTube URL", 0, "5", "" , "")
		if New_ID != "skip":
			New_Name = dialogkeyboard('My Button', "Button Name", 0, "",Custom_Playlist_Name, "0")
			if New_Name != "skip":
				setCustom_Playlist_ID(Custom_Playlist_ID, New_ID, mode, url, New_Name, num, viewtype)
				
	text = "mode" + space2 + str(mode) + space + "name" + space2 + str(name) + newline + \
	"New_Type" + space2 + str(New_Type) + newline + \
	"New_ID" + space2 + str(New_ID) + newline + \
	"New_Name" + space2 + str(New_Name) + newline + \
	"value" + space2 + str(value) + newline + \
	"value2" + space2 + str(value2) + newline + \
	"url" + space2 + str(url) + newline + \
	"iconimage" + space2 + str(iconimage) + newline
	printlog(title="AddCustom", printpoint=printpoint, text=text, level=2, option="")
	'''---------------------------'''
	
def CheckMoveCustom(name, num):
	extra = "" ; printpoint = "" ; down = "" ; up = ""
	
	'''---------------------------'''
	if num == "1":
		'''---------------------------'''
		if Custom_PlaylistL[1] != "": down = "2"
		elif Custom_PlaylistL[2] != "": down = "3"
		elif Custom_PlaylistL[3] != "": down = "4"
		elif Custom_PlaylistL[4] != "": down = "5"
		elif Custom_PlaylistL[5] != "": down = "6"
		elif Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "2":
		if Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[2] != "": down = "3"
		elif Custom_PlaylistL[3] != "": down = "4"
		elif Custom_PlaylistL[4] != "": down = "5"
		elif Custom_PlaylistL[5] != "": down = "6"
		elif Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "3":
		if Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[3] != "": down = "4"
		elif Custom_PlaylistL[4] != "": down = "5"
		elif Custom_PlaylistL[5] != "": down = "6"
		elif Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "4":
		if Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[4] != "": down = "5"
		elif Custom_PlaylistL[5] != "": down = "6"
		elif Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "5":
		if Custom_PlaylistL[3] != "": up = "4"
		elif Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[5] != "": down = "6"
		elif Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "6":
		if Custom_PlaylistL[4] != "": up = "5"
		elif Custom_PlaylistL[3] != "": up = "4"
		elif Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[6] != "": down = "7"
		elif Custom_PlaylistL[7] != "": down = "8"
		elif Custom_PlaylistL[8] != "": down = "9"
		elif Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "7":
		if Custom_PlaylistL[6] != "": up = "7"
		elif Custom_PlaylistL[5] != "": up = "6"
		elif Custom_PlaylistL[4] != "": up = "5"
		elif Custom_PlaylistL[3] != "": up = "4"
		elif Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[8] != "": up = "9"
		elif Custom_PlaylistL[9] != "": up = "10"
		'''---------------------------'''
	elif num == "8":
		if Custom_PlaylistL[7] != "": up = "8"
		elif Custom_PlaylistL[6] != "": up = "7"
		elif Custom_PlaylistL[5] != "": up = "6"
		elif Custom_PlaylistL[4] != "": up = "5"
		elif Custom_PlaylistL[3] != "": up = "4"
		elif Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
		if Custom_PlaylistL[9] != "": down = "10"
		'''---------------------------'''
	elif num == "10":
		if Custom_PlaylistL[8] != "": up = "9"
		elif Custom_PlaylistL[7] != "": up = "8"
		elif Custom_PlaylistL[6] != "": up = "7"
		elif Custom_PlaylistL[5] != "": up = "6"
		elif Custom_PlaylistL[4] != "": up = "5"
		elif Custom_PlaylistL[3] != "": up = "4"
		elif Custom_PlaylistL[2] != "": up = "3"
		elif Custom_PlaylistL[1] != "": up = "2"
		elif Custom_PlaylistL[0] != "": up = "1"
		'''---------------------------'''
	
	text = "name" + space2 + str(name) + space + "num" + space2 + str(num) + space + "down" + space2 + str(down) + space + "up" + space2 + str(up)
	printlog(title="CheckMoveCustom", printpoint=printpoint, text=text, level=2, option="")
		
	return up, down

def cleanfanartCustom(fanart):
	printpoint = ""
	fanart2 = fanart.replace("/","")
	fanart2 = fanart2.replace("\\","")
	addonFanart2 = addonFanart.replace("/","")
	addonFanart2 = addonFanart2.replace("\\","")
	if fanart2 == addonFanart2:
		printpoint = printpoint + "7"
		fanart = "" # or not os.path.exists(fanart)
	
	text = "fanart" + space2 + str(fanart) + newline + \
	"fanart2" + space2 + str(fanart2) + newline + \
	"addonFanart" + space2 + str(addonFanart) + newline + \
	"addonFanart2" + space2 + str(addonFanart2)
	printlog(title="cleanfanartCustom", printpoint=printpoint, text=text, level=2, option="")
	return fanart
	
def MoveCustom(mode, name, url, iconimage, desc, num, viewtype, fanart):
	'''23'''
	printpoint = ""
	'''---------------------------'''
	if not "__" in num: printpoint = printpoint + "9"
	else:
		printpoint = printpoint + "1"
		num = num.split("__")
		num1 = num[0]
		num2 = num[1]
	try:
		test = int(num1) + 1
		test = int(num2) + 1
	except Exception, TypeError: printpoint = printpoint + "9"
	
	fanart = cleanfanartCustom(fanart)
	
	if not "9" in printpoint:
		printpoint = printpoint + "3"
		Custom_Playlist_ID = "Custom_Playlist" + num1 + "_ID"
		if Custom_Playlist_ID == "": notification("Error ID", "Use featherence Debug addon for support", "", 2000) ; printpoint = printpoint + "9"
		Custom_Playlist_Name = "Custom_Playlist" + num1 + "_Name"
		Custom_Playlist_Thumb = "Custom_Playlist" + num1 + "_Thumb"
		Custom_Playlist_Description = "Custom_Playlist" + num1 + "_Description"
		Custom_Playlist_Fanart = "Custom_Playlist" + num1 + "_Fanart"
		'''---------------------------'''
		Custom_Playlist_ID2 = "Custom_Playlist" + str(num2) + "_ID"
		if Custom_Playlist_ID2 == "": notification("Error ID", "Use featherence Debug addon for support", "", 2000) ; printpoint = printpoint + "9"
		Custom_Playlist_Name2 = "Custom_Playlist" + str(num2) + "_Name"
		Custom_Playlist_Thumb2 = "Custom_Playlist" + str(num2) + "_Thumb"
		Custom_Playlist_Description2 = "Custom_Playlist" + str(num2) + "_Description"
		Custom_Playlist_Fanart2 = "Custom_Playlist" + str(num2) + "_Fanart"
		'''---------------------------'''
	
	if not "9" in printpoint:
		printpoint = printpoint + "7"
		'''---------------------------'''
		setsetting(Custom_Playlist_ID, getsetting(Custom_Playlist_ID2))
		setsetting(Custom_Playlist_Name, getsetting(Custom_Playlist_Name2))
		setsetting(Custom_Playlist_Thumb, getsetting(Custom_Playlist_Thumb2))
		setsetting(Custom_Playlist_Description, getsetting(Custom_Playlist_Description2))
		setsetting(Custom_Playlist_Fanart, getsetting(Custom_Playlist_Fanart2))
		'''---------------------------'''
		setsetting(Custom_Playlist_ID2, url)
		setsetting(Custom_Playlist_Name2, name)
		setsetting(Custom_Playlist_Thumb2, iconimage)
		setsetting(Custom_Playlist_Description2, desc)
		setsetting(Custom_Playlist_Fanart2, fanart)
		'''---------------------------'''
		update_view(url, num, viewtype)
	
	text = "url" + space2 + str(url) + space + "num" + space2 + str(num)
	printlog(title="MoveCustom", printpoint=printpoint, text=text, level=2, option="")
		
def ManageCustom(mode, name, url, thumb, desc, num, viewtype, fanart):
	extra = "" ; printpoint = "" ; New_ID = ""
	
	Custom_Playlist_ID = "Custom_Playlist" + num + "_ID"
	if Custom_Playlist_ID == "": notification("Error ID", "Use featherence Debug addon for support", "", 2000) ; printpoint = printpoint + "9"
	Custom_Playlist_Name = "Custom_Playlist" + num + "_Name"
	Custom_Playlist_Thumb = "Custom_Playlist" + num + "_Thumb"
	Custom_Playlist_Description = "Custom_Playlist" + num + "_Description"
	Custom_Playlist_Fanart = "Custom_Playlist" + num + "_Fanart"
	
	if printpoint != "9":
		list = ['-> (Exit)']
		list.append(addonString_servicefeatherence(38).encode('utf-8')) #Edit URL
		list.append(addonString_servicefeatherence(41).encode('utf-8')) #Rename Button
		if thumb == "": list.append(addonString_servicefeatherence(36).encode('utf-8')) #Add Thumb
		else: list.append(addonString_servicefeatherence(37).encode('utf-8')) #Remove Thumb
		if desc == "": list.append(addonString_servicefeatherence(32).encode('utf-8')) #Add Description
		else: list.append(addonString_servicefeatherence(33).encode('utf-8')) #Edit Description
		fanart = cleanfanartCustom(getsetting(Custom_Playlist_Fanart))
		if fanart == "": list.append(addonString_servicefeatherence(34).encode('utf-8')) #Add Fanart
		else: list.append(addonString_servicefeatherence(35).encode('utf-8')) #Remove Fanart
		list.append(localize(13336)) #Remove Button

		returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
			
		if returned == -1: printpoint = printpoint + "9"
		elif returned == 0: printpoint = printpoint + "8"
		else: printpoint = printpoint + "7"
	
	if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
		if returned == 1: printpoint = printpoint + "A" #Edit URL
		elif returned == 2: printpoint = printpoint + "B" #Rename
		elif returned == 3: printpoint = printpoint + "C" #Add/Remove Thumb
		elif returned == 4: printpoint = printpoint + "D" #Add/Edit Description
		elif returned == 5: printpoint = printpoint + "E" #Add/Remove Fanart
		elif returned == 6: printpoint = printpoint + "F" #Remove Button
		'''---------------------------'''
	if "A" in printpoint:
		'''------------------------------
		---Edit-URL----------------------
		------------------------------'''
		list = ['-> (Exit)']
		list.append(addonString_servicefeatherence(42).encode('utf-8')) #View URL
		list.append(addonString_servicefeatherence(40).encode('utf-8')) #Add URL
		list.append(addonString_servicefeatherence(39).encode('utf-8')) #Remove URL
		
		returned2, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
			
		if returned2 == -1: printpoint = printpoint + "9"
		elif returned2 == 0: printpoint = printpoint + "8"
		else: printpoint = printpoint + "7"
		
		if returned2 == 1: printpoint = printpoint + "1" #View URL
		elif returned2 == 2: printpoint = printpoint + "2" #Add URL
		elif returned2 == 3: printpoint = printpoint + "3" #Remove URL
		
		if "1" in printpoint:
			'''------------------------------
			---View-URL----------------------
			------------------------------'''
			message2 = "" ; i = 0
			url2 = url.split(",")
			for x in url2:
				i += 1
				x2 = ""
				if "&youtube_ch=" in x:
					x = x.replace("&youtube_ch=","")
					x2 = space + "[" + "YouTube Channel" + "]"
					'''---------------------------'''
				elif "&youtube_pl=" in x:
					x = x.replace("&youtube_pl=","")
					x2 = space + "[" + "YouTube Playlist" + "]"
					'''---------------------------'''
				elif "&youtube_id=" in x:
					x = x.replace("&youtube_id=","")
					x2 = space + "[" + "YouTube Video" + "]"
					'''---------------------------'''
				if x2 != "": message2 = message2 + '[CR]' + str(i) + space2 + str(x) + str(x2)
				'''---------------------------'''
			header = addonString_servicefeatherence(42).encode('utf-8') + space2 + str(name)
			if message2 != "": message = message2 + '[CR][CR]' + addonString_servicefeatherence(89).encode('utf-8')
			else: message = addonString_servicefeatherence(90).encode('utf-8') #URL Error occured.
			diaogtextviewer(header,message)
			'''---------------------------'''
			
		elif "2" in printpoint:
			'''------------------------------
			---Add-URL-----------------------
			------------------------------'''
			New_ID = dialogkeyboard("", addonString_servicefeatherence(40).encode('utf-8'), 0, "5", "" , "")
			setCustom_Playlist_ID(Custom_Playlist_ID, New_ID, mode, url, name, num, viewtype)
			
				
		elif "3" in printpoint:
			'''------------------------------
			---Remove-URL--------------------
			------------------------------'''
			list = ['-> (Exit)']
			url2 = url.split(',')
			i = 0
			for x in url2:
				i += 1
				list.append(x)

			returned2, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)
				
			if returned2 == -1: printpoint = printpoint + "9"
			elif returned2 == 0: printpoint = printpoint + "8"
			else: printpoint = printpoint + "7"
			
			if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
				
				if i == 1:
					'''Warning 1 URL found!'''
					check = dialogyesno(localize(13336), addonString_servicefeatherence(92).encode('utf-8') + '[CR]' + addonString_servicefeatherence(91).encode('utf-8'))
					if check == "ok":
						'''Remove Button'''
						printpoint = printpoint + "F"
					else:
						'''Skip'''
				else:
					if value + "," in url:
						'''multi links'''
						value2 = url.replace(value + ",","",1)
					elif value in url:
						'''single link'''
						value2 = url.replace(value,"",1)
					else: value2 = ""
					if value2 == "": notification_common("17")
					else:
						setsetting(Custom_Playlist_ID, value2)
						notification(addonString_servicefeatherence(44).encode('utf-8') + space + addonString_servicefeatherence(43).encode('utf-8'),str(name), "", 4000) #URL Removed Succesfully!
						'''---------------------------'''
				
	elif "B" in printpoint:
		'''------------------------------
		---Rename-Button-----------------
		------------------------------'''
		New_Name = dialogkeyboard(name, addonString_servicefeatherence(41).encode('utf-8'), 0, "", Custom_Playlist_Name, "0")
		if New_Name != "skip" and New_Name != name:
			notification(addonString_servicefeatherence(45).encode('utf-8') + space + addonString_servicefeatherence(30).encode('utf-8'), str(name), "", 4000) #Button Name Update Succesfully!
			'''---------------------------'''
		
	elif "C" in printpoint:
		if thumb == "":
			'''------------------------------
			---Add-Thumb---------------------
			------------------------------'''
			New_Thumb = ""
			returned = dialogyesno(str(name), addonString_servicefeatherence(31).encode('utf-8'), nolabel=localize(20017), yeslabel=localize(20015))
			if returned == 'ok':
				'''remote'''
				x = localize(20015) #Remote thumb
				value = dialogkeyboard("", x + space + "URL", 0, "1", "", "")
				if value != "skip":
					returned = urlcheck(value, ping=False)
					if returned != "ok":
						notification("URL Error", "Try again..", "", 2000)
						header = "URL Error"
						message = "Examine your URL for errors:" + newline + '[B]' + str(value) + '[/B]'
						diaogtextviewer(header,message)
					else:
						New_Thumb = value
			else:
				'''local'''
				x = localize(20017) #Local thumb
				xbmc.executebuiltin('Skin.SetString('+addonID+'_Temp,)')
				xbmc.executebuiltin('Skin.SetImage('+addonID+'_Temp,)') ; xbmc.sleep(4000)
				dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
				while dialogfilebrowserW and not xbmc.abortRequested:
					xbmc.sleep(500)
					dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
					xbmc.sleep(500)
				xbmc.sleep(500)
				New_Thumb = xbmc.getInfoLabel('Skin.String('+addonID+'_Temp)')
			
			if New_Thumb != "":
				setsetting(Custom_Playlist_Thumb, New_Thumb)
				notification(str(x) + space + addonString_servicefeatherence(30).encode('utf-8'), str(name), "", 4000) #Thumb* Update Succesfully!
				'''---------------------------'''
		else:
			'''------------------------------
			---Remove-Thumb------------------
			------------------------------'''
			if os.path.exists(thumb): x = localize(20017) #Local thumb
			else: x = localize(20015)
			setsetting(Custom_Playlist_Thumb, "")
			notification(str(x) + space + addonString_servicefeatherence(43).encode('utf-8'), str(name), "", 2000) #Thumb* Removed Succesfully!
			'''---------------------------'''
			
	elif "D" in printpoint:
		'''------------------------------
		---Add-Description---------------
		------------------------------'''
		returned, value = getRandom("0", min=0, max=100, percent=50)
		if int(value) <= 10: notification("Tip New Line:", "[CR]", "", 4000)
		elif int(value) <= 20: notification("Tip Bold:", "[B]text[/B]", "", 4000)
		elif int(value) <= 30: notification("Tip Color:", "[COLOR=X]text[/COLOR]", "", 4000)
		elif int(value) <= 40: notification("Tip Italic:", "[I]text[/I]", "", 4000)
		
		if Custom_Playlist_Description == "": extra1 = addonString_servicefeatherence(32).encode('utf-8') #Add Description
		else: extra1 = addonString_servicefeatherence(33).encode('utf-8') #Edit Description
		
		returned = dialogkeyboard(desc, extra1, 0, "", Custom_Playlist_Description, "0")
		if returned != "skip":
			if returned == "": extra2 = addonString_servicefeatherence(43).encode('utf-8') #Removed Succesfully!
			else: extra2 = addonString_servicefeatherence(30).encode('utf-8') #Update Succesfully!
			if returned != desc: notification(localize(21821) + space + extra2, str(name), "", 4000) #Description Update/Removed Succesfully!
			'''---------------------------'''
	
	elif "E" in printpoint:
		
		if fanart == "":
			'''------------------------------
			---Add-Fanart----------------
			------------------------------'''
			New_Fanart = ""
			returned = dialogyesno(str(name), addonString_servicefeatherence(31).encode('utf-8'), nolabel=localize(20438), yeslabel=localize(20441))
			if returned == 'ok':
				'''remote'''
				x = localize(20441) #Remote fanart
				value = dialogkeyboard("", localize(20441), 0, "1", "", "")
				if value != "skip":
					returned2 = urlcheck(value, ping=False)
					if returned2 != "ok":
						notification("URL Error", "Try again..", "", 2000)
						header = "URL Error"
						message = "Examine your URL for errors:" + newline + '[B]' + str(value) + '[/B]'
						diaogtextviewer(header,message)
					else:
						New_Fanart = value
			else:
				'''local'''
				x = localize(20438) #Local fanart
				xbmc.executebuiltin('Skin.SetString('+addonID+'_Temp,)')
				xbmc.executebuiltin('Skin.SetImage('+addonID+'_Temp,)') ; xbmc.sleep(4000)
				dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
				while dialogfilebrowserW and not xbmc.abortRequested:
					xbmc.sleep(500)
					dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
					xbmc.sleep(500)
				xbmc.sleep(500)
				New_Fanart = xbmc.getInfoLabel('Skin.String('+addonID+'_Temp)')
			
			if New_Fanart != "":
				setsetting(Custom_Playlist_Fanart, New_Fanart)
				 
				notification(str(x) + space + addonString_servicefeatherence(30).encode('utf-8'), str(New_Fanart), "", 2000) #Fanart* Update Succesfully!
				xbmc.sleep(2000)
				if Fanart_Enable != "true": notification(addonString_servicefeatherence(28).encode('utf-8') + space + localize(24023) + "!", "->" + localize(1045), "", 4000) # Allow Backgrounds disabled, ->Add-on settings
				elif Fanart_EnableCustom != "true": notification(localize(21389) + space + localize(24023) + "!", "->" + localize(1045), "", 4000) # Enable custom background disabled, ->Add-on settings
				'''---------------------------'''
		else:
			'''------------------------------
			---Remove-Fanart------------
			------------------------------'''
			setsetting(Custom_Playlist_Fanart, "")
			notification(localize(33068) + space + localize(19179) + "!", str(name), "", 4000) #Background Deleted!
			'''---------------------------'''
			
	if "F" in printpoint:
		if Custom_Playlist_Description != "":
			'''------------------------------
			---Remove-Button-----------------
			------------------------------'''
			returned = dialogyesno(localize(13336) + '[CR]' + str(name),localize(19194)) #Remove Button, Continue?
			if returned == "ok":
				setsetting(Custom_Playlist_ID, "")
				setsetting(Custom_Playlist_Name, "")
				setsetting(Custom_Playlist_Thumb, "")
				setsetting(Custom_Playlist_Description, "")
				setsetting(Custom_Playlist_Fanart, "")
				'''---------------------------'''
				if desc != "": extra1 = localize(21821) + space2 + str(desc)
				else: extra1 = ""
				dialogok(localize(50) + space + addonString_servicefeatherence(43).encode('utf-8') + '[CR]' + str(name), "ID" + space2 + str(url), "", extra1)
				'''---------------------------'''
				
	if "7" in printpoint and not "8" in printpoint and not "9" in printpoint:
		update_view(url, num, viewtype)
		#xbmcplugin.endOfDirectory(int(sys.argv[1]))
		
	text = "name" + space2 + str(name) + newline + \
	"Custom_Playlist_ID" + space2 + str(Custom_Playlist_ID) + newline + \
	"Custom_Playlist_Name" + space2 + str(Custom_Playlist_Name) + newline + \
	"Custom_Playlist_Thumb" + space2 + str(Custom_Playlist_Thumb) + newline + \
	"thumb" + space2 + str(thumb) + newline + \
	"Custom_Playlist_Description" + space2 + str(Custom_Playlist_Description) + newline + \
	"Custom_Playlist_Fanart" + space2 + str(Custom_Playlist_Fanart) + newline + \
	"fanart" + space2 + str(fanart) + newline + \
	"New_ID" + space2 + str(New_ID) + newline + \
	"url" + space2 + str(url) + newline
	'''---------------------------'''
	printlog(title="ManageCustom", printpoint=printpoint, text=text, level=2, option="")

def getLists(mode, name, url, iconimage, desc, num, viewtype, fanart):
	
	count = 0
	setProperty('script.featherence.service_random', "true", type="home")
	#returned = ActivateWindow('0', addonID, containerfolderpath, 0, wait=True)
	xbmc.executebuiltin('Container.Refresh') ; xbmc.sleep(2000)
	dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
	while count < 20 and dialogbusyW and not xbmc.abortRequested:
		if count == 0: notification('Random-Play','.','',2000)
		elif count == 4: notification('Random-Play','..','',2000)
		elif count == 8: notification('Random-Play','...','',2000)
		xbmc.sleep(500)
		dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
		count += 1
	
	setProperty('script.featherence.service_random', "", type="home")
	xbmc.executebuiltin('RunScript(script.featherence.service,,?mode=17&value='+addonID+')')
	#print 'getLists: ' + 'scriptfeatherenceservice_randomL' + space2 + str(scriptfeatherenceservice_randomL)

def CATEGORIES_RANDOM():
	'''אקראי'''
	addDir('-' + localize(590),list,1,featherenceserviceicons_path + 'random.png',addonString_servicefeatherence(8).encode('utf-8'),'1',"", "") #אקראי

def CATEGORIES_SEARCH(mode=3, name='-' + localize(137), url="", num=""):
	'''חיפוש'''
	printpoint = "" ; infile_ = ""
	if Search_History == 'true' and os.path.exists(Search_History_file) and mode == 30:
		infile_ = read_from_file(Search_History_file, silent=True, lines=True, retry=True, createlist=True, printpoint="", addlines="")
		if infile_ != "" and infile_ != []: pass
		else: mode = 3
	else: mode = 3
	addDir(name,url,mode,featherenceserviceicons_path + 'se.png',localize(137) + space + 'YouTube',num,"", getAddonFanart("", custom="", urlcheck_=True))
	
	text = 'mode' + space2 + str(mode) + newline + \
	'infile_' + space2 + str(infile_)
	printlog(title="CATEGORIES_SEARCH", printpoint=printpoint, text=text, level=0, option="")
	
def CATEGORIES_SEARCH2(mode, name, url, iconimage, desc, num, viewtype, fanart):
	'''רשימת חיפוש'''
	CATEGORIES_SEARCH()
	infile_ = read_from_file(Search_History_file, silent=True, lines=True, retry=True, createlist=True, printpoint="", addlines="")
	for x in infile_:
		CATEGORIES_SEARCH(url=str(x), name=str(x), num='Custom')

def Search_Menu(mode, name, url, iconimage, desc, num, viewtype, fanart):
	if num == 'Delete':
		replace_word(Search_History_file, url, "", infile_="", LineR=False , LineClean=False)
	elif num == 'Delete All':
		removefiles(Search_History_file)
	xbmc.sleep(500) ; xbmc.executebuiltin('Container.Refresh')

def MyFavourites(mode, name, url, iconimage, desc, num, viewtype, fanart):
	pass