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
import time
from datetime import datetime, timedelta
from threading import Timer

from resources.lib.Data.PL_DataSet import PL_DataSet, DataSetError, ItemConflictError
from resources.lib.Data.PlayListItem import PlayListItem, PlayListItemError, RecurrenceOptions
from resources.lib.KodiLib.KodiUtilities import kodiObj, getChannelGroups, getChannelInfo, getLastChannelInfo, TvGuideIsPresent
from resources.lib.Network.ClientServer import Server
from resources.lib.Network.SecretSauce import *
from resources.lib.Network.utilities import decodeRequest, encodeResponse, encodeErrorResponse, decodeError, genericEncode
from resources.lib.Utilities.DebugPrint import DbgPrint, setDebugMode, startTimer, stopTimer
from resources.lib.Utilities.Messaging import Cmd, OpStatus, xlateCmd2Notification, DAILYSTOPCOMMAND, STOPCMD_ACTIVE, \
    NotificationAction, VACATIONMODE,DEBUGMODE, ALARMTIME, PREROLLTIME, AUTOCLEANMODE
from resources.lib.Utilities.VirtualEvents import TS_decorator


__Version__ = "1.1.1"

MODULEDEBUGMODE=True

PLSERVERTAG = "LTVPL_PLSERVER_ACTIVE"



