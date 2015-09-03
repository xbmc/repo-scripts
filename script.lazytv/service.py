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

'''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ - allow for next ep notification in LazyTV smartplaylist READY FOR TESTING
#@@@@@@@@@@ - suppress notification at start up READY FOR TESTING
#@@@@@@@@@@ - improve handling of specials
#@@@@@@@@@@ - improve refreshing of LazyTV Show Me window
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''


import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import datetime
import ast
import json
import re
import random
import sys

# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass

__addon__              = xbmcaddon.Addon()
__addonid__            = __addon__.getAddonInfo('id')
__addonversion__       = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__         = __addon__.getAddonInfo('path')
__profile__            = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__            = __addon__.getSetting
videoplaylistlocation  = xbmc.translatePath('special://profile/playlists/video/')
start_time             = time.time()
base_time              = time.time()
WINDOW                 = xbmcgui.Window(10000)
DIALOG                 = xbmcgui.Dialog()

WINDOW.setProperty("LazyTV.Version", str(__addonversion__))
WINDOW.setProperty("LazyTV.ServicePath", str(__scriptPath__))
WINDOW.setProperty('LazyTV_service_running', 'starting')

promptduration         = int(float(__setting__('promptduration')))
promptdefaultaction    = int(float(__setting__('promptdefaultaction')))

keep_logs              = True if __setting__('logging') 			== 'true' else False
playlist_notifications = True if __setting__("notify")  			== 'true' else False
resume_partials        = True if __setting__('resume_partials') 	== 'true' else False
nextprompt             = True if __setting__('nextprompt') 			== 'true' else False
nextprompt_or          = True if __setting__('nextprompt_or') 		== 'true' else False
prevcheck              = True if __setting__('prevcheck') 			== 'true' else False
moviemid               = True if __setting__('moviemid') 			== 'true' else False
first_run              = True if __setting__('first_run') 			== 'true' else False
startup                = True if __setting__('startup') 			== 'true' else False
maintainsmartplaylist  = True if __setting__('maintainsmartplaylist') 			== 'true' else False

if promptduration == 0:
	promptduration = 1 / 1000.0

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
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__ + 'service', total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time


# get the current version of XBMC
versstr = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
vers = ast.literal_eval(versstr)
if 'result' in vers and 'version' in vers['result'] and (int(vers['result']['version']['major']) > 12 or int(vers['result']['version']['major']) == 12 and int(vers['result']['version']['minor']) > 8):
	__release__            = "Gotham"
else:
	__release__            = "Frodo"

whats_playing          = {"jsonrpc": "2.0","method": "Player.GetItem","params": {"properties": ["showtitle","tvshowid","episode", "season", "playcount", "resume"],"playerid": 1},"id": "1"}
now_playing_details    = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["playcount", "tvshowid"],"episodeid": "1"},"id": "1"}
ep_to_show_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": "1"},"id": "1"}
prompt_query           = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["season","episode","showtitle","tvshowid"],"episodeid": "1"},"id": "1"}
show_request           = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount","operator": "is","value": "0"},"properties": ["genre","title","playcount","mpaa","watchedepisodes","episode","thumbnail"]},"id": "1"}
show_request_all       = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"properties": ["title"]},"id": "1"}
show_request_lw        = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort":{"order": "descending", "method":"lastplayed"} },"id": "1" }
eps_query              = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "1"},"id": "1"}
ep_details_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["title","playcount","plot","season","episode","showtitle","file","lastplayed","rating","resume","art","streamdetails","firstaired","runtime","tvshowid"],"episodeid": 1},"id": "1"}
seek                   = {"jsonrpc": "2.0","id": 1, "method": "Player.Seek","params": {"playerid": 1, "value": 0 }}
plf                    = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}}
add_this_ep            = {'jsonrpc': '2.0','id': 1, "method": 'Playlist.Add', 				"params": {'item' : {'episodeid' : 'placeholder' }, 'playlistid' : 1}}

log('Running: ' + str(__release__))


def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		result = unicode(result, 'utf-8', errors='ignore')
		if ret:
			return json.loads(result)['result']

		else:
			return json.loads(result)
	except:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		result = unicode(result, 'utf-8', errors='ignore')
		log(json.loads(result))
		return json.loads(result)


def stringlist_to_reallist(string):
	# this is needed because ast.literal_eval gives me EOF errors for no obvious reason
	real_string = string.replace("[","").replace("]","").replace(" ","").split(",")
	return real_string


def runtime_converter(time_string):
	if time_string == '':
		return 0
	else:
		x = time_string.count(':')

		if x ==  0:
			return int(time_string)
		elif x == 2:
			h, m, s = time_string.split(':')
			return int(h) * 3600 + int(m) * 60 + int(s)
		elif x == 1:
			m, s = time_string.split(':')
			return int(m) * 60 + int(s)
		else:
			return 0


def iStream_fix(show_npid,showtitle,episode_np,season_np):

	# streams from iStream dont provide the showid and epid for above
	# they come through as tvshowid = -1, but it has episode no and season no and show name
	# need to insert work around here to get showid from showname, and get epid from season and episode no's
	# then need to ignore prevcheck
	log('fixing istream, data follows...')
	log('show_npid = ' +str(show_npid))
	log('showtitle = ' +str(showtitle))
	log('episode_np = ' +str(episode_np))
	log('season_np = ' + str(season_np))
	redo = True
	count = 0
	while redo and count < 2: 				# this ensures the section of code only runs twice at most
		redo = False
		count += 1
		if show_npid == -1 and showtitle and episode_np and season_np:
			prevcheck = False
			tmp_shows = json_query(show_request_all,True)
			log('tmp_shows = ' + str(tmp_shows))
			if 'tvshows'in tmp_shows:
				for x in tmp_shows['tvshows']:
					if x['label'] == showtitle:
						show_npid = x['tvshowid']
						eps_query['params']['tvshowid'] = show_npid
						tmp_eps = json_query(eps_query,True)
						log('tmp eps = '+ str(tmp_eps))
						if 'episodes' in tmp_eps:
							for y in tmp_eps['episodes']:
								if fix_SE(y['season']) == season_np and fix_SE(y['episode']) == episode_np:
									ep_npid = y['episodeid']
									log('playing epid stream = ' + str(ep_npid))

									# get odlist
									tmp_od    = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" 						% ('LazyTV', show_npid)))
									if show_npid in randos:
										tmpoff = WINDOW.getProperty("%s.%s.offlist" 					% ('LazyTV', show_npid))
										if tmp_off:
											tmp_od += ast.literal_eval(tmp_off)
									log('tmp od = ' + str(tmp_od))
									log('ep_npid = ' + str(ep_npid))
									if ep_npid not in tmp_od:
										log('iStream fix calls get eps')
										Main.get_eps([show_npid])
										log('iStream fix post get eps')
										redo = True

	return False, show_npid, ep_npid


def fix_SE(string):
	if len(str(string)) == 1:
		return '0' + str(string)
	else:
		return str(string)


def _breathe():
	# lets addon know the service is running
	if WINDOW.getProperty('LazyTV_service_running') == 'marco':
		WINDOW.setProperty('LazyTV_service_running', 'polo')


class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		LazyPlayer.np_next = False
		LazyPlayer.pl_running = 'null'
		LazyPlayer.playing_showid = False
		LazyPlayer.playing_epid = False
		LazyPlayer.nextprompt_trigger = False


	def onPlayBackStarted(self):
		log('Playbackstarted',reset=True)
		global prevcheck

		Main.target = False
		LazyPlayer.nextprompt_trigger_override = True


		#check if an episode is playing
		self.ep_details = json_query(whats_playing, True)
		log('this is playing = ' + str(self.ep_details))

		# grab odlist
		# check if current show is in odlist
		# if it is then pause and post notification, include S0xE0x of first available
		# if notification is Yes Watch then unpause (this should be default action)
		# if notification is No, then go to the TV show page
		# of if they prefer, start playing that OnDeck episode

		# xbmc.getInfoLabel('')

		self.pl_running = WINDOW.getProperty("%s.playlist_running"	% ('LazyTV'))

		if 'item' in self.ep_details and 'type' in self.ep_details['item']:

			pll = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')

			# check if this is a playlist, and if it is then suppress the next_ep_notify when there are more than 1 items
			# unless it IS a LazyTV playlist and the user wants nextprompts in LazyTV playlists
			if pll != '1' and not all([self.pl_running == 'true', nextprompt_or]):
				log('nextprompt override')
				LazyPlayer.nextprompt_trigger_override = False			


			if self.ep_details['item']['type'] in ['unknown','episode']:

				episode_np = fix_SE(self.ep_details['item']['episode'])
				season_np = fix_SE(self.ep_details['item']['season'])
				showtitle = self.ep_details['item']['showtitle']
				show_npid = int(self.ep_details['item']['tvshowid'])

				try:
					ep_npid = int(self.ep_details['item']['id'])
				except KeyError:
					if self.ep_details['item']['episode'] <0:
						prevcheck = False
						ep_npid = False
						show_npid = False
					else:
						prevcheck, show_npid, ep_npid = iStream_fix(show_npid,showtitle,episode_np,season_np)


				log(prevcheck, label='prevcheck')

				if prevcheck and show_npid not in randos and self.pl_running != 'true':
					log('Passed prevcheck')
					odlist = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', show_npid)))
					stored_epid = int(WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', show_npid)))
					stored_seas = fix_SE(int(WINDOW.getProperty("%s.%s.Season" % ('LazyTV', show_npid))))
					stored_epis = fix_SE(int(WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', show_npid))))
					if ep_npid in odlist[1:] and stored_epid:
						#pause
						xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')

						#show notification
						usr_note = DIALOG.yesno(lang(32160), lang(32161) % (showtitle,stored_seas, stored_epis), lang(32162))
						log(usr_note)

						if usr_note == 0:
							#unpause
							xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
						else:
							xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
							xbmc.sleep(100)
							xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % (stored_epid))

				if self.pl_running == 'true' and playlist_notifications:

					xbmc.executebuiltin('Notification(%s,%s S%sE%s,%i)' % (lang(32163),showtitle,season_np,episode_np,5000))

				if (self.pl_running == 'true' and resume_partials) or self.pl_running == 'listview':

					res_point = self.ep_details['item']['resume']
					if res_point['position'] > 0:

						seek_point = int((float(res_point['position']) / float(res_point['total'])) *100)
						seek['params']['value'] = seek_point
						json_query(seek, True)

				# this prompts Main daemon to set up the swap and prepare the prompt
				LazyPlayer.playing_epid = ep_npid
				LazyPlayer.playing_showid = show_npid
				log('LazyPlayer supplied showid = ' + str(LazyPlayer.playing_showid))
				log('LazyPlayer supplied epid = '+ str(LazyPlayer.playing_epid))


			elif self.ep_details['item']['type'] == 'movie' and self.pl_running == 'true' :

				if playlist_notifications:

					xbmc.executebuiltin('Notification(%s,%s,%i)' % (lang(32163),self.ep_details['item']['label'],5000))

				if resume_partials and self.ep_details['item']['resume']['position'] > 0:
					seek_point = int((float(self.ep_details['item']['resume']['position']) / float(self.ep_details['item']['resume']['total'])) *100)
					seek['params']['value'] = seek_point
					json_query(seek, True)

				elif moviemid and self.ep_details['item']['playcount'] != 0:
					time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
					seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)
					seek['params']['value'] = seek_point
					json_query(seek, True)

		log('Playbackstarted_End')


	def onPlayBackStopped(self):

		pre_showid  = Main.nextprompt_info['tvshowid']

		WINDOW.setProperty("%s.%s.Resume" % ('LazyTV', pre_showid), 'true')
		
		self.onPlayBackEnded()


	def onPlayBackEnded(self):


		# this is right at the start so that the info for the previously played episode is retrieved while
		# it is still available

		pre_seas  = Main.nextprompt_info.get('season', None)
		pre_ep    = Main.nextprompt_info.get('episode', None)
		pre_title = Main.nextprompt_info.get('showtitle', None)
		pre_epid  = Main.nextprompt_info.get('episodeid', None)
		paused    = False

		if any([pre_seas is None, pre_ep is None, pre_title is None, pre_epid is None]):

			log('Main.nextprompt_info missing vital data')

			log('pre_seas %s' % pre_seas)
			log('pre_ep %s' % pre_ep)
			log('pre_title %s' % pre_title)
			log('pre_epid %s' % pre_epid)
			
			Main.nextprompt_info = {}

			return

		log('Playbackended', reset =True)

		LazyPlayer.playing_epid = False

		xbmc.sleep(500)		#give the chance for the playlist to start the next item

		# this is all to handle the next_ep_notification
		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')


		# if pl_running and user wants next ep notifications to run
		# then pause currently playing item, run notification.
		# the next prompt info gets refreshed when something new starts playing
		# so the prompt has to show BEFORE the information gets over written
		# OR this method needs to extract the information from the next_prompt_info dictionary as soon as the show is stopped

		if self.now_name == '' or all([self.pl_running == 'true', nextprompt_or]):

			if all([self.now_name == '', self.pl_running == 'true']):
				WINDOW.setProperty("LazyTV.playlist_running", 'false')

			if LazyPlayer.nextprompt_trigger and LazyPlayer.nextprompt_trigger_override:

				if self.now_name != '':
					# if something is playing, then the list if a LazyTV playlist and nextprompt override is in chosen by the user
					#pause
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')
					paused = True

				LazyPlayer.nextprompt_trigger = False

				SE = str(int(pre_seas)) + 'x' + str(int(pre_ep))

				log('promptdefaultaction = ' + str(promptdefaultaction))

				if promptdefaultaction == 0:
					ylabel = lang(32092)
					nlabel = lang(32091)
					prompt = -1
				elif promptdefaultaction == 1:
					ylabel = lang(32091)
					nlabel = lang(32092)	
					prompt = -1	

				if __release__ == 'Frodo':
					if promptduration:
						prompt = DIALOG.select(lang(32164), [lang(32165) % promptduration, lang(32166) % (pre_title, SE)], yeslabel = ylabel, nolabel = nlabel, autoclose=int(promptduration * 1000))
					else:
						prompt = DIALOG.select(lang(32164), [lang(32165) % promptduration, lang(32166) % (pre_title, SE)], yeslabel = ylabel, nolabel = nlabel)

				elif __release__ == 'Gotham':
					if promptduration:
						prompt = DIALOG.yesno(lang(32167) % promptduration, lang(32168) % (pre_title, SE), lang(32169), yeslabel = ylabel, nolabel = nlabel, autoclose=int(promptduration * 1000))
					else:
						prompt = DIALOG.yesno(lang(32167) % promptduration, lang(32168) % (pre_title, SE), lang(32169), yeslabel = ylabel, nolabel = nlabel)

				else:
					prompt = 0

				log('starting prompt = ' + str(prompt))

				if prompt == -1:
					prompt = 0
				elif prompt == 0:
					if promptdefaultaction == 1:
						prompt = 1
				elif prompt == 1:
					if promptdefaultaction == 1:
						prompt = 0

				log("nextep final prompt = " + str(prompt))

				if prompt:
					xbmc.executeJSONRPC('{"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",				"params": {"playlistid": 1}}')
					#xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % Main.nextprompt_info['episodeid'])

					add_this_ep['params']['item']['episodeid'] = int(pre_epid)
					json_query(add_this_ep, False)
					xbmc.sleep(50)
					xbmc.Player().play(xbmc.PlayList(1))
					if paused:
						log('unpausing')
						xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
				elif self.now_name != '' and paused:
					# if something is playing, then the list if a LazyTV playlist and nextprompt override is in chosen by the user
					# if they elected not to play the next prompt, then we need to unpause
					log('unpausing')
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')

			Main.nextprompt_info = {}

		log('Playbackended_End')


class LazyMonitor(xbmc.Monitor):

	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)


	def onSettingsChanged(self):
		#update the settings
		grab_settings()

	def onDatabaseUpdated(self, database):
		if database == 'video':
			log('updating due to database notification')
			# update the entire list again, this is to ensure we have picked up any new shows.
			Main.onLibUpdate = True


	def onNotification(self, sender, method, data):
		#this only works for GOTHAM
		log('notification!')

		skip = False

		try:
			self.ndata = ast.literal_eval(data)
		except:
			skip = True

		if skip == True:
			pass

		elif method == 'VideoLibrary.OnUpdate':
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}

			if 'item' in self.ndata:

				if 'playcount' in self.ndata:

					if 'type' in self.ndata['item']:

						if self.ndata['item']['type'] == 'episode':

							if self.ndata['playcount'] == 1:

								log('manual change to watched status, data = ' + str(self.ndata))

								ep_to_show_query['params']['episodeid'] = self.ndata['item']['id']
								tmp_showid = json_query(ep_to_show_query, True)['episodedetails']['tvshowid']
								LazyPlayer.playing_epid = self.ndata['item']['id']

								proceed = False
								if tmp_showid in randos:

									retod    = WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', tmp_showid))
									try:
										a = ast.literal_eval(retod)
									except:
										a=[]
									retoff    = WINDOW.getProperty("%s.%s.offlist" % ('LazyTV', tmp_showid))
									try:
										b = ast.literal_eval(retoff)
									except:
										b = []

									if LazyPlayer.playing_epid in a or LazyPlayer.playing_epid in b:
										proceed = True

								else:
									retod    = WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', tmp_showid))
									try:
										a = ast.literal_eval(retod)
									except:
										a = []
									if LazyPlayer.playing_epid in a:
										proceed = True

								if proceed:
									Main.monitor_override = True
									LazyPlayer.playing_showid = json_query(ep_to_show_query, True)['episodedetails']['tvshowid']
									log('monitor supplied showid - ' + str(LazyPlayer.playing_showid))
									log('monitor supplied epid - ' + str(LazyPlayer.playing_epid))
								else:
									LazyPlayer.playing_epid = False


class Main(object):
	def __init__(self, *args, **kwargs):
		log('monitor instantiated', reset = True)

		self.initial_limit    = 10
		self.count            = 0
		Main.target           = False
		Main.nextprompt_info  = {}
		Main.onLibUpdate      = False
		Main.monitor_override = False
		Main.nepl             = []
		self.eject            = False
		self.randy_flag       = False							# the list of currently stored episodes

		self.initialisation()

		log('daemon started')
		self._daemon()			#_daemon keeps the monitor alive

	def initialisation(self):
		log('variable_init_started')

		self.Player  = LazyPlayer()							# used to post notifications on episode change
		self.Monitor = LazyMonitor(self)
		self.retrieve_all_show_ids()									# queries to get all show IDs

		WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'null')

		#self.get_eps(showids = self.all_shows_list)				#gets the beginning list of unwatched shows

		#xbmc.sleep(1000) 		# wait 1 seconds before filling the full list

		self.get_eps(showids = self.all_shows_list)

		log('variable_init_End')



	def _daemon(self):

		WINDOW.setProperty('LazyTV_service_running' , 'true')
		
		if startup:
			xbmc.executebuiltin('Notification(%s,%s,%i)' % ('LazyTV',lang(32173),5000))

		while not xbmc.abortRequested and WINDOW.getProperty('LazyTV_service_running'):
			xbmc.sleep(100)
			self._daemon_check()

	def _daemon_check(self):

		_breathe()

		self.np_next = False

		if Main.onLibUpdate:
			Main.onLibUpdate = False
			self.retrieve_all_show_ids()
			self.get_eps(showids = self.all_shows_list)


		shuf = WINDOW.getProperty("LazyTV.rando_shuffle")
		if shuf == 'true':
			WINDOW.setProperty("LazyTV.rando_shuffle", 'false')
			log('shuffling randos')
			self.reshuffle_randos()


		# this will only show up when the Player detects a TV episode is playing
		if LazyPlayer.playing_showid and LazyPlayer.playing_showid in Main.nepl:
			log('message recieved, showid = ' + str(LazyPlayer.playing_showid))

			self.sp_next = LazyPlayer.playing_showid

			# set TEMP episode
			retod    = WINDOW.getProperty("%s.%s.odlist" 						% ('LazyTV', self.sp_next))
			retoff   = WINDOW.getProperty("%s.%s.offlist" 						% ('LazyTV', self.sp_next))
			offd     = ast.literal_eval(retoff)
			ond      = ast.literal_eval(retod)
			tmp_wep  = int(WINDOW.getProperty("%s.%s.CountWatchedEps"         	% ('LazyTV', self.sp_next)).replace("''",'0')) + 1
			tmp_uwep = max(0, int(WINDOW.getProperty("%s.%s.CountUnwatchedEps"  % ('LazyTV', self.sp_next)).replace("''",'0')) - 1)

			log('odlist = ' + str(retod))


			if self.sp_next in randos:

				npodlist = offd + ond

				if npodlist:

					if LazyPlayer.playing_epid not in npodlist:
						log('rando not in npodlist')

						self.np_next = False

					else:
						log('rando in odlist')

						if LazyPlayer.playing_epid in ond:
							ond.remove(LazyPlayer.playing_epid)
						else:
							offd.remove(LazyPlayer.playing_epid)

						npodlist 		= offd + ond
						random.shuffle(npodlist)
						self.np_next    = npodlist[0]

						self.randy_flag = True

						self.store_next_ep(self.np_next,'temp', ond, offd, tmp_uwep, tmp_wep)

					LazyPlayer.playing_epid   = False
					LazyPlayer.playing_showid = False

					if Main.monitor_override:
						log('monitor override, swap called')

						Main.monitor_override   = False
						LazyPlayer.playing_epid = False
						Main.target             = False
						self.np_next            = False

						self.swap_over(self.sp_next)

			else:

				npodlist = ond

				if npodlist:

					if LazyPlayer.playing_epid not in npodlist:
						log('supplied epid not in odlist')

						self.np_next              = False
						LazyPlayer.playing_showid = False
						LazyPlayer.playing_epid   = False

					else:

						cp = npodlist.index(LazyPlayer.playing_epid)
						log('supplied epid in odlist at position = ' + str(cp))

						if cp != len(npodlist) - 1:

							self.np_next = npodlist[cp + 1]		#if the episode is in the list then take the next item and store in temp
							newod        = [int(x) for x in npodlist[cp + 1:]]

							self.store_next_ep(self.np_next,'temp', newod, offd, tmp_uwep, tmp_wep )

							log('supplied epid not last in list, retrieved new ep = ' + str(self.np_next))
							log('new odlist = ' + str(newod))

							if Main.monitor_override:
								log('monitor override, swap called')

								self.swap_over(self.sp_next)

								Main.monitor_override   = False
								LazyPlayer.playing_epid = False
								Main.target             = False
								self.np_next            = False

						else:
							log('supplied epid in last position in odlist, flag to remove from nepl')
							self.eject = True 		#if the episode is the last in the list then send the message to remove the showid from nepl

			if self.np_next:
				log('next ep to load = ' + str(self.np_next))

			# set NEXTPROMPT if required

			if nextprompt and self.np_next and not self.eject and not self.randy_flag:

				prompt_query['params']['episodeid'] = int(self.np_next)

				cp_details = json_query(prompt_query, True)

				log(cp_details, label='cp_details')

				if 'episodedetails' in cp_details:

					Main.nextprompt_info = cp_details['episodedetails']


			# set the TARGET time, every tv show will have a target, some may take longer to start up
			tick = 0
			while not Main.target and tick < 20:

				Main.target = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration')) * 0.9
				tick += 1

				xbmc.sleep(250)

			log(label='tick = ',message=str(tick))
			log(message='%s:%d' % (int(Main.target/60 if Main.target else 0),Main.target%60), label='target')

		# resets the ids so this first section doesnt run again until some thing new is playing
		LazyPlayer.playing_showid = False

		# only allow the monitor override to run once
		Main.monitor_override     = False

		# only allow the randy flag to run once, this avoids previous episode notification for randos
		self.randy_flag = False


		# check the position of the played item every 5 seconds, if it is beyond the Main.target position then trigger the pre-stop update
		if Main.target:

			self.count = (self.count + 1) % 50

			if self.count == 0: 	#check the position of the playing item every 5 seconds, if it is past the Main.target then run the swap

				if runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time')) > Main.target:

					log('Main.target exceeded')
					log(self.nextprompt_info)

					if self.eject:
						self.remove_from_nepl(self.sp_next)
						self.sp_next = False
						self.eject = False

					if self.sp_next:
						self.swap_over(self.sp_next)
						log('swap occurred')

					if nextprompt and self.nextprompt_info:
						log('trigger set')
						LazyPlayer.nextprompt_trigger = True

					self.sp_next          = False
					self.np_next          = False
					Main.target           = False
					Main.monitor_override = False

	@classmethod
	def remove_from_nepl(self,showid):
		log('removing from nepl')
		if showid in Main.nepl:
			log('nepl before = ' + str(Main.nepl))
			Main.nepl.remove(showid)
			log('nepl after = ' + str(Main.nepl))
			WINDOW.setProperty("%s.nepl" % 'LazyTV', str(Main.nepl))

		self.update_smartplaylist(showid, remove = True)
 


	@classmethod
	def add_to_nepl(self,showid):
		log('adding to nepl')
		if showid not in Main.nepl:
			log('nepl before = ' + str(Main.nepl))
			Main.nepl.append(showid)
			log('nepl after = ' + str(Main.nepl))
			WINDOW.setProperty("%s.nepl" % 'LazyTV', str(Main.nepl))


	@classmethod
	def reshuffle_randos(self, sup_rand=[]):
		# this reshuffles the randos, it leaves the rando in the odlist
		# it can accept a list of randos or individual ones
		# this can only be called at the start of the random play or list view ADDON
		# because if it happens after the rando is displayed
		# the playingID wont match the stored ID
		log('shuffle started')

		if not sup_rand:
			shuf_rand = randos
		else:
			shuf_rand = sup_rand

		log('shuffle list = ' +str(shuf_rand))

		for rando in shuf_rand:

			# get odlist
			try:
				tmp_od = ast.literal_eval(WINDOW.getProperty("LazyTV.%s.odlist" % rando))
			except:
				tmp_od = []
			try:
				tmp_off = ast.literal_eval(WINDOW.getProperty("LazyTV.%s.offlist" % rando))
			except:
				tmp_off = []

			ep = WINDOW.getProperty("LazyTV.%s.EpisodeID" % rando)

			if not ep:
				continue

			tmp_ep = int(ep)

			tmp_wep = WINDOW.getProperty("%s.%s.CountWatchedEps"         % ('LazyTV', rando)).replace("''",'0')
			tmp_uwep = WINDOW.getProperty("%s.%s.CountUnwatchedEps"         % ('LazyTV', rando)).replace("''",'0')

			tmp_cmb = tmp_od + tmp_off
			if not tmp_cmb:
				continue

			# choose new rando
			random.shuffle(tmp_cmb)
			randy = tmp_cmb[0]

			# get ep details and load it up
			self.store_next_ep(randy, rando, tmp_od, tmp_off, tmp_uwep, tmp_wep)
		log('shuffle ended')


	def retrieve_all_show_ids(self):
		log('retrieve_all_shows_started')

		self.result = json_query(show_request, True)
		if 'tvshows' not in self.result:
			self.all_shows_list = []
		else:
			self.all_shows_list = [id['tvshowid'] for id in self.result['tvshows']]
		log('retrieve_all_shows_End')


	@classmethod
	def get_eps(self, showids = []):
		log('get_eps_started', reset =True)
		kcount = 0
		# called whenever the Next_Eps stored in 10000 need to be updated
		# determines the next ep for the showids it is sent and saves the info to 10000

		#turns single show id into a list
		self.showids    = showids if isinstance(showids, list) else [showids]

		self.lshowsR = json_query(show_request_lw, True)		#gets showids and last watched

		if 'tvshows' not in self.lshowsR:						#if 'tvshows' isnt in the result, have the list be empty so we return without doing anything
			self.show_lw = []
		else:
			self.show_lw = [x['tvshowid'] for x in self.lshowsR['tvshows'] if x['tvshowid'] in self.showids]

		for my_showid in self.show_lw:				#process the list of shows

			_breathe()

			eps_query['params']['tvshowid'] = my_showid			# creates query
			self.ep = json_query(eps_query, True)				# query grabs the TV show episodes

			if 'episodes' not in self.ep: 						#ignore show if show has no episodes
				continue
			else:
				self.eps = self.ep['episodes']

			played_eps           = []
			all_unplayed         = []
			ondeck_eps           = []
			Season               = 1 	# these are set to 1x1 in order to ignore specials
			Episode              = 0
			watched_showcount    = 0
			self.count_ondeckeps = 0 	# will be the total number of ondeck episodes
			on_deck_epid         = ''

			_append = all_unplayed.append 		#reference to avoid reevaluation on each loop

			# runs through the list and finds the watched episode with the highest season and episode numbers, and creates a list of unwatched episodes
			for ep in self.eps:
				if ep['playcount'] != 0:
					watched_showcount += 1
					if (ep['season'] == Season and ep['episode'] > Episode) or ep['season'] > Season:
						Season = ep['season']
						Episode = ep['episode']
				else:
					_append(ep)

			# remove duplicate files, this removes the second ep in double episodes
			files = []
			tmpvar = all_unplayed
			for ep in tmpvar:
				if ep['file'] and ep['file'] in files:
					all_unplayed.remove(ep)
				else:
					files.append(ep['file'])
			del files
			del tmpvar


			# this is the handler for random shows, basically, if the show is in the rando list, then unwatched all shows are considered on deck
			# this section will now provide both an ondeck list and an offdeck list
			unordered_ondeck_eps = [x for x in all_unplayed if x['season'] > Season or (x['season'] == Season and x['episode'] > Episode)]
			offdeck_eps = [x for x in all_unplayed if x not in unordered_ondeck_eps]

			self.count_eps   = len(self.eps)						# the total number of episodes
			self.count_weps  = watched_showcount					# the total number of watched episodes
			self.count_uweps = self.count_eps - self.count_weps 	# the total number of unwatched episodes

			# sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			if unordered_ondeck_eps:
				unordered_ordered_eps = sorted(unordered_ondeck_eps, key = lambda unordered_ondeck_eps: (unordered_ondeck_eps['season'], unordered_ondeck_eps['episode']))
			else:
				unordered_ordered_eps = []
			ondeck_eps = filter(None, unordered_ordered_eps)

			if not ondeck_eps and not offdeck_eps:			# ignores show if there is no on-deck or offdeck episodes
				if my_showid in Main.nepl:					# remove the show from nepl
					self.remove_from_nepl(my_showid)
				continue

			# get the id for the next show and load the list of episode ids into ondecklist
			if my_showid in randos or not ondeck_eps:
				comb_deck = ondeck_eps + offdeck_eps
				random.shuffle(comb_deck)
				on_deck_epid = comb_deck[0]['episodeid']
			else:
				on_deck_epid = ondeck_eps[0]['episodeid']

			# another handler for randos, as they have to stay in the odlist
			on_deck_list = [x['episodeid'] for x in ondeck_eps] if ondeck_eps else []
			off_deck_list = [x['episodeid'] for x in offdeck_eps] if offdeck_eps else []

			#load the data into 10000 using the showID as the ID
			self.store_next_ep(on_deck_epid, my_showid, on_deck_list, off_deck_list, self.count_uweps, self.count_weps)

			# if the show doesnt have any ondeck eps and it isnt in randos, then dont consider it active
			# (even though the offdeck list has been saved and a random episode has been selected and saved)
			if not ondeck_eps and my_showid not in randos:
				continue

			# store the showID in NEPL so DEFAULT can retrieve it
			if my_showid not in Main.nepl:
				Main.nepl.append(my_showid)

		#update the stored nepl
		WINDOW.setProperty("%s.nepl" % 'LazyTV', str(Main.nepl))

		log('get_eps_Ended')

	@classmethod
	def store_next_ep(self,episodeid,tvshowid, ondecklist, offdecklist, uwep=0,wep=0):

		#stores the episode info into 10000
		try:
			TVShowID_ = int(tvshowid)
		except:
			TVShowID_ = tvshowid

		if not xbmc.abortRequested:

			_breathe()

			ep_details_query['params']['episodeid'] = episodeid				# creates query

			ep_details = json_query(ep_details_query, True)					# query grabs all the episode details

			if ep_details.has_key('episodedetails'):						# continue only if there are details
				ep_details = ep_details['episodedetails']
				episode    = ("%.2d" % float(ep_details['episode']))
				season     = "%.2d" % float(ep_details['season'])
				episodeno  = "s%se%s" %(season,episode)
				rating     = str(round(float(ep_details['rating']),1))

				if ep_details['resume']['position'] and ep_details['resume']['total']:
					resume = "true"
					played = '%s%%'%int((float(ep_details['resume']['position']) / float(ep_details['resume']['total'])) * 100)
				else:
					resume = "false"
					played = '0%'

				art = ep_details['art']

				#if ep_details['playcount'] >= 1:
				#	watched = "true"
				#else:
				#	watched = "false"
				#if not self.PLOT_ENABLE and watched == "false":
				#if watched == "false":
				#	plot = "* Plot hidden to avoid spoilers. *"
				#else:
				
				plot = ep_details['plot']
				
				#plot = ''
				#path = self.media_path(ep_details['file'])
				#play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')'
				#streaminfo = self.media_streamdetails(ep_details['file'].encode('utf-8').lower(),ep_details['streamdetails'])

				WINDOW.setProperty("%s.%s.Title"                % ('LazyTV', TVShowID_), ep_details['title'])
				WINDOW.setProperty("%s.%s.Episode"              % ('LazyTV', TVShowID_), episode)
				WINDOW.setProperty("%s.%s.EpisodeNo"            % ('LazyTV', TVShowID_), episodeno)
				WINDOW.setProperty("%s.%s.Season"               % ('LazyTV', TVShowID_), season)
				WINDOW.setProperty("%s.%s.TVshowTitle"          % ('LazyTV', TVShowID_), ep_details['showtitle'])
				WINDOW.setProperty("%s.%s.Art(thumb)"           % ('LazyTV', TVShowID_), art.get('thumb',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.poster)"   % ('LazyTV', TVShowID_), art.get('tvshow.poster',''))
				WINDOW.setProperty("%s.%s.Resume"               % ('LazyTV', TVShowID_), resume)
				WINDOW.setProperty("%s.%s.PercentPlayed"        % ('LazyTV', TVShowID_), played)
				WINDOW.setProperty("%s.%s.CountWatchedEps"      % ('LazyTV', TVShowID_), str(wep))
				WINDOW.setProperty("%s.%s.CountUnwatchedEps"    % ('LazyTV', TVShowID_), str(uwep))
				WINDOW.setProperty("%s.%s.CountonDeckEps"       % ('LazyTV', TVShowID_), str(len(ondecklist)))
				WINDOW.setProperty("%s.%s.EpisodeID"            % ('LazyTV', TVShowID_), str(episodeid))
				WINDOW.setProperty("%s.%s.odlist"               % ('LazyTV', TVShowID_), str(ondecklist))
				WINDOW.setProperty("%s.%s.offlist"              % ('LazyTV', TVShowID_), str(offdecklist))
				WINDOW.setProperty("%s.%s.File"                 % ('LazyTV', TVShowID_), ep_details['file'])
				WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"   % ('LazyTV', TVShowID_), art.get('tvshow.fanart',''))

				#WINDOW.setProperty("%s.%s.Watched"                 % ('LazyTV', TVShowID_), watched)
				#WINDOW.setProperty("%s.%s.Path"                    % ('LazyTV', TVShowID_), path)
				#WINDOW.setProperty("%s.%s.Play"                    % ('LazyTV', TVShowID_), play)
				#WINDOW.setProperty("%s.%s.VideoCodec"              % ('LazyTV', TVShowID_), streaminfo['videocodec'])
				#WINDOW.setProperty("%s.%s.VideoResolution"         % ('LazyTV', TVShowID_), streaminfo['videoresolution'])
				#WINDOW.setProperty("%s.%s.VideoAspect"             % ('LazyTV', TVShowID_), streaminfo['videoaspect'])
				#WINDOW.setProperty("%s.%s.AudioCodec"              % ('LazyTV', TVShowID_), streaminfo['audiocodec'])
				#WINDOW.setProperty("%s.%s.AudioChannels"           % ('LazyTV', TVShowID_), str(streaminfo['audiochannels']))
				#WINDOW.setProperty("%s.%s.Art(tvshow.banner)"      % ('LazyTV', TVShowID_), art.get('tvshow.banner',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"   % ('LazyTV', TVShowID_), art.get('tvshow.clearlogo',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.clearart)"    % ('LazyTV', TVShowID_), art.get('tvshow.clearart',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"   % ('LazyTV', TVShowID_), art.get('tvshow.landscape',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), art.get('tvshow.characterart',''))
				#WINDOW.setProperty("%s.%s.Rating"                  % ('LazyTV', TVShowID_), rating)
				#WINDOW.setProperty("%s.%s.Runtime"                 % ('LazyTV', TVShowID_), str(int((ep_details['runtime'] / 60) + 0.5)))
				WINDOW.setProperty("%s.%s.Premiered"            % ('LazyTV', TVShowID_), ep_details['firstaired'])
				WINDOW.setProperty("%s.%s.Plot"                 % ('LazyTV', TVShowID_), plot)
				#WINDOW.setProperty("%s.%s.DBID"                    % ('LazyTV', TVShowID_), str(ep_details.get('episodeid')
					
			del ep_details

			if TVShowID_ != 'temp':
				Main.update_smartplaylist(TVShowID_)


	def swap_over(self, TVShowID_):
		log('swapover_started')

		WINDOW.setProperty("%s.%s.Title"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Title"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Episode"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Episode"                 % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.EpisodeNo"               % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.EpisodeNo"               % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Season"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Season"                  % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.TVshowTitle"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.TVshowTitle"             % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(thumb)"              % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(thumb)"              % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.poster)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.poster)"      % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Resume"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Resume"                  % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.PercentPlayed"           % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.PercentPlayed"           % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountWatchedEps"         % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountWatchedEps"         % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountonDeckEps"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountonDeckEps"          % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.EpisodeID"               % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.EpisodeID"               % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.odlist"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.odlist"                  % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.offlist"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.offlist"                 % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.File"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.File"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.fanart)"                   % ('LazyTV', 'temp')))

		#WINDOW.setProperty("%s.%s.Watched"                % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.watched"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Path"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Path"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Play"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Play"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoResolution"        % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoResolution"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoAspect"            % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoAspect"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioChannels"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioChannels"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.banner)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.banner)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearlogo)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.clearart)"    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearart)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.landscape)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.characterart)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Rating"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Rating"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Runtime"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Runtime"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Premiered"              % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Premiered"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Plot"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Plot"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.DBID"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.DBID"                   % ('LazyTV', 'temp')))

		Main.update_smartplaylist(TVShowID_)

		log('swapover_End')


	@classmethod
	def update_smartplaylist(self, tvshowid, remove = False):

		if maintainsmartplaylist and tvshowid != 'temp':

			log('updating playlist for: ' + str(tvshowid) + ', remove is ' + str(remove))

			playlist_file = os.path.join(videoplaylistlocation,'LazyTV.xsp')

			showname = WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', tvshowid))
			filename = os.path.basename(WINDOW.getProperty("%s.%s.File" % ('LazyTV', tvshowid)))

			if showname:

				# tries to read the file, if it cant it creates a new file
				try:
					f = open(playlist_file, 'r')
					all_lines = f.readlines()
					f.close()
				except:
					all_lines = []

				content = []
				line1 = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><smartplaylist type="episodes"><name>LazyTV</name><match>one</match>\n'
				linex = '<order direction="ascending">random</order></smartplaylist>'
				rawshowline = '<!--%s--><rule field="filename" operator="is"> <value>%s</value> </rule><!--END-->\n'

				xbmc.sleep(10)

				with open(playlist_file, 'w+') as g:

					found = False

					# creates the file if it doesnt exist or is empty
					if not all_lines:
						content.append(line1)
						content.append(rawshowline % (showname, filename))
						content.append(linex)

					# this will only occur if the file had contents
					for num, line in enumerate(all_lines):


						# showname found in line, replacing the file
						if ''.join(["<!--",showname,"-->"]) in line:
							if filename and not remove:
								log('playlist item updated: ' + str(showname) + ', ' + str(filename))

								content.append(rawshowline % (showname, filename))

								found = True

						# no entry found and this is the last line, create a new entry and finish off the file
						elif found == False and line == linex and not remove:
							log('entry not found, adding')

							content.append(rawshowline % (showname, filename))
							content.append(line)

						# showname not found, not final line, so just carry it over to the new file
						else:
							content.append(line)


					# writes the new stuff to the file
					guts = ''.join(content)
					g.write(guts)

			#log('playlist update complete')

		

def grab_settings(firstrun = False):
	global playlist_notifications
	global resume_partials
	global keep_logs
	global nextprompt
	global promptduration
	global randos
	global prevcheck
	global maintainsmartplaylist
	global promptdefaultaction

	playlist_notifications = True if __setting__("notify")  == 'true' else False
	resume_partials        = True if __setting__('resume_partials') == 'true' else False
	keep_logs              = True if __setting__('logging') == 'true' else False
	nextprompt             = True if __setting__('nextprompt') == 'true' else False
	nextprompt_or          = True if __setting__('nextprompt_or') == 'true' else False
	startup                = True if __setting__('startup') == 'true' else False
	promptduration         = int(float(__setting__('promptduration')))
	prevcheck              = True if __setting__('prevcheck') == 'true' else False
	promptdefaultaction    = int(float(__setting__('promptdefaultaction')))

	if promptduration == 0:
		promptduration = 1 / 1000.0

	if not maintainsmartplaylist:
		maintainsmartplaylist  = True if __setting__('maintainsmartplaylist') == 'true' else False
		if maintainsmartplaylist and not firstrun:
			for neep in Main.nepl:
				Main.update_smartplaylist(neep)

	else:
		maintainsmartplaylist  = True if __setting__('maintainsmartplaylist') == 'true' else False


	try:
		randos             = ast.literal_eval(__setting__('randos'))
	except:
		randos = []

	try:
		old_randos = ast.literal_eval(WINDOW.getProperty("LazyTV.randos"))
	except:
		old_randos = []

	if old_randos != randos and not firstrun:
		for r in randos:
			if r not in old_randos:
				log('adding rando')
				# if new rando, then add new randos to nepl and shuffle
				Main.add_to_nepl(r)
				Main.reshuffle_randos(sup_rand = [r])

		for oar in old_randos:
			if oar not in randos:
				log('removing rando')
				# if rando removed then check if rando has ondeck, if not then remove from nepl,
				try:
					has_ond = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" 	% ('LazyTV', oar)))
					log('odlist = ' + str(has_ond))
				except:
					has_ond = False

				# if so, then store the next ep
				if has_ond:
					log('adding ondeck ep for removed rando')
					retod    = WINDOW.getProperty("%s.%s.odlist" 						% ('LazyTV', oar))
					retoff   = WINDOW.getProperty("%s.%s.offlist" 					% ('LazyTV', oar))
					offd     = ast.literal_eval(retoff)
					ond      = ast.literal_eval(retod)
					tmp_wep  = int(WINDOW.getProperty("%s.%s.CountWatchedEps"         	% ('LazyTV', oar)).replace("''",'0')) + 1
					tmp_uwep = max(0, int(WINDOW.getProperty("%s.%s.CountUnwatchedEps"  % ('LazyTV', oar)).replace("''",'0')) - 1)

					Main.store_next_ep(ond[0], oar, ond, offd, tmp_uwep, tmp_wep)

				else:
					Main.remove_from_nepl(oar)

	# finally, set the new stored randos
	WINDOW.setProperty("LazyTV.randos", str(randos))

	log('randos = ' + str(randos))

	log('settings grabbed')


if ( __name__ == "__main__" ):
	xbmc.sleep(000) #testing delay for clean system
	log(' %s started' % str(__addonversion__))

	grab_settings(firstrun = True)											# gets the settings for the Addon

	Main()

	del Main
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % str(__addonversion__))


