# -*- sesacoding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
from simplecache import  SimpleCache
import const
import urllib.request, urllib.parse, urllib.error
import urllib
import sys
import json
import os.path
import datetime
import time
# import threading

WIDTH 					= 1280
HEIGHT 					= 720


dialog 					= xbmcgui.Dialog()

def pro2px(width, pro, rnd=False):
	if rnd:
		return int(round( width * (pro / 100) ) )
	else:	
		return int( width * (pro / 100) )
def log(  text):
	xbmc.log('%s addon: %s' % (const.ADDON_NAME , text))

def num( a):
	if a is None: return
	n=int(float(a))
	return n

def cleanUpUrl(url):
	site_base = '://bgtime.tv/mobile/'
	if site_base in url: 	url = url.replace(site_base, '')
	if '?' in url: 			url = url.replace('?', '')
	return url

def mi2hex(mi_color):
	mi_color = int(mi_color)
	r = mi_color // (256*256)
	g = (mi_color - (r*256*256)) // 256
	b = mi_color - (r*256*256) - (g*256)

	return "0xFF{0:02x}{1:02x}{2:02x}".format(r,g,b).upper()


def _json_rpc_request(payload):
	response = xbmc.executeJSONRPC(json.dumps(payload))
	return json.loads(response)

def _has_inputstream():
	"""Checks if selected InputStream add-on is installed."""
	payload = {
		'jsonrpc': '2.0',
		'id': 1,
		'method': 'Addons.GetAddonDetails',
		'params': {
			'addonid': 'inputstream.adaptive'
		}
	}
	data = _json_rpc_request(payload)

	if 'error' in data:
		try:
			xbmc.executebuiltin('InstallAddon(inputstream.adaptive)', True)
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{"addonid":"inputstream.adaptive","enabled":true}}')
			return xbmcaddon.Addon('inputstream.adaptive')
		except:
			xbmcgui.Dialog().ok('Missing inputstream.adaptive add-on', 'inputstream.adaptive add-on not found or not enabled.This add-on is required to view DRM protected content.')
		return False
	else:
		return True



##########################################################################################
##									CONTROLLER  										##
##########################################################################################


