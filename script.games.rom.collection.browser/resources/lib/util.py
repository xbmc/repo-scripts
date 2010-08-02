
import os, sys
import xbmc

#
# CONSTANTS #
#

RCBHOME = os.getcwd()
SCRIPTNAME = 'Rom Collection Browser'

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

ROMCOLLECTION_consoleId = 2
ROMCOLLECTION_emuCommandLine = 3
ROMCOLLECTION_useEmuSolo = 4
ROMCOLLECTION_escapeEmuCmd = 5


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
VIDEO_CONTROL_MV_VideoWindowBig = 'mainviewvideowindowbig'
VIDEO_CONTROL_MV_VideoWindowSmall = 'mainviewvideowindowsmall'

IMAGE_CONTROL_GIV_BACKGROUND = 'gameinfoviewbackground'
IMAGE_CONTROL_GIV_Img1 = 'gameinfoview1'
IMAGE_CONTROL_GIV_Img2 = 'gameinfoview2'
IMAGE_CONTROL_GIV_Img3 = 'gameinfoview3'
IMAGE_CONTROL_GIV_Img4 = 'gameinfoview4'
IMAGE_CONTROL_GIV_VideoWindow = 'gameinfoviewvideowindow'

TEXT_CONTROL_MV_GAMEDESC = 'gamedesc'

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
	return xbmc.translatePath('special://profile/addon_data/script.games.rom.collection.browser')
	
def getAutoexecPath():
	return xbmc.translatePath('special://profile/autoexec.py')


def log(message, logLevel):
		
		if(logLevel > CURRENT_LOG_LEVEL):
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