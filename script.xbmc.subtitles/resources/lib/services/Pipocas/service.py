# -*- coding: utf-8 -*-

# Service pipocas.tv version 0.0.5
# Code based on Undertext service
# Coded by HiGhLaNdR@OLDSCHOOL
# Help by VaRaTRoN
# Bugs & Features to highlander@teknorage.com
# http://www.teknorage.com
# License: GPL v2
#
# New on Service Pipocas.tv - v0.0.5:
# Developers changed the site security preventing the service to work. Service now works again.
# Fixed download bug when XBMC is set to Portuguese language and probably others.
# Some code cleanup
#
# New on Service Pipocas.tv - v0.0.4:
# Pipocas now is only for registered users so we had todo some changes to the code.
# Fixed bug on Openelec based XBMC preventing to download multiple subtitiles inside a compressed file.
# Some code cleanup
#
# New on Service Pipocas.tv - v0.0.3:
# Fixed bug on the authentication preventing to download the latest subtitles!
#
# New on Service Pipocas.tv - v0.0.2:
# Added authentication system. Now you don't need to wait 24h to download the new subtitles. Go register on the site!!!
# Added Portuguese Brazilian. Now has Portuguese and Portuguese Brazilian.
# Messages now in xbmc choosen language.
# Code re-arrange...
#
# Initial Release of Service Pipocas.tv - v0.0.1:
# Very first version of this service. Expect bugs. Regex is not the best way to parse html so nothing is perfect :)
# If you are watching this then you can see the several approaches I had with regex. The site code is a mess of html :)
# Fortunaly I came up with an ideia that sorted a few things and made the code work. Cheers!
# Expect new versions when the plugin core is changed, to due in a few weeks.
#

# pipocas.tv subtitles, based on a mod of Undertext subtitles
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, cookielib, shutil, fnmatch, uuid
from utilities import log
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

main_url = "http://pipocas.tv/"
debug_pretext = "Pipocas.tv"
subext = ['srt', 'aas', 'ssa', 'sub', 'smi']
sub_ext = ['srt', 'aas', 'ssa', 'sub', 'smi']
packext = ['rar', 'zip']
username = __addon__.getSetting( "Pipocasuser" )
password = __addon__.getSetting( "Pipocaspass" )

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