class Controller(object):
	history 				= list()
	menu_list 				= list()
	last_controls 			= list()
	
	player 					= None
	list_instance 			= None
	last_sel_item 			= None
	
	is_from_click 			= False
	is_new 					= False
	loading 				= False
	menu_id 				= 0
	last_sel_on_list 		= 0
	url 					= ''


	def onInit(self):
		pass

	def search(self, item_url, _self):
	
		self.removeMenu()

		d = dialog.input(const.LANG(32001))
		show_title = str(d)

		item_url = item_url+'?s='+str(d)
		self.handleURLFromClick(item_url, show_title)

		_self.close()


	def changeControlVisibility(self, _self, _bool, controlId, **data):
		#using flags to change visibility of a group of controls
		loader = _self.getControl(controlId)
		loader.setVisible(_bool)

		if 'focusId' in data:
			focusId = data['focusId']
			_self.setFocus(_self.getControl(focusId))


	def handleURLFromClick(self, url, show_title='', _self=None):
		if self.loading == True:
			return
	
		self.loading = True

		if(xbmc.getCondVisibility("System.HasModalDialog")):
			pass
		elif( xbmc.getCondVisibility("System.HasActiveModalDialog") ):
			xbmc.executebuiltin('Dialog.Close(all, true)')
		
		if url == 'menu':
			url = 'menu/tvselected'
		elif url == 'account':
			self.loading = False
			account = Account()
			account.doModal()
			del account

	 
		if show_title == '' and '?' not in url :
			dialog.ok(const.LANG(32001),  const.LANG(32008))
			return

		if len(url) > 3:
			title=''
			items=[]
			rtr = self.getListData(url=url)
			if rtr is None:
				return
			if url == 'menu/livetv_alternative':
				rtr = self.getListData(url=rtr['menu'][0]['key'])
			if 'search' in url and show_title is not None:
				rtr['title_prev'] = const.LANG(32009)+ show_title
		

			if 'menu' not in rtr:
				if 'key' not in rtr:
					dialog.ok(const.LANG(32003), rtr['msg'])
					return				

				self.loading = False


				if 'quality_urls' in rtr and len(rtr['quality_urls']) > 1:
					for key,val in enumerate(rtr['quality_urls']):
						items.append(val['title'])

					ret = dialog.select(const.LANG(32006), items)
					if ret < 0:
						_self.close()
						return
					if rtr['quality_urls'][ret]['title'] == 'Success': rtr['quality_urls'][ret]['title'] =''
					self.tvPlay(rtr['quality_urls'][ret], rtr['quality_urls'][ret]['key'], u"{0}".format(show_title), 0)
					return

				if 'title' in rtr:
					title=rtr['title']
					if rtr['title'] == 'Success': title =''
			
				self.tvPlay(rtr, rtr['key'], show_title, 0)
			
			else:
				#if not a video - creating new page 
				if url == 'menu/news' or  url == 'menu/home':
					slider = Sliders(rtr)
					slider.doModal()
					del slider

				else:
					self.is_new = True
					self.is_from_click = True

					info = {
						'url'			: url,
						'data'			: rtr,
					}
					thumb_view = ThumbView(info)
					thumb_view.doModal()
					del thumb_view
		return

	def tvPlay(self,info,  url, show_title, curr_time):
		title = '';
		
		if 'title' in info:
			title = info['title']
			if info['title'] == 'Success': title =''

		controller.url = url 

		#player.stop does not trigger onPlayBackStopped
		if self.player:				self.player.stopPlayer()
	
		self.player 				= Player()

		self.player.tracking_key 	= info['tracking_key'] if 'tracking_key' in info else ''
		self.player.is_live  		= self.isLive(url, info['tracking_key']);
		self.player.is_playing 		= True
		self.player.resume 			= curr_time if curr_time else 0
		

		#set inputstream.adaptive
		if _has_inputstream(): 
			li = xbmcgui.ListItem(label=show_title + ' ' + title)
			li.setProperty('inputstream', 'inputstream.adaptive')
			li.setProperty('inputstream.adaptive.manifest_type', 'hls')

			self.player.play(url, li)
			xbmc.sleep(500)

		# if video doesn't start because of inputstream_adaptive 
		# inputstream_adaptive  works from 17 and over
		if not self.player.isPlaying():
			self.player.play(url, xbmcgui.ListItem(label=show_title + ' ' + title))
		
		now 					= datetime.datetime.today()
		self.player.str_time 	= num(time.mktime(now.timetuple()))
		
		self.track()

	def createMenu(self):
		data = self.getListData(url=str(const.BASE_URL)) 
		if not data : return

		list_items = list()

		if 'menu' in data:
			menulist = data['menu']

			if not menulist:
				dialog.ok(const.LANG(32003), const.LANG(32004))
			if menulist: 

				menulist.append({'title': 'Профил', 'key':'account'})
				menulist.append({'title': 'Търсене', 'key':'search'})
				menulist.append({'title': 'изход', 'key':'logout'})
				
				for (key, val) in enumerate(menulist):
					label = val['title']

					item = xbmcgui.ListItem(u"{0}".format( label), label2=u"{0}".format(val['key']))
					list_items.append(item)


		self.menu_list = list_items


	def track(self):
		if not self.player:
			return

		tracking_key = self.player.tracking_key
		str_time = self.player.str_time
		counter = 0
		while self.player and self.player.is_playing:
			try:
				if self.player.isPlaying():
					self.player.info = {
						'key'			: tracking_key,
						'stream_started': str_time,
						'current_time'	:  num(self.player.getTime()),
					}
					if counter == 90:
						counter = 0
						self.player.reportPlaybackProgress(self.player.info, 'progress')
			except:
				log('!!!ERROR: playing file')

			counter += 1
			xbmc.sleep(1000)
		
		if self.player:
			del self.player

	def isLive(self, url, key):
		if const.LIVETV_PATH in url:
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

	def renderMenu(self, _self):

		if not self.menu_list :
			self.createMenu()
		self.list_instance = List()

		self.removeMenu()
		self.list_instance.doModal()


	def removeMenu(self):
		if self.list_instance:				
			self.list_instance.close()


	def getToken(self):
		token = None;

		if os.path.isfile(const.TOKEN_FILEPATH):
			fopen = open(const.TOKEN_FILEPATH, "r")
			temp_token = fopen.read()
			fopen.close()
			if temp_token:
				arr = temp_token.partition(" ")
				token = arr[0]
				if arr[2] and arr[2] != const.ADDON.getSetting('username'):
					token = '';
				temp_token = ''
	
		if not token: return
		return token

	def getListData(self, url, data=None, is_menu=None):

		if(not const.ADDON.getSetting('username')) or (not const.ADDON.getSetting('password')):
			dialog.ok(const.LANG(32003), const.LANG(32005))
			const.ADDON.openSettings(const.ID)
			login = self.login.logIN()
	
		cached = const.CACHE.get(str(url+'_'+const.ADDON.getSetting('username')+'_'+const.ADDON.getSetting('password')))
		token = self.getToken();

		if cached is not None and is_menu is None:
			return cached
		else:
			url = const.SITE_PATH + url
			token = self.getToken();

			if not token:
				ans = dialog.yesno(const.LANG(32003), 'За да използвате услугата трябва да се впишете')

				if ans :
					login = self.login.logIN();
					if not login:
						const.ADDON.openSettings(const.ID)
						login = self.login.logIN()
						token = self.getToken()
						if not login:
							xbmc.executebuiltin("ActivateWindow(Home)") 
							return
				else:							 return

			send = ({'token' : token})
			if data is not None:					send.update(data)

			data = self.getData(url, data=send)

		expiration=datetime.timedelta(hours=3)
		cleaned_url = cleanUpUrl(url)
		
		if const.LIVETV_PATH in cleaned_url and len(cleaned_url)> len(const.LIVETV_PATH):
			expiration=datetime.timedelta(minutes=15)

		const.CACHE.set(str(url+'_'+const.ADDON.getSetting('username')+'_'+const.ADDON.getSetting('password')), data, expiration=expiration)
		return data


	
	def getData(self, url, data):
		send = urllib.parse.urlencode(data).encode()
		self.request = urllib.request.Request(url, send, headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(const.VERSION)})

		try:
			response = urllib.request.urlopen(self.request)

		except urllib.error.HTTPError as e: 
			dialog.ok(const.LANG(32003),  e.code)
			return
		except urllib.error.URLError as e:
			dialog.ok(const.LANG(32003), const.LANG(32007))
			return
		
		data_result = response.read()
		xbmc.log('%s addon: %s' % (const.ADDON_NAME, url))

		try:
			res = json.loads(data_result)		
		except Exception as e:
			xbmc.log('%s addon: %s' % (const.ADDON_NAME, e))
			return
			
		if 'login_required' in res:
			if res['login_required']:
				ans = dialog.yesno(const.LANG(32212), const.LANG(32213))

				if ans :
					login = self.login.logIN();
				
					if login:
						if self.last_page_url:
							self.handleURLFromClick(self.last_page_url)
				else:
					return
		
		if 'token' in res:
			return res['token']
		
		if 'status' in res:
			if res['status'] == 'ok':
				return
				
			if 'login' in res and res['login'] == 'yes':
				dialog.ok(const.LANG(32003), res['msg'])
				return
	
			else:
				 
				if 'status' in res and res['status']== 204:
					dialog.ok(const.LANG(32003), res['msg'])
					return
				if 'subscription_required' in res and res['subscription_required'] == True:
					dialog.ok(const.LANG(32003), res['msg'])
					return
				if 'search' in url:
					dialog.ok(const.LANG(32003), res['msg'])
					return

				dialog.ok(const.LANG(32003), res['msg'])
				return
		
		return res


