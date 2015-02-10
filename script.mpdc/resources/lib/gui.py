#/*
# *      Copyright (C) 2010 lzoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */
import sys,os,time,re,traceback,threading
import xbmc,xbmcaddon,xbmcgui,xbmcplugin
import pmpd,xbmpc,albumart,playercontrols,cache
import mpdcdialog as dialog
__scriptid__ = 'script.mpdc'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__scriptname__ = __addon__.getAddonInfo('name')
#get actioncodes from keymap.xml
ACTION_SELECT_ITEM = 7
ACTIONS = dict({
	'3':'self._action_up()',
	'4':'self._action_down()',
	'9':'self._action_back()',
	'10':'self.exit()',
	'12':'self.client.pause()',
	'13':'self.client.stop()',
	'14':'self.client.next()',
	'15':'self.client.previous()',
	'34':'self._queue_item()',
	'79':'self.client.play()',
	'107':'self._action_mousemove()',
	'117':'self._context_menu()',
	'88':'self._volume(88)',
	'89':'self._volume(89)',
	'92':'self._action_back()'
	})
CLICK_ACTIONS = dict({
	'1401':'self._playlist_contextmenu()',
	'1101':'self._playlist_on_click()',
	'1301':'self._update_artist_browser(artist_item=self.getControl(1301).getSelectedItem())',
	'1201':'self._update_file_browser(browser_item=self.getControl(1201).getSelectedItem())',
	'2000':'self._playback_click()',
	'2502':'self._volume(89)',
	'2503':'self._volume(88)',
	'3000':'self._player_control_click()',
	'3101':'self._toggle_output()'
	})
PLAYER_CONTROL_ACTIONS = dict({
	'repeat0':'self.client.repeat(1)',
	'repeat1':'self.client.repeat(0)',
	'random0':'self.client.random(1)',
	'random1':'self.client.random(0)',
	'consume0':'self.client.consume(1)',
	'consume1':'self.client.consume(0)',
	'single0':'self.client.single(1)',
	'single1':'self.client.single(0)',
	'outputs0':'self._show_outputs()'
	})
