# -*- coding: utf-8 -*-

# Service LegendasDivx.com version 0.2.3
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# NEW on Service LegendasDivx.com v0.2.3:
# Fixed typo on the version.
# Added built-in notifications.
#
# NEW on Service LegendasDivx.com v0.2.2:
# Fixed pathnames using (os.sep). For sure :)
#
# NEW on Service LegendasDivx.com v0.2.1:
# Fixed bug when the file is played from a root path, no parent dir search\sync when that happens.
# Fixed pathnames to work with all OS (Win, Unix, etc).
# Added pattern to search several subtitle extensions.
#
# NEW on Service LegendasDivx.com v0.2.0:
# Better "star" rating, remember that the start rating is calculated using the number of hits/downloads.
# Fixed a bug in the SYNC subtitles, it wouldn't assume that any were sync (in the code), a dialog box would open in multi packs.
#
# NEW on Service LegendasDivx.com v0.1.9:
# When no sync subtitle is found and the pack has more then 1 sub, it will open a dialog box for browsing the substitles inside the multi pack.
#
# NEW on Service LegendasDivx.com v0.1.8:
# Uncompress rar'ed subtitles inside a rar file... yeh weird site...
#
# NEW on Service LegendasDivx.com v0.1.7:
# BUG found in multi packs is now fixed.
# Added more accuracy to the selection of subtitle to load. Now checks the release dirname against the subtitles downloaded.
# When no sync is found and if the substitle name is not equal to the release dirname or release filename it will load one random subtitle from the package.
#
# NEW on Service LegendasDivx.com v0.1.6:
# Movies or TV eps with 2cds or more will now work.
# Sync subs is now much more accurate.
#
# Initial Release of Service LegendasDivx.com - v0.1.5:
# TV Season packs now downloads and chooses the best one available in the pack
# Movie packs with several releases now works too, tries to choose the sync sub using filename or dirname
# Search description for SYNC subtitles using filename or dirname
#
# KNOWN BUGS (TODO for next versions):
# Regex isn't perfect so a few results might have html tags still, not many but ...
# Filtering languages, shows only European Portuguese flag.

# LegendasDivx.com subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__        = sys.modules[ "__main__" ].__cwd__

main_url = "http://www.legendasdivx.com/"
debug_pretext = "LegendasDivx"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']

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

subtitle_pattern = "<div\sclass=\"sub_box\">[\r\n\t]{2}<div\sclass=\"sub_header\">[\r\n\t]{2}<b>(.+?)</b>\s\((\d\d\d\d)\)\s.+?[\r\n\t ]+?[\r\n\t]</div>[\r\n\t]{2}<table\sclass=\"sub_main\scolor1\"\scellspacing=\"0\">[\r\n\t]{2}<tr>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th>CDs:</th>[\r\n\t ]{2}<td>(.+?)</td>[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<a\shref=\"\?name=Downloads&d_op=ratedownload&lid=(.+?)\">[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}.+?[\r\n\t]{2}<th\sclass=\"color2\">Hits:</th>[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t]{2}<td>(.+?)</td>[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?[\r\n\t ]{2}.+?.{2,5}[\r\n\t ]{2}.+?[\r\n\t ]{2}<td\scolspan=\"5\"\sclass=\"td_desc\sbrd_up\">((\n|.)*)</td>"
# group(1) = Name, group(2) = Year, group(3) = Number Files, group(4) = ID, group(5) = Hits, group(6) = Requests, group(7) = Description
#====================================================================================================================
# Functions
#====================================================================================================================
def msg(text, timeout):
	icon =  os.path.join(__cwd__,"icon.png")
	xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,timeout,icon))


def getallsubs(searchstring, languageshort, languagelong, file_original_path, subtitles_list, searchstring_notclean):

	page = 1
	if languageshort == "pt":
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)

	content = geturl(url)
	log( __name__ ,"%s Getting '%s' subs ..." % (debug_pretext, languageshort))
	msg("Searching Title... Please wait!", 6000)
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE) and page < 6:
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE | re.VERBOSE):
			hits = matches.group(5)
			id = matches.group(4)
			movieyear = matches.group(2)
			no_files = matches.group(3)
			downloads = int(matches.group(5)) / 300
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
			filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
			subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 1
		url = main_url + "modules.php?name=Downloads&file=jz&d_op=search_next&order=&form_cat=28&page=" + str(page) + "&query=" + urllib.quote_plus(searchstring)
		content = geturl(url)

	if subtitles_list != []:
		msg("Finished Searching. Choose One!", 3000)
	else:
		msg("No Results! Try Parent Dir Or Manual!", 4000)
		
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

	msg("Downloading... Please Wait!", 6000)
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
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
			msg("Extracting... Please Wait!", 6000)
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
				msg("Done Extracting!", 3000)
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
		
		msg("Playing Title!", 3000)

		return False, language, subs_file #standard output