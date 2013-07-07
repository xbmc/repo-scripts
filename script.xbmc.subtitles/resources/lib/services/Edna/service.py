# -*- coding: UTF-8 -*-

import sys
import os
import xbmc,xbmcgui

import urllib2,urllib,re
from utilities import log, hashFile, languageTranslate

_ = sys.modules[ "__main__" ].__language__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	log(__name__,"Starting search by TV Show")
	if (tvshow == None or tvshow == ''):
		log(__name__,"No TVShow name, stop")
		return [],"",""

	cli = EdnaClient()
	found_tv_shows = cli.search_show(tvshow)
	if (found_tv_shows.__len__() == 0):
		log(__name__,"TVShow not found, stop")
		return [],"",""
	elif (found_tv_shows.__len__() == 1):
		log(__name__,"One TVShow found, auto select")
		tvshow_url = found_tv_shows[0]['url']
	else:
		log(__name__,"More TVShows found, user dialog for select")
		menu_dialog = []
		for found_tv_show in found_tv_shows:
			menu_dialog.append(found_tv_show['title'])
		dialog = xbmcgui.Dialog()
		found_tv_show_id = dialog.select(_( 610 ), menu_dialog)
		if (found_tv_show_id == -1):
			return [],"",""
		tvshow_url = found_tv_shows[found_tv_show_id]['url']
	log(__name__,"Selected show URL: " + tvshow_url)

	found_season_subtitles = cli.list_show_subtitles(tvshow_url,season)

	episode_subtitle_list = None

	for found_season_subtitle in found_season_subtitles:
		if (found_season_subtitle['episode'] == int(episode) and found_season_subtitle['season'] == int(season)):
			episode_subtitle_list = found_season_subtitle
			break

	if episode_subtitle_list == None:
		return [], "", ""

	result_subtitles = []
	for episode_subtitle in episode_subtitle_list['versions']:

		result_subtitles.append({
			'filename': episode_subtitle_list['full_title'],
			'link': cli.server_url + episode_subtitle['link'],
			'lang': lng_short2long(episode_subtitle['lang']),
			'rating': "0",
			'sync': False,
			'language_flag': 'flags/' + lng_short2flag(episode_subtitle['lang']) + '.gif',
			'language_name': lng_short2long(episode_subtitle['lang']),
		})

	log(__name__,result_subtitles)

	# Standard output -
	# subtitles list
	# session id (e.g a cookie string, passed on to download_subtitles),
	# message to print back to the user
	# return subtitlesList, "", msg
	return result_subtitles, "", ""

def download_subtitles (subtitles_list, pos, extract_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	selected_subtitles = subtitles_list[pos]

	log(__name__,'Downloading subtitles')
	res = urllib.urlopen(selected_subtitles['link'])
	subtitles_filename = re.search("Content\-Disposition: attachment; filename=\"(.+?)\"",str(res.info())).group(1)
	log(__name__,'Filename: %s' % subtitles_filename)
	# subs are in .zip or .rar
	subtitles_format = re.search("\.(\w+?)$", subtitles_filename, re.IGNORECASE).group(1)
	log(__name__,"Subs in %s" % subtitles_format)

	store_path_file = open(extract_subs,'wb')
	store_path_file.write(res.read())
	store_path_file.close()

	# Standard output -
	# True if the file is packed as zip: addon will automatically unpack it.
	# language of subtitles,
	# Name of subtitles file if not packed (or if we unpacked it ourselves)
	# return False, language, subs_file
	return True, selected_subtitles['lang'], subtitles_format

def lng_short2long(lang):
	if lang == 'CZ': return 'Czech'
	if lang == 'SK': return 'Slovak'
	return 'English'

def lng_long2short(lang):
	if lang == 'Czech': return 'CZ'
	if lang == 'Slovak': return 'SK'
	return 'EN'

def lng_short2flag(lang):
	return languageTranslate(lng_short2long(lang),0,2)


class EdnaClient(object):

	def __init__(self):
		self.server_url = "http://www.edna.cz"

	def search_show(self,title):
		enc_title = urllib.urlencode({ "q" : title})
		res = urllib.urlopen(self.server_url + "/vyhledavani/?" + enc_title)
		shows = []
		if re.search("/vyhledavani/\?q=",res.geturl()):
			log(__name__,"Parsing search result")
			res_body = re.search("<ul class=\"list serieslist\">(.+?)</ul>",res.read(),re.IGNORECASE | re.DOTALL)
			if res_body:
				for row in re.findall("<li>(.+?)</li>", res_body.group(1), re.IGNORECASE | re.DOTALL):
					show = {}
					show_reg_exp = re.compile("<h3><a href=\"(.+?)\">(.+?)</a></h3>",re.IGNORECASE | re.DOTALL)
					show['url'], show['title'] = re.search(show_reg_exp, row).groups()
					shows.append(show)
		else:
			log(__name__,"Parsing redirect to show URL")
			show = {}
			show['url'] = re.search(self.server_url + "(.+)",res.geturl()).group(1)
			show['title'] = title
			shows.append(show)
		return shows

	def list_show_subtitles(self, show_url, show_series):
		res = urllib.urlopen(self.server_url + show_url + "titulky/?season=" + show_series)
		if not res.getcode() == 200: return []
		subtitles = []
		html_subtitle_table = re.search("<table class=\"episodes\">.+<tbody>(.+?)</tbody>.+</table>",res.read(), re.IGNORECASE | re.DOTALL)
		if html_subtitle_table == None: return []
		for html_episode in re.findall("<tr>(.+?)</tr>", html_subtitle_table.group(1), re.IGNORECASE | re.DOTALL):
			subtitle = {}
			show_title_with_numbers = re.sub("<[^<]+?>", "",re.search("<h3>(.+?)</h3>", html_episode).group(1))
			subtitle['full_title'] = show_title_with_numbers
			show_title_with_numbers = re.search("S([0-9]+)E([0-9]+): (.+)",show_title_with_numbers).groups()
			subtitle['season'] = int(show_title_with_numbers[0])
			subtitle['episode'] = int(show_title_with_numbers[1])
			subtitle['title'] = show_title_with_numbers[2]
			subtitle['versions'] = []
			for subs_url, subs_lang in re.findall("a href=\"(.+?)\" class=\"flag\".+?><i class=\"flag\-.+?\">(cz|sk)</i>",html_episode):
				subtitle_version = {}
				subtitle_version['link'] = re.sub("/titulky/#content","/titulky/?direct=1",subs_url)
				subtitle_version['lang'] = subs_lang.upper()
				subtitle['versions'].append(subtitle_version)
			if subtitle['versions'].__len__() > 0: subtitles.append(subtitle)
		return subtitles
