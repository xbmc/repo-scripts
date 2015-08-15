#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


import random
import xbmcgui
import xbmc
import xbmcaddon
import time
import datetime
import sys
import os
import ast
import json

plf              = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", 		"params": {"directory": "special://profile/playlists/video/", "media": "video"}}
clear_playlist   = {"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",				"params": {"playlistid": 1}}
add_this_ep      = {'jsonrpc': '2.0','id': 1, "method": 'Playlist.Add', 				"params": {'item' : {'episodeid' : 'placeholder' }, 'playlistid' : 1}}
add_this_movie   = {'jsonrpc': '2.0','id': 1, "method": 'Playlist.Add', 				"params": {'item' : {'movieid' : 'placeholder' }, 'playlistid' : 1}}
get_movies       = {"jsonrpc": "2.0",'id': 1, "method": "VideoLibrary.GetMovies", 	"params": { "filter": {"field": "playcount", "operator": "is", "value": "0"}, "properties" : ["playcount", "title"] }}
get_moviesw      = {"jsonrpc": "2.0",'id': 1, "method": "VideoLibrary.GetMovies", 	"params": { "filter": {"field": "playcount", "operator": "is", "value": "1"}, "properties" : ["playcount", "title"] }}
get_moviesa      = {"jsonrpc": "2.0",'id': 1, "method": "VideoLibrary.GetMovies", 	"params": { "properties" : ["playcount", "title"] }}
get_legacy		 = {"jsonrpc": "2.0","id": 1, "method": "VideoLibrary.GetTVShows",  "params": { "properties" : ["mpaa","genre"] }}
mark_as_watched  = '{"jsonrpc": "2.0","id": 1, "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %i, "playcount" : %i}}'

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
scriptName       = __addon__.getAddonInfo('Name')

WINDOW           = xbmcgui.Window(10000)

__resource__     =  os.path.join(scriptPath, 'resources')
sys.path.append(__resource__)

start_time       = time.time()
base_time        = time.time()
language         = xbmc.getInfoLabel('System.Language')

primary_function = __setting__('primary_function')
populate_by_d    = __setting__('populate_by_d')
select_pl        = __setting__('select_pl')
default_playlist = __setting__('users_spl')

sort_by          = int(float(__setting__('sort_by')))
length           = int(float(__setting__('length')))
window_length    = int(float(__setting__('window_length')))

if __setting__('skinorno') == 'true':
	skin = 1
	__addon__.setSetting('skinorno','1')
elif __setting__('skinorno') == 'false' or __setting__('skinorno') == '32073':
	skin = 0
	__addon__.setSetting('skinorno','1')
else:
	skin = int(float(__setting__('skinorno')))

movieweight      = float(__setting__('movieweight'))

filterYN         = True if __setting__('filterYN') == 'true' else False
multipleshows    = True if __setting__('multipleshows') == 'true' else False
premieres        = True if __setting__('premieres') == 'true' else False
keep_logs        = True if __setting__('logging') == 'true' else False
limitshows       = True if __setting__('limitshows') == 'true' else False
movies           = True if __setting__('movies') == 'true' else False
moviesw          = True if __setting__('moviesw') == 'true' else False
noshow           = True if __setting__('noshow') == 'true' else False
excl_randos      = True if __setting__('excl_randos') == 'true' else False
sort_reverse     = True if __setting__('sort_reverse') == 'true' else False
start_partials   = True if __setting__('start_partials') == 'true' else False
skin_return      = True if __setting__('skin_return') == 'true' else False
stay_puft        = True
play_now         = False
open_addon_window      = True


try:
	spec_shows = ast.literal_eval(__setting__('selection'))
except:
	spec_shows = []

try:
	randos = ast.literal_eval(WINDOW.getProperty("LazyTV.randos"))
except:
	randos = []


# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass

def lang(id):
	san = __addon__.getLocalizedString(id).encode( 'utf-8', 'ignore' )
	return san 
	
def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__ + 'default', total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time


log('language = ' + str(language))


def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()


def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		#print result
		#result = unicode(result, 'utf-8', errors='ignore')
		#log('result = ' + str(result))
		if ret:
			return json.loads(result)['result']
		else:
			return json.loads(result)
	except:
		return {}


def playlist_selection_window():
	''' Purpose: launch Select Window populated with smart playlists '''
	log('playlist_window_start')

	playlist_files = json_query(plf, True)['files']

	if playlist_files != None:

		plist_files   = dict((x['label'],x['file']) for x in playlist_files)

		playlist_list =  plist_files.keys()

		playlist_list.sort()

		log('playlist_window_called')

		inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)

		log('playlist_window_selectionmade', reset = True)

		return plist_files[playlist_list[inputchoice]]
	else:
		return 'empty'


def day_conv(date_string):
	op_format = '%Y-%m-%d %H:%M:%S'
	Y, M, D, h, mn, s, ux, uy, uz        = time.strptime(date_string, op_format)
	lw_max    = datetime.datetime(Y, M, D, h ,mn, s)
	date_num  = time.mktime(lw_max.timetuple())
	return date_num

