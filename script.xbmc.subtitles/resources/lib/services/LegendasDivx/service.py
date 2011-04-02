# -*- coding: utf-8 -*-

# Version 0.1.6
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# FIXED on v0.1.6:
# Movies or TV eps with 2cds or more will now work.
# Sync subs is now much more accurate.
#
# FIXED on v0.1.5:
# TV Season packs now downloads and chooses the best one available in the pack
# Movie packs with several releases now works too, tries to choose the sync sub using filename or dirname
# Search description for SYNC subtitles using filename or dirname
#
# KNOWN BUGS (TODO for next versions):
# Regex isn't perfect so a few results might have html tags still, not many but...
# Filtering languages, shows only European Portuguese flag.
# Just using .srt subs. Others will come in further versions.

# LegendasDivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__

main_url = "http://www.legendasdivx.com/"
debug_pretext = "LegendasDivx"

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="sub_box">
<div class="sub_header">
<b>The Dark Knight</b> (2008) &nbsp; - &nbsp; Enviada por: <a href='modules.php?name=User_Info&username=tck17'><b>tck17</b></a> &nbsp; em 2010-02-03 02:44:09

</div>
<table class="sub_main color1" cellspacing="0">
<tr>
<th class="color2">Idioma:</th>
<td><img width="18" height="12" src="modules/Downloads/img/portugal.gif" /></td>
<th>CDs:</th>
<td>1&nbsp;</td>
<th>Frame Rate:</th>
<td>23.976&nbsp;</td>
<td rowspan="2" class="td_right color2">
<a href="?name=Downloads&d_op=ratedownload&lid=128943">
<img border="0" src="modules/Downloads/images/rank9.gif"><br>Classifique (3 votos)

</a>
</td>
</tr>
<tr>
<th class="color2">Hits:</th>
<td>1842</td>
<th>Pedidos:</th>
<td>77&nbsp;</td>
<th>Origem:</th>
<td>DVD Rip&nbsp;</td>
</tr>

