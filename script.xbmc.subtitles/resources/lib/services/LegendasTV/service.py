# -*- coding: UTF-8 -*-

# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 1.0.4

import xbmc, xbmcgui
import cookielib, urllib2, urllib, sys, re, os, webbrowser, time, unicodedata
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from htmlentitydefs import name2codepoint as n2cp
from utilities import log

base_url = "http://legendas.tv"
sub_ext = "srt,aas,ssa,sub,smi"
debug_pretext = ""
YEAR_MAX_ERROR = 1

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	cookie = LegendasLogin()
	if len(tvshow) > 0:
		subtitles =  LegendasTVSeries(tvshow, year, season, episode, lang1, lang2, lang3 )
	else:
		subtitles =  LegendasTVMovies(file_original_path, title, year, lang1, lang2, lang3 )
	return subtitles, cookie, ""

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	# Parse the cookie to LegendasLogin and install the url opener
	LegendasLogin(session_id)
	#Create some variables
	subtitle = ""
	extract_path = os.path.join(tmp_sub_dir, "extracted")
	# Download the subtitle using its ID.
	id = subtitles_list[pos][ "ID" ]
	url_request = base_url+'/info.php?d='+id+'&c=1'
	request =  urllib2.Request(url_request)
	response = urllib2.urlopen(request)
	ltv_sub = response.read()
	
	# Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
	# Write the subtitle in binary mode.
	fname = os.path.join(tmp_sub_dir,str(id))
	if response.info().get('Content-Type').__contains__('rar'):
		fname += '.rar'
	else:
		fname += '.zip'
	f = open(fname,'wb')
	f.write(ltv_sub)
	f.close()
	
	# Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
	# then removes all files from the temp dir that aren't subtitles.
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
	
	# If there are more than one subtitle in the temp dir, launch a browse dialog
	# so user can choose. If only one subtitle is found, parse it to the addon.
	if len(legendas_tmp) > 1:
		dialog = xbmcgui.Dialog()
		subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, extract_path+"/")
		if subtitle == extract_path+"/": subtitle = ""
	elif legendas_tmp:
		subtitle = legendas_tmp[0]
	
	language = subtitles_list[pos][ "language_name" ]
	return False, language, subtitle #standard output

def LegendasLanguage(lang1,lang2,lang3):
	if lang1 == "PortugueseBrazil" or lang1 == "Brazilian":
		ltv_flag1 = "pb"
		langid1 = "1"
	elif lang1 == "Portuguese":
		ltv_flag1 = "pt"
		langid1 = "10"
	elif lang1 == "English":
		ltv_flag1 = "en"
		langid1 = "2"
	elif lang1 == "Spanish":
		ltv_flag1 = "es"
		langid1 = "3"
	else:
		lang1 = "PortugueseBrazil"
		ltv_flag1 = "pb"
		langid1 = "1"
		
	if lang2 == "PortugueseBrazil" or lang2 == "Brazilian":
		ltv_flag2 = "pb"
		langid2 = "1"
	elif lang2 == "Portuguese":
		ltv_flag2 = "pt"
		langid2 = "10"
	elif lang2 == "English":
		ltv_flag2 = "en"
		langid2 = "2"
	elif lang2 == "Spanish":
		ltv_flag2 = "es"
		langid2 = "3"
	else:
		lang2 = "Portuguese"
		ltv_flag2 = "pt"
		langid2 = "10"

	if lang3 == "PortugueseBrazil" or lang3 == "Brazilian":
		ltv_flag3 = "pb"
		langid3 = "1"
	elif lang3 == "Portuguese":
		ltv_flag3 = "pt"
		langid3 = "10"
	elif lang3 == "English":
		ltv_flag3 = "en"
		langid3 = "2"
	elif lang3 == "Spanish":
		ltv_flag3 = "es"
		langid3 = "3"
	else:
		lang3 = "Spanish"
		ltv_flag3 = "es"
		langid3 = "3"
	
	return lang1, ltv_flag1, langid1, lang2, ltv_flag2, langid2, lang3, ltv_flag3, langid3

