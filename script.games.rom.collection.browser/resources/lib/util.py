
import os, sys, re
import xbmc, time


#
# CONSTANTS #
#

RCBHOME = os.getcwd()
SCRIPTNAME = 'Rom Collection Browser'
SCRIPTID = 'script.games.rom.collection.browser'
CURRENT_SCRIPT_VERSION = "0.6.1"
CURRENT_DB_VERSION = "0.6.0"

#time to wait before automatic playback starts
WAITTIME_PLAYERSTART = 500
#time that xbmc needs to close the player (before we can load the list again)
WAITTIME_PLAYERSTOP = 500
#time that xbmc needs to update controls (before we can rely on position)
WAITTIME_UPDATECONTROLS = 100
#don't call onAction if last call was not more than x ms before
WAITTIME_ONACTION = 50
#don't call onAction if last call was not more than x ms before (we need higher values on xbox)
WAITTIME_ONACTION_XBOX = 600


LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

CURRENT_LOG_LEVEL = LOG_LEVEL_INFO

SETTING_RCB_VIEW_MODE = 'rcb_view_mode'

#
# DB FIELDS #
#

ROW_ID = 0
ROW_NAME = 1

RCBSETTING_lastSelectedView = 1
RCBSETTING_lastSelectedConsoleIndex = 2
RCBSETTING_lastSelectedGenreIndex = 3
RCBSETTING_lastSelectedPublisherIndex = 4
RCBSETTING_lastSelectedYearIndex = 5
RCBSETTING_lastSelectedGameIndex = 6
RCBSETTING_favoriteConsoleId = 7
RCBSETTING_favoriteGenreId = 8
RCBSETTING_autoexecBackupPath = 9
RCBSETTING_dbVersion = 10
RCBSETTING_showEntryAllConsoles = 11
RCBSETTING_showEntryAllGenres = 12
RCBSETTING_showEntryAllYears = 13
RCBSETTING_showEntryAllPublisher = 14
RCBSETTING_saveViewStateOnExit = 15
RCBSETTING_saveViewStateOnLaunchEmu = 16
RCBSETTING_lastFocusedControlMainView = 17
RCBSETTING_lastFocusedControlGameInfoView = 18
RCBSETTING_logLevel = 19
RCBSETTING_showEntryAllChars = 20
RCBSETTING_lastSelectedCharacterIndex = 21
RCBSETTING_preventUnfilteredSearch = 22
RCBSETTING_cachingOption = 23

ROMCOLLECTION_consoleId = 2
ROMCOLLECTION_emuCommandLine = 3
ROMCOLLECTION_useEmuSolo = 4
ROMCOLLECTION_escapeEmuCmd = 5
ROMCOLLECTION_xboxCreateShortcut = 17
ROMCOLLECTION_xboxCreateShortcutAddRomfile = 18
ROMCOLLECTION_xboxCreateShortcutUseShortGamename = 19


GAME_description = 2
GAME_romCollectionId = 5
GAME_publisherId = 6
GAME_developerId = 7
GAME_reviewerId = 8
GAME_yearId = 9
GAME_maxPlayers = 10
GAME_rating = 11
GAME_numVotes = 12
GAME_url = 13
GAME_region = 14
GAME_media = 15
GAME_perspective = 16
GAME_controllerType = 17
GAME_isFavorite = 18
GAME_launchCount = 19
GAME_originalTitle = 20
GAME_alternateTitle = 21
GAME_translatedBy = 22
GAME_version = 23

FILE_fileTypeId = 2
FILE_parentId = 3

FILETYPE_parent = 3

FILETYPEFORCONTROL_control = 1
FILETYPEFORCONTROL_romCollectionId = 3
FILETYPEFORCONTROL_fileTypeId = 4

GENREGAME_genreId = 1
GENREGAME_gameId = 2

#
# UI #
#

VIEW_MAINVIEW = 'mainView'
VIEW_GAMEINFOVIEW = 'gameInfoView'

IMAGE_CONTROL_MV_BACKGROUND = 'mainviewbackground'
IMAGE_CONTROL_MV_GAMELIST = 'gamelist'
IMAGE_CONTROL_MV_GAMELISTSELECTED = 'gamelistselected'
IMAGE_CONTROL_MV_GAMEINFO_BIG = 'mainviewgameinfobig'
IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT = 'mainviewgameinfoupperleft'
IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT = 'mainviewgameinfoupperright'
IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT = 'mainviewgameinfolowerleft'
IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT = 'mainviewgameinfolowerright'
IMAGE_CONTROL_MV_1 = 'mainview1'
IMAGE_CONTROL_MV_2 = 'mainview2'
IMAGE_CONTROL_MV_3 = 'mainview3'
VIDEO_CONTROL_MV_VideoWindow = 'mainviewvideowindow'
VIDEO_CONTROL_MV_VideoWindowBig = 'mainviewvideowindowbig'
VIDEO_CONTROL_MV_VideoWindowSmall = 'mainviewvideowindowsmall'
VIDEO_CONTROL_MV_VideoFullscreen = 'mainviewvideofullscreen'

