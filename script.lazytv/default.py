# declare file encoding
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

import random, xbmcgui, xbmcaddon
import os
from resources.lazy_lib import *

#Buggalo
bug_exists = False

try:

	_buggalo_ = xbmcaddon.Addon("script.module.buggalo")
	_bugversion_ = _buggalo_.getAddonInfo("version")

	bv = _bugversion_.split(".")
	if int(bv[0]) > 1 or (int(bv[0]) == 1 and int(bv[1]) > 1) or (int(bv[0]) == 1 and int(bv[1]) == 1 and int(bv[2]) > 3):
		import buggalo
		bug_exists = True

except:
	pass

#import sys
#sys.stdout = open('C:\\Temp\\test.txt', 'w')

_addon_ = xbmcaddon.Addon("script.lazytv")	
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString
dialog = xbmcgui.Dialog()

premieres = _setting_('premieres')
partial = _setting_('partial')
playlist_length = _setting_('length')
multiples = _setting_('multipleshows')
ignore_list = _setting_('IGNORE')
streams = _setting_('streams')
expartials = _setting_('expartials')
filter_show = _setting_('filter_show')
filter_genre = _setting_('filter_genre')
filter_length = _setting_('filter_length')
filter_rating = _setting_('filter_rating')
first_run = _setting_('first_run')
primary_function = _setting_('primary_function')
populate_by = _setting_('populate_by')
smart_pl = _setting_('default_spl')
sort_list_by = _setting_('sort_list_by')

IGNORE_SHOWS = proc_ig(ignore_list,'name') if filter_show == 'true' else []
IGNORE_GENRE = proc_ig(ignore_list,'genre') if filter_genre == 'true' else []
IGNORE_LENGTH = proc_ig(ignore_list,'length') if filter_length == 'true' else []
IGNORE_RATING = proc_ig(ignore_list,'rating') if filter_rating == 'true' else []
IGNORES = [IGNORE_SHOWS,IGNORE_GENRE,IGNORE_LENGTH,IGNORE_RATING]

#opens progress dialog
proglog = xbmcgui.DialogProgress()
proglog.create("LazyTV","Initializing...")
proglog.update(1, lang(30151))

def criteria_filter():
	#apply the custom filter to get the list of allowable TV shows and episodes

	#retrieve all TV Shows
	show_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode"]}, 
	"id": "allTVShows"}
	all_shows = json_query(show_request)['result']['tvshows']

	#filter the TV shows by custom criteria
	filtered_showids = [show['tvshowid'] for show in all_shows 
	if show['title'] not in IGNORES[0] 
	and bool(set(show['genre']) & set(IGNORES[1])) == False
	and show['mpaa'] not in IGNORES[3]
	and (show['watchedepisodes'] > 0 or premieres == 'true')
	and show['episode']>0]

	#retrieve all TV episodes
	episode_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}
	eps = json_query(episode_request)['result']['episodes']

	#Apply the show length filter and remove the episodes for shows not in the filtered show list
	filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids and x['runtime'] not in IGNORES[2]]
	filtered_eps_showids = [x['tvshowid'] for x in filtered_eps]
	filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]

	#return the list of all and filtered shows and episodes
	return filtered_eps, filtered_showids, all_shows, eps


def smart_playlist_filter(playlist):
	# derive filtered_eps, filtered_showids from smart playlist

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf = {"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "placeholder", "media": "video"}, "id": 1}
	plf['params']['directory'] = playlist
	playlist_contents = json_query(plf)['result']['files']
	filtered_showids = [x['id'] for x in playlist_contents]

	#retrieve all tv episodes and remove the episodes that are not in the filtered show lisy
	episode_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}
	eps = json_query(episode_request)['result']['episodes']
	filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids]

	#retrieves information on all tv shows
	show_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode"]}, 
	"id": "allTVShows"}
	all_shows = json_query(show_request)['result']['tvshows']

	#remove empty strings from the lists
	filtered_eps = filter(None, filtered_eps)
	filtered_showids = filter(None, filtered_showids)

	#returns the list of all and filtered shows and episodes
	return filtered_eps, filtered_showids, all_shows, eps


def populate_by_x():
	#populates the lists depending on the users selected playlist, or custom filter
	
	#updates progress dialog
	proglog.update(25, lang(30152))

	if populate_by == '1':
		if smart_pl == '':
			selected_pl = playlist_selection_window()
			if selected_pl == 'empty':
				filtered_eps, filtered_showids, all_shows, eps = criteria_filter()
			else:
				filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(selected_pl)
		else:
			filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(smart_pl)
	elif populate_by == '2':
		selected_pl = playlist_selection_window()
		if selected_pl == 'empty':
			filtered_eps, filtered_showids, all_shows, eps = criteria_filter()
		else:
			filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(selected_pl)
		filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(selected_pl)
	else:
		filtered_eps, filtered_showids, all_shows, eps = criteria_filter()

	#remove empty strings from the lists
	filtered_eps = filter(None, filtered_eps)
	filtered_showids = filter(None, filtered_showids)

	#returns the list of all and filtered shows and episodes
	proglog.update(50, lang(30153))
	return filtered_eps, filtered_showids, all_shows, eps


