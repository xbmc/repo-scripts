# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 1.0.0

import xbmc, xbmcgui
import cookielib, urllib2, urllib, sys, re, os, webbrowser, time, unicodedata
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from htmlentitydefs import name2codepoint as n2cp

base_url = "http://legendas.tv"
sub_ext = "srt,aas,ssa,sub,smi"
debug_pretext = "[Legendas.TV]:"
YEAR_MAX_ERROR = 1

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
	cookie = LegendasLogin()
	if len(tvshow) > 0:
		subtitles =  LegendasTVSeries(tvshow, year, season, episode, lang1, lang2, lang3 )
	else:
		subtitles =  LegendasTVMovies(file_original_path, title, year, lang1, lang2, lang3 )
	return subtitles, cookie, ""

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	# Parse the cookie to LegendasLogin and install the url opener
	LegendasLogin(session_id)
	
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
	xbmc.executebuiltin("XBMC.Extract(" + fname + "," + tmp_sub_dir +")")
	time.sleep(2)
	legendas_tmp = []
	for root, dirs, files in os.walk(tmp_sub_dir, topdown=False):
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
		subtitle = dialog.browse(1, 'XBMC', 'files', '', False, False, 'special://temp/sub_tmp/')
		if subtitle == "special://temp/sub_tmp/": subtitle = ""
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
		username = __settings__.getSetting( "LTVuser" )
		password = __settings__.getSetting( "LTVpass" )
		login_data = urllib.urlencode({'txtLogin':username,'txtSenha':password})
		request = urllib2.Request(base_url+'/login_verificar.php',login_data)
		response = urllib2.urlopen(request).read()
		if response.__contains__('Dados incorretos'):
			xbmc.output(u"%s Login Failed. Check your data at the addon configuration." % (debug_pretext), level=xbmc.LOGDEBUG )
			xbmc.executebuiltin("Notification(Legendas.TV,%s,10000])"%( _( 756 ).encode('utf-8') ))
		else:
			xbmc.output(u"%s Succesfully logged in." % (debug_pretext), level=xbmc.LOGDEBUG )
	return cj

