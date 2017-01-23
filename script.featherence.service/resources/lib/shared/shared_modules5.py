# -*- coding: utf-8 -*-
import urllib,urllib2,sys,re,xbmcplugin,xbmcgui,xbmcaddon,xbmc,os,random
import json
from random import shuffle

from variables import *

from shared_modules import *
from shared_modules3 import *

'''
shared_modules5 is used for Kodi's plugins.
Import the module and input the addDir in your addon module.py file.
'''
	
def CheckMoveCustom(name, num):
	'''Prepare reposition of customized buttons'''
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
	
def menu_list(custom, menu, addonID, name, url, mode, iconimage, desc, num, viewtype, fanart):
	if mode == 20:
		menu.append((localize(33063), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=22&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Options....
	modeL = [4,5,6,7,8,9,10,11,12,13,15,17]
	if mode in modeL:
		'''Play All'''
		menu.append((localize(22083), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=1&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart)))
		'''Add to favourites [Featherence]'''
		menu.append((localize(14076) + space + '[Featherence]', "XBMC.RunPlugin(plugin://%s/?url=%s&mode=24&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart)))
	if mode == 5 or mode == 6 or mode == 17:
		'''TV Mode'''
		menu.append(('TV Mode', "XBMC.RunPlugin(plugin://%s/?url=%s&mode=5&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart)))
	if mode >= 100 and mode <= 139 or mode >= 10001:
		menu.append(('Set Custom Fanart', 'RunScript(script.featherence.service,,?mode=34&value='+str(addonID)+'&value2='+str(mode)+')'))
		if getsetting('Fanart_Custom'+str(mode)) != "": menu.append(('Remove Custom Fanart', 'RunScript(script.featherence.service,,?mode=35&value='+str(addonID)+'&value2='+str(mode)+')'))
	if mode == 3 and num == 'Custom':
		'''search'''
		menu.append(("Remove", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=31&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), 'Delete', viewtype, urllib.quote_plus(fanart))))
		menu.append(("Remove All", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=31&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), 'Delete All', viewtype, urllib.quote_plus(fanart))))
	if mode == 18:
		up, down = CheckMoveCustom(name, num)			
		if up != "": menu.append(("Move Up", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=23&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num + "__" + up, viewtype, urllib.quote_plus(fanart)))) #Move Up
		if down != "": menu.append(("Move Down", "XBMC.RunPlugin(plugin://%s/?url=%s&mode=23&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)" % (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num + "__" + down, viewtype, fanart))) #Move Down
		#u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&desc="+urllib.quote_plus(desc)+"&num="+urllib.quote_plus(num)+"&viewtype="+str(viewtype)
		
		#menu.append((localize(16106), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=21&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, url, name, iconimage, desc, num, viewtype, fanart))) #Manage....
		
		menu.append((localize(16106), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=21&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Manage....
		menu.append((localize(33063), "XBMC.RunPlugin(plugin://%s/?url=%s&mode=22&name=%s&iconimage=%s&desc=%s&num=%s&viewtype=%s&fanart=%s)"% (addonID, urllib.quote_plus(url), urllib.quote_plus(name), iconimage, urllib.quote_plus(desc), num, viewtype, fanart))) #Options....
	return menu

def gettitle2(x):
	title2 = ""
	if '&custom' in x:
		if 1 + 1 == 3: title2 = ""
		else: title2 = '[Custom]'
		
	
	return title2
	
def getisFolder(name, url, mode, iconimage, desc, num, viewtype, fanart):
	isFolder = True
	modeL = [1,3,4,5,7,9,12,15,20,41,42,44]
	modeL2 = [13,18]
	
	if mode in modeL:
		isFolder = False
	elif mode in modeL2:
		if mode == 13 and not '&dailymotion_pl' in url: isFolder = False
		if mode == 18 and url == "None": isFolder = False
	elif mode == 8 and 'plugin://' in url:
		isFolder = False
	
	return isFolder

def checkMode11(mode, name, url, iconimage, desc, num, viewtype, fanart):
	printpoint = "" ; id_L = [] ; title_L = [] ; thumb_L = [] ; desc_L = [] ; fanart_L = []
					   
					   #<url="&googledrive=0B02H6jdF_-acQkNYUFYxNkZYZzQ"/>
									 #<title="דרגון בול זי פרק 69
												  #"/><thumb="
																  #"/><desc=""/>
	match = re.compile('<url="(.+?)"/><title="(.+?)"/><thumb="(.+?)"/><desc="(.+?)"/>').findall(url)
	blankL = ["",None]
	url2 = regex_from_to(url, '<url="', '"/>', excluding=True)
	name2 = regex_from_to(url, '<title="', '"/>', excluding=True)
	iconimage2 = regex_from_to(url, '<thumb="', '"/>', excluding=True)
	desc2 = regex_from_to(url, '<desc="', '"/>', excluding=True)
	
	if url2 in blankL or name2 in blankL:
		printpoint = printpoint + '6'
		id_L.append(url)
		title_L.append(name)
		thumb_L.append(iconimage)
		desc_L.append(desc)
		fanart_L.append(desc)
	else:
		id_L.append(url2)
		if 'Episode' in name2:
			name2 = name2.replace('Episode',localize(36906))
			name2 = name + space + name2
		title_L.append(name2)
		if iconimage2 in blankL: thumb_L.append(iconimage)
		else: thumb_L.append(iconimage2)
		if desc2 in blankL: desc_L.append(desc)
		else: desc_L.append(desc2)
		fanart_L.append(desc)
	
	text = 'url' + space2 + str(url) + newline + \
	'id_L' + space2 + str(id_L) + newline + \
	'name' + space2 + str(name) + newline + \
	'iconimage' + space2 + str(iconimage) + newline + \
	'desc' + space2 + str(desc) + newline + \
	'match' + space2 + str(match)
	printlog(title="checkMode11", printpoint=printpoint, text=text, level=0, option="")
	return id_L, title_L, thumb_L, desc_L, fanart_L
	
def GetHTML(url, agent = 'Apple-iPhone/'):
    html = geturllib.GetURL(url, 86400, agent)
    html = html.replace('\n',            '')
    html = html.replace('\r',            '')
    html = html.replace('\t',            '')
    html = html.replace('&quot;',        '"')
    html = html.replace('title="Search', '')
    return html

	
def getUserAgent():
    agents = []
    agents.append('Mozilla/5.0 (Android; Mobile; rv:%d.0) Gecko/%d.0 Firefox/%d.0')
    agents.append('Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.%d (KHTML, like Gecko) Chrome/%d.0.1847.114 Mobile Safari/537.%d')
    agents.append('Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/5%d.51.1 (KHTML, like Gecko) CriOS/%d.0.1847.%d Mobile/11B554a')
    agents.append('Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/5%d.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B5%da Safari/9537.%d')
    agents.append('Mozilla/5.0 (iPhone; CPU OS 7_0_4 like Mac OS X) AppleWebKit/5%d.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B%d4a Safari/9537.%d')
    agents.append('Mozilla/5.0 (Android; Mobile; rv:%d.0) Gecko/%d.0 Firefox/%d.0')

    agent = random.choice(agents) % (random.randint(10, 40), random.randint(10, 40), random.randint(10, 40))

    return '?|User-Agent=%s' % agent

def playURL(mode, name, url, iconimage, desc, num, viewtype, fanart):
	printpoint = ""
	url += getUserAgent()
	iconimage += getUserAgent()
	liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": desc} )
	liz.setProperty('IsPlayable', 'true')
	liz.setPath(url)
	#xbmcplugin.setContent(int(sys.argv[1]), 'movies')
	xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
	
	if mode == 44:
		xbmc.executebuiltin('PlayMedia('+url+')')
	
def listURL(mode, name, url, iconimage, desc, num, viewtype, fanart):
	from shared_modules3 import addDir
	printpoint = "" ; TypeError = "" ; extra = ""
	if mode == 41 or mode == 42:
		url += getUserAgent()
		iconimage += getUserAgent()

	addDir(name, url, mode, iconimage, desc, str(num), viewtype, fanart)
	
	if mode == 42:
		return url
		
def listURLS(id_L, title_L, thumb_L, desc_L, url2, desc2, iconimage2, name2):
	url2 += getUserAgent()
	iconimage2 += getUserAgent()
	
	id_L.append(url2)
	title_L.append(name2)
	thumb_L.append(iconimage2)
	desc_L.append(desc2)
	return id_L, title_L, thumb_L, desc_L
	
def listURLS_(mode, name, url, iconimage, desc, page, viewtype, fanart):
	printpoint = "" ; TypeError = "" ; extra = ""
	url_ = url ; total = 0 ; pageL = [] ; html = "" ; match = "" ; match_page = ""
	id_L = [] ; title_L = [] ; thumb_L = [] ; desc_L = []
	
	try: test = page + 1
	except: page = 1
	if '' in url: id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL = listURLS_1(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart)
	elif '' in url: id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL = listURLS_3(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart)
	elif '' in url:
		url = url.replace('&googledrive2=',"")
		if '' in url:
			id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL = listURLS_2(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart)
	else: printpoint = '9'
	
	if match != "": match = 'ok'
	#if match_page != "": match_page = 'ok'
	text = 'url_' + space2 + str(url_) + newline + \
	'url' + space2 + str(url) + newline + \
	'total' + space2 + str(total) + newline + \
	'name' + space2 + str(name) + newline + \
	'html' + space2 + str(html) + newline + \
	'pageL' + space2 + str(pageL) + newline + \
	'match' + space2 + str(match) + newline + \
	'match_page' + space2 + str(match_page) + extra
	printlog(title="listURLS_", printpoint=printpoint, text=text, level=0, option="")
	
	return id_L, title_L, thumb_L, desc_L
	
def listURLS_1(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart):
	extra = "" ; TypeError = "" ; pageL = []
	pageP = int(page) - 1
	pageN = int(page) + 1
	html_ = GetHTML(url + str(page))
	
	match_page = regex_from_to(html_, '<div class="pages">', '</div>', excluding=False)
	match_page2 = re.compile('<a href="(.+?)">(.+?)</a>').findall(match_page)
	for page_url, page_num in match_page2:
		try: pageL.append(int(page_num))
		except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError) + space + 'page_num' + space2 + str(page_num)
	
	if mode == 42:
		page = random.choice(pageL)
		
	html = '<div class="cartoon">' + html_.split('<div class="cartoon">', 1)[-1]
	
	match = re.compile('<div class="cartoon"><a class="img" href="(.+?)" title="(.+?)"><img src="(.+?)" alt=.+?<span class="title"><a href=".+?" title=".+?">(.+?)</a></span></div>').findall(html)

	if pageP in pageL:
		from shared_modules3 import addDir
		listURL(40, 'Previous Page', url, iconimage, desc, str(pageP), viewtype, fanart)
		addDir('Home','plugin://' + addonID,8,featherenceserviceicons_path + 'home.png',desc,'1',50,fanart)
	i = 0
	for url2, desc2, iconimage2, name2 in match:
		url2 = url2.replace('/cartoon/', '/video/')
		url2 = url2.replace('.html', '.mp4')
		if mode == 42:
			id_L, title_L, thumb_L, desc_L = listURLS(id_L, title_L, thumb_L, desc_L, url2, desc2, iconimage2, name2)
		else:
			listURL(41, name2, url2, iconimage2, desc2, str(page), viewtype, fanart)
		i += 1
	if pageN in pageL:
		listURL(40, 'Next Page', url, iconimage, desc, str(pageN), viewtype, fanart)
	
	total = i
	return id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL
	
def listURLS_2(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart):
	extra = "" ; TypeError = "" ; pageL = [] ; match_page = "" ; match_page2 = ""
	pageP = int(page) - 1
	pageN = int(page) + 1
	html_ = GetHTML(url)

	if 1 + 1 == 3:
		match_page = regex_from_to(html_, '<article class', '</article>', excluding=False)
		match_page2 = re.compile('<a href="(.+?)">(.+?)</a>').findall(match_page)
		for page_url, page_num in match_page2:
			try: pageL.append(int(page_num))
			except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError) + space + 'page_num' + space2 + str(page_num)
	
	if mode == 42:
		page = random.choice(pageL)
		
	html = '<article class' + html_.split('<article class', 1)[-1]
	
	match = re.compile('<a href="(.+?)" title="(.+?)"><img src="(.+?)" alt=.+?<span class="title"><a href=".+?" title=".+?">(.+?)</a></span></div>').findall(html)

	if pageP in pageL:
		from shared_modules3 import addDir
		listURL(40, 'Previous Page', url, iconimage, desc, str(pageP), viewtype, fanart)
		addDir('Home','plugin://' + addonID,8,featherenceserviceicons_path + 'home.png',desc,'1',50,fanart)
	i = 0
	for url2, desc2, iconimage2, name2 in match:
		url2 = url2.replace('/cartoon/', '/video/')
		url2 = url2.replace('.html', '.mp4')
		if mode == 42:
			id_L, title_L, thumb_L, desc_L = listURLS(id_L, title_L, thumb_L, desc_L, url2, desc2, iconimage2, name2)
		else:
			listURL(41, name2, url2, iconimage2, desc2, str(page), viewtype, fanart)
		i += 1
	if pageN in pageL:
		listURL(40, 'Next Page', url, iconimage, desc, str(pageN), viewtype, fanart)
	
	total = i
	return id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL

