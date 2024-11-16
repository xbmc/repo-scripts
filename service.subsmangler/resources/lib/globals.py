# this file includes all global variables used across the plugin

import os
import xbmc
import xbmcaddon
import xbmcvfs

# addon globals
__addon__ = xbmcaddon.Addon(id='service.subsmangler')
__addondir__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__addonworkdir__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__version__ = __addon__.getAddonInfo('version')
__addonlang__ = __addon__.getLocalizedString
__kodiversion__ = xbmc.getInfoLabel('System.BuildVersion')[:4]

# definitions file
# path and file name of public definitions
deffileurl = "https://raw.githubusercontent.com/bkiziuk/service.subsmangler/master/resources/regexdef.def"
# location of locally stored subtitles
localdeffilename = os.path.join(__addonworkdir__, 'regexdef.def')
# location of sample definitions
sampledeffilename = os.path.join(__addondir__, 'resources', 'regexdef.def')
# location of temporary file used during download
tempdeffilename = os.path.join(__addonworkdir__, 'tempdef.def')
# file that will be used during subtitle processing
deffilename = None
# file holding excluded paths for cleaning process
cleaningexclusionsfilename = os.path.join(__addonworkdir__, 'cleanexcl.def')

# list of input file extensions
# extensions in lowercase with leading dot
# note: we do not include output extension .utf
SubExtList = ['.txt', '.srt', '.sub', '.subrip', '.microdvd', '.mpl', '.tmp', '.ass']

# list of video file extensions
# extensions in lowercase with leading dot
VideoExtList = ['.mkv', '.avi', '.mp4', '.mpg', '.mpeg']

# detection status of new subtitles
DetectionIsRunning = False

# player objects
player = None
monitor = None

# logger object
logger = None

# timer object
rt = None

# video and subtitle variables
subtitlePath = None
playingFilename = None
playingFilenamePath = None
playingFps = None
SubsSearchWasOpened = False

# timer which triggers SupplementaryServices routine
ClockTick = 180

# user settings
setting_ConversionServiceEnabled = False
setting_AlsoConvertExistingSubtitles = False
setting_RemoveCCmarks = False
setting_RemoveAds = False
setting_PauseOnConversion = False
setting_AutoInvokeSubsDialog = False
setting_AutoInvokeSubsDialogOnStream = False
setting_NoAutoInvokeIfLocalUnprocSubsFound = False
setting_NoConfirmationInvokeIfDownloadedSubsNotFound = False
setting_AutoUpdateDef = False
setting_SeparateLogFile = False
setting_AutoRemoveOldSubs = False
setting_BackupOldSubs = False
setting_RemoveSubsBackup = False
setting_RemoveUnprocessedSubs = False
setting_SimulateRemovalOnly = False
setting_AdjustSubDisplayTime = False
setting_FixOverlappingSubDisplayTime = False
setting_ShowNoautosubsContextItem = False
setting_HideOrphanedSubsCleaningProgress = False
setting_LogLevel = 0
