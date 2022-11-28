# This file includes parts of code that are shared between modules

import os
import logging
import unicodedata
import xbmc
import xbmcvfs

from json import loads
from logging.handlers import RotatingFileHandler
from resources.lib import globals
from datetime import datetime


# function initiates external log handler for an instance of application
def InitiateLogger():
    # prepare external log handler
    # https://docs.python.org/2/library/logging.handlers.html
    globals.logger = logging.getLogger(__name__)
    loghandler = logging.handlers.TimedRotatingFileHandler(os.path.join(globals.__addonworkdir__, 'smangler.log', ),
                                                           when="midnight", interval=1, backupCount=2)
    globals.logger.addHandler(loghandler)


# function parses log events based on internal logging level
# xbmc loglevels: https://forum.kodi.tv/showthread.php?tid=324570&pid=2671926#pid2671926
# 0 = LOGDEBUG
# 1 = LOGINFO
# 2 = LOGNOTICE - since Kodi 19 is deprecated and LOGINFO should be used instead
# 3 = LOGWARNING
# 4 = LOGERROR
# 5 = LOGSEVERE - since Kodi 19 is deprecated and LOGFATAL should be used instead
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
    setting_LogLevel = int(globals.__addon__.getSetting("LogLevel"))
    setting_SeparateLogFile = int(globals.__addon__.getSetting("SeparateLogFile"))

    if severity >= setting_LogLevel:
        # log the message to Log
        if setting_SeparateLogFile == 0:
            # use kodi.log for logging
            xbmc.log("SubsMangler: " + message, level=xbmc.LOGNONE)
        else:
            # use smangler's own log file located in addon's datadir
            # construct log text
            # cut last 3 trailing zero's from timestamp
            logtext = str(datetime.now())[:-3]
            if severity == xbmc.LOGDEBUG:
                logtext += "   DEBUG: "
            elif severity == xbmc.LOGINFO:
                logtext += "    INFO: "
            elif severity == xbmc.LOGWARNING:
                logtext += " WARNING: "
            elif severity == xbmc.LOGERROR:
                logtext += "   ERROR: "
            elif severity == xbmc.LOGFATAL:
                logtext += "   FATAL: "
            else:
                logtext += "    NONE: "
            logtext += unicodedata.normalize('NFKD', message).encode('ascii', 'ignore').decode('ascii')
            # append line to external log file
            # logging via warning level to prevent filtering of messages by default filtering level of ROOT logger
            globals.logger.warning(logtext)


# set Kodi system setting
# https://forum.kodi.tv/showthread.php?tid=209587&pid=1844182#pid1844182
def SetKodiSetting(name, setting):
    """Set Kodi setting value for given section name.

    Arguments:
        name {str} -- Kodi section name
        setting {str} -- setting value
    """

    # Uses XBMC/Kodi JSON-RPC API to set value.
    command = '''{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Settings.SetSettingValue",
    "params": {
        "setting": "%s",
        "value": %s
    }
}'''
    result = xbmc.executeJSONRPC(command % (name, setting))
    py = loads(result)
    Log("JSON-RPC: Settings.SetSettingValue: " + str(py), xbmc.LOGDEBUG)


