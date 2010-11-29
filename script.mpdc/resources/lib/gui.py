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
import sys,os,time,re,traceback
import xbmc,xbmcaddon,xbmcgui,xbmcplugin
import pmpd,mpd,dialog
__scriptid__ = 'script.mpdc'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__scriptname__ = __addon__.getAddonInfo('name')
#get actioncodes from keymap.xml
ACTION_SELECT_ITEM = 7
ACTIONS = dict({
	'9':'self._action_back()',
	'10':'self.exit()',
	'12':'self.client.pause()',
	'13':'self.client.stop()',
	'14':'self.client.next()',
	'15':'self.client.previous()',
	'34':'self._queue_item()',
	'79':'self.client.play()',
	'117':'self._context_menu()',
	'88':'self._volume(88)',
	'89':'self._volume(89)'
	})
CLICK_ACTIONS = dict({
	'668':'self.client.play()',
	'670':'self.client.pause()',
	'667':'self.client.stop()',
	'666':'self.client.previous()',
	'669':'self.client.next()',
	'700':'self.client.repeat(1)',
	'701':'self.client.repeat(0)',
	'702':'self.client.random(1)',
	'703':'self.client.random(0)',
	'704':'self._consume_mode_toggle()',
	'1401':'self._playlist_contextmenu()',
	'1101':'self._playlist_on_click()',
	'1301':'self._update_artist_browser(artist_item=self.getControl(1301).getSelectedItem())',
	'1201':'self._update_file_browser(browser_item=self.getControl(1201).getSelectedItem())',
	'671':'self._set_volume()'
	})
