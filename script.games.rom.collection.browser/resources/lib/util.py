
import xbmc, xbmcaddon, xbmcvfs

import os, sys, re, shutil
#import xbmc, time
import time


#
# CONSTANTS AND GLOBALS #
#

SCRIPTNAME = 'Rom Collection Browser'
SCRIPTID = 'script.games.rom.collection.browser'
CURRENT_CONFIG_VERSION = "2.0.8"
CURRENT_DB_VERSION = "0.7.4"
ISTESTRUN = False

__addon__ = xbmcaddon.Addon(id='%s' %SCRIPTID)
__language__ = __addon__.getLocalizedString


#compatibility checks
XBMC_VERSION_HELIX = 14

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
#use a little delay before applying filter settings
WAITTIME_APPLY_FILTERS = 500


LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

CURRENT_LOG_LEVEL = LOG_LEVEL_INFO

API_KEYS = {'%VGDBAPIKey%' : 'Zx5m2Y9Ndj6B4XwTf83JyKz7r8WHt3i4',
			'%GIANTBOMBAPIKey%' : '279442d60999f92c5e5f693b4d23bd3b6fd8e868',
			'%ARCHIVEAPIKEY%' : 'VT7RJ960FWD4CC71L0Z0K4KQYR4PJNW8'}

FUZZY_FACTOR_ENUM = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
MAXNUMGAMES_ENUM = [0,100,250,500,1000,2500,5000,10000]

SETTING_RCB_VIEW_MODE = 'rcb_view_mode'
SETTING_RCB_SKIN = 'rcb_skin'
SETTING_RCB_CACHINGOPTION = 'rcb_cachingOption'
SETTING_RCB_MEMDB = 'rcb_memDB'
SETTING_RCB_FUZZYFACTOR = 'rcb_fuzzyFactor'
SETTING_RCB_LOGLEVEL = 'rcb_logLevel'
SETTING_RCB_ESCAPECOMMAND = 'rcb_escapeEmulatorCommand'
SETTING_RCB_CREATENFOFILE = 'rcb_createNfoWhileScraping'
SETTING_RCB_ENABLEFULLREIMPORT = 'rcb_enableFullReimport'
SETTING_RCB_ALLOWOVERWRITEWITHNULLVALUES = 'rcb_overwriteWithNullvalues'
SETTING_RCB_IGNOREGAMEWITHOUTDESC = 'rcb_ignoreGamesWithoutDesc'
SETTING_RCB_IGNOREGAMEWITHOUTARTWORK = 'rcb_ignoreGamesWithoutArtwork'
SETTING_RCB_SHOWENTRYALLCONSOLES = 'rcb_showEntryAllConsoles'
SETTING_RCB_SHOWENTRYALLGENRES = 'rcb_showEntryAllGenres'
SETTING_RCB_SHOWENTRYALLYEARS = 'rcb_showEntryAllYears'
SETTING_RCB_SHOWENTRYALLPUBLISHER = 'rcb_showEntryAllPublisher'
SETTING_RCB_SHOWENTRYALLCHARS = 'rcb_showEntryAllChars'
SETTING_RCB_PREVENTUNFILTEREDSEARCH = 'rcb_preventUnfilteredSearch'
SETTING_RCB_SAVEVIEWSTATEONEXIT = 'rcb_saveViewStateOnExit'
SETTING_RCB_SAVEVIEWSTATEONLAUNCHEMU = 'rcb_saveViewStateOnLaunchEmu'
SETTING_RCB_SHOWIMPORTOPTIONSDIALOG = 'rcb_showImportOptions'
SETTING_RCB_SCRAPINGMODE = 'rcb_scrapingMode'
SETTING_RCB_SCRAPONSTART = 'rcb_scrapOnStartUP'
SETTING_RCB_LAUNCHONSTARTUP = 'rcb_launchOnStartup'
SETTING_RCB_SCRAPEONSTARTUPACTION = 'rcb_scrapeOnStartupAction'
SETTING_RCB_SHOWFAVORITESTARS = 'rcb_showFavoriteStars'
SETTING_RCB_FAVORITESSELECTED = 'rcb_favoritesSelected'
SETTING_RCB_SEARCHTEXT = 'rcb_searchText'
SETTING_RCB_OVERWRITEIMPORTOPTIONS = 'rcb_overwriteImportOptions'
SETTING_RCB_IMPORTOPTIONS_DISABLEROMCOLLECTIONS = 'rcb_disableRomcollections'
SETTING_RCB_EDITSCRAPER_DESCFILEPERGAME = 'rcb_editScraper_descFilePerGame'
SETTING_RCB_USENFOFOLDER = 'rcb_useNfoFolder'
SETTING_RCB_NFOFOLDER = 'rcb_nfoFolder'
SETTING_RCB_PRELAUNCHDELAY = 'rcb_prelaunchDelay'
SETTING_RCB_POSTLAUNCHDELAY = 'rcb_postlaunchDelay'
SETTING_RCB_USEVBINSOLOMODE = 'rcb_useVBInSoloMode'
SETTING_RCB_SUSPENDAUDIO = 'rcb_suspendAudio'
SETTING_RCB_TOGGLESCREENMODE = 'rcb_toggleScreenMode'
SETTING_RCB_EMUAUTOCONFIGPATH = 'rcb_pathToEmuAutoConfig'
SETTING_RCB_MAXNUMGAMESTODISPLAY = 'rcb_maxNumGames'