"""
<div class="box last-box"> <!-- INFO: IF last box ... add class "last-box" -->
	<div class="colhead">
		<div class="colhead-corner"></div>
		<span class="align-right"> 20/10/2011 18:23:13</span>
				<span><img alt="Portugal" class="title-flag" src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-portugal.png" />  Batman: Year One (2011)</span>
	</div>
	<div class="box-content"><br />
		
		<h1 class="title">
			Release: <input value="Batman.Year.One.2011.DVDRiP.XviD-T00NG0D" style="font-size: 8pt; color:#666666; border: solid #E7E4E0 1px; background-color: #E7E4E0;" type="text" size="105" readonly="readonly" />		</h1>
		
		<ul class="sub-details">
			<li class="sub-box1">
				<img alt="Poster" src="http://img.pipocas.tv/images/1672723.jpg" />			</li>
			<li class="sub-box2">
				<ul>
					<li><span>Fonte:</span>  Tradução</li>
					<li><span>CDs:</span> 1</li>
					<li><span>FPS:</span> 23.976</li>
					<li><span>Hits:</span> 30</li>
					<li><span>Comentários:</span> 2</li>
					<li><span>Enviada por:</span> <a href="my.php?u=23019"><font style="font-weight:normal;"> arodri</font></a> </li>
				</ul>
			</li>
			<li class="sub-box3">
				<p>Legendas Relacionadas</p>
				<ul>
					<li><span>Portugal <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-portugal.png" alt="Portugal"/></span> <a href="legendas.php?release=1672723&amp;linguagem=portugues&amp;grupo=imdb">1</a></li>
					<li><span>Brasil <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-brazil.png" alt="Brasil"/></span> <a href="legendas.php?release=1672723&amp;linguagem=brasileiro&amp;grupo=imdb">1</a></li>
					<li><span>España <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-spain.png" alt="España"/></span> <a href="legendas.php?release=1672723&amp;linguagem=espanhol&amp;grupo=imdb">0</a></li>
					<li><span>England <img src="http://img.pipocas.tv/themes/pipocas2/css/img/flag-uk.png" alt="UK"/></span> <a href="legendas.php?release=1672723&amp;linguagem=ingles&amp;grupo=imdb">0</a></li>
				</ul>
			</li>
			<li class="sub-box4"><div style="padding-left:25px;"><div id="rate_23671"><ul class="star-rating"><li style="width: 100%;" class="current-rating">.</li><li><a href="/rating.php?id=23671&amp;rate=1&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="one-star" onclick="do_rate(1,23671,'legenda'); return false" title="1 estrela de 5" >1</a></li><li><a href="/rating.php?id=23671&amp;rate=2&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="two-stars" onclick="do_rate(2,23671,'legenda'); return false" title="2 estrelas de 5" >2</a></li><li><a href="/rating.php?id=23671&amp;rate=3&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="three-stars" onclick="do_rate(3,23671,'legenda'); return false" title="3 estrelas de 5" >3</a></li><li><a href="/rating.php?id=23671&amp;rate=4&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="four-stars" onclick="do_rate(4,23671,'legenda'); return false" title="4 estrelas de 5" >4</a></li><li><a href="/rating.php?id=23671&amp;rate=5&amp;ref=%2Flegendas.php%3Frelease%3Dbatman%26grupo%3Drel%26linguagem%3Dtodas&amp;what=legenda" class="five-stars" onclick="do_rate(5,23671,'legenda'); return false" title="5 estrelas de 5" >5</a></li></ul>5.00 / 5 de 1 Voto(s)</div></div><br />
				<a href="download.php?id=23671" class="download"></a>
				<a href="info/23671/Batman.Year.One.2011.DVDRiP.XviD-T00NG0D.html" class="info"></a>
								<a href="vagradecer.php?id=23671" class="thanks"></a> 			</li>
		</ul>
		<br class="clr"/>
		
		<div class="horizontal-divider"></div>
		
		<p class="description-title">Descrição</p>
		<div class="description-box">
			<center><font color="#2B60DE">Batman: Year One </font></center><br />
<br />
<center><b><br />
<br />
Versão<br />
Batman.Year.One.2011.DVDRiP.XviD-T00NG0D<br />
<br />
</b></center><br />
<br />
Tradução Brasileira &nbsp;por The_Tozz e Dres<br />
<br />
<br />
A adaptação PtPt: <center><span style="font-size:12px;"><font face="arial"><font color="#0000A0">arodri</font></font> </span></center><br />
<br />
Um agradecimento muito especial à<br />
<br />
<center><b><font color="#008000"><span style="font-size:14px;">FreedOM</span></font></b></center><br />
<br />
Pela revisão total...<br />
<br />
"""
subtitle_pattern = "<a href=\"info.php(.+?)\" class=\"info\"></a>"
name_pattern = "<h1 class=\"title\">[\r\n\s].+?Release: (.+?)</h1>"
id_pattern = "download.php\?id=(.+?)\""
hits_pattern = "<li><span>Hits:</span> (.+?)</li>"
#desc_pattern = "<div class=\"description-box\">([\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*[\n\r\t].*)<center><iframe"
uploader_pattern = "<a href=\"/my.php\?u.+?:normal;\"> (.+?)</font></a>"
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

	# LOGIN FIRST AND THEN SEARCH
	url = main_url + 'vlogin.php'
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

	page = 0
	if languageshort == "pt":
		url = main_url + "legendas.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
	if languageshort == "pb":
		url = main_url + "legendas.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)

	content = opener.open(url)
	content = content.read()
	content = content.decode('latin1')
	while re.search(subtitle_pattern, content, re.IGNORECASE | re.DOTALL) and page < 2:
		#log( __name__ ,"%s Getting '%s' inside while ..." % (debug_pretext, subtitle_pattern))
		for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
			#log( __name__ ,"%s FILENAME: '%s' ..." % (debug_pretext, matches.group(1)))
			#hits = matches.group(4)
			#id = matches.group(2)
			#movieyear = matches.group(2)
			#no_files = matches.group(3)
			#uploader = string.strip(matches.group(2))
			#downloads = int(matches.group(2)) / 2
			#if (downloads > 10):
			#	downloads=10
			#filename = string.strip(matches.group(1))
			#desc = string.strip(matches.group(1))
			#desc = string.strip(matches.group(13))
			#Remove new lines on the commentaries
			details = matches.group(1)
			content_details = opener.open(main_url + "info.php" + details)
			content_details = content_details.read()
			content_details = content_details.decode('latin1')
			for namematch in re.finditer(name_pattern, content_details, re.IGNORECASE | re.DOTALL):
				filename = string.strip(namematch.group(1))
				desc = filename
				log( __name__ ,"%s FILENAME match: '%s' ..." % (debug_pretext, namematch.group(1)))			
			for idmatch in re.finditer(id_pattern, content_details, re.IGNORECASE | re.DOTALL):
				id = idmatch.group(1)
				log( __name__ ,"%s ID match: '%s' ..." % (debug_pretext, idmatch.group(1)))			
			for upmatch in re.finditer(uploader_pattern, content_details, re.IGNORECASE | re.DOTALL):
				uploader = upmatch.group(1)
			for hitsmatch in re.finditer(hits_pattern, content_details, re.IGNORECASE | re.DOTALL):
				hits = hitsmatch.group(1)
			log( __name__ ,"%s UP match: '%s' ..." % (debug_pretext, upmatch.group(1)))			
			#for descmatch in re.finditer(desc_pattern, content_details, re.IGNORECASE | re.DOTALL):
			#	desc = string.strip(descmatch.group(1))
			#	log( __name__ ,"%s DESC match: '%s' ..." % (debug_pretext, decmatch.group(1)))
			downloads = int(hits) / 4
			if (downloads > 10):
				downloads=10
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
			#filename = filename + " " + "(" + movieyear + ")" + "  " + hits + "Hits" + " - " + desc
			filename = filename + " " + "- Enviado por: " + uploader +  " - Hits: " + hits
			#subtitles_list.append({'rating': str(downloads), 'no_files': no_files, 'filename': filename, 'desc': desc, 'sync': sync, 'hits' : hits, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
			subtitles_list.append({'rating': str(downloads), 'filename': filename, 'hits': hits, 'desc': desc, 'sync': sync, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})
		page = page + 1
		if languageshort == "pt":
			url = main_url + "legendas.php?grupo=rel&linguagem=portugues&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
		if languageshort == "pb":
			url = main_url + "legendas.php?grupo=rel&linguagem=brasileiro&page=" + str(page) + "&release=" + urllib.quote_plus(searchstring)
		content = opener.open(url)
		content = content.read()
		content = content.decode('latin1')

	