##########################################################################################
##										LOGIN  											##
##########################################################################################



class Login:
	token 			= ''""
	data 			= ''
	request 		= ''
	usr 			= ''
	pas 			= ''
	login_iteration = 0

	def logIN(self):
		self.usr = const.ADDON.getSetting('username');
		self.pas = const.ADDON.getSetting('password');

		if not self.usr or not self.pas:
			const.ADDON.openSettings(const.ID)
			return
		
		data = self.makeUserPass()
		self.token = controller.getData(const.SITE_LOGIN_PAGE, data)

		if self.token:
			self.writeInFile()
			return True
		return False
	
	def logOUT(self):
		fopen 	= open(const.TOKEN_FILEPATH, "w+")
		fopen.write(' ')
		fopen.close()

		data 	= self.makeUserPass()
		res 	= controller.getData(const.SITE_LOGOUT_PAGE, data)


	
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
		fopen = open(const.TOKEN_FILEPATH, "w+")
		fopen.write(self.token + " " +  const.ADDON.getSetting('username'))
		fopen.close()

	def openReadFile(self):

		if os.path.isfile(const.TOKEN_FILEPATH):
			fopen = open(const.TOKEN_FILEPATH, "r")
			temp_token = fopen.read()
			fopen.close()
			if temp_token:
				arr = temp_token.partition(" ")
				self.token = arr[0]
				if arr[2] and arr[2] != const.ADDON.getSetting('username'):
					self.token = '';
				temp_token = ''
		else:
			self.writeInFile()

controller = Controller()
controller.login = Login()



# ##########################################################################################
# ##									LIST VIEW 											##
# ##########################################################################################

# view used for the menu
# the list handles up and down automatically

class List(xbmcgui.WindowXMLDialog):
	C_LIST = 6001
	C_CANCEL = 6004

	#C_CANCEL is large fully transparent button on the right so the menu can be closed with a click outside of it  
	def __new__(cls):
		#specifing the proper xml
		#it is in /resources/skins/Default/720p/....
		return super(List, cls).__new__(cls, 'script-video-bgtime-tv-list.xml',const.ADDONPATH)

	def __init__(self):
		super(List, self).__init__()

	def onInit(self):
		self.updateList(controller.menu_list)		
		self.setFocus(self.getControl(self.C_LIST))

	def onClick(self, controlId):
		if controlId == self.C_CANCEL:
			self.close()

		if controlId == self.C_LIST:
			list_control 				= self.getControl(self.C_LIST)
			item_url 					= list_control.getSelectedItem().getLabel2()
			show_title 					= list_control.getSelectedItem().getLabel()
			controller.last_sel_on_list = num(list_control.getSelectedPosition())

			if item_url == 'logout':
				controller.login.logOUT()
				self.close()
				return

			elif item_url =='search' :
				controller.search(item_url, self)
				return
		
			controller.handleURLFromClick(item_url, show_title, self)
			controller.removeMenu()

	def onAction(self, action):
		act_id = action.getId()

		if act_id in[const.ACTION_RIGHT , const.KEY_NAV_BACK]:
			controller.removeMenu()

	def onFocus(self, controlId):
		pass

	def updateList(self, list_items):
		self.is_menu = False
		
		if not list_items:
			controller.createMenu()
			self.is_menu = True

		list_control = self.getControl(self.C_LIST)
		list_control.reset()
	
		try:
			list_control.addItems(list_items)
		except:
			log('!!!ERROR: rendering menu')

		if controller.last_sel_on_list >= 0:  list_control.selectItem(controller.last_sel_on_list)
		controller.changeControlVisibility(self, True, const.LOADER_FLAG)



# ##########################################################################################
# ##								Sliders VIEW 										  ##
# ##########################################################################################


