"""
	###################### xbmcutil ######################
	Copyright: (c) 2013 William Forde (willforde+kodi@gmail.com)
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
	if subAction == u"videohosts":
		# Import VideoHosts APIs and Call Required Class
		import videohostsAPI
		try:   func = getattr(videohostsAPI, plugin.actions[2])
		except AttributeError: pass
		else:  func()
	
	elif subAction == u"direct":
		# Import PlayMedia Module and Exacute
		from listitem import PlayDirect
		PlayDirect()
	
	elif subAction == u"source":
		# Import PlayMedia Module and Exacute
		from listitem import PlaySource
		PlaySource()
	
	elif subAction == u"opensettings":
		# Open Settings Dialog
		plugin.openSettings()
		plugin.executebuiltin("Container.Refresh")
		plugin.destroyer()
	
	elif subAction == u"search":
		# Call storageDB and exacute saved searches
		from xbmcutil import listitem
		listitem.SavedSearches()
	
	elif subAction == u"setviewmode":
		# Call viewModes and diskplay options
		from xbmcutil import viewModes
		viewModes.Selector(plugin.actions[2])
		plugin.destroyer()

class Addon(object):
	def getAddonInfo(self, id):
		""" # List of possible ids.
			author, changelog, description, disclaimer,
			fanart, icon, id, name, path, profile,
			stars, summary, type, version
		"""
		# Call parent method and convert response to unicode
		return self._addonData.getAddonInfo(id).decode("utf8")
	
	def getuni(self, id):
		""" Return localized unicode string for selected id """
		if   id >= 30000 and id <= 30899: return self.getLocalizedString(id)
		elif id >= 32800 and id <= 32999: return self._scriptData.getLocalizedString(id)
		else: return self.xbmc.getLocalizedString(id)
	
	def getstr(self, id):
		""" Return localized unicode string for selected id """
		if   id >= 30000 and id <= 30899: return self.getLocalizedString(id).encode("utf8")
		elif id >= 32800 and id <= 32999: return self._scriptData.getLocalizedString(id).encode("utf8")
		else: return self.xbmc.getLocalizedString(id).encode("utf8")
	
	def getLocalPath(self):
		return self.getAddonInfo("path")
	
	def getGlobalPath(self):
		return self._scriptData.getAddonInfo("path").decode("utf8")
	
	def getProfile(self):
		""" Returns full unicode path to the addons saved data location """
		if self._profile: return self._profile
		else:
			self._profile = _profile = self.translatePath(self.getAddonInfo("profile"))
			if not self.os.path.exists(_profile): self.os.makedirs(_profile)
			return _profile
	
	def getGlobalProfile(self):
		""" Returns full unicode path to the Script saved data location """
		if self._gprofile: return self._gprofile
		else:
			self._gprofile = _gprofile = self.translatePath(self._scriptData.getAddonInfo("profile"))
			if not self.os.path.exists(_gprofile): self.os.makedirs(_gprofile)
			return _gprofile
	
	def getFanart(self):
		fanart = self.translatePath(self.getAddonInfo("fanart"))
		if self.os.path.exists(fanart): return fanart
		else: return ""
	
	def getAddonSetting(self, id, key):
		""" Return setting for selected addon """
		return self.xbmcaddon.Addon(id).getSetting(key)
	
	def getAddonData(self, id, key):
		""" Return Addon info for specified addon """
		return self.xbmcaddon.Addon(id).getAddonInfo(key)
	
	def getSettingInt(self, id):
		""" Return Integer for settings """
		return int(self.getSetting(id))
	
	def getSettingBool(self, id):
		""" Return boolean for setting """
		return self.getSetting(id) == u"true"
	
	def setSetting(self, key, value):
		""" Set Addon Setting """
		self._addonData.setSetting(key, value)
	
	def openSettings(self):
		""" Open Addon Settings Dialog """
		self._addonData.openSettings()
	
	def getIcon(self):
		""" Return unicode path to addon icon """
		return self.translatePath(self.getAddonInfo("icon"))
	
	def translatePath(self, path):
		""" Return translated special paths as unicode """
		if path[:10] == "special://": return self.xbmc.translatePath(path).decode("utf8")
		else: return path

class Dialog(object):
	def dialogSelect(self, heading, list, autoclose=0):
		""" Returns the position of the highlighted item as an integer. """
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.select(heading, list, autoclose)
	
	def dialogNumeric(self, type, heading, default=""):
		""" Returns the entered data as a unicode string """
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.numeric(type, heading, default).decode("utf8")
	
	def browseMultiple(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
		""" Returns tuple of marked filenames as a unicode string """
		dialogbox = self.xbmcgui.Dialog()
		return tuple([filename.decode("utf8") for filename in dialogbox.browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, True)])
	
	def browseSingle(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
		""" Returns filename and/or path as a unicode string to the location of the highlighted item """
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, False).decode("utf8")
	
	def keyBoard(self, default="", heading="", hidden=False):
		""" Return User input as a unicode string """
		kb = self.xbmc.Keyboard(default, heading, hidden)
		kb.doModal()
		if kb.isConfirmed() and kb.getText(): return kb.getText().decode("utf8")
		else: return None
	
	def dialogSearch(self, urlString=None):
		""" Open KeyBoard Dialog and return input with urlString """
		ret = self.keyBoard("", self.getstr(16017), False) # 16017 = Enter Search String
		if ret and urlString: return urlString % ret
		elif ret: return ret
		else:
			self.debug("User Cannceled The Search KeyBoard Dialog")
			raise plugin.URLError(None)
	
	def sendNotification(self, heading, message, icon="info", time=5000, sound=True):
		""" Send a notification to xbmc to be displayed """
		if isinstance(heading, int): heading = self.getstr(heading)
		elif isinstance(heading, unicode): heading = heading.encode("utf8")
		if isinstance(message, int): message = self.getstr(message)
		elif isinstance(message, unicode): message = message.encode("utf8")
		if icon == "info": icon = self.getIcon()
		
		# Send Error Message to Display
		dialog = self.xbmcgui.Dialog()
		dialog.notification(heading, message, icon, time, sound)

# Class For Fetching plugin Information
class Info(Addon, Dialog):
	import xbmcplugin, xbmcaddon, xbmcgui, xbmc, urllib, sys, os
	_suppressErrors = False
	_traceback = None
	_xbmcvfs = None
	_devmode = True
	_profile = None
	_gprofile = None
	
	# Create Addon Object to the System Script Module
	_scriptData = xbmcaddon.Addon("script.module.xbmcutil")
	_addonData = xbmcaddon.Addon()
	getLocalizedString = _addonData.getLocalizedString
	getSetting = _addonData.getSetting
	addonID = _addonData.getAddonInfo("id")
	
	class Error(Exception):
		exceptionName = 32851 # UnexpectedError
		def __init__(self, errorMsg="", debugMsg=""):
			self.errorMsg = errorMsg
			self.debugMsg = debugMsg
	
	class URLError(Error):      exceptionName = 32807 # URLError
	class ScraperError(Error):  exceptionName = 32824 # ScraperError
	class CacheError(Error):    exceptionName = 32808 # CacheError
	class ParserError(Error):   exceptionName = 32821 # ParserError
	class YoutubeAPI(Error):    exceptionName = 32822 # YoutubeError
	class videoResolver(Error): exceptionName = 32823 # ResolverError
	
	def destroyer(self):
		""" Prevent Memory leak by Manually Removing references to the below xbmcaddon objects """
		del Info.getLocalizedString
		del Info.getSetting
		del Info._addonData
		del Info._scriptData
	
	def error_handler(cls, function):
		# Wrapper for Scraper Function
		def wrapper(*arguments, **keywords):
			try: response = function(*arguments, **keywords)
			except (UnicodeEncodeError, UnicodeDecodeError) as e:
				cls.sendNotification(32852, e.reason, icon="error") # 32852 = Unicode Error
				cls.severe("A Severe Unicode Encode/Decode Error was raise, unable to continue", traceback=True)
				cls._suppressErrors = True
			
			except ImportError as e:
				cls.sendNotification(32851, e.message, icon="error") # 32852 = Unexpected Error
				cls.severe("An unexpected python exception was raised, unable to continue", traceback=True)
				cls._suppressErrors = True
			
			except cls.Error as e:
				exceptionName = cls.getstr(e.exceptionName)
				if e.debugMsg: cls.severe("%s:%s" % (exceptionName, e.debugMsg))
				if e.errorMsg:
					cls.sendNotification(exceptionName, e.errorMsg, icon="error")
					cls.severe("%s:%s" % (exceptionName, e.errorMsg))
					cls._suppressErrors = True
				
				# print TraceBack to Kodi log
				cls.severe("Unrecoverable Error", traceback=True)
			
			except:
				cls.sendNotification(32851, 32853, icon="error")
				cls.severe("A Severe Unhandled Error was raise, unable to continue", traceback=True)
				cls._suppressErrors = True
			
			else:
				if response: return response
				elif response is not False:
					cls.sendNotification(cls.getAddonInfo("name"), 33077, icon="error")
					cls.debug("No Video information was found")
		
		# Return Wrapper
		return wrapper
	
	@property
	def xbmcvfs(self):
		if self._xbmcvfs: return self._xbmcvfs
		else:
			self._xbmcvfs = xbmcvfs = __import__("xbmcvfs")
			return xbmcvfs
	
	@property
	def traceback(self):
		if self._traceback: return self._traceback
		else:
			self._traceback = traceback = __import__("traceback")
			return traceback
	
	def __init__(self):
		# Check for Quary handles
		argv = self.sys.argv
		if argv[0].startswith("plugin://"):
			# Fetch system elements
			self.handleZero = handleZero = argv[0]
			self.handleOne = int(argv[1])
			self.handleTwo = handleTwo = argv[2]
			
			# Initiate Local and Global xbmcAddon Objects
			self.sys.path.append(self.os.path.join(self.getAddonInfo("path"), u"resources", u"lib"))
			
			# Check for Quary handle
			if handleTwo:
				# Fetch Dict of Params
				self._Params = self.parse_qs(handleTwo)
				# Fetch list of actions
				self.actions = self._Params.get("action",u"Initialize").split(".")
				# Create Plugin Handle No Three
				self.handleThree = "%s%s&" % (handleZero, handleTwo.replace("refresh","_"))
				# Log values for debug
				self.debug(handleTwo)
			else:
				# Create empty params
				self._Params = {}
				# Create Initialize action
				self.actions = [u"Initialize"]
				# Create Plugin Handle Three
				self.handleThree = "%s?" % handleZero
		
		# Else Must be running from script so set values to defaults
		else: argv[0] = "system"; self.actions = argv
	
	def debug(self, msg): self.log(msg, 0)
	def info(self, msg): self.log(msg, 1)
	def notice(self, msg): self.log(msg, 2)
	def warning(self, msg): self.log(msg, 3)
	def error(self, msg, traceback=False): self.log(msg, 4, traceback)
	def severe(self, msg, traceback=False): self.log(msg, 5, traceback)
	def fatal(self, msg, traceback=False): self.log(msg, 6, traceback)
	def log(self, msg, level=2, traceback=False):
		if level < 2 and self._devmode is True: level = 7
		if isinstance(msg, unicode): msg = msg.encode("utf8")
		if traceback is True: msg = "%s\n%s" % (msg, self.traceback.format_exc())
		self.xbmc.log("[%s] %s" % (self.addonID, str(msg)), level)
	
	def setViewMode(self, mode):
		""" Returns selected View Mode setting if available """
		settingKey = "%s.%s.view" % (self.xbmc.getSkinDir(), mode)
		viewMode = self.getSetting(settingKey)
		if viewMode: self.executebuiltin("Container.SetViewMode(%s)" % viewMode)
	
	def executebuiltin(self, function):
		""" Exacute XBMC Builtin Function """
		if isinstance(function, unicode): self.xbmc.executebuiltin(function.encode("utf8"))
		else: self.xbmc.executebuiltin(function)
	
	def urlencode(self, query):
		# Create Sortcuts
		quote_plus = self.urllib.quote_plus
		isinstancel = isinstance
		unicodel = unicode
		strl = str
		
		# Parse dict and return urlEncoded string of key and values separated by &
		return "&".join([strl(key) + "=" + quote_plus(value.encode("utf8")) if isinstancel(value, unicodel) else strl(key) + "=" + quote_plus(strl(value)) for key, value in query.iteritems()])
	
	def parse_qs(self, params, asList=False):
		# Convert Unicode to UTF-8 if needed
		if isinstance(params, unicode):
			params = params.encode("utf8")
		
		# Convert urlEncoded String into a dict and unquote
		qDict = {}
		unquoter = self.urllib.unquote_plus
		for part in params[params.find("?")+1:].split("&"):
			try: key, value = part.split("=",1)
			except: continue
			else:
				if not asList: qDict[key.lower()] = unquoter(value).decode("utf8")
				else: qDict[key.lower()] = [unquoter(segment).decode("utf8") for segment in value.split(",")]
		return qDict
	
	def strip_tags(self, html):
		# Strips out html code and return plan text
		sub_start = html.find(u"<")
		sub_end = html.find(u">")
		while sub_start < sub_end and sub_start > -1:
			html = html.replace(html[sub_start:sub_end + 1], u"").strip()
			sub_start = html.find(u"<")
			sub_end = html.find(u">")
		return html
	
	def isYoutubeHD(self):
		# Check if HD quality is set for youtube videos
		try: setting = int(self.getAddonSetting("plugin.video.youtube", "hd_videos"))
		except: return None
		else:
			if setting == 1: return False
			elif setting == 0 or setting >= 2: return True
			else: return None
	
	def update(self, dicts):
		self._Params.update(dicts)
	
	def copy(self):
		return self._Params.copy()
	
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
	
	def get(self, key, default=None):
		if key in self._Params: return self._Params[key]
		else: return default
	
	def setdefault(self, key, failobj=None):
		if key in self._Params: return self._Params[key]
		else:
			self._Params[key] = failobj
			return failobj
	
	def pop(self, key, default=None):
		if key in self._Params:
			try: return self._Params[key]
			finally: del self._Params[key]
		elif default is not None:
			return default
		else:
			raise KeyError

# Set plugin ID
plugin = Info()