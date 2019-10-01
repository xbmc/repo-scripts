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

import hashlib
import json
import pickle
import sys
import xml.etree.ElementTree as ET
from time import sleep
from resources.lib.Utilities.DebugPrint import DbgPrint

try:
    from datetime import datetime, timedelta
except:
    DbgPrint("Nasty, Nasty ERROR: Cannot Import datetime module")
import _strptime

# from threading import Timer
from resources.lib.Utilities.AlarmsMgr import Timer

try:
    datetime.strptime("2016", "%Y") #Workaround _strptime import error
except:
    pass

from enum import Enum
from resources.lib.Network.myPickle_io import myPickle_io
from resources.lib.Network.utilities import encodeError

from resources.lib.Utilities.PythonEvent import Event
from resources.lib.Utilities.Messaging import OpStatus
from resources.lib.Utilities import indent

__Version__ = "1.0.1"

MODULEDEBUGMODE=True
ALARMPADDING = 5

class RecurrenceOptions(Enum):
    ONCE=0 #only on the day/time specified
    DAILY=1 #at the time specified
    WEEKDAYS=2 #mon-fri at the time specified
    WEEKENDS=3 #sat-sun at the time specified
    WEEKLY=4 #Once a week on the day/time specified
    MONTHLY=5 #once a month on the day/time specified

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


def isPlayListItem(item):
    if sys.version_info[0]==2:
        return isinstance(item,PlayListItem)
    else:
        return type(item) == PlayListItem

def isStr(item):
    if sys.version_info[0]==2:
        return isinstance(item,str) or type(item) == unicode
    else:
        return type(item) == str or type(item) == unicode

