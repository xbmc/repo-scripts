# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser
import cookielib
if sys.version_info < (2, 7):
	import simplejson
else:
	import json as simplejson

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString
main_url = 'https://www.italiansubs.net/'

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__serieoriginalpath__ = os.path.join(__cwd__, 'resources', 'Serie.json')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__serieprofilepath__ = os.path.join(__profile__, 'Serie.json')
__lastdownload__ = os.path.join(__profile__, 'last.json')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode('utf-8')
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp','')).decode('utf-8')

sys.path.append(__resource__)

def log(msg, force = False):
	if force:
		xbmc.log((u'### [' + __scriptname__ + u'] - ' + msg).encode('utf-8'), level = xbmc.LOGNOTICE)
	else:
		xbmc.log((u'### [' + __scriptname__ + u'] - ' + msg).encode('utf-8'), level = xbmc.LOGDEBUG)

def notify(msg):
	xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , msg)).encode('utf-8'))
def normalizeString(str):
	return unicodedata.normalize(
		'NFKD', unicode(unicode(str, 'utf-8'))
	).encode('ascii', 'ignore')

def getOnlineID():
	json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["tvshowid","imdbnumber"]},"id":1}' )
	json_player_getitem = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
	#if json_player_getitem['result']['item']['type'] == 'movie' and json_player_getitem['result']['item'].has_key('imdbnumber') and json_player_getitem['result']['item']['imdbnumber']!='':
		#	return json_player_getitem['result']['item']['imdbnumber']
	if json_player_getitem.has_key('result') and json_player_getitem['result'].has_key('item') and json_player_getitem['result']['item'].has_key('id') and json_player_getitem['result']['item'].has_key('type') and json_player_getitem['result']['item']['type'] == 'episode':
			json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%s, "properties": ["imdbnumber"]}}' % (json_player_getitem['result']['item']['tvshowid']) )
			json_getepisodedetails = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
			if json_getepisodedetails.has_key('result') and json_getepisodedetails['result'].has_key('tvshowdetails') and json_getepisodedetails['result']['tvshowdetails'].has_key('imdbnumber') and json_getepisodedetails['result']['tvshowdetails'].has_key('imdbnumber') and json_getepisodedetails['result']['tvshowdetails']['imdbnumber']!='':
				return str(json_getepisodedetails['result']['tvshowdetails']['imdbnumber'])
	return -1 

def get_params():
	param = {}
	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = paramstring
		cleanedparams = params.replace('?', '')
		if (params[len(params) - 1] == '/'):
			params = params[0:len(params) - 2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0]] = splitparams[1]

	return param

def geturl(url):
	log("Getting url: %s" % (url))
	try:
		headers = { 'User-Agent' : 'XBMC ItaSA Subtitle downloader' }
		req = urllib2.Request(url, None, headers)
		content = urllib2.urlopen(req).read()
	except:
		log("Failed to get url:%s" % (url))
		content = None
	return content

def saveSerie(contents):
	try:
		fh = open(__serieprofilepath__, 'w')
		fh.write(simplejson.dumps(contents))
		fh.close()
	except:
		log("Unable to save file: %s" % __serieprofilepath__)

def openSerie():
	if xbmcvfs.exists(__serieprofilepath__):
		contents = None
		try:
			fh = open(__serieprofilepath__, 'r')
			contents = simplejson.loads(unicode(fh.read(), errors='ignore'))
			fh.close()
		except:
			log("Unable to open file: %s" % __serieprofilepath__)
			return contents
		if xbmcvfs.exists(__serieoriginalpath__) and os.path.getctime(__serieprofilepath__) < os.path.getctime(__serieoriginalpath__):		
			log('Check if the new Serie.json has new tv shows')
			contents2 = None
			try:
				fh = open(__serieoriginalpath__, 'r')
				contents2 = simplejson.loads(unicode(fh.read(), errors='ignore'))
				fh.close()		
			except:
				log("Unable to open file: %s" % __serieoriginalpath__)
				return contents
			if contents and contents2:
				c = dict(contents.items() + contents2.items())
				saveSerie(c)
				return c
			else:
				return contents
		else:
			return contents
	elif xbmcvfs.exists(__serieoriginalpath__):	
		contents = None
		try:
			fh = open(__serieoriginalpath__, 'r')
			contents = simplejson.loads(unicode(fh.read(), errors='ignore'))
			fh.close()
			saveSerie(contents)
			return contents
		except:
			log("Unable to open file: %s" % __serieoriginalpath__)
			return contents
	else:			
		log('No file in both serie.json locations')
		return None