#multiple horizontal list create sliders view for home page and news
# the list handle left and right automatically 
class Sliders(xbmcgui.WindowXML):
	C_LIST 			= 7001
	C_TITLE 		= 7009
	T_LIST			= 7101
	I_LIST			= 7201

	lists 			= [7001, 7002, 7003]
	idx_start		= 0
	idx_end			= 0
	rows 			= 3
	last_focused 	= None 
	items 			= list()
	visible 		= list()

	def __new__(cls, data):
		return super(Sliders, cls).__new__(cls, 'script-video-bgtime-tv-sliders.xml',const.ADDONPATH)

	def __init__(self, data):
		self.data = data
		super(Sliders, self).__init__()


	def onInit(self):

		if not self.data:
			self.data = controller.getListData(url=str(const.BASE_URL+'/home'), is_menu=True)


			if not self.data:
				self.close()
				return

		self.title = self.data['title_prev'] if 'title_prev' in self.data else ''
		self.items = self.data['menu'] if 'menu' in self.data else self.close()

		self.getControl(self.C_TITLE).setLabel('[B]'+self.title.upper()+'[/B]')

		try :
			controller.removeMenu()
		except:
			log('!!!ERROR:F no menu')

		self.visible 	= self.updateVisible(0)
		self.idx_end 	= len(self.items) - 1
		self.updateList(self.visible) 


	def onClick(self, controlId):
		if controlId in self.lists:
			list_control 	= self.getControl(controlId)
			item_url 		= list_control.getSelectedItem().getLabel2()
			show_title 		= list_control.getSelectedItem().getLabel()

			controller.handleURLFromClick(item_url, show_title, self)

	
	def onAction(self, action):
		act_id = action.getId()
		if act_id == const.ACTION_MOUSE_MOVE or act_id == 243:
			return

		if act_id in [const.ACTION_PARENT_DIR, const.KEY_NAV_BACK, const.ACTION_PREVIOUS_MENU, const.ACTION_SHOW_FULLSCREEN] :
			self.close()
			return

		curr_id = self.getFocusId()
		if not curr_id :
			return

		if act_id in [const.ACTION_UP, const.ACTION_DOWN] 	:	
			if curr_id in self.lists:	

				next_id = curr_id- 1 if act_id == const.ACTION_UP else curr_id+1 
				idx = self.getControl(self.I_LIST + (curr_id - self.C_LIST))
				idx = int(idx.getLabel())
	
				if idx >= self.idx_end: 		return

				if next_id not in self.lists:
					self.visible = self.updateVisible(idx-1)
					self.updateList(self.visible)
					return

				cont = self.getControl( curr_id + 1 )
				self.setFocus(self.getControl( next_id ))
				self.last_focused = cont
			elif curr_id == const.MENU_CONTROL:
				pass

		elif act_id == const.ACTION_RIGHT:	
			if curr_id == const.MENU_CONTROL:
				self.setFocus(self.last_focused)

		
	def onFocus(self, controlId):
		if controlId == const.MENU_CONTROL:
			self.setFocus(self.last_focused)
			controller.renderMenu(self)
			

	def focus(self):
		if self.last_focused:
			self.setFocus(self.last_focused)


	def updateVisible(self, start):
		_list = list()

		for x in range(start, start+self.rows):
			_list.append(x)

		return _list

	def updateList(self, visible):
		controller.loading 			= False
		curr_row 					= 0
		

		#using visible for the verticle scrolling of rows 
		if not visible:					visible = self.visible		

		for idx in visible:
			curr_list = self.items[idx]
			if not curr_list:			return

			try:
				_list = self.getControl(self.C_LIST+ curr_row)
			except:
				break 

			title = self.getControl(self.T_LIST + curr_row)
			title.setLabel('[B]'+curr_list['title'].upper()+'[/B]')
			self.getControl(self.I_LIST + curr_row).setLabel(str(idx))
			
			items = list()
			curr_row += 1
			for (key, val) in enumerate(curr_list['items']):
				label = val['title']

				item = xbmcgui.ListItem(label=u"{0}".format( label), label2=val['key'])
				item.setArt({'icon': val['thumb']})
				
				items.append(item)

			_list.reset()
	
			try:
				_list.addItems(items)
			except:
				log('!!!!!!!!!Error rendering list')

		self.setFocus(self.getControl(self.C_LIST))
		self.last_focused = self.getControl(self.C_LIST)




# ##########################################################################################
# ##							  ACCOUNT VIEW  		     							  ##
# ##########################################################################################