def order_name(raw_name):

	name = raw_name.lower()

	if language in ['English', 'Russian','Polish','Turkish'] or 'English' in language:
		if name.startswith('the '):
			new_name = name[4:]
		else:
			new_name = name

	elif language == 'Spanish':
		variants = ['la ','los ','las ','el ','lo ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language == 'Dutch':
		variants = ['de ','het ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language in ['Danish','Swedish']:
		variants = ['de ','det ','den ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language in ['German', 'Afrikaans']:
		variants = ['die ','der ','den ','das ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language == 'French':
		variants = ['les ','la ','le ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	else:
		new_name = name

	return new_name

def day_calc(date_string, todate, output):
	op_format = '%Y-%m-%d %H:%M:%S'
	lw = time.strptime(date_string, op_format)
	if output == 'diff':
		lw_date    = datetime.date(lw[0],lw[1],lw[2])
		day_string = str((todate - lw_date).days) + " days)"
		return day_string
	else:
		lw_max   = datetime.datetime(lw[0],lw[1],lw[2],lw[3],lw[4],lw[5])
		date_num = time.mktime(lw_max.timetuple())
		return date_num


def next_show_engine(showid, epid=[],eps = [], Season = 'null', Episode = 'null'):
	log('nextep_engine_start', showid)

	if showid in randos:
		newod = eps.remove(epid)
		if not eps:
			return 'null', ['null','null', 'null','null']
		random.shuffle(newod)
		next_ep = newod[0]

	else:
		if not eps:
			return 'null', ['null','null', 'null','null']
		try:
			next_ep = eps[1]
		except:
			return 'null', ['null','null', 'null','null']
			
		newod = eps[1:]

	#get details of next_ep
	ep_details_query = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["season","episode"],"episodeid": next_ep},"id": "1"}
	epd = json_query(ep_details_query, True)

	if 'episodedetails' in epd and epd['episodedetails']:
		return next_ep, [epd['episodedetails']['season'],epd['episodedetails']['episode'],newod,next_ep]

	else:
		return 'null', ['null','null', 'null','null']

	log('nextep_engine_End', showid)


def get_TVshows():
	log('get_TVshows_started', reset = True)
	log('sort by = ' + str(sort_by))

	#get the most recent info on inProgress TV shows, cross-check it with what is currently stored
	query          = '{"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort": {"order": "descending", "method": "lastplayed"} },"id": "1" }'

	nepl_retrieved = xbmc.executeJSONRPC(query)
	nepl_retrieved = unicode(nepl_retrieved, 'utf-8', errors='ignore')
	nepl_retrieved = json.loads(nepl_retrieved)

	log('get_TVshows_querycomplete')

	if 'result' in nepl_retrieved and 'tvshows' in nepl_retrieved["result"] and nepl_retrieved['result']['tvshows']:
		nepl_retrieved = nepl_retrieved['result']['tvshows']
		for x in nepl_retrieved:
			log(str(x))
	else:
		log('no unwatched TV shows in library')
		log(nepl_retrieved)
		nepl_retrieved = {}

	nepl_from_service = WINDOW.getProperty("LazyTV.nepl")

	if nepl_from_service:
		p = ast.literal_eval(nepl_from_service)
		nepl_stored = [int(x) for x in p]
	else:
		dialog.ok('LazyTV',lang(32115),lang(32116))
		sys.exit()

	nepl = sort_shows(nepl_retrieved, nepl_stored)

	stored_data = [[x[0],x[1],WINDOW.getProperty("%s.%s.EpisodeID"  % ('LazyTV', x[1]))] for x in nepl]

	log('get_TVshows_End')

	return stored_data


def sort_shows(nepl_retrieved, nepl_stored):

	if sort_by == 0:
		# SORT BY show name
		log('sort by name')
		nepl_inter  = [[x['label'], day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in nepl_retrieved if x['tvshowid'] in nepl_stored]
		nepl_inter.sort(key= lambda x: order_name(x[0]), reverse = sort_reverse )
		nepl        = [x[1:] for x in nepl_inter]

	elif sort_by == 2:
		# sort by Unwatched Episodes
		log('sort by unwatched count')
		nepl_inter  = [[ int(WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', x['tvshowid'])))
								, day_conv(x['lastplayed']) if x['lastplayed'] else 0
								, x['tvshowid']]
							for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		nepl_inter.sort(reverse = sort_reverse == False)
		nepl        = [x[1:] for x in nepl_inter]

	elif sort_by == 3:
		# sort by Watched Episodes
		log('sort by watched count')
		nepl_inter  = [[ int(WINDOW.getProperty("%s.%s.CountWatchedEps" % ('LazyTV', x['tvshowid'])))
							, day_conv(x['lastplayed']) if x['lastplayed'] else 0
							, x['tvshowid']]
						for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		nepl_inter.sort(reverse = sort_reverse == False)

		nepl        = [x[1:] for x in nepl_inter]


	elif sort_by == 4:
		# sort by Season
		log('sort by season')
		nepl_inter  = [[int(WINDOW.getProperty("%s.%s.Season" % ('LazyTV', x['tvshowid'])))
						, day_conv(x['lastplayed']) if x['lastplayed'] else 0
						, x['tvshowid']]
					for x in nepl_retrieved if x['tvshowid'] in nepl_stored]
		
		nepl_inter.sort(reverse = sort_reverse == False)

		nepl        = [x[1:] for x in nepl_inter]

	else:
		# SORT BY LAST WATCHED
		log('sort by last watched')
		nepl_inter        = [[day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		# this sorting section needs to ignore everything that has never been played
		nepl_nev = [x for x in nepl_inter if x[0] == 0]
		nepl_w = [x for x in nepl_inter if x[0] != 0]

		nepl_w.sort(reverse = sort_reverse == False)

		nepl = nepl_w + nepl_nev


	return nepl


def process_stored(population):

	stored_data = get_TVshows()

	log('process_stored', reset = True)

	if 'playlist' in population:
		extracted_showlist = convert_pl_to_showlist(population['playlist'])
	elif 'usersel' in population:
		extracted_showlist = population['usersel']
	else:
		extracted_showlist = False

	if extracted_showlist:
		stored_data_filtered  = [x for x in stored_data if x[1] in extracted_showlist]
	else:
		stored_data_filtered = stored_data

	log('process_stored_End')

	return stored_data_filtered


def convert_pl_to_showlist(pop):
	# derive filtered_showids from smart playlist
	filename = os.path.split(pop)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = clean_path
	playlist_contents = json_query(plf, True)

	if 'files' not in playlist_contents:
		gracefail('files not in playlist contents')
	else:
		if not playlist_contents['files']:
			gracefail('playlist contents empty')
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log(filtered_showids, 'showids in playlist')
				if not filtered_showids:
					gracefail('no tv shows in playlist')

	#returns the list of all and filtered shows and episodes
	return filtered_showids


def random_playlist(population):
	global movies
	global movieweight

	#get the showids and such from the playlist
	stored_data_filtered = process_stored(population)

	log('random_playlist_started',reset = True)

	#clear the existing playlist
	json_query(clear_playlist, False)

	added_ep_dict   = {}
	count           = 0
	movie_list      = []


	if movies or moviesw:

		if movies and moviesw:
			mov = json_query(get_moviesa, True)
		elif movies:
			mov = json_query(get_movies, True)
		elif moviesw:
			mov = json_query(get_moviesw, True)

		movies = True

		if 'movies' in mov and mov['movies']:
			movie_list = [x['movieid'] for x in mov['movies']]
			log('all movies = ' + str(movie_list))
			if not movie_list:
				movies = False
			else:
				random.shuffle(movie_list)
		else:
			movies = False

	storecount = len(stored_data_filtered)
	moviecount = len(movie_list)

	if noshow:
		movieweight = 0.0
		stored_data_filtered = []

	if movieweight != 0.0:
		movieint = min(max(int(round(storecount * movieweight,0)), 1), moviecount)
	else:
		movieint = moviecount

	if movies:
		movie_list = movie_list[:movieint]
		log('truncated movie list = ' + str(movie_list))

	candidate_list = ['t' + str(x[1]) for x in stored_data_filtered] + ['m' + str(x) for x in movie_list]
	random.shuffle(candidate_list)

	watch_partial_now = False

	if start_partials:

		if candidate_list:
			red_candy = [int(x[1:]) for x in candidate_list if x[0] == 't']
		else:
			red_candy = []

		lst = []

		for showid in red_candy:

			if WINDOW.getProperty("%s.%s.Resume" % ('LazyTV',showid)) == 'true':
				temp_ep = WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',showid))
				if temp_ep:
					lst.append({"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": int(temp_ep)},"id": "1"})

		lwlist = []

		if lst:

			xbmc_request = json.dumps(lst)
			result = xbmc.executeJSONRPC(xbmc_request)

			if result:
				reslist = ast.literal_eval(result)
				for res in reslist:
					if 'result' in res:
						if 'episodedetails' in res['result']:
							lwlist.append((res['result']['episodedetails']['lastplayed'],res['result']['episodedetails']['tvshowid']))

			lwlist.sort(reverse=True)

		if lwlist:

			log(lwlist, label="lwlist = ")

			R = candidate_list.index('t' + str(lwlist[0][1]))

			watch_partial_now = True

			log(R,label="R = ")




	while count < length and candidate_list: 		#while the list isnt filled, and all shows arent abandoned or movies added
		log('candidate list = ' + str(candidate_list))
		multi = False

		if start_partials and watch_partial_now:
			watch_partial_now = False
		else:
			R = random.randint(0, len(candidate_list) -1 )	#get random number

		log('R = ' + str(R))

		curr_candi = candidate_list[R][1:]
		candi_type = candidate_list[R][:1]

		if candi_type == 't':
			log('tvadd attempt')

			if curr_candi in added_ep_dict.keys():
				log(str(curr_candi) + ' in added_shows')
				if multipleshows:		#check added_ep list if multiples allowed
					multi = True
					tmp_episode_id, tmp_details = next_show_engine(showid=curr_candi,epid=added_ep_dict[curr_candi][3],eps=added_ep_dict[curr_candi][2],Season=added_ep_dict[curr_candi][0],Episode=added_ep_dict[curr_candi][1])
					if tmp_episode_id == 'null':
						tg = 't' + str(curr_candi)
						if tg in candidate_list:
							candidate_list.remove('t' + str(curr_candi))
							log(str(curr_candi) + ' added to abandonded shows (no next show)')
						continue
				else:
					continue
			else:
				log(str(curr_candi) + ' not in added_showss')
				tmp_episode_id = int(WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',curr_candi)))
				if not multipleshows:		#check added_ep list if multiples allowed, if not then abandon the show
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (no multi)')


			if not premieres:
				if WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV',curr_candi)) == 's01e01':	#if desired, ignore s01e01
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (premieres)')
					continue

			#add episode to playlist
			if tmp_episode_id:
				add_this_ep['params']['item']['episodeid'] = int(tmp_episode_id)
				json_query(add_this_ep, False)
				log('episode added = ' + str(tmp_episode_id))
			else:
				tg = 't' + str(curr_candi)
				if tg in candidate_list:
					candidate_list.remove('t' + str(curr_candi))
				continue

			#add episode to added episode dictionary
			if not multi:
				if multipleshows:
					if curr_candi in randos:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi))) + ast.literal_eval(WINDOW.getProperty("%s.%s.offlist" % ('LazyTV',curr_candi)))
					else:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi)))
					added_ep_dict[curr_candi] = [WINDOW.getProperty("%s.%s.Season" % ('LazyTV', curr_candi)), WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', curr_candi)),eps_list,WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', curr_candi))]
				else:
					added_ep_dict[curr_candi] = ''
			else:
				added_ep_dict[curr_candi] = [tmp_details[0],tmp_details[1],tmp_details[2],tmp_details[3]]

		elif candi_type == 'm':
			#add movie to playlist
			log('movieadd')
			add_this_movie['params']['item']['movieid'] = int(curr_candi)
			json_query(add_this_movie, False)
			candidate_list.remove('m' + str(curr_candi))
		else:
			count = 99999

		count += 1

	WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'true')		# notifies the service that a playlist is running
	WINDOW.setProperty("LazyTV.rando_shuffle", 'true')						# notifies the service to re-randomise the randos

	xbmc.Player().play(xbmc.PlayList(1))
	#xbmc.executebuiltin('ActivateWindow(MyVideoPlaylist)')
	log('random_playlist_End')