def prepare_search_string(s):
	se = re.sub(r'(( ((\(\d\d\d\d\))|((\([a-zA-Z]{2,3})\))))|(((\(\d\d\d\d\))|((\([a-zA-Z]{2,3})\)))))*$', '', s)	# remove year or country from title
	return s

def getItaSATheTVDBID(tvshowid):
	log('Obtaining TheTVDB ID of itasa tv show')
	content = geturl('https://api.italiansubs.net/api/rest/shows/' + tvshowid + '?apikey=4ffc34b31af2bca207b7256483e24aac')
	if content:
		match = re.findall(r'<id_tvdb>([\s\S]*?)</id_tvdb>', content, re.IGNORECASE | re.DOTALL)
		if match:
			return match[0]
	else:
		log('Download of user page failed')
	return None

def getItaSATVShowList():
	content = geturl('https://api.italiansubs.net/api/rest/shows?apikey=4ffc34b31af2bca207b7256483e24aac')
	if content:
		result = re.findall(r'<id>([\s\S]*?)</id>[\s\S]*?<name>([\s\S]*?)</name>', content, re.IGNORECASE | re.DOTALL)
		if result:
			return result
		else:
			log('Match of tv shows failed')
	else:
		log('Download of tv show list failed')
	return None

def getItaSATVShowID(tvshow, onlineid):
	seriesname = tvshow
	result = None
	if onlineid != -1:
		log("Search tv show by TheTVDB id %s" % onlineid)
		series = openSerie()
		if series:
			if onlineid in series:
				return series[onlineid]
			else:
				log('Download tv show list and search for new tv shows')
				missingseries = {}
				result = getItaSATVShowList()
				if result:
					for (tvshowid, tvshowname) in result:
						if not (tvshowid in series.values()):
							newid = getItaSATheTVDBID(tvshowid)
							if newid and newid != '0':
								series[newid] = tvshowid
								missingseries[newid] = tvshowid
					log("Added %s tv shows" % len(missingseries))
					saveSerie(series)
					if onlineid in missingseries:
						return missingseries[onlineid]
					log('TheTVDB ID not found in itasa. Searching by TV show name')
				else:
					return None
		HTTPResponse = urllib2.urlopen('http://www.thetvdb.com/data/series/'+onlineid+'/').read()
		if re.search('<SeriesName>(.*?)</SeriesName>', HTTPResponse):
			seriesname = re.findall('<SeriesName>(.*?)</SeriesName>', HTTPResponse)[0]
			log("Obtained original file name '%s'." % seriesname)
	if not result:
		result = getItaSATVShowList()
		if not result:
			return None
	seriesname = string.strip(seriesname)
	seriesclean = seriesname.replace('(', '').replace(')', '').lower()
	for (tvshowid, tvshowname) in result:
		if seriesclean == tvshowname.lower():
			return tvshowid
	log('Searching by full TV show name failed. Trying with year and nation removed')
	seriesclean = prepare_search_string(seriesname)
	d = []
	for (tvshowid, tvshowname) in result:
		if tvshowname.lower().startswith(seriesclean):
			d[tvshowname]=tvshowid
	if d:
		return d[min(d, key = len)]
	else:
		return None


def getAuthID():
	username = __addon__.getSetting( 'ITuser' )
	password = __addon__.getSetting( 'ITpass' )
	authid = ''
	if (username == '' or password == ''):
		notify(__language__(32004))
		log('Missing username or password. Login to Itasa failed.')
		return ''
	else:
		log("Logging in with username '%s' ..." % (username))
		oldusername = __addon__.getSetting( 'ITLoggeduser' )
		authid = __addon__.getSetting( 'authid' )
		if (authid =='' or oldusername != username):
			content = geturl('https://api.italiansubs.net/api/rest/users/login?username=' + username + '&password=' + password + '&apikey=4ffc34b31af2bca207b7256483e24aac')
			if content:
				match = re.findall(r'<authcode>([\s\S]*?)</authcode>', content, re.IGNORECASE | re.DOTALL)
				if match and match[0]!='':
					authid=match[0]
					__addon__.setSetting(id="ITLoggeduser", value=username)
					__addon__.setSetting(id="authid", value=authid)
				else:
					notify(__language__(32005))
					log('Login to Itasa api failed. Check your username/password at the addon configuration')
					return ''
			else:
				return ''
	content= geturl(main_url + 'index.php')
	if content:
		match = re.search('logouticon.png', content, re.IGNORECASE | re.DOTALL)
		if match:
			return authid
		else:
			match = re.search('<input type="hidden" name="return" value="([^\n\r\t ]+?)" /><input type="hidden" name="([^\n\r\t ]+?)" value="([^\n\r\t ]+?)" />', content, re.IGNORECASE | re.DOTALL)
			if match:
				return_value = match.group(1)
				unique_name = match.group(2)
				unique_value = match.group(3)
				login_postdata = urllib.urlencode({'username': username, 'passwd': password, 'remember': 'yes', 'Submit': 'Login', 'remember': 'yes', 'option': 'com_user', 'task': 'login', 'silent': 'true', 'return': return_value, unique_name: unique_value} )
				cj = cookielib.CookieJar()
				my_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
				my_opener.addheaders = [('Referer', main_url)]
				urllib2.install_opener(my_opener)
				request = urllib2.Request(main_url + 'index.php', login_postdata)
				response = urllib2.urlopen(request).read()
				match = re.search('logouticon.png', response, re.IGNORECASE | re.DOTALL)
				if match:
					return authid
				else:
					notify(__language__(32006))
					log('Login to Itasa failed. Check your username/password at the addon configuration')
					return ''
	else:
		notify(__language__(32007))
		log('Error loading itasa page. Login to Itasa failed')
		return ''