#	Bubble sort, to put syncs on top
	for n in range(0,len(subtitles_list)):
		for i in range(1, len(subtitles_list)):
			temp = subtitles_list[i]
			if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
				subtitles_list[i] = subtitles_list[i-1]
				subtitles_list[i-1] = temp


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

	portuguesebrazil = 0
	if string.lower(lang1) == "portuguesebrazil": portuguesebrazil = 1
	elif string.lower(lang2) == "portuguesebrazil": portuguesebrazil = 2
	elif string.lower(lang3) == "portuguesebrazil": portuguesebrazil = 3
	
	if ((portuguese > 0) and (portuguesebrazil == 0)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguesebrazil > 0) and (portuguese == 0)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese > 0) and (portuguesebrazil > 0) and (portuguese < portuguesebrazil)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese > 0) and (portuguesebrazil > 0) and (portuguese > portuguesebrazil)):
			msgnote(debug_pretext,__language__(30153), 12000)
			getallsubs(searchstring, "pb", "PortugueseBrazil", file_original_path, subtitles_list, searchstring_notclean)
			getallsubs(searchstring, "pt", "Portuguese", file_original_path, subtitles_list, searchstring_notclean)

	if ((portuguese == 0) and (portuguesebrazil == 0)):
			msg = "Won't work, Pipocas.tv is only for Portuguese and Portuguese Brazil subtitles."
	
	return subtitles_list, "", msg #standard output
	
def recursive_glob(treeroot, pattern):
	results = []
	for base, dirs, files in os.walk(treeroot):
		for extension in pattern:
			for filename in fnmatch.filter(files, '*.' + extension):
				results.append(os.path.join(base, filename))
	return results

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
    download_data = urllib.urlencode({'id' : id})
    request1 = urllib2.Request(download, download_data, req_headers)
    f = opener.open(request1)
    return f 

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	msgnote(debug_pretext,__language__(30154), 6000)
	id = subtitles_list[pos][ "id" ]
	sync = subtitles_list[pos][ "sync" ]
	language = subtitles_list[pos][ "language_name" ]
	log( __name__ ,"%s Fetching id using url %s" % (debug_pretext, id))

	url = main_url + 'vlogin.php'
	download = main_url + 'download.php?id=' + id
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
	download_data = urllib.urlencode({'id' : id})
	request1 = urllib2.Request(download, download_data, req_headers)
	content = opener.open(request1)

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