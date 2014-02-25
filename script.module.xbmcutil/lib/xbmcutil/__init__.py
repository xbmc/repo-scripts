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
	if subAction == u"videohosts":
		# Import VideoHosts APIs and Call Required Class
		import videohostsAPI
		try:   func = getattr(videohostsAPI, plugin.actions[2])
		except AttributeError: pass
		else:  func()
	
	elif subAction == u"direct" or subAction == u"source":
		# Import listitem Module and Exacute
		from listitem import PlayMedia
		PlayMedia()
	
	elif subAction == u"opensettings":
		# Open Settings Dialog
		plugin.openSettings()
		plugin.refreshContainer()
	
	elif subAction == u"search":
		# Call storageDB and exacute saved searches
		from xbmcutil import storageDB
		storageDB.SavedSearches()

class Addon(object):
	_addonObj = __import__("xbmcaddon").Addon
	_addonName = None
	_profile = None
	
	def setAddonIDs(self, localID, globalID):
		""" Initiate Local and Global Objects """
		self._addonData = self._addonObj(localID)
		self._scriptData = self._addonObj(globalID)
		self._addonID = localID
		
		# Shortcuts
		self.openSettings = self._addonData.openSettings
		self.setSetting = self._addonData.setSetting
		self.getstr = self.getLocalizedString
	
	def getLocalizedString(self, id):
		""" Return localized string for selected id """
		if   id >= 30000 and id <= 30899: return self._addonData.getLocalizedString(id).decode("utf8")
		elif id >= 32900 and id <= 32999: return self._scriptData.getLocalizedString(id).decode("utf8")
		else: return self.xbmc.getLocalizedString(id)
	
	def getuni(self, id):
		""" Return localized unicode string for selected id """
		return self.getLocalizedString(id).decode("utf8")
	
	def getAddonSetting(self, id, key):
		""" Return setting for selected addon """
		try: addonData = self._addonObj(id)
		except: return u""
		else: return addonData.getSetting(key).decode("utf8")
	
	def getQuality(self):
		""" Return unicode for quality setting """
		return self._addonData.getSetting("quality").decode("utf8")
	
	def getSetting(self, id):
		""" Return unicode for setting """
		return self._addonData.getSetting(id).decode("utf8")
	
	def getSettingInt(self, id):
		""" Return Integer for settings """
		return int(self._addonData.getSetting(id))
	
	def getSettingBool(self, id):
		""" Return boolean for setting """
		return self._addonData.getSetting(id) == "true"
	
	def translatePath(self, path):
		""" Return translated special paths as unicode """
		return self.xbmc.translatePath(path).decode("utf8")
	
	def getId(self):
		""" Return addon id """
		return self._addonID.decode("utf8")
	
	def getAuthor(self):
		""" Return author for current addon """
		return self._addonData.getAddonInfo("author").decode("utf8")
	
	def getChangelog(self):
		""" Return path to changelog for addon """
		return self._addonData.getAddonInfo("changelog").decode("utf8")
	
	def getDescription(self):
		""" Return full description for addon """
		return self._addonData.getAddonInfo("description").decode("utf8")
	
	def getDisclaimer(self):
		""" Return the disclamimer for current addon if any """
		return self._addonData.getAddonInfo("disclaimer").decode("utf8")
	
	def getName(self):
		""" Return name of current addon """
		if self._addonName: return self._addonName
		else:
			self._addonName = self._addonData.getAddonInfo("name").decode("utf8")
			return self._addonName
	
	def getStars(self):
		""" Return Start rating for addon """
		return self._addonData.getAddonInfo("stars").decode("utf8")
	
	def getSummary(self):
		""" Return description summary for addon """
		return self._addonData.getAddonInfo("summary").decode("utf8")
	
	def getType(self):
		""" Return type of addon """
		return self._addonData.getAddonInfo("type").decode("utf8")
	
	def getVersion(self):
		""" Return current addon version """
		return self._addonData.getAddonInfo("version").decode("utf8")
	
	def getTempPath(self):
		""" Return unicode path to temp folder """
		return self.translatePath("special://home/temp/")
	
	def getProfile(self):
		""" Returns full unicode path to the addons saved data location """
		if self._profile: return self._profile
		else:
			self._profile = self.translatePath(self._addonData.getAddonInfo("profile"))
			return self._profile
	
	def getLibPath(self):
		""" Returns full unicode path to the plugin library location """
		return self.os.path.join(self._addonData.getAddonInfo("path"), "resources", "lib").decode("utf8")
	
	def getIcon(self):
		""" Return unicode path to addon icon """
		return self.translatePath(self._addonData.getAddonInfo("icon"))
	
	def getFanartImage(self):
		""" Return unicode path of addon fanart """
		return self.translatePath(self._addonData.getAddonInfo("fanart"))
	
	def getImageLocation(self, local=True):
		""" Return unicode path to local or globale image location """
		return self.os.path.join(self.getPath(local), "resources", "media", "%s")
	
	def getPath(self, local=True):
		""" Returns full unicode path to the plugin location """
		if local: return self._addonData.getAddonInfo("path").decode("utf8")
		else: return self._scriptData.getAddonInfo("path").decode("utf8")