# Log into LTV and retrieve the cookie. If the cookie is parsed,
# only install the url opener.
def LegendasLogin(cj=0):
	if cj:
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		urllib2.install_opener(opener)
	else:
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		urllib2.install_opener(opener)
		username = __addon__.getSetting( "LTVuser" )
		password = __addon__.getSetting( "LTVpass" )
		login_data = urllib.urlencode({'txtLogin':username,'txtSenha':password})
		request = urllib2.Request(base_url+'/login_verificar.php',login_data)
		response = urllib2.urlopen(request).read()
		if response.__contains__('Dados incorretos'):
			log( __name__ ,u" Login Failed. Check your data at the addon configuration.")
			xbmc.executebuiltin("Notification(Legendas.TV,%s,10000])"%( _( 756 ).encode('utf-8') ))
		else:
			log( __name__ ,u" Succesfully logged in.")
	return cj

def LegendasTVMovies(file_original_path, title, year, lang1, lang2, lang3 ):

	# Initiating variables and languages.
	lang1, ltv_flag1, langid1, lang2, ltv_flag2, langid2, lang3, ltv_flag3, langid3 = LegendasLanguage(lang1,lang2,lang3)
	tipo = "2"
	subtitles, sub1, sub2, sub3, PartialSubtitles = [], [], [], [], []
	
	# Try to get the original movie name from the XBMC database, 
	# and if not available, set it to the parsed title.
	xbmcPlayerTitle = xbmc.getCleanMovieTitle( xbmc.getInfoLabel("VideoPlayer.Title") )[0]
	original_title = re.sub("</?[^>]*>","",xbmc.executehttpapi("QueryVideoDatabase(select c16 from movie where movie.c00 = \""+xbmcPlayerTitle+"\")"))

	if original_title == "" or year == "" : original_title = CleanLTVTitle(title)
	else:
		original_title = CleanLTVTitle(original_title)
		log( __name__ ,u"%s Original Title[%s]" % (debug_pretext, original_title))

	# Encodes the first search string using the original movie title,
	# and download it.
	search_string = original_title
	log( __name__ ,u"Searching[%s]" % (debug_pretext))
	if len(search_string) < 3: search_string = search_string + year
	search_dict = {'txtLegenda':search_string,'selTipo':tipo,'int_idioma':'99'}
	search_data = urllib.urlencode(search_dict)
	request = urllib2.Request(base_url+'/index.php?opcao=buscarlegenda',search_data)
	response = to_unicode_or_bust(urllib2.urlopen(request).read())

	# If no subtitles with the original name are found, try the parsed title.
	if response.__contains__('Nenhuma legenda foi encontrada') and original_title != title:
		log( __name__ ,u" No subtitles found using the original title, using title instead.")
		search_string = CleanLTVTitle(title)
		search_dict = {'txtLegenda':search_string,'selTipo':tipo,'int_idioma':'99'}
		search_data = urllib.urlencode(search_dict)
		request = urllib2.Request(base_url+'/index.php?opcao=buscarlegenda',search_data)
		response = to_unicode_or_bust(urllib2.urlopen(request).read())

	# Retrieves the number of pages.
	pages = re.findall("<a class=\"paginacao\" href=",response)
	if pages: pages = len(pages)+1
	else: pages = 1
	log( __name__ ,u"%s Found [%s] pages." % (debug_pretext, pages))

	# Download all pages content.
	for x in range(pages):
		if x:
			log( __name__ ,u"%s Downloading page [%s]" % (debug_pretext, str(x+1)))
			html = urllib2.urlopen(base_url+'/index.php?opcao=buscarlegenda&pagina='+str(x+1)).read()
			response = response + to_unicode_or_bust(html)
	log( __name__ ,u"%s Results downloaded." % (debug_pretext))
	
	# Parse all content to BeautifulSoup
	soup = BeautifulSoup(response)
	td_results =  soup.findAll('td',{'id':'conteudodest'})
	for td in td_results:
		span_results = td.findAll('span')
		for span in span_results:
			if span.attrs == [('class', 'brls')]:
				continue
			td = span.find('td',{'class':'mais'})
			
			# Translated and original titles from LTV.
			ltv_title = CleanLTVTitle(td.contents[2])
			ltv_original_title = CleanLTVTitle(td.contents[0].contents[0])
			
			if re.search("[0-9]+[St|Nd|Rd|Th] Season", ltv_original_title): continue
			
			# Release name of the subtitle file.
			release = Uconvert(td.parent.parent.find('span',{'class':'brls'}).contents[0])
			
			# Retrieves the rating of the subtitle, and set it to '0' id not available.
			ltv_rating = td.contents[10]
			ltv_rating = chomp(ltv_rating.split("/")[0])
			if ltv_rating == "N": ltv_rating = "0"
			user = span.findAll('td')[3].contents[0].contents[0]
			
			# This is the download ID for the subtitle.
			download_id = re.search('[a-z0-9]{32}',td.parent.parent.attrs[1][1]).group(0)

			# Find the language of the subtitle extracting it from a image name,
			# and convert it to the OpenSubtitles format.
			ltv_lang = re.findall("images/flag_([^.]*).gif",span.findAll('td')[4].contents[0].attrs[0][1])
			if ltv_lang: ltv_lang = ltv_lang[0]
			if ltv_lang == "br": ltv_lang = "pb"
			if ltv_lang == "us": ltv_lang = "en"
			
			# Compare the retrieved titles from LTV to those parsed or snatched by this service.
			# Each language is appended to a sequence.
			original_title, title = CleanLTVTitle(original_title), CleanLTVTitle(title)
			if comparetitle(ltv_original_title, original_title) or comparetitle(ltv_title, title) or comparetitle(ltv_original_title, title) or comparetitle(original_title, ltv_title) or re.findall('^'+original_title+"[ |$]",ltv_original_title) or re.findall(original_title+'$',ltv_original_title) or re.findall('^'+title,ltv_title) or re.findall(title+'$',ltv_title):
				if ltv_lang == ltv_flag1: sub1.append( { "title" : ltv_title, "filename" : release,"language_name" : lang1, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag1+".gif" } )
				if ltv_lang == ltv_flag2: sub2.append( { "title" : ltv_title, "filename" : release,"language_name" : lang2, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag2+".gif" } )
				if ltv_lang == ltv_flag3: sub3.append( { "title" : ltv_title, "filename" : release,"language_name" : lang3, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag3+".gif" } )
				log( __name__ ,u" Matched!\nTitle[%s], Original Title[%s]\nLTV Title[%s], LTV Original Title[%s]\nID[%s], Release[%s], Language[%s], Rating[%s]" % (title, original_title, ltv_title, ltv_original_title, download_id, release, ltv_lang, ltv_rating))
			else:log( __name__ ,u" Mismatched.\nTitle[%s], Original Title[%s]\nLTV Title[%s], LTV Original Title[%s]\nID[%s], Release[%s], Language[%s], Rating[%s]" % (title, original_title, ltv_title, ltv_original_title, download_id, release, ltv_lang, ltv_rating))

	# Append all three language sequences.
	subtitles.extend(sub1)
	subtitles.extend(sub2)
	subtitles.extend(sub3)
	return subtitles

