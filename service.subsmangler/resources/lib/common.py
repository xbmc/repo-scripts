# This file includes parts of code that are shared between modules

import logging
import os
import xbmc
import xbmcaddon
import xbmcvfs

from datetime import datetime
from logging.handlers import RotatingFileHandler


global __addon__
global __addondir__
global __addonworkdir__
global __version__
global __addonlang__
global __kodiversion__
__addon__ = xbmcaddon.Addon(id='service.subsmangler')
__addondir__ = xbmc.translatePath(__addon__.getAddonInfo('path').decode('utf-8'))
__addonworkdir__ = xbmc.translatePath(__addon__.getAddonInfo('profile').decode('utf-8'))
__version__ = __addon__.getAddonInfo('version')
__addonlang__ = __addon__.getLocalizedString
__kodiversion__ = xbmc.getInfoLabel('System.BuildVersion')[:4]



# prepare datadir
# directory and file is local to the filesystem
# no need to use xbmcvfs
if not os.path.isdir(__addonworkdir__):
    xbmc.log("SubsMangler: profile directory doesn't exist: " + __addonworkdir__.encode('utf-8') + "   Trying to create.", level=xbmc.LOGNOTICE)
    try:
        os.mkdir(__addonworkdir__)
        xbmc.log("SubsMangler: profile directory created: " + __addonworkdir__.encode('utf-8'), level=xbmc.LOGNOTICE)
    except OSError as e:
        xbmc.log("SubsMangler: Log: can't create directory: " + __addonworkdir__.encode('utf-8'), level=xbmc.LOGERROR)
        xbmc.log("Exception: " + str(e.message).encode('utf-8'), xbmc.LOGERROR)



# prepare external log handler
# https://docs.python.org/2/library/logging.handlers.html
global logger
logger = logging.getLogger(__name__)
loghandler = logging.handlers.TimedRotatingFileHandler(os.path.join(__addonworkdir__, 'smangler.log',), when="midnight", interval=1, backupCount=2)
logger.addHandler(loghandler)



# function parses log events based on internal logging level
# xbmc loglevels: https://forum.kodi.tv/showthread.php?tid=324570&pid=2671926#pid2671926
# 0 = LOGDEBUG
# 1 = LOGINFO
# 2 = LOGNOTICE
# 3 = LOGWARNING
# 4 = LOGERROR
# 5 = LOGSEVERE
# 6 = LOGFATAL
# 7 = LOGNONE
def Log(message, severity=xbmc.LOGDEBUG):
    """Log message to internal Kodi log or external log file.

    Arguments:
        message {str} -- message text

    Keyword Arguments:
        severity {int} -- log level (default: {xbmc.LOGDEBUG})
    """

    # get log level settings
    setting_LogLevel = int(__addon__.getSetting("LogLevel"))
    setting_SeparateLogFile = int(__addon__.getSetting("SeparateLogFile"))

    if severity >= setting_LogLevel:
        # log the message to Log
        if setting_SeparateLogFile == 0:
            # use kodi.log for logging
            # check if string is str
            if isinstance(message, str):
                # convert to unicode string
                message = message.decode('utf-8')
            # re-encode to utf-8
            xbmc.log("SubsMangler: " + message.encode('utf-8'), level=xbmc.LOGNONE)
        else:
            # use smangler's own log file located in addon's datadir
            # construct log text
            # cut last 3 trailing zero's from timestamp
            logtext = str(datetime.now())[:-3]
            if severity == xbmc.LOGDEBUG:
                logtext += "   DEBUG: "
            elif severity == xbmc.LOGINFO:
                logtext += "    INFO: "
            elif severity == xbmc.LOGNOTICE:
                logtext += "  NOTICE: "
            elif severity == xbmc.LOGWARNING:
                logtext += " WARNING: "
            elif severity == xbmc.LOGERROR:
                logtext += "   ERROR: "
            elif severity == xbmc.LOGSEVERE:
                logtext += "  SEVERE: "
            elif severity == xbmc.LOGFATAL:
                logtext += "   FATAL: "
            else:
                logtext += "    NONE: "
            logtext += message
            # append line to external log file
            # logging via warning level to prevent filtering of messages by default filtering level of ROOT logger
            logger.warning(logtext)