class Dialog(object):
	import xbmcgui
	xbmcgui.INPUT_ALPHANUM = 0
	xbmcgui.INPUT_NUMERIC = 1
	xbmcgui.INPUT_DATE = 2
	xbmcgui.INPUT_TIME = 3
	xbmcgui.INPUT_IPADDRESS = 4
	xbmcgui.INPUT_PASSWORD = 5
	xbmcgui.PASSWORD_VERIFY = 1
	xbmcgui.ALPHANUM_HIDE_INPUT = 2
	
	def dialogYesNo(self, heading, line1, line2="", line3="", nolabel="", yeslabel=""):
		"""
			Returns True if 'Yes' was pressed, else False.
			
			heading		: string or unicode - dialog heading.
			line1		: string or unicode - line #1 text.
			line2		: [opt] string or unicode - line #2 text.
			line3		: [opt] string or unicode - line #3 text.
			nolabel		: [opt] label to put on the no button.
			yeslabel	: [opt] label to put on the yes button.
		"""
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.yesno(heading, line1, line2, line3, nolabel, yeslabel)
	
	def dialogOK(self, heading, line1, line2="", line3=""):
		"""
			Returns True if 'Ok' was pressed, else False.
			
			heading		: string or unicode - dialog heading.
			line1		: string or unicode - line #1 text.
			line2		: [opt] string or unicode - line #2 text.
			line3		: [opt] string or unicode - line #3 text.
		"""
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.ok(heading, line1, line2, line3)
	
	def dialogSelect(self, heading, list, autoclose=0):
		"""
			Returns the position of the highlighted item as an integer.
			
			heading		: string or unicode - dialog heading.
			list		: string list - list of items.
			autoclose	: [opt] integer - milliseconds to autoclose dialog. (default=do not autoclose)
		"""
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.select(heading, list, autoclose)
	
	def dialogNumeric(self, type, heading, default=""):
		"""
			Returns the entered data as a unicode string
			
			type		: integer - the type of numeric dialog.
			heading		: string or unicode - dialog heading.
			default		: [opt] string - default value.
			
			Types:
			- 0 : ShowAndGetNumber (default format: #)
			- 1 : ShowAndGetDate (default format: DD/MM/YYYY)
			- 2 : ShowAndGetTime (default format: HH:MM)
			- 3 : ShowAndGetIPAddress (default format: #.#.#.#)
		"""
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.numeric(type, heading, default).decode("utf8")
	
	def dialogInput(self, heading, default="", type=0, option=0, autoclose=0):
		"""
			Returns the entered data as a unicode string
			
			heading		: string - dialog heading.
			default		: [opt] string - default value. (default=empty string)
			type		: [opt] integer - the type of keyboard dialog. (default=xbmcgui.INPUT_ALPHANUM)
			option		: [opt] integer - option for the dialog. (see Options below)
			autoclose	: [opt] integer - milliseconds to autoclose dialog. (default=do not autoclose)
			
			Types:
			0 - xbmcgui.INPUT_ALPHANUM (standard keyboard)
			1 - xbmcgui.INPUT_NUMERIC (format: #)
			2 - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
			3 - xbmcgui.INPUT_TIME (format: HH:MM)
			4 - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
			5 - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
		"""
		if type == 0: return self.keyBoard(default, heading, option==2)
		elif type >= 1 and type <= 4: return self.dialogNumeric(type-1, heading, default)
		elif type == 5:
			ret = self.keyBoard(default, heading, True)
			if ret:
				from hashlib import md5
				hash = md5(ret).hexdigest().decode("utf8")
				if option == 1: return default == hash
				else: return hash
			else: return None
		else: raise ValueError("dialogInput argument type is out of bounds")
	
	def dialogBrowse(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default="", enableMultiple=False):
		"""
			Returns filename and/or path as a unicode string to the location of the highlighted item
			
			type           : integer - the type of browse dialog.
			heading        : string or unicode - dialog heading.
			shares         : string or unicode - from sources.xml. (i.e. 'myprograms')
			mask           : [opt] string or unicode - '|' separated file mask. (i.e. '.jpg|.png')
			useThumbs      : [opt] boolean - if True autoswitch to Thumb view if files exist.
			treatAsFolder  : [opt] boolean - if True playlists and archives act as folders.
			default        : [opt] string - default path or file.
		"""
		dialogbox = self.xbmcgui.Dialog()
		return dialogbox.browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, enableMultiple)
	
	def browseMultiple(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
		""" Returns tuple of marked filenames as a unicode string """
		return tuple([filename.decode("utf8") for filename in self.dialogBrowse(type, heading, shares, mask, useThumbs, treatAsFolder, default, True)])
	
	def browseSingle(self, type, heading, shares, mask="", useThumbs=False, treatAsFolder=False, default=""):
		""" Returns filename and/or path as a unicode string to the location of the highlighted item """
		return self.dialogBrowse(type, heading, shares, mask, useThumbs, treatAsFolder, default, False).decode("utf8")
	
	def keyBoard(self, default="", heading="", hidden=False):
		"""
			Return User input as a unicode string
			
			default	: default text entry.
			heading	: keyboard heading.
			hidden	: True for hidden text entry.
		"""
		kb = self.xbmc.Keyboard(default, heading, hidden)
		kb.doModal()
		if kb.isConfirmed() and kb.getText(): return kb.getText().decode("utf8")
		else: return None
	
	def dialogSearch(self, urlString=""):
		# Open KeyBoard Dialog
		ret = self.keyBoard("", self.getstr(16017), False)
		
		# Check if User Entered Any Data
		if ret and urlString: return urlString % ret
		elif ret: return ret
		else: raise plugin.URLError(0, "User Cannceled The Search KeyBoard Dialog")
	
	def setNotification(self, heading, message, icon="error", time=5000, sound=True):
		"""
			heading	: string - dialog heading.
			message	: string - dialog message.
			icon	: [opt] string - icon to use.
			time	: [opt] integer - time in milliseconds (default 5000)
			sound	: [opt] bool - play notification sound (default True)
		"""
		
		# Check if Errors are Suppressed
		if icon == "error":
			if self._suppressErrors == True: return
			else: self._suppressErrors = True
		
		# Fetch Localized String if Needed
		if isinstance(heading, int): heading = self.getstr(heading)
		if isinstance(message, int): message = self.getstr(message)
		
		# Send Error Messisg to Display
		#box = self.dialogBox
		#box.notification(heading, message, icon, time, sound)
		
		# Send Error Message to Display
		exeString = "xbmc.Notification(%s,%s,%i)" % (heading, message, time)
		self.executebuiltin(exeString)

# Class For Fetching plugin Information
class Info(Addon, Dialog):
	import xbmcplugin, xbmc, urllib, sys, os
	_suppressErrors = False
	_traceback = None
	_xbmcvfs = None
	
	class Error(Exception):
		exceptionName = 32909 # UnexpectedError
		def __init__(self, errorCode=0, errorMsg=""):
			if errorMsg: plugin.setDebugMsg(self.exceptionName, errorMsg)
			self.errorCode = errorCode
			self.errorMsg = errorMsg
		
		def __str__(self): return self.errorMsg
		def __int__(self): return self.errorCode

	class ScraperError(Error):  exceptionName = 32915 # ScraperError
	class URLError(Error):      exceptionName = 32916 # URLError
	class CacheError(Error):    exceptionName = 32917 # CacheError
	class ParserError(Error):   exceptionName = 32918 # ParserError
	class YoutubeAPI(Error):    exceptionName = 32919 # YoutubeAPI
	class videoResolver(Error): exceptionName = 32920 # videoResolver
	
	def error_handler(cls, function):
		# Wrapper for Scraper Function
		def wrapper(*arguments, **keywords):
			try: response = function(*arguments, **keywords)
			except cls.Error as e:
				if e.errorCode: cls.setNotification(e.exceptionName, e.errorCode, icon="error")
				cls.printTraceback()
				return False
			except (UnicodeEncodeError, UnicodeDecodeError):
				cls.setNotification(32909, 32921, icon="error")
				cls.printTraceback()
				return False
			except:
				cls.setNotification(32909, 32974, icon="error")
				cls.printTraceback()
				return False
			else:
				if response: return response
				else:
					cls.setNotification(cls.getName(), 33077, icon="error")
					return False
		
		# Return Wrapper
		return wrapper
	
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
	
	def __init__(self):
		# Fetch system elements
		self.handleZero = self.sys.argv[0]
		self.handleOne = int(self.sys.argv[1])
		self.handleTwo = self.sys.argv[2]
		
		# Create Plugin Handle Three
		if self.handleTwo: self.handleThree = "%s%s&" % (self.handleZero, self.handleTwo.replace("refresh","_"))
		else: self.handleThree = "%s?" % self.handleZero.replace("refresh","_")
		
		# Fetch Dict of Params
		if self.handleTwo: self._Params = self.get_params(self.handleTwo)
		else: self._Params = {}
		
		# Initiate Local and Global xbmcAddon Objects
		self.setAddonIDs(self.handleZero[9:-1], "script.module.xbmcutil")
		
		# Fetch list of actions
		self.actions = self.get("action",u"Initialize").split(".")
		
		# Set addon library path
		self.sys.path.append(self.getLibPath())
		
		# Display Current ID in XBMC Log
		self.log("### %s ###" % self._addonID)
	
	def getSelectedViewID(self, content):
		""" Returns selected View Mode setting if available """
		
		# Check if content type is one of the accepted options
		if not (content == "files" or content == "episodes"): return None
		else:
			# Check if Content ViewMode is Custom
			contentViewMode = self.getSettingInt(content)
			if contentViewMode == 0: return None
			elif contentViewMode == 3:
				customView = self.getSetting("%scustom" % content)
				try: return int(customView)
				except: return None
			else:
				# Create Table to Sky IDs
				viewModes = {'skin.ace':			{'files': {1:59, 2:56},		'episodes': {1:59, 2:64}},
							 'skin.aeonmq5':		{'files': {1:59, 2:56},		'episodes': {1:59, 2:64}},
							 'skin.aeon.nox':		{'files': {1:52, 2:500},	'episodes': {1:518, 2:500}},
							 'skin.amber':			{'files': {1:None, 2:53},	'episodes': {1:52, 2:53}},
							#'skin.back-row':		{'files': {1:None, 2:None},	'episodes': {1:None, 2:None}},
							 'skin.bello':			{'files': {1:50, 2:56},		'episodes': {1:50, 2:561}},
							 'skin.carmichael':		{'files': {1:50, 2:51},		'episodes': {1:50, 2:56}},
							 'skin.confluence':		{'files': {1:51, 2:500},	'episodes': {1:51, 2:500}},
							#'skin.diffuse':		{'files': {1:None, 2:None},	'episodes': {1:None, 2:None}},
							 'skin.droid':			{'files': {1:50, 2:55},		'episodes': {1:50, 2:51}},
							 'skin.hybrid':			{'files': {1:50, 2:500},	'episodes': {1:50, 2:500}},
							 'skin.metropolis':		{'files': {1:503, 2:None},	'episodes': {1:55, 2:59}},
							#'skin.nbox':			{'files': {1:None, 2:None},	'episodes': {1:None, 2:None}},
							 'skin.pm3-hd':			{'files': {1:550, 2:53},	'episodes': {1:550, 2:53}},
							 'skin.quartz':			{'files': {1:52, 2:None},	'episodes': {1:52, 2:None}},
							 'skin.re-touched':		{'files': {1:50, 2:500},	'episodes': {1:550, 2:500}},
							 'skin.simplicity':		{'files': {1:50, 2:500},	'episodes': {1:532, 2:505}},
							 'skin.transparency':	{'files': {1:52, 2:53},		'episodes': {1:52, 2:53}},
							 'skin.xeebo':			{'files': {1:50, 2:51},		'episodes': {1:53, 2:51}},
							 'skin.xperience-more':	{'files': {1:None, 2:None},	'episodes': {1:50, 2:68}},
							 'skin.xperience1080':	{'files': {1:50, 2:500},	'episodes': {1:50, 2:500}},
							 'skin.xtv-saf':		{'files': {1:50, 2:58},		'episodes': {1:50, 2:58}}}
				
				# Fetch IDs for current skin
				skinID = self.xbmc.getSkinDir()
				if skinID in viewModes: return viewModes[skinID][content][contentViewMode]
				else: return None
	
	def log(self, msg, level=2):
		"""
			msg		: string - text to output.
			level	: [opt] integer - log level to ouput at. (default=LOGNOTICE)
			
			Text is written to the log for the following conditions.
			0 - LOGDEBUG
			1 - LOGINFO
			2 - LOGNOTICE
			3 - LOGWARNING
			4 - LOGERROR
			5 - LOGSEVERE
			6 - LOGFATAL
			7 - LOGNONE
		"""
		# Convert Unicode to UTF-8 if needed
		if isinstance(msg, unicode):
			msg = msg.encode("utf8")
		
		# Send message to xbmc log
		self.xbmc.log(msg, level)
	
	def setDebugMsg(self, exceptionName="", errorMsg=""):
		""" Recives a *list of mesages to print """
		if isinstance(exceptionName, int): exceptionName = self.getstr(exceptionName)
		if isinstance(errorMsg, int): errorMsg = self.getstr(errorMsg)
		self.log("%s: %s" % (exceptionName, errorMsg), 0)
	
	def printTraceback(self):
		""" Print Exception Traceback to log """
		self.log(self.traceback.format_exc(), 6)
	
	def executebuiltin(self, function):
		""" Exacute XBMC Builtin Fuction """
		
		# Convert Unicode to UTF-8 if needed
		if isinstance(function, unicode):
			function = function.encode("utf8")
		
		# Execute Builtin Function
		self.xbmc.executebuiltin(function)
	
	def executePlugin(self, pluginUrl):
		""" Execute XBMC plugin """
		self.executebuiltin(u"XBMC.RunPlugin(%s)" % pluginUrl)
	
	def executeAddon(self, addonID):
		""" Execute XBMC Addon """
		self.executebuiltin(u"XBMC.RunAddon(%s)" % addonID)
	
	def refreshContainer(self):
		""" Refresh XBMC Container Listing """
		self.xbmc.executebuiltin("Container.Refresh")
	
	def setviewMode(self, viewMode):
		""" Sets XBMC View Mode, Identified by View Mode ID """
		self.xbmc.executebuiltin("Container.SetViewMode(%d)" % viewMode)
	
	def urlencode(self, query):
		# Create Sortcuts
		quote_plus = self.urllib.quote_plus
		isinstancex = isinstance
		unicodex = unicode
		strx = str
		
		# Parse dict and return urlEncoded string of key and values separated by &
		return "&".join([quote_plus(strx(key)) + "=" + quote_plus(value.encode("utf8")) if isinstancex(value, unicodex) else quote_plus(strx(key)) + "=" + quote_plus(strx(value)) for key, value in query.iteritems()])
	
	def get_params(self, params):
		# Convert Unicode to UTF-8 if needed
		if isinstance(params, unicode):
			params = params.encode("utf8")
		
		# Convert urlEncoded String into a dict and unquote
		worker = {}
		unquoter = self.urllib.unquote_plus
		for part in params[params[:1].find("?")+1:].split("&"):
			part = unquoter(part)
			try: key, value = part.split("=",1)
			except: continue
			else: worker[key] = value.decode("utf8")
		return worker
	
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
	
	def popitem(self, key):
		value = self._Params[key]
		del self._Params[key]
		return value
	
	def setdefault(self, key, failobj=None):
		if key in self._Params: return self._Params[key]
		else:
			self._Params[key] = failobj
			return failobj

# Set plugin ID
plugin = Info()