PLAYBACK_ACTIONS={
	'pause':'self.client.play()',
	'play':'self.client.pause()',
	'stop':'self.client.stop()',
	'prev':'self.client.previous()',
	'next':'self.client.next()'
}
ACTION_VOLUME_UP=88
ACTION_VOLUME_DOWN=89
# control IDs
TAB_CONTROL=1000
VOLUME_GROUP = 2500
VOLUME_STATUS = 2501
CURRENT_PLAYLIST = 1101
FILE_BROWSER = 1201
PROFILE=101
PLAYLIST_BROWSER=1401
PLAYLIST_DETAILS=1403
PLAYLIST_SUM=1405
ARTIST_BROWSER=1301
SONG_INFO_PROGRESS=991
SONG_INFO_GROUP=99
SONG_INFO_TIME=992
SONG_INFO_ATRIST=993
SONG_INFO_ALBUM=994
SONG_INFO_ALBUM_IMAGE=995
PLAYBACK=2000
PLAYER_CONTROL=3000
OUTPUTS_SETTING=3100
OUTPUTS_LIST=3101
#String IDs
STR_STOPPED=__addon__.getLocalizedString(30003)
STR_PAUSED=__addon__.getLocalizedString(30004)
STR_NOT_CONNECTED=__addon__.getLocalizedString(30005)
STR_CONNECTED=__addon__.getLocalizedString(30011)
STR_PLAYING=__addon__.getLocalizedString(30006)
STR_PROFILE_NAME=__addon__.getLocalizedString(30002)
STR_CONNECTING_TITLE=__addon__.getLocalizedString(30015)
STR_DISCONNECTING_TITLE=__addon__.getLocalizedString(30017)
STR_GETTING_QUEUE=__addon__.getLocalizedString(30016)
STR_GETTING_PLAYLISTS=__addon__.getLocalizedString(30019)
STR_GETTING_ARTISTS=__addon__.getLocalizedString(30020)
STR_WAS_QUEUED=__addon__.getLocalizedString(30018)
STR_PLAYLIST_SAVED=__addon__.getLocalizedString(30021)
STR_SELECT_ACTION=__addon__.getLocalizedString(30022)
STR_LOAD_ADD=__addon__.getLocalizedString(30023)
STR_DELETE=__addon__.getLocalizedString(30024)
STR_LOAD_REPLACE=__addon__.getLocalizedString(30025)
STR_RENAME=__addon__.getLocalizedString(30026)
STR_Q__PLAYLIST_EXISTS=__addon__.getLocalizedString(30027)
STR_Q_OVERWRITE=__addon__.getLocalizedString(30028)
STR_UPDATE_LIBRARY=__addon__.getLocalizedString(30029)
STR_QUEUE_ADD=__addon__.getLocalizedString(30030)
STR_QUEUE_REPLACE=__addon__.getLocalizedString(30031)
STR_UPDATING_LIBRARY=__addon__.getLocalizedString(30032)
STR_REMOVE_FROM_QUEUE=__addon__.getLocalizedString(30036)
STR_SAVE_QUEUE_AS=__addon__.getLocalizedString(30037)
STR_CLEAR_QUEUE=__addon__.getLocalizedString(30038)
STR_PLAYING_STREAM=__addon__.getLocalizedString(30039)
STR_SERVER_STATS=__addon__.getLocalizedString(30042)
STR_SAVE_AS=__addon__.getLocalizedString(205)
STR_PLAYLIST_SUM=__addon__.getLocalizedString(30057)
STR_REMOVE_FROM_PLAYLIST=__addon__.getLocalizedString(30059)
STR_ADD_TO_PLAYLIST=__addon__.getLocalizedString(30060)
STR_SELECT_PLAYLIST=__addon__.getLocalizedString(30061)
STR_WAS_ADDED_TO_PLAYLIST=__addon__.getLocalizedString(30062)
STR_NEW_PLAYLIST=__addon__.getLocalizedString(30063)
class GUI ( xbmcgui.WindowXMLDialog ) :

	def __init__( self, *args, **kwargs ):
		self.addon = xbmcaddon.Addon(id=__scriptid__)
		self.time_polling=False
		if 'false' == self.addon.getSetting('use-idle'):
			self.client = pmpd.MopidyMPDClient(poll_time = ('true' == self.addon.getSetting('time-polling')))
		else:
			self.client = pmpd.PMPDClient(poll_time = ('true' == self.addon.getSetting('time-polling')))
		if 'true' == self.addon.getSetting('time-polling'):
			self.client.register_time_callback(self._handle_time_changes)
			self.time_polling = True
		self.client.register_callback(self._handle_changes)
		self.profile_id=args[3]
		self.skin=args[2]
		self.profile_name= self.addon.getSetting(self.profile_id+'_name')
		self.mpd_host = self.addon.getSetting(self.profile_id+'_mpd_host')
		self.mpd_port = self.addon.getSetting(self.profile_id+'_mpd_port')
		self.stream_url = self.addon.getSetting(self.profile_id+'_stream_url')
		if not self.stream_url == '' and not self.stream_url.startswith('http://'):
			self.stream_url = 'http://'+self.stream_url
		self.mpd_pass = self.addon.getSetting(self.profile_id+'_mpd_pass')
		self.fb_indexes = []
		self.ab_indexes = []
		self.cache = cache.MPDCache(__addon__,self.profile_id)
		if self.mpd_pass == '':
			self.mpd_pass = None
		self.is_play_stream = False
		if self.addon.getSetting(self.profile_id+'_play_stream') == 'true':
			self.is_play_stream = True
		art_dir = xbmc.translatePath(os.path.join( self.addon.getAddonInfo('profile'),'albums'))
		if not os.path.exists(art_dir):
			os.makedirs(art_dir)
		fetcher_setting = self.addon.getSetting('fetch-albums')
		if fetcher_setting == '1':
			self.art_fetcher = albumart.AllMusicFetcher(xbmc.translatePath(art_dir),self.addon.getSetting('fetch-cache') == 'true')
		elif fetcher_setting == '2':
			self.art_fetcher = albumart.LocalFetcher(xbmc.translatePath(self.addon.getSetting(self.profile_id+'_media_root')),self.addon.getSetting('fetch-search-image'))
		self.album_fetch_enabled = int(fetcher_setting) > 0
		self.last_album=''
		self.notification_enabled = self.addon.getSetting('notify') == 'true'
		self.controls = playercontrols.Controls(self.skin)
		self.stop_on_exit = self.addon.getSetting(self.profile_id+'_stop_on_exit') == 'true'
		self.play_on_queued= self.addon.getSetting(self.profile_id+'_play_on_queued') == 'true'

	def onFocus (self,controlId ):
		self.controlId=controlId
		if controlId == PLAYLIST_BROWSER:
			return self._update_playlist_details()
		if controlId == PLAYER_CONTROL:
			return self.getControl(OUTPUTS_SETTING).setVisible(False)

	def onInit (self ):
		self.getControl(OUTPUTS_SETTING).setVisible(False)
		self.getControl(SONG_INFO_ALBUM_IMAGE).setVisible(self.album_fetch_enabled)
		self.getControl( PROFILE ).setLabel(self.profile_name)
		self.controls.init_playback_controls(self.getControl(PLAYBACK))
		self._connect()

	def _connect(self):
		self.getControl(SONG_INFO_GROUP).setVisible(False)
		p = xbmcgui.DialogProgress()
		p.create(STR_CONNECTING_TITLE,STR_CONNECTING_TITLE+' '+self.mpd_host+':'+self.mpd_port)
		p.update(0)
		try:
			print 'Connecting  to  MPD ' + self.mpd_host + ':'+self.mpd_port 
			self.client.connect(self.mpd_host,int(self.mpd_port),self.mpd_pass)
		except:
			traceback.print_exc()
			print 'Cannot connect'
			p.close()
			formatted_lines = traceback.format_exc().splitlines()
			xbmcgui.Dialog().ok(STR_NOT_CONNECTED,formatted_lines[-1])
			self.exit()
			return
		print 'Connected'
		try:
			status = self.client.status()
			self.controls.init_player_controls(self.getControl(PLAYER_CONTROL),status)
			self._status_notify(self.mpd_host+':'+self.mpd_port,STR_CONNECTED)
			self._create_outputs()
			p.update(25,STR_GETTING_QUEUE)
			self._force_settings()
			self._handle_changes(self.client,['mixer','playlist','player','options'])
			self._handle_time_changes(self.client,status)
			p.update(50,STR_GETTING_PLAYLISTS)
			self._update_file_browser()
			self._update_playlist_browser(self.client)
			p.update(75,STR_GETTING_ARTISTS)
			self._update_artist_browser()
			p.close()
		except:
			p.close()
			traceback.print_exc()
			xbmcgui.Dialog().ok('MPD','An error occured, see log')
			self.exit()		

	def _force_settings(self):
		if self.addon.getSetting(self.profile_id+'_force_settings') == 'true':
			for name in ['force_repeat','force_single','force_random','force_consume']:
				value = self.addon.getSetting(self.profile_id+'_'+name)
				val = '0'
				if value == 'true':
					val = '1'
				cmd = name[name.rfind('_')+1:]
				self._exec_command('self.client.%s(%s)' % (cmd,val))
	def _update_current_queue(self,client=None):
		state = client.status()
		playlist = client.playlistinfo()
		current = client.currentsong()
		self.update_fields(current,['id'])
		current_id = current['id']
		index = self.getControl(CURRENT_PLAYLIST).getSelectedPosition()
		if index < 0:
			index = 0
		gen_index=0 # generate index value to each item
		self.getControl( CURRENT_PLAYLIST ).reset()
		for item in playlist:
			self._update_song_item(item)
			listitem = xbmcgui.ListItem( label=item['title'])
			listitem.setProperty( 'index', str(gen_index))
			listitem.setProperty( 'id', item['id'] )
			listitem.setProperty( 'artist', item['artist'] )
			listitem.setProperty( 'album', item['album'] )
			listitem.setProperty( 'track',item['track'] )
			listitem.setProperty( 'url', item['file'] )
			try:
				listitem.setProperty('track','%02d'%int(item['track']))
			except:
				pass
			if item['track'].find('/') >= 0:
				listitem.setProperty('track',item['track'].split('/')[0])
			gen_index=gen_index+1
			if not item['time'] == '':
				listitem.setProperty( 'time', self._format_time(item['time']) )
			if item['title'] == '' and item['artist'] == '' and item['album'] == '':
				listitem.setProperty( 'file' , item['file'] )
			if item['id'] == current_id:
				listitem.setIconImage(state['state']+'-item.png')
			self.getControl( CURRENT_PLAYLIST ).addItem( listitem )
			if current_id == '' and self.getControl(CURRENT_PLAYLIST).size() > 0:
				item = self.getControl(CURRENT_PLAYLIST).getListItem(0)
				item.setIconImage(state['state']+'-item.png')
		if self.getControl( CURRENT_PLAYLIST ).size() <= index:
			index = self.getControl( CURRENT_PLAYLIST ).size()-1
		self.getControl(CURRENT_PLAYLIST).selectItem(index)

	def _update_song_item(self,item):
		if 'xbmc_updated' in item: # do not update already updated item
			return
		self.update_fields(item,['artist','album','title','date','file','name','track','time'])
		item['xbmc_updated']=True
		if self._is_stream(item['file']):
			if not item['name'] == '':
				item['name'] = '%s (%s)'%(item['name'],item['file'])
			stream_info = item['title'].split(':')
			if len(stream_info) == 3:
				item['artist']=stream_info[0].strip()
				item['album']=stream_info[2].strip()
				item['title']=stream_info[1].strip()
				return
			stream_info = item['title'].split('-') # parse stream info reported by MPD
			if len(stream_info) == 3:
				item['artist']=stream_info[1].strip()
				item['album']=stream_info[0].strip()
				item['title']=stream_info[2].strip()

	def _is_stream(self,name):
		return name.startswith('http')

	def _create_outputs(self):
		try:
			self.getControl(OUTPUTS_LIST).reset()
			for output in self.client.outputs():
				item = xbmcgui.ListItem(label=output['outputname'])
				item.setProperty('outputenabled',output['outputenabled'])
				item.setProperty('outputid',output['outputid'])
				if output['outputenabled'] == '1':
					item.setIconImage('radiobutton-focus.png')
				else:
					item.setIconImage('radiobutton-nofocus.png')
				self.getControl(OUTPUTS_LIST).addItem(item)
		except:
			traceback.print_exc()

	def _show_outputs(self):
		self.getControl(OUTPUTS_SETTING).setVisible(True)
		self.setFocus(self.getControl(OUTPUTS_LIST))

	def _toggle_output(self):
		item = self.getControl(OUTPUTS_LIST).getSelectedItem()
		if not item == None:
			outputid = item.getProperty('outputid')
			if item.getProperty('outputenabled') == '1':
				self.client.disableoutput(outputid)
			else:
				self.client.enableoutput(outputid)

	def _update_song_info(self,current, status):
		self.getControl(SONG_INFO_GROUP).setVisible(self.time_polling)	
		self._update_song_item(current)
		if self._is_stream(current['file']):
			self.getControl(SONG_INFO_ATRIST).setLabel(current['artist']+' - '+current['title'])
			self.getControl(SONG_INFO_ALBUM).setLabel(current['name'])
		else:
			if current['artist']=='' or current['title']=='':
				self.getControl(SONG_INFO_ATRIST).setLabel(current['file'])
			else:
				self.getControl(SONG_INFO_ATRIST).setLabel(current['artist']+' - '+current['title'])
			if isinstance(current['date'],str) and len(current['date']) > 3:
				self.getControl(SONG_INFO_ALBUM).setLabel(current['album']+' ('+current['date'][:4]+')')
			elif isinstance(current['date'],list) and len(current['date']) > 0:
				self.getControl(SONG_INFO_ALBUM).setLabel(current['album']+' ('+current['date'][0][:4]+')')
			else:
				self.getControl(SONG_INFO_ALBUM).setLabel(current['album'])
		if not self.album_fetch_enabled:
			return
		album_image = self.art_fetcher.get_image_file_name(current['artist'],current['album'],current['file'])
		if album_image == self.last_album:
			#do not update image, album is same as before
			return
		self.last_album = album_image
		image = self.art_fetcher.get_album_art(current['artist'],current['album'],current['file'])
		if not image == None:
			print 'Loading album art image %s' % image
			self.getControl(SONG_INFO_ALBUM_IMAGE).setVisible(True)
			self.getControl(SONG_INFO_ALBUM_IMAGE).setImage(image)
		else:
			self.getControl(SONG_INFO_ALBUM_IMAGE).setVisible(False)

	def _update_artist_browser(self,artist_item=None,client=None,back=False):		
		select_index=0
		index = self.getControl(ARTIST_BROWSER).getSelectedPosition()
		if client == None:
			client = self.client
		if artist_item==None:
			self.getControl(ARTIST_BROWSER).reset()
			artists = self.cache.getArtists()
			if [] == artists:
				artists = self.client.list('artist')
				artists.sort()
				self.cache.putArtists(artists)
			listitem = xbmcgui.ListItem(label='..')
			listitem.setIconImage('DefaultFolderBack.png')
			listitem.setProperty('type','')
			self.getControl(ARTIST_BROWSER).addItem(listitem)			
			for item in artists:
				if not item=='':
					listitem = xbmcgui.ListItem(label=item)
					listitem.setProperty('artist',item)
					listitem.setProperty('type','artist')
					listitem.setIconImage('DefaultMusicArtists.png')
					self.getControl(ARTIST_BROWSER).addItem(listitem)
			if back:
					if not self.ab_indexes == []:
						select_index = self.ab_indexes.pop()
			self.getControl(ARTIST_BROWSER).selectItem(select_index)
		else:
			typ = artist_item.getProperty('type')
			if typ =='file':
				return
			if typ == '':
				return self._update_artist_browser(back=True)
			else:
				if index == 0 or back:
					if not self.ab_indexes == []:
						select_index = self.ab_indexes.pop()
				else:
					self.ab_indexes.append(index)
				# *srl_2013-06-24_resets*
	                        srl_artist = artist_item.getProperty('artist')
        	                srl_artist_album = artist_item.getProperty('album')
				# *srl_2013-06-24_resets* end
				self.getControl(ARTIST_BROWSER).reset()
				if typ == 'artist':					
					# *srl_2013-06-24_resets* listitem = xbmcgui.ListItem(label='.. %s' % artist_item.getProperty('artist'))
                                        listitem = xbmcgui.ListItem(label='.. %s' % srl_artist)
					# *srl_2013-06-24_resets* end
					listitem.setIconImage('DefaultFolderBack.png')
					listitem.setProperty('type','')
					self.getControl(ARTIST_BROWSER).addItem(listitem)
					# *srl_2013-06-24_resets* albums = self.client.list('album','artist',artist_item.getProperty('artist'))
                                        albums = self.client.list('album','artist',srl_artist)
					# *srl_2013-06-24_resets* end
					sorted_albums = {}
					spaces=''
					for item in albums:
						# *srl_2013-06-24_resets* date = self.client.list('date','album',item,'artist',artist_item.getProperty('artist'))
                                                date = self.client.list('date','album',item,'artist',srl_artist)
						# *srl_2013-06-24_resets* end
						date = date[0]
						if date =='':
							date = spaces
							spaces = spaces+' '
						sorted_albums[date[:4]] = item
					for item in sorted(sorted_albums,reverse=True):
						listitem = xbmcgui.ListItem(label=sorted_albums[item])
						# *srl_2013-06-24_resets* listitem.setProperty('artist',artist_item.getProperty('artist'))
                                                listitem.setProperty('artist',srl_artist)
						# *srl_2013-06-24_resets* end
						listitem.setProperty('type','album')
						listitem.setProperty('album',sorted_albums[item])
						listitem.setIconImage('DefaultMusicAlbums.png')
						listitem.setProperty( 'time', item )
						self.getControl(ARTIST_BROWSER).addItem(listitem)
				elif typ == 'album':
					# *srl_2013-06-24_resets* listitem = xbmcgui.ListItem(label='..  %s - %s'%(artist_item.getProperty('artist'),artist_item.getProperty('album')))
                                        listitem = xbmcgui.ListItem(label='..  %s - %s'%(srl_artist,srl_artist_album))
					# *srl_2013-06-24_resets* end
					listitem.setProperty('type','artist')
					listitem.setIconImage('DefaultFolderBack.png')
                                        # *srl_2013-06-24_resets* listitem.setProperty('artist',artist_item.getProperty('artist'))
 					listitem.setProperty('artist',srl_artist)
					# *srl_2013-06-24_resets* end
					self.getControl(ARTIST_BROWSER).addItem(listitem)
					# *srl_2013-06-24_resets* for item in self.client.find('artist',artist_item.getProperty('artist'),'album',artist_item.getProperty('album')):
                                        for item in self.client.find('artist',srl_artist,'album',srl_artist_album):
					# *srl_2013-06-24_resets* end
						listitem = xbmcgui.ListItem(label=item['title'])
						# *srl_2013-06-24_resets* listitem.setProperty('artist',artist_item.getProperty('artist'))
                                                listitem.setProperty('artist',srl_artist)
						# *srl_2013-06-24_resets* end
						listitem.setProperty('type','file')
						listitem.setProperty('file',item['file'])
						# *srl_2013-06-24_resets* listitem.setProperty('album',artist_item.getProperty('album'))
                                                listitem.setProperty('album',srl_artist_album)
						# *srl_2013-06-24_resets* end
						listitem.setProperty( 'time', self._format_time(item['time']) )
						listitem.setIconImage('DefaultAudio.png')
						self.getControl(ARTIST_BROWSER).addItem(listitem)
			self.getControl(ARTIST_BROWSER).selectItem(select_index)

	def _volume(self,action):
		if self._can_volume:
			volume = int(self.client.status()['volume'])
			if action == ACTION_VOLUME_DOWN:
				volume = volume - 5
			elif action == ACTION_VOLUME_UP:
				volume = volume + 5
			if volume >=0 and volume <=100:
				self.client.setvol(volume)

	def _update_playlist_browser(self,client):
		pos = self.getControl(PLAYLIST_BROWSER).getSelectedPosition()
		self.getControl(PLAYLIST_BROWSER).reset()
		self.playlists = []
		try:
			self.playlists = sorted(client.listplaylists(), key=lambda pls: pls['playlist'])
		except:
			#in case server does not support this command
			pass
		for item in self.playlists:
			item['data'] = client.listplaylistinfo(item['playlist'])
			time = 0
			tracks = 0
			for song in item['data']:
				self._update_song_item(song)
				if not song['time'] == '':
					time = time + int(song['time'])
				tracks = tracks + 1
			item['time'] = self._format_time2(time)
			item['tracks']=tracks
			listitem = xbmcgui.ListItem(label=item['playlist'])
			listitem.setIconImage('DefaultPlaylist.png')
			self.getControl(PLAYLIST_BROWSER).addItem(listitem)
		self.getControl(PLAYLIST_BROWSER).selectItem(pos)
		self._update_playlist_details(force=True,position=pos)

	def _playlists_as_array(self):
		ret = [STR_NEW_PLAYLIST]
		for item in self.playlists:
			pl = ('%s ('+STR_PLAYLIST_SUM+')') % (item['playlist'],item['tracks'],item['time'])
			ret.append(pl)
		return ret
	def _update_playlist_details(self,force=False,position=-1):
		if position > 0:
			item = self.getControl(PLAYLIST_BROWSER).getListItem(position)
		else:
			item = self.getControl(PLAYLIST_BROWSER).getSelectedItem()
		if len(self.playlists) == 0:
			self.getControl(PLAYLIST_DETAILS).reset()
			self.getControl(PLAYLIST_SUM).setLabel('')
			return
		if not item == None:
			for playlist in self.playlists:
				if playlist['playlist'] == item.getLabel():
					details = self.getControl(PLAYLIST_DETAILS)
					if details.size() > 0 and not force:
						if details.getListItem(0).getProperty('playlist') == item.getLabel():
							return
					lastpos = details.getSelectedPosition()
					details.reset()
					self.getControl(PLAYLIST_SUM).setLabel(STR_PLAYLIST_SUM % (playlist['tracks'],playlist['time']))
					index = 0
					listitems = []
					for track in playlist['data']:
						listitem = xbmcgui.ListItem(label=self._current_song(track))
						listitem.setProperty('playlist',item.getLabel())
						listitem.setProperty('file',track['file'])
						listitem.setIconImage('DefaultAudio.png')
						listitem.setProperty('pos',str(index))
						index+=1
						listitems.append(listitem)
					details.addItems(listitems)
					details.selectItem(lastpos)
		

	def _update_file_browser(self,browser_item=None,client=None,back=False):
		select_index = 0
		index = self.getControl(FILE_BROWSER).getSelectedPosition()
		firstitem= None
		if client==None:
			client = self.client
		if browser_item == None:
			self.getControl(FILE_BROWSER).reset()
			dirs = client.lsinfo()
			listitem = xbmcgui.ListItem( label='..')
			listitem.setProperty('directory','')
			listitem.setIconImage('DefaultFolderBack.png')
			firstitem = listitem
		elif browser_item.getProperty('type') == 'file':
			return
		else:
			if index == 0 or back:
				if not self.fb_indexes == []:
					select_index = self.fb_indexes.pop()
			else:
				self.fb_indexes.append(index)
			# *srl_2013-06-24_resets* self.getControl(FILE_BROWSER).reset()
			# uri = browser_item.getProperty('directory')
                        uri = browser_item.getProperty('directory')
                        self.getControl(FILE_BROWSER).reset()
			# *srl_2013-06-24_resets* end
			dirs = client.lsinfo(uri)
			listitem = xbmcgui.ListItem( label='..')
			listitem.setProperty('directory',os.path.dirname(uri))
			listitem.setIconImage('DefaultFolderBack.png')
			firstitem = listitem
		file_items = []
		dir_items = []
		for item in dirs:
			if 'directory' in item:
				listitem = xbmcgui.ListItem( label=os.path.basename(item['directory']))
				listitem.setProperty('type','directory')
				listitem.setProperty('directory',item['directory'])
				listitem.setIconImage('DefaultFolder.png')
				dir_items.append(listitem)
			elif 'file' in item:
				listitem = xbmcgui.ListItem( label=os.path.basename(item['file']))
				listitem.setProperty('type','file')
				listitem.setProperty('directory',os.path.dirname(item['file']))
				listitem.setProperty('file',item['file'])
				listitem.setIconImage('DefaultAudio.png')
				file_items.append(listitem)
		dir_items = sorted(dir_items,key=lambda i:i.getLabel())
		if not firstitem == None:
			dir_items.insert(0,firstitem)
		for i in sorted(file_items,key=lambda i:i.getLabel()):
			dir_items.append(i)
		self.getControl(FILE_BROWSER).addItems(dir_items)
		self.getControl(FILE_BROWSER).selectItem(select_index)

	def _handle_time_changes(self,poller_client,status):
		if not status['state'] == 'stop' and self.time_polling:
			time = status['time'].split(':')
			if float(time[1])>0:
				percent = float(time[0]) / (float(time[1])/100 )
				self.getControl(SONG_INFO_PROGRESS).setPercent(percent)
				self.getControl(SONG_INFO_TIME).setLabel(self._format_time(time[0])+' - '+self._format_time(time[1]))
			else:
				self.getControl(SONG_INFO_PROGRESS).setPercent(0)
				self.getControl(SONG_INFO_TIME).setLabel('')

	def _update_volume(self,state):
		if state['volume']=='-1':
			self.getControl(VOLUME_GROUP).setVisible(False)
			self._can_volume=False
		else:
			self._can_volume=True
			self.getControl(VOLUME_GROUP).setVisible(True)
			self.getControl(VOLUME_STATUS).setPercent(int(state['volume']))

	def _update_player_controls(self,current,state):
		self.controls.update_playback_controls(self.getControl(PLAYBACK),state)
		if state['state'] =='play':
			self._status_notify(self._current_song(current),STR_PLAYING)
			self.update_playlist('play',current)
		elif state['state'] == 'pause':
			self._status_notify(self._current_song(current),STR_PAUSED)
			self.update_playlist('pause',current)
		elif state['state'] == 'stop':
			self._status_notify(STR_STOPPED)
			self.update_playlist('stop',current)

	def _handle_changes(self,poller_client,changes):
		state = poller_client.status()
