# -*- coding: utf-8 -*-



#      Copyright (C) 2014 Tommy Winther
#      http://tommy.winther.nu
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
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


from xbmcswift import xbmc, xbmcaddon, xbmcgui
from simplecache import  SimpleCache
from urllib2 import  HTTPError, URLError
import urllib2 
import urllib
import operator
import sys
import json
import os.path
import datetime
import time
import threading


reload(sys)  
sys.setdefaultencoding('UTF8')

ADDON           = xbmcaddon.Addon()
VERSION         = ADDON.getAddonInfo('version')
LANG            = ADDON.getLocalizedString
ADDON_NAME      = ADDON.getAddonInfo('name')
ID              = ADDON.getAddonInfo('id')
PROFILE_PATH    = xbmc.translatePath( ADDON.getAddonInfo('profile') ).decode("utf-8")
ADDONPATH       = xbmc.translatePath( ADDON.getAddonInfo('path') ).decode("utf-8")

TOKEN_FILEPATH  = PROFILE_PATH + '/token.txt'

ACTION_LEFT 			= 1
ACTION_RIGHT 			= 2
ACTION_UP 				= 3
ACTION_DOWN 			= 4

ACTION_PAGE_UP 			= 5
ACTION_PAGE_DOWN 		= 6
ACTION_SELECT_ITEM		= 7
ACTION_PARENT_DIR 		= 9
ACTION_PREVIOUS_MENU 	= 10
ACTION_SHOW_INFO 		= 11
ACTION_STOP 			= 13
ACTION_NEXT_ITEM 		= 14
ACTION_PREV_ITEM 		= 15
ACTION_SHOW_CODEC		= 27
ACTION_SHOW_FULLSCREEN 	= 199
ACTION_DELETE_ITEM 		= 80
ACTION_MENU 			= 163
ACTION_LAST_PAGE 		= 160
ACTION_RECORD 			= 170

ACTION_MOUSE_WHEEL_UP 	= 104
ACTION_MOUSE_WHEEL_DOWN = 105
ACTION_MOUSE_MOVE 		= 107

ACTION_GESTURE_SWIPE_LEFT   = 511
ACTION_GESTURE_SWIPE_RIGHT  = 521
ACTION_GESTURE_SWIPE_UP   	= 531
ACTION_GESTURE_SWIPE_DOWN   = 541


KEY_NAV_BACK 			= 92
KEY_CONTEXT_MENU 		= 117
KEY_HOME 				= 159


REMOTE_0 = 58
REMOTE_1 = 59
REMOTE_2 = 60
REMOTE_3 = 61
REMOTE_4 = 62
REMOTE_5 = 63
REMOTE_6 = 64
REMOTE_7 = 65
REMOTE_8 = 66
REMOTE_9 = 67

ACTION_JUMP_SMS2 = 142
ACTION_JUMP_SMS3 = 143
ACTION_JUMP_SMS4 = 144
ACTION_JUMP_SMS5 = 145
ACTION_JUMP_SMS6 = 146
ACTION_JUMP_SMS7 = 147
ACTION_JUMP_SMS8 = 148
ACTION_JUMP_SMS9 = 149



CHANNELS_PER_PAGE 		= 9
CHANNEL_HEIGHT			= 70
PROG_SHOWN_HOURS 		= 5
PROG_PANEL_HOURS		= 6
PROG_HOURS_BACK 		= 2
PROG_DAYS_BACK 			= 14



# LOAder
LOADER_FLAG 			= 5100
C_MAIN_LOADING_PROGRESS = 5101

FILTER_FLAG 			= 6100
FILTER 					= 6101
# BEGIN #
SITE_PATH 				= 'https://bgtime.tv/api/mobile_v4/'
IMAGE_PATH 				= os.path.join(ADDONPATH, 'resources', 'skins', 'Default', 'media')


# Onli load master menu
BASE_URL				= 'menu'
EPG_MENU 				= 'tablet=1'
LIVETV_PATH				= 'menu/livetv_alternative'
SITE_LOGIN_PAGE			= SITE_PATH + 'user/signin'

# VIEW #
WIDTH 					= 1280
HEIGHT 					= 720
TIMEBAR_HEIGHT			= int(float(WIDTH/32))
TV_LOGO_WIDTH 			= (HEIGHT - TIMEBAR_HEIGHT) /CHANNELS_PER_PAGE


CACHE 					= SimpleCache()
dialog 					= xbmcgui.Dialog()






def log(  text):
	xbmc.log('%s addon: %s' % (ADDON_NAME , text))

def num( a):
	if a is None: return
	n=int(float(a))
	return n

def cleanUpUrl(url):
	site_base = '://bgtime.tv/mobile/'
	if site_base in url: 	url = url.replace(site_base, '')
	if EPG_MENU in url: 	url = url.replace(EPG_MENU, '')
	if '?' in url: 			url = url.replace('?', '')
	return url




##########################################################################################
##									CONTROLLER  										##
##########################################################################################