SCRAPING_OPTION_AUTO_ACCURATE = 0
SCRAPING_OPTION_AUTO_GUESS = 1
SCRAPING_OPTION_INTERACTIVE = 2


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
RCBSETTING_autoexecBackupPath = 7
RCBSETTING_dbVersion = 8
RCBSETTING_lastFocusedControlMainView = 9
RCBSETTING_lastFocusedControlGameInfoView = 10
RCBSETTING_lastSelectedCharacterIndex = 11


GAME_description = 2
GAME_gameCmd = 3
GAME_alternateGameCmd = 4
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

GENREGAME_genreId = 1
GENREGAME_gameId = 2

#
# UI #
#

VIEW_MAINVIEW = 'mainView'
VIEW_GAMEINFOVIEW = 'gameInfoView'

IMAGE_CONTROL_BACKGROUND = 'background'
IMAGE_CONTROL_GAMELIST = 'gamelist'
IMAGE_CONTROL_GAMELISTSELECTED = 'gamelistselected'
IMAGE_CONTROL_GAMEINFO_BIG = 'gameinfobig'

IMAGE_CONTROL_GAMEINFO_UPPERLEFT = 'gameinfoupperleft'
IMAGE_CONTROL_GAMEINFO_UPPERRIGHT = 'gameinfoupperright'
IMAGE_CONTROL_GAMEINFO_LOWERLEFT = 'gameinfolowerleft'
IMAGE_CONTROL_GAMEINFO_LOWERRIGHT = 'gameinfolowerright'

IMAGE_CONTROL_GAMEINFO_UPPER = 'gameinfoupper'
IMAGE_CONTROL_GAMEINFO_LOWER = 'gameinfolower'
IMAGE_CONTROL_GAMEINFO_LEFT = 'gameinfoleft'
IMAGE_CONTROL_GAMEINFO_RIGHT = 'gameinforight'

IMAGE_CONTROL_1 = 'extraImage1'
IMAGE_CONTROL_2 = 'extraImage2'
IMAGE_CONTROL_3 = 'extraImage3'
VIDEO_CONTROL_VideoWindowBig = 'videowindowbig'
VIDEO_CONTROL_VideoWindowSmall = 'videowindowsmall'
VIDEO_CONTROL_VideoFullscreen = 'videofullscreen'

GAMEPROPERTY_Console = 'console'


FILETYPEPARENT_GAME = 'game'
FILETYPEPARENT_PUBLISHER = 'publisher'
FILETYPEPARENT_DEVELOPER = 'developer'
FILETYPEPARENT_CONSOLE = 'console'
FILETYPEPARENT_ROMCOLLECTION = 'romcollection'
				

html_unescape_table = {
		"&amp;" : "&",
		"&quot;" : '"' ,
		"&apos;" : "'",
		"&gt;" : ">",
		"&lt;" : "<",
		"&nbsp;" : " ",
		"&#x26;" : "&",
		"&#x27;" : "\'",
		"&#xB2;" : "2",
		"&#xB3;" : "3",		
		}

def html_unescape(text):
		
		for key in html_unescape_table.keys():
			text = text.replace(key, html_unescape_table[key])
			
		return text
	

html_escape_table = {
		"&" : "%26",
		" " : "%20" ,
		"'" : "%27",
		">" : "%3E",
		"<" : "%3C",		
		}

def html_escape(text):
		
		for key in html_escape_table.keys():
			text = text.replace(key, html_escape_table[key])
			
		return text


def joinPath(part1, *parts):
	path = ''
	if(part1.startswith('smb://')):
		path = part1
		for part in parts:
			path = "%s/%s" %(path, part)
	else:
		path = os.path.join(part1, *parts)
		
	return path


#
# METHODS #
#

def getEnvironment():
	return ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]

def localize(id):
	try:
		return __language__(id)
	except:
		return "Sorry. No translation available for string with id: " +str(id)

