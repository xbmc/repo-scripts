from resources.lazy_lib import *
import xbmcgui
import sys

#sys.stdout = open('C:\\Temp\\test.txt', 'w')

_addon_ = xbmcaddon.Addon("script.lazytv")	
lang = _addon_.getLocalizedString

def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()


def backfill():

	user_options = [lang(32085),lang(32086),lang(32106)]

	inputchoice = xbmcgui.Dialog().select(lang(32084), user_options) 

	#retrieve all TV Shows
	show_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode"]}, 
	"id": "allTVShows"}
	s = json_query(show_request, True)

	if 'tvshows' not in s:
		gracefail(lang(32201))
	else:
		shows = s['tvshows']


	#retrieve all TV episodes
	episode_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}
	e = json_query(episode_request, True)

	if 'episodes' not in e:
		gracefail(lang(32203))
	else:
		eps = e['episodes']

	all_shows = sorted(shows, key =  lambda shows: (shows['title']))

	tvshownames = [x['title'] for x in all_shows]
	ids_safe = [x['tvshowid'] for x in all_shows]
	ids = ids_safe

	if inputchoice == 2:
		ids = []
	elif inputchoice == 0:
		pass
	elif inputchoice == 1:
		ids = []
		new_inputchoice = xbmcgui.Dialog().select(lang(32087), tvshownames) 
		ids += [ids_safe[new_inputchoice]]

	if ids:
		for sid in ids:
			watched_eps = [x for x in eps if x['tvshowid'] == sid and x['playcount'] != 0]
			lpe = sorted(watched_eps, key =  lambda watched_eps: (watched_eps['season'], watched_eps['episode']), reverse=True)
			if lpe:
				last_played_ep = lpe[0]
				Season = last_played_ep['season']
				Episode = last_played_ep['episode']

				#uses the season and episode number to create a list of unwatched shows newer than the last watched one
				unplayed_eps = [x['episodeid'] for x in eps if ((x['season'] == Season and x['episode'] < Episode) or (x['season'] < Season)) and x['tvshowid'] == sid]

				for d in unplayed_eps:

					set_to_watched = {"jsonrpc": "2.0", 
					"method": "VideoLibrary.SetEpisodeDetails", 
					"params": {"episodeid" : d, "playcount" : 1},
					"id": 1}
					json_query(set_to_watched, False)