class Controller(object):
	last_sel_l_item = 0
	last_sel_tv_item = None
	is_new = False
	last_controls =  []
	is_from_click = False
	thumb_view_id = False
	list_view_id = False
	program_view_id = False

	history = list()
	def changeControlVisibility(self, _self, _bool, *controlIds):
		for controlId in controlIds:
			loader = _self.getControl(controlId)
			loader.setVisible(_bool)

	def handleURLFromClick(self, url, show_title, _self=None):

		sign= '?'
		if '?' in url:  sign = '&'
		else: 
			if show_title == '':
				dialog.ok(LANG(32001),  LANG(32008))
				return
		if len(url) > 3:
		
			rtr = self.getListData(url=url+sign+EPG_MENU)
			if rtr is None: return

			if 'search' in url and show_title is not None: 
				rtr['title_prev'] = LANG(32009)+ show_title
			if rtr is None: return
			if url == 'menu/program_v2':
				new_program = Program(rtr)
				new_program.doModal()
				del new_program
				return

			if 'menu' not in rtr:
				tracking_key =''
				if 'key' not in rtr:
					dialog.ok(LANG(32003), rtr['msg'])
					return
				else:
					title=''
					items=[]

					if 'quality_urls' in rtr and len(rtr['quality_urls']) > 1:
						for key,val in enumerate(rtr['quality_urls']):
							items.append(val['title'])

						ret = dialog.select(LANG(32006), items)
						if ret < 0:
							_self.close()
							return

						if 'tracking_key' in rtr['quality_urls'][ret]:
							tracking_key = rtr['quality_urls'][ret]['tracking_key']

						if rtr['quality_urls'][ret]['title'] == 'Success': rtr['quality_urls'][ret]['title'] =''
						self.tvPlay(rtr['quality_urls'][ret]['key'],  u"{0}".format(rtr['quality_urls'][ret]['title']),  u"{0}".format(show_title), tracking_key, self.isLive(url, tracking_key))
						return

					if 'title' in rtr:
						title=rtr['title']
						if rtr['title'] == 'Success': title =''

				if 'tracking_key' in rtr:
					tracking_key = rtr['tracking_key']
				self.tvPlay(rtr['key'], title, show_title, tracking_key, self.isLive(url, tracking_key))
				return
			else:
				self.is_from_click = True
				if 'thumb' in rtr['menu'][0] and len(rtr['menu'][0]['thumb']) > 1:
					self.is_new = True
					# if self.thumb_view_id:
					new_view = ThumbView(rtr, url)
					new_view.doModal()
					# del new_view
				else:

					list_items = self.createMenuList(rtr)
					new_list = List(list_items)
					new_list.doModal()
					# del new_list
		return



	def isLive(self, url, key):
		if LIVETV_PATH in url:
			return True

		if key is None: return False
		arr = key.split('_')
		now = datetime.datetime.today()
		now = num(time.mktime(now.timetuple()))
		if len(arr) >= 2:
			try: 
				int(arr[-1])
				int(arr[-2])
				if int(arr[-1]) > now and int(arr[-2])<now:
					return True
			except: 
				return True

		return False


	def createMenuList(self, data):        
			menulist=[]
			items=[]
			menulist = data['menu']
			if not menulist:
				dialog.ok(LANG(32003), LANG(32004))
			if menulist: 

				for (key, val) in enumerate(menulist):
					label = val['title'].encode('utf-8')
					if val['key'] == 'menu/home': continue

					items.append({
						'title': label,
						'key': u"{0}".format(key),
						'url': val['key'],
						'thumb': "{0}".format(val["thumb"])})

			return items

	def getListData(self, url, send=None, is_menu=None):

		if(not ADDON.getSetting('username')) or (not ADDON.getSetting('password')):
			dialog.ok(LANG(32003), LANG(32005))
		cached = CACHE.get(str(url+'_'+ADDON.getSetting('username')+'_'+ADDON.getSetting('password')))
		
		if cached is not None and is_menu is None:
			return cached
		else:
			signin = login( 
				ADDON.getSetting('username'), 
				ADDON.getSetting('password'),
				url,
				send
			)

			if (not signin) or (not signin.token):
				return
			if not signin.data:
				return


			expiration=datetime.timedelta(hours=3)
			cleaned_url = cleanUpUrl(url)
			if LIVETV_PATH in cleaned_url and len(cleaned_url)> len(LIVETV_PATH):
				expiration=datetime.timedelta(minutes=15)

			CACHE.set(str(url+'_'+ADDON.getSetting('username')+'_'+ADDON.getSetting('password')), signin.data, expiration=expiration)
		return signin.data
	


	def tvPlay(self, url, title, show_title, tracking_key, is_live):
		self.player = Player()

		li 					= xbmcgui.ListItem(label=show_title + ' ' + title)
		self.player.tracking_key = tracking_key
		self.player.is_live  	= is_live
		self.player.is_playing 	= True
		now 				= datetime.datetime.today()
		str_time 			= num(time.mktime(now.timetuple()))

		self.player.play(url, li)

		counter = 0
		last_time = 0;
		while self.player.is_playing:
			if self.player.isPlaying():
				self.player.info = {
					'key'			: tracking_key,
					'stream_started': str_time,
					'current_time'	:  num(self.player.getTime()),
				}
				if counter == 90:
					counter = 0
					self.player.reportPlaybackProgress(self.player.info, 'progress')

			counter += 1
			xbmc.sleep(1000)

		del self.player




controller = Controller()



##########################################################################################
##									PLAYER 	 											##
##########################################################################################



class Player(xbmc.Player):
	info 			= None
	tracking_key 	= None
	is_live 		= None
	is_playing 		= False
	
	def __init__(self):
		xbmc.Player.__init__(self)

	def onPlayBackStarted(self):

		if self.tracking_key is not None:
			now = datetime.datetime.today()
			str_time = int(time.mktime(now.timetuple()))
			self.info = {
				'key'			: self.tracking_key,
				'stream_started': str_time,
				'current_time'	: num(self.getTime()),
			}
			self.reportPlaybackProgress(self.info, 'start')

	def onPlayBackResumed(self):
		pass 

	def onPlayBackPaused(self):
		pass

	def is_overlay(self):
		return xbmc.getCondVisibility("VideoPlayer.UsingOverlays")

	def is_playback_paused(self):
		return bool(xbmc.getCondVisibility("Player.Paused"))

	def onPlayBackStopped(self):

		if self.info is not None:
			self.reportPlaybackProgress(self.info, 'stop')
			
		self.is_playing = False

	def onPlayBackSeek(self, time, seekOffset):
		pass

	def getToken(self):
			if os.path.isfile(TOKEN_FILEPATH):
				fopen = open(TOKEN_FILEPATH, "r")
				temp_token = fopen.read()
				fopen.close()
				if temp_token:
					arr = temp_token.partition(" ")
					token = arr[0]
					if arr[2] and arr[2] != ADDON.getSetting('username'):
						token = '';
					temp_token = ''
		
			if not token: return
			return token

	def reportPlaybackProgress(self, info, action):
		token = self.getToken()
		if info is None: return
		if self.tracking_key is not None:
			data ={	'token'			: token,
				'key'			: self.tracking_key,
				'stream_started': str(num(info['stream_started'])),
				'current_time'	: str(num(info['current_time'])),
				'action'		: action,
			}
			send = urllib.urlencode(data)
			request = urllib2.Request(SITE_PATH +'tracking/report_playback', send, headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(VERSION)})
	

##########################################################################################
##										LOGIN  											##
##########################################################################################



class login:

	token = ""
	data = ""
	request = ""
	login_iteration = 0
	
	def __init__(self, username, password, url, send = None):
		self.usr = username
		self.pas = password
		self.url = url
		
		self.openReadFile()
		if not self.token:
			self.logIN()
			if not self.token:
				return

		self.data=self.getLive()
		if send is not None:	self.data.update(send)
		self.data=self.getData(SITE_PATH + url)

	def logIN(self):
		
		self.data = self.makeUserPass()
		self.token = self.getData(SITE_LOGIN_PAGE)
		if self.token:
			self.writeInFile()
		return
	
	def getData(self, url):
		send = urllib.urlencode(self.data)
		self.request = urllib2.Request(url, send, headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(VERSION)})
		try:
			response = urllib2.urlopen(self.request)

		except HTTPError, e:
			dialog = xbmcgui.Dialog()
			dialog.ok(LANG(32003), e.code)
			return
		except urllib2.URLError, e:
   			dialog = xbmcgui.Dialog()
			dialog.ok(LANG(32003), LANG(32007))
			return
		
		data_result = response.read()
		xbmc.log('%s addon: %s' % (ADDON_NAME, url))
		try:
			res = json.loads(data_result)
		except Exception, e:
			xbmc.log('%s addon: %s' % (ADDON_NAME, e))
			return
		
		if 'token' in res:
			return res['token']
		
		if 'status' in res:
			if res['status'] == 'ok':
				return
				
			if 'login' in res and res['login'] == 'yes':
	
				if self.login_iteration > 0:
					self.login_iteration = 0
					return
				
				self.logIN()
				self.data=self.getLive()
				data_new=self.getData(url)
				self.login_iteration += 1
				
				return data_new
	
			else:
				dialog = xbmcgui.Dialog()
				if 'status' in res and res['status'] == 204:
					dialog.ok(LANG(32003), res['msg'].encode('utf-8'))
					return
				if 'subscription_required' in res and res['subscription_required'] == True:
					dialog.ok(LANG(32003), res['msg'].encode('utf-8'))
					return
				if 'search' in url:
					dialog.ok(LANG(32003), res['msg'].encode('utf-8'))
					return
				dialog.ok(LANG(32003), res['msg'].encode('utf-8'))
				ADDON.openSettings(ID)

				return
		
		return res
	
	def getLive(self):
		return {'token': self.token}
	
	def makeUserPass(self):
		return {
			"usr":self.usr,
			"pwd":self.pas,
			"access_type": "xbmc_kodi",
			"device_info": json.dumps({
				"board":xbmc.getInfoLabel("System.BuildVersion"),
				"brand":"xbmc/kodi " + xbmc.getInfoLabel("System.ProfileName"),
				"device":xbmc.getInfoLabel("System.KernelVersion"),
				"display":xbmc.getInfoLabel("System.FriendlyName"),
				"model":xbmc.getInfoLabel("System.BuildDate"),
				"product":"",
				"push_id":"",
				"uuid":""
			})
		}

	def writeInFile(self):
		fopen = open(TOKEN_FILEPATH, "w+")
		fopen.write(self.token + " " +  ADDON.getSetting('username'))
		fopen.close()

	def openReadFile(self):
		if os.path.isfile(TOKEN_FILEPATH):
			fopen = open(TOKEN_FILEPATH, "r")
			temp_token = fopen.read()
			fopen.close()
			if temp_token:
				arr = temp_token.partition(" ")
				self.token = arr[0]
				if arr[2] and arr[2] != ADDON.getSetting('username'):
					self.token = '';
				temp_token = ''
		else:
			self.writeInFile()
		