IMAGE_CONTROL_GIV_BACKGROUND = 'gameinfoviewbackground'
IMAGE_CONTROL_GIV_Img1 = 'gameinfoview1'
IMAGE_CONTROL_GIV_Img2 = 'gameinfoview2'
IMAGE_CONTROL_GIV_Img3 = 'gameinfoview3'
IMAGE_CONTROL_GIV_Img4 = 'gameinfoview4'
IMAGE_CONTROL_GIV_VideoWindow = 'gameinfoviewvideowindow'

TEXT_CONTROL_MV_GAMEDESC = 'plot'

GAMEPROPERTY_Console = 'console'


FILETYPEPARENT_GAME = 'game'
FILETYPEPARENT_PUBLISHER = 'publisher'
FILETYPEPARENT_DEVELOPER = 'developer'
FILETYPEPARENT_CONSOLE = 'console'
FILETYPEPARENT_ROMCOLLECTION = 'romcollection'


#
# METHODS #
#


def getAddonDataPath():
	
	path = ''
	
	if(isPostCamelot()):		
		path = xbmc.translatePath('special://profile/addon_data/%s' %(SCRIPTID))
		#path = xbmc.translatePath('special://profile/addon_data/%s-%s' %(SCRIPTID, CURRENT_SCRIPT_VERSION))
	else:
		path = xbmc.translatePath('special://profile/script_data/%s' %(SCRIPTID))
		#path = xbmc.translatePath('special://profile/script_data/%s-%s' %(SCRIPTID, CURRENT_SCRIPT_VERSION))
		
	if not os.path.exists(path):
		try:
			os.makedirs(path)
		except:
			path = ''	
	return path
			


def getAutoexecPath():
	if(isPostCamelot()):
		return xbmc.translatePath('special://profile/autoexec.py')
	else:
		autoexec = os.path.join(RCBHOME, '..', 'autoexec.py')
		autoexec = os.path.normpath(autoexec)
		return autoexec
	

def getConfigXmlPath():
	addonDataPath = getAddonDataPath() 
	configFile = os.path.join(addonDataPath, "config.xml")
	
	return configFile


def getConfigXmlModifyTime():
	configFile = getConfigXmlPath()		
	if(os.path.isfile(configFile)):
		modifyTime = os.path.getmtime(configFile)
	else:
		modifyTime = 0
	
	Logutil.log("modifyTime from file (as int): " +str(modifyTime), LOG_LEVEL_INFO)
	Logutil.log("modifyTime from file (as time): " +str(time.ctime(modifyTime)), LOG_LEVEL_INFO)
	return modifyTime
	
	
def getSettings():
	settings = ''
	if isPostCamelot():
		import xbmcaddon
		settings = xbmcaddon.Addon(id='%s' %SCRIPTID)
	else:
		settings = xbmc.Settings(RCBHOME)
	return settings


def isPostCamelot():  
	if os.environ.get('OS') == 'xbox':
		return False
	# preliminary test number for now. will bump this to the revision of the stable
	# xbmc release when it is out
	elif getRevision() >= 28276:
		return True
	else:
		return False  


def getRevision():
	rev_re = re.compile('r(\d+)')
	try: xbmc_version = xbmc.getInfoLabel('System.BuildVersion')
	except: xbmc_version = 'Unknown'

	try:
		xbmc_rev = int(rev_re.search(xbmc_version).group(1))
		print "XBMC Revision: %s" % xbmc_rev
	except:
		print "XBMC Revision not available - Version String: %s" % xbmc_version
		xbmc_rev = 0

	return xbmc_rev

#
# Logging
#


from pysqlite2 import dbapi2 as sqlite

class Logutil:
	
	currentLogLevel = None

	@staticmethod
	def log(message, logLevel):
			
		if(Logutil.currentLogLevel == None):
			print "RCB: init log level"
			Logutil.currentLogLevel = Logutil.getCurrentLogLevel()
			print "RCB: current log level: " +str(Logutil.currentLogLevel)
		
		if(logLevel > Logutil.currentLogLevel):			
			return
			
		prefix = ''
		if(logLevel == LOG_LEVEL_DEBUG):
			prefix = 'RCB_DEBUG: '
		elif(logLevel == LOG_LEVEL_INFO):
			prefix = 'RCB_INFO: '
		elif(logLevel == LOG_LEVEL_WARNING):
			prefix = 'RCB_WARNING: '
		elif(logLevel == LOG_LEVEL_ERROR):
			prefix = 'RCB_ERROR: '

		print prefix + message
		
	
	@staticmethod
	def getCurrentLogLevel():	
		logLevel = 1
		try:
			dataBasePath = os.path.join(getAddonDataPath(), 'MyGames.db')
			connection = sqlite.connect(dataBasePath)
			cursor = connection.cursor()
			cursor.execute("SELECT * FROM RCBSetting")
			rcbSettings = cursor.fetchall()
			
			rcbSetting = rcbSettings[0]
			logLevel = rcbSetting[19]
		except:
			logLevel = 1
		return logLevel