ACTION_VOLUME_UP=88
ACTION_VOLUME_DOWN=89
# control IDs
STATUS = 100
SERVER_STATS=1009
PLAY = 668
PAUSE = 670
PREV = 666
STOP = 667
NEXT = 669
VOLUME = 671 
REPEAT_OFF = 700
REPEAT_ON = 701
SHUFFLE_OFF = 702
SHUFFLE_ON = 703
CURRENT_PLAYLIST = 1101
FILE_BROWSER = 1201
PROFILE=101
PLAYLIST_BROWSER=1401
ARTIST_BROWSER=1301
RB_CONSUME_MODE=704
SONG_INFO_PROGRESS=991
SONG_INFO_GROUP=99
SONG_INFO_TIME=992
SONG_INFO_ATRIST=993
SONG_INFO_ALBUM=994
#String IDs
STR_STOPPED=__addon__.getLocalizedString(30003)
STR_PAUSED=__addon__.getLocalizedString(30004)
STR_NOT_CONNECTED=__addon__.getLocalizedString(30005)
STR_CONNECTED_TO=__addon__.getLocalizedString(30011)
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
class GUI ( xbmcgui.WindowXMLDialog ) :
	
	def __init__( self, *args, **kwargs ):
		self.addon = xbmcaddon.Addon(id=__scriptid__)
		self.time_polling=False
		if 'true' == self.addon.getSetting('time-polling'):
			self.client = pmpd.PMPDClient(poll_time=True)
			self.client.register_time_callback(self._handle_time_changes)
			self.time_polling = True
		else:
			self.client = pmpd.PMPDClient()
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
		if self.mpd_pass == '':
			self.mpd_pass = None
		self.is_play_stream = False
		if self.addon.getSetting(self.profile_id+'_play_stream') == 'true':
			self.is_play_stream = True
		
	def onFocus (self,controlId ):
		self.controlId=controlId

	def onInit (self ):
		self.getControl( PAUSE ).setVisible( False )
		self.getControl( PROFILE ).setLabel(self.profile_name)					
		self._connect()
	def _connect(self):
		self.getControl(SONG_INFO_GROUP).setVisible(False)
		p = xbmcgui.DialogProgress()
		p.create(STR_CONNECTING_TITLE,STR_CONNECTING_TITLE+' '+self.mpd_host+':'+self.mpd_port)
		p.update(0)
		try:				
			print 'Connecting  to  MPD ' + self.mpd_host + ':'+self.mpd_port 
			self.client.connect(self.mpd_host,int(self.mpd_port),self.mpd_pass)
		except mpd.CommandError:
			traceback.print_exc()
			formatted_lines = traceback.format_exc().splitlines()
			xbmcgui.Dialog().ok(STR_NOT_CONNECTED,formatted_lines[-1])
			self.exit()
			return
		except:
			self.getControl ( STATUS ).setLabel(STR_NOT_CONNECTED)
			traceback.print_exc()
			print 'Cannot connect'
			p.close()
			return
		print 'Connected'
		try:
			stats = self.client.stats()
			self.getControl(SERVER_STATS).setLabel(STR_SERVER_STATS % (stats['artists']+'\n',stats['albums']+'\n',stats['songs']+'\n',self._format_time2(stats['db_playtime'])))
			self.getControl ( STATUS ).setLabel(STR_CONNECTED_TO +' '+self.mpd_host+':'+self.mpd_port )
			p.update(25,STR_GETTING_QUEUE)
			self._handle_changes(self.client,['mixer','playlist','player','options'])
			self._handle_time_changes(self.client,self.client.status())
			p.update(50,STR_GETTING_PLAYLISTS)
			self._update_file_browser()
			self._update_playlist_browser(self.client.listplaylists())
			p.update(75,STR_GETTING_ARTISTS)
			self._update_artist_browser()
			p.close()
		except:
			p.close()
			traceback.print_exc()
			xbmcgui.Dialog().ok('MPD','An error occured, see log')
			self.exit()		

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
			self.update_fields(item,['title','artist','album','time'])
			listitem = xbmcgui.ListItem( label=item['title'])
			listitem.setProperty( 'index', str(gen_index))
			listitem.setProperty( 'id', item['id'] )
			listitem.setProperty( 'artist', item['artist'] )
			listitem.setProperty( 'album', item['album'] )
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

	def _update_song_info(self,current, status):
		self.getControl(SONG_INFO_GROUP).setVisible(self.time_polling)	
		self.update_fields(current,['artist','album','title','date','file'])
		if current['artist']=='' or current['title']=='':
			self.getControl(SONG_INFO_ATRIST).setLabel(current['file'])
		else:
			self.getControl(SONG_INFO_ATRIST).setLabel(current['artist']+' - '+current['title'])
		self.getControl(SONG_INFO_ALBUM).setLabel(current['album']+' ('+current['date']+')')
		
	def _update_artist_browser(self,artist_item=None,client=None,back=False):		
		select_index=0
		index = self.getControl(ARTIST_BROWSER).getSelectedPosition()
		if client == None:
			client = self.client
		if artist_item==None:
			self.getControl(ARTIST_BROWSER).reset()
			artists = self.client.list('artist')
			artists.sort()
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
				self.getControl(ARTIST_BROWSER).reset()
				if typ == 'artist':					
					listitem = xbmcgui.ListItem(label='..')
					listitem.setIconImage('DefaultFolderBack.png')
					listitem.setProperty('type','')
					self.getControl(ARTIST_BROWSER).addItem(listitem)
					for item in self.client.list('album',artist_item.getProperty('artist')):
						listitem = xbmcgui.ListItem(label=item)
						listitem.setProperty('artist',artist_item.getProperty('artist'))
						listitem.setProperty('type','album')
						listitem.setProperty('album',item)
						listitem.setIconImage('DefaultMusicAlbums.png')
						self.getControl(ARTIST_BROWSER).addItem(listitem)
				elif typ == 'album':
					listitem = xbmcgui.ListItem(label='..')
					listitem.setProperty('type','artist')
					listitem.setIconImage('DefaultFolderBack.png')
					listitem.setProperty('artist',artist_item.getProperty('artist'))
					self.getControl(ARTIST_BROWSER).addItem(listitem)
					for item in self.client.search('artist',artist_item.getProperty('artist'),'album',artist_item.getProperty('album')):
						listitem = xbmcgui.ListItem(label=item['title'])
						listitem.setProperty('artist',artist_item.getProperty('artist'))
						listitem.setProperty('type','file')
						listitem.setProperty('file',item['file'])
						listitem.setProperty('album',artist_item.getProperty('album'))
						listitem.setProperty( 'time', self._format_time(item['time']) )
						listitem.setIconImage('DefaultAudio.png')
						self.getControl(ARTIST_BROWSER).addItem(listitem)
			self.getControl(ARTIST_BROWSER).selectItem(select_index)

	def _volume(self,action):
		if self._can_volume:
			volume = int(self.client.status()['volume'])
			if action == ACTION_VOLUME_DOWN:
				self.client.setvol(volume - 5)
			elif action == ACTION_VOLUME_UP:
				self.client.setvol(volume + 5)

	def _update_playlist_browser(self,playlists):
		self.getControl(PLAYLIST_BROWSER).reset()
		for item in playlists:
			listitem = xbmcgui.ListItem(label=item['playlist'])
			listitem.setIconImage('DefaultPlaylist.png')
			self.getControl(PLAYLIST_BROWSER).addItem(listitem)
			
	def _update_file_browser(self,browser_item=None,client=None,back=False):
		select_index = 0		
		index = self.getControl(FILE_BROWSER).getSelectedPosition()
		if client==None:
			client = self.client				
		if browser_item == None:
			self.getControl(FILE_BROWSER).reset()
			dirs = client.lsinfo()
			listitem = xbmcgui.ListItem( label='..')
			listitem.setProperty('directory','')
			listitem.setIconImage('DefaultFolderBack.png')
			self.getControl(FILE_BROWSER).addItem(listitem)
		elif browser_item.getProperty('type') == 'file':
			return
		else:
			if index == 0 or back:
				if not self.fb_indexes == []:
					select_index = self.fb_indexes.pop()			
			else:
				self.fb_indexes.append(index)
			self.getControl(FILE_BROWSER).reset()
			uri = browser_item.getProperty('directory')
			dirs = client.lsinfo(uri)
			listitem = xbmcgui.ListItem( label='..')
			listitem.setProperty('directory',os.path.dirname(uri))
			listitem.setIconImage('DefaultFolderBack.png')
			self.getControl(FILE_BROWSER).addItem(listitem)		
		for item in dirs:
			if 'directory' in item:
				listitem = xbmcgui.ListItem( label=os.path.basename(item['directory']))
				listitem.setProperty('type','directory')
				listitem.setProperty('directory',item['directory'])
				listitem.setIconImage('DefaultFolder.png')
				self.getControl(FILE_BROWSER).addItem(listitem)
			elif 'file' in item:
				listitem = xbmcgui.ListItem( label=os.path.basename(item['file']))			
				listitem.setProperty('type','file')
				listitem.setProperty('directory',os.path.dirname(item['file']))
				listitem.setProperty('file',item['file'])				
				listitem.setIconImage('DefaultAudio.png')
				self.getControl(FILE_BROWSER).addItem(listitem)
		self.getControl(FILE_BROWSER).selectItem(select_index)

	def _handle_time_changes(self,poller_client,status):
		if not status['state'] == 'stop' and self.time_polling:
			time = status['time'].split(':')
			percent = float(time[0]) / (float(time[1])/100 )
			self.getControl(SONG_INFO_PROGRESS).setPercent(percent)
			self.getControl(SONG_INFO_TIME).setLabel(self._format_time(time[0])+' - '+self._format_time(time[1]))

	def _update_volume(self,state):
		if state['volume']=='-1':
			self.getControl(VOLUME).setVisible(False)
			self._can_volume=False
		else:
			self._can_volume=True
			self.getControl(VOLUME).setVisible(True)
			self.getControl(VOLUME).setPercent(int(state['volume']))

	def _update_player_controls(self,current,state):
		if state['state'] =='play':
			self.toggleVisible( PLAY, PAUSE )
			self.getControl( STATUS ).setLabel(STR_PLAYING + ' : ' + self._current_song(current))
			self.update_playlist('play',current)
		elif state['state'] == 'pause':
			self.toggleVisible( PAUSE, PLAY )
			self.getControl( STATUS ).setLabel(STR_PAUSED + ' : ' + self._current_song(current))
			self.update_playlist('pause',current)
		elif state['state'] == 'stop':
			self.getControl( STATUS ).setLabel(STR_STOPPED)
			self.toggleVisible( PAUSE, PLAY )
			self.update_playlist('stop',current)

	def _handle_changes(self,poller_client,changes):
		state = poller_client.status()
