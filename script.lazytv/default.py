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

import random
import xbmcgui
import xbmcaddon
import time
import datetime
import sys
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

'''
sys.stdout = open('C:\\Temp\\test.txt', 'w')#'''

_addon_    = xbmcaddon.Addon("script.lazytv")	
_setting_  = _addon_.getSetting
lang       = _addon_.getLocalizedString
dialog     = xbmcgui.Dialog()
scriptPath = _addon_.getAddonInfo('path')


premieres        = _setting_('premieres')
partial          = _setting_('partial')
multiples        = _setting_('multipleshows')
ignore_list      = _setting_('IGNORE')
streams          = _setting_('streams')
expartials       = _setting_('expartials')
filter_show      = _setting_('filter_show')
filter_genre     = _setting_('filter_genre')
filter_length    = _setting_('filter_length')
filter_rating    = _setting_('filter_rating')
first_run        = _setting_('first_run')
primary_function = _setting_('primary_function')
populate_by      = _setting_('populate_by')
smart_pl         = _setting_('default_spl')
sort_list_by     = _setting_('sort_list_by')
debug            = True if _setting_('debug') == "true" else False
debug_type       = _setting_('debug_type')
playlist_length  = int(float(_setting_('length'))) #fix needed for jesse, as 'length' is being stored as float

if debug_type == '1':
	_addon_.setSetting(id="debug",value="false")

IGNORE_SHOWS  = proc_ig(ignore_list,'name') if filter_show == 'true' else []
IGNORE_GENRE  = proc_ig(ignore_list,'genre') if filter_genre == 'true' else []
IGNORE_LENGTH = proc_ig(ignore_list,'length') if filter_length == 'true' else []
IGNORE_RATING = proc_ig(ignore_list,'rating') if filter_rating == 'true' else []
IGNORES       = [IGNORE_SHOWS,IGNORE_GENRE,IGNORE_LENGTH,IGNORE_RATING]


#opens progress dialog, removes the cancel button
proglog = xbmcgui.DialogProgress()
proglog.create("LazyTV","Initializing...")

# get window progress
WINDOW_PROGRESS = xbmcgui.Window( 10101 )
# give window time to initialize
xbmc.sleep( 100 )
# get our cancel button
CANCEL_BUTTON = WINDOW_PROGRESS.getControl( 10 )
# disable button (bool - True=enabled / False=disabled.)
CANCEL_BUTTON.setVisible(False)
CANCEL_BUTTON.setEnabled( False )

proglog.update(1, lang(32151))

def log(vname, message):
	if debug:
		xbmc.log(msg=vname + " -- " + str(message))

log('premieres',premieres)
log('partial',partial)
log('multiples',multiples)
log('ignore_list',ignore_list)
log('streams',streams)
log('expartials',expartials)
log('filter_show',filter_show)
log('filter_genre',filter_genre)
log('filter_length',filter_length)
log('filter_rating',filter_rating)
log('first_run',first_run)
log('primary_function',primary_function)
log('populate_by',populate_by)
log('smart_pl',smart_pl)
log('sort_list_by',sort_list_by)
log('playlist_length',playlist_length)
log('IGNORE_SHOWS',IGNORE_SHOWS)
log('IGNORE_GENRE',IGNORE_GENRE)
log('IGNORE_LENGTH',IGNORE_LENGTH)
log('IGNORE_RATING',IGNORE_RATING)
log('bug_exists',bug_exists)

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK      = 92
SAVE                 = 5
HEADING              = 1
THUMBNAILS_VIEW      = 6
SELECT_VIEW          = 3
ACTION_SELECT_ITEM   = 7



def gracefail(message):
	proglog.close()
	dialog.ok("LazyTV",message)
	sys.exit()