def LegendasTVSeries(tvshow, year, season, episode, lang1, lang2, lang3 ):

	# Initiating variables and languages.
	lang1, ltv_flag1, langid1, lang2, ltv_flag2, langid2, lang3, ltv_flag3, langid3 = LegendasLanguage(lang1,lang2,lang3)
	tipo = "1"
	subtitles, sub1, sub2, sub3, PartialSubtitles = [], [], [], [], []
	
	# Searching XBMC Database for TheTVDb id of the tvshow and retreaving the original tvshow title from TheTVDB.
	# This tries to avoid mismatches when using translated tvshow names.
	
	try:
		xbmcTVShow = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
		tvshow_id = int(re.sub("</?[^>]*>","",xbmc.executehttpapi("QueryVideoDatabase(select c12 from tvshow where c00 = \""+xbmcTVShow+"\")")))
		if tvshow_id: original_tvshow = CleanLTVTitle(BeautifulStoneSoup(urllib2.urlopen("http://www.thetvdb.com/data/series/"+str(tvshow_id)+"/").read()).data.series.seriesname.string)
		else: original_tvshow = CleanLTVTitle(tvshow)
	except: original_tvshow = CleanLTVTitle(tvshow)
	log( __name__ , original_tvshow )

	# Formating the season to double digit format
	if int(season) < 10: ss = "0"+season
	else: ss = season
	if int(episode) < 10: ee = "0"+episode
	else: ee = episode

	# Setting up the search string; the original tvshow name is preferable.
	# If the tvshow name lenght is less than 3 characters, append the year to the search.
	
	search_string = original_tvshow + " " +"S"+ss+"E"+ee
	if len(search_string) < 3: search_string = search_string +" "+ year
	log( __name__ , "Searching "+search_string )
	
	# Doing the search and parsing the results to BeautifulSoup
	search_dict = {'txtLegenda':search_string,'selTipo':tipo,'int_idioma':'99'}
	search_data = urllib.urlencode(search_dict)
	request = urllib2.Request(base_url+'/index.php?opcao=buscarlegenda',search_data)
	response = urllib2.urlopen(request)
	page = to_unicode_or_bust(response.read())
	soup = BeautifulSoup(page)
	span_results = soup.find('td',{'id':'conteudodest'}).findAll('span')
	for span in span_results:
	
		# Jumping season packs
		if span.attrs == [('class', 'brls')]:
			continue
		td = span.find('td',{'class':'mais'})

		# Translated and original titles from LTV, the LTV season number and the
		# scene release name of the subtitle. If a movie is retrieved, the re.findall
		# will raise an exception and will continue to the next loop.
		reResult = re.findall("(.*) - [0-9]*",CleanLTVTitle(td.contents[2]))
		if reResult: ltv_title = reResult[0]
		else:
			ltv_title = CleanLTVTitle(td.contents[2])
		
		reResult = re.findall("(.*) - ([0-9]*)",CleanLTVTitle(td.contents[0].contents[0]))
		if reResult: ltv_original_title, ltv_season = reResult[0]
		else:
			ltv_original_title = CleanLTVTitle(td.contents[0].contents[0])
			ltv_season = 0

		release = td.parent.parent.find('span',{'class':'brls'}).contents[0]
		if not ltv_season:
			reResult = re.findall("[Ss]([0-9]+)[Ee][0-9]+",release)
			if reResult: ltv_season = re.sub("^0","",reResult[0])
			
		if not ltv_season: continue

		# Retrieves the rating of the subtitle, and set it to '0' if not available.
		ltv_rating = td.contents[10]
		ltv_rating = chomp(ltv_rating.split("/")[0])
		if ltv_rating == "N": ltv_rating = "0"
		
		# This is the download ID for the subtitle.
		download_id = re.search('[a-z0-9]{32}',td.parent.parent.attrs[1][1]).group(0)
		
		# Find the language of the subtitle extracting it from a image name,
		# and convert it to the OpenSubtitles format.	
		ltv_lang = re.findall("images/flag_([^.]*).gif",span.findAll('td')[4].contents[0].attrs[0][1])
		if ltv_lang: ltv_lang = ltv_lang[0]
		if ltv_lang == "br": ltv_lang = "pb"
		if ltv_lang == "us": ltv_lang = "en"
		
		# Compares the parsed and the LTV season number, then compares the retrieved titles from LTV
		# to those parsed or snatched by this service.
		# Each language is appended to a unique sequence.
		tvshow = CleanLTVTitle(tvshow)
		if int(ltv_season) == int(season): 
			SubtitleResult = { "title" : ltv_original_title, "filename" : release,"language_name" : lang1, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_lang+".gif" } 
			if re.findall("^%s" % (tvshow),ltv_original_title) or comparetitle(ltv_title,tvshow) or comparetitle(ltv_original_title,original_tvshow):
				if ltv_lang == ltv_flag1: sub1.append( SubtitleResult )
				if ltv_lang == ltv_flag2: sub2.append( SubtitleResult )
				if ltv_lang == ltv_flag3: sub3.append( SubtitleResult )
				log( __name__ ,u" Matched!\nTVShow[%s], Original TVShow[%s]\nLTV TVShow[%s], LTV Original TVShow[%s]\nRelease[%s], Season[%s], ID[%s], Language[%s], Rating[%s]" % (tvshow, original_tvshow, ltv_title, ltv_original_title, release, ltv_season, download_id, ltv_lang, ltv_rating))
			else:
				reResult = re.findall("[Ss][0-9]+[Ee]([0-9]+)",release)
				if reResult: LTVEpisode = re.sub("^0","",reResult[0])
				else: LTVEpisode = 0
				if int(LTVEpisode) == int(episode):
					PartialSubtitles.append( SubtitleResult )
				log( __name__ ,u" Mismatched.\nTVShow[%s], Original TVShow[%s]\nLTV TVShow[%s], LTV Original TVShow[%s]\nRelease[%s], Season[%s], ID[%s], Language[%s], Rating[%s]" % (tvshow, original_tvshow, ltv_title, ltv_original_title, release, ltv_season, download_id, ltv_lang, ltv_rating))
		else: log( __name__ ,u" Seasons mismatched. Season[%s], LTV Season[%s]." % (season, ltv_season))
		
	# Append all three language sequences.
	subtitles.extend(sub1)
	subtitles.extend(sub2)
	subtitles.extend(sub3)
	if not len(subtitles): subtitles.extend(PartialSubtitles)
	return subtitles

