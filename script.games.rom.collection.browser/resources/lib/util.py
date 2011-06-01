
import os, sys, re
#import xbmc, time
import time


#
# CONSTANTS #
#

SCRIPTNAME = 'Rom Collection Browser'
SCRIPTID = 'script.games.rom.collection.browser'
CURRENT_CONFIG_VERSION = "0.8.6"
CURRENT_DB_VERSION = "0.7.4"
ISTESTRUN = False

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

API_KEYS = {'%VGDBAPIKey%' : 'Zx5m2Y9Ndj6B4XwTf83JyKz7r8WHt3i4',
			'%GIANTBOMBAPIKey%' : '279442d60999f92c5e5f693b4d23bd3b6fd8e868',
			'%ARCHIVEAPIKEY%' : 'VT7RJ960FWD4CC71L0Z0K4KQYR4PJNW8'}

FUZZY_FACTOR_ENUM = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

SETTING_RCB_VIEW_MODE = 'rcb_view_mode'
SETTING_RCB_CACHINGOPTION = 'rcb_cachingOption'
SETTING_RCB_MEMDB = 'rcb_memDB'
SETTING_RCB_FUZZYFACTOR = 'rcb_fuzzyFactor'
SETTING_RCB_LOGLEVEL = 'rcb_logLevel'
SETTING_RCB_ESCAPECOMMAND = 'rcb_escapeEmulatorCommand'
SETTING_RCB_CREATENFOFILE = 'rcb_createNfoWhileScraping'
SETTING_RCB_ENABLEFULLREIMPORT = 'rcb_enableFullReimport'
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

IMAGE_CONTROL_MV_BACKGROUND = 'mainviewbackground'
IMAGE_CONTROL_MV_GAMELIST = 'gamelist'
IMAGE_CONTROL_MV_GAMELISTSELECTED = 'gamelistselected'
IMAGE_CONTROL_MV_GAMEINFO_BIG = 'mainviewgameinfobig'

IMAGE_CONTROL_MV_GAMEINFO_UPPERLEFT = 'mainviewgameinfoupperleft'
IMAGE_CONTROL_MV_GAMEINFO_UPPERRIGHT = 'mainviewgameinfoupperright'
IMAGE_CONTROL_MV_GAMEINFO_LOWERLEFT = 'mainviewgameinfolowerleft'
IMAGE_CONTROL_MV_GAMEINFO_LOWERRIGHT = 'mainviewgameinfolowerright'

IMAGE_CONTROL_MV_GAMEINFO_UPPER = 'mainviewgameinfoupper'
IMAGE_CONTROL_MV_GAMEINFO_LOWER = 'mainviewgameinfolower'
IMAGE_CONTROL_MV_GAMEINFO_LEFT = 'mainviewgameinfoleft'
IMAGE_CONTROL_MV_GAMEINFO_RIGHT = 'mainviewgameinforight'

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



#
# METHODS #
#

def getEnvironment():
	return ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]
	

def getAddonDataPath():
    path = ''
    
    if(hasAddons()):        
        import xbmc
        path = xbmc.translatePath('special://profile/addon_data/%s' %(SCRIPTID))
    else:        
        import xbmc
        path = xbmc.translatePath('special://profile/script_data/%s' %(SCRIPTID))
        
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            path = ''    
    return path


def getAddonInstallPath():
    
    path = ''
    
    if(hasAddons()):
        import xbmcaddon
        addon = xbmcaddon.Addon(id='%s' %SCRIPTID)
        path = addon.getAddonInfo('path')
    else:
        path = os.getcwd()
    return path
            

def getAutoexecPath():
    import xbmc
    if(hasAddons()):
        return xbmc.translatePath('special://profile/autoexec.py')
    else:
        autoexec = os.path.join(RCBHOME, '..', 'autoexec.py')
        autoexec = os.path.normpath(autoexec)
        return autoexec
    

def getConfigXmlPath():
    if(not ISTESTRUN):
        addonDataPath = getAddonDataPath() 
        configFile = os.path.join(addonDataPath, "config.xml")
    else:
        configFile = os.path.join(getAddonInstallPath(), "TestDataBase", "config.xml")
    
    Logutil.log('Path to configuration file: ' +str(configFile), LOG_LEVEL_INFO)
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
    import xbmc
    settings = ''
    if hasAddons():
        import xbmcaddon
        settings = xbmcaddon.Addon(id='%s' %SCRIPTID)
    else:
        settings = xbmc.Settings(RCBHOME)
    return settings


def hasAddons():  
    if os.environ.get('OS') == 'xbox':
        return False
    
    try:
        import xbmcaddon
        return True
    except:
        return False
       
       
def getDbupdateStatusFilename():
	return os.path.join(getAddonDataPath(), 'dbupdatestatus.txt')


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