class Account(xbmcgui.WindowXML):
	C_TITLE 		= 6900;
	C_L_EMAIL 		= 6901;
	C_EMAIL 		= 6902;
	C_L_ACTIVE 		= 6903;
	C_ACTIVE 		= 6904;
	C_MENU 			= 6001;
	DEFAULT_CONTROL = 6905;
	C_EDIT_OLD 		= 6905;
	C_EDIT_NEW 		= 6906;
	C_EDIT_REP 		= 6908;
	C_SAVE_BTN 		= 6909;
	last_focused 	= None;
	login_iteration = 0;
	def __new__(cls):
		return super(Account, cls).__new__(cls, 'script-video-bgtime-tv-account.xml',const.ADDONPATH)

	def __init__(self):
		super(Account, self).__init__()

	def onInit(self):
		controller.changeControlVisibility(self, True, const.LOADER_FLAG)

		try:
			controller.removeMenu()
		except Exception as e:
			log(e)

		user_info =  self.getAccountInfo()
		if not user_info:
			return

		self.getControl(self.C_L_EMAIL).setLabel(const.LANG(32202))

		try:
			self.getControl(self.C_EMAIL).setLabel(user_info['username'])
		except:
			pass

		self.getControl(self.C_L_ACTIVE).setLabel(const.LANG(32203))
		if user_info['premium'] > 0:
			self.getControl(self.C_ACTIVE).setLabel(const.LANG(32204))
		else:
			self.getControl(self.C_ACTIVE).setLabel(const.LANG(32205))

		self.getControl(self.C_EDIT_OLD).setLabel(const.LANG(32206))
		self.getControl(self.C_EDIT_NEW).setLabel(const.LANG(32207))
		self.getControl(self.C_EDIT_REP).setLabel(const.LANG(32208))

		self.getControl(self.C_SAVE_BTN).setLabel(const.LANG(32209))
		inputs = list()


		self.setFocus(self.getControl(self.DEFAULT_CONTROL))

		pass

	def onClick(self, controlId):
		if controlId== 6909:
			self.changePassword(self.getControl(6905).getText(), self.getControl(6906).getText(), self.getControl(6908).getText() );

	
	def onAction(self, action):
		act_id = action.getId();
		if act_id in [107,243]:
			return

		if self.getFocusId() == 0:
			self.setFocus(self.getControl(self.DEFAULT_CONTROL))

		if act_id == const.KEY_NAV_BACK:
			self.close()



	def onFocus(self, controlId):
		if controlId == self.C_MENU:
			self.setFocus(self.last_focused)
			controller.renderMenu(self)
			return

		self.last_focused =  self.getControl(controlId)

	def focus(self):
		if self.last_focused:
			self.setFocus(self.last_focused)
		

	def changePassword(self, psw, new_pwd_1, new_pwd_2):
		
		if not psw or not new_pwd_1 or not new_pwd_2:
			dialog.ok(const.LANG(32003),const.LANG(32210))


		send = urllib.parse.urlencode({	
			'token'			: controller.getToken(),
			'pwd': psw,
			'new_pwd_1': new_pwd_1,
			'new_pwd_2': new_pwd_2
		}).encode()

		url = const.SITE_PATH +'settings/update'
		self.request = urllib.request.Request(url,send,  headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(const.VERSION)})

		try:
			response = urllib.request.urlopen(self.request)
		except Exception as e:
			dialog.ok(const.LANG(32003),  e.code)

		data_result = response.read()
		try:
			res = json.loads(data_result)

			if 'msg' in res: 			dialog.ok(const.LANG(32003), res['msg'])
			if 'error' not in res:		self.refreshData()
		except Exception as e:
			pass

	def refreshData(self):
		self.getControl(self.C_EDIT_OLD).setText('')
		self.getControl(self.C_EDIT_NEW).setText('')
		self.getControl(self.C_EDIT_REP).setText('')
	

	def getAccountInfo(self):
		# data ={	'token'			: controller.getToken() }
		send = urllib.parse.urlencode({	
			'token'			: controller.getToken() 
		}).encode()
		
		url = const.SITE_PATH +'settings/info'

		self.request = urllib.request.Request(url,send,  headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(const.VERSION)})

		try:
			response = urllib.request.urlopen(self.request)
		except urllib.error.HTTPError as e:
			dialog.ok(const.LANG(32003),  e.code)
			return
		except urllib.error.URLError as e:
			dialog.ok(const.LANG(32003), const.LANG(32007))
			return
		
		data_result = response.read()
		res = json.loads(data_result)
		
		if 'msg' in res:
				log(res['msg'])

		try:
			if 'data' in res:
					return res['data']
			else:
				login = controller.login.logIN();
				if self.login_iteration > 0:
					self.login_iteration = 0
					return
				
				self.login_iteration += 1
				return self.getAccountInfo()
		except Exception as e:
			pass


##########################################################################################
##									PLAYER 	 											##
##########################################################################################