<tr>
<th class="color2">Descrição:</th>
<td colspan="5" class="td_desc brd_up">Não são minhas.<br />
<br />
Release: The.Dark.Knight.2008.720p.BluRay.DTS.x264-ESiR</td>
"""
#subtitle_pattern = "<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?img/(.+?)gif\".+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)&nbsp;</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>"
# group(1) = Name, group(2) = Year, group(3) = Language, group(4)= Number Files, group(5) = ID, group(6) = Hits, group(7) = Requests, group(8) = Description

subtitle_pattern = "<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)&nbsp;</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>"
# group(1) = Name, group(2) = Year, group(3) = Number Files, group(4) = ID, group(5) = Hits, group(6) = Requests, group(7) = Description
#====================================================================================================================
# Functions
#====================================================================================================================

def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	page = 1
	if languageshort == "pt":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)

	content = geturl(url)
	log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(5)
			id = matches.group(4)
			movieyear = matches.group(2)
			no_files = matches.group(3)
			downloads = int(matches.group(5)) / 500
			if (downloads > 10):
				downloads=10
			filename = string.strip(matches.group(1))
			desc = string.strip(matches.group(7))
			#Remove new lines on the commentaries
			filename = re.sub('\n',' ',filename)
			desc = re.sub('\n',' ',desc)
			#Remove HTML tags on the commentaries
			filename = re.sub(r'<[^<]+?>','', filename)
			desc = re.sub(r'<[^<]+?>|[~]','', desc)
			#Find filename on the comentaries to show sync label using filename or dirname (making it global for further usage)
			global filesearch
			filesearch = os.path.split(file_original_path)
			dirsearch = string.split(filesearch[0], '/')
			dirsearch_check = string.split(dirsearch[-1], '.')
			if (searchstring_notclean != ""):
				sync = False
				if re.search(searchstring_notclean, desc):
					sync = True
				#log( __name__ ,"%s dirsearch-2 found: %s" % (debug_pretext, searchstring_notclean))
			else:
				if (string.lower(dirsearch_check[-1]) == "rar") or (string.lower(dirsearch_check[-1]) == "cd1") or (string.lower(dirsearch_check[-1]) == "cd2"):
					sync = False
					if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-2], desc):
						sync = True
					log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
					#log( __name__ ,"%s dirsearch-2 found: %s" % (debug_pretext, dirsearch[-2]))
				else:
					sync = False
					if re.search(filesearch[1][:len(filesearch[1])-4], desc) or re.search(dirsearch[-1], desc):
						sync = True
					log( __name__ ,"%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
					#log( __name__ ,"%s dirsearch-2 found: %s" % (debug_pretext, dirsearch[-1]))
				log( __name__ ,"%s Desc found: %s (id = %s)" % (debug_pretext, desc, id))
			filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 1
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		content = geturl(url)

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
	israr = os.path.split(file_original_path)
	israr = string.split(israr[0], '/')
	israr = string.split(israr[-1], '.')
	israr = string.lower(israr[-1])
	
	#log( __name__ ,"%s string israr = %s" % (debug_pretext, israr))

	if len(tvshow) == 0:
		if 'rar' in israr and searchstring is not None:
			#log( __name__ ,"%s em israr = %s" % (debug_pretext, israr))
			if 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
				#log( __name__ ,"%s em cd1-2-3 = %s" % (debug_pretext, israr))
				dirsearch = os.path.split(file_original_path)
				dirsearch = string.split(dirsearch[0], '/')
				searchstring_notclean = dirsearch[-3]
				searchstring = xbmc.getCleanMovieTitle(dirsearch[-3])
				searchstring = searchstring[0]
				#log( __name__ ,"%s searchstringisrar = %s" % (debug_pretext, searchstring))
				#log( __name__ ,"%s searchstringnotclean = %s" % (debug_pretext, searchstring_notclean))
			else:
				searchstring = title
				#log( __name__ ,"%s searchstringELSEafterIF = %s" % (debug_pretext, searchstring))
		elif 'cd1' in string.lower(title) or 'cd2' in string.lower(title) or 'cd3' in string.lower(title):
			dirsearch = os.path.split(file_original_path)
			dirsearch = string.split(dirsearch[0], '/')
			searchstring_notclean = dirsearch[-2]
			searchstring = xbmc.getCleanMovieTitle(dirsearch[-2])
			searchstring = searchstring[0]
			#log( __name__ ,"%s searchstringnotrar = %s" % (debug_pretext, searchstring))
			#log( __name__ ,"%s searchstringnotclean = %s" % (debug_pretext, searchstring_notclean))
		else:
			searchstring = title
			#log( __name__ ,"%s searchstringELSE = %s" % (debug_pretext, searchstring))
			
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
		goodfiles = fnmatch.filter(files, pattern)
		results.extend(os.path.join(base, f) for f in goodfiles)
	return results 

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, subtitles_list))
	id = subtitles_list[pos][ "id" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))
	#Grabbing login and pass from xbmc settings
	username = __settings__.getSetting( "LDivxuser" )
	password = __settings__.getSetting( "LDivxpass" )
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders.append(('User-agent', 'Mozilla/4.0'))
	opener.addheaders.append(('Referer', 'http://www.legendasdivx.com/modules.php?name=Your_Account&op=userinfo&bypass=1&username=highlander'))
	login_data = urllib.urlencode({'username' : username, 'user_password' : password, 'op' : 'login'})
	#This is where you are logged in
	resp = opener.open('http://www.legendasdivx.com/modules.php?name=Your_Account', login_data)
	#For DEBUG only uncomment next line
	#log( __name__ ,"%s resposta '%s' subs ..." % (debug_pretext, resp))
	#Now you can go to member only pages
	resp1 = opener.open('http://www.legendasdivx.com/modules.php?name=Your_Account&op=userinfo&bypass=1&username=highlander')
	d = resp1.read()
	#Now you download the subtitles
	language = subtitles_list[pos][ "language_name" ]
	if string.lower(language) == "portuguese":
		content = opener.open('http://www.legendasdivx.com/modules.php?name=Downloads&d_op=getit&lid=' + id + '&username=highlander')

	if content is not None:
		header = content.info()['Content-Disposition'].split('filename')[1].split('.')[-1].strip("\"")
		#log( __name__ ,"%s Fetching subtitles using url %s" % (debug_pretext, content))
		if header == 'rar':
			log( __name__ ,"%s file: content is RAR" % (debug_pretext)) #EGO
			local_tmp_file = os.path.join(tmp_sub_dir, "ldivx.rar")
			log( __name__ ,"%s file: local_tmp_file %s" % (debug_pretext, local_tmp_file)) #EGO
			packed = True
		elif header == 'zip':
			local_tmp_file = os.path.join(tmp_sub_dir, "ldivx.zip")
			packed = True
		else: # never found/downloaded an unpacked subtitles file, but just to be sure ...
			local_tmp_file = os.path.join(tmp_sub_dir, "ldivx.srt") # assume unpacked sub file is an '.srt'
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
				searchsubs = recursive_glob(tmp_sub_dir, '*.srt')
				searchsubscount = len(searchsubs)
				for filesub in searchsubs:
					nopath = string.split(filesub, tmp_sub_dir)[-1]
					justfile = string.split(nopath, '\\')[-1]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-nopath: '%s'" % (debug_pretext, nopath))
					#log( __name__ ,"%s DEBUG-justfile: '%s'" % (debug_pretext, justfile))
					releasefilename = filesearch[1][:len(filesearch[1])-4]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-releasefilename: '%s'" % (debug_pretext, releasefilename))
					subsfilename = justfile[:len(justfile)-4]
					#For DEBUG only uncomment next line
					#log( __name__ ,"%s DEBUG-subsfilename: '%s'" % (debug_pretext, subsfilename))
					#log( __name__ ,"%s DEBUG-subscount: '%s'" % (debug_pretext, searchsubscount))
					if searchsubscount == 1:
						#log( __name__ ,"%s DEBUG-inside subscount: '%s'" % (debug_pretext, searchsubscount))
						subs_file = filesub
					elif (string.lower(subsfilename)) == (string.lower(releasefilename)):
						subs_file = filesub
						#For DEBUG only uncomment next line
						#log( __name__ ,"%s DEBUG-subsfile: '%s'" % (debug_pretext, subs_file))
					else:
						multicds_pattern = "\+?(cd\d)\+?"
						multicdsubs = re.search(multicds_pattern, subsfilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
						multicdsrls = re.search(multicds_pattern, releasefilename, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE)
						if (multicdsubs != None) and (multicdsrls != None):
							multicdsubs = multicdsubs.group(1)
							multicdsrls = multicdsrls.group(1)
							#log( __name__ ,"%s DEBUG-multicdsubs: '%s'" % (debug_pretext, multicdsubs))
							#log( __name__ ,"%s DEBUG-multicdsrls: '%s'" % (debug_pretext, multicdsrls))
							if (string.lower(multicdsrls) == string.lower(multicdsubs)):
								subs_file = filesub
				else:
					subs_file = filesub
								
		return False, language, subs_file #standard output