#		print state
		print 'Handling changes - ' + str(changes)
		for change in changes:
			if change =='mixer':
				self._update_volume(state)
			if change == 'player':
				current = poller_client.currentsong()
				self._update_player_controls(current,state)
				self._update_song_info(current,state)
			if change == 'options':
				self.controls.update_player_controls(self.getControl(PLAYER_CONTROL),state)
			if change == 'stored_playlist':
				self._update_playlist_browser(poller_client)
			if change == 'database':
				self.cache.clear()
				self._update_file_browser(client=poller_client)
				self._update_artist_browser(client=poller_client)
			if change == 'playlist':
				self._update_current_queue(client=poller_client)
			if change == 'output':
				self._create_outputs()
#		print 'Changes handled'

	def _format_time(self,time):
		return '%d:%02d' % ((int(time) / 60 ),(int(time) % 60))
	def _format_time2(self,time):
		minutes = (int(time) - ((int(time) / 3600) * 3600))/60
		return '%d:%d:%02d' % ((int(time) / 3600 ),minutes,(int(time) % 60))

	def toggleVisible(self,cFrom,cTo):
		self.getControl( cFrom ).setVisible(False)
		self.getControl( cTo ).setVisible(True)
	
	def update_fields(self,obj,fields):
		for field in fields:
			if not field in obj:
				obj[field]=''

	def _current_song(self,current) :
		self._update_song_item(current)
		try:
			if current['title'] == '' and current['artist'] == '' and current['album'] == '':
				ret = current['file']
			else:
				ret = current['artist'] + ' - ' + current['album'] + ' - ' + current['title']
			return ret.decode('utf-8') 
		except:
			return 'Error encoding current song'

	def update_playlist(self,state,current) :
		self.update_fields(current,['id'])
		itemid = current['id']
		playlist = self.getControl(CURRENT_PLAYLIST)
		for i in range(0,playlist.size()):
			item = playlist.getListItem(i)
			item.setIconImage('')
			if item.getProperty('id') == itemid:
				item.setIconImage(state+'-item.png')
				playlist.selectItem(int(item.getProperty('index')))
		if itemid == '' and self.getControl(CURRENT_PLAYLIST).size() > 0:
			item = self.getControl(CURRENT_PLAYLIST).getListItem(0)
			item.setIconImage(state+'-item.png')
		if state == 'play':
			self._play_stream()	

	def _queue_item(self,replace=False,play=False):
		if replace:
			stopped = self._stop_if_playing()
			self.client.stop()
			self.client.clear()
			return self._queue_item(play=stopped or play)
		if self.getFocusId() == PLAYLIST_DETAILS:
			item = self.getControl(PLAYLIST_DETAILS).getSelectedItem()
			if not item == None:
				self.client.add(item.getProperty('file'))
				self._status_notify(item.getProperty('file'),STR_WAS_QUEUED)
		if self.getFocusId() == FILE_BROWSER:
				item = self.getControl(FILE_BROWSER).getSelectedItem()
				uri = item.getProperty(item.getProperty('type'))
				if not uri=='':
					self.client.add(uri)
					self._status_notify(uri,STR_WAS_QUEUED)
		if self.getFocusId() == ARTIST_BROWSER:
			item = self.getControl(ARTIST_BROWSER).getSelectedItem()
			typ = item.getProperty('type')
			if typ == '':
				return
			if typ == 'file':
				self.client.add(item.getProperty(typ))
				self._status_notify(item.getProperty(typ),STR_WAS_QUEUED)
			else:
				if typ == 'artist':
					found = self.client.find('artist',item.getProperty('artist'))
					status = item.getProperty('artist')
				elif typ == 'album':
					found = self.client.find('artist',item.getProperty('artist'),'album',item.getProperty('album'))
					status = item.getProperty('artist')
				if not found == []:
					self.client.try_command('add')
					self.client.command_list_ok_begin()
					for f_item in found:
						self.client.add(f_item['file'])
					self.client.command_list_end()
					self._status_notify(status,STR_WAS_QUEUED)
		if play or self.play_on_queued:
			self.client.play()

	def _context_menu(self):
		if self.getFocusId() == PLAYLIST_BROWSER:
			return self._playlist_contextmenu()
		if self.getFocusId() == PLAYLIST_DETAILS:
			return self._playlist_details_contextmenu()
		if self.getFocusId() == CURRENT_PLAYLIST:
			if self.getControl(CURRENT_PLAYLIST).size() < 1:
				return
			ret = self.dialog(STR_SELECT_ACTION,[STR_REMOVE_FROM_QUEUE,STR_SAVE_QUEUE_AS,STR_CLEAR_QUEUE,STR_ADD_TO_PLAYLIST])
			if ret==0:
				self.client.deleteid(self.getControl(CURRENT_PLAYLIST).getSelectedItem().getProperty('id'))
			if ret==1:
				self._save_queue_as()
			if ret==2:
				self._clear_queue()
			if ret==3:
				playlist = self._select_playlist_dialog()
				if not playlist == None:
					item = self.getControl(CURRENT_PLAYLIST).getSelectedItem()
					if not item == None:
						uri = item.getProperty('url')
						self.client.playlistadd(playlist,uri)
						self._status_notify(uri,STR_WAS_ADDED_TO_PLAYLIST%playlist)
		if self.getFocusId() == ARTIST_BROWSER:
			if self.getControl(ARTIST_BROWSER).size() < 2:
				return
			ret = self.dialog(STR_SELECT_ACTION,[STR_QUEUE_ADD,STR_QUEUE_REPLACE,STR_ADD_TO_PLAYLIST])
			if ret == 0:
				self._queue_item()
			if ret == 1:
				self._queue_item(replace=True)
			if ret == 2:
				playlist = self._select_playlist_dialog()
				if not playlist == None:
					item = self.getControl(ARTIST_BROWSER).getSelectedItem()
					typ = item.getProperty('type')
					if typ == 'file':
						self.client.playlistadd(playlist,item.getProperty(typ))
						self._status_notify(item.getProperty(typ),STR_WAS_ADDED_TO_PLAYLIST%playlist)
					else:
						if typ == 'artist':
							found = self.client.find('artist',item.getProperty('artist'))
							status = item.getProperty('artist')
						elif typ == 'album':
							found = self.client.find('artist',item.getProperty('artist'),'album',item.getProperty('album'))
							status = item.getProperty('artist')
						if not found == []:
							self.client.try_command('add')
							self.client.command_list_ok_begin()
							for f_item in found:
								self.client.playlistadd(playlist,f_item['file'])
							self.client.command_list_end()
							self._status_notify(status,STR_WAS_ADDED_TO_PLAYLIST%playlist)

		if self.getFocusId() == FILE_BROWSER:
			if self.getControl(FILE_BROWSER).size() < 2:
				return
			ret = self.dialog(STR_SELECT_ACTION,[STR_QUEUE_ADD,STR_QUEUE_REPLACE,STR_ADD_TO_PLAYLIST,STR_UPDATE_LIBRARY])
			if ret == 0:
				self._queue_item()
			if ret == 1:
				self._queue_item(replace=True)
			if ret == 2:
				playlist = self._select_playlist_dialog()
				if not playlist == None:
					item = self.getControl(FILE_BROWSER).getSelectedItem()
					uri = item.getProperty(item.getProperty('type'))
					self.client.playlistadd(playlist,uri)
					self._status_notify(uri,STR_WAS_ADDED_TO_PLAYLIST%playlist)
			if ret == 3:
				item = self.getControl(FILE_BROWSER).getSelectedItem()
				uri = item.getProperty(item.getProperty('type'))
				if uri =='':
					self.client.update()
				else:
					self.client.update(uri)
				self._status_notify(uri,STR_UPDATING_LIBRARY)

	def _select_playlist_dialog(self):
		ret = xbmcgui.Dialog().select(STR_SELECT_PLAYLIST,self._playlists_as_array())
		if ret==0:
			kb = xbmc.Keyboard('',STR_SELECT_PLAYLIST,False)
			kb.doModal()
			if kb.isConfirmed():
				if self._exists_playlist(kb.getText()):
					dialog = xbmcgui.Dialog()
					ret = dialog.yesno(STR_Q__PLAYLIST_EXISTS, STR_Q_OVERWRITE)
					if ret:
						self.client.rm(kb.getText())
						return kb.getText()
				else:
					return kb.getText()
		if ret > 0:
			return self.playlists[ret-1]['playlist']

	def exit(self):
		self.disconnect()
		self.close()
	def _action_up(self):
		if self.getFocusId() == PLAYLIST_BROWSER:
			self._update_playlist_details()
	def _action_down(self):
		if self.getFocusId() == PLAYLIST_BROWSER:
			self._update_playlist_details()
	def _action_mousemove(self):
		if self.getFocusId() == PLAYLIST_BROWSER:
			self._update_playlist_details()
	def _action_back(self):
		if self.getFocusId() == FILE_BROWSER:
			if self.getControl(FILE_BROWSER).getSelectedPosition() == 0:
				self.setFocus(self.getControl(TAB_CONTROL))
			else:
				self._update_file_browser(browser_item=self.getControl(FILE_BROWSER).getListItem(0),back=True)
		elif self.getFocusId() == PLAYLIST_DETAILS:
			self.setFocus(self.getControl(PLAYLIST_BROWSER))
		elif self.getFocusId() == ARTIST_BROWSER:
			if self.getControl(ARTIST_BROWSER).getSelectedPosition() == 0:
				self.setFocus(self.getControl(TAB_CONTROL))
			else:
				self._update_artist_browser(artist_item=self.getControl(ARTIST_BROWSER).getListItem(0),back=True)
		elif self.getFocusId() == TAB_CONTROL:
			self.exit()
		elif self.getFocusId() in [PLAYBACK,PLAYER_CONTROL,PLAYLIST_BROWSER,CURRENT_PLAYLIST]:
			self.setFocus(self.getControl(TAB_CONTROL))

	def _play_stream(self):
		if self.is_play_stream and not self.stream_url=='':
			player = xbmc.Player(xbmc.PLAYER_CORE_MPLAYER)
			if player.isPlayingVideo():
				return
			if player.isPlayingAudio():
				if not player.getPlayingFile() == self.stream_url:
					self._start_media_player()
			else:
				self._start_media_player()

	def _start_media_player(self):
		print 'Playing '+self.stream_url
		icon =  os.path.join(__addon__.getAddonInfo('path'),'icon.png')
		self._status_notify(self.stream_url,STR_PLAYING_STREAM)
		xbmc.executebuiltin('PlayMedia(%s)' % self.stream_url)

	def _status_notify(self,message,title=None):
		try:
			if title==None:
				title = __scriptname__
			if self.notification_enabled:
				icon =  os.path.join(__addon__.getAddonInfo('path'),'icon.png')
				xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (title.encode('UTF-8','ignore'),message.encode('UTF-8','ignore'),icon))
		except:
			print 'Unable to display notify message'
			traceback.print_exc()

	def disconnect(self):
		try:
			if self.stop_on_exit:
				self.client.stop()
		except:
			pass
		p = xbmcgui.DialogProgress()
		p.create(STR_DISCONNECTING_TITLE)
		p.update(0)
		self.client.disconnect()
		p.close()

	def _playlist_contextmenu(self):
		if self.getControl(PLAYLIST_BROWSER).size() < 1:
			return
		ret = self.dialog(STR_SELECT_ACTION,[STR_LOAD_ADD,STR_LOAD_REPLACE,STR_RENAME,STR_DELETE])
		playlist = self.getControl(PLAYLIST_BROWSER).getSelectedItem().getLabel()
		if ret == 0:
			self.client.load(playlist)
			self._status_notify('Playlist %s'%playlist,STR_WAS_QUEUED)
			if self.play_on_queued:
				self.client.play()
		elif ret == 1:
			stopped = self._stop_if_playing()
			self.client.stop()
			self.client.clear()
			self.client.load(playlist)
			self._status_notify('Playlist %s'%playlist,STR_WAS_QUEUED)
			if stopped or self.play_on_queued:
				self.client.play()
		elif ret == 2:
				kb = xbmc.Keyboard(playlist,STR_RENAME,False)
				kb.doModal()
				if kb.isConfirmed():
					if playlist==kb.getText():
						return
					if self._exists_playlist(kb.getText()):
						dialog = xbmcgui.Dialog()
						ret = dialog.yesno(STR_Q__PLAYLIST_EXISTS, STR_Q_OVERWRITE)
						if ret:
							self.client.rm(kb.getText())
							self.client.rename(playlist,kb.getText())
							self._status_notify(kb.getText(),STR_PLAYLIST_SAVED)
					else:
						self.client.rename(playlist,kb.getText())
						self._status_notify(kb.getText(),STR_PLAYLIST_SAVED)
		elif ret == 3:
			self.client.rm(playlist)
	def _playlist_details_contextmenu(self):
		track = self.getControl(PLAYLIST_DETAILS).getSelectedItem()
		if not track == None:
			ret = self.dialog(STR_SELECT_ACTION,[STR_QUEUE_ADD,STR_QUEUE_REPLACE,STR_REMOVE_FROM_PLAYLIST])
			if ret == 0:
				self._queue_item()
			elif ret == 1:
				self._queue_item(replace=True)
			elif ret == 2:
				self.client.playlistdelete(track.getProperty('playlist'),track.getProperty('pos'))

	def dialog(self,title,list):
		d = dialog.Dialog('menu-dialog.xml',__addon__.getAddonInfo('path'),self.skin,'0')
		d.list=list
		d.title = title
		d.doModal()
		return d.result

	def _clear_queue(self):
		self.client.try_command('clear')
		self.client.stop()
		self.client.clear()

	def _exists_playlist(self,playlist):
		playlists = self.getControl(PLAYLIST_BROWSER)
		for i in range(0,playlists.size()):
			item = playlists.getListItem(i)
			if item.getLabel() == playlist:
				return True
		return False

	def _playback_click(self):
		item = self.getControl(PLAYBACK).getSelectedItem()
		action = item.getProperty('label')
		if action in PLAYBACK_ACTIONS:
			self._exec_command(PLAYBACK_ACTIONS[action])

	def _player_control_click(self):
		item = self.getControl(PLAYER_CONTROL).getSelectedItem()
		action = item.getProperty('label')+item.getProperty('state')
		if action in PLAYER_CONTROL_ACTIONS:
			self._exec_command(PLAYER_CONTROL_ACTIONS[action])

	def _save_queue_as(self):
		kb = xbmc.Keyboard('playlist',STR_SAVE_AS,False)
		kb.doModal()
		if kb.isConfirmed():
			if self._exists_playlist(kb.getText()):
				dialog = xbmcgui.Dialog()
				ret = dialog.yesno(STR_Q__PLAYLIST_EXISTS, STR_Q_OVERWRITE)
				if ret:
					self.client.rm(kb.getText())
					self.client.save(kb.getText())
					self._status_notify(kb.getText(),STR_PLAYLIST_SAVED)
			else:	
				self.client.save(kb.getText())
				self._status_notify(kb.getText(),STR_PLAYLIST_SAVED)

	def _stop_if_playing(self):
		status = self.client.status()
		if status['state'] == 'play':
			self.client.stop()
			return True
		return False

	def _playlist_on_click(self):
		seekid = self.getControl( CURRENT_PLAYLIST ).getSelectedItem().getProperty('id')
		status = self.client.status()
		if status['state'] == 'play' and status['songid'] == seekid:
			self.client.pause()
		elif status['state'] == 'pause' and status['songid'] == seekid:
			self.client.play()
		else:
			self.client.seekid(seekid,0)
			
	def onAction(self, action):
		# print 'Action id=%s buttonCode=%s amount1=%s amount2=%s' % (action.getId(),action.getButtonCode(),action.getAmount1(),action.getAmount2())
		if str(action.getId()) in ACTIONS:
			command = ACTIONS[str(action.getId())]
#			print 'action: '+command
			self._exec_command(command)

	def onClick( self, controlId ):
		if str(controlId) in CLICK_ACTIONS:
			command = CLICK_ACTIONS[str(controlId)]
#			print 'click action: '+command
			self._exec_command(command)

	def _exec_command(self,command):
		try:
			exec(command)
		except xbmpc.CommandError:
			traceback.print_exc()
			formatted_lines = traceback.format_exc().splitlines()
			xbmcgui.Dialog().ok('MPD',formatted_lines[-1])
		except xbmpc.ProtocolError:
			traceback.print_exc()
			self.disconnect()
			self._status_notify(STR_NOT_CONNECTED)
		except xbmpc.ConnectionError:
			traceback.print_exc()
			self.disconnect()
			self._status_notify(STR_NOT_CONNECTED)