def create_next_episode_list(population):

	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist
	log('create_nextep_list')

	global stay_puft
	global play_now
	global open_addon_window

	stored_data_filtered = process_stored(population)

	if excl_randos:
		stored_data_filtered = [x for x in stored_data_filtered if x[1] not in randos]

	skins = {1: "script-lazytv-main.xml", 2: "script-lazytv-BigScreenList.xml"}

	xmlfile = skins.get(skin, "DialogSelect.xml")

	list_window = yGUI(xmlfile, scriptPath, 'Default', data=stored_data_filtered)

	window_returner = myPlayer(parent=list_window)

	while stay_puft and not xbmc.abortRequested:

		if open_addon_window:
			log('Opening addon window, existing window %s' % xbmc.getInfoLabel('Window.Property(xmlfile)'))

			# this loop is required as the window opening covers any YesNo dialog, including that put up by the service
			# prompting to watch the next episode
			count = 0
			while count < 5 or xbmc.getInfoLabel('Window.Property(xmlfile)') == 'DialogYesNo.xml':
				xbmc.sleep(100)
				count += 1
			
			open_addon_window = False

			list_window.doModal()

		da_show = list_window.selected_show

		if da_show != 'null' and play_now:
			log('da_show not null, or play_now')

			play_now = False
			# this fix clears the playlist, adds the episode to the playlist, and then starts the playlist
			# it is needed because .strms will not start if using the executeJSONRPC method

			WINDOW.setProperty("%s.playlist_running"    % ('LazyTV'), 'listview')

			json_query(clear_playlist, False)

			try:
				for ep in da_show:
					add_this_ep['params']['item']['episodeid'] = int(ep)
					json_query(add_this_ep, False)
			except:
				add_this_ep['params']['item']['episodeid'] = int(da_show)
				json_query(add_this_ep, False)

			xbmc.sleep(50)
			window_returner.play(xbmc.PlayList(1))
			xbmc.executebuiltin('ActivateWindow(12005)')
			da_show = 'null'

			WINDOW.setProperty("LazyTV.rando_shuffle", 'true')

		if not skin_return:
			stay_puft = False

		xbmc.sleep(100)

	del list_window
	del window_returner

	WINDOW.setProperty("LazyTV.rando_shuffle", 'true')                      # notifies the service to re-randomise the randos


