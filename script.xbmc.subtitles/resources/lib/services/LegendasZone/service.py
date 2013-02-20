# -*- coding: utf-8 -*-

# Service Legendas-Zone.org version 0.2.1
# Code based on Undertext service and the download function encode fix from legendastv service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service Legendas-Zone.org v0.2.1:
# Service working again, developers change the page way too much!
# Fixed download bug when XBMC is set to Portuguese language
# Removed IMDB search since they are always changing code!
# Some code cleanup
#
# NEW on Service Legendas-Zone.org v0.2.0:
# Fixed bug on openelec based XBMC prevent the script to work
# Removed some XBMC messages from the script who were annoying!
# Some code cleanup
#
# NEW on Service Legendas-Zone.org v0.1.9:
# Added all site languages (English, Portuguese, Portuguese Brazilian and Spanish)
# Changed the way it would handle several patterns for much better finding (site not well formed...)
# Messages now in xbmc choosen language.
# Added new logo.
# Fixed download.
# Code re-arrange...
#
# NEW on Service Legendas-Zone.org v0.1.8:
# Added uuid for better file handling, no more hangups.
#
# NEW on Service Legendas-Zone.org v0.1.7:
# Changed 2 patterns that were crashing the plugin, now it works correctly.
# Better builtin notifications for better information.
#
# NEW on Service Legendas-Zone.org v0.1.6:
# Better search results with 3 types of searching. Single title, multi titles and IMDB search.
# Added builtin notifications for better information.
#
# Initial Release of Service Legendas-Zone.org - v0.1.5:
# TODO: re-arrange code :)
#
# Legendas-Zone.org subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import languageTranslate, log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://www.legendas-zone.org/"
debug_pretext = "Legendas-Zone"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
#Grabbing login and pass from xbmc settings
username = __addon__.getSetting( "LZuser" )
password = __addon__.getSetting( "LZpass" )

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
"""
subtitle_pattern = "<b><a\shref=\"legendas.php\?modo=detalhes&amp;(.+?)\".+?[\r\n\t]+?.+?[\r\n\t]+?.+?onmouseover=\"Tip\(\'<table><tr><td><b>(.+?)</b></td></tr></table>.+?<b>Hits:</b>\s(.+?)\s<br>.+?<b>CDs:</b>\s(.+?)<br>.+?Uploader:</b>\s(.+?)</td>"
# group(1) = ID, group(2) = Name, group(3) = Hits, group(4) = Files, group(5) = Uploader
multiple_results_pattern = "<td\salign=\"left\".+?<b><a\shref=\"legendas.php\?imdb=(.+?)\"\stitle=\".+?\">"
# group(1) = IMDB
imdb_pattern = "<td class=\"result_text\"> <a\shref=\"\/title\/tt(.+?)\/\?"
# group(1) = IMDB
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
	xbmc.executebuiltin((u"Notification(%s,%s,%i,%s)" % (site, text, timeout, icon)).encode("utf-8"))

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	#Grabbing login and pass from xbmc settings
	username = __addon__.getSetting( "LZuser" )
	password = __addon__.getSetting( "LZpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	login_data = urllib.urlencode({'username' : username, 'password' : password})
	opener.open(main_url+'fazendologin.php', login_data)
	
	

	page = 0
	if languageshort == "pb":
			languageshort = "br"
	url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	#log( __name__ ,"%s Content: '%s'" % (debug_pretext, content))
	content = content.read().decode('latin1')
	#log( __name__ ,"%s Contentread: '%s'" % (debug_pretext, content.decode('latin1')))
	if re.search(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) == None:
		log( __name__ ,"%s LangSingleSUBS: '%s'" % (debug_pretext, languageshort))
		log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "Single Title"))
		while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 3:
			for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
				hits = matches.group(3)
				downloads = int(matches.group(3)) / 5
				if (downloads > 10):
					downloads=10
				id = matches.group(1)
				filename = string.strip(matches.group(2))
				desc = string.strip(matches.group(2))
				no_files = matches.group(4)
				uploader = matches.group(5)
				#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
				filename_check = string.split(filename,' ')
				#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
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
				#filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
				if languageshort == "br":
					languageshort = "pb"
				subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits': hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
			page = page + 1
			if languageshort == "br":
				languageshort = "pb"
			url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
			content = opener.open(url)
			content = content.read().decode('latin1')
			#For DEBUG only uncomment next line
			#log( __name__ ,"%s Getting '%s' list part xxx..." % (debug_pretext, content))
	else:
		page = 0
		if languageshort == "pb":
			languageshort = "br"
		url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read().decode('latin1')
		maxsubs = re.findall(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
		#maxsubs = len(maxsubs)
		if maxsubs != "":
			log( __name__ ,"%s LangMULTISUBS: '%s'" % (debug_pretext, languageshort))
			#log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "Less Then 10 Titles"))
			while re.search(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 1:
				for resmatches in re.finditer(multiple_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
					imdb = resmatches.group(1)
					page1 = 0
					if languageshort == "pb":
						languageshort = "br"
					content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
					content1 = content1.read()
					content1 = content1.decode('latin1')
					while re.search(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page1 == 0:
						for matches in re.finditer(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
							#log( __name__ ,"%s PAGE? '%s'" % (debug_pretext, page1))
							hits = matches.group(3)
							downloads = int(matches.group(3)) / 5
							if (downloads > 10):
								downloads=10
							id = matches.group(1)
							filename = string.strip(matches.group(2))
							desc = string.strip(matches.group(2))
							#desc = filename + " - uploader: " + desc
							no_files = matches.group(4)
							uploader = matches.group(5)
							#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
							filename_check = string.split(filename,' ')
							#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
							#Remove new lines on the commentaries
							filename = re.sub('\n',' ',filename)
							desc = re.sub('\n',' ',desc)
							desc = re.sub('&quot;','"',desc)
							#Remove HTML tags on the commentaries
							filename = re.sub(r'<[^<]+?>','', filename)
							desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
							#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
							#global filesearch
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
							filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
							if languageshort == "br":
								languageshort = "pb"
							subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
						page1 = page1 + 1
						content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb + "&page=" + str(page1))
						content1 = content1.read().decode('latin1')
				page = page + 1
				if languageshort == "pb":
					languageshort = "br"
				url = main_url + "legendas.php?l=" + languageshort + "&page=" + str(page) + "&s=" + urllib.quote_plus(searchstring)
				content = opener.open(url)
				content = content.read().decode('latin1')
################### IMDB DISABLED FOR NOW #######################################
#		else:
#			url = "http://uk.imdb.com/find?s=all&q=" + urllib.quote_plus(searchstring)
#			content = opener.open(url)
#			content = content.read().decode('latin1')
#			imdb = re.findall(imdb_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
#			page1 = 0
#			log( __name__ ,"%s LangIMDB: '%s'" % (debug_pretext, languageshort))
#			if languageshort == "pb":
#				languageshort = "br"
#			content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb[0] + "&page=" + str(page1))
#			content1 = content1.read().decode('latin1')
#			#msgnote(pretext, "Too many hits. Grabbing IMDB title!", 6000)
#			while re.search(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
#				log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, "IMDB Title"))
#				for matches in re.finditer(subtitle_pattern, content1, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
#					hits = matches.group(3)
#					downloads = int(matches.group(3)) / 5
#					if (downloads > 10):
#						downloads=10
#					id = matches.group(1)
#					filename = string.strip(matches.group(2))
#					desc = string.strip(matches.group(2))
#					#desc = filename + " - uploader: " + desc
#					no_files = matches.group(4)
#					uploader = matches.group(5)
#					#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename))
#					filename_check = string.split(filename,' ')
#					#log( __name__ ,"%s filename '%s'" % (debug_pretext, filename_check))
#					#Remove new lines on the commentaries
#					filename = re.sub('\n',' ',filename)
#					desc = re.sub('\n',' ',desc)
#					desc = re.sub('&quot;','"',desc)
#					#Remove HTML tags on the commentaries
#					filename = re.sub(r'<[^<]+?>','', filename)
#					desc = re.sub(r'<[^<]+?>|[~]',' ', desc)
#					#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
#					#global filesearch
#					filesearch = os.path.abspath(file_original_path)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s abspath: '%s'" % (debug_pretext, filesearch))
#					filesearch = os.path.split(filesearch)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s path.split: '%s'" % (debug_pretext, filesearch))
#					dirsearch = filesearch[0].split(os.sep)
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s dirsearch: '%s'" % (debug_pretext, dirsearch))
#					dirsearch_check = string.split(dirsearch[-1], '.')
#					#For DEBUG only uncomment next line
#					#log( __name__ ,"%s dirsearch_check: '%s'" % (debug_pretext, dirsearch_check))
#					if (searchstring_notclean != ""):
#						sync = False
#						if re.search(searchstring_notclean, desc):
#							sync = True
#					else:
#						if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
#							sync = False
#							if len(dirsearch) > 1 and dirsearch[1] != '':
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
#									sync = True
#							else:
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc):
#									sync = True
#						else:
#							sync = False
#							if len(dirsearch) > 1 and dirsearch[1] != '':
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
#									sync = True
#							else:
#								if re.search(filesearch[1][:len(filesearch[1])-4], desc):
#									sync = True
#					filename = filename + "  " + hits + "Hits" + " - " + desc + " - uploader: " + uploader
#					if languageshort == "br":
#						languageshort = "pb"
#					subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'id': id, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
#				page1 = page1 + 1
#				if languageshort == "pb":
#					languageshort = "br"
#				content1 = opener.open(main_url + "legendas.php?l=" + languageshort + "&imdb=" + imdb[0] + "&page=" + str(page1))
#				content1 = content1.read().decode('latin1')
#				#For DEBUG only uncomment next line


##### ANNOYING #####
	#if subtitles_list == []:
		#msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
		#msgnote(debug_pretext,"Try manual or parent dir!", 2000)
	#elif subtitles_list != []:
	#	lst = str(subtitles_list)
	#	if languagelong in lst:
	#		msgnote(debug_pretext,"Found sub(s) in "  + languagelong + ".", 2000)
	#	else:
			#msgnote(debug_pretext,"No sub in "  + languagelong + "!", 2000)
			#msgnote(debug_pretext,"Try manual or parent dir!", 2000)

	#Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp


def get_download(url, download, id):
    req_headers = {
		'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
		'Referer': main_url,
		'Keep-Alive': '300',
		'Connection': 'keep-alive'}
    request = urllib2.Request(url, headers=req_headers)
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    response = opener.open(request,login_data)
    download_data = urllib.urlencode({'sid' : id, 'submit' : '+', 'action' : 'Download'})
    request1 = urllib2.Request(download, download_data, req_headers)
    f = opener.open(request1)
    return f

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

	hasLang = languageTranslate(lang1,0,2) + " " + languageTranslate(lang2,0,2) + " " + languageTranslate(lang3,0,2)

	if re.search('pt', hasLang) or re.search('en', hasLang) or re.search('es', hasLang) or re.search('pb', hasLang):
		msgnote(debug_pretext,__language__(30153), 6000)
		getallsubs(searchstring, languageTranslate(lang1,0,2), lang1, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang2,0,2), lang2, file_original_path, subtitles_list, searchstring_notclean)
		getallsubs(searchstring, languageTranslate(lang3,0,2), lang3, file_original_path, subtitles_list, searchstring_notclean)
	else:
		msg = "Won't work, LegendasDivx.com is only for PT, PTBR, ES or EN subtitles."
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				log( __name__ ,"%s base: %s" % (debug_pretext, base)) #EGO
				log( __name__ ,"%s filename: %s" % (debug_pretext, filename)) #EGO
				base = base.decode('latin1')
				filename = filename.decode('latin1')
				results.append(os.path.join(base, filename))
	return results

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext, "Downloading... Please Wait!", 6000)
	id = subtitles_list[pos][ "id" ]
	id = string.split(id,"=")
	id = id[-1]
	sync = subtitles_list[pos][ "sync" ]
	language = subtitles_list[pos][ "language_name" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))

	#This is where you are logged in and download
	content = get_download(main_url+'fazendologin.php', main_url+'downloadsub.php', id)

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