#		print state
#		print poller_client.playlistid(state['songid'])
		print 'Handling changes - ' + str(changes)
		for change in changes:
			if change =='mixer':
				self._update_volume(state)
			if change == 'player':
				current = poller_client.currentsong()
				self._update_song_info(current,state)
				self._update_player_controls(current,state)
			if change == 'options':
				if state['repeat'] == '0':
					self.toggleVisible( REPEAT_ON, REPEAT_OFF )
				elif state['repeat'] == '1':
					self.toggleVisible( REPEAT_OFF, REPEAT_ON )
				if state['random'] == '0':
					self.toggleVisible( SHUFFLE_ON, SHUFFLE_OFF )
				elif state['random'] == '1':
					self.toggleVisible( SHUFFLE_OFF, SHUFFLE_ON )
				if state['consume'] == '1':
					self.getControl(RB_CONSUME_MODE).setSelected(True)
				else:
					self.getControl(RB_CONSUME_MODE).setSelected(False)					
			if change == 'stored_playlist':
				self._update_playlist_browser(poller_client.listplaylists())
			if change == 'database':
				self._update_file_browser(client=poller_client)
				self._update_artist_browser(client=poller_client)
			if change == 'playlist':
				self._update_current_queue(client=poller_client)
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
		self.update_fields(current,['artist','album','title'])
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
		playlist = 	self.getControl(CURRENT_PLAYLIST)
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
	
	def _queue_item(self):
		if self.getFocusId() == FILE_BROWSER:
				item = self.getControl(FILE_BROWSER).getSelectedItem()
				uri = item.getProperty(item.getProperty('type'))
				self.client.add(uri)
				self.getControl( STATUS ).setLabel(uri+ ' '+STR_WAS_QUEUED)
		if self.getFocusId() == ARTIST_BROWSER:
			item = self.getControl(ARTIST_BROWSER).getSelectedItem()
			typ = item.getProperty('type')
			if typ == 'file':
				self.client.add(item.getProperty(typ))
				self.getControl( STATUS ).setLabel(item.getProperty(typ)+ ' '+STR_WAS_QUEUED)
			else:
				if typ == 'artist':
					found = self.client.find('artist',item.getProperty('artist'))
					status = item.getProperty('artist')+' '+STR_WAS_QUEUED
				elif typ == 'album':
					found = self.client.find('artist',item.getProperty('artist'),'album',item.getProperty('album'))
					status = item.getProperty('artist')+' - '+item.getProperty('album')+ ' '+STR_WAS_QUEUED
				if not found == []:
					self.client.try_command('add')
					self.client.command_list_ok_begin()
					for f_item in found:
						self.client.add(f_item['file'])
					self.client.command_list_end()
					self.getControl( STATUS ).setLabel(status)					

	def _context_menu(self):
		if self.getFocusId() == CURRENT_PLAYLIST:
			if self.getControl(CURRENT_PLAYLIST).size() < 1:
				return
			ret = self.dialog(STR_SELECT_ACTION,[STR_REMOVE_FROM_QUEUE,STR_SAVE_QUEUE_AS,STR_CLEAR_QUEUE])
			if ret==0:
				self.client.deleteid(self.getControl(CURRENT_PLAYLIST).getSelectedItem().getProperty('id'))
			if ret==1:
				self._save_queue_as()
			if ret==2:
				self._clear_queue()
		if self.getFocusId() == ARTIST_BROWSER:
			ret = self.dialog(STR_SELECT_ACTION,[STR_QUEUE_ADD,STR_QUEUE_REPLACE])
			if ret == 0:
				self._queue_item()
			if ret == 1:
				self.client.stop()
				self.client.clear()
				self._queue_item()
		if self.getFocusId() == FILE_BROWSER:
			ret = self.dialog(STR_SELECT_ACTION,[STR_QUEUE_ADD,STR_QUEUE_REPLACE,STR_UPDATE_LIBRARY])
			if ret == 0:
				self._queue_item()
			if ret == 1:
				self.client.stop()
				self.client.clear()		
				self._queue_item()			
			if ret == 2:
				item = self.getControl(FILE_BROWSER).getSelectedItem()
				uri = item.getProperty(item.getProperty('type'))
				print 'URI '+uri
				if uri =='':
					self.client.update()
				else:
					self.client.update(uri)
				self.getControl( STATUS ).setLabel(STR_UPDATING_LIBRARY+ ' ('+uri+')')
						
	def exit(self):
		self.disconnect()
		self.close()
	def _action_back(self):
		if self.getFocusId() == FILE_BROWSER:
			self._update_file_browser(browser_item=self.getControl(FILE_BROWSER).getListItem(0),back=True)
		if self.getFocusId() == ARTIST_BROWSER:
			self._update_artist_browser(artist_item=self.getControl(ARTIST_BROWSER).getListItem(0),back=True)

		
			
	def _play_stream(self):
		if self.is_play_stream and not self.stream_url=='':
			print 'Playing '+self.stream_url
			player = xbmc.Player(xbmc.PLAYER_CORE_MPLAYER)
			if player.isPlayingVideo():
				return
			if player.isPlayingAudio():
				if not player.getPlayingFile() == self.stream_url:
					self._start_media_player()
			else:
				self._start_media_player()

	def _start_media_player(self):
		icon =  os.path.join(__addon__.getAddonInfo('path'),'icon.png')
		xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (__scriptname__,STR_PLAYING_STREAM,'icon.png'))
		xbmc.executebuiltin('PlayMedia(%s)' % self.stream_url)
	
	def disconnect(self):
		p = xbmcgui.DialogProgress()
		p.create(STR_DISCONNECTING_TITLE)
		p.update(0)
		self.client.disconnect()
		p.close()
	
	def _playlist_contextmenu(self):
		ret = self.dialog(STR_SELECT_ACTION,[STR_LOAD_ADD,STR_LOAD_REPLACE,STR_RENAME,STR_DELETE])
		playlist = self.getControl(PLAYLIST_BROWSER).getSelectedItem().getLabel()
		if ret == 0:
			self.client.load(playlist)
		elif ret == 1:
			self.client.stop()
			self.client.clear()		
			self.client.load(playlist)

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
							self.getControl( STATUS ).setLabel(STR_PLAYLIST_SAVED)
					else:
						self.client.rename(playlist,kb.getText())
						self.getControl( STATUS ).setLabel(STR_PLAYLIST_SAVED)					
						
		elif ret == 3:
			self.client.rm(playlist)
			
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
					self.getControl( STATUS ).setLabel(STR_PLAYLIST_SAVED)
			else:	
				self.client.save(kb.getText())
				self.getControl( STATUS ).setLabel(STR_PLAYLIST_SAVED)
	def _consume_mode_toggle(self):
		if self.getControl(RB_CONSUME_MODE).isSelected():
			self.client.consume(1)
		else:
			self.client.consume(0)
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
		except mpd.CommandError:
			traceback.print_exc()
			formatted_lines = traceback.format_exc().splitlines()
			xbmcgui.Dialog().ok('MPD',formatted_lines[-1])
		except mpd.ProtocolError:
			traceback.print_exc()
			self.disconnect()
			self.getControl( STATUS ).setLabel(STR_NOT_CONNECTED)
		except mpd.ConnectionError:
			traceback.print_exc()
			self.disconnect()
			self.getControl( STATUS ).setLabel(STR_NOT_CONNECTED)
