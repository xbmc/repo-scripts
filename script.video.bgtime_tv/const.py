# -*- coding: utf-8 -*-


import xbmc
import xbmcaddon
import xbmcgui
from simplecache import  SimpleCache
import os.path


ADDON           = xbmcaddon.Addon()
VERSION         = ADDON.getAddonInfo('version')
LANG            = ADDON.getLocalizedString
ADDON_NAME      = ADDON.getAddonInfo('name')
ID              = ADDON.getAddonInfo('id')
PROFILE_PATH    = xbmc.translatePath( ADDON.getAddonInfo('profile') )
ADDONPATH       = xbmc.translatePath( ADDON.getAddonInfo('path') )

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
ACTION_PAUSE	 		= 12
ACTION_STOP 			= 13
ACTION_NEXT_ITEM 		= 14
ACTION_PREV_ITEM 		= 15
ACTION_SHOW_CODEC		= 27
ACTION_SHOW_GUI 		= 18
ACTION_SHOW_FULLSCREEN 	= 36
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

MENU_CONTROL 			= 6001
PLAYER_STATE			= 6219

FILTER_FLAG 			= 6100
FILTER 					= 6101
# BEGIN #
SITE_PATH 				= 'http://bgtime.tv/api/mobile_v5/'
IMAGE_PATH 				= os.path.join(ADDONPATH, 'resources', 'skins', 'Default', 'media')

# Onli load master menu
BASE_URL				= 'menu'
EPG_MENU 				= 'tablet=1'
LIVETV_PATH				= 'menu/livetv_alternative'
SITE_LOGIN_PAGE			= SITE_PATH + 'user/signin'
SITE_LOGOUT_PAGE		= SITE_PATH + 'logout'

# VIEW #
WIDTH 					= 1280
HEIGHT 					= 720
TIMEBAR_HEIGHT			= int(float(WIDTH/32))
TV_LOGO_WIDTH 			= (HEIGHT - TIMEBAR_HEIGHT) /CHANNELS_PER_PAGE


CACHE 					= SimpleCache()
# dialog 					= xbmcgui.Dialog()





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
		if 'nxt' in info: 				self.nxt 			= info['nxt']
		if 'crr' in info: 				self.crr 			= info['crr']
		if 'prv' in info: 				self.prv 			= info['prv']



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