def chomp(s):
	s = re.sub("[ ]{2,20}"," ",s)
	a = re.compile("(\r|\n|^ | $|\'|\"|,|;|[(]|[)])")
	b = re.compile("(\t|-|:|\/)")
	s = b.sub(" ",s)
	s = re.sub("[ ]{2,20}"," ",s)
	s = a.sub("",s)
	return s
	
def CleanLTVTitle(s):
	s = Uconvert(s)
	s = re.sub("[(]?[0-9]{4}[)]?$","",s)
	s = chomp(s)
	s = s.title()
	return s

	
def shiftarticle(s):
	for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
		x = '^' + art + ' '
		y = ', ' + art
		if re.search(x, s):
			return re.sub(x, '', s) + y
	return s

def unshiftarticle(s):
	for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
		x = ', ' + art + '$'
		y = art + ' '
		if re.search(x, s):
			return y + re.sub(x, '', s)
	return s

def noarticle(s):
	for art in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ]:
		x = '^' + art + ' '
		if re.search(x, s):
			return re.sub(x, '', s)
	return s

def notag(s):
	return re.sub('<([^>]*)>', '', s)

def compareyear(a, b):
	if int(b) == 0:
		return 1
	if abs(int(a) - int(b)) <= YEAR_MAX_ERROR:
		return 1
	else:
		return 0