class Player(xbmc.Player):
	info 			= None
	tracking_key 	= None
	is_live 		= None
	is_playing 		= False
	player_playing 	= "script-video-bgtime-tv-player-pause"
	player_paused 	= "script-video-bgtime-tv-player-play"
	gui 			= None
	resume 			= 0
	str_time 		= 0

	def __init__(self):
		xbmc.Player.__init__(self)

	def onIint(self):
		pass
		

	def onPlayBackStarted(self):
		self.checkTime(self.resume)

		if self.tracking_key is not None:
			now = datetime.datetime.today()
			
			str_time = 0
			current_time = 0
			
			if self.isPlaying():
				str_time = int(time.mktime(now.timetuple()))
				current_time = int(num(self.getTime()))
			
			self.info = {
				'key'			: self.tracking_key,
				'stream_started': str_time,
				'current_time'	: current_time,
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

	def stopPlayer(self):
		self.onPlayBackStopped()
		self.stop()

	def reportPlaybackProgress(self, info, action):
		token = controller.getToken()
		if info is None: return
		if self.tracking_key is not None:
			data ={	'token'			: token,
				'key'			: self.tracking_key,
				'stream_started': str(num(info['stream_started'])),
				'current_time'	: str(num(info['current_time'])),
				'action'		: action,
			}
			send = urllib.parse.urlencode(data).encode()
			request = urllib.request.Request(const.SITE_PATH +'tracking/report_playback', send, headers={"User-Agent" :  xbmc.getUserAgent()+ " BGTimeTV Addon " + str(const.VERSION)})
	

	def checkTime(self, curr_time):
		if curr_time > 0:
			try:
				self.seekTime(curr_time);
			except Exception as e:
				log(e)




##########################################################################################
##									THUMB VIEW 											##
##########################################################################################

# Grid view for displaying content
# Moving focus on the x and y and scrolling vertically
# Some pages have Filter button on row -1

class ThumbView(xbmcgui.WindowXML):
	C_TITLE 	= 6104
	C_LIST		= 6001
	C_CANCEL 	= 6004

	COLS 		= 0
	ROWS 		= 0
	TEXT_Y		= 50
	BOX_X		= 236
	BOX_Y		= 180
	TITLE_Y		= 40
	DESC_Y		= 0

	is_menu		= False
	is_sliders	= False
	data 		= False
	url 		= False

	def __new__(cls,data):
		return super(ThumbView, cls).__new__(cls, 'script-video-bgtime-tv-thumb-view.xml', const.ADDONPATH)

	def __init__(self, data):
		if data:
			self.data = data['data']
			self.url = data['url']
		super(ThumbView, self).__init__()

	def onInit(self):

		self.windowid 			= xbmcgui.getCurrentWindowId()
		self.pages 				= list()
		self.filters 			= list()
		self.is_new 			= True
		self.has_filter 		= False
		self.DEFAULT_CONTROL 	= None
		self.curr_page 			= None
		self.last_focused_elem	= None
		self.last_position		= None
		self.z_index_order		= None
		self.history 			= 0

		if not self.url:
			self.url = str(const.BASE_URL+'/home')

		controller.changeControlVisibility(self, False, const.LOADER_FLAG)
		self.createThumbView(self.data, self.url)
		
	def createThumbView(self, data, url):	
		img_width = self.BOX_X
		if controller.list_instance:
			try:
				controller.removeMenu()
			except Exception as e:
				log(e)

		data = self.data

		for page in controller.history:
			if page.url == url and self.windowid == page.windowid:
				self.history  = controller.history.index(page)
				self.pages = page.pages
				self.curr_page = page.idx
				self.ROWS = page.rows
				self.COLS = page.cols
				self.filters = page.filters
		
		if self.pages:
			if self.filters:
				controller.changeControlVisibility(self, False, const.FILTER_FLAG)
			
			self.updateView(self.curr_page, controller.history[self.history].x, controller.history[self.history].y)
			return
		else:
			controller.last_page_url = url
			if not data:
				pass
			
			if url == 'menu/bgmovies' or url[-4:] == 'voyo':
				self.BOX_X, self.BOX_Y = (190, 236+self.TEXT_Y)

			if 'livetv_alternative' in url or 'program' in url and 'bg_color' in data['menu'][0]:	
				self.BOX_X = self.BOX_Y;
				img_width = self.BOX_X;
				
				if len(data['title_prev']) <=2:
					data['title_prev'] 	= const.LANG(32010)+' '+ data['title_prev']+ const.LANG(32011)
			
			if 'title_prev' in data:
				control = self.getControl(self.C_TITLE)
				control.setLabel(u"{0}".format('[B]'+data['title_prev'].upper()+'[/B]'))
			
			controls 			= list()
			self.page_list 		= list()
			
			self.COLS 			= num((WIDTH-2*20)/(self.BOX_X+20))
			self.ROWS 			= num((HEIGHT-self.TITLE_Y-self.DESC_Y)/self.BOX_Y)
			panel_image 		='script-video-bgtime-tv-grey.png';
						
			x_margin 			= num((WIDTH - self.COLS*self.BOX_X - self.TITLE_Y-self.DESC_Y)/(self.COLS))
			y_margin 			= num((HEIGHT - self.ROWS*self.BOX_Y - self.TITLE_Y-self.DESC_Y)/(self.ROWS))
			x , y 				= (60, self.TITLE_Y+self.DESC_Y)
			x_step 				= num(x_margin + self.BOX_X)
			y_step 				= num(self.BOX_Y+y_margin)

			counter_y, counter_x= (0, 0)
			filters = None
			if 'filters' in data:
				filters = data['filters']
			elif 'timeshift' in data:
				filters = data['timeshift']
				
			if filters:
				for k, v in enumerate(filters):
					key =  v['key_full'] if 'key_full' in v else v['key']
					self.filters.append({
						'title'	: str(v['title']),
						'url'	: key
					})

				self.has_filter = True
				controller.changeControlVisibility(self, False, const.FILTER_FLAG)
		
			for k, v in enumerate(data['menu']):
				y_offset = y + y_step
				
				if k % (self.COLS*self.ROWS) == 0 and k > 0:
					self.pages.append(self.page_list)
					self.page_list = list()
					y = self.TITLE_Y+self.DESC_Y
					
					counter_y, counter_x =(0, 0)
				
				if 'title' in v: 			title = v['title']
				elif 'start' in v:  		title  = str(datetime.datetime.fromtimestamp( intv['start'] ).strftime('%d.%M.%y %H:%M'))
				
				title 					= u"{0}".format(title)
				bg_color 				= '0xFF000000'
				img_width 				= self.BOX_X
				center = 0
				
				if 'bg_color' in  v and 'is_voyo' not in v:
					bg_color 				= mi2hex(v['bg_color'])
					panel_image 			= 'script-video-bgtime-tv-white07.png'
					
					title = u"{0}".format(v['desc'])if v['desc']  else ''
					title = title.replace('\n', ' ')
					
				control 	= xbmcgui.ControlButton(x=x-10, y=y-10, width=self.BOX_X+20, height=self.BOX_Y+20, label='', focusTexture=os.path.join(const.IMAGE_PATH, 'script-video-bgtime-tv-gblue10.png'), noFocusTexture=os.path.join(const.IMAGE_PATH,  'script-video-bgtime-tv-darker-no.png'))
				thumb		= xbmcgui.ControlImage(x=x+ center, y=y, width = img_width,  height=self.BOX_Y-self.TEXT_Y, filename=v['thumb'])
				panel 		= xbmcgui.ControlImage(x=x, y=y, width = self.BOX_X, height=self.BOX_Y-self.TEXT_Y, filename=os.path.join(const.IMAGE_PATH, panel_image), colorDiffuse=bg_color)
				text 		= xbmcgui.ControlLabel(x=x, y=y+self.BOX_Y-self.TEXT_Y, width=self.BOX_X, height=self.TEXT_Y, label=title)
			
				if 'bg_color' in  v  and 'is_voyo' not in v:
					z_index_order 		= [panel, thumb, text]
					self.z_index_order 	= {'panel': 0, 'thumb': 1, 'text' :2}
				else:								
					z_index_order 		= [thumb, panel, text]
					self.z_index_order 	={'thumb': 0, 'panel': 1, 'text' :2}

				info = {
					'url'			: u"{0}".format( v['key']),
					'title'			: u"{0}".format( v['title']),
					'is_visible'	: False,
					'sec_controls' 	: z_index_order,
					'pos'			: [ counter_x, counter_y],
					'page' 			: len(self.pages)
				}
				
				self.page_list.append(const.ControlAndInfo(control, info))
				
				counter_x , x= counter_x+1, x+x_step
				
				if counter_x >= self.COLS or x > WIDTH - self.BOX_X:
					x, y, counter_x, counter_y = 60, y+y_step, 0, counter_y+1

			
			self.pages.append(self.page_list)	
			self.updateView(0)
			
			controller.history.append(const.URLandInfo(url, self.pages, self.filters, self.ROWS, self.COLS, xbmcgui.getCurrentWindowId()))
			self.history = len(controller.history)-1
		

	def updateView(self, page = None, x=None, y=None):
		controller.loading = False

		if page is None:
			page = 0
		if page < 0 or page>= len(self.pages):
			return 
		
		if controller.is_new is False and self.is_new is True and controller.last_sel_item is not None:
			if len(controller.last_sel_item)	> 0:
				el = controller.last_sel_item.pop()
				page, x, y = el['page'], el['pos'][0], el['pos'][1]
			
		controller.is_new = False
		self.is_new = False		

		try: 		
			self.clearView(self.curr_page)
		except:
			pass 
		
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

		if self.curr_page is not None and page < self.curr_page:
			y = self.pages[page][-1].pos[1]
		
		self.curr_page = page
		controller.changeControlVisibility(self, True, const.LOADER_FLAG)
		
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
			controller.removeMenu()
		except RuntimeError:	
			for con in controls:
				try:
					self.removeControl(con)
				except:	
					pass
	
	def onClick(self, controlId):
		control = self.getControl(controlId)

		if controlId == 6001:
			controller.renderMenu(self)
			return

		if controlId == controller.menu_id:
			list_control 				= self.getControl(controlId)
			item_url 					= list_control.getSelectedItem().getLabel2()
			show_title 					= list_control.getSelectedItem().getLabel()
			controller.last_sel_l_item 	= num(list_control.getSelectedPosition())

			self.clearView(self.curr_page)
			controller.handleURLFromClick(item_url, show_title, self)

			return

		if controlId == const.FILTER:
			 
			filters = self.getFilters()
			select 	= dialog.select(const.LANG(32006), filters)
			if select < 0: return
			
			if controller.last_sel_item is None:
				controller.last_sel_item = [{'page':self.curr_page,'pos': [0,0]}]
			else:
				controller.last_sel_item = controller.last_sel_item + [{'page':self.curr_page,'pos': [0,0]}]
			
			controller.handleURLFromClick(self.filters[num(select)]['url'], self.filters[num(select)]['title'], self)
			return

		
		curr_elem = self.getInfoFromControl(control, self.curr_page)
		
		if curr_elem is None:
			return
		
		self.clearView(self.curr_page)
		
		if controller.last_sel_item is None:
			controller.last_sel_item = [{'page':self.curr_page,'pos': curr_elem.pos}]
		else:
			controller.last_sel_item = controller.last_sel_item + [{'page':self.curr_page,'pos': curr_elem.pos}]

		controller.handleURLFromClick(curr_elem.url, curr_elem.title, self)

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
		new_elem = None
		for elem in self.pages[page]:
			if elem.control.getId() == control.getId():
				new_elem = elem
		
		return new_elem

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
		except : 
			pass

	def onAction(self, action):
		focused_elem = None
		act_id =  action.getId()
		if act_id in [const.ACTION_MOUSE_MOVE, 243]:
			return
		
		if act_id in [const.ACTION_PARENT_DIR, const.KEY_NAV_BACK, const.ACTION_PREVIOUS_MENU, const.ACTION_SHOW_FULLSCREEN] :
			controller.removeMenu()
			self.close()
			return
		if act_id in [const.ACTION_UP, const.ACTION_LEFT, const.ACTION_RIGHT, const.ACTION_DOWN, const.ACTION_MOUSE_WHEEL_UP, const.ACTION_MOUSE_WHEEL_DOWN, const.ACTION_GESTURE_SWIPE_LEFT, const.ACTION_GESTURE_SWIPE_RIGHT, const.ACTION_GESTURE_SWIPE_DOWN, const.ACTION_GESTURE_SWIPE_UP]:
			try:	
				focused_elem = self.getFocus()
			except:
				'excpt'
				if self.last_position is not None:
					focused_elem = self.getControlFromPosition(self.last_position[0], self.last_position[1], self.curr_page)
				elif self.DEFAULT_CONTROL is not None:
					focused_elem = self.DEFAULT_CONTROL

			if focused_elem is None:
				return
			
			curr_el = self.getInfoFromControl(focused_elem, self.curr_page)
			
			
			if curr_el is None:
				if focused_elem.getId()!=const.FILTER and focused_elem.getId()!=controller.menu_id:								return
				elif focused_elem.getId()==const.FILTER and act_id in[const.ACTION_LEFT, const.ACTION_UP, const.ACTION_RIGHT]:						return
				elif focused_elem.getId()==controller.menu_id and act_id in[const.ACTION_LEFT, const.ACTION_UP, const.ACTION_DOWN]:			return
			

			if act_id == const.ACTION_UP: 		
				self.up(  focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == const.ACTION_LEFT:		
				self.left(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == const.ACTION_RIGHT:
				if focused_elem.getId() == controller.menu_id:	
					controller.removeMenu()
					self.setFocus(self.last_focused_elem.control)															
					return 	
				self.right(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			elif act_id == const.ACTION_DOWN:
				if focused_elem.getId() == const.FILTER:
					return self.setFocus(self.last_focused_elem.control)
				self.down(focused_elem, curr_el,curr_el.pos[0], curr_el.pos[1], curr_el.page )

			if act_id in [const.ACTION_MOUSE_WHEEL_UP, const.ACTION_GESTURE_SWIPE_DOWN, const.ACTION_PAGE_UP]:  
				self.updateView(self.curr_page-1)

			elif act_id in [const.ACTION_MOUSE_WHEEL_DOWN, const.ACTION_GESTURE_SWIPE_UP, const.ACTION_PAGE_DOWN]:  
				self.updateView(self.curr_page+1)

			self.last_focused_elem = curr_el

	# Search acording to coordinates
	def up(self, cont, curr_el, x, y, page):
		if cont is None:
			if self.DEFAULT_CONTROL:
				return self.setFocus()

		if page == 0 and y==0:		
			if self.has_filter == True:	
				self.setFocus(  self.getControl(const.FILTER)  )
		if y == 0: 																		
			return self.updateView(self.curr_page-1, x)

		return  self.setFocus(  self.getControlFromPosition(x, y-1, page)  )
		

	def down(self, cont, curr_el, x, y, page):
		if page == len(self.pages)-1:
			if y == self.pages[page][-1].pos[1]:
				return
			if y == self.pages[page][-1].pos[1]-1 and x >  self.pages[page][-1].pos[0]:
				return
		
		if cont is None:			
			return self.setFocus()
		if y >= self.ROWS-1: 															
			return self.updateView(self.curr_page+1, x)

		return  self.setFocus(self.getControlFromPosition(x, y+1, page))
		

	def left(self, cont, curr_el, x, y, page):
		if cont is None: 
			if self.DEFAULT_CONTROL:
				return self.setFocus()
		if x <= 0: 
			controller.renderMenu(self)
			self.setFocus(const.MENU_CONTROL)
			return
				
		return self.setFocus(  self.getControlFromPosition(x-1, y, page)  )		

	def right(self, cont, curr_el, x, y, page):
		if cont is None:
			return self.setFocus()

		last = self.pages[-1][-1]
		if page == len(self.pages) - 1 and y == last.pos[1] and x==last.pos[0]:
			return self.setFocus(cont)
		if x >= self.COLS-1: 
			if y+1 <= self.ROWS-1:
				return self.setFocus(  self.getControlFromPosition(0 , y+1, page)  )	
			else:																		
				return self.updateView(self.curr_page+1, 0)

		return self.setFocus(  self.getControlFromPosition(x+1, y, page)  )



