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

	cli = SerialZoneClient()
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
			if (found_tv_show['orig_title'] == found_tv_show['title']):
				menu_dialog.append(found_tv_show['title'] + " - " + found_tv_show['years'])
			else:
				menu_dialog.append(found_tv_show['title'] + " / " + found_tv_show['orig_title'] + " - " + found_tv_show['years'])
		dialog = xbmcgui.Dialog()
		found_tv_show_id = dialog.select(_( 610 ), menu_dialog)
		if (found_tv_show_id == -1):
			return [],"",""
		tvshow_url = found_tv_shows[found_tv_show_id]['url']
	log(__name__,"Selected show URL: " + tvshow_url)

	try:
		file_size, file_hash = hashFile(file_original_path, rar)
	except:
		file_size, file_hash = -1, None
	log(__name__, "File size: " + str(file_size))

	found_season_subtitles = cli.list_show_subtitles(tvshow_url,season)

	episode_subtitle_list = None

	for found_season_subtitle in found_season_subtitles:
		if (found_season_subtitle['episode'] == int(episode) and found_season_subtitle['season'] == int(season)):
			episode_subtitle_list = found_season_subtitle
			break

	if episode_subtitle_list == None:
		return [], "", ""

	max_down_count = 0
	for episode_subtitle in episode_subtitle_list['versions']:
		if max_down_count < episode_subtitle['down_count']:
			max_down_count = episode_subtitle['down_count']

	log(__name__,"Max download count: " + str(max_down_count))

	result_subtitles = []
	for episode_subtitle in episode_subtitle_list['versions']:

		print_out_filename = episode_subtitle['rip'] + " by " + episode_subtitle['author']
		if not episode_subtitle['notes'] == None:
			print_out_filename = print_out_filename + "(" + episode_subtitle['notes'] + ")"

		result_subtitles.append({ 
			'filename': print_out_filename,
			'link': episode_subtitle['link'],
			'lang': lng_short2long(episode_subtitle['lang']),
 			'rating': str(episode_subtitle['down_count']*10/max_down_count),
			'sync': (episode_subtitle['file_size'] == file_size),
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

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	selected_subtitles = subtitles_list[pos]

	log(__name__, selected_subtitles)

	log(__name__,'Downloading subtitle zip')
	res = urllib.urlopen(selected_subtitles['link'])
	subtitles_data = res.read()

	log(__name__,'Saving to file %s' % zip_subs)
	zip_file = open(zip_subs,'wb')
	zip_file.write(subtitles_data)
	zip_file.close()

	# Standard output -
	# True if the file is packed as zip: addon will automatically unpack it.
	# language of subtitles,
	# Name of subtitles file if not packed (or if we unpacked it ourselves)
	# return False, language, subs_file
	return True, selected_subtitles['lang'],""

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


class SerialZoneClient(object):

	def __init__(self):
		self.server_url = "http://www.serialzone.cz"

	def search_show(self,title):
		enc_title = urllib.urlencode({ "co" : title, "kde" : "serialy" })
		res = urllib.urlopen(self.server_url + "/hledani/?" + enc_title)
		shows = []
		try:
			res_body = re.search("<div class=\"column4 wd2 fl-left\">(.+?)<div class=\"cl12px fl-left\"></div>",res.read(), re.IGNORECASE | re.DOTALL).group(1)
		except:
			res_body = res.read()

		for row in re.findall('<li>(.+?)</li>', res_body, re.IGNORECASE | re.DOTALL):
			if re.search("\/serial\/", row):
				show = {}
				show_reg_exp = re.compile("<a href=\"(.+?)\">(.+?) <span class=\"vysilani\">\((.+?)\)</span></a><br />(.+?)$")
				show['url'], show['title'], show['years'], show['orig_title'] = re.search(show_reg_exp, row).groups()
				show['years'] = show['years'].replace("&#8211;", "-")
				shows.append(show)
		return shows

	def list_show_subtitles(self, show_url, show_series):
		res = urllib.urlopen(show_url + "titulky/" + show_series + "-rada/")
		if not res.getcode() == 200: return []
		subtitles = []
		for html_episode in re.findall('<div .+? class=\"sub\-line .+?>(.+?)</div></div></div></div>',res.read(), re.IGNORECASE | re.DOTALL):
			subtitle = {}
			for html_subtitle in html_episode.split("<div class=\"sb1\">"):
				show_numbers = re.search("<div class=\"sub-nr\">(.+?)</div>",html_subtitle)
				if not show_numbers == None:
					subtitle['season'], subtitle['episode'] = re.search("([0-9]+)x([0-9]+)", show_numbers.group(1)).groups()
					subtitle['season'] = int(subtitle['season'])
					subtitle['episode'] = int(subtitle['episode'])
					subtitle['versions'] = []
				else:
					subtitle_version = {}
					subtitle_version['lang'] = re.search("<div class=\"sub-info-menu sb-lang\">(.+?)</div>", html_subtitle).group(1)
					subtitle_version['link'] = re.search("<a href=\"(.+?)\" .+? class=\"sub-info-menu sb-down\">",html_subtitle).group(1)
					subtitle_version['author'] = re.sub("<[^<]+?>", "",(re.search("<div class=\"sub-info-auth\">(.+?)</div>",html_subtitle).group(1)))
					subtitle_version['rip'] = re.search("<div class=\"sil\">Verze / Rip:</div><div class=\"sid\"><b>(.+?)</b>",html_subtitle).group(1)
					try:
						subtitle_version['notes'] = re.search("<div class=\"sil\">Poznámka:</div><div class=\"sid\">(.+?)</div>",html_subtitle).group(1)
					except:
						subtitle_version['notes'] = None
					subtitle_version['down_count'] = int(re.search("<div class=\"sil\">Počet stažení:</div><div class=\"sid2\">(.+?)x</div>",html_subtitle).group(1))
					try:
						subtitle_version['file_size'] = re.search("<span class=\"fl-right\" title=\".+\">\((.+?) b\)</span>",html_subtitle).group(1)
						subtitle_version['file_size'] = int(subtitle_version['file_size'].replace(" ",""))
					except:
						subtitle_version['file_size'] = -1
					subtitle['versions'].append(subtitle_version)
			# print subtitle
			subtitles.append(subtitle)
		return subtitles