def append_subtitle(subid, subtitlename, filename, sync, count):
	listitem = xbmcgui.ListItem(label='Italian',
								label2=subtitlename,
								thumbnailImage='it')

	listitem.setProperty('sync', 'true' if sync else 'false')
	listitem.setProperty('hearing_imp', 'false')

	## below arguments are optional, it can be used to pass any info needed in download function
	## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
	url = "plugin://%s/?action=download&count=%s&subid=%s&filename=%s" % (__scriptid__, count, subid, filename)
	## add it to list, this can be done as many times as needed for all subtitles found
	log("Adding subtitle '%s' to gui list" % subtitlename)
	xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = url, listitem = listitem, isFolder = False)

def search(item):
	if 'ita' in item['languages']:
		filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
		log("Search_itasa='%s', filename='%s', addon_version=%s" % (item, filename, __version__))

		if item['mansearch']:
			search_manual(item['mansearchstr'], filename)
		elif item['tvshow']:
			search_tvshow(item['tvshow'], item['season'], item['episode'], item['onlineid'], filename, True)
		elif item['title'] and item['year']:
			notify(__language__(32009))
			log('Itasa only works with tv shows. Skipped')
		else:
			search_filename(filename, False)
	else:
		notify(__language__(32008))
		log('Itasa only works with italian. Skipped')
	
def search_tvshow(tvshow, season, episode, onlineid, filename, allowfallback):
	log("Search tv show '%s'" % tvshow)
	itasaid = getItaSATVShowID(tvshow, onlineid)
	if itasaid:
		log("Found itasa id %s" % itasaid)
		content = geturl('https://api.italiansubs.net/api/rest/subtitles/search?q=%sx%s&show_id=%s&apikey=4ffc34b31af2bca207b7256483e24aac' % (season, episode, itasaid))
		if content:
			result = re.findall(r'<id>([\s\S]*?)</id>[\s\S]*?<name>([\s\S]*?)</name>[\s\S]*?<version>([\s\S]*?)</version>', content, re.IGNORECASE | re.DOTALL)
			if result:
				checksyncandadd(result, filename)
			else:
				log('No subtitles found')
	else:
		if allowfallback:
			log('TV Show not found, try with filename search')
			search_filename(filename, False)
		else:
			log('TV Show not found')

def search_manual(searchstr, filename):
	searchstring = searchstr
	log("Search tvshow with manual string %s" % searchstring)
	result = re.findall(r'(.*?)((s(\d{1,3})){0,1})(e(\d{1,3}))(.*)', searchstring, re.IGNORECASE)
	if result:
		if result[0][3]=='':
			searchstring = result[0][0]+'1x'+result[0][5]+result[0][6]
		elif result[0][3].strip('0')=='':
			searchstring = result[0][0]+'0x'+result[0][5]+result[0][6]
		else:
			searchstring = result[0][0]+result[0][3].strip('0')+'x'+result[0][5]+result[0][6]
			log(result[0][3].strip('0'))
	content = geturl('https://api.italiansubs.net/api/rest/subtitles/search?q=%s&apikey=4ffc34b31af2bca207b7256483e24aac' % searchstring)
	if content:
		result = re.findall(r'<id>([\s\S]*?)</id>[\s\S]*?<name>([\s\S]*?)</name>[\s\S]*?<version>([\s\S]*?)</version>', content, re.IGNORECASE | re.DOTALL)
		if result:
			checksyncandadd(result, filename)
		else:
			log('No subtitles found')