def LegendasTVMovies(file_original_path, title, year, lang1, lang2, lang3 ):

	# Initiating variables and languages.
	lang1, ltv_flag1, langid1, lang2, ltv_flag2, langid2, lang3, ltv_flag3, langid3 = LegendasLanguage(lang1,lang2,lang3)
	tipo = "2"
	legenda_id = 0
	subtitles = []
	sub1 = []
	sub2 = []
	sub3 = []
	
	# Try to get the original movie name from the XBMC database, 
	# and if not available, set it to the parsed title.
	original_title = re.findall("<[^>]*>([^<]*)</[^>]*>",xbmc.executehttpapi("QueryVideoDatabase(select c16 from movie where movie.c00 = '"+xbmc.Player().getVideoInfoTag().getTitle()+"')"))
	if not original_title or not year: original_title = title
	else:
		original_title = Uconvert(original_title[0])
		xbmc.output(u"%s Original Title[%s]" % (debug_pretext, original_title), level=xbmc.LOGDEBUG )

	# Encodes the first search string using the original movie title,
	# and download it.
	search_string = chomp(original_title)
	if len(search_string) < 3: search_string = search_string + year
	search_dict = {'txtLegenda':search_string,'selTipo':tipo,'int_idioma':'99'}
	search_data = urllib.urlencode(search_dict)
	request = urllib2.Request(base_url+'/index.php?opcao=buscarlegenda',search_data)
	response = to_unicode_or_bust(urllib2.urlopen(request).read())

	# If no subtitles with the original name are found, try the parsed title.
	if response.__contains__('Nenhuma legenda foi encontrada') and original_title != title:
		xbmc.output(u"%s No subtitles found using the original title, using title instead." % (debug_pretext), level=xbmc.LOGDEBUG )
		search_string = chomp(title)
		search_dict = {'txtLegenda':search_string,'selTipo':tipo,'int_idioma':'99'}
		search_data = urllib.urlencode(search_dict)
		request = urllib2.Request(base_url+'/index.php?opcao=buscarlegenda',search_data)
		response = to_unicode_or_bust(urllib2.urlopen(request).read())

	# Retrieves the number of pages.
	pages = re.findall("<a class=\"paginacao\" href=",response)
	if pages: pages = len(pages)+1
	else: pages = 1
	xbmc.output(u"%s Found [%s] pages." % (debug_pretext, pages), level=xbmc.LOGDEBUG )

	# Download all pages content.
	for x in range(pages):
		if x:
			xbmc.output(u"%s Downloading page [%s]" % (debug_pretext, str(x+1)), level=xbmc.LOGDEBUG )
			html = urllib2.urlopen(base_url+'/index.php?opcao=buscarlegenda&pagina='+str(x+1)).read()
			response = response + to_unicode_or_bust(html)
	xbmc.output(u"%s Results downloaded." % (debug_pretext), level=xbmc.LOGDEBUG )
	
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
			ltv_title = Uconvert(td.contents[2])
			ltv_original_title = Uconvert(td.contents[0].contents[0])
			
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
			if comparetitle(ltv_original_title, original_title) or comparetitle(ltv_title, title) or comparetitle(ltv_original_title, title) or comparetitle(original_title, ltv_title) or re.findall('^'+original_title+"[/s|$]",ltv_original_title) or re.findall(original_title+'$',ltv_original_title) or re.findall('^'+title,ltv_title) or re.findall(title+'$',ltv_title):
				if ltv_lang == ltv_flag1: sub1.append( { "title" : ltv_title, "filename" : release,"language_name" : lang1, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag1+".gif" } )
				if ltv_lang == ltv_flag2: sub2.append( { "title" : ltv_title, "filename" : release,"language_name" : lang2, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag2+".gif" } )
				if ltv_lang == ltv_flag3: sub3.append( { "title" : ltv_title, "filename" : release,"language_name" : lang3, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag3+".gif" } )
				xbmc.output(u"%s Matched!\nTitle[%s], Original Title[%s]\nLTV Title[%s], LTV Original Title[%s]\nID[%s], Release[%s], Language[%s], Rating[%s]" % (debug_pretext, title, original_title, ltv_title, ltv_original_title, download_id, release, ltv_lang, ltv_rating), level=xbmc.LOGDEBUG )
			else: xbmc.output(u"%s Discarted.\nTitle[%s], Original Title[%s]\nLTV Title[%s], LTV Original Title[%s]\nID[%s], Release[%s], Language[%s], Rating[%s]" % (debug_pretext, title, original_title, ltv_title, ltv_original_title, download_id, release, ltv_lang, ltv_rating), level=xbmc.LOGDEBUG )

	# Append all three language sequences.
	subtitles.extend(sub1)
	subtitles.extend(sub2)
	subtitles.extend(sub3)
	return subtitles