class myPlayer(xbmc.Player):

	def __init__(self, parent, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.dawindow = parent


	def onPlayBackStarted(self):
		log('Playbackstarted',reset=True)
		self.dawindow.close()

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):
		log('Playbackended', reset =True)
		self.dawindow.data_refresh()


class yGUI(xbmcgui.WindowXMLDialog):

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, data=[]):
		self.data = data
		self.selected_show = 'null'
		yGUI.context_order = 'null'
		yGUI.multiselect = False
		self.load_items = True
		WINDOW.setProperty('runninglist', '') 

	def onInit(self):
		if self.load_items:
			self.load_items = False
			log('window_init', reset = True)

			if skin == 0: 
				self.ok = self.getControl(5)
				self.ok.setLabel(lang(32105))

				self.hdg = self.getControl(1)
				self.hdg.setLabel('LazyTV')
				self.hdg.setVisible(True)

				self.ctrl6failed = False

				try:
					self.name_list = self.getControl(6)
					self.x = self.getControl(3)
					self.x.setVisible(False)
					self.ok.controlRight(self.name_list)

				except:
					self.ctrl6failed = True  #for some reason control3 doesnt work for me, so this work around tries control6
					self.close()             #and exits if it fails, CTRL6FAILED then triggers a dialog.select instead '''

			else:
				self.name_list = self.getControl(655)

			self.now = time.time()

			self.count = 0

			log('this is the data the window is using = ' + str(self.data))

			for i, show in enumerate(self.data):

				if self.count == 1000 or (limitshows == True and i == window_length):
					break

				self.pctplyd  = WINDOW.getProperty("%s.%s.PercentPlayed" % ('LazyTV', show[1]))

				if show[0] == 0:
					self.lw_time = lang(32112)
				else:
					self.gap = round((self.now - show[0]) / 86400.0, 1)
					if self.gap == 1.0:
						self.lw_time = ' '.join([str(self.gap),lang(32113)])
					else:
						self.lw_time = ' '.join([str(self.gap),lang(32114)])

				if self.pctplyd == '0%' and skin == 0:
					self.pct = ''
				elif self.pctplyd == '0%':
					self.pct = self.pctplyd
				else:
					self.pct = self.pctplyd + ', '

				self.label2 = self.pct if skin != 0 else self.pct + self.lw_time

				self.poster = WINDOW.getProperty("%s.%s.Art(tvshow.poster)" % ('LazyTV', show[1]))
				self.thumb  = WINDOW.getProperty("%s.%s.Art(thumb)" % ('LazyTV', show[1]))
				self.eptitle = WINDOW.getProperty("%s.%s.title" % ('LazyTV', show[1]))
				self.plot = WINDOW.getProperty("%s.%s.Plot" % ('LazyTV', show[1]))
				self.season = WINDOW.getProperty("%s.%s.Season" % ('LazyTV', show[1]))
				self.episode = WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', show[1]))
				self.EpisodeID = WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', show[1]))
				self.file = WINDOW.getProperty("%s.%s.file" % ('LazyTV', show[1]))

				if skin != 0:
					self.title  = WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show[1]))
					self.fanart = WINDOW.getProperty("%s.%s.Art(tvshow.fanart)" % ('LazyTV', show[1]))
					self.numwatched = WINDOW.getProperty("%s.%s.CountWatchedEps" % ('LazyTV', show[1]))
					self.numondeck = WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', show[1]))
					try:
						self.numskipped = str(int(WINDOW.getProperty("%s.%s.CountUnwatchedEps" % ('LazyTV', 
							show[1]))) - int(WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', show[1]))))
					except:
						self.numskipped = '0'
					self.tmp = xbmcgui.ListItem(label=self.title, label2=self.eptitle, thumbnailImage = self.poster)
					self.tmp.setProperty("Fanart_Image", self.fanart)
					self.tmp.setProperty("Backup_Image", self.thumb)
					self.tmp.setProperty("numwatched", self.numwatched)
					self.tmp.setProperty("numondeck", self.numondeck)
					self.tmp.setProperty("numskipped", self.numskipped)
					self.tmp.setProperty("lastwatched", self.lw_time)
					self.tmp.setProperty("percentplayed", self.pctplyd)
					self.tmp.setProperty("watched",'false')
					self.tmp.setProperty('ID', str(show[1]))

				else:
					self.title  = ''.join([WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show[1])),' ', WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', show[1]))])
					self.tmp = xbmcgui.ListItem(label=self.title, label2=self.label2, thumbnailImage = self.poster)

				self.tmp.setProperty("file",self.file)
				self.tmp.setProperty("EpisodeID",self.EpisodeID)

				# self.tmp.setProperty("season", self.season)
				# self.tmp.setProperty("episode", self.episode)
				# self.tmp.setProperty("plot", self.plot)

				self.tmp.setInfo('video', {'season': self.season, "episode": self.episode,'plot': self.plot, 'title':self.eptitle})

				self.tmp.setLabel(self.title)
				self.tmp.setIconImage(self.poster)

				self.name_list.addItem(self.tmp)
				self.count += 1

			#self.ok.controlRight(self.name_list)
			self.setFocus(self.name_list)

			log('window_init_End')


	def onAction(self, action):
		contextagogone = False

		actionID = action.getId()
		
		if (actionID in (10, 92)):
			log('closing due to action')
			self.load_show_id = -1
			global stay_puft
			stay_puft = False
			self.close()

		elif actionID in [117] and not contextagogone:
			contextagogone = True
			log(actionID)
			log('context menu via action')
	
			self.pos    = self.name_list.getSelectedPosition()

			myContext = contextwindow('script-lazytv-contextwindow.xml', scriptPath, 'Default')

			myContext.doModal()

			if myContext.contextoption == 110:
				'''toggle'''
				log('multiselect toggled')
				self.toggle_multiselect()

			elif myContext.contextoption == 120:
				'''playsel'''
				log('play selection')
				self.play_selection()

			elif myContext.contextoption == 130:
				'''playfrom'''
				log('play from here')
				self.play_from_here()
			
			elif myContext.contextoption == 140:
				'''export'''
				log('export selection')
				self.export_selection()
			
			elif myContext.contextoption == 150:
				'''markwatched'''
				log('toggle watched')
				self.toggle_watched()
			
			elif myContext.contextoption == 160:
				'''ignore'''
				pass
			
			elif myContext.contextoption == 170:
				'''update library'''
				self.update_library()
			
			elif myContext.contextoption == 180:
				'''refresh'''
				self.refresh()

			log('context button: ' + str(myContext.contextoption))

			del myContext


	def onClick(self, controlID):

		contextagogone = False

		if controlID == 5:
			self.load_show_id = -1
			global stay_puft
			stay_puft = False
			self.close()

		else:
			self.pos    = self.name_list.getSelectedPosition()

			if yGUI.multiselect == False:
				# self.playid = self.data[self.pos][2]
				self.playitem = self.name_list.getListItem(self.pos)
				self.playid = self.playitem.getProperty('EpisodeID')

				self.selected_show = int(self.playid)
				log('setting epid = ' + str(self.selected_show))
				global play_now
				play_now = True
				self.close()

			else:
				selection = self.name_list.getSelectedItem()
				if selection.isSelected():
					selection.select(False)
					log(str(self.pos) + ' toggled off')
				else:
					selection.select(True)
					log(str(self.pos) + ' toggled on')


	def update_library(self):

		xbmc.executebuiltin('UpdateLibrary(video)') 


	def toggle_multiselect(self):
		if yGUI.multiselect:
			yGUI.multiselect = False

			for itm in range(self.name_list.size()):
				self.name_list.getListItem(itm).select(False)

		else:
			yGUI.multiselect = True


	def play_selection(self):
		self.selected_show = []
		self.pos    = self.name_list.getSelectedPosition()
		for itm in range(self.name_list.size()):
			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				# self.selected_show.append(self.data[itm][2])
				playitem = self.name_list.getListItem(itm)
				self.selected_show.append(playitem.getProperty('EpisodeID'))
		global play_now
		play_now = True
		self.close()        


	def play_from_here(self):
		self.pos    = self.name_list.getSelectedPosition()
		self.selected_show = []
		for itm in range(self.pos,self.name_list.size()):

			playitem = self.name_list.getListItem(itm)
			self.selected_show.append(playitem.getProperty('EpisodeID'))

			# self.selected_show.append(self.data[itm][2])
		global play_now
		play_now = True
		self.close()            


	def toggle_watched(self):
		log('watch toggling')
		self.pos    = self.name_list.getSelectedPosition()
		q_batch = []
		count = 0
		for itm in range(self.name_list.size()):
			count += 1
			if itm == self.pos: 
				EpID = self.name_list.getListItem(itm).getProperty('EpisodeID')
				log(EpID)
				if EpID:
					if skin != 0:
						if self.name_list.getListItem(itm).getProperty('watched') == 'false':
							log('toggling from unwatched to watched')
							self.name_list.getListItem(itm).setProperty("watched",'true')

					tmp = mark_as_watched % (int(EpID),1)
					q_batch.append(ast.literal_eval(tmp))
		log(q_batch)
		json_query(q_batch, False)


	def export_selection(self):
		self.pos    = self.name_list.getSelectedPosition()
		log(self.pos, label="exporting position")
		self.export_list = ''
		for itm in range(self.name_list.size()):
			log(self.name_list.getListItem(itm).isSelected())
			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				filename = self.name_list.getListItem(itm).getProperty('file')
				if self.export_list:
					self.export_list = ''.join([self.export_list,':-exporter-:',filename])
				else:
					self.export_list = filename

		log(self.export_list, label='export list sent from LazyTV')
		script = os.path.join(__resource__,'episode_exporter.py')
		xbmc.executebuiltin('RunScript(%s,%s)' % (script,self.export_list)  ) 
		self.selected_show = []


	def refresh(self):
		log('refresh called')
		global open_addon_window
		open_addon_window = True
		self.close()


	def data_refresh(self):

		log('attempting data refresh')
		
		global open_addon_window
		open_addon_window = True

		item_count = self.name_list.size()

		for item_position in range(item_count):

			try:
				list_item_show = self.name_list.getListItem(item_position)
			except ValueError:
				log('Value %s out of range of show list control' % item_position)
				continue

			show_id = list_item_show.getProperty('ID')

			pctplyd  = WINDOW.getProperty("%s.%s.PercentPlayed" % ('LazyTV', show_id))

			if pctplyd == '0%' and skin == 0:
				pct = ''
			elif pctplyd == '0%':
				pct = pctplyd
			else:
				pct = pctplyd + ', '

			poster 		= WINDOW.getProperty("%s.%s.Art(tvshow.poster)" 	% ('LazyTV', show_id))
			thumb  		= WINDOW.getProperty("%s.%s.Art(thumb)" 			% ('LazyTV', show_id))
			eptitle 	= WINDOW.getProperty("%s.%s.title" 					% ('LazyTV', show_id))
			plot 		= WINDOW.getProperty("%s.%s.Plot"					% ('LazyTV', show_id))
			season 		= WINDOW.getProperty("%s.%s.Season" 				% ('LazyTV', show_id))
			episode 	= WINDOW.getProperty("%s.%s.Episode" 				% ('LazyTV', show_id))
			EpisodeID 	= WINDOW.getProperty("%s.%s.EpisodeID" 				% ('LazyTV', show_id))
			filename 	= WINDOW.getProperty("%s.%s.file" 					% ('LazyTV', show_id))

			if skin != 0:
				title  		= WINDOW.getProperty("%s.%s.TVshowTitle" 		% ('LazyTV', show_id))
				fanart 		= WINDOW.getProperty("%s.%s.Art(tvshow.fanart)" % ('LazyTV', show_id))
				numwatched 	= WINDOW.getProperty("%s.%s.CountWatchedEps" 	% ('LazyTV', show_id))
				numondeck 	= WINDOW.getProperty("%s.%s.CountonDeckEps" 	% ('LazyTV', show_id))
				
				try:
					numskipped = str(int(WINDOW.getProperty("%s.%s.CountUnwatchedEps" 	% ('LazyTV', 
						show_id))) - int(WINDOW.getProperty("%s.%s.CountonDeckEps" 		% ('LazyTV', show_id))))
				except:
					numskipped = '0'

				list_item_show.setLabel(title)
				list_item_show.setLabel2(eptitle)
				list_item_show.setThumbnailImage(poster)

				list_item_show.setProperty("Fanart_Image"	, fanart)
				list_item_show.setProperty("Backup_Image"	, thumb)
				list_item_show.setProperty("numwatched"		, numwatched)
				list_item_show.setProperty("numondeck"		, numondeck)
				list_item_show.setProperty("numskipped"		, numskipped)
				list_item_show.setProperty("percentplayed"	, pctplyd)
				list_item_show.setProperty("watched"		, 'false')

			else:
				title  = ''.join([WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show_id)),' ',
																WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', show_id))])
				
				list_item_show.setLabel(title)
				list_item_show.setLabel2(eptitle)
				list_item_show.setThumbnailImage(poster)

			list_item_show.setProperty("file",filename)
			list_item_show.setProperty("EpisodeID",EpisodeID)

			list_item_show.setInfo('video', {'season': season, "episode": episode,'plot': plot, 'title': eptitle})

			list_item_show.setLabel(title)
			list_item_show.setIconImage(poster)




class contextwindow(xbmcgui.WindowXMLDialog):

	def onInit(self):
		self.contextoption = '' 

		log('init multiselect ' + str(yGUI.multiselect))
		if yGUI.multiselect:
			self.getControl(110).setLabel(lang(32200))
			self.getControl(120).setLabel(lang(32202))
			self.getControl(140).setLabel(lang(32203))
		else:
			self.getControl(110).setLabel(lang(32201))
			self.getControl(120).setLabel(lang(32204))
			self.getControl(140).setLabel(lang(32205))

		self.getControl(130).setLabel(lang(32206))
		self.getControl(150).setLabel(lang(32207)) # go to Show in Library?
		#self.getControl(160).setLabel('Ignore Show')    # open show info?
		self.getControl(170).setLabel(lang(32208))
		self.getControl(180).setLabel(lang(32209))

		self.setFocus(self.getControl(110))


	def onClick(self, controlID):

		self.contextoption = controlID

		if controlID == 110:
			if self.getControl(110).getLabel() == lang(32200):
				self.getControl(110).setLabel(lang(32201))
				xbmc.sleep(500)
			else:
				self.getControl(110).setLabel(lang(32200))
				xbmc.sleep(500)

		self.close()


def main_entry():
	log('Main_entry')

	if filterYN:

		if populate_by_d == '1':

			if select_pl == '0':
				selected_pl = playlist_selection_window()
				population = {'playlist': selected_pl}

			else:
				#get setting for default_playlist
				if not default_playlist:
					population = {'none':''}
				else:
					population = {'playlist': default_playlist}
		else:
			population = {'usersel':spec_shows}
	else:
		population = {'none':''}


	if primary_function == '2':

		#assume this is selection
		choice = dialog.yesno('LazyTV', lang(32100),'',lang(32101), lang(32102),lang(32103))
		if choice < 0:
			sys.exit()

	elif primary_function == '1':
		choice = 1

	else:
		choice = 0


	if choice == 1:
		random_playlist(population)
	elif choice == 0:
		create_next_episode_list(population)


def convert_previous_settings(ignore):
	filter_genre         = True if __setting__('filter_genre') == 'true' else False
	filter_length         = True if __setting__('filter_length') == 'true' else False
	filter_rating         = True if __setting__('filter_rating') == 'true' else False
	filter_show         = True if __setting__('filter_show') == 'true' else False

	# convert the ignore list into a dict
	jkl = {}
	all_showids = []
	for ig in ignore.split("|"):
		if ig:
			k, v = ig.split(":-:")
			if k in jkl:
				jkl[k].append(v)
			else:
				jkl[k] = [v]
	if jkl:
		# create a list of permissable TV shows
		show_data = json_query(get_legacy, True)

		if 'tvshows' in show_data and show_data['tvshows']:
			show_data = show_data['tvshows']
	
			all_showids = [x['tvshowid'] for x in show_data]

			for show in show_data:

				if filter_genre and "genre" in jkl:
					for gen in jkl['genre']:
						if gen in show['genre'] and show['tvshowid'] in all_showids:
							all_showids.remove(show['tvshowid'])

				if filter_rating and "rating" in jkl:
					if show['mpaa'] in jkl['rating'] and show['tvshowid'] in all_showids:
						all_showids.remove(show['tvshowid'])

				if filter_show and "name" in jkl:

					if str(show['tvshowid']) in jkl['name'] and show['tvshowid'] in all_showids:
						all_showids.remove(show['tvshowid'])
	if all_showids:
		spec_shows = [int(x) for x in all_showids]

		# save the new list to settings
		__addon__.setSetting('selection',str(spec_shows))
		# set the filterYN to be Y
		__addon__.setSetting('filterYN','true')
		filterYN = True


	# reset IGNORE to be null
	__addon__.setSetting('IGNORE','')

# this check is to ensure that the Ignore list from the previous addon is respected and replaced in the new version
ignore = __setting__('IGNORE')

if ignore:
	convert_previous_settings(ignore)

if __name__ == "__main__":
	log('entered LazyTV')

	if WINDOW.getProperty('LazyTV_service_running') == 'starting':
		dialog.ok("LazyTV",lang(32115), lang(32116))
		sys.exit()


	# call to the service wait 500 for response
	WINDOW.setProperty('LazyTV_service_running', 'marco')
	service_lives = 'marco'
	count = 0

	while service_lives == 'marco':
		count += 1
		if count > 500:
			service_lives = False
			break
		xbmc.sleep(10)
		service_lives = WINDOW.getProperty('LazyTV_service_running')
		log('checking, ' + service_lives)
	else:
		service_lives = True

	if not service_lives:
		log('service not running')

		ans = dialog.yesno('LazyTV',lang(32106),lang(32107))

		if ans == 1:
			# this will always happen after the first install. The addon service is not auto started after install.
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":false}}')
			xbmc.sleep(1000)
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":true}}')

	else:

		service_version = ast.literal_eval(WINDOW.getProperty("LazyTV.Version"))

		if __addonversion__ != service_version and __addonid__ == "script.lazytv":
			log('versions do not match')

			# the service version may show as lower than the addon version
			# this may happen if the addon is updated while the service is running.
			# due to a 'bug', and because the service extension point is after the script one,
			# the service cannot be stopped to allow an update of the running script.
			# this restart should allow that code to update.
			dialog.ok('LazyTV',lang(32108))
			sys.exit()

		if __addonversion__ < service_version and __addonid__ != "script.lazytv":
			log('clone out of date')
			clone_upd = dialog.yesno('LazyTV',lang(32110),lang(32111))

			# this section is to determine if the clone needs to be up-dated with the new version
			# it checks the clone's version against the services version.
			if clone_upd == 1:
				service_path = WINDOW.getProperty("LazyTV.ServicePath")
				update_script = os.path.join(scriptPath,'resources','update_clone.py')
				xbmc.executebuiltin('RunScript(%s,%s,%s,%s,%s)' % (update_script,service_path, scriptPath, __addonid__, scriptName))
				sys.exit()

		main_entry()
		log('exited LazyTV')




  