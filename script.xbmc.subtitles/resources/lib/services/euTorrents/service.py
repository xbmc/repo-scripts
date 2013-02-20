# -*- coding: utf-8 -*-

# Service euTorrents.ph version 0.0.3
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service euTorrents.ph v0.0.3:
# Service working again, changed .me to .ph
# Fixed download bug when XBMC is set to Portuguese language and probably any other lang!
# Code re-arrange... no more annoying messages!
#
# NEW on Service euTorrents.ph v0.0.2:
# Added all site languages.
# Messages now in xbmc choosen language.
# Code re-arrange...
#
# Initial release of Service euTorrents.ph v0.0.1:
# First version of the service. Requests are welcome.
# Works with every language available on the site.
#
# euTorrents.ph subtitles, based on a mod of Undertext subtitles

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import languageTranslate, log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://eutorrents.ph/"
debug_pretext = "euTorrents"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
isLang = xbmc.getLanguage()
#DEBUG ONLY
#log( __name__ ,"%s isLang: '%s'" % (debug_pretext, isLang))

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
			<tr>
				<td class="lista"><a href="index.php?page=torrent-details&id=0b6431c18917842465b658c2d429cb9f50f9becc" title="My Life in the Air (2008) Ma vie en l'air">My Life in the Air (2008) Ma vie en l'air</a></td>
				<td class="lista"><a href="index.php?page=userdetails&id=94803"><span style='color: #333333'>Sammahel</span></a></td>
				<td class="lista"><img src="images/flag/gb.png" alt="English" /> <a href="download-subtitle.php?subid=3321">English</a></td>
				<td class="lista"><a href="download-subtitle.php?subid=3321"><img src="images/download.gif" border="0" /></a></td>
				<td class="lista"></td>
				<td class="lista">94.93 KB</td>
				<td class="lista">39</td>
				<td class="lista">&nbsp;</td>
			</tr>
