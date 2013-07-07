# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, requests
from utilities import log

_ = sys.modules[ "__main__" ].__language__

main_url = "http://ondertitel.com/"
debug_pretext = ""
releases_types   = ['web-dl', '480p', '720p', '1080p', 'h264', 'x264', 'xvid', 'aac20', 'hdtv', 'dvdrip', 'ac3', 'bluray', 'dd51', 'divx', 'proper', 'repack', 'pdtv', 'rerip', 'dts']

FETCH_NORMAL = 0
FETCH_COOKIE = 1
FETCH_SUBTITLE = 2

#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
<a href="/ondertitels/info/Dead-Man-Down/62137.html" style="color: #161616;" class="recent" id="<div class='div_ondertit_afbeeling'><img src='http://ondertitel.com/movie_images/ondertitelcom_84723_902.jpg' alt='' height='178'><div class='div_ondertit_afbeeling_p'>Poster: <strong>demario</strong></div></div>">Dead Man Down</a></strong> <img src="/images/nederlandse_vlag.jpg" height="11">  
					</div>
				</div>
				<div class="div_ondertitel_r_pos">
					<a href="http://www.imdb.com/title/tt2101341/?ref_=sr_1" target="_blank"><img src="/images/imdb_logo.gif" border="0"></a> <img src="/images/good_rate_small.png" height="17"> <font class="font_color_g">1</font> 
				</div>
				<br clear="both">

				<div class="div_ondertitel_vers">
					<i class="i_font">Dead.Man.Down.2013.DVDRip.XVID.AC3.HQ.Hive-CM8 1 CD</i>
"""
subtitle_pattern = "<a href=\"(/ondertitels/info/.+?)\".+?<i class=\"i_font\">(.+?)<\/i>"
# group(1) = link, group(2) = filename


# downloadlink pattern example:
"""
<a href="/getdownload.php?id=45071&userfile=94 Avatar (2009) PROPER TS XviD-MAXSPEED.zip"><b>Download</b></a>
"""
downloadlink_pattern = "<a href=\"/(getdownload\.php\?id=\d{1,10}&userfile=[^\n\r\t]*\.\w{3})\"><b>Download</b></a>"
# group(1) = downloadlink

#====================================================================================================================
# Functions
#====================================================================================================================
def getallsubs(content, title, moviefile, subtitles_list):
	for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
		link = matches.group(1)
		filename = matches.group(2)
		log( __name__ ,"%s Subtitles found: %s (link=%s)" % (debug_pretext, filename, link))
		if isexactmatch(filename, moviefile):
			sync = True
			rating = 10
		else:
			rating = getrating(filename, moviefile)
			sync = False
		subtitles_list.append({'rating': str(rating), 'no_files': 1, 'movie':  title, 'filename': filename, 'sync': sync, 'link': link, 'language_flag': 'flags/nl.gif', 'language_name': 'Dutch'})

def getrating(subsfile, videofile):
	rating = 0
	videofile = string.replace(string.lower("".join(string.split(videofile, '.')[:-1])), '.', '')
	subsfile = string.replace(string.lower(subsfile), '.', '')
	for release_type in releases_types:
		if (release_type in videofile) and (release_type in subsfile):
			rating += 1
	if string.split(videofile, '-')[-1] == string.split(subsfile, '-')[-1]:
		rating += 1
	if rating > 0:
		rating = rating * 2 - 1
		if rating > 9:
			rating = 9
	return rating

def isexactmatch(subsfile, videofile):
	videofile = string.replace(string.replace(string.lower("".join(string.split(videofile, '.')[:-1])), ' ', '.'), '.', '')
	subsfile = string.replace(string.lower(subsfile), '.', '')
	log( __name__ ," comparing subtitle file with videofile (sync?):\nsubtitlesfile  = '%s'\nvideofile      = '%s'" % (subsfile, videofile) )
	if string.find(subsfile, videofile) > -1:
		log( __name__ ," found matching subtitle file, marking it as 'sync': '%s'" % (subsfile) )
		return True
	else:
		return False

def getdownloadlink(content):
	link = None
	i = 0
	for matches in re.finditer(downloadlink_pattern, content, re.IGNORECASE | re.DOTALL):
		link = matches.group(1)
		i = i + 1
	if i == 1:
		return link
	else:
		return None

def geturl(url, action=FETCH_NORMAL, cookiedata=''):
	log( __name__ ,"%s Getting url:%s" % (debug_pretext, url))
	try:
		if action == FETCH_SUBTITLE:
			r = requests.get(url, cookies=cookiedata)
			return r.content
		elif action == FETCH_COOKIE:
			r = requests.get(url)
			return (r.text, r)
		else:
			r = requests.get(url)
			return r.text
	except:
		log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
		return None
		
def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
	subtitles_list = []
	msg = ""
	log( __name__ ,"%s Title = %s" % (debug_pretext, title))
	if len(tvshow) == 0: # only process movies
		url = main_url + "zoeken.php?type=1&trefwoord=" + urllib.quote_plus(title)
		Dutch = False
		if (string.lower(lang1) == "dutch") or (string.lower(lang2) == "dutch") or (string.lower(lang3) == "dutch"):
			Dutch = True
			content = geturl(url, FETCH_NORMAL)
			if content is not None:
				log( __name__ ,"%s Getting subs ..." % debug_pretext)
				moviefile = os.path.basename(file_original_path)
				getallsubs(content, title, moviefile, subtitles_list)
				subtitles_list.sort(key=lambda x: [ x['sync'], x['rating']], reverse = True)
		else:
			log( __name__ ,"%s Dutch language is not selected" % (debug_pretext))
			msg = "Won't work, Ondertitel is only for Dutch subtitles."
	else:
		log( __name__ ,"%s Tv show detected: %s" % (debug_pretext, tvshow))
		msg = "Won't work, Ondertitel is only for movies."
	return subtitles_list, "", msg #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	url = main_url + subtitles_list[pos][ "link" ]
	local_tmp_file = zip_subs
	content, cookie = geturl(url, FETCH_COOKIE)
	downloadlink = getdownloadlink(content)
	if downloadlink is not None:
		try:
			url = main_url + downloadlink
			url = string.replace(url," ","+")
			log( __name__ ,"%s Fetching subtitles using url %s - and cookie: %s" % (debug_pretext, url, cookie.cookies))
			content = geturl(url, FETCH_SUBTITLE, cookie.cookies)
			if content is not None:
				log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
				local_file_handle = open(local_tmp_file, "w" + "b")
				local_file_handle.write(content)
				local_file_handle.close()
		except:
			log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
		log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
		language = subtitles_list[pos][ "language_name" ]
		return True, language, "" #standard output
