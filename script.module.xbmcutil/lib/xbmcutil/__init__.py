"""
	###################### xbmcutil ######################
	Copyright: (c) 2013 William Forde (willforde+xbmc@gmail.com)
	License: GPLv3, see LICENSE for more details
	
	This file is part of xbmcutil
	
	xbmcutil is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.
	
	xbmcutil is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
	
	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Funtion for Checking the subAction Params
def sysCheck():
	# Fetch SubAction Param
	subAction = plugin.actions[1].lower()
	
	# Check Subaction
	if subAction == "videohosts":
		# Import VideoHosts APIs and Call Required Class
		import videohostsAPI
		try:   func = getattr(videohostsAPI, plugin.actions[2])
		except AttributeError: pass
		else:  func()
	
	elif subAction == "direct" or subAction == "source":
		# Import listitem Module and Exacute
		from listitem import PlayMedia
		PlayMedia()
	
	elif subAction == "opensettings":
		# Open Settings Dialog
		plugin.openSettings()
		plugin.refreshContainer()

# Class For Fetching plugin Information
class Info(object):
	import xbmcaddon, xbmcplugin, xbmcgui, xbmc, urllib, sys, os
	_suppressErrors = False
	_traceback = None
	_xbmcvfs = None
	class Error(Exception):
		exceptionName = 30909 # UnexpectedError
		def __init__(self, errorCode=0, errorMsg=""):
			if errorMsg: plugin.setDebugMsg(self.exceptionName, errorMsg)
			self.errorCode = errorCode
			self.errorMsg = errorMsg
		
		def __str__(self): return self.errorMsg
		def __int__(self): return self.errorCode

	class ScraperError(Error):  exceptionName = 30915 # ScraperError
	class URLError(Error):      exceptionName = 30916 # URLError
	class CacheError(Error):    exceptionName = 30917 # CacheError
	class ParserError(Error):   exceptionName = 30918 # ParserError
	class YoutubeAPI(Error):    exceptionName = 30919 # YoutubeAPI
	class videoResolver(Error): exceptionName = 30920 # videoResolver
	
	@property
	def xbmcvfs(self):
		if self._xbmcvfs: return self._xbmcvfs
		else:
			self._xbmcvfs = __import__("xbmcvfs")
			return self._xbmcvfs
	
	@property
	def traceback(self):
		if self._traceback: return self._traceback
		else:
			self._traceback = __import__("traceback")
			return self._traceback
	
	def error_handler(cls, function):
		# Wrapper for Scraper Function
		def wrapper(*arguments, **keywords):
			try: response = function(*arguments, **keywords)
			except cls.Error as e:
				if e.errorCode: cls.setNotification(e.exceptionName, e.errorCode, icon="error")
				cls.print_traceback()
				return False
			except:
				cls.setNotification(30909, 30974, icon="error")
				cls.print_traceback()
				return False
			else:
				if response: return response
				else:
					cls.setNotification(cls._addonName, 33077, icon="error")
					return False
		
		# Return Wrapper
		return wrapper
	
	def __init__(self):
		sysargv = self.sys.argv
		# Initiate Local and Global plugin Objects
		self._scriptData = self.xbmcaddon.Addon(id="script.module.xbmcutil")
		self._addonData = self.xbmcaddon.Addon(id=sysargv[0][9:-1])
		self._addonName = self._addonData.getAddonInfo("name")
		
		# Fetch Dict of Params
		self._Params = self.get_params(sysargv[2])
		self.__dict__.update(self._Params)
		
		# Create Local Methods of Global Functions
		self.openSettings = self._addonData.openSettings
		self.getSetting = self._addonData.getSetting
		self.setSetting = self._addonData.setSetting
		self.translatePath = self.xbmc.translatePath
		self.dialogBox = self.xbmcgui.Dialog
		self.getstr = self.getLocalizedString
		self.handelOne = int(sysargv[1])
		self.handelZero = sysargv[0]
		self.log = self.xbmc.log
		
		# Create Third Handel
		self.actions = self.get("action","Initialize").split(".")
		if sysargv[2]: self.handelTwo = self.handelZero + sysargv[2] + "&"
		else: self.handelTwo = self.handelZero + "?"
		self.sys.path.append(self.getLibPath())
		
		# Display plugin Name in Debug Log
		self.skinID = self.xbmc.getSkinDir()
		self.log("### %s ###" % self._addonName)
		self.viewModes = {'skin.ace':			{'files': {'1': 59, '2': 56},		'episodes': {'1': 59, '2': 64}},
						  'skin.aeonmq5':		{'files': {'1': 59, '2': 56},		'episodes': {'1': 59, '2': 64}},
						  'skin.aeon.nox':		{'files': {'1': 52, '2': 500},		'episodes': {'1': 518, '2': 500}},
						  'skin.amber':			{'files': {'1': None, '2':53},		'episodes': {'1': 52, '2': 53}},
						 #'skin.back-row':		{'files': {'1': None, '2': None},	'episodes': {'1': None, '2': None}},
						  'skin.bello':			{'files': {'1': 50, '2': 56},		'episodes': {'1': 50, '2': 561}},
						  'skin.carmichael':	{'files': {'1': 50, '2': 51},		'episodes': {'1': 50, '2': 56}},
						  'skin.confluence':	{'files': {'1': 51, '2': 500},		'episodes': {'1': 51, '2': 500}},
						 #'skin.diffuse':		{'files': {'1': None, '2': None},	'episodes': {'1': None, '2': None}},
						  'skin.droid':			{'files': {'1': 50, '2': 55},		'episodes': {'1': 50, '2': 51}},
						  'skin.hybrid':		{'files': {'1': 50, '2': 500},		'episodes': {'1': 50, '2': 500}},
						  'skin.metropolis':	{'files': {'1': 503, '2': None},	'episodes': {'1': 55, '2': 59}},
						 #'skin.nbox':			{'files': {'1': None, '2': None},	'episodes': {'1': None, '2': None}},
						  'skin.pm3-hd':		{'files': {'1': 550, '2': 53},		'episodes': {'1': 550, '2': 53}},
						  'skin.quartz':		{'files': {'1': 52, '2': None},		'episodes': {'1': 52, '2': None}},
						  'skin.re-touched':	{'files': {'1': 50, '2': 500},		'episodes': {'1': 550, '2': 500}},
						  'skin.simplicity':	{'files': {'1': 50, '2': 500},		'episodes': {'1': 532, '2': 505}},
						  'skin.transparency':	{'files': {'1': 52, '2': 53},		'episodes': {'1': 52, '2': 53}},
						  'skin.xeebo':			{'files': {'1': 50, '2': 51},		'episodes': {'1': 53, '2': 51}},
						  'skin.xperience-more':{'files': {'1': None, '2': None},	'episodes': {'1': 50, '2': 68}},
						  'skin.xperience1080':	{'files': {'1': 50, '2': 500},		'episodes': {'1': 50, '2': 500}},
						  'skin.xtv-saf':		{'files': {'1': 50, '2': 58},		'episodes': {'1': 50, '2': 58}}}
	
	def get_params(self, params):
		# Loop Each Quary and add to Params Dict
		if params:
			worker = {}
			unquoter = self.urllib.unquote_plus
			if params.startswith("?"): params = params[1:]
			for part in params.split("&"):
				try: key, value = part.split("=")
				except: continue
				if value: worker[key] = unquoter(value)
			return worker
		else:
			return {}
	
	def getAddonSetting(self, id, key):
		try: addonData = self.xbmcaddon.Addon(id)
		except: return ""
		else: return addonData.getSetting(key)
	
	def getLocalizedString(self, id):
		if   id >= 30000 and id <= 30899: return self._addonData.getLocalizedString(id)
		elif id >= 30900 and id <= 30999: return self._scriptData.getLocalizedString(id)
		else: return self.xbmc.getLocalizedString(id)
	
	def getQuality(self):
		return self._addonData.getSetting("quality")
	
	def getSettingInt(self, id):
		return int(self.getSetting(id))
	
	def getSettingBool(self, id):
		return self.getSetting(id) == "true"
	
	def getAddonInfo(self, id, local=True):
		if local: return self._addonData.getAddonInfo(id)
		else: return self._scriptData.getAddonInfo(id)
	
	def getAuthor(self):
		return self._addonData.getAddonInfo("author")
	
	def getChangelog(self):
		return self._addonData.getAddonInfo("changelog")
	
	def getDescription(self):
		return self._addonData.getAddonInfo("description")
	
	def getDisclaimer(self):
		return self._addonData.getAddonInfo("disclaimer")
	
	def getId(self):
		return self._addonData.getAddonInfo("id")
	
	def get_name(self):
		return self._addonData.getAddonInfo("name")
	
	def getStars(self):
		return self._addonData.getAddonInfo("stars")
	
	def getSummary(self):
		return self._addonData.getAddonInfo("summary")
	
	def getType(self):
		return self._addonData.getAddonInfo("type")
	
	def getVersion(self):
		return self._addonData.getAddonInfo("version")
	
	def getPath(self, local=True):
		''' Returns Full Path to the plugin Location '''
		return self.getAddonInfo("path", local)
	
	def getLibPath(self):
		''' Returns Full Path to the plugin Library Location '''
		return self.os.path.join(self.getAddonInfo("path", True), "resources", "lib")
	
	def getProfile(self, local=True):
		''' Returns Full Path to the Addons Saved Data Location '''
		return self.translatePath(self.getAddonInfo("profile", local))
	
	def get_image_location(self, local=True):
		return self.os.path.join(self.getPath(local), "resources", "media", "%s")
	
	def get_fanart_image(self):
		return self.translatePath(self._addonData.getAddonInfo("fanart"))
	
	def getIcon(self):
		return self.xbmc.translatePath(self._addonData.getAddonInfo("icon"))
	
	def tempPath(self):
		return self.translatePath("special://home/temp/")
	
	def print_traceback(self):
		# Print Exception Traceback to log
		print self.traceback.format_exc()
	
	def dialogYesNo(self, heading, line1, line2="", line3="", nolabel="", yeslabel=""):
		'''
			Returns True if 'Yes' was pressed, else False.
			
			heading        : dialog heading.
			line1          : line #1 text.
			line2          : line #2 text.
			line3          : line #3 text.
			nolabel        : label to put on the no button.
			yeslabel       : label to put on the yes button.
		'''
		box = self.dialogBox()
		return box.yesno(heading, line1, line2, line3, nolabel, yeslabel)
	
	def dialogOK(self, heading, line1, line2="", line3=""):
		'''
			Returns True if 'Ok' was pressed, else False.
			
			heading        : dialog heading.
			line1          : line #1 text.
			line2          : line #2 text.
			line3          : line #3 text.
		'''
		box = self.dialogBox()
		return box.ok(heading, line1, line2, line3)
	
	def dialogBrowse(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default="", enableMultiple=False):
		'''
			type : integer - the type of browse dialog.
			heading : string or unicode - dialog heading.
			shares : string or unicode - from sources.xml. (i.e. 'myprograms')
			mask : [opt] string or unicode - '|' separated file mask. (i.e. '.jpg|.png')
			useThumbs : [opt] boolean - if True autoswitch to Thumb view if files exist.
			treatAsFolder : [opt] boolean - if True playlists and archives act as folders.
			default : [opt] string - default path or file.
			enableMultiple : [opt] boolean - if True multiple file selection is enabled.
		'''
		box = self.dialogBox()
		return box.browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, enableMultiple)
	
	def dialogSelect(self, heading, list, autoclose=0):
		'''
			heading : string - dialog heading.
			list : string list - list of items.
			autoclose : [opt] integer - milliseconds to autoclose dialog. default=0(do not autoclose)
		'''
		box = self.dialogBox()
		return box.select(heading, list, autoclose)
	
	def keyBoard(self, default="", heading="", hidden=False):
		'''
		default        : default text entry.
		heading        : keyboard heading.
		hidden         : True for hidden text entry.
		'''
		kb = self.xbmc.Keyboard(default, heading, hidden)
		kb.doModal()
		if kb.isConfirmed() and kb.getText(): return kb.getText()
		else: return None
	
	def setNotification(self, heading, message, icon="error", time=5000, sound=True):
		'''
			heading : string - dialog heading.
			message : string - dialog message.
			icon : [opt] string - icon to use.
			time : [opt] integer - time in milliseconds (default 5000)
			sound : [opt] bool - play notification sound (default True)
		'''
		
		# Check if Errors are Suppressed
		if icon == "error":
			if self._suppressErrors == True: return
			else: self._suppressErrors = True
		
		# Fetch Localized String if Needed
		if type(heading) is int: heading = self.getLocalizedString(heading)
		if type(message) is int: message = self.getLocalizedString(message)
		
		# Send Error Messisg to Display
		#box = self.dialogBox
		#box.notification(heading, message, icon, time, sound)
		
		# Send Error Messisg to Display
		exeString = "xbmc.Notification(%s,%s,%i)" % (heading, message, time)
		self.xbmc.executebuiltin(exeString)
	
	def refreshContainer(self):
		self.xbmc.executebuiltin("Container.Refresh")
	
	def executePlugin(self, pluginUrl):
		""" Execute XBMC plugin """
		self.xbmc.executebuiltin("XBMC.RunPlugin(%s)" % pluginUrl)
	
	def executeAddon(self, addonID):
		""" Execute XBMC Addon """
		self.xbmc.executebuiltin("XBMC.RunAddon(%s)" % addonID)
	
	def setviewMode(self, viewMode):
		""" Sets XBMC View Mode, Identified by View Mode ID """
		self.xbmc.executebuiltin("Container.SetViewMode(%d)" % viewMode)
	
	def setDebugMsg(self, exceptionName="", errorMsg=""):
		''' Recives a *list of mesages to print '''
		if type(exceptionName) is int: exceptionName = self.getLocalizedString(exceptionName)
		if type(errorMsg) is int: errorMsg = self.getLocalizedString(errorMsg)
		self.xbmc.log("%s: %s" % (exceptionName, errorMsg))
	
	def update(self, dicts):
		self._Params.update(dicts)
	
	def __contains__(self, key):
		return key in self._Params
	
	def __setitem__(self, key, value):
		self._Params[key] = value
	
	def __getitem__(self, key):
		return self._Params[key]
	
	def __delitem__(self, key):
		del self._Params[key]
	
	def __len__(self):
		return len(self._Params)
	
	def get(self, key, failobj=None):
		if key in self._Params: return self._Params[key]
		else: return failobj
	
	def setdefault(self, key, failobj=None):
		if key in self._Params: return self._Params[key]
		else:
			self._Params[key] = failobj
			return failobj

# Set plugin ID
plugin = Info()