def create_playlist():
	#creates a random playlist of unwatched episodes

	partial_exists = False
	itera = 0
	cycle = 0
	_checked = False
	playlist_tally = {}

	#clears the playlist
	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'}) 

	#generates the show and episode lists
	filtered_eps, filtered_showids, all_shows, eps = populate_by_x()

	#updates progross dialog
	proglog.update(75, lang(30154))

	#Applies start with partial setting
	if partial == 'true':

		#generates a list of partially watched episodes
		partial_eps = [x for x in filtered_eps if x['resume']['position']>0]
		partial_eps = filter(None, partial_eps)

		if partial_eps:
			#identifies the most recently partially watched episode
			most_recent_partial = sorted(partial_eps, key = lambda partial_eps: (partial_eps['lastplayed']), reverse=True)[0]

			#adds the id, season and episode for the partial to a list
			playlist_tally[most_recent_partial['tvshowid']] = (most_recent_partial['season'],most_recent_partial['episode'])
			
			#removes the show from the show list if the user doesnt want more than one episode from each series
			if multiples == 'false':
				filtered_showids = [x for x in filtered_showids if x != most_recent_partial['tvshowid']]
			
			#adds the partial to the new playlist		
			json_query(dict_engine(most_recent_partial['file']))

			proglog.close()

			#starts the player
			player_start()

			#notifies the rest of the script that a partial has been set up
			partial_exists = True

			#jumps to resume point of the parial
			seek_percent = float(most_recent_partial['resume']['position'])/float(most_recent_partial['resume']['total'])*100.0
			seek = {'jsonrpc': '2.0','method': 'Player.Seek','params': {'playerid':1,'value':0.0}, 'id':1}
			seek['params']['value'] = seek_percent
			json_query(seek)

	#removes the shows with partial episodes as the next episode from the show list
	if expartials == 'true':
		partially_watched = [x['tvshowid'] for x in filtered_eps if x['resume']['position']>0]
		filtered_eps = [x for x in filtered_eps if x['tvshowid'] not in partially_watched]
		filtered_eps_showids = [show['tvshowid'] for show in filtered_eps]
		filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]

	#notifies the user when there is no shows in the show list
	if not filtered_showids and partial == 'false':
		dialog.ok('LazyTV', lang(30150))


	#loop to add more files to the playlist, the loop carries on until the playlist is full or not shows are left in the show list
	while itera in range((int(playlist_length)-1) if partial_exists == True else int(playlist_length)):

		#counts the number of shows in the showlist, if it is ever empty, the loop ends
		show_count = len(filtered_showids)
		if show_count == 0 or not filtered_showids:
			itera = 10000

		else:

			#selects a show at random from the show list
			R = random.randint(0,show_count - 1)
			SHOWID = filtered_showids[R]

			#gets the details of that show
			this_show = [x for x in all_shows if x['tvshowid'] == SHOWID][0]

			#ascertains the appropriate season and episode number of the last watched show
			if SHOWID in playlist_tally.keys():

				#if the show is already in the tally, then use that entry as the last show watched
				Season = playlist_tally[SHOWID][0]
				Episode = playlist_tally[SHOWID][1]

			elif this_show['watchedepisodes'] == 0 and premieres == 'true':

				#if the show doesnt have any watched episodes, the season and episode are both zero
				Season = 0
				Episode = 0

			else:

				#creates a list of episodes for the show that have been watched
				played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]

				#the last played episode is the one with the highest season number and then the highest episode number
				last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				Season = last_played_ep['season']
				Episode = last_played_ep['episode']

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode)
			or (x['season'] > Season)) and x['tvshowid'] == SHOWID]

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			next_ep = filter(None, next_ep)

			#creates safe version of next episode
			clean_next_ep = next_ep

			#if there is no next episode then remove the show from the show list, and start again
			if not next_ep:    
				filtered_showids = [x for x in filtered_showids if x != SHOWID]
			
			#only processes files that arent streams or that are streams but the user has specified that that is ok and either it isnt the first entry in the list or there is already a partial running
			elif ".strm" not in str(clean_next_ep[0]['file'].lower()) or (".strm" in str(clean_next_ep[0]['file'].lower()) and streams == 'true' and (itera != 0 or partial_exists == True)):

				#adds the file to the playlist
				json_query(dict_engine(next_ep[0]['file']))

				#if the user doesnt want multiples then the file is removed from the list, otherwise the episode is added to the tally list
				if multiples == 'false':
					filtered_showids = [x for x in filtered_showids if x != SHOWID]
				else:
					playlist_tally[SHOWID] = (next_ep[0]['season'],next_ep[0]['episode'])

				#starts the player if this is the first entry and a partial isnt running
				if itera == 0 and partial_exists == False:	
					proglog.close()
					player_start()

				#records a file was added to the playlist
				itera +=1

			#if the next episode is a stream and the user doesnt want streams, the show is removed from the show list
			elif ".strm" in str(clean_next_ep[0]['file'].lower()) and streams == 'false':
				filtered_showids = [x for x in filtered_showids if x != SHOWID]

			#records that he loop has completed one more time
			cycle +=1

			#infinite loop escape, is triggered if the cycle has run 100 times and streams are not allowed or there hasnt been anything added to the playlist
			#this may occur if all episodes of all shows are strms and strms are not permitted
			#if all the shows are streams, then exit the loop, otherwise, keep trying another 100 times
			if cycle % 100 == 0 and _checked == False and (streams == 'false' or itera == 0):
				#confirm all eps are streams
				check_eps = [x['file'] for x in eps if x['tvshowid'] in filtered_showids]
				if all(".strm" in ep.lower() for ep in check_eps):
					itera = 1000
				_checked = True


