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
from datetime import datetime
from threading import Event as Signal
from time import sleep

from resources.lib.Data.PlayListItem import PlayListItem, RecurrenceOptions
from resources.lib.Network.ClientServer import Client
from resources.lib.Network.utilities import encodeRequest, decodeResponse, Utilities, decodeErrorResponse, \
    decodeError, decodeNotification, decodeRequest, genericDecode, genericEncode
from resources.lib.Utilities.Messaging import Cmd, MsgType, OpStatus, NotificationAction
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Utilities.PythonEvent import Event
from resources.lib.Network.SecretSauce import *

__Version__ = "1.0.0"

MODULEDEBUGMODE=False
util=Utilities()

class PL_Client(object):
    def __init__(self, address):
        self.c=None
        self.signal=None
        self.currentResult=None
        self.DataReceivedEvent = Event("DataReceivedEvent", spawn=True)
        self.ErrorReceivedEvent = Event("ErrorReceivedEvent", spawn=True)
        self.NotificationReceivedEvent = Event("NotificationReceivedEvent", spawn=True)
        self.MessageReceivedEvent = Event("MessageReceivedEvent", spawn=True)
        self.RemoteDSEvent = Event("RemoteDSEvent", spawn=True)


        try:
            self.c=Client(address, self.commDataHandler)
            self.c.start()
        except Exception as e:
            print(e)
            raise Exception(str(e))
            #exit(-1)

    def closeConnection(self):
        self.c.closeConnection()

    def stopClient(self):
        self.c.closeConnection()

    def addDataReceivedEventHandler(self, handler):
        self.DataReceivedEvent.AddHandler(handler)

    def addErrorReceivedEventHandler(self, handler):
        self.ErrorReceivedEvent.AddHandler(handler)

    def addNotificationReceivedEventHandler(self, handler):
        self.NotificationReceivedEvent.AddHandler(handler)

    def addMessageReceivedEventHandler(self, handler):
        self.MessageReceivedEvent.AddHandler(handler)

    def fireDataReceivedEvent(self,cmd, data):
        self.DataReceivedEvent(cmd, data)

    def fireErrorReceivedEvent(self, opstatus, errMsg):
        self.ErrorReceivedEvent(opstatus, errMsg)

    def fireNotificationReceivedEvent(self, msg):
        self.NotificationReceivedEvent(msg)

    def fireMessageReceivedEvent(self, msg):
        self.MessageReceivedEvent(msg)

    def AddRemoteDSEventHandler(self,handler):
        self.RemoteDSEvent.AddHandler(handler)

    def onDataReceived(self,cmd, data):
        try:
            DbgPrint(data,MODULEDEBUGMODE=MODULEDEBUGMODE)

            if cmd == MsgType.Error:
                self.fireErrorReceivedEvent(cmd,data)
            else:
                self.fireDataReceivedEvent(cmd,data)
                self.RemoteDSEvent(cmd,data)
        except:
            pass



    def onMessageReceived(self,msg):
        DbgPrint("Message Received by Client: {}".format(msg),MODULEDEBUGMODE=MODULEDEBUGMODE)
        self.fireMessageReceivedEvent(msg)

    def onNotificationReceived(self, msg):
        DbgPrint("Notification Received by Client: {}".format(msg),MODULEDEBUGMODE=True)
        self.fireNotificationReceivedEvent(msg)


    def commDataHandler(self,data, pData):
        if pData is not None:

            try:
                cmd, rData = decodeResponse(pData)
                self.onDataReceived(cmd, rData)
            except:
                try:
                    cmd, rData = decodeRequest(pData)
                    if cmd in Cmd:
                        self.onDataReceived(cmd, rData)
                    else:
                        DbgPrint("ERROR:Unknown Data Type Received:{}".format((cmd,rData)))
                        raise Exception("Unknown Data Type Received")
                except:
                    try:
                        notice = decodeNotification(pData)
                        self.onNotificationReceived(notice)
                    except:
                        try:
                            cmd,errMsg = decodeErrorResponse(pData)
                            if cmd in OpStatus:
                                DbgPrint("ERROR:{}:{}".format(cmd,errMsg))
                                self.fireErrorReceivedEvent(cmd, errMsg)

                        except:
                            self.onDataReceived(cmd, pData)

        else:  # Assuming str type
            if len(data) > 0:
                DbgPrint("Data is a Message")
                self.onMessageReceived(data)


    def sendRequest(self, request):
        sleep(1.0)
        self.c.Send(request)


    def UpdatePlayListObj(self,obj):
        """
        :type obj: PlayListItem
        """

        request = encodeRequest(Cmd.UpdatePlayListItem, obj.Data)
        self.sendRequest(request)


    def AddPlayListObj(self, obj):
        """
        :type obj: PlayListItem
        """

        request = encodeRequest(Cmd.AddPlayListItem, obj.Data)
        self.sendRequest(request)


    def AddPlayListItem(self, alarmTime, ch, title,recurrenceInterval=RecurrenceOptions.ONCE):
        """
        :type alarmTime: datetime
        :type ch: int
        :type title: str
        :type recurrenceInterval: RecurrenceOptions
        """

        obj=PlayListItem(alarmtime=alarmTime,chID=0,ch=ch, title=title,recurrenceInterval=recurrenceInterval)

        request = encodeRequest(Cmd.AddPlayListItem, obj.Data)
        self.sendRequest(request)

    def RemovePlayListItem(self, itemID):
        """
        :type itemID: str
            PlayListItem.id
        """

        request=encodeRequest(Cmd.RemovePlayListItem,itemID)
        self.sendRequest(request)

    def SkipPlayListItem(self,itemID):
        """
        :type itemID: str
            PlayListItem.id
        """
        request = encodeRequest(Cmd.SkipEvent, itemID)
        self.sendRequest(request)


    def GetPlayListItem(self, itemID):
        """
        :type itemID: str
            PlayListItem.id
        """
        request = encodeRequest(Cmd.GetPlayListItem, itemID)
        self.sendRequest(request)

    def suspendPlayListItem(self, itemID):
        # DbgPrint("***Suspending PlayListItem: {}".format(itemID))
        request = encodeRequest(Cmd.DisablePlayListItem, itemID)
        self.sendRequest(request)

    def enablePlayListItem(self, itemID):
        request = encodeRequest(Cmd.EnablePlayListItem, itemID)
        self.sendRequest(request)

    def GetPlayList(self):
        request=encodeRequest(Cmd.GetPlayList,None)
        self.sendRequest(request)

    def GetChGroupList(self):
        request = encodeRequest(Cmd.GetChGroupList, None)
        self.sendRequest(request)

    def GetChannelList(self, chGroup):
        request = encodeRequest(Cmd.GetChannelList, chGroup)
        self.sendRequest(request)

    def Login(self):
        pass

    def Logout(self):
        pass

    def getVacationmode(self):
        request = encodeRequest(Cmd.GetVacationMode, None)
        self.sendRequest(request)

    def setVacationmode(self, value):
        request = encodeRequest(Cmd.SetVacationMode, value)
        self.sendRequest(request)

if __name__=='__main__':
    address = ('localhost', ServerPort)
    c = PL_Client(address)
    glist=c.GetChGroupList()
    sleep(10)
    c.c.ServerShutDown()
    pass