class PL_Server(object):
    def __init__(self, address, dataFileName, vacationmode=False, debugmode=False, autocleanMode=True):
        setDebugMode(debugmode)
        self.dataSet=PL_DataSet(dataFileName, vacationmode, autocleanMode)
        self.dataSet.AddItemRemovedEventHandler(self.onDataSetEvent)
        self.dataSet.AddItemCancelledEventHandler(self.onDataSetEvent)
        self.dataSet.AddItemUpdatedEventHandler(self.onDataSetEvent)
        self.dailyMaintenanceFlag = False
        self.dailyMaintThread = None # type: Timer
        self.server=Server(address, maxConnections=5)
        self.server.addDataReceivedEventHandler(self.onServerDataReceived)
        
        self.cmds={Cmd.AddPlayListItem:self.AddPlayListItem,
                   Cmd.RemovePlayListItem:self.RemovePlayListItem,
                   Cmd.RemoveAllPlayListItems:self.RemoveAllPlayListItems,
                   Cmd.GetChPlayListItems:self.GetChPlayListItems,
                   Cmd.GetPlayList:self.GetPlayList,
                   Cmd.GetChGroupList:self.GetChGroupList,
                   Cmd.GetChannelList:self.GetChannelList,
                   Cmd.SkipEvent:self.SkipEvent,
                   Cmd.GetPlayListItem:self.GetPlayListItem,
                   Cmd.UpdatePlayListItem:self.UpdatePlayListItem,
                   Cmd.SetVacationMode:self.SetVacationMode,
                   Cmd.GetVacationMode:self.GetVacationMode,
                   Cmd.SetPreRollTime:self.SetPreRollTime,
                   Cmd.GetPreRollTime:self.GetPreRollTime,
                   Cmd.EnablePlayListItem:self.EnablePlayListItem,
                   Cmd.GetPlayListItemState:self.GetPlayListItemState,
                   Cmd.DisablePlayListItem:self.DisablePlayListItem,
                   Cmd.ClearPlayList:self.ClearPlayList}

        DbgPrint("Server Initialized",MODULEDEBUGMODE=MODULEDEBUGMODE)


    def addSettingsChangedEventHandler(self, handler):
        self.dataSet.SettingsChangedEventHandler(handler)

    def onDataSetEvent(self, data):
        self.server.sendNotification(data)

    @TS_decorator
    def dailyMaintenance(self):
        from time import sleep
        """
            Wait for EPG to be present before verifying dataset and
            also before launching daily maintenance service 
        """
        count = 60
        lastCh = lastChNumber = self.dataSet.LastChNumber

        while count >= 0:
            try:
                if lastChNumber is None:
                    lastCh = getLastChannelInfo(kodiObj)['channelnumber']
                    if lastChNumber is None or lastCh > lastChNumber:
                        lastChNumber = self.dataSet.LastChNumber = lastCh

                if lastCh == lastChNumber and TvGuideIsPresent(kodiObj, lastCh):
                    DbgPrint("Got Last Channel & Tv Guide...")
                    self.dataSet.verifyDataset()
                    break
            except: pass

            sleep(5)
            count -= 1


        DbgPrint("Daily Maintenance Operation Started...")

        while self.dailyMaintenanceFlag:
            today = datetime.today().date()
            tomorrow = datetime.combine(today, datetime.min.time()) + timedelta(days=1, seconds=60)
            seconds = tomorrow - datetime.now()
            self.dailyMaintThread = Timer(seconds.total_seconds(), self.dataSet.verifyDataset)
            self.dailyMaintThread.start()
            time.sleep(1.0)
            self.dailyMaintThread.join()

        DbgPrint("Daily Maintenance Operation Stopped...")

    def stopServer(self):
        self.dailyMaintenanceFlag = False
        if self.dailyMaintThread is not None:
            self.dailyMaintThread.cancel()

        startTimer()  # measure time to stop server
        self.dataSet.Shutdown()
        self.server.stop()
        duration = stopTimer()  # measure time to stop server

        DbgPrint("Server Stopped",MODULEDEBUGMODE=MODULEDEBUGMODE)
        DbgPrint("It took {} seconds to stop the server".format(duration))

    def startServer(self):
        self.server.start()
        self.dailyMaintenanceFlag = True
        self.dailyMaintenance()
        DbgPrint("Server Started",MODULEDEBUGMODE=MODULEDEBUGMODE)


    def sendNotification(self, msg):
        self.server.sendNotification(msg)
        
    def onServerDataReceived(self,conn, data):
        DbgPrint("Calling onServerDataReceived",MODULEDEBUGMODE=MODULEDEBUGMODE)
        cmd,args=decodeRequest(data)
        arg=args[1]
        DbgPrint("cmd:{}\nargs:{}".format(cmd,arg),MODULEDEBUGMODE=MODULEDEBUGMODE)
        status=self.cmds[cmd](conn, arg) #Call the service provider
        DbgPrint("Exiting onServerDataReceived",MODULEDEBUGMODE=MODULEDEBUGMODE)

    def NotificationSend(self, cmd, data):
        try:
            rData3 = genericEncode(cmd, data)
            rData4 = genericEncode(xlateCmd2Notification(cmd), rData3)
            self.sendNotification(rData4)
            return rData4
        except Exception as e:
            DbgPrint("Exception:{}".format(str(e)))

    def ReturnData(self,conn,cmd, data, notify=True):
        rData = encodeResponse(cmd, data)
        rData2 = self.server._processData(rData) + DATAEndMarker
        conn.send(rData2.encode())

        if notify:
            time.sleep(1)
            self.NotificationSend(cmd, data)


    def ReturnError(self,conn,opStatus,errMsg):
        rData = encodeErrorResponse(opStatus, errMsg)
        rData2 = self.server._processData(rData) + DATAEndMarker
        conn.send(rData2.encode())

    def onChannelChange(self, PL_OBJ):
        DbgPrint("Deleting {} From List".format(PL_OBJ),MODULEDEBUGMODE=MODULEDEBUGMODE)


    def EnablePlayListItem(self, conn, args):
        id=args
        try:
            DbgPrint("Enabling PlayList Item:{}".format(id))
            item = self.dataSet.SearchByID(id)
            if item is None:
                self.ReturnError(conn,OpStatus.ItemDoesNotExist,"Item.ID {} Does Not Exist".format(id))
            try:
                item.SuspendedFlag=False
                self.dataSet.fileManager.Dirty = True
                self.dataSet.fileManager.backup()
                self.ReturnData(conn, Cmd.EnablePlayListItem, item.Data)
            except Exception as e:
                self.dataSet.SkipEventByID(item.ID)
                self.ReturnData(conn, Cmd.SkipEvent,item.Data)

        except Exception as e:
            self.ReturnError(conn, OpStatus.ItemDoesNotExist, str(e))

    def DisablePlayListItem(self, conn, args):
        id = args
        try:
            DbgPrint("Disabling PlayList Item:{}".format(id))
            item = self.dataSet.SearchByID(id)
            item.SuspendedFlag = True
            self.dataSet.fileManager.Dirty = True
            self.dataSet.fileManager.backup()
            self.ReturnData(conn, Cmd.DisablePlayListItem, item.Data)
        except Exception as e:
            self.ReturnError(conn, OpStatus.ItemDoesNotExist, str(e))

    def GetPlayListItemState(self, conn, args):
        id = args
        try:
            item = self.dataSet.SearchByID(id)
            data={id:item.SuspendedFlag}
            self.ReturnData(conn, Cmd.GetPlayListItemState, data, notify=False)
        except Exception as e:
            self.ReturnError(conn, OpStatus.ItemDoesNotExist, str(e))

    def SetVacationMode(self, conn, args):
        """
        :param args: boolean
        :return:
        """
        self.dataSet.VacationMode = args
        self.ReturnData(conn,Cmd.SetVacationMode, self.dataSet.VacationMode)


    def GetVacationMode(self, conn, args):
        retvalue = self.dataSet.VacationMode
        self.ReturnData(conn,Cmd.GetVacationMode,retvalue, notify=False)


    def SetPreRollTime(self, conn, args):
        self.dataSet.PreRollTime = int(args)
        self.ReturnData(conn, Cmd.SetPreRollTime, args)

    def GetPreRollTime(self, conn, args):
        retvalue = self.dataSet.PreRollTime
        self.ReturnData(conn, Cmd.GetPreRollTime, retvalue, notify=False)


    def SkipEvent(self,conn, args):
        DbgPrint("SkipEvent Called",MODULEDEBUGMODE=MODULEDEBUGMODE)
        try:
            item=self.dataSet.SkipEventByID(args)

            if item.isActive or item.SuspendedFlag:
                self.ReturnData(conn, Cmd.SkipEvent, item.Data)
            else:
                self.ReturnData(conn, Cmd.RemovePlayListItem, item.Data)
        except Exception as e:
            self.ReturnError(conn,OpStatus.GeneralFailure,"SkipEvent:" + str(e))


    def GetChGroupList(self,conn, args):
        try:
            grpList = getChannelGroups(kodiObj)
            self.ReturnData(conn,Cmd.GetChGroupList,grpList, notify=False)
        except Exception as e:
            self.ReturnError(conn,OpStatus.GeneralFailure, "GetChGroupList:" + str(e))


    def GetChannelList(self,conn, args):
        try:
            chList = getChannelInfo(kodiObj, chGroup=args, params=None)
            self.ReturnData(conn, Cmd.GetChannelList, chList, notify=False)
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, "GetChannelList:" + str(e))


    def UpdatePlayListItem(self,conn,args):
        obj = PlayListItem()
        obj.Data=args
        try:
            self.dataSet.updatePlayListItem(obj)
            self.ReturnData(conn, Cmd.UpdatePlayListItem, obj.Data) #Send Display Request
        except DataSetError as e:
            err,errmsg=decodeError(e.errdata)
            self.ReturnError(conn, err, str(e))
        except PlayListItemError as e:
            err, errmsg = decodeError(e.errdata)
            self.ReturnError(conn, err, str(e))


    def AddPlayListItem(self,conn, args):
        try:
            DbgPrint("Calling AddPlayListItem",MODULEDEBUGMODE=MODULEDEBUGMODE)
            obj=PlayListItem(eventHandler=self.onChannelChange)
            DbgPrint("type(obj.ChChangeEvent): {}".format(type(obj.ChChangeEvent)),MODULEDEBUGMODE=MODULEDEBUGMODE)
            DbgPrint("obj.ChChangeEvent: {}".format(obj.ChChangeEvent),MODULEDEBUGMODE=MODULEDEBUGMODE)
            obj.Data=args
            DbgPrint("AddPlayListItem({})".format(obj),MODULEDEBUGMODE=MODULEDEBUGMODE)
            self.dataSet.AddPlayList(obj)
            DbgPrint("Exiting AddPlayListItem",MODULEDEBUGMODE=MODULEDEBUGMODE)

            self.ReturnData(conn, Cmd.AddPlayListItem, obj.Data) # Send back display request
        except DataSetError as e:
            err,errmsg=decodeError(e.errdata)
            self.ReturnError(conn, err, errmsg)
        except ItemConflictError as e:
            err, errmsg = decodeError(e.errdata)
            self.ReturnError(conn, err, errmsg)


    def RemoveAllPlayListItems(self, conn):
        try:
            DbgPrint("RemoveAllPlayListItems",MODULEDEBUGMODE=MODULEDEBUGMODE)
            self.dataSet.RemoveAll()
            self.ReturnData(conn, Cmd.RemoveAllPlayListItems, str(OpStatus.Success))
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, "RemoveAllPlayListItems:" + str(e))

    def RemovePlayListItem(self,conn, id):
        try:
            DbgPrint("RemovePlayListItem({})".format(id),MODULEDEBUGMODE=MODULEDEBUGMODE)
            self.dataSet.RemoveByID(id)
            self.ReturnData(conn, Cmd.RemovePlayListItem, id) # Send back display request
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, "RemovePlayListItem:" + str(e))


    def GetChPlayListItems(self, conn, ch):
        try:
            DbgPrint("GetPlayListItem({})".format(ch),MODULEDEBUGMODE=MODULEDEBUGMODE)
            itemList=self.dataSet.FindCh(ch[1])
            myList=[]
            for item in itemList:
                myList.append(item.Data)

            self.ReturnData(conn, Cmd.GetChPlayListItems, myList, notify=False)
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, str(e))


    def GetPlayList(self,conn, args):
        try:
            DbgPrint("GetPlayList Called",MODULEDEBUGMODE=MODULEDEBUGMODE)
            data = self.dataSet.Data
            try:
                del data['lastChNumber']
            except: pass

            self.ReturnData(conn, Cmd.GetPlayList,data, notify=False)
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, "GetPlayList:" + str(e))


    def GetPlayListItem(self,conn,args):
        try:
            DbgPrint("GetPlayListItem Called",MODULEDEBUGMODE=MODULEDEBUGMODE)
            obj = self.dataSet.GetPlayListItemByID(args)
            data = encodeResponse(Cmd.GetPlayListItem, obj.Data)
            rData = self.server.translateData(data)
            self.ReturnData(conn,Cmd.GetPlayListItem,rData, notify=False)
        except Exception as e:
            self.ReturnError(conn, OpStatus.GeneralFailure, "GetPlayListItem:" + str(e))

    def ClearPlayList(self,conn,args):
        DbgPrint("ClearPlayList Called", MODULEDEBUGMODE=MODULEDEBUGMODE)
        self.dataSet.clear()
        self.ReturnData(conn, Cmd.ClearPlayList,None)

    def setSettings(self, newValues):
        """
        :type newValues: dict
        """
        for key in newValues.keys():
            if key == VACATIONMODE:
                #Vacation Mode
                vacationMode = newValues[key]
                self.dataSet.VacationMode = vacationMode
                msg = self.NotificationSend(Cmd.SetVacationMode, vacationMode)
                DbgPrint("Server Vacation Mode:{}\tNotification:{}".format(vacationMode, msg))

            elif key == AUTOCLEANMODE:
                #Playlist Auto Clean Mode
                autocleanMode = newValues[key]
                self.dataSet.AutocleanMode = autocleanMode

            elif key == DEBUGMODE:
                #Debug Mode
                debugMode = newValues[key]
                setDebugMode(debugMode)
                DbgPrint("***setingsChanged: DebugMode:{}".format(debugMode))

            elif key == STOPCMD_ACTIVE:
                #Daily Stop Command
                dailyStopCmdActive = newValues[key]
                strStopCmdAlarmtime = newValues[ALARMTIME]
                self.setDailyStopCmdAlarmtime(dailyStopCmdActive, strStopCmdAlarmtime)

            elif key == PREROLLTIME:
                #Preroll Time
                self.dataSet.PreRollTime = newValues[key]

    def getDailyStopCmdAlarmtime(self):
        itemlist = self.dataSet.FindCh(Cmd.Stop_Player.value)
        if len(itemlist) == 0:
            return None

        item = itemlist[0]
        alarmtime = item.alarmtime
        strAlarmtime= "{:02d}:{:02d}".format(alarmtime.hour, alarmtime.minute)
        return strAlarmtime

    def setDailyStopCmdAlarmtime(self, dailyStopCmdActive, strStopCmdAlarmtime):
        if not dailyStopCmdActive:
            self.disableDailyStopCmd()
            self.dataSet.FireSettingsChangedEvent(DAILYSTOPCOMMAND, {STOPCMD_ACTIVE: False, 'alarmtime': None})

        elif dailyStopCmdActive and strStopCmdAlarmtime is not None:
            if dailyStopCmdActive == False:
                return

            if len(strStopCmdAlarmtime) <= 0:
                return
            try:
                tmp = strStopCmdAlarmtime.split(':')
                seconds = int(tmp[0]) * 3600 + int(tmp[1]) * 60
                alarmtime = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(seconds=seconds)
                if alarmtime < datetime.now():
                    alarmtime = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(days=1, seconds=seconds)

                self.enableDailyStopCmd(alarmtime)
                self.dataSet.FireSettingsChangedEvent(DAILYSTOPCOMMAND,{'stopcmd_active': True, 'alarmtime': strStopCmdAlarmtime})
            except Exception as e: pass

    def enableDailyStopCmd(self, alarmtime):
        itemlist = self.dataSet.FindCh(Cmd.Stop_Player.value)
        if len(itemlist) > 0:
            item = itemlist[0]
            if item.alarmtime != alarmtime:
                DbgPrint("Updating Stop Command")
                item.alarmtime = alarmtime
                self.dataSet.updatePlayListItem(item)
                self.NotificationSend(Cmd.UpdatePlayListItem, item.Data)

        else:
            item = PlayListItem(alarmtime=alarmtime, ch=Cmd.Stop_Player.value, title="Daily Player Stop Command",
                               recurrenceInterval=RecurrenceOptions.DAILY)

            item.eventHandler=self.onChannelChange
            DbgPrint("Creating Stop Command")
            self.dataSet.AddPlayList(item)
            self.NotificationSend(Cmd.AddPlayListItem, item.Data)


    def disableDailyStopCmd(self):
        itemlist = self.dataSet.FindCh(Cmd.Stop_Player.value)
        if len(itemlist) > 0:
            item = itemlist[0]
            id = item.ID
            self.dataSet.Remove(itemlist[0])
            self.NotificationSend(Cmd.RemovePlayListItem, item.Data)


    def getDailyStopCmdTime(self,conn,args):
        itemlist = self.dataSet.FindCh(Cmd.Stop_Player.value)
        if len(itemlist > 0):
            item = itemlist[0]
            self.ReturnData(conn,Cmd.GetDailyStopCmdTime, str(item.alarmtime), notify=False)


    def Login(self,conn,args):
        pass


    def Logout(self,conn,args):
        pass