def getAddonDataPath():
	
	path = ''
	path = xbmc.translatePath('special://profile/addon_data/%s' %(SCRIPTID))
		
	if not os.path.exists(path):
		try:
			os.makedirs(path)
		except:
			path = ''	
	return path


def getAddonInstallPath():
	path = ''
				
	path = __addon__.getAddonInfo('path')
	
	return path
			

def getAutoexecPath():	
	return xbmc.translatePath('special://profile/autoexec.py')


def getEmuAutoConfigPath():	
	
	settings = getSettings()
	path = settings.getSetting(SETTING_RCB_EMUAUTOCONFIGPATH)
	if(path == ''):
		path = os.path.join(getAddonDataPath(), 'emu_autoconfig.xml')
		
	if(not xbmcvfs.exists(path)):
		oldPath = os.path.join(getAddonInstallPath(), 'resources', 'emu_autoconfig.xml')
		copyFile(oldPath, path)
		
	return path


def getTempDir():
	tempDir = os.path.join(getAddonDataPath(), 'tmp')
	
	try:
		#check if folder exists
		if(not os.path.isdir(tempDir)):
			os.mkdir(tempDir)
		return tempDir
	except Exception, (exc):
		Logutil.log('Error creating temp dir: ' +str(exc), LOG_LEVEL_ERROR)
		return None


def getConfigXmlPath():
	if(not ISTESTRUN):
		addonDataPath = getAddonDataPath() 
		configFile = os.path.join(addonDataPath, "config.xml")
	else:
		configFile = os.path.join(getAddonInstallPath(), "resources", "lib", "TestDataBase", "config.xml")
	
	Logutil.log('Path to configuration file: ' +str(configFile), LOG_LEVEL_INFO)
	return configFile


def copyFile(oldPath, newPath):
	Logutil.log('new path = %s' %newPath, LOG_LEVEL_INFO)
	newDir = os.path.dirname(newPath)
	if not os.path.isdir(newDir):
		Logutil.log('create directory: %s' %newDir, LOG_LEVEL_INFO)
		try:
			os.mkdir(newDir)
		except Exception, (exc):
			Logutil.log('Error creating directory: %s\%s' %(newDir, str(exc)), LOG_LEVEL_ERROR)
			return
	
	if not os.path.isfile(newPath):
		Logutil.log('copy file from %s to %s' %(oldPath, newPath), LOG_LEVEL_INFO)
		try:
			shutil.copy2(oldPath, newPath)
		except Exception, (exc):
			Logutil.log('Error copying file from %s to %s\%s' %(oldPath, newPath, str(exc)), LOG_LEVEL_ERROR)
	
	
def getSettings():
	settings = xbmcaddon.Addon(id='%s' %SCRIPTID)
	return settings


#HACK: XBMC does not update labels with empty strings
def setLabel(label, control):
	if(label == ''):
		label = ' '
		
	control.setLabel(str(label))


#HACK: XBMC does not update labels with empty strings
def getLabel(control):
	label = control.getLabel()
	if(label == ' '):
		label = ''
		
	return label


def getScrapingMode(settings):
	scrapingMode = 0
	scrapingModeStr = settings.getSetting(SETTING_RCB_SCRAPINGMODE)			
	if(scrapingModeStr == 'Automatic: Accurate'):
		scrapingMode = 0
	elif(scrapingModeStr == 'Automatic: Guess Matches'):
		scrapingMode = 1
	elif(scrapingModeStr == 'Interactive: Select Matches'):
		scrapingMode = 2
		
	return scrapingMode


def indentXml(elem, level=0):
	i = "\n" + level*"  "
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + "  "
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			indentXml(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i


RCBHOME = getAddonInstallPath()


#
# Logging
#


try:
	from sqlite3 import dbapi2 as sqlite
	print("RCB_INFO: Loading sqlite3 as DB engine")
except:
	from pysqlite2 import dbapi2 as sqlite
	print("RCB_INFO: Loading pysqlite2 as DB engine")

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
						
		try:
			print prefix + message
		except:
			pass
		
	
	@staticmethod
	def getCurrentLogLevel():
		logLevel = 1
		try:
			settings = getSettings()
			logLevelStr = settings.getSetting(SETTING_RCB_LOGLEVEL)
			if(logLevelStr == 'ERROR'):
				logLevel = LOG_LEVEL_ERROR
			elif(logLevelStr == 'WARNING'):
				logLevel = LOG_LEVEL_WARNING
			elif(logLevelStr == 'INFO'):
				logLevel = LOG_LEVEL_INFO
			elif(logLevelStr == 'DEBUG'):
				logLevel = LOG_LEVEL_DEBUG
		except:
			pass
		return logLevel