# read settings from configuration file
# settings are read only during addon's start - so for service type addon we need to re-read them after they are altered
# https://forum.kodi.tv/showthread.php?tid=201423&pid=1766246#pid1766246
def GetSettings():
    """Load settings from settings.xml file"""

    globals.setting_AutoInvokeSubsDialog = GetBool(globals.__addon__.getSetting("AutoInvokeSubsDialog"))
    globals.setting_AutoInvokeSubsDialogOnStream = GetBool(globals.__addon__.getSetting("AutoInvokeSubsDialogOnStream"))
    globals.setting_NoAutoInvokeIfLocalUnprocSubsFound = GetBool(
        globals.__addon__.getSetting("NoAutoInvokeIfLocalUnprocSubsFound"))
    globals.setting_NoConfirmationInvokeIfDownloadedSubsNotFound = GetBool(
        globals.__addon__.getSetting("NoConfirmationInvokeIfDownloadedSubsNotFound"))
    globals.setting_ShowNoautosubsContextItem = GetBool(globals.__addon__.getSetting("ShowNoautosubsContextItem"))
    globals.setting_ConversionServiceEnabled = GetBool(globals.__addon__.getSetting("ConversionServiceEnabled"))
    globals.setting_AlsoConvertExistingSubtitles = GetBool(globals.__addon__.getSetting("AlsoConvertExistingSubtitles"))
    globals.setting_RemoveCCmarks = GetBool(globals.__addon__.getSetting("RemoveCCmarks"))
    globals.setting_RemoveAds = GetBool(globals.__addon__.getSetting("RemoveAdds"))
    globals.setting_AdjustSubDisplayTime = GetBool(globals.__addon__.getSetting("AdjustSubDisplayTime"))
    globals.setting_FixOverlappingSubDisplayTime = GetBool(globals.__addon__.getSetting("FixOverlappingSubDisplayTime"))
    globals.setting_PauseOnConversion = GetBool(globals.__addon__.getSetting("PauseOnConversion"))
    globals.setting_BackupOldSubs = GetBool(globals.__addon__.getSetting("BackupOldSubs"))
    globals.setting_AutoRemoveOldSubs = GetBool(globals.__addon__.getSetting("AutoRemoveOldSubs"))
    globals.setting_RemoveSubsBackup = GetBool(globals.__addon__.getSetting("RemoveSubsBackup"))
    globals.setting_RemoveUnprocessedSubs = GetBool(globals.__addon__.getSetting("RemoveUnprocessedSubs"))
    globals.setting_SimulateRemovalOnly = GetBool(globals.__addon__.getSetting("SimulateRemovalOnly"))
    globals.setting_AutoUpdateDef = GetBool(globals.__addon__.getSetting("AutoUpdateDef"))
    globals.setting_LogLevel = int(globals.__addon__.getSetting("LogLevel"))
    globals.setting_SeparateLogFile = int(globals.__addon__.getSetting("SeparateLogFile"))

    Log("Reading settings.", xbmc.LOGINFO)
    Log("Setting:                 AutoInvokeSubsDialog = " + str(globals.setting_AutoInvokeSubsDialog), xbmc.LOGINFO)
    Log("                 AutoInvokeSubsDialogOnStream = " + str(globals.setting_AutoInvokeSubsDialogOnStream),
        xbmc.LOGINFO)
    Log("           NoAutoInvokeIfLocalUnprocSubsFound = " + str(globals.setting_NoAutoInvokeIfLocalUnprocSubsFound),
        xbmc.LOGINFO)
    Log(" NoConfirmationInvokeIfDownloadedSubsNotFound = " + str(
        globals.setting_NoConfirmationInvokeIfDownloadedSubsNotFound), xbmc.LOGINFO)
    Log("                    ShowNoautosubsContextItem = " + str(globals.setting_ShowNoautosubsContextItem),
        xbmc.LOGINFO)
    Log("                     ConversionServiceEnabled = " + str(globals.setting_ConversionServiceEnabled),
        xbmc.LOGINFO)
    Log("                 AlsoConvertExistingSubtitles = " + str(globals.setting_AlsoConvertExistingSubtitles),
        xbmc.LOGINFO)
    Log("                                RemoveCCmarks = " + str(globals.setting_RemoveCCmarks), xbmc.LOGINFO)
    Log("                                    RemoveAds = " + str(globals.setting_RemoveAds), xbmc.LOGINFO)
    Log("                         AdjustSubDisplayTime = " + str(globals.setting_AdjustSubDisplayTime), xbmc.LOGINFO)
    Log("                 FixOverlappingSubDisplayTime = " + str(globals.setting_FixOverlappingSubDisplayTime),
        xbmc.LOGINFO)
    Log("                            PauseOnConversion = " + str(globals.setting_PauseOnConversion), xbmc.LOGINFO)
    Log("                                BackupOldSubs = " + str(globals.setting_BackupOldSubs), xbmc.LOGINFO)
    Log("                            AutoRemoveOldSubs = " + str(globals.setting_AutoRemoveOldSubs), xbmc.LOGINFO)
    Log("                             RemoveSubsBackup = " + str(globals.setting_RemoveSubsBackup), xbmc.LOGINFO)
    Log("                        RemoveUnprocessedSubs = " + str(globals.setting_RemoveUnprocessedSubs), xbmc.LOGINFO)
    Log("                          SimulateRemovalOnly = " + str(globals.setting_SimulateRemovalOnly), xbmc.LOGINFO)
    Log("                                AutoUpdateDef = " + str(globals.setting_AutoUpdateDef), xbmc.LOGINFO)
    Log("                                     LogLevel = " + str(globals.setting_LogLevel), xbmc.LOGINFO)
    Log("                              SeparateLogFile = " + str(globals.setting_SeparateLogFile), xbmc.LOGINFO)

    # set setting value into the skin
    if globals.setting_ShowNoautosubsContextItem:
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
        f = xbmcvfs.File(file, 'w')
        _result = f.write(
            "# This file was created by Subtitles Mangler.\n# Presence of this file prevents automatical opening of subtitles search dialog.")
        f.close()
    except Exception as e:
        Log("Can not create noautosubs file.", xbmc.LOGERROR)
        Log("  Exception: " + str(e), xbmc.LOGERROR)


# function deletes file
def DeleteFile(file):
    """Delete file

    Arguments:
        file {str} -- path and name of file
    """

    try:
        xbmcvfs.delete(file)
    except Exception as e:
        Log("Delete failed: " + file, xbmc.LOGERROR)
        Log("    Exception: " + str(e), xbmc.LOGERROR)