def create_next_episode_list():

	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist 
	ep_list = []

	#clears existing playlist
	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'}) 

	#retrieves show and episode lists
	filtered_eps, filtered_showids, all_shows, eps = populate_by_x()

	#notifies the user if there are no unwatched shows
	if not filtered_showids:
		dialog.ok('LazyTV', lang(30150))

	#updates progress dialog
	proglog.update(75, lang(30155))

	#generates a list of the last played episodes of TV shows
	for SHOWID in filtered_showids:

		played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]
		
		if not played_eps:
			#if the show doesnt have any watched episodes, the season and episode are both zero
			Season = 0
			Episode = 0			
		else:
			last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
			Season = last_played_ep['season']
			Episode = last_played_ep['episode']
			LastPlayed = last_played_ep['lastplayed']

		#creates list of unplayed episodes for the TV show
		unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode) or (x['season'] > Season)) and x['tvshowid'] == SHOWID]
		
		if unplayed_eps:

			#sorts the list so the next to be played episode is first and removes empty strings
			sorted_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			sorted_ep = filter(None, sorted_ep)
			
			if sorted_ep:

				next_ep = sorted_ep[0]

				#replaces the lastplayed
				if next_ep['lastplayed'] == 0:
					next_ep['lastplayed'] = LastPlayed

				#adds the episode to the episode list
				ep_list.append(next_ep.copy())

	#sort episode list
	if sort_list_by == '0': # Title

		load_list = [x['file'] for x in ep_list]
		load_list.sort()

	else: # last played

		#splits the list into two parts, active ordered by last played and premieres order alphabetically
		active_list = [x for x in ep_list if x['lastplayed'] is not '']
		act_list = sorted(active_list, key = lambda active_list: (active_list['lastplayed']), reverse=True)
		act_show_list = [x['tvshowid'] for x in act_list]
		a_list = [x['file'] for x in act_list]
		prem_list = [x['file'] for x in ep_list if x['tvshowid'] not in act_show_list]
		prem_list.sort()
		load_list = a_list + prem_list

	#adds the episodes one by one to the playlist
	for episode_to_load in load_list:
		json_query(dict_engine(episode_to_load))

	proglog.close()

	#launches the playlist window
	xbmc.executebuiltin("XBMC.ActivateWindow(10028)")

	
if __name__ == "__main__":
	
	if bug_exists:

		buggalo.GMAIL_RECIPIENT = 'subliminal.karnage@gmail.com'

		try:
			
			if first_run == 'true':
				_addon_.setSetting(id="first_run",value="false")
				xbmcaddon.Addon().openSettings()
			elif primary_function == '0':
				create_playlist()
			elif primary_function == '1':
				create_next_episode_list()
		except Exception:
			proglog.close()
			buggalo.onExceptionRaised()
	else:

		try:

			if first_run == 'true':
				_addon_.setSetting(id="first_run",value="false")
				xbmcaddon.Addon().openSettings()
			elif primary_function == '0':
				create_playlist()
			elif primary_function == '1':
				create_next_episode_list()
		except:
			proglog.close()
			dialog.ok('LazyTV', lang(30156), lang(30157))
