#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import os
import sys

import xbmc
import xbmcgui

__Version__ = "1.0.3"

#from logger import logxbmc.log("***path")

# print str(sys.path)
myLog = xbmc.log

from util import ADDON, ADDONID, ADDON_USERDATA_FOLDER, DATAFILE_LOCATIONFILE, ADDON_DATAFILENAME,\
    DEFAULTPATH, DEBUGFILE_LOCATIONFILE, DEBUGFILE_LOCATIONCONTENT
from resources.lib.Network.SecretSauce import ServerPort
from resources.PL_Server import PLSERVERTAG, PL_Server
from utility import isDialogActive, clearDialogActive, setDialogActive
from resources.lib.Utilities.Messaging import VACATIONMODE, PREROLLTIME, DAILYSTOPCOMMAND, DEBUGMODE, STOPCMD_ACTIVE,\
    ALARMTIME, COUNTDOWN_DURATION, TRUE, FALSE, WRITEMODE, AUTOCLEANMODE
import Countdown
from resources.lib.Utilities.DebugPrint import DbgPrint


xbmc.log("***sys.path: "+str(sys.path))

LTVPL = 'Live TV Playlist'

LocalOperationFlag = False
RemoteOperationFlag = False


def establishDataLocations():
    if not os.path.exists(ADDON_USERDATA_FOLDER):
        xbmc.log("LTVPL: Making addonUserDataFolder")
        try:
            os.mkdir(ADDON_USERDATA_FOLDER)
        except Exception as e:
            DbgPrint(e)
    else:
        xbmc.log("LTVPL: addonUserDataFolder Exists")

    #Data File
    fs = open(DATAFILE_LOCATIONFILE,WRITEMODE)
    fs.write(DEFAULTPATH)
    fs.close()
    #

    # Debug File
    fs = open(DEBUGFILE_LOCATIONFILE, WRITEMODE)
    fs.write(DEBUGFILE_LOCATIONCONTENT)
    fs.close()
    xbmc.log("LTVPL: establishDataLocations Done")

xbmc.log("ltvpl data path: " + ADDON_USERDATA_FOLDER )

class Monitor(xbmc.Monitor):
    def __init__(self, server, cdService):
        """

        :type server: PL_Server
        """
        xbmc.Monitor.__init__(self)
        self.server = server #type: PL_Server
        self.cdService = cdService #type: Countdown.miniClient
        self.countdown_duration=int(ADDON.getSetting(COUNTDOWN_DURATION))
        self.debugMode=str(ADDON.getSetting(DEBUGMODE)).lower() == TRUE
        self.vacationMode=str(ADDON.getSetting(VACATIONMODE)).lower() == TRUE
        self.stopcmd_active=str(ADDON.getSetting(STOPCMD_ACTIVE)).lower() == TRUE
        self.strAlarmtime=str(ADDON.getSetting(ALARMTIME))
        self.preroll_time=int(ADDON.getSetting(PREROLLTIME))
        self.autocleanMode=ADDON.getSetting(AUTOCLEANMODE)

    def onSettingsChanged(self):
        global LocalOperationFlag
        global RemoteOperationFlag

        if RemoteOperationFlag:
            RemoteOperationFlag = False
            return

        newValues = {}
        myLog("onSettingsChanged Called", level=xbmc.LOGDEBUG)
        #Local Settings

        # Countdown Duration
        countdown_duration = int(ADDON.getSetting(COUNTDOWN_DURATION))
        if self.countdown_duration != countdown_duration:
            self.countdown_duration=countdown_duration
            self.cdService.CountDownDuration = countdown_duration

        #Debug_Mode
        LocalOperationFlag=True
        #Debug Mode
        debugMode = str(ADDON.getSetting(DEBUGMODE)).lower() == TRUE
        if self.debugMode != debugMode:
            self.debugMode=debugMode
            newValues.update({DEBUGMODE:debugMode})

        #Vacation Mode
        vacationMode = str(ADDON.getSetting(VACATIONMODE)).lower() == TRUE
        if self.vacationMode != vacationMode:
            self.vacationMode=vacationMode
            newValues.update({VACATIONMODE:vacationMode})

        #Playlist Auto Clean Mode
        autocleanMode = str(ADDON.getSetting(AUTOCLEANMODE)).lower() == TRUE
        if self.autocleanMode != autocleanMode:
            self.autocleanMode = autocleanMode
            newValues.update({AUTOCLEANMODE:autocleanMode})

        #Daily Stop Command
        stopcmd_active = str(ADDON.getSetting(STOPCMD_ACTIVE)).lower() == TRUE
        strAlarmtime = str(ADDON.getSetting(ALARMTIME))
        if self.stopcmd_active != stopcmd_active or self.strAlarmtime != strAlarmtime:
            self.stopcmd_active = stopcmd_active
            self.strAlarmtime = strAlarmtime
            newValues.update({STOPCMD_ACTIVE:stopcmd_active})
            newValues.update({ALARMTIME:strAlarmtime})


        #Preroll Time
        preroll_time = int(ADDON.getSetting(PREROLLTIME))
        if self.preroll_time!= preroll_time:
            self.preroll_time=preroll_time
            newValues.update({PREROLLTIME:preroll_time})

        #Process Changed Settings
        try:
            if len(newValues) > 0:
                myLog("settingsChangedFlag: True", level=xbmc.LOGDEBUG)
                try:
                    self.server.setSettings(newValues)
                except Exception as e:
                    xbmcgui.Dialog().notification(LTVPL,str(e), xbmcgui.NOTIFICATION_ERROR)

        except ValueError as e:
            xbmcgui.Dialog().notification(LTVPL, str(e))