# read settings from configuration file
# settings are read only during addon's start - so for service type addon we need to re-read them after they are altered
# https://forum.kodi.tv/showthread.php?tid=201423&pid=1766246#pid1766246
def GetSettings():
    """Load settings from settings.xml file"""

    global setting_ConversionServiceEnabled
    global setting_AlsoConvertExistingSubtitles
    global setting_SubsOutputFormat
    global setting_SubsFontSize
    global setting_ForegroundColor
    global setting_BackgroundColor
    global setting_BackgroundTransparency
    global setting_MaintainBiggerLineSpacing
    global setting_RemoveCCmarks
    global setting_RemoveAds
    global setting_PauseOnConversion
    global setting_AutoInvokeSubsDialog
    global setting_AutoInvokeSubsDialogOnStream
    global setting_NoAutoInvokeIfLocalUnprocSubsFound
    global setting_NoConfirmationInvokeIfDownloadedSubsNotFound
    global setting_AutoUpdateDef
    global setting_SeparateLogFile
    global setting_AutoRemoveOldSubs
    global setting_BackupOldSubs
    global setting_RemoveSubsBackup
    global setting_RemoveUnprocessedSubs
    global setting_SimulateRemovalOnly
    global setting_AdjustSubDisplayTime
    global setting_FixOverlappingSubDisplayTime

    setting_AutoInvokeSubsDialog = GetBool(__addon__.getSetting("AutoInvokeSubsDialog"))
    setting_AutoInvokeSubsDialogOnStream = GetBool(__addon__.getSetting("AutoInvokeSubsDialogOnStream"))
    setting_NoAutoInvokeIfLocalUnprocSubsFound = GetBool(__addon__.getSetting("NoAutoInvokeIfLocalUnprocSubsFound"))
    setting_NoConfirmationInvokeIfDownloadedSubsNotFound = GetBool(__addon__.getSetting("NoConfirmationInvokeIfDownloadedSubsNotFound"))
    setting_ShowNoautosubsContextItem = GetBool(__addon__.getSetting("ShowNoautosubsContextItem"))
    setting_ConversionServiceEnabled = GetBool(__addon__.getSetting("ConversionServiceEnabled"))
    setting_AlsoConvertExistingSubtitles = GetBool(__addon__.getSetting("AlsoConvertExistingSubtitles"))
    setting_SubsOutputFormat = int(__addon__.getSetting("SubsOutputFormat"))
    setting_SubsFontSize = int(__addon__.getSetting("SubsFontSize"))
    setting_ForegroundColor = int(__addon__.getSetting("ForegroundColor"))
    setting_BackgroundColor = int(__addon__.getSetting("BackgroundColor"))
    setting_BackgroundTransparency = int(__addon__.getSetting("BackgroundTransparency"))
    setting_MaintainBiggerLineSpacing = GetBool(__addon__.getSetting("MaintainBiggerLineSpacing"))
    setting_RemoveCCmarks = GetBool(__addon__.getSetting("RemoveCCmarks"))
    setting_RemoveAds = GetBool(__addon__.getSetting("RemoveAdds"))
    setting_AdjustSubDisplayTime = GetBool(__addon__.getSetting("AdjustSubDisplayTime"))
    setting_FixOverlappingSubDisplayTime = GetBool(__addon__.getSetting("FixOverlappingSubDisplayTime"))
    setting_PauseOnConversion = GetBool(__addon__.getSetting("PauseOnConversion"))
    setting_BackupOldSubs = GetBool(__addon__.getSetting("BackupOldSubs"))
    setting_AutoRemoveOldSubs = GetBool(__addon__.getSetting("AutoRemoveOldSubs"))
    setting_RemoveSubsBackup = GetBool(__addon__.getSetting("RemoveSubsBackup"))
    setting_RemoveUnprocessedSubs = GetBool(__addon__.getSetting("RemoveUnprocessedSubs"))
    setting_SimulateRemovalOnly = GetBool(__addon__.getSetting("SimulateRemovalOnly"))
    setting_AutoUpdateDef = GetBool(__addon__.getSetting("AutoUpdateDef"))
    setting_LogLevel = int(__addon__.getSetting("LogLevel"))
    setting_SeparateLogFile = int(__addon__.getSetting("SeparateLogFile"))

    Log("Reading settings.", xbmc.LOGINFO)
    Log("Setting:                 AutoInvokeSubsDialog = " + str(setting_AutoInvokeSubsDialog), xbmc.LOGINFO)
    Log("                 AutoInvokeSubsDialogOnStream = " + str(setting_AutoInvokeSubsDialogOnStream), xbmc.LOGINFO)
    Log("           NoAutoInvokeIfLocalUnprocSubsFound = " + str(setting_NoAutoInvokeIfLocalUnprocSubsFound), xbmc.LOGINFO)
    Log(" NoConfirmationInvokeIfDownloadedSubsNotFound = " + str(setting_NoConfirmationInvokeIfDownloadedSubsNotFound), xbmc.LOGINFO)
    Log("                    ShowNoautosubsContextItem = " + str(setting_ShowNoautosubsContextItem), xbmc.LOGINFO)
    Log("                     ConversionServiceEnabled = " + str(setting_ConversionServiceEnabled), xbmc.LOGINFO)
    Log("                 AlsoConvertExistingSubtitles = " + str(setting_AlsoConvertExistingSubtitles), xbmc.LOGINFO)
    Log("                             SubsOutputFormat = " + str(setting_SubsOutputFormat), xbmc.LOGINFO)
    Log("                                 SubsFontSize = " + str(setting_SubsFontSize), xbmc.LOGINFO)
    Log("                              ForegroundColor = " + str(setting_ForegroundColor), xbmc.LOGINFO)
    Log("                              BackgroundColor = " + str(setting_BackgroundColor), xbmc.LOGINFO)
    Log("                       BackgroundTransparency = " + str(setting_BackgroundTransparency), xbmc.LOGINFO)
    Log("                    MaintainBiggerLineSpacing = " + str(setting_MaintainBiggerLineSpacing), xbmc.LOGINFO)
    Log("                                RemoveCCmarks = " + str(setting_RemoveCCmarks), xbmc.LOGINFO)
    Log("                                    RemoveAds = " + str(setting_RemoveAds), xbmc.LOGINFO)
    Log("                         AdjustSubDisplayTime = " + str(setting_AdjustSubDisplayTime), xbmc.LOGINFO)
    Log("                 FixOverlappingSubDisplayTime = " + str(setting_FixOverlappingSubDisplayTime), xbmc.LOGINFO)
    Log("                            PauseOnConversion = " + str(setting_PauseOnConversion), xbmc.LOGINFO)
    Log("                                BackupOldSubs = " + str(setting_BackupOldSubs), xbmc.LOGINFO)
    Log("                            AutoRemoveOldSubs = " + str(setting_AutoRemoveOldSubs), xbmc.LOGINFO)
    Log("                             RemoveSubsBackup = " + str(setting_RemoveSubsBackup), xbmc.LOGINFO)
    Log("                        RemoveUnprocessedSubs = " + str(setting_RemoveUnprocessedSubs), xbmc.LOGINFO)
    Log("                          SimulateRemovalOnly = " + str(setting_SimulateRemovalOnly), xbmc.LOGINFO)
    Log("                                AutoUpdateDef = " + str(setting_AutoUpdateDef), xbmc.LOGINFO)
    Log("                                     LogLevel = " + str(setting_LogLevel), xbmc.LOGINFO)
    Log("                              SeparateLogFile = " + str(setting_SeparateLogFile), xbmc.LOGINFO)

    # set setting value into the skin
    if setting_ShowNoautosubsContextItem:
        xbmc.executebuiltin('Skin.SetString(SubsMangler_ShowContextItem, true)')
    else:
        xbmc.executebuiltin('Skin.SetString(SubsMangler_ShowContextItem, false)')