def checksyncandadd(result, filename):
	fl = filename.lower()
	count=0
	for (subtitleid, subtitlename, subtitleversion) in result:
		if subtitleversion == 'WEB-DL':						
			if ('web-dl' in fl) or ('web.dl' in fl) or ('webdl' in fl) or ('web dl' in fl):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, True, count)
		elif subtitleversion == '720p':						
			if ('720p' in fl) and ('hdtv' in fl):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, True, count)
		elif subtitleversion == 'Normale':
			if ('hdtv' in fl) and ( not ('720p' in fl)):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, True, count)
		elif subtitleversion.lower() in fl:
			append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, True, count)
		count +=1
	for (subtitleid, subtitlename, subtitleversion) in result:
		if subtitleversion == 'WEB-DL':						
			if not (('web-dl' in fl) or ('web.dl' in fl) or ('webdl' in fl) or ('web dl' in fl)):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, False, count)
		elif subtitleversion == '720p':
			if not (('720p' in fl) and ('hdtv' in fl)):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, False, count)
		elif subtitleversion == 'Normale':
			if not (('hdtv' in fl) and ( not ('720p' in fl))):
				append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, False, count)
		elif not (subtitleversion.lower() in fl):
			append_subtitle(subtitleid, subtitlename + ' ' + subtitleversion, filename, False, count)
		count +=1

def search_filename(filename, allowfallback):
	log('Search tv show using the file name')
	title, year = xbmc.getCleanMovieTitle(filename)
	log("clean title: \"%s\" (%s)" % (title, year))
	match = re.search(r'\WS(?P<season>\d{1,3})[ ._-]*E(?P<episode>\d{1,3})', title, flags = re.IGNORECASE)
	if match is not None:
		tvshow = string.strip(title[:match.start('season')-1]).lower()
		season = string.lstrip(match.group('season'), '0')
		episode = match.group('episode')
		search_tvshow(tvshow, season, episode, -1, filename, allowfallback)
	else:
		match = re.search(r'\W(?P<season>\d{1,3})x(?P<episode>\d{1,3})', title, flags = re.IGNORECASE)
		if match is not None:
			tvshow = string.strip(title[:match.start('season')-1])
			season = string.lstrip(match.group('season'), '0')
			episode = string.lstrip(match.group('episode'), '0')
			search_tvshow(tvshow, season, episode, -1, filename, allowfallback)
		else:
			log('Unable to retrieve a tv show name and episode from file name')

def download (subid): #standard input
	authid = getAuthID()
	if authid != '':
		url = 'https://api.italiansubs.net/api/rest/subtitles/download?authcode=' + authid + '&subtitle_id=' + subid + '&apikey=4ffc34b31af2bca207b7256483e24aac'
		log("Fetching subtitles using url %s" % url)
		content= geturl(url)
		if content:
			log('File downloaded')
			try:
				if xbmcvfs.exists(__temp__):
					shutil.rmtree(__temp__)
				xbmcvfs.mkdirs(__temp__)
			except:
				log('Failed to delete the temp folder')
			local_tmp_file = os.path.join(__temp__, 'itasa.xxx')
			
			try:
				log("Saving subtitles to '%s'" % local_tmp_file)
				local_file_handle = open(local_tmp_file, 'wb')
				local_file_handle.write(content)
				local_file_handle.close()
				#Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
				myfile = open(local_tmp_file, 'rb')
				myfile.seek(0)
				if myfile.read(1) == 'R':
					typeid = 'rar'
					packed = True
					log('Discovered RAR Archive')
				else:
					myfile.seek(0)
					if myfile.read(1) == 'P':
						typeid = 'zip'
						packed = True
						log('Discovered ZIP Archive')
					else:
						myfile.seek(0)
						if myfile.read(92) != '<br/>&nbsp;<br/> Spiacente il tuo limite di download per questo file &egrave stato raggiunto':
							typeid = 'srt'
							packed = False
							log('Discovered a non-archive file')
						else:
							notify(__language__(32010))
							log('Subtitle downloaded too many times.')
							return []
				myfile.close()
				local_tmp_file = os.path.join(__temp__, 'itasa.' + typeid)
				os.rename(os.path.join(__temp__, 'itasa.xxx'), local_tmp_file)
				log("Saving to %s" % local_tmp_file)
			except:
				log("Failed to save subtitle to %s" % local_tmp_file)
				return []
			if packed:
				xbmc.sleep(500)
				xbmc.executebuiltin(('XBMC.Extract(' + local_tmp_file + ',' + __temp__ +')').encode('utf-8'), True)
				files = []
				filesfirst = []
				exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']
				tag = True
				first = '****'
				found = False
				log('Check if file contains tags in srt and if not returns it')
				if xbmcvfs.exists(__lastdownload__):
					try:
						fh = open(__lastdownload__, 'r')
						contents = simplejson.loads(unicode(fh.read(), errors='ignore'))
						fh.close()
						if  contents.has_key('subid') and  contents.has_key('subname') and contents['subid']==subid:
							log('Change the order to get a different subtitle than the old one')
							first = contents['subname']
					except:
						log('No last downloaded file, skip the check')
				for file in os.listdir(__temp__):
					if '.tag.' not in file.lower() and os.path.splitext(file)[1] in exts:
						filepath = os.path.join(__temp__, file)
						if found:
							filesfirst.append(filepath)
						else:
							if first == filepath:
								found = True
							files.append(filepath)
						if tag and '.notag.' in file.lower():
							tag = False
				if tag:
					writeLastDownload(subid,files,filesfirst)
					return filesfirst+files
				else:
					files2 = []
					filesfirst = []
					found = False
					for file in files:
						if not ('.notag.' not in file.lower() and os.path.splitext(file)[1]=='.srt'):
							filepath = os.path.join(__temp__, file)
							if found:
								filesfirst.append(filepath)
							else:
								if first == filepath:
									found = True
								files2.append(filepath)
					writeLastDownload(subid,files2,filesfirst)
					return filesfirst+files2
			else:
				return [local_tmp_file]
		else:
			log('Failed to download the file')
			return []

def writeLastDownload(subid,files,filesfirst):
	subname = ''
	if len(filesfirst)>0:
		subname = filesfirst[0] 
	elif (files)>0:
		subname =files[0] 
	if subname != '':
		content = {}
		content['subid'] = subid
		content['subname'] = subname
		try:
			fh = open(__lastdownload__, 'w')
			fh.write(simplejson.dumps(content))
			fh.close()
		except:
			log("Unable to save file: %s" % __serieprofilepath__)


log("Application version: %s" % __version__)
if xbmc.Player().isPlayingVideo():
	if not xbmcvfs.exists(__profile__):
		xbmcvfs.mkdirs(__profile__)
	params = get_params()

	if params['action'] == 'search' or params['action'] == 'manualsearch':
		log(__serieprofilepath__)
		item = {}
		item['temp'] = False
		item['rar'] = False
		item['mansearch'] = False
		item['year'] = xbmc.getInfoLabel('VideoPlayer.Year')										# Year
		item['season'] = str(xbmc.getInfoLabel('VideoPlayer.Season'))								# Season
		item['episode'] = str(xbmc.getInfoLabel('VideoPlayer.Episode')).zfill(2)					# Episode
		item['tvshow'] = normalizeString(xbmc.getInfoLabel('VideoPlayer.TVshowtitle'))				# Show
		item['title'] = normalizeString(xbmc.getInfoLabel('VideoPlayer.OriginalTitle'))				# try to get original title
		item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')             	# Full path
		item['onlineid'] = getOnlineID()															# Thetvdb id or imdb id
		item['languages'] = []

		if 'searchstring' in params:
			item['mansearch'] = True
			item['mansearchstr'] = urllib.unquote(params['searchstring'])

		for lang in urllib.unquote(params['languages']).decode('utf-8').split(','):
			item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

		if item['title'] == '':
			item['title'] = normalizeString(xbmc.getInfoLabel('VideoPlayer.Title'))	 # no original title, get just Title

		if item['episode'].lower().find('s') > -1:									 # Check if season is "Special"
			item['season'] = '0'														 #
			item['episode'] = item['episode'][-1:]

		if item['file_original_path'].find('http') > -1:
			item['temp'] = True

		elif item['file_original_path'].find('rar://') > -1:
			item['rar'] = True
			item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

		elif item['file_original_path'].find('stack://') > -1:
			stackPath = item['file_original_path'].split(' , ')
			item['file_original_path'] = stackPath[0][8:]

		search(item)

	elif params['action'] == 'download':
		## we pickup all our arguments sent from def Search()
		subs = download(params['subid'])
		## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that
		## in XBMC core
		log('Pass the subtitle paths to xbmc')
		for sub in subs:
			listitem = xbmcgui.ListItem(label = sub)
			xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = sub, listitem = listitem, isFolder = False)

	xbmcplugin.endOfDirectory(int(sys.argv[1]))	# send end of directory to XBMC
else:
	notify(__language__(32011))