def onServerSettingsChanged(setting, value):
    global LocalOperationFlag
    global RemoteOperationFlag

    if LocalOperationFlag:
        LocalOperationFlag = False
        return

    RemoteOperationFlag = True

    if setting==PREROLLTIME:
        ADDON.setSetting(PREROLLTIME, str(value))
    elif setting==VACATIONMODE:
        ADDON.setSetting(VACATIONMODE, str(value).lower())
    elif setting==AUTOCLEANMODE:
        ADDON.setSetting(AUTOCLEANMODE, str(value).lower())
    elif setting==DAILYSTOPCOMMAND:
        if value[STOPCMD_ACTIVE]:
            ADDON.setSetting(STOPCMD_ACTIVE, TRUE)
            ADDON.setSetting(ALARMTIME, value[ALARMTIME])
        else:
            ADDON.setSetting(STOPCMD_ACTIVE, FALSE)

    # RemoteOperationFlag = False

if __name__ == '__main__':
    cdService = None #type: Countdown.miniClient
    server = None #type: PL_Server

    if not isDialogActive(PLSERVERTAG):
        address = ('', ServerPort)
        establishDataLocations()
        vacationMode = str(ADDON.getSetting(VACATIONMODE)).lower() == TRUE
        debugMode = str(ADDON.getSetting(DEBUGMODE)).lower() == TRUE
        autocleanMode = str(ADDON.getSetting(AUTOCLEANMODE)).lower() == TRUE
        stopcmd_active = str(ADDON.getSetting(STOPCMD_ACTIVE)).lower() == TRUE

        server = PL_Server(address, ADDON_DATAFILENAME, vacationMode, debugMode, autocleanMode)
        setDialogActive(PLSERVERTAG)
        # check for daily stop command and add it if settings authorize it
        strAlarmtime = server.getDailyStopCmdAlarmtime()
        if strAlarmtime is not None:
            ADDON.setSetting(STOPCMD_ACTIVE, TRUE)
            ADDON.setSetting(ALARMTIME, strAlarmtime)
        elif stopcmd_active:
            strAlarmtime = str(ADDON.getSetting(ALARMTIME))
            if strAlarmtime is not None:
                newValues = {}
                newValues.update({STOPCMD_ACTIVE: stopcmd_active})
                newValues.update({ALARMTIME: strAlarmtime})
                server.setSettings(newValues)

        server.startServer()
        server.addSettingsChangedEventHandler(onServerSettingsChanged)
        xbmc.log("Live TV Playlist Server Started...")

        while not server.server.isAlive():
            xbmc.sleep(500)

        # import Countdown
        try:
            countdown_duration= int(ADDON.getSetting(COUNTDOWN_DURATION))
            cdService = Countdown.StartCountdownService(ADDONID, clockstarttime=countdown_duration, abortChChange=server.dataSet.AbortChannelChangeOperation)
            xbmc.log("****Mini Client Service Successfully Started....")
        except Exception as e: pass

        monitor = Monitor(server, cdService)
        monitor.waitForAbort()

        cdService.Stop()
        server.stopServer()

        del monitor
        del cdService
        del server
        clearDialogActive(PLSERVERTAG)
        xbmc.log("Live TV Playlist Server Stopped...", level=xbmc.LOGNOTICE)