def criteria_filter():
	#apply the custom filter to get the list of allowable TV shows and episodes

	#retrieve all TV Shows
	show_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode", "thumbnail"]}, 
	"id": "allTVShows"}

	all_s = json_query(show_request, True)

	log('all_s criteria filter', all_s)

	#checks for the absence of unwatched tv shows in the library
	if 'tvshows' not in all_s:
		gracefail(lang(32201))
	else:
		all_shows = all_s['tvshows']

	#filter the TV shows by custom criteria
	filtered_showids = [show['tvshowid'] for show in all_shows 
	if str(show['tvshowid']) not in IGNORES[0] 
	and bool(set(show['genre']) & set(IGNORES[1])) == False
	and show['mpaa'] not in IGNORES[3]
	and (show['watchedepisodes'] > 0 or premieres == 'true')
	and show['episode']>0]

	proglog.update(50, lang(32152))

	if not filtered_showids:
		gracefail(lang(32202))

	log('filtered_showids criteria filer',filtered_showids)

	#retrieve all TV episodes
	episode_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}

	ep = json_query(episode_request, True)

	log('ep criteria filter',ep)

	#accounts for the query not returning any TV shows
	if 'episodes' not in ep:
		gracefail(lang(32203))
	else:
		eps = ep['episodes']

		#Apply the show length filter and remove the episodes for shows not in the filtered show list
		filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids and x['runtime'] not in IGNORES[2]]
		
		log('filtered_eps criteria filter', filtered_eps)

		if not filtered_eps:
			gracefail(lang(32204))

		filtered_eps_showids = [x['tvshowid'] for x in filtered_eps]
		filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]
		log('filtered_eps_showids criteria filter', filtered_eps_showids)
		log('filtered_showids criteria filter', filtered_showids)
		if not filtered_eps:
			gracefail(lang(32204))


	#return the list of all and filtered shows and episodes
	return filtered_eps, filtered_showids, all_shows, eps


def smart_playlist_filter(playlist):
	# derive filtered_eps, filtered_showids from smart playlist

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf = {"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "placeholder", "media": "video"}, "id": 1}
	plf['params']['directory'] = playlist
	playlist_contents = json_query(plf, True)

	log('playlist_contents playlist filter',playlist_contents)

	if 'files' not in playlist_contents:
		gracefail(lang(32205))
	else:
		if not playlist_contents['files']:
			gracefail(lang(32205))
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log('filtered_showids playlist filter',filtered_showids)
			if not filtered_showids:
				gracefail(lang(32206))

	#retrieve all tv episodes and remove the episodes that are not in the filtered show lisy
	episode_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}

	ep = json_query(episode_request, True)
	log('ep playlist filter', ep)
	#accounts for the query not returning any TV shows
	if 'episodes' not in ep:
		gracefail(lang(32203))
	else:
		eps = ep['episodes']
		filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids]
		log('filtered_eps playlist filter',filtered_eps)

	proglog.update(50, lang(32152))

	#retrieves information on all tv shows
	show_request = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode", "thumbnail"]}, 
	"id": "allTVShows"}

	all_s = json_query(show_request, True)
	log('all_s playlist filter',all_s)
	#checks for the absence of unwatched tv shows in the library
	if 'tvshows' not in all_s:
		gracefail(lang(32201))
	else:
		all_shows = all_s['tvshows']

	#filter out the showids not in all_shows
	shows_w_unwatched = [x['tvshowid'] for x in all_shows]
	filtered_showids = [x for x in filtered_showids if x in shows_w_unwatched]

	#remove empty strings from the lists
	filtered_eps = filter(None, filtered_eps)
	filtered_showids = filter(None, filtered_showids)
	log('filtered_eps playlist filter',filtered_eps)
	log('filtered_showids playlist filter',filtered_showids)

	#returns the list of all and filtered shows and episodes
	return filtered_eps, filtered_showids, all_shows, eps


def populate_by_x():
	#populates the lists depending on the users selected playlist, or custom filter
	
	#updates progress dialog
	proglog.update(25, lang(32152))

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
	else:
		filtered_eps, filtered_showids, all_shows, eps = criteria_filter()
	
	#remove empty strings from the lists
	filtered_eps = filter(None, filtered_eps)
	filtered_showids = filter(None, filtered_showids)

	#returns the list of all and filtered shows and episodes
	proglog.update(50, lang(32153))
	return filtered_eps, filtered_showids, all_shows, eps