# function parses input value and determines if it should be True or False value
# this is because Kodi's .getSetting function returns string type instead of a bool value
def GetBool(stringvalue):
    """Get boolean value from its text representation.

    Arguments:
        stringvalue {str} -- string representation

    Returns:
        bool -- boolean value
    """

    if stringvalue in ["1", "true", "True", "TRUE"]:
        return True
    else:
        return False



# function creates '.noautosubs' file for a particular video file
def CreateNoAutoSubsFile(file):
    """Create 'noautosubs' file.

    Arguments:
        file {str} -- path and name of file
    """

    # create .noautosubs file
    try:
        f = xbmcvfs.File (file, 'w')
        _result = f.write("# This file was created by Subtitles Mangler.\n# Presence of this file prevents automatical opening of subtitles search dialog.")
        f.close()
    except Exception as e:
        Log("Can not create noautosubs file.", xbmc.LOGERROR)
        Log("  Exception: " + str(e.message), xbmc.LOGERROR)



# function deletes file
def DeleteFile(file):
    """Delete file

    Arguments:
        file {str} -- path and name of file
    """

    try:
        xbmcvfs.delete(file)
    except Exception as e:
        Log("Delete failed: " + file.encode('utf-8'), xbmc.LOGERROR)
        Log("    Exception: " + str(e.message), xbmc.LOGERROR)