##########################################################################################
##									INFO OBJECT 										##
##########################################################################################



class ControlAndInfo(object):
	def __init__(self, control, info):
		self.control = control
		if 'title' in info:				self.title 			= info['title'].encode('utf-8')
		if 'is_visible' in info:		self.is_visible 	= info['is_visible']
		if 'url' in info:				self.url 			= info['url']
		if 'pos' in info: 				self.pos 			= info['pos']
		if 'sec_controls' in info:		self.sec_controls 	= info['sec_controls']
		if 'page' in info: 				self.page 			= info['page']




##########################################################################################
##									HHISTORY    DATA									##
##########################################################################################

class URLandInfo(object):
	def __init__(self, url, pages, filters, rows, cols, windowid):
		self.url = url
		self.pages = pages
		self.idx 	= 0
		self.x = 0
		self.y = 0
		self.windowid = windowid
		self.rows = rows
		self.cols = cols
		self.filters = filters
	def set_idx(self, idx):
		self.idx = idx

	def set_pos(self, x, y):
		self.x = x
		self.y = y
		pass

##########################################################################################
##									LIST VIEW 											##
##########################################################################################



class List(xbmcgui.WindowXML):
	C_LIST = 6001
	C_CANCEL = 6004

	def __new__(cls,list_items):
		return super(List, cls).__new__(cls, 'script-video-bgtime-tv-list.xml',ADDONPATH)

	def __init__(self, list_items):
		self.list_items = list_items
		super(List, self).__init__()
		self.swapInProgress = False

	def onInit(self):
		c = self.getControl(self.C_LIST)
		if hasattr(self, 'list_items'):
			self.updateList(self.list_items)
		else:
			self.updateList(list_items=[])
		self.setFocus(c)

	def onClick(self, controlId):
		controller.changeControlVisibility(self, False, LOADER_FLAG)
		if controlId == self.C_LIST:
			list_control = self.getControl(self.C_LIST)
			item_url = list_control.getSelectedItem().getLabel2()
			show_title = list_control.getSelectedItem().getLabel()
			controller.last_sel_l_item = num(list_control.getSelectedPosition())


			if 'search' in item_url:
				controller.changeControlVisibility(self, True, LOADER_FLAG)

				dialog = xbmcgui.Dialog()
				d = dialog.input('Enter secret code', type=xbmcgui.INPUT_ALPHANUM)
				item_url = item_url+'?s='+str(d)
				show_title = str(d)

			controller.handleURLFromClick(item_url, show_title, self)
				

	def onFocus(self, controlId):
		pass

	def updateList(self, list_items):
		self.is_menu = False
		if not list_items:
			data = controller.getListData(url=str(BASE_URL+'?'+EPG_MENU), is_menu=True)

			if data is None: self.close()

			list_items = controller.createMenuList(data)
			self.is_menu = True

		list_control = self.getControl(self.C_LIST)
		list_control.reset()
		if self.is_menu:
			list_items.append({
					'title': 'Tърси',
					'key': num(len(list_items)),
					'url': 'search',
					'thumb': ''
					})

		for key, val in enumerate(list_items):
			item = xbmcgui.ListItem(u"{0}".format( val['title']), label2=val['url'])
			item.setProperty('idx', str(key))
			list_control.addItem(item)

		if controller.last_sel_l_item >= 0:  list_control.selectItem(controller.last_sel_l_item)
		controller.changeControlVisibility(self, True, LOADER_FLAG)



##########################################################################################
##									THUMB VIEW 											##
##########################################################################################


