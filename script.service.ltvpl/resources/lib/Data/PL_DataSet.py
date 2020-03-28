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
from copy import copy
from datetime import datetime, timedelta

from resources.lib.KodiLib.KodiUtilities import kodiObj, changeChannelByChannelNumber, playerStop, \
    getBroadcast_startTimeList, KODI_ENV
from resources.lib.Network.myJson_io import myJson_io
from resources.lib.Network.myPickle_io import myPickle_io
from resources.lib.Network.utilities import genericEncode, encodeError
from resources.lib.Utilities.AlarmsMgr import _Alarms
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Utilities.Messaging import Cmd, VACATIONMODE, PREROLLTIME
from resources.lib.Utilities.Messaging import NotificationAction, OpStatus
from resources.lib.Utilities.PythonEvent import Event
from resources.lib.Utilities.VirtualEvents import TS_decorator
from .PlayListItem import PlayListItem, isPlayListItem, RecurrenceOptions, ALARMPADDING
from .fileManager import fileManager, FileManagerMode

if KODI_ENV:
    import xbmcgui
    import xbmcaddon

    ADDON = xbmcaddon.Addon()

    def GETTEXT(id):
        return ADDON.getLocalizedString(id).encode('utf-8')

__Version__ = "1.1.3"

DELETE_WAIT_TIME=1
MODULEDEBUGMODE=True
LTVPL = 'Live TV Playlist'
#DbgPrint=LoggerSetup("PL_DataSet")

        
class PL_DataSet(list,myPickle_io,myJson_io):
    """
        Events:
            ItemRemovedEvent -> Fired when a PlayList item is removed from the dataset
            ItemCancelledEvent -> Fired when a PlayList item is cancelled
    """
    def __init__(self, dataFileName, vacationmode=False, autocleanMode=True):
        list.__init__(self)
        myPickle_io.__init__(self)
        self.ItemRemovedEvent=Event("ItemRemovedEvent",spawn=True)
        self.ItemCancelledEvent=Event("ItemCancelledEvent",spawn=True)
        self.ItemAddedEvent=Event("ItemAddedEvent",spawn=True)
        self.ItemUpdatedEvent=Event("ItemUpdatedEvent",spawn=True)
        self.SettingsChangedEvent=Event("SettingsChangedEvent", spawn=True)
        self.skipOperationActive = False
        self.vacationmode = vacationmode
        self.autocleanmode = autocleanMode
        self.prerolltime = ALARMPADDING
        self.abortOperation = False
        self.lastChannel = None
        self.fileManager=fileManager(self, dataFileName, mode=FileManagerMode.PICKLE)
        DbgPrint("***Calling Data Restore Operation...")
        self.fileManager.restore()
        DbgPrint("***LastChannel: {}".format(self.lastChannel))
        if KODI_ENV and self.lastChannel is None:
            DbgPrint("*****LastChannel->: {} isNone:{}".format(self.lastChannel, self.lastChannel is None))
            xbmcgui.Dialog().notification(LTVPL, GETTEXT(30068)) #"Scanning Channel List..."
        self.prerolltime=ALARMPADDING


    def AbortChannelChangeOperation(self):
        self.abortOperation = True

    @TS_decorator
    def _processVacationMode(self, mode):
        if mode:
            self.CancelAll(notify=False)
        else:
            self.verifyDataset()
            self.Start()

        self.fileManager.Dirty = True
        self.fileManager.backup()

    @property
    def VacationMode(self):
        return self.vacationmode

    @VacationMode.setter
    def VacationMode(self, mode):
        """
        :param mode: boolean
        :return:
        """
        if self.vacationmode == mode:
            return

        self.vacationmode=mode
        self._processVacationMode(mode)

        self.FireSettingsChangedEvent(VACATIONMODE, mode)

    @property
    def AutocleanMode(self):
        return self.autocleanmode

    @AutocleanMode.setter
    def AutocleanMode(self, value):
        if self.autocleanmode != value:
            self.autocleanmode = value
            DbgPrint("Playlist Autoclean Mode: {}".format(self.autocleanmode))

    @property
    def LastChNumber(self):
        return self.lastChannel

    @LastChNumber.setter
    def LastChNumber(self, value):
        if type(value) == float and value > 0.0:
            self.lastChannel = value
            self.fileManager.Dirty = True
            self.fileManager.backup()

    @property
    def PreRollTime(self):
        return self.prerolltime

    @PreRollTime.setter
    def PreRollTime(self, value):
        if self.prerolltime == value:
            return

        self.prerolltime = value
        for item in self: # type: PlayListItem
            item.PreRollTime = value

        self.FireSettingsChangedEvent(PREROLLTIME, value)


    def SuspendItem(self, id):
        item = self.SearchByID(id)
        if item is None:
            raise Exception
            # raise(Exception("ItemID: {} Not Found".format(id)))

        item.SuspendedFlag=True
        self.fileManager.Dirty = True
        self.fileManager.backup()

    def EnableItem(self, id):
        item = self.SearchByID(id)
        if item is None:
            raise Exception
            # raise (Exception("ItemID: {} Not Found".format(id)))

        item.SuspendedFlag=False
        self.fileManager.Dirty = True
        self.fileManager.backup()

    def AddItemRemovedEventHandler(self, handler):
        self.ItemRemovedEvent.AddHandler(handler)

    def AddItemCancelledEventHandler(self, handler):
        self.ItemCancelledEvent.AddHandler(handler)

    def AddItemAddedEventHandler(self, handler):
        self.ItemAddedEvent.AddHandler(handler)

    def AddItemUpdatedEventHandler(self, handler):
        self.ItemUpdatedEvent.AddHandler(handler)

    def SettingsChangedEventHandler(self, handler):
        self.SettingsChangedEvent.AddHandler(handler)

    def FireItemRemovedEvent(self, item):
        #data={str(Cmd.ItemRemoved):item.Data}
        data1 = genericEncode(Cmd.RemovePlayListItem, item.Data)
        data=genericEncode(NotificationAction.ItemRemoved, data1)
        self.ItemRemovedEvent(data)

    def FireItemCancelledEvent(self, item):
        """
        :param item: PlayListItem
        :return:
        """
        data=genericEncode(NotificationAction.ItemCancelled, item.Data)
        self.ItemCancelledEvent(data)

    def FireItemAddedEvent(self, item):
        """
        :param item: PlayListItem
        :return:
        """
        data1 = genericEncode(Cmd.AddPlayListItem, item.Data)
        data=genericEncode(NotificationAction.ItemAdded, data1)
        self.ItemAddedEvent(data)

    def FireItemUpdatedEvent(self, item):
        """
        :param item: PlayListItem
        :return:
        """
        data=genericEncode(NotificationAction.ItemUpdated, item.Data)
        self.ItemUpdatedEvent(data)

    def FireSettingsChangedEvent(self, setting, value):
        self.SettingsChangedEvent(setting, value)

    def onChannelChange_Event(self, ch):
        if not self.vacationmode:
            if not self.abortOperation:
                if ch == Cmd.Stop_Player.value:
                    self.StopVideoPlayer()
                else:
                    changeChannelByChannelNumber(kodiObj,ch)

            self.abortOperation = False

    @staticmethod
    def StopVideoPlayer():
        playerStop(kodiObj)


    def onPLX_Event(self, item, doNotBackup=False, simulationOn=False):
        """
        :param simulationOn:
        :param PlayListItem item:
        :param doNotBackup:
        :return:
        """
        time.sleep(DELETE_WAIT_TIME) #Sleep 30 seconds
        recurrenceInterval=item.recurrenceInterval
        alarmtime=item.alarmtime
        DbgPrint("alarmtime: {}".format(alarmtime))
        newtime=None # type: datetime

        if recurrenceInterval==RecurrenceOptions.ONCE:
            DbgPrint("\nWating to Remove {} from list".format(item),MODULEDEBUGMODE=MODULEDEBUGMODE)
            try:
                self.Remove(item)
                DbgPrint("Item Removed from list!!!",MODULEDEBUGMODE=MODULEDEBUGMODE)
                return NotificationAction.ItemRemoved
            except Exception as e:
                raise Exception("Item has expired")
        elif recurrenceInterval==RecurrenceOptions.DAILY:
            diff=alarmtime - datetime.now()
            if diff.days > 0:
                numDays=1
            else:
                numDays = max(1,abs(diff.days))
            newtime=alarmtime + timedelta(days=numDays)
        elif recurrenceInterval == RecurrenceOptions.WEEKDAYS:
            diff = alarmtime - datetime.now()
            if diff.days > 0:
                numDays=1
            else:
                numDays = max(1,abs(diff.days))
            newtime = alarmtime + timedelta(days=numDays)
            weekday = newtime.isoweekday()
            if weekday > 5:
                newtime += timedelta(days = (8 - weekday)) #set to Monday
        elif recurrenceInterval == RecurrenceOptions.WEEKENDS:
            diff = alarmtime - datetime.now()
            if diff.days > 0:
                numDays=1
            else:
                numDays = max(1,abs(diff.days))
            newtime = alarmtime + timedelta(days=numDays)
            weekday = newtime.isoweekday()
            if weekday < 6:
                newtime += timedelta(days = (6 - weekday)) #set to Saturday
        elif recurrenceInterval == RecurrenceOptions.WEEKLY:
            diff = alarmtime - datetime.now()
            weekday1 = alarmtime.isoweekday()
            if diff.days > 0:
                numDays=7
            else:
                numDays = max(1,abs(diff.days))
            if numDays < 7:
                numDays += 7 - numDays
            else:
                numDays += 7

            newtime = alarmtime + timedelta(days=numDays)
            weekday2=newtime.isoweekday()
            if weekday1 != weekday2:
                newtime += timedelta(days = (weekday1 - weekday2)) #keep same day of week
        elif recurrenceInterval == RecurrenceOptions.MONTHLY:
            one_day = timedelta(days=1)
            one_month_later = alarmtime + one_day
            while one_month_later.month == alarmtime.month:  # advance to start of next month
                one_month_later += one_day
            target_month = one_month_later.month
            while one_month_later.day < alarmtime.day:  # advance to appropriate day
                one_month_later += one_day
                if one_month_later.month != target_month:  # gone too far
                    one_month_later -= one_day
                    break

            newtime=one_month_later

        if not simulationOn:
            #Restart item with new alarmtime
            if newtime is not None:
                item.Cancel()
                time.sleep(1)

                item.alarmtime=newtime

                if item.isExpired:
                    self.Remove(item)
                    return

                DbgPrint("newtime: {}".format(newtime))

                try:
                    item.Start()

                    if not doNotBackup:
                        self.fileManager.Dirty = True
                        self.fileManager.backup()

                    if not self.skipOperationActive:
                        data1 = genericEncode(Cmd.UpdatePlayListItem, item.Data)
                        data = genericEncode(NotificationAction.ItemUpdated, data1)
                        self.ItemUpdatedEvent(data)

                    return NotificationAction.ItemUpdated

                except Exception as e:
                    result = self.onPLX_Event( item, doNotBackup=doNotBackup, simulationOn=simulationOn)
                    return result


        else: # simulationOn == True
            DbgPrint("newtime: {}".format(newtime))
            item.alarmtime = newtime

    @staticmethod
    def CreatePlayListItem(data):
        obj=PlayListItem()
        obj.Data=data
        return obj

    def _check4conflicts(self, alarmtime, conflictList):
        for lstItem in self: # type: PlayListItem
            if lstItem.suspendedFlag:
                continue

            diff = abs(alarmtime - lstItem.alarmtime)
            if diff.days == 0 and 0 <= diff.seconds <= 30:
                conflictList.append(lstItem)

        return conflictList

    def identifyConflicts(self,item):
        """

        :param PlayListItem item:
        :return: list
        """
        originalalarmtime=alarmtime=item.alarmtime
        conflictList=[]
        DbgPrint("***newItem b4 Conflict Check:{}".format(item))
        if item.recurrenceInterval != RecurrenceOptions.ONCE:
            conflictList = self._check4conflicts(alarmtime, conflictList)
            self.SkipEvent(item, doNotBackup=True, simulationOn=True)
            alarmtime = item.alarmtime

        conflictList = self._check4conflicts(alarmtime, conflictList)

        if item.recurrenceInterval != RecurrenceOptions.ONCE:
            item.alarmtime = originalalarmtime

        DbgPrint("***newItem after Conflict Check:{}".format(item))

        return conflictList

    def isItemInList(self, item):
        chList = self.FindCh(item.ch)
        if len(chList) == 0:
            return False

        for chItem in chList:
            if chItem == item:
                return True

        return False

    def _addPlayList(self, item, doNotStartFlag=False):
        if item.PreRollTime != self.PreRollTime: # type: PlayListItem
            item.PreRollTime = self.PreRollTime

        if self.IndexByID(item.ID) >= 0:
            item.createNewID()

        self.append(item)
        item.AddPLX_EventHandler(self.onPLX_Event)
        item.AddChChangeEventHandler(self.onChannelChange_Event)
        self.FireItemAddedEvent(item)
        if not doNotStartFlag:
            item.Start()
            self.fileManager.Dirty = True
            self.fileManager.backup()

    def AddPlayList(self, item):
        if self.vacationmode:
            raise DataSetError(OpStatus.VacationModeActive, "Vacation Mode Active")

        if not isPlayListItem(item):
            raise TypeError("Item {} is not a PlayListItem".format(item))

        conflicts=self.identifyConflicts(item)
        if len(conflicts)> 0:
            raise ItemConflictError(item,conflicts)

        if not self.isItemInList(item):
            if item.isStale():
                try:
                    self.onPLX_Event(item,doNotBackup=True)
                    if not self.isItemInList(item):
                        self._addPlayList(item,doNotStartFlag=True)
                        self.fileManager.Dirty = True
                        self.fileManager.backup()
                except Exception as e:
                    raise DataSetError(OpStatus.InvalidAlarmTimeError,str(e) + ":{}".format(item))
            else:
                self._addPlayList(item)
        else:
            DbgPrint("ERROR: {} is already in the database".format(item),MODULEDEBUGMODE=MODULEDEBUGMODE)
            raise DataSetError(OpStatus.DuplicateItemError,"{} is already in the database".format(item))


    def updatePlayListItem(self,obj):
        """
        :type obj: PlayListItem
        :return:
        """
        if not isPlayListItem(obj):
            return

        item=self.SearchByID(obj.id)
        if item is not None:
            item.Cancel()
            item.Data=obj.Data
            item.Start()
            self.fileManager.Dirty = True
            self.fileManager.backup()
            self.FireItemUpdatedEvent(item)
        else:
            raise DataSetError(OpStatus.ItemUpdateFailed,str(OpStatus.ItemDoesNotExist))


    def GetPlayListItemByID(self, id):
        for item in self:
            if item.id == id:
                return item


    def GetPlayListItemsByCh(self, ch):
        chList=[]
        for item in self:
            if item.ch == ch:
                chList.append(item)

        return chList

    def _verifyNotification(self, item, status):
        if status == NotificationAction.ItemUpdated:
            data1 = genericEncode(Cmd.UpdatePlayListItem, item.Data)
            data = genericEncode(NotificationAction.ItemUpdated, data1)
            self.ItemUpdatedEvent(data)
        elif status == NotificationAction.ItemRemoved:
            data1 = genericEncode(Cmd.RemovePlayListItem, item.Data)
            data = genericEncode(NotificationAction.ItemRemoved, data1)
            self.ItemRemovedEvent(data)

    def verifyDataset(self):
        DbgPrint("Veryfying Database...")
        today = datetime.today().date()
        for item in self:  # type: PlayListItem
            if not item.isAlarmtimeLegal():
                status = self.SkipEvent(item)
                self._verifyNotification(item, status)
            try:
                if today == item.Alarmtime.date() and item.Ch != Cmd.Stop_Player.value and self.autocleanmode:
                    DbgPrint("Updating item:{}:{}:ch {}".format(item.Title, item.Alarmtime, item.Ch))
                    startTimes = getBroadcast_startTimeList(kodiObj, item.Ch, item.Title)
                    # Normally if we don't find the event in the EPG, we'll just skip the event to the next occurrence
                    if not item.Alarmtime in startTimes and len(startTimes) >= 0:
                        DbgPrint("Fixing {} on ch {}".format(item.Title,item.Ch))
                        status = self.SkipEvent(item)
                        self._verifyNotification(item, status)
                        # If this has been a time resheduled event on the same day, then schedule a one time event
                        #   for the show with the rescheduled time
                        if len(startTimes) > 0 and startTimes[0].date() == datetime.today().date():
                            tmp = copy(item)
                            tmp.createNewID()
                            tmp.alarmtime = startTimes[0]
                            tmp.recurrenceInterval=RecurrenceOptions.ONCE
                            self.AddPlayList(tmp)
            except Exception as e:
                DbgPrint(e)

    def GetPlayList(self):
        plList=[]
        for item in self:
            plList.append(item)

        return plList

    def SkipEventByID(self, id):
        item=self.SearchByID(id)
        if item is not None:
            self.SkipEvent(item)
            return item
        else:
            raise Exception("SkipEvent Failure: Invalid objID")


    def SkipEvent(self, item, doNotBackup=False, simulationOn=False):
        if not isPlayListItem(item):
            raise TypeError("Item is not a PlayListItem")

        self.skipOperationActive = True
        status = self.onPLX_Event(item, doNotBackup=doNotBackup, simulationOn=simulationOn)
        self.skipOperationActive = False

        return status


    def RemoveByID(self, id):
        item=self.SearchByID(id)
        if item is not None:
            self.Remove(item)


    def Remove(self, item):
        """
        :type item: PlayListItem
        """
        if not isPlayListItem(item):
            raise TypeError("Item is not a PlayListItem")

        try:
            item.Cancel()
            self.remove(item)
            self.FireItemRemovedEvent(item)
            self.fileManager.Dirty = True
            self.fileManager.backup()
        except Exception as e:
            DbgPrint(e)
            raise Exception("Problem deleting {}".format(item))


    def clear(self):
        #Clear the list
        del self[:]

    def RemoveAll(self):
        #Cmd.RemoveAllPlayListItems
        for item in self:
            item.Cancel()
            self.Remove(item)
            
        self.clear()


    def FindCh(self, key):
        result = []
        for item in self:
            if item.ch == key:
                result.append(item)

        return result

    def IndexByID(self, id):
        for index,item in enumerate(self):
            if item.ID == id:
                return index

        return -1

    def SearchByID(self, id):
        """
        :rtype: PlayListItem
        """
        for item in self:
            if item.ID == id:
                return item

        return None

    def Start(self):
        if self.vacationmode:
            DbgPrint("Cannot Start Playlist Items: Vacation Mode is Active",MODULEDEBUGMODE=MODULEDEBUGMODE)
            return

        flag=False
        for item in self: # type: PlayListItem
            item.Start()
            flag=True

        if not flag:
            DbgPrint("NOthing to Start!!",MODULEDEBUGMODE=MODULEDEBUGMODE)


    def CancelAll(self, notify=True):
        self.StopAllPlaylistItems(notify=notify)


    def Cancel(self, index, notify=True):
        if index < 0 or index >= len(self):
            raise ValueError("Invalid Index")

        item=self[index]
        item.Cancel(notify=notify)
        # self.fileManager.backup()

    def StopAllPlaylistItems(self, notify=True):
        for item in self:
            item.Cancel(notify=notify)


    def Shutdown(self):
        if len(self) > 0:
            item = self[0]
            if item.t is not None:
                alarmsMgr = item.t.parent # type: _Alarms
                alarmsMgr.shutdown()


    #=================JSON=======================
    """
        JSON Example
        xx=json.dumps(obj)
        obj2=json.loads(xx)
    """

    @property
    def Data(self):
        tmp = [("LTVPL"+str(key),value.Data) for key,value in enumerate(self)]
        tmp = dict(tmp)
        tmp.update({"vacationmode":self.vacationmode})
        tmp.update({"lastChNumber":self.lastChannel})
        return tmp

    @Data.setter
    def Data(self, items):
        vacationmode = False
        try:
            vacationmode = items['vacationmode']
            del items['vacationmode']
            self.lastChannel = items['lastChNumber']
            del items['lastChNumber']
        except Exception as e:
            DbgPrint(e)

        for v in items.values():
            item=self.CreatePlayListItem(v)
            if not item.isStale():
                self._addPlayList(item)
            elif item.recurrenceInterval != RecurrenceOptions.ONCE:
                self._addPlayList(item, doNotStartFlag=True)
                self.onPLX_Event(item)

        if vacationmode:
            self.VacationMode = True


class ItemConflictError(Exception):
    def __init__(self, item, cList):
        """

        :param PlayListItem item:
        :param list[PlayListItem] cList:
        """
        self.message="Error: item conflicts with Ch{}-{}".format(item.ch, item.Title)
        self.conflictList=cList
        conflictItem = cList[0] # type: PlayListItem
        self.item=item # type: PlayListItem
        self.errdata=encodeError(OpStatus.DuplicateItemError,"Ch{}-{}".format(conflictItem.ch, conflictItem.Title))

    def __repr__(self):
        return str("{}->{}".format(self.message,self.item))


class DataSetError(Exception):
    def __init__(self,opstatus,errmsg):
        self.message=errmsg
        self.errdata=encodeError(opstatus,errmsg)

    def __repr__(self):
        return str("{}->{}".format(self.message,self.errdata))



