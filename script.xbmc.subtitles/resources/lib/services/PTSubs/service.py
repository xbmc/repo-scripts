# -*- coding: utf-8 -*-

# Service PT-SUBS.NET version 0.1.5
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service PT-SUBS.NET v0.1.6:
# Added uuid for better file handling, no more hangups.
#
# Initial Release of Service PT-SUBS.NET - v0.1.5:
# TODO: re-arrange code :)
#
# PT-SUBS.NET subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

main_url = "http://www.pt-subs.net/site/"
debug_pretext = "PT-SUBS"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
desc_pattern = "<td><b>Descri.+?</b><br\s/>(.+?)<br\s/><a\shref="
subtitle_pattern = "<tr><td><a\shref=\"(.+?)\">(.+?)</a></td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td><td>(.+?)</td></tr>"
# group(1) = Download link, group(2) = Name, group(3) = Visualizações, group(4) = N Legendas, group(5) = Tamanho, group(6) = Data
#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "PTSuser" )
	password = __addon__.getSetting( "PTSpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	opener.open(main_url+'index.php', login_data)

	page = 0
	if languageshort == "pt":
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	content = content.read()
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s Getting '%s' list ..." % (debug_pretext, content))
	#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(4)
			id = matches.group(1)
			no_files = matches.group(3)
			downloads = int(matches.group(4)) / 10
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(2))
			content_desc = opener.open(id)
			content_desc = content_desc.read()
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s Getting '%s' desc" % (debug_pretext, content_desc))
			for descmatch in re.finditer(desc_pattern, content_desc, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
				desc = string.strip(descmatch.group(1))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			desc = re.sub('&quot;','"',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
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
			filename = filename + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 10
		url = main_url + "index.php?action=downloads;sa=search2;start=" + str(page) + ";searchfor=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		#For DEBUG only uncomment next line
		#log( __name__ ,"%s Getting '%s' list part xxx..." % (debug_pretext, content))

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

	portuguese = 0
	if string.lower(lang1) == "portuguese": portuguese = 1
	elif string.lower(lang2) == "portuguese": portuguese = 2
	elif string.lower(lang3) == "portuguese": portuguese = 3

	getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if portuguese == 0:
		msg = "Won't work, LegendasDivx is only for Portuguese subtitles!"
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	id = subtitles_list[pos][ "id" ]
	id = string.split(id,"=")
	id = id[-1]
	sync = subtitles_list[pos][ "sync" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "PTSuser" )
	password = __addon__.getSetting( "PTSpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'user' : username, 'passwrd' : password, 'action' : 'login2'})
	#This is where you are logged in
	resp = opener.open('http://www.pt-subs.net/site/index.php', login_data)
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s resposta '%s' subs ..." % (debug_pretext, resp))
	#Now you download the subtitles
	language = subtitles_list[pos][ "language_name" ]
	if string.lower(language) == "portuguese":
		content = opener.open('http://www.pt-subs.net/site/index.php?action=downloads;sa=downfile;id=' + id)

	if content is not None:
		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
		if header == 'rar':
			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".rar")
			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
			packed = True
		elif header == 'zip':
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".zip")
			packed = True
		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
			local_tmp_file = os.path.join(tmp_sub_dir, str(uuid.uuid1()) + ".srt") # assume unpacked sub file is an '.srt'
			subs_file = local_tmp_file
			packed = False
		log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
		try:
			log( __name__ ,"%s file: write in %s" % (debug_pretext, local_tmp_file)) #EGO
			local_file_handle = open(local_tmp_file, "wb")
			shutil.copyfileobj(content.fp, local_file_handle)
			local_file_handle.close()
		except:
			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
		if packed:
			files = os.listdir(tmp_sub_dir)
			init_filecount = len(files)
			log( __name__ ,"%s file: number init_filecount %s" % (debug_pretext, init_filecount)) #EGO
			filecount = init_filecount
			max_mtime = 0
			# determine the newest file from tmp_sub_dir
			for file in files:
				if (string.split(file,'.')[-1] in ['srt','sub','txt']):
					mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
					if mtime > max_mtime:
						max_mtime =  mtime
			init_max_mtime = max_mtime
			time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
			xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
			waittime  = 0
			while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
				time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
				files = os.listdir(tmp_sub_dir)
				log( __name__ ,"%s DIRLIST '%s'" % (debug_pretext, files))
				filecount = len(files)
				# determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
				for file in files:
					if (string.split(file,'.')[-1] in ['srt','sub','txt']):
						mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
						if (mtime > max_mtime):
							max_mtime =  mtime
				waittime  = waittime + 1
			if waittime == 20:
				log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
			else:
				log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
				searchrars = recursive_glob(tmp_sub_dir, packext)
				searchrarcount = len(searchrars)
				if searchrarcount > 1:
					for filerar in searchrars:
						if filerar != os.path.join(tmp_sub_dir,'ldivx.rar') and filerar != os.path.join(tmp_sub_dir,'ldivx.zip'):
							xbmc.executebuiltin("XBMC.Extract(" + filerar + "," + tmp_sub_dir +")")
				time.sleep(1)
				searchsubs = recursive_glob(tmp_sub_dir, subext)
				searchsubscount = len(searchsubs)
				for filesub in searchsubs:
					nopath = string.split(filesub, tmp_sub_dir)[-1]
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
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
						break
					elif string.lower(subsfilename) == string.lower(releasefilename) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1: '%s'" % (debug_pretext, subs_file))
						break
					elif string.lower(subsfilename) == string.lower(releasedirname) and sync == True:
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile-morethen1-dirname: '%s'" % (debug_pretext, subs_file))
						break
					elif (multicdsubs != None) and (multicdsrls != None) and sync == True:
						multicdsubs = string.lower(multicdsubs.group(1))
						multicdsrls = string.lower(multicdsrls.group(1))
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
						#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
						if multicdsrls == multicdsubs:
							subs_file = filesub
							break
				else:
					#If none is found just open a dialog box for browsing the temporary subtitle folder
					sub_ext = "srt,aas,ssa,sub,smi"
					sub_tmp = []
					for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
						for file in files:
							dirfile = os.path.join(root, file)
							ext = os.path.splitext(dirfile)[1][1:].lower()
							if ext in sub_ext:
								sub_tmp.append(dirfile)
							elif os.path.isfile(dirfile):
								os.remove(dirfile)
					
					# If there are more than one subtitle in the temp dir, launch a browse dialog
					# so user can choose. If only one subtitle is found, parse it to the addon.
					if len(sub_tmp) > 1:
						dialog = xbmcgui.Dialog()
						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, tmp_sub_dir+"/")
						if subs_file == tmp_sub_dir+"/": subs_file = ""
					elif sub_tmp:
						subs_file = sub_tmp[0]
							
		return False, language, subs_file #standard output