def listURLS_3(id_L, title_L, thumb_L, desc_L, mode, name, url, iconimage, desc, page, viewtype, fanart):
	extra = "" ; TypeError = "" ; pageL = []
	pageP = int(page) - 1
	pageN = int(page) + 1
	html_ = GetHTML(url + str(page))
	
	match_page = regex_from_to(html_, '<div class="pages">', '</div>', excluding=False)
	match_page2 = re.compile('<a href="(.+?)">(.+?)</a>').findall(match_page)
	for page_url, page_num in match_page2:
		try: pageL.append(int(page_num))
		except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError) + space + 'page_num' + space2 + str(page_num)
	
	if mode == 42:
		page = random.choice(pageL)
		
	html = '<div class="cartoon">' + html_.split('<div class="cartoon">', 1)[-1]
	
	match = re.compile('<div class="cartoon"><a class="img" href="(.+?)" title="(.+?)"><img src="(.+?)" alt=.+?<span class="title"><a href=".+?" title=".+?">(.+?)</a></span></div>').findall(html)

	if pageP in pageL:
		from shared_modules3 import addDir
		listURL(40, 'Previous Page', url, iconimage, desc, str(pageP), viewtype, fanart)
		addDir('Home','plugin://' + addonID,8,featherenceserviceicons_path + 'home.png',desc,'1',50,fanart)
	i = 0
	for url2, desc2, iconimage2, name2 in match:
		url2 = url2.replace('/cartoon/', '/video/')
		url2 = url2.replace('.html', '.mp4')
		if mode == 42:
			id_L, title_L, thumb_L, desc_L = listURLS(id_L, title_L, thumb_L, desc_L, url2, desc2, iconimage2, name2)
		else:
			listURL(41, name2, url2, iconimage2, desc2, str(page), viewtype, fanart)
		i += 1
	if pageN in pageL:
		listURL(40, 'Next Page', url, iconimage, desc, str(pageN), viewtype, fanart)
	
	total = i
	return id_L, title_L, thumb_L, desc_L, extra, url, html, match, match_page, total, pageL
	