class ThumbView(xbmcgui.WindowXML):
	C_TITLE 	= 6001
	C_LIST 		= 6002
	TEXT_Y		= 50
	BOX_X		= 236
	BOX_Y		= 180
	COLS 		= 0
	ROWS 		= 0
	TITLE_Y		= 40
	DESC_Y		= 0

	def __new__(cls,data, url):
		return super(ThumbView, cls).__new__(cls, 'script-video-bgtime-tv-thumb-view.xml', ADDONPATH)

	def __init__(self, data, url):
		self.data = data
		self.url = url
		super(ThumbView, self).__init__()
		# self.swapInProgress = False

	def onInit(self):

		self.pages 				= list()
		self.filters 			= list()
		self.windowid 			= xbmcgui.getCurrentWindowId()
		self.is_new 			= True
		self.has_filter 		= False
		self.history 			= 0
		self.DEFAULT_CONTROL 	= None
		self.curr_page 			= None
		self.last_focused_elem	= None
		self.last_position		= None
		self.z_index_order		= None

		controller.changeControlVisibility(self, False, LOADER_FLAG)
		self.createThumbView(self.data, self.url)
		
	def createThumbView(self, data, url):
	
		for page in controller.history:
			if page.url == url and self.windowid == page.windowid:
				self.history  = controller.history.index(page)
				self.pages = page.pages
				self.curr_page = page.idx
				self.ROWS = page.rows
				self.COLS = page.cols
				self.filters = page.filters

		if self.pages :
			if self.filters:
				controller.changeControlVisibility(self, False, FILTER_FLAG)
			self.updateView(self.curr_page, controller.history[self.history].x, controller.history[self.history].y)
			return
		else:
			controller.last_page_url = url
			if not data: pass
			if url == 'menu/bgmovies' or url[-4:] == 'voyo':	
				self.BOX_X, self.BOX_Y = (190, 236+self.TEXT_Y)

			if 'livetv_alternative' in url:	
				self.BOX_X = self.BOX_Y;

				if len(data['title_prev']) <=2:
					data['title_prev'] 	= LANG(32010)+' '+ data['title_prev']+ LANG(32011)

			if 'title_prev' in data:
				control = self.getControl(self.C_TITLE)
				control.setLabel(u"{0}".format('[B]'+data['title_prev'].upper()+'[/B]'))

			
			controls 			= list()
			self.page_list 		= list()
			self.COLS 			= num((WIDTH-2*20)/self.BOX_X)
			self.ROWS 			= num((HEIGHT-self.TITLE_Y-self.DESC_Y)/self.BOX_Y)
			panel_image 		='script-video-bgtime-tv-grey.png';
			
			
			x_margin 			= num((WIDTH - self.COLS*self.BOX_X - self.TITLE_Y-self.DESC_Y)/(self.COLS))
			y_margin 			= num((HEIGHT - self.ROWS*self.BOX_Y - self.TITLE_Y-self.DESC_Y)/(self.ROWS))
			x , y 				= (20, self.TITLE_Y+self.DESC_Y)
			x_step 				= num(x_margin + self.BOX_X)
			y_step 				= num(self.BOX_Y+y_margin)

			counter_y, counter_x= (0, 0)

			if 'filters' in data:
				for k, v in enumerate(data['filters']):
					self.filters.append({
						'title'	: str(v['title'].encode('utf-8')),
						'url'	: v['key_full']
					})

				self.has_filter = True
				controller.changeControlVisibility(self, False, FILTER_FLAG)

			for k, v in enumerate(data['menu']):
				y_offset = y+y_step
				if k % (self.COLS*self.ROWS) == 0 and k > 0:
					self.pages.append(self.page_list)
					self.page_list = list()
					y = self.TITLE_Y+self.DESC_Y

					counter_y, counter_x =(0, 0)

				if 'title' in v: 			title = v['title']
				elif 'start' in v:  		title  = str(datetime.datetime.fromtimestamp( intv['start'] ).strftime('%d.%M.%y %H:%M'))
				title = u"{0}".format(title)

				if 'livetv_alternative' in url:
					title = u"{0}".format(v['desc'])
					title = title.replace('\n', ' ')
					panel_image = 'script-video-bgtime-tv-very-dark-grey.png'

				control 	= xbmcgui.ControlButton(x=x, y=y, width=self.BOX_X, height=self.BOX_Y, label='', focusTexture=os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-very-lighter-blue.png'), noFocusTexture=os.path.join(IMAGE_PATH,  'script-video-bgtime-tv-darker-no.png'))
				thumb		= xbmcgui.ControlImage(x=x, y=y, width = self.BOX_X, height=self.BOX_Y-self.TEXT_Y, filename=v['thumb'])
				panel 		= xbmcgui.ControlImage(x=x, y=y, width = self.BOX_X, height=self.BOX_Y-self.TEXT_Y, filename=os.path.join(IMAGE_PATH, panel_image))
				text 		= xbmcgui.ControlLabel(x=x, y=y+self.BOX_Y-self.TEXT_Y, width=self.BOX_X, height=self.TEXT_Y, label=title)
				if 'livetv_alternative' in url:		
					z_index_order = [panel, thumb, text]
					self.z_index_order = {'panel': 0, 'thumb': 1, 'text' :2}
				else:								
					z_index_order = [thumb, panel, text]
					self.z_index_order ={'thumb': 0, 'panel': 1, 'text' :2}

				info = {
					'url'			: u"{0}".format( v['key']),
					'title'			: u"{0}".format( v['title']),
					'is_visible'	: False,
					'sec_controls' 	: z_index_order,
					'pos'			: [ counter_x, counter_y],
					'page' 			: len(self.pages)
				}

				obj = ControlAndInfo(control, info)
				self.page_list.append(ControlAndInfo(control, info))
				
				counter_x , x= counter_x+1, x+x_step

				if counter_x >= self.COLS or x > WIDTH - self.BOX_X:
					x, y, counter_x, counter_y = 20, y+y_step, 0, counter_y+1

			
			self.pages.append(self.page_list)	
			self.updateView(0)
			
			controller.history.append(URLandInfo(url, self.pages, self.filters, self.ROWS, self.COLS, xbmcgui.getCurrentWindowId()))
			self.history = len(controller.history)-1
		

	def updateView(self, page = None, x=None, y=None):
		if page is None:							page = 0
		if page < 0 or page>= len(self.pages): 		return 
		
		if controller.is_new is False and self.is_new is True and controller.last_sel_tv_item is not None:
			if len(controller.last_sel_tv_item)	> 0:
				el = controller.last_sel_tv_item.pop()
				page, x, y = el['page'], el['pos'][0], el['pos'][1]
			
		controller.is_new = False

		self.is_new = False
		try: 				
			self.clearView(self.curr_page)
		except:				 	pass 
		
		controls = [elem.control  for elem in self.pages[page] ]+[el  for elem in self.pages[page] for el in elem.sec_controls]


		self.DEFAULT_CONTROL = controls[0]

		try:
			self.addControls(controls)
		except :
			for v in controls:
				try:
					self.addControl(v)
				except:
					log('Error adding contorols!!')

		if page < self.curr_page: 					 y = self.pages[page][-1].pos[1]

		self.curr_page = page
	
		controller.changeControlVisibility(self, True, LOADER_FLAG)
	
		if controller.history:
			controller.history[self.history].set_idx(page)
			controller.history[self.history].set_pos(x, y)
	
		if x is None: 
			return self.setFocus(self.DEFAULT_CONTROL)
		else: 
			if len(self.pages[page]) <= x: 						x=len(self.pages[page])-1
			if y is not None and y != 0:						
				return self.setFocus(controls[num(self.COLS*y+x)])

		self.setFocus(controls[num(x)])

	def clearView(self, page=None):
		if page is not None:		
			controls = [elem.control for elem in self.pages[page] ]+[el for elem in self.pages[page] for el in elem.sec_controls]
		else:						
			controls = list()

		try:
			self.removeControls(controls)
		except RuntimeError:	
			for con in controls:
				try:
					self.removeControl(con)
				except:	
					log('Error removing control')
	
	def onClick(self, controlId):
		control 	= self.getControl(controlId)
		
		
		if controlId == FILTER:

			filters = self.getFilters()
			select 	= dialog.select(LANG(32006), filters)
			if select < 0: return

			
			if controller.last_sel_tv_item is None: 		controller.last_sel_tv_item = [{'page':self.curr_page,'pos': [0,0]}]
			else:									controller.last_sel_tv_item = controller.last_sel_tv_item + [{'page':self.curr_page,'pos': [0,0]}]

			controller.handleURLFromClick(self.filters[num(select)]['url'], self.filters[num(select)]['title'], self)
			self.close()
			return

			
		curr_elem 	= self.getInfoFromControl(control, self.curr_page)

		if controller.last_sel_tv_item is None: 		controller.last_sel_tv_item = [{'page':self.curr_page,'pos': curr_elem.pos}]
		else:									controller.last_sel_tv_item = controller.last_sel_tv_item + [{'page':self.curr_page,'pos': curr_elem.pos}]
		
		self.clearView(self.curr_page)
		if curr_elem is None: return
		controller.handleURLFromClick(curr_elem.url, curr_elem.title, self)
		self.close()
		return

	

	def getControlFromPosition(self, x, y, page=0):
		if x is None or y is None or page is None: 	return self.pages[page][0].control

		for el in self.pages[page]: 
			if  el.pos[0] == x and el.pos[1] == y:	return el.control

		return 		 self.pages[page][0].control
	
	def getFilters(self):

		rtr = list()
		if self.filters is not None: 
			for k, v in enumerate(self.filters):
				rtr.append(str(v['title']))
			return rtr
		return

	def getInfoFromControl(self, control, page):
		for elem in self.pages[page]:
			if elem.control == control:
				return elem
		return None

	def close(self):
		super(ThumbView, self).close()

	def getFocus(self):
		return super(ThumbView, self).getFocus()

	def setFocus(self, control= None):
		if control is None: 
			if self.DEFAULT_CONTROL is not None: control = self.DEFAULT_CONTROL

		el = self.getInfoFromControl(control, self.curr_page)	

		if controller.history and el:  
			controller.history[self.history].set_pos( el.pos[0], el.pos[1])

		
		try:
			super(ThumbView, self).setFocus(control)
		except RuntimeError: 
			log('error')
			pass

	def onAction(self, action):
		focused_elem = None
		act_id =  action.getId()
	
		if act_id in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU, ACTION_SHOW_FULLSCREEN] :
			self.close()
			return
		if act_id in [ACTION_UP, ACTION_LEFT, ACTION_RIGHT, ACTION_DOWN, ACTION_MOUSE_WHEEL_UP, ACTION_MOUSE_WHEEL_DOWN, ACTION_GESTURE_SWIPE_LEFT,ACTION_GESTURE_SWIPE_RIGHT, ACTION_GESTURE_SWIPE_DOWN, ACTION_GESTURE_SWIPE_UP]:
			try:	
				focused_elem = self.getFocus()
			except:
				'excpt'
				if self.last_position is not None:											focused_elem = self.getControlFromPosition(self.last_position[0], self.last_position[1], self.curr_page)
				elif self.DEFAULT_CONTROL is not None:										focused_elem = self.DEFAULT_CONTROL

			if focused_elem is None: 														return
		
			curr_el = self.getInfoFromControl(focused_elem, self.curr_page)

			if curr_el is None:
				if focused_elem.getId()!=FILTER: 																return
				elif focused_elem.getId()==FILTER and act_id in[ACTION_LEFT, ACTION_UP, ACTION_RIGHT]:			return
			

			if act_id == ACTION_UP: 		
				self.up(  focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == ACTION_LEFT:		
				self.left(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == ACTION_RIGHT:
				self.right(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == ACTION_DOWN:
				if focused_elem.getId() == FILTER:																return self.setFocus(self.last_focused_elem.control)	
				self.down(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			if   act_id in [ACTION_MOUSE_WHEEL_UP, ACTION_GESTURE_SWIPE_DOWN, ACTION_PAGE_UP]:  
				self.updateView(self.curr_page-1)

			elif act_id in [ACTION_MOUSE_WHEEL_DOWN, ACTION_GESTURE_SWIPE_UP, ACTION_PAGE_DOWN]:  
				self.updateView(self.curr_page+1)

			self.last_focused_elem = curr_el

	# Search acording to coordinates
	def up(self, cont, curr_el, x, y, page):
		if cont is None:
			if self.DEFAULT_CONTROL: 													return self.setFocus()

		if page == 0 and y==0:		
			if self.has_filter == True:	
				self.setFocus(  self.getControl(FILTER)  )
		if y == 0: 																		return self.updateView(self.curr_page-1, x)

		return  self.setFocus(  self.getControlFromPosition(x, y-1, page)  )
		

	def down(self, cont, curr_el, x, y, page):
		if page == len(self.pages)-1:
			if y == self.pages[page][-1].pos[1]:										return
			if y == self.pages[page][-1].pos[1]-1 and x >  self.pages[page][-1].pos[0]: return
		
		if cont is None:			
			return self.setFocus()
		if y >= self.ROWS-1: 															return self.updateView(self.curr_page+1, x)

		return  self.setFocus(self.getControlFromPosition(x, y+1, page))
		

	def left(self, cont, curr_el, x, y, page):
		if cont is None: 
			if self.DEFAULT_CONTROL: 													return self.setFocus()
		if x <= 0: 
			if y == 0:
				if page == 0: 															return self.setFocus(cont)
				else: 																	return self.updateView(page-1, self.COLS-1)
			elif y-1 >=0 :																return self.setFocus(  self.getControlFromPosition(self.pages[curr_el.page][-1].pos[0], y-1, page)  )
				
		return self.setFocus(  self.getControlFromPosition(x-1, y, page)  )
		

	def right(self, cont, curr_el, x, y, page):
		if cont is None: 																return self.setFocus()

		last = self.pages[-1][-1]
		if page == len(self.pages) - 1 and y == last.pos[1] and x==last.pos[0]:			return self.setFocus(cont)
		if x >= self.COLS-1: 
			if y+1 <= self.ROWS-1: 														return self.setFocus(  self.getControlFromPosition(0 , y+1, page)  )	
			else:																		return self.updateView(self.curr_page+1, 0)

		return self.setFocus(  self.getControlFromPosition(x+1, y, page)  )



##########################################################################################
##								PROGRAM ( EPG ) VIEW 									##
##########################################################################################



class Program(xbmcgui.WindowXML):

	CONTAINER_PROGRAM    = 5001
	CONTAINER_LINE		 = 5002
	CONTAINER_PROG_DATE  = 5010


	def __new__(cls, data):
		return super(Program, cls).__new__(cls, 'script-video-bgtime-tv-program.xml', ADDONPATH)


	def __init__(self, data):
		self.data = data

		self.program 			= list()
		self.timebar 			= list()
		self.channels 			= list()
		self.visibleList 		= list()
		self.visible_channels 	= list()
		self.colors_controls	= list()


		self.view_start_date 	= datetime.datetime.today()
		self.now_tsmp 			= num(time.mktime(self.view_start_date.timetuple()))
		self.program_end 		= num(time.mktime(datetime.date(self.view_start_date.year, self.view_start_date.month, self.view_start_date.day).timetuple()))+3600*24
		self.program_start 		= self.program_end - (24*3600*PROG_DAYS_BACK)

		self.view_st_tsmp 		= None
		self.curr_page 			= None
		self.curr_cha 			= None
		self.last_focus 		= None
		self.foc_cha 			= None
		self.default_focus 		= None
		self.line 				= None




	def onInit(self):
		controller.changeControlVisibility(self, False, LOADER_FLAG)

		control = self.getControl(self.CONTAINER_PROGRAM)
		control.setWidth(WIDTH - TV_LOGO_WIDTH)

		if control:
			left, top = control.getPosition()
	
			self.left 		= left
			self.top 		= top
			self.right 		= left + control.getWidth()
			self.bottom 	= top + control.getHeight()
			self.width 		= control.getWidth()
			self.cellHeight = control.getHeight() / CHANNELS_PER_PAGE

		self.createProgram(self.data)


	def createProgram(self, data):

		self.program =  self.createProgramTimePanels()
		
		for key, val in enumerate(data['menu']):
			# Channels
			if str(val['k']) == '':
				continue
			self.channels.append({
				'is_vis' :		0,
				'control':		None,
				'thumb' : 		u"{0}".format(val['p']),
				'title'	: 		u"{0}".format(val['t']),
				'idx' : 		key, 
				'offset': 		0
				})
		
			for i, v in enumerate(val['s']):
				# Shows
				s =  num(v['s'])
				l =  num(v['l'])

				if s < self.program_start:
					continue
				
				if i-1>=0:			 prv = [key, val['s'][i-1][ 's'] ]
				if i+1 <= len(val['s'])-1:  nxt = [key, val['s'][i+1]['s' ] ]

				for p in self.program:
					# Shows separated in panels
					if ( s >= p['start'] and s < p['end']):
						
						p['shows'].append({
							'is_vis' : 		0,
							'title'	 : 		u"{0}".format(v['t']),
							'lngth'	 : 		l,
							'str'	 :		s,
							'url'    : 		u"{0}".format(v['k']),
							'cha'    :  	key,
							'prv'	 : 		prv,
							'nxt'	 : 		nxt,
							'control': 		xbmcgui.ControlButton(
												0,
												0,   
												0,   
												self.cellHeight - 2,
												label=u"{0}".format(v['t']),   
												textColor = '0xFFFFFFFF',
												focusTexture=os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-grey.png'),   
												noFocusTexture= os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-basic-blue.png')
								)
							})
		
		self.updateView()
	
	def updateView(self, view_st_tsmp = None, view_frst_ch = None, focus=None):
		prev_cha_id = None
		self.left = TV_LOGO_WIDTH
		today  = datetime.datetime.today()

		if  view_st_tsmp is None:
			if  self.view_st_tsmp is not None: 
				view_st_tsmp = self.view_st_tsmp
			else:
				view_st_tsmp = today - datetime.timedelta(hours=PROG_HOURS_BACK, minutes=self.view_start_date.minute % 60, seconds=self.view_start_date.second)
				view_st_tsmp = num(time.mktime(view_st_tsmp.timetuple()))
		
		view_end_tsmp = view_st_tsmp + 3600*PROG_SHOWN_HOURS
		
		if view_st_tsmp < self.program_start: 			return 

		if view_frst_ch is None:
			if self.curr_cha is not None:	
				view_frst_ch = self.curr_cha
			else:							
				view_frst_ch = 0

		self.clearView()

		cha_cont = self.updateVisibleChannels(view_frst_ch)
		time_cont = [elem['control'] for elem in self.updateTimebar(view_st_tsmp)]
		controls = list()

		shows = self.getProgramSegment(view_st_tsmp)
		_shows = sorted(shows, key=operator.itemgetter('cha', 'str'))

		for k, v in enumerate(_shows):

			w,  s,  l= None,  num(v['str']),  num(v['lngth'])

			if self.channels[v['cha']]['is_vis'] == 0:
				continue

			if s < view_st_tsmp : 
				
				if (s+l) > view_st_tsmp :  	# Cut the width of shows that cross view_st_tmsp
					w = num( (self.width* ( (s+l) - view_st_tsmp) )/(3600*PROG_SHOWN_HOURS))
				else:  			  # Skip if is before view_st_tmsp
				
					v['is_vis'] = 0
					continue	
		
			if s+l > view_end_tsmp: 

				if s< view_end_tsmp and s+l > view_end_tsmp: # Cut the width of shows that cross view_end_tmsp
					if s+100>view_end_tsmp: 
						v['is_vis'] = 0
						continue

					w = num((self.width* ( view_end_tsmp - s ) )/(3600*PROG_SHOWN_HOURS))
				else:				# Skip if is after the time
				
					v['is_vis'] = 0
					continue

			if w  is None:  	w = num((self.width*l/(3600*PROG_SHOWN_HOURS)))

			v['is_vis'] = 1
			
			# No title if btn is too small
			if w < 30: 			t = ' '
			else: 				t = v['title']

			if k> 0:
				if v['cha']  == _shows[k-1]['cha'] and  v['str']  == _shows[k-1]['str']:			continue
					
			# Changing the height of the channel program
			if v['cha'] != prev_cha_id and prev_cha_id != None: 	self.left = TV_LOGO_WIDTH

			
			if s > self.now_tsmp: 
				col_control = xbmcgui.ControlImage(x=self.left, y=self.channels[v['cha']]['offset'], width = w, height=self.cellHeight - 2, filename=os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-very-dark-grey.png'))
				self.colors_controls.append(col_control)
			elif s< self.now_tsmp and s+l>self.now_tsmp :
				col_control = xbmcgui.ControlImage(x=self.left, y=self.channels[v['cha']]['offset'], width = w, height=self.cellHeight - 2, filename=os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-grey.png'))
				self.colors_controls.append(col_control)


			if self.left == TV_LOGO_WIDTH and s > view_st_tsmp:
				# if element has started before the previous segment 
				last_prev = self.findNext([ v['cha'], s-3000], 1)
				if last_prev is not None:

					last_prev['control'].setLabel(t,focusedColor='0xFFFFFFFF', textColor='0xFFFFFFFF')
					last_prev['control'].setPosition(self.left,   self.channels[v['cha']]['offset'])
					last_prev['control'].setWidth(num((self.width*(s-view_st_tsmp)/(3600*PROG_SHOWN_HOURS))))

					controls.append(last_prev['control'])
					self.visibleList.append({'el': last_prev, 'control': last_prev['control']})

				self.left += num((self.width*(s-view_st_tsmp)/(3600*PROG_SHOWN_HOURS)))
				
			v['control'].setLabel(t,focusedColor='0xFFFFFFFF', textColor='0xFFFFFFFF')
			v['control'].setPosition(self.left,   self.channels[v['cha']]['offset'])
			v['control'].setWidth(w)
			
			self.left += w+2
			prev_cha_id = v['cha']

			controls.append(v['control'])
			self.visibleList.append({'el': v, 'control': v['control']})
		
		all_controls = controls + cha_cont + time_cont+self.colors_controls 
		self.line = self.setLineNow([view_st_tsmp, view_end_tsmp])
		if self.line is not None: all_controls.append(self.line)
		try:
			self.addControls(all_controls)
		except RuntimeError:	
			for elem in all_controls:
				try:
					self.addControl(elem)
				except RuntimeError:
					pass  # happens if we try to add a control twice

		self.view_st_tsmp = view_st_tsmp
		self.curr_cha = view_frst_ch
		
		controller.changeControlVisibility(self, True, LOADER_FLAG)
	
		if focus is None:   	
			self.setFocus()
		else: 					
			try:
				self.setFocus(focus)
			except:
	
				self.setFocus() 
		

		timeout = threading.Timer(15*60, self.refresh, [self.view_st_tsmp])

		if self.now_tsmp > view_st_tsmp and self.now_tsmp < view_end_tsmp: 	timeout.start()
		else:																timeout.cancel()

	
	def refresh(self, view_tsmp):
		if view_tsmp != self.view_st_tsmp:	return 
		
		today = datetime.datetime.today()

		self.now_tsmp =  num(time.mktime(today.timetuple()))

		tsmp = today - datetime.timedelta(hours=PROG_HOURS_BACK, minutes=today.minute % 60, seconds=today.second)
		tsmp = num(time.mktime(tsmp.timetuple()))
		
		self.updateView(tsmp, self.curr_cha, self.last_focus)
		


	def onAction(self, action):
		focused_cont = None
		act_id = action.getId()
	
		if act_id in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU, ACTION_SHOW_FULLSCREEN]:
			self.close()
			return

		if   act_id in [ACTION_MOUSE_WHEEL_UP, ACTION_GESTURE_SWIPE_DOWN, ACTION_PAGE_UP]:  
			if self.curr_cha+1- CHANNELS_PER_PAGE>=0:						return self.updateView( view_frst_ch = self.curr_cha+1- CHANNELS_PER_PAGE)
		elif act_id in [ACTION_MOUSE_WHEEL_DOWN, ACTION_GESTURE_SWIPE_UP, ACTION_PAGE_DOWN]: 
			if self.curr_cha-1+ CHANNELS_PER_PAGE <len(self.channels)-1:	return self.updateView( view_frst_ch = self.curr_cha-1+ CHANNELS_PER_PAGE)

		elif act_id == ACTION_GESTURE_SWIPE_RIGHT: 							return self.updateView( view_st_tsmp=self.view_st_tsmp - (3600*PROG_SHOWN_HOURS-1), view_frst_ch=self.curr_cha)
		elif act_id == ACTION_GESTURE_SWIPE_LEFT: 							return self.updateView( view_st_tsmp=self.view_st_tsmp + (3600*PROG_SHOWN_HOURS-1), view_frst_ch=self.curr_cha)

		if act_id in [ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN]:
			try:	
				focused_cont = self.getFocus()
			except:
				if self.default_focus is not None:							return self.setFocus()
				else:														return self.setFocus()
		
			if focused_cont.getId() == self.CONTAINER_PROG_DATE:
				if act_id in [ACTION_LEFT, ACTION_RIGHT, ACTION_UP]:		return			
				if self.last_focus is not None: 							return self.setFocus(self.last_focus)
				else:														return self.setFocus()

			c_el = self.getElemFromControl(focused_cont)
			self.foc_cha = c_el['cha']
		
			if   act_id == ACTION_LEFT:		self.onLeftMove(c_el)
			elif act_id == ACTION_RIGHT:	self.onRigthMove(c_el)
			elif act_id == ACTION_UP: 		self.onUpMove(c_el)
			elif act_id == ACTION_DOWN:     self.onDownMove(c_el)



	def onLeftMove(self, el):
		if el is None: 														return

		left_el = self.findNext(el['prv'])

		if left_el is None:													return self.setFocus()	
		if left_el['is_vis'] == False:										return self.updateView( view_st_tsmp=self.view_st_tsmp - (3600*PROG_SHOWN_HOURS-1), view_frst_ch=self.curr_cha, focus=left_el['control'])
	
		return self.setFocus(left_el['control'])

		
	def onRigthMove(self, el):
		if el is None:														return
		
		if el['str']+el['lngth'] > self.view_st_tsmp+3600*PROG_SHOWN_HOURS: return self.updateView( view_st_tsmp=self.view_st_tsmp + (3600*PROG_SHOWN_HOURS-1),  view_frst_ch=self.curr_cha, focus=el['control'])
		
		rgth_el = self.findNext(el['nxt'])
		
		if rgth_el is None: 												return self.setFocus()
		if rgth_el['is_vis'] == False:										return self.updateView( view_st_tsmp=self.view_st_tsmp + (3600*PROG_SHOWN_HOURS-1),  view_frst_ch=self.curr_cha, focus=rgth_el['control'])
		
		return 	self.setFocus(rgth_el['control'])

	

	def onUpMove(self, el):
		if el is None: 														return

		if el['cha'] - 1 < 0: 						  						
			self.last_focus = el['control']
			return self.setFocus(self.getControl(self.CONTAINER_PROG_DATE))

			
		if self.channels[el['cha'] -1]['is_vis'] == False:
			if el['cha']  <=  CHANNELS_PER_PAGE - 1: 						return self.updateView( view_frst_ch = 0, focus = el['control']) 	
			else :									 						return self.updateView( view_frst_ch = el['cha'] - CHANNELS_PER_PAGE+1, focus = el['control'])

		if el['str'] < self.view_st_tsmp:									start = self.view_st_tsmp
		else:																start = el['str']
	
		up_el = self.findNext([el['cha']-1, start], 3)

		if up_el is None:													return self.setFocus()
		if up_el['is_vis'] == False or  up_el['control'] is None: 			return self.updateView(focus=up_el['control'])
	
		return	self.setFocus(up_el['control'])
		

	def onDownMove(self, el):

		if el is None: 														return
		
		if el['cha'] >= self.channels[-1]['idx']:			  				return self.setFocus( el['control'])
		if self.channels[el['cha']+1]['is_vis'] == False: 					
			return self.updateView( view_frst_ch = el['cha'], focus=el['control'])
		
		if el['str'] < self.view_st_tsmp:									start = self.view_st_tsmp
		else: 																start = el['str']

		down_el = self.findNext([el['cha']+1,start], 4)

		if down_el is None:													return self.setFocus()	
		if down_el['is_vis'] == False or  down_el['control'] is None:		return self.updateView( view_st_tsmp=self.view_st_tsmp - (3600*PROG_SHOWN_HOURS-1), focus=down_el['control'] )
		return self.setFocus(down_el['control'])
	

	def getElemFromControl(self, control = None):
		if control is not None:
			for i, v in enumerate(self.visibleList):
				if v['control'] == control:
					return v['el']

			shows = self.getProgramSegment(segment=self.curr_page)
			for el in shows:
				if 'control' not in el: continue

				if el['control'] == control:
					return el

		return  None



	def findNext(self, _id=None, direction= None):
		if _id is not None:
			cha, s = _id[0], num( _id[1])
			cl = 1000
			page = num(self.curr_page)
			for i, v in enumerate(self.visibleList) :
				if v['el']['cha'] != cha: continue

				if num(v['el']['str']) == num(s):
					return v['el'] 
				
				if num(v['el']['str']) <= num(s) and  num(s) <num(v['el']['str'])+ num(v['el']['lngth']):
					if i <len(self.visibleList)-1:
						return self.check_for_closer(v['el'], self.visibleList[i+1]['el'], s)

			shows = self.getProgramSegment(segment =page) + self.getProgramSegment(segment=page-1)+ self.getProgramSegment(segment=page+1)
			for shows in self.program:
				for el in shows['shows']:
					if el['cha'] != cha: continue
					
					if el['str'] == s:
					
						return el
					if el['str'] <= s and el['str']+el['lngth']>s:
						return el
			
			if direction is not None and direction in [3, 4]:
				if direction == 4 and cha+1 < len(self.channels) : new_cha = cha+ 1
				if direction == 3 and cha-1 >= 0 : new_cha = cha-1

				for shows in self.program:
					for el in shows['shows']:
						if el['cha'] != new_cha: continue
						if el['str'] == s:
						
							return el
						if el['str'] <= s and el['str']+el['lngth']>s:
							return el

		return  None

	
	def getProgramSegment(self, st_tsmp=None, segment=None) :
		if segment is not None:
			return self.program[segment]['shows']

		if st_tsmp is None: return self.program[0]['shows']
		shows = None
		for i, p in enumerate(self.program):
			if st_tsmp > p['start'] and st_tsmp < p['end']:
				if st_tsmp+3600*PROG_SHOWN_HOURS > p['end']:
					
					if i>0 and i<len(self.program)-1:  	
						self.curr_page = i
						return self.program[i+1]['shows'] + p['shows'] + self.program[i-1]['shows']	
					if i==0: 					
						return self.program[i+1]['shows'] + p['shows']
					if i==len(self.program)-1: 	
						return p['shows'] + self.program[i-1]['shows']	
				self.curr_page = i
				
				if i<len(self.program)-1:  
					return p['shows'] + self.program[i+1]['shows']	
				else: 	
					return p['shows']
		
		return self.program[0]['shows']


	def check_for_closer(self, el, next_el, s):
		if el['cha'] != next_el['cha']:					return el

		if abs(el['str'] - s) >abs(next_el['str']-s):	return next_el 
		else:											return el

	def getProgramDates(self):
		dates = list()

		for x in range(0, PROG_DAYS_BACK):
			d = datetime.datetime.today() - datetime.timedelta(days=x)
			d = str(d.day)+' '+str(self.translateMonth(d.month-1))
			dates.append(str(d).encode('utf-8'))
		return dates
		

	def onClick(self, controlId):
		if controlId == self.CONTAINER_PROG_DATE:
			dates = self.getProgramDates()
			select = dialog.select(LANG(32006), dates)

			if select or select is 0:
				if select < 0: return
				if select == 0: return self.updateView(num(time.mktime(self.view_start_date.timetuple()))) 

				d = datetime.datetime.today()- datetime.timedelta(hours=PROG_HOURS_BACK, minutes=self.view_start_date.minute % 60, seconds=self.view_start_date.second)
	
				self.updateView(num(time.mktime(d.timetuple()) - select*24*3600))
			return

		elem=self.getElemFromControl(self.getControl(controlId))
		if elem is None: return
		controller.handleURLFromClick(elem['url'], elem['title'], self)


	def clearView(self):
		try:
			controls = [elem['control'] for elem in self.visibleList] + [elem['control'] for elem in self.visible_channels] + [elem['control'] for elem in self.timebar] + [elem for elem in self.colors_controls]

			if self.line is not None: controls.append(self.line)
			self.removeControls(controls)
		except RuntimeError:
			for elem in controls:
				try:
					self.removeControl(elem)
				except RuntimeError:
					pass  # happens if we try to remove a control that doesn't exist
		del self.visibleList[:]
		del self.visible_channels[:]
		del self.timebar[:]
		del self.colors_controls[:]
		self.line=None


	def setFocus(self, control= None):
		if control is None: 
			control = self.findNext([self.foc_cha, self.view_st_tsmp])
			if control is None: 
				if len(self.visibleList) > 0:
					control = self.visibleList[0]['control']
			else:
				control = control['control']
		try:
			super(Program, self).setFocus(control)
			return
		except:
			pass

	def getFocus(self):
		return super(Program, self).getFocus()

	def close(self): 
		super(Program, self).close()

	def getControl(self, controlId):
		try:
			return super(Program, self).getControl(controlId)
		except:
			return None


	def onFocus(self, controlId):
		if controlId == self.CONTAINER_PROG_DATE: return 
		try:
			focus = self.getFocus()
			self.last_focus = focus
		except:
			pass



	def translateMonth(self, _int):
		monthsDict = [ 	LANG(32013), LANG(32014), LANG(32015), LANG(32016), 
						LANG(32017), LANG(32018), LANG(32019), LANG(32020), 
						LANG(32021), LANG(32022), LANG(32023), LANG(32024)]
		if monthsDict[_int] is not None:return monthsDict[_int]
		else: return _int

	def setLineNow(self, times=list()):
		line = self.getControl(self.CONTAINER_LINE)
		
		if self.now_tsmp > times[0] and self.now_tsmp < times[1]:
			# line.setVisible(True)
			pos_x = num((self.width*(self.now_tsmp-times[0]))/(3600*PROG_SHOWN_HOURS)) + TV_LOGO_WIDTH
			line = xbmcgui.ControlImage(x=pos_x, y=TIMEBAR_HEIGHT, width=2, height=HEIGHT-TIMEBAR_HEIGHT, filename=os.path.join(IMAGE_PATH, 'timebar.png'))
			return line
			# line.setImage(os.path.join(IMAGE_PATH, 'timebar.png'))
			# line.setPosition(pos_x,TIMEBAR_HEIGHT)	
		else: 
			return 



	def updateVisibleChannels(self, st_cha):
		
		if st_cha is None: st_channel = 0

		controls = list()
		self.top = TIMEBAR_HEIGHT
		for el in self.channels:
			el['is_vis'] = 0
			if el['idx'] < st_cha or el['idx']>= st_cha+CHANNELS_PER_PAGE:
				continue
			el['is_vis'] = 1
			
			control = xbmcgui.ControlImage (0, self.top, TV_LOGO_WIDTH-2, self.cellHeight - 2, el['thumb'])
			el['offset'], el['control'] =self.top, control

			self.top += self.cellHeight 
			self.visible_channels.append({'control': control})
			controls.append(control)
		return controls


	def updateTimebar(self, st_tsmp):
		timebar = list()

		if st_tsmp == False: 
			st_tsmp = datetime.datetime.today() - datetime.timedelta(hours=PROG_HOURS_BACK, minutes=self.view_start_date.minute % 60, seconds=self.view_start_date.second)
			st_tsmp = num(time.mktime(st_tsmp.timetuple()))
		end_tsmp = st_tsmp + 3600*PROG_SHOWN_HOURS

		# Put the label on the control for changing the date
		date =  datetime.datetime.fromtimestamp(  int(st_tsmp )  )
		cont = self.getControl(self.CONTAINER_PROG_DATE)
		cont.setLabel( str(date.day)+' '+str(self.translateMonth(date.month-1) ) )

		x = TV_LOGO_WIDTH
		x_step = num(self.width / PROG_SHOWN_HOURS)

		for i in  range(0, PROG_SHOWN_HOURS):
			t_string = datetime.datetime.fromtimestamp(  int(st_tsmp )  )

			c 		= xbmcgui.ControlLabel(x,   2,   x_step-2,   36, str(t_string.strftime('%H:%M')),   alignment=4)
			c_img 	= xbmcgui.ControlImage(x,   2,   x_step-2,   36, filename=os.path.join(IMAGE_PATH, 'script-video-bgtime-tv-grey.png'))
			st_tsmp += 3600
			x += x_step

			self.timebar.append({'control': c})
			self.timebar.append({'control': c_img})
		return self.timebar


	def createProgramTimePanels(self):
		start_tsmp = self.program_end
		program = list()
		for x in range(0, PROG_DAYS_BACK*(24/PROG_PANEL_HOURS)):
			end_tsmp = start_tsmp
			start_tsmp -= PROG_PANEL_HOURS*3600
			
			program.append({
				'start':	 start_tsmp,
				'end':		 end_tsmp,
				'idx' :		 x,
				'shows' :	 list()
				})

		return program