def create_playlist():
	#creates a random playlist of unwatched episodes

	partial_exists = False
	itera = 0
	cycle = 0
	_checked = False
	playlist_tally = {}

	#clears the playlist
	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'}, False) 

	#generates the show and episode lists
	filtered_eps, filtered_showids, all_shows, eps = populate_by_x()

	#updates progross dialog
	proglog.update(75, lang(32154))

	#Applies start with partial setting
	if partial == 'true':

		#generates a list of partially watched episodes
		partial_eps = [x for x in filtered_eps if x['resume']['position']>0]
		partial_eps = filter(None, partial_eps)
		log('partial_eps create playlist',partial_eps)

		if partial_eps:
			#identifies the most recently partially watched episode
			most_recent_partial = sorted(partial_eps, key = lambda partial_eps: (partial_eps['lastplayed']), reverse=True)[0]
			log('most_recent_partial create playlist',most_recent_partial)
			#adds the id, season and episode for the partial to a list
			playlist_tally[most_recent_partial['tvshowid']] = (most_recent_partial['season'],most_recent_partial['episode'])
			
			#removes the show from the show list if the user doesnt want more than one episode from each series
			if multiples == 'false':
				filtered_showids = [x for x in filtered_showids if x != most_recent_partial['tvshowid']]
				log('filtered_showids create playlist partials',filtered_showids)
			#adds the partial to the new playlist		
			json_query(dict_engine(most_recent_partial['episodeid'], 'episodeid'), False)

			proglog.close()

			#starts the player
			player_start()

			#notifies the rest of the script that a partial has been set up
			partial_exists = True
			log('partial_exists create playlist', partial_exists)

			#jumps to resume point of the parial
			seek_percent = float(most_recent_partial['resume']['position'])/float(most_recent_partial['resume']['total'])*100.0
			seek = {'jsonrpc': '2.0','method': 'Player.Seek','params': {'playerid':1,'value':0.0}, 'id':1}
			seek['params']['value'] = seek_percent
			json_query(seek, False)

	#removes the shows with partial episodes as the next episode from the show list
	if expartials == 'true':
		partially_watched = [x['tvshowid'] for x in filtered_eps if x['resume']['position']>0]
		filtered_eps = [x for x in filtered_eps if x['tvshowid'] not in partially_watched]
		filtered_eps_showids = [show['tvshowid'] for show in filtered_eps]
		filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]
		log('partially_watched create playlist expartials', partially_watched)
		log('filtered_eps create playlist expartials',filtered_eps)
		log('filtered_eps_showids create playlist expartials',filtered_eps_showids)
		log('filtered_showids create playlist expartials',filtered_showids)

	#notifies the user when there is no shows in the show list
	if not filtered_showids and partial_exists == False:
		dialog.ok('LazyTV', lang(32150))


	#loop to add more files to the playlist, the loop carries on until the playlist is full or not shows are left in the show list
	while itera in range((int(playlist_length)-1) if partial_exists == True else int(playlist_length)):
		log('filtered_showids itera='+str(itera),filtered_showids)
		log('playlist_tally itera',playlist_tally)
		#counts the number of shows in the showlist, if it is ever empty, the loop ends
		show_count = len(filtered_showids)
		if show_count == 0 or not filtered_showids:
			itera = 10000

		else:

			#selects a show at random from the show list
			R = random.randint(0,show_count - 1)
			SHOWID = filtered_showids[R]

			log('SHOWID itera',SHOWID)
			
			#gets the details of that show
			this_show = [x for x in all_shows if x['tvshowid'] == SHOWID][0]

			log('this_show itera',this_show)

			#ascertains the appropriate season and episode number of the last watched show
			if SHOWID in playlist_tally:

				#if the show is already in the tally, then use that entry as the last show watched
				Season = playlist_tally[SHOWID][0]
				Episode = playlist_tally[SHOWID][1]

			elif this_show['watchedepisodes'] == 0:
				#if the show doesnt have any watched episodes, the season and episode are both zero
				Season = 0
				Episode = 0

			else:
				#creates a list of episodes for the show that have been watched
				played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]
				log('played_eps itera',played_eps)
				#the last played episode is the one with the highest season number and then the highest episode number
				last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				log('last_played_ep itera',last_played_ep)
				Season = last_played_ep['season']
				Episode = last_played_ep['episode']

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode)
			or (x['season'] > Season)) and x['tvshowid'] == SHOWID]
			log('unplayed_eps itera',unplayed_eps)

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			next_ep = filter(None, next_ep)
			log('next_ep itera',next_ep)

			#removes the next_ep if it is the first in the series and premieres arent wanted
			if this_show['watchedepisodes'] == 0 and premieres == 'false':
				next_ep = []
			
			#creates safe version of next episode				
			clean_next_ep = next_ep

			#cleans the name, letters such as à were breaking the search for .strm in the name
			if clean_next_ep:
				dirty_name = clean_next_ep[0]['file']
				clean_name = fix_name(dirty_name).lower()
				log('clean_name itera',clean_name)

			#if there is no next episode then remove the show from the show list, and start again
			if not next_ep:    
				filtered_showids = [x for x in filtered_showids if x != SHOWID]
				if itera == 0 and not filtered_showids:
					dialog.ok('LazyTV', lang(32150))
			
			#only processes files that arent streams or that are streams but the user has specified that that is ok and either it isnt the first entry in the list or there is already a partial running
			elif ".strm" not in clean_name or (".strm" in clean_name and streams == 'true' and (itera != 0 or partial_exists == True)):

				#adds the file to the playlist
				json_query(dict_engine(next_ep[0]['episodeid'],'episodeid'), False)

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
			elif ".strm" in clean_name and streams == 'false':
				filtered_showids = [x for x in filtered_showids if x != SHOWID]

			#records that he loop has completed one more time
			cycle +=1

			#infinite loop escape, is triggered if the cycle has run 100 times and streams are not allowed or there hasnt been anything added to the playlist
			#this may occur if all episodes of all shows are strms and strms are not permitted
			#if all the shows are streams, then exit the loop, otherwise, keep trying another 100 times
			if cycle % 100 == 0 and _checked == False and (streams == 'false' or itera == 0):
				#confirm all eps are streams
				check_eps = [fix_name(x['file']) for x in eps if x['tvshowid'] in filtered_showids]
				if all(".strm" in ep.lower() for ep in check_eps):
					itera = 1000
				_checked = True