class PlayListItem(myPickle_io):
    """
        PlayListItem(alarmtime=None, expryDate=None, ch=None, fp=None, eventHandler=None)
            Parameters:
                alarmtime ->Type: datetime  Represents the time when the event should fire
                expryDate -> Type: date The item expiration date
                ch -> Type: float The Channel Number, ex:10.1
                title-> Type: string The Show Title

            Events:
                ChChangeEvent:
                    Description: Change Channel Event
                    EventHandler: ChChangeEvent(ch)
                    Executes when change channel event fires

                PLX_Event:
                    Description: PlayList Executed Event
                    EventHandler: PLX_EventHandler(PlayListItem)
                    Executes when change channel event fires
    """
    ALARMPADDING = 5

    def __init__(self,alarmtime=None, expiryDate=None, ch=None,title=None, fp=None, eventHandler=None,
                 recurrenceInterval=RecurrenceOptions.ONCE, suspendedFlag=False, prerolltime=ALARMPADDING):
        myPickle_io.__init__(self)
        self.eventHandler=eventHandler
        self.recurrenceInterval=recurrenceInterval
        self.id=None
        self.t=None
        self.ChChangeEvent = Event("ChannelChangeEvent",spawn=True)
        self.PLX_Event = Event("PlayListExecutedEvent",spawn=True)
        self.prerolltime=prerolltime

        if eventHandler is not None:
            self.ChChangeEvent.AddHandler(eventHandler)
        
        if alarmtime is not None and ch is not None and title is not None:
            self.SetData(alarmtime,expiryDate, ch, title,recurrenceInterval, suspendedFlag)
        else:
            self.alarmtime=None
            self.expiryDate=None
            self.ch=None
            self.title=None
            self.recurrenceInterval=RecurrenceOptions.ONCE
            self.suspendedFlag = False

        if fp is not None:
            self.ImportPKL(fp)

            

    def AddChChangeEventHandler(self,handler):
        self.ChChangeEvent.AddHandler(handler)

    def AddPLX_EventHandler(self,handler):
        self.PLX_Event.AddHandler(handler)

    def RemoveChChangeEventHandler(self,handler):
        self.ChChangeEvent.RemoveHandler(handler)

    def RemovePLX_EventHandler(self,handler):
        self.PLX_Event.RemoveHandler(handler)

    def isAlarmWeekday(self):
        day = self.alarmtime.weekday()
        if day < 5:
            return True

        return False

    def isAlarmWeekend(self):
        day = self.alarmtime.weekday()
        if day >= 5:
            return True
        return False

    def isDateLegal(self):
        if self.recurrenceInterval == RecurrenceOptions.WEEKENDS:
            return self.isAlarmWeekend()
        elif self.recurrenceInterval == RecurrenceOptions.WEEKDAYS:
            return self.isAlarmWeekday()
        else:
            return True

    def isAlarmtimeLegal(self):
        return (self.alarmtime - datetime.now()).total_seconds() >= 0

    def calcHash(self,salt=0):
        tmp = str(self.alarmtime) + str(self.expiryDate) + str(self.expiryDate) + str(salt)
        return hashlib.md5(tmp.encode()).hexdigest()

    def reStart(self):
        count = 30
        self.Cancel()
        while self.isActive and count > 0:
            sleep(1)
            count -= 1

        self.Start()

    @property
    def Ch(self):
        return self.ch

    @property
    def Title(self):
        return self.title

    @property
    def Alarmtime(self):
        return self.alarmtime

    @property
    def SuspendedFlag(self):
        return self.suspendedFlag

    @SuspendedFlag.setter
    def SuspendedFlag(self, value):
        if value != self.suspendedFlag:
            self.suspendedFlag = value
            if value == False:
                if self.isAlarmtimeLegal():
                    self.reStart()
                else:
                    raise Exception("Invalid AlarmTime")
            else:
                self.Cancel()

    @property
    def PreRollTime(self):
        return self.prerolltime

    @PreRollTime.setter
    def PreRollTime(self,value):
        self.prerolltime = value
        self.reStart()

    @property
    def ID(self):
        """PlayList Item ID """
        return self.id
    
    def createNewID(self):
        self.id=self.calcHash()

    def SetData(self,alarmtime,expiryDate, ch, title, recurrenceInterval, suspendedFlag):
        self.alarmtime=alarmtime
        self.expiryDate=expiryDate
        self.ch=ch
        self.t=None
        self.title=title
        self.id=self.calcHash()
        self.recurrenceInterval=recurrenceInterval
        self.suspendedFlag=suspendedFlag

        

    def Start(self):
        """Activates the PlayList"""
        DbgPrint("***item thread alive: {}".format(self.isActive))
        if self.isActive:
            DbgPrint("Timer Already Active")
            return

        if self.isExpired:
            DbgPrint("Playlist alarmtime {} has expired".format(self.alarmtime))
            return

        if self.SuspendedFlag:
            DbgPrint("Playlist has been suspended")
            changeOp = self._suspendedPLX_Op
        else:
            changeOp = self._ChangeCh

        # DbgPrint("\ntype(self.alarmtime):{}".format(type(self.alarmtime)))
        if self.suspendedFlag == False:
            td= self.alarmtime - datetime.now() - timedelta(seconds=self.PreRollTime)
        else:
            td = self.alarmtime - datetime.now() - timedelta(seconds=self.PreRollTime) + timedelta(seconds=30)

        if td.days >= 0:
            self.t=Timer(td.total_seconds() + 1, changeOp, self.ch)
            self.t.start()
            #TODO: Error Log Output
        else:
            val = "Cannot Start Item: {}".format(self.Data)
            DbgPrint(val)
            raise PlayListItemError(OpStatus.InvalidAlarmTimeError, val)


    def Cancel(self, notify=True):
        """Deactivates the PlayList"""
        if self.t is not None:
            self.t.cancel()
            self.t=None
            if notify:
                DbgPrint("Cancelling PlayList Item: {}".format(self))

    def strDate2TimeStamp(self, tdata, fmt):
        import time
        ts=datetime (* (time.strptime (tdata, fmt) [0: 6]))
        return ts
    
    def _checkTimeStamp(self, tData):
        if isStr(tData):
            try:
                tData = self.strDate2TimeStamp(tData, "%Y-%m-%d %H:%M:%S.%f")
            except:
                tData = self.strDate2TimeStamp(tData, "%Y-%m-%d %H:%M:%S")

        return tData

    #===============Pickle=======================
    def __getstate__(self):
        state = myPickle_io.__getstate__(self)
        del state['t']
        return state

    def __iadd__(self, other):
        self.Data=other.__dict__



    def ToPKL(self):
        return pickle.dumps(self)

    def FromPKL(self, values):
        tmp=pickle.loads(values)
        self+=tmp


    #=================JSON=======================        
    @property
    def Data(self):
        """Gets Class Attributes Dictionary"""
        tmp={'ch':self.ch,'expiryDate':self.expiryDate, 'id':self.id, 'title':self.title,
             'recurrenceInterval':str(self.recurrenceInterval),'suspendedFlag':self.suspendedFlag}

        tmp.update({'alarmtime':str(self.alarmtime)})
        return tmp


    @Data.setter
    def Data(self, values):
        """Sets Class Attributes Dictionary"""
        if values is None:
            return
        try:
            self.__dict__.update(values)
        except Exception as e:
            raise e

        self.alarmtime = self._checkTimeStamp(self.alarmtime)
        self.expiryDate = self._checkTimeStamp(self.expiryDate)
        self.recurrenceInterval=RecurrenceOptions[self.recurrenceInterval]


    def ExportJSON(self,fp):
        json.dump(self.Data, fp)

    def ImportJSON(self,fp):
        self.Data=json.load(fp)



    #==================XML============================

    def ToXML(self):
        tree=ET.Element("PlayListItem")
        tmp = self.Data
        for k,v in tmp.items():
            e=ET.SubElement(tree,k)
            e.text=str(v)

        return indent(tree)


    def FromXML(self, xmlstr):
        xml=ET.fromstring(xmlstr)
        if xml.tag!='PlayListItem' and len(xml) != 3:
            raise TypeError("ERROR:FromXML: arg is not a valid PlayList XML")
        tmp={}
        tmp.update({xml[0].tag:xml[0].text})
        tmp.update({xml[1].tag:int(xml[1].text)})
        tmp.update({xml[2].tag:float(xml[2].text)})
        tmp.update({xml[3].tag:float(xml[3].text)})
        self.Data=tmp


    def ExportXML(self,fp):
        xmlStr=ET.tostring(self.ToXML()).decode("utf-8")
        fp.write(xmlStr)
        fp.close()

    def ImportXML(self,fp):
        data=fp.readlines()
        data=''.join(data)
        fp.close()
        self.FromXML(data)

    #=======================General Functions/Properties=================
    @property
    def isActive(self):
        try:
            return self.t.isAlive()
        except:
            return False

    @property
    def isExpired(self):
        if self.expiryDate is None:
            return False

        return self.alarmtime > self.expiryDate

    def _suspendedPLX_Op(self):
        self.PLX_Event(self)

    def _ChangeCh(self):
        DbgPrint("Changing to channel {} at {}\n".format(self.ch,datetime.now()))
        try:
            self.ChChangeEvent(self.ch)
            self.PLX_Event(self)
        except:
            pass #TODO: Raise Invalid EventHandler Error

    def isStale(self):
        if self.alarmtime < datetime.now():
            return True

        return False

    def __repr__(self):
        return "ch {} at {} : {}".format(self.ch,self.alarmtime,self.recurrenceInterval)

    def __eq__(self,other):
        if not isPlayListItem(other):
            return False
        return self.expiryDate == other.expiryDate and self.alarmtime == other.alarmtime \
               and self.ch == other.ch and self.id == other.id


    def isEqual(self, other):
        """
        :param other: PlayListItem
        :return:
        """
        if not isPlayListItem(other):
            return False
        return self.alarmtime==other.alarmtime and self.ch == other.ch

class PlayListItemError(Exception):
    def __init__(self,err, errmsg):
        self.message=errmsg
        self.errdata = encodeError(err,errmsg)

    def __repr__(self):
        return str("{}->{}".format(self.message,self.errdata))

    