def comparetitle(a, b):
	if (a == b) or (noarticle(a) == noarticle(b)) or (a == noarticle(b)) or (noarticle(a) == b) or (a == shiftarticle(b)) or (shiftarticle(a) == b):
		return 1
	else:
#		print "[%s] != [%s]" % (a,b)
		return 0
		

def to_unicode_or_bust(
         obj, encoding='iso-8859-1'):
     if isinstance(obj, basestring):
         if not isinstance(obj, unicode):
             obj = unicode(obj, encoding)
     return obj	 

def substitute_entity(match):
	ent = match.group(3)
	if match.group(1) == "#":
		# decoding by number
		if match.group(2) == '':
			# number is in decimal
			return unichr(int(ent))
		elif match.group(2) == 'x':
			# number is in hex
			return unichr(int('0x'+ent, 16))
	else:
		# they were using a name
		cp = n2cp.get(ent)
		if cp: return unichr(cp)
		else: return match.group()

def decode_htmlentities(string):
	entity_re = re.compile(r'&(#?)(x?)(\w+);')
	return entity_re.subn(substitute_entity, string)[0]

# This function tries to decode the string to Unicode, then tries to decode
# all HTML entities, anf finally normalize the string and convert it to ASCII.
def Uconvert(obj):
	try:
		obj = to_unicode_or_bust(obj)
		obj = decode_htmlentities(obj)
		obj = unicodedata.normalize('NFKD', obj).encode('ascii','ignore')
		return obj
	except:return obj