class xGUI(xbmcgui.WindowXMLDialog):

	def onInit(self):

		self.ok = self.getControl(SAVE)
		self.ok.setLabel(lang(32106))

		self.hdg = self.getControl(HEADING)
		self.hdg.setLabel('LazyTV')
		self.hdg.setVisible(True)

		self.ctrl6failed = False

		try:
			self.name_list = self.getControl(THUMBNAILS_VIEW)

			self.x = self.getControl(SELECT_VIEW)
			self.x.setVisible(False)
			
		except:
			self.ctrl6failed = True  #for some reason control3 doesnt work for me, so this work around tries control6
			self.close()			 #and exits if it fails, CTRL6FAILED then trigger a dialog.select instead

		self.show_load_list = show_load_list

		for i in self.show_load_list:
			self.tmp = xbmcgui.ListItem(i[0],i[1],thumbnailImage=i[2])
			self.name_list.addItem(self.tmp)
			
		self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)

	def onAction(self, action):
		actionID = action.getId()
		if (actionID in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK)):
			self.load_show_id = -1
			self.close()

	def onClick(self, controlID):
		if controlID == SAVE:
			self.load_show_id = -1
			self.close()
		else:
			self.load_show_id = self.name_list.getSelectedPosition()
			self.close()


def create_next_episode_list():

	global show_load_list
	load_show_id = -1

	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist 
	ep_list = []

	#clears existing playlist
	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'}, False) 

	#retrieves show and episode lists
	filtered_eps, filtered_showids, all_shows, eps = populate_by_x()

	#notifies the user if there are no unwatched shows
	if not filtered_showids:
		gracefail(lang(32150))

	#updates progress dialog
	proglog.update(75, lang(32155))

	#generates a list of the last played episodes of TV shows
	for SHOWID in filtered_showids:

		played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]
		log('played_eps list',played_eps)
		if not played_eps:
			#if the show doesnt have any watched episodes, the season and episode are both zero
			Season = 0
			Episode = 0
			LastPlayed = ''			
		else:
			last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
			log('last_played_ep list',last_played_ep)
			Season = last_played_ep['season']
			Episode = last_played_ep['episode']
			LastPlayed = last_played_ep['lastplayed']

		#creates list of unplayed episodes for the TV show
		unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode) or (x['season'] > Season)) and x['tvshowid'] == SHOWID]
		log('unplayed_eps list',unplayed_eps)
		if unplayed_eps:

			#sorts the list so the next to be played episode is first and removes empty strings
			sorted_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			sorted_ep = filter(None, sorted_ep)
			log('sorted_ep list',sorted_ep)
			if sorted_ep:

				next_ep = sorted_ep[0]

				#replaces the lastplayed
				if not next_ep['lastplayed']:
					next_ep['lastplayed'] = LastPlayed

				#adds the episode to the episode list
				ep_list.append(next_ep.copy())

	# create a dict of tvshowids and shownames &thumbnails
	shownames = {}
	for x in all_shows:
		shownames[x['tvshowid']] = {}
		shownames[x['tvshowid']]['title'] = x['title']
		shownames[x['tvshowid']]['thumbnail'] = x['thumbnail']
	log('shownames list',shownames)
	#today
	tdf = '%Y-%m-%d'
	today = time.strptime(str(datetime.date.today()), tdf)
	todate = datetime.date(today[0],today[1],today[2])

	#sort episode list
	if sort_list_by == '0': # Title

		active_list = [(shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("" if not x['resume']['position'] and not x['lastplayed'] else "(") +  ("" if not x['resume']['position'] else str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%") + (",  " if x['resume']['position'] and x['lastplayed'] else "") + ("" if not x['lastplayed'] else day_calc(x['lastplayed'],todate,'diff')) + (")" if x['resume']['position'] and not x['lastplayed'] else ""), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list]
		active_list.sort()

		show_load_list = [(x[0],x[1],x[2]) for x in active_list]
		id_list = [x[3] for x in active_list]

	else: # last played

		active_list = [(day_calc(x['lastplayed'],todate,'date_list'), shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("(" if x['resume']['position'] == 0 else "(" + str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%,  ") + day_calc(x['lastplayed'],todate,'diff'), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list if x['lastplayed']]
		prem_list = [(shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("" if x['resume']['position'] == 0 else "(" + str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%"), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list  if not x['lastplayed']]

		prem_list.sort()
		active_list.sort(reverse=True)		
		active_list_final = [(x[1],x[2],x[3],x[4]) for x in active_list]

		show_load_list = active_list_final + prem_list
		id_list = [x[3] for x in show_load_list]

	log('show_load_list list',show_load_list)
	log('id_list list',id_list)

	proglog.close()

	list_window = xGUI("DialogSelect.xml", scriptPath, 'Default')
	list_window.doModal()
	
	if list_window.ctrl6failed == True:
		del list_window
		user_options = []
		for xi in show_load_list:
			user_options.append(xi[0] + "  " + xi[1])
		load_show_id= xbmcgui.Dialog().select("LazyTV", user_options)
	
	else:
		load_show_id = list_window.load_show_id
		del list_window


	if load_show_id != -1:
		play_command = {'jsonrpc': '2.0','method': 'Player.Open','params': {'item': {'episodeid':id_list[load_show_id]}, 'options':{'resume': True}},'id': 1}
		try:
			json_query(play_command, False) 
		except:
			gracefail(lang(32207))


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
			elif primary_function == '2':
				choice = dialog.yesno('LazyTV', lang(32158),'',lang(32159), lang(32160),lang(32161))
				if choice == 1:
					create_playlist()
				elif choice == 0:
					create_next_episode_list()
				else:
					pass
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
			elif primary_function == '2':
				choice = dialog.yesno('LazyTV', lang(32158),'',lang(32159), lang(32160),lang(32161))
				if choice == 1:
					create_playlist()
				elif choice == 0:
					create_next_episode_list()
				else:
					pass
		except:
			proglog.close()
			dialog.ok('LazyTV', lang(32156), lang(32157))