def LegendasTVSeries(tvshow, year, season, episode, lang1, lang2, lang3 ):

	# Initiating variables and languages.
	lang1, ltv_flag1, langid1, lang2, ltv_flag2, langid2, lang3, ltv_flag3, langid3 = LegendasLanguage(lang1,lang2,lang3)
	tipo = "1"
	idioma = "1"
	subtitles = []
	sub1 = []
	sub2 = []
	sub3 = []
	
	# Searching XBMC Database for TheTVDb id of the tvshow and retreaving the original tvshow title from TheTVDB.
	# This tries to avoid mismatches when using translated tvshow names.
	tvshow_id = re.sub("</?[^>]*>","",xbmc.executehttpapi("QueryVideoDatabase(select c12 from tvshow where c00 = '"+xbmc.getInfoLabel("VideoPlayer.TVshowtitle")+"')"))
	if tvshow_id: original_tvshow = Uconvert(BeautifulStoneSoup(urllib2.urlopen("http://www.thetvdb.com/data/series/"+tvshow_id+"/").read()).data.series.seriesname.string)
	else: original_tvshow = 0
	print original_tvshow

	# Formating the season to double digit format
	if int(season) < 10: ss = "0"+season
	else: ss = season
	if int(episode) < 10: ee = "0"+episode
	else: ee = episode

	# Setting up the search string; the original tvshow name is preferable.
	# If the tvshow name lenght is less than 3 characters, append the year to the search.
	if original_tvshow: search_string = chomp(original_tvshow) + " " +"S"+ss+"E"+ee
	else: search_string = chomp(tvshow) + " " +"S"+ss+"E"+ee
	if len(search_string) < 3: search_string = search_string +" "+ year
	print "Searching "+search_string
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
		try:
			ltv_title = re.findall("(.*) - [0-9]*",Uconvert(td.contents[2]))[0]
			ltv_original_title, ltv_season = re.findall("(.*) - ([0-9]*)",Uconvert(td.contents[0].contents[0]))[0]
			release = td.parent.parent.find('span',{'class':'brls'}).contents[0]
			if not ltv_season: continue
		except:
			continue
		
		# Retrieves the rating of the subtitle, and set it to '0' id not available.
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
		if int(ltv_season) == int(season): 
			if re.findall('^%s' % (tvshow),ltv_original_title) or comparetitle(ltv_title,tvshow) or comparetitle(ltv_original_title,original_tvshow):
				if ltv_lang == ltv_flag1: sub1.append( { "title" : ltv_original_title, "filename" : release,"language_name" : lang1, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag1+".gif" } )
				if ltv_lang == ltv_flag2: sub2.append( { "title" : ltv_original_title, "filename" : release,"language_name" : lang2, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag2+".gif" } )
				if ltv_lang == ltv_flag3: sub3.append( { "title" : ltv_original_title, "filename" : release,"language_name" : lang3, "ID" : download_id, "sync" : False, "rating" : ltv_rating, "language_flag": "flags/"+ltv_flag3+".gif" } )
				xbmc.output(u"%s Matched!\nTVShow[%s], Original TVShow[%s]\nLTV TVShow[%s], LTV Original TVShow[%s]\nRelease[%s], Season[%s], ID[%s], Language[%s], Rating[%s]" % (debug_pretext, tvshow, original_tvshow, ltv_title, ltv_original_title, release, ltv_season, download_id, ltv_lang, ltv_rating), level=xbmc.LOGDEBUG )
			else: xbmc.output(u"%s Discarted.\nTVShow[%s], Original TVShow[%s]\nLTV TVShow[%s], LTV Original TVShow[%s]\nRelease[%s], Season[%s], ID[%s], Language[%s], Rating[%s]" % (debug_pretext, tvshow, original_tvshow, ltv_title, ltv_original_title, release, ltv_season, download_id, ltv_lang, ltv_rating), level=xbmc.LOGDEBUG )
		else: xbmc.output(u"%s Season do not match. Season[%s], LTV Season[%s]." % (debug_pretext), level=xbmc.LOGDEBUG )
		
	# Append all three language sequences.
	subtitles.extend(sub1)
	subtitles.extend(sub2)
	subtitles.extend(sub3)
	return subtitles

def chomp(s):
	a = re.compile("(\r|\n|^ | $|\'|\"|,|;)")
	b = re.compile("(\t|-|:|[(]|[)]|\/)")
	s = a.sub("",s)
	s = b.sub(" ",s)
	s = re.sub("[ ]{2,20}"," ",s)
	return s
	
def CleanLTVTitle(s):
	a = re.compile("(\r|\n|^ | $|\'|\"|,|;)")
	b = re.compile("(\t|-|:|[(]|[)]|\/)")
	s = re.sub("[(]?[0-9]{4}[)]?$","",s)
	s = a.sub("",s)
	s = b.sub(" ",s)
	s = re.sub("[ ]{2,20}"," ",s)
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
	a = CleanLTVTitle(a.title())
	b = CleanLTVTitle(b.title())
	if (a == b) or (noarticle(a) == noarticle(b)) or (a == noarticle(b)) or (noarticle(a) == b) or (a == shiftarticle(b)) or (shiftarticle(a) == b):
		return 1
	else:
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