"""

subtitle_pattern = "<tr>[\n\r\t][\n\r\t].+?index.php\?page=torrent-details.+?\">(.+?)</a></td>[\n\r\t][\n\r\t].+?page=userdetails.+?\'>(.+?)</span></a></td>[\n\r\t][\n\r\t].+?alt=\"(.+?)\" />.+?\?subid=(.+?)\">.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?</td>[\n\r\t][\n\r\t].+?<td.+?\">(.+?)</td>"

# group(1) = Name, group(2) = Uploader, group(3) = Language, group(4) = ID, group(5) = Downloads
#====================================================================================================================
# Functions
#====================================================================================================================
def _from_utf8(text):
    if isinstance(text, str):
        return text.decode('utf-8')
    else:
        return text

def msgnote(site, text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	text = _from_utf8(text)
	site = _from_utf8(site)
	#log( __name__ ,"%s ipath: %s" % (debug_pretext, icon))
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):
	

	page = 1
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "euTuser" )
	password = __addon__.getSetting( "euTpass" )
	login_data = urllib.urlencode({'uid' : username, 'pwd' : password})
	#This is where you are logged in
	resp = opener.open('http://eutorrents.ph/index.php?page=login', login_data)
	#log( __name__ ,"%s Getting '%s'  ..." % (debug_pretext, resp))

	url = main_url + "subtitles.php?action=search&language=" + languageshort + "&pages=" + str(page) + "&search=" + urllib.quote_plus(searchstring)
	content = opener.open(url)
	content = content.read()
	content = content.decode('latin1')
	#log( __name__ ,"%s CONTENT: '%s'" % (debug_pretext, content))
	

	#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))

	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL) and page < 6:
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
			hits = matches.group(5)
			id = matches.group(4)
			uploader = string.strip(matches.group(2))
			downloads = int(matches.group(5)) / 10
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(1))
			desc = string.strip(matches.group(1))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			uploader = re.sub('\n',' ',uploader)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			uploader = re.sub(r'<[^<]+?>','', uploader)
			desc = re.sub(r'<[^<]+?>|[~]','', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.abspath(file_original_path)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
			filesearch = os.path.split(filesearch)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
			dirsearch = filesearch[0].split(os.sep)
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
			dirsearch_check = string.split(dirsearch[-1], '.')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
				else:
					sync = False
					if len(dirsearch) > 1 and dirsearch[1] != '':
						if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
							sync = True
					else:
						if re.search(filesearch[1][:len(filesearch[1])-4], desc):
							sync = True
			filename = filename + " " + "(sent by: " + uploader + ")" + "  " + hits + "hits"
			subtitles_list.append({'rating': str(downloads), 'filename': filename, 'uploader': uploader, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageTranslate(languageshort,3,2) + '.gif', 'language_name': languagelong})

		page = page + 1
		url = main_url + "subtitles.php?action=search&language=" + languageshort + "&pages=" + str(page) + "&search=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		content = content.decode('latin1')
	
		
### ANNOYING ###
#	if subtitles_list == []:
#		msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
#		msgnote(debug_pretext,"Try manual or parent dir!", 2000)
#	elif subtitles_list != []:
#		lst = str(subtitles_list)
#		if languagelong in lst:
#			msgnote(debug_pretext,"Found sub(s) in "  + languagelong + ".", 2000)
#		else:
#			msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
#			msgnote(debug_pretext,"Try manual or parent dir!", 2000)
		
#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp




def geturl(url):
	class MyOpener(urllib.FancyURLopener):
		version = ''
	my_urlopener = MyOpener()
	log( __name__ ,"%s Getting url: %s" % (debug_pretext, url))
	try:
		response = my_urlopener.open(url)
		content    = response.read()
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		content    = None
	return content

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	subtitles_list = []
	msg = ""
	searchstring_notclean = ""
	searchstring = ""
	global israr
	israr = os.path.abspath(file_original_path)
	israr = os.path.split(israr)
	israr = israr[0].split(os.sep)
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				dirsearch = os.path.abspath(file_original_path)
				dirsearch = os.path.split(dirsearch)
				dirsearch = dirsearch[0].split(os.sep)
				if len(dirsearch) > 1:
					searchstring_notclean = dirsearch[-3]
					searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
					searchstring = searchstring[0]
				else:
					searchstring = title
			else:
				searchstring = title
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.abspath(file_original_path)
			dirsearch = os.path.split(dirsearch)
			dirsearch = dirsearch[0].split(os.sep)
			if len(dirsearch) > 1:
				searchstring_notclean = dirsearch[-2]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
				searchstring = searchstring[0]
			else:
				#We are at the root of the drive!!! so there's no dir to lookup only file#
				title = os.path.split(file_original_path)
				searchstring = title[-1]
		else:
			if title == "":
				title = os.path.split(file_original_path)
				searchstring = title[-1]
			else:
				searchstring = title
			
	if len(tvshow) > 0:
		searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
	log( __name__ ,"%s Search string = %s" % (debug_pretext, searchstring))

	
	msgnote(debug_pretext,__language__(30153), 6000)
	getallsubs(searchstring, languageTranslate(lang1,0,3), lang1, file_original_path, subtitles_list, searchstring_notclean)
	getallsubs(searchstring, languageTranslate(lang2,0,3), lang2, file_original_path, subtitles_list, searchstring_notclean)
	getallsubs(searchstring, languageTranslate(lang3,0,3), lang3, file_original_path, subtitles_list, searchstring_notclean)

	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext,__language__(30154), 6000)
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "euTuser" )
	password = __addon__.getSetting( "euTpass" )
	login_data = urllib.urlencode({'uid' : username, 'pwd' : password})
	#This is where you are logged in
	resp = opener.open('http://eutorrents.ph/index.php?page=login', login_data)
	language = subtitles_list[pos][ "language_name" ]
	#Now you download the subtitles
	content = opener.open('http://eutorrents.ph/download-subtitle.php?subid=' + id)

	downloaded_content = content.read()

	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	
	fname = os.path.join(tmp_sub_dir,str(id))
	if content.info().get('Content-Disposition').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(downloaded_content)
	f.close()
	
	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
	msgnote(debug_pretext,__language__(30155), 3000)
	xbmc.executebuiltin("XBMC.Extract(" + fname + "," + extract_path +")")
	time.sleep(2)
	legendas_tmp = []
	# brunoga fixed solution for non unicode caracters
	fs_encoding = sys.getfilesystemencoding()
	for root, dirs, files in os.walk(extract_path.encode(fs_encoding), topdown=False):
		for file in files:
			dirfile = os.path.join(root, file)
			ext = os.path.splitext(dirfile)[1][1:].lower()
			if ext in sub_ext:
				legendas_tmp.append(dirfile)
			elif os.path.isfile(dirfile):
				os.remove(dirfile)
	
	msgnote(debug_pretext,__language__(30156), 3000)
	searchrars = recursive_glob(extract_path, packext)
	searchrarcount = len(searchrars)
	if searchrarcount > 1:
		for filerar in searchrars:
			if filerar != os.path.join(extract_path,local_tmp_file) and filerar != os.path.join(extract_path,local_tmp_file):
				try:
					xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + extract_path +")")
				except:
					return False
	time.sleep(1)
	searchsubs = recursive_glob(extract_path, subext)
	searchsubscount = len(searchsubs)
	for filesub in searchsubs:
		nopath = string.split(filesub, extract_path)[-1]
		justfile = nopath.split(os.sep)[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
		#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
		releasefilename = filesearch[1][:len(filesearch[1])-4]
		releasedirname = filesearch[0].split(os.sep)
		if 'rar' in israr:
			releasedirname = releasedirname[-2]
		else:
			releasedirname = releasedirname[-1]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
		#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
		subsfilename = justfile[:len(justfile)-4]
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
		#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
		#Check for multi CD Releases
		multicds_pattern = "\+?(cd\d)\+?"
		multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#Start choosing the right subtitle(s)
		if searchsubscount == 1 and sync == True:
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
			break
		elif string.lower(subsfilename) == string.lower(releasefilename):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
			break
		elif string.lower(subsfilename) == string.lower(releasedirname):
			subs_file = filesub
			subtitle = subs_file
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
			break
		elif (multicdsubs != None) and (multicdsrls != None):
			multicdsubs = string.lower(multicdsubs.group(1))
			multicdsrls = string.lower(multicdsrls.group(1))
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
			#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
			if multicdsrls == multicdsubs:
				subs_file = filesub
				subtitle = subs_file
				break

	else:
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
		if len(legendas_tmp) > 1:
			dialog = xbmcgui.Dialog()
			subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
			if subtitle == extract_path+"/": subtitle = ""
		elif legendas_tmp:
			subtitle = legendas_tmp[0]
	
	msgnote(debug_pretext,__language__(30157), 3000)
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output


#	if content is not None:
#		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
#		if header == 'rar':
#			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".rar")
#			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
#			packed = True
#		elif header == 'zip':
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".zip")
#			packed = True
#		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
#			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".srt") # assume unpacked sub file is an '.srt'
#			subs_file = local_tmp_file
#			packed = False
#		log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
#		try:
#			log( __name__ ,"%s file: write in %s" % (debug_pretext, local_tmp_file)) #EGO
#			local_file_handle = open(local_tmp_file, "wb")
#			shutil.copyfileobj(content.fp, local_file_handle)
#			local_file_handle.close()
#		except:
#			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
#		if packed:
#			files = os.listdir(tmp_sub_dir)
#			init_filecount = len(files)
#			log( __name__ ,"%s file: number init_filecount %s" % (debug_pretext, init_filecount)) #EGO
#			filecount = init_filecount
#			max_mtime = 0
#			# determine the newest file from tmp_sub_dir
#			for file in files:
#				if (string.split(file,'.')[-1] in ['srt','sub','txt']):
#					mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
#					if mtime > max_mtime:
#						max_mtime =  mtime
#			init_max_mtime = max_mtime
#			time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
#			msgnote(debug_pretext,__language__(30155), 6000)
#			xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
#			waittime  = 0
#			while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
#				time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
#				files = os.listdir(tmp_sub_dir)
#				log( __name__ ,"%s DIRLIST '%s'" % (debug_pretext, files))
#				filecount = len(files)
#				# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
#				for file in files:
#					if (string.split(file,'.')[-1] in ['srt','sub','txt']):
#						mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
#						if (mtime > max_mtime):
#							max_mtime =  mtime
#				waittime  = waittime + 1
#			if waittime == 20:
#				log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
#			else:
#				msgnote(debug_pretext,__language__(30156), 3000)
#				log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
#				searchrars = recursive_glob(tmp_sub_dir, packext)
#				searchrarcount = len(searchrars)
#				if searchrarcount > 1:
#					for filerar in searchrars:
#						if filerar != os.path.join(tmp_sub_dir,'ldivx.rar') and filerar != os.path.join(tmp_sub_dir,'ldivx.zip'):
#							xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + tmp_sub_dir +")")
#				time.sleep(1)
#				searchsubs = recursive_glob(tmp_sub_dir, subext)
#				searchsubscount = len(searchsubs)
#				for filesub in searchsubs:
#					nopath = string.split(filesub, tmp_sub_dir)[-1]
#					justfile = nopath.split(os.sep)[-1]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
#					#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
#					releasefilename = filesearch[1][:len(filesearch[1])-4]
#					releasedirname = filesearch[0].split(os.sep)
#					if 'rar' in israr:
#						releasedirname = releasedirname[-2]
#					else:
#						releasedirname = releasedirname[-1]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
#					#log( __name__ ,"%s DEBUG-releasedirname: '%s'" % (debug_pretext, releasedirname))
#					subsfilename = justfile[:len(justfile)-4]
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
#					#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
#					#Check for multi CD Releases
#					multicds_pattern = "\+?(cd\d)\+?"
#					multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#					multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#					#Start choosing the right subtitle(s)
#					if searchsubscount == 1 and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
#						break
#					elif string.lower(subsfilename) == string.lower(releasefilename) and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
#						break
#					elif string.lower(subsfilename) == string.lower(releasedirname) and sync == True:
#						subs_file = filesub
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
#						break
#					elif (multicdsubs != None) and (multicdsrls != None) and sync == True:
#						multicdsubs = string.lower(multicdsubs.group(1))
#						multicdsrls = string.lower(multicdsrls.group(1))
#						#For DEBUG only uncomment next line
#						#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
#						#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
#						if multicdsrls == multicdsubs:
#							subs_file = filesub
#							break
#				else:
#					#If none is found just open a dialog box for browsing the temporary subtitle folder
#					sub_ext = "srt,aas,ssa,sub,smi"
#					sub_tmp = []
#					for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
#						for file in files:
#							dirfile = os.path.join(root, file)
#							ext = os.path.splitext(dirfile)[1][1:].lower()
#							if ext in sub_ext:
#								sub_tmp.append(dirfile)
#							elif os.path.isfile(dirfile):
#								os.remove(dirfile)
#					
#					# If there are more than one subtitle in the temp dir, launch a browse dialog
#					# so user can choose. If only one subtitle is found, parse it to the addon.
#					if len(sub_tmp) > 1:
#						dialog = xbmcgui.Dialog()
#						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, tmp_sub_dir+"/")
#						if subs_file == tmp_sub_dir+"/": subs_file = ""
#					elif sub_tmp:
#						subs_file = sub_tmp[0]
#		
#		msgnote(debug_pretext,__language__(30157), 3000)
#
#		return False, language, subs_file #standard output