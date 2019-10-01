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
import xbmc
import xbmcgui
import xbmcaddon
from datetime import datetime, timedelta
from threading import Thread, Timer

from resources.PL_Client import PL_Client, genericDecode, OpStatus, Cmd, NotificationAction
from resources.lib.Network.SecretSauce import *
from utility import TS_decorator, myLog, Signal, setDialogActive, isDialogActive, clearDialogActive
from resources.lib.Utilities.DebugPrint import DbgPrint
from util import ADDON, ACTIVATIONKEY
from keymapper import keymapper
from ListItemPlus import ListItemPlus
from util import GETTEXT

__Version__ = "1.0.0"

def IdCmd(obj):
    return id(obj)

LTVPL = 'Live TV Playlist'
VACATIONMODE_VALUE = False
try:
    VACATIONMODE_VALUE = ADDON.getSetting('vacationmode') == 'true'
except: pass

ACTION_BACK = 92
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_CONTEXT_MENU = 117

CANCEL_BUTTON = 900


COUNTDOWNTAG = "LTVPL_COUNTDOWNDIALOG_VISIBLE"
MINICLIENTTAG = "LTVPL_MINCLIENTDIALOG_VISIBLE"


class Countdown(xbmcgui.WindowXMLDialog):

    def __new__(cls, addonID, client=None, listitem=None, clockstarttime=15, abortChChange=None):
        return super(Countdown, cls).__new__(cls, 'countdownDialog.xml', xbmcaddon.Addon(addonID).getAddonInfo('path'))

    def __init__(self, addonID, client=None, listitem=None, clockstarttime=15, abortChChange=None):
        super(Countdown, self).__init__()
        xbmc.log("*****Countdown.Init()")
        self.t = None
        self.client = client
        self.listitem = listitem
        if abortChChange is None:
            self.ServerAbortChannelChangeEvent = self.noop
        else:
            self.ServerAbortChannelChangeEvent = abortChChange

        if self.listitem is not None:
            #Next
            self.setProperty('pgmData', GETTEXT(30071).format(self.listitem.getProperty('pgmCh'),self.listitem.getProperty('pgmTitle')))
            self.pgmId = self.listitem.getProperty('pgmId')

        else:
            self.setProperty('pgmData', 'Next: ch 6.1 *Now is the time for all good men!!!')

        self.clockStartTime = clockstarttime
        setDialogActive(COUNTDOWNTAG)


    @TS_decorator
    def doCountDown(self):
        count = self.clockStartTime

        while count > 0:
            self.setProperty('Time', ":{:02d}".format(count))
            count = count - 1
            xbmc.sleep(1000)

        self.closeDialog()

    def onInit(self):
        self.setProperty('maintitle', GETTEXT(30070))
        self.setProperty('cancel', GETTEXT(30046))
        self.doCountDown()

    def closeDialog(self):
        self.close()
        xbmc.sleep(100)


    def noop(self):
        pass

    def abortPlayListEvent(self, id):
        if self.client is not None:
            self.ServerAbortChannelChangeEvent()
            #self.client.SkipPlayListItem(id)

    def onClick(self, controlId):
        if controlId == CANCEL_BUTTON:
            self.abortPlayListEvent(self.pgmId)
            self.closeDialog()

    def onAction(self, action):
        actionId = action.getId()

        if actionId in [ACTION_CONTEXT_MENU, ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_BACK]:
            return self.closeDialog()


class miniClient(Thread):
    def __init__(self, addonID, clockstarttime, abortChChange=None):
        super(miniClient, self).__init__(name="LTVPL_miniClient")
        self.addonID = addonID
        self.clockStartTime = clockstarttime
        self.abortChChange = abortChChange
        self.t = None
        self.stopFlag = False
        self.client = None
        self.signal = Signal()
        self.signal.clear()
        self.currentLaunchItem = None
        self.plList = []
        #Get Activation key from gen.xml
        key = keymapper.getCurrentActivationKey()
        if key is not None:
            ADDON.setSetting(ACTIVATIONKEY, key)

        setDialogActive(MINICLIENTTAG)

    @property
    def CountDownDuration(self):
        return self.clockStartTime

    @CountDownDuration.setter
    def CountDownDuration(self, value):
        if value != self.clockStartTime:
            self.clockStartTime = value
            #Restart Thread
            currentLaunchItem = self.currentLaunchItem
            self.killThread()
            self.Launch(currentLaunchItem)

    # @TS_decorator
    def connectToServer(self):
        address = (ServerHost, ServerPort)
        try:
            self.client = PL_Client(address)
            self.client.addErrorReceivedEventHandler(self.onErrorNotification)
            self.client.addDataReceivedEventHandler(self.onResponseReceived)
            self.client.addNotificationReceivedEventHandler(self.onNotificationReceived)
        except:
            pass

    def onErrorNotification(self, opstatus, errMsg):
        xbmc.log("*****onErrorNotification {}:{}".format(opstatus, errMsg))
        if opstatus.value >= 30000:
            xbmcgui.Dialog().notification(LTVPL, "{}:\n{}".format(str(opstatus), GETTEXT(opstatus.value)), icon=xbmcgui.NOTIFICATION_ERROR)
        else:
            xbmcgui.Dialog().notification("Live TV Playlist Error", "{}:\n{}".format(str(opstatus), errMsg), icon=xbmcgui.NOTIFICATION_ERROR)

    def onResponseReceived(self, cmd, data):
        DbgPrint("**DataResponse Received: {}".format(data))
        # self.blockNotification = True
        if cmd == Cmd.GetChannelList:
            pass

        elif cmd == Cmd.GetPlayList:
            dataSetData = data
            try:
                dataSetData['vacationmode']
                del dataSetData['vacationmode']
            except Exception as e:
                pass

            for key in dataSetData:
                myLog("**Data: {}".format(dataSetData[key]))
                data = dataSetData[key]
                self.plList.append(data)

            self.sortData()
            self.signal.set()

        elif cmd == Cmd.AddPlayListItem:
            myLog("********onResponseReceived.addPlayListItem: {}".format(data))
            self.plList.append(data)
            self.sortData()

        elif cmd == Cmd.UpdatePlayListItem or cmd == Cmd.SkipEvent:
            myLog("********onResponseReceived.UpdatePlayListItem: {}".format(data))
            try:
                id = data['id']
                n = self.searchByID(id)
                self.plList[n] = data
                self.sortData()
            except:
                pass

        elif cmd == Cmd.RemovePlayListItem:
            DbgPrint("********onResponseReceived.RemovePlayListItem: {}".format(data))
            try:
                id = data['id']
                n = self.searchByID(id)
                del self.plList[n]
                self.sortData()
            except:
                pass

        elif cmd == Cmd.GetChGroupList:
            pass

        elif cmd == Cmd.GetVacationMode:
            DbgPrint("***setting vacation mode: {}".format(data))
            ADDON.setSetting('vacationmode', str(data).lower())
            self.sortData()

    def onNotificationReceived(self, msg):
        """
        Decode the notification message and perform the appropriate function.
        Decoded Functions:
            1. ItemAdded
            2. ItemCancelled
            3. ItemUpdated
            4. ItemRemoved
            5. VacationMode
        The purpose of this function is to update the GUI display based on feedback from the server
        :param msg: Notification String
        :return:
        """
        global VACATIONMODE_VALUE

        DbgPrint("***Notification: {}".format(msg))
        try:
            cmd, data = genericDecode(msg)
            DbgPrint("****cmd:{}\tdata:{}\n".format(cmd, data))
            if cmd == NotificationAction.ItemRemoved:
                cmd, data = genericDecode(data)
                try:
                    id = data['id']
                except:
                    id = data

                try:
                    DbgPrint("****self.removeItemByID({})".format(id))
                    n = self.searchByID(id)
                    DbgPrint("*****Preparing to delete item at index: {}".format(n))
                    del self.plList[n]
                    DbgPrint("*****Successfully deleted item at index: {}".format(n))
                    self.sortData()

                except Exception as e:
                    DbgPrint("Exception in Notification: {}".format(str(e)))

            elif cmd == NotificationAction.ItemAdded:
                cmd, data = genericDecode(data)
                DbgPrint("****Notification.addNewItem({})".format(data))
                self.plList.append(data)
                self.sortData()

            elif cmd == NotificationAction.ItemUpdated:
                try:
                    cmd, data = genericDecode(data)
                    id = data['id']
                    DbgPrint("****self.updateItemByID({},{})".format(id, data))
                    n = self.searchByID(id)
                    self.plList[n] = data
                    self.sortData()
                except:
                    pass

            elif cmd == NotificationAction.VacationMode:
                # cmd, data = genericDecode(data)
                try:
                    DbgPrint("Setting VacationMode: {}".format(data))
                    try:
                        VACATIONMODE_VALUE = data['SetVacationMode']
                    except:
                        VACATIONMODE_VALUE = data

                    if VACATIONMODE_VALUE == True:
                        if self.t is not None:
                            self.t.cancel()
                            self.t = None
                    else:
                        self.sortData()
                except Exception as e:
                    DbgPrint(str(e))

        except:
            pass

    def BuildListItem(self):
        DbgPrint("len(plList): {}".format(len(self.plList)))
        item = xbmcgui.ListItem()
        try:
            # return the first non-suspended item
            for data in self.plList:
                if data['suspendedFlag'] == False:
                    DbgPrint("****BuildListItem data: {}".format(data))
                    try:
                        item.setProperty('pgmCh', "{}".format(data['ch']))
                    except:
                        item.setProperty('pgmCh', "{:2.1f}".format(float(data['ch'])))

                    item.setProperty('pgmTitle', data['title'])
                    item.setProperty('pgmAlarmtime', data['alarmtime'])
                    item.setProperty('pgmId', data['id'])
                    DbgPrint("***Returning item: {}".format(data['title']))
                    return item
        except Exception as e:
            pass

    def killThread(self):
        count = 10
        if self.t is not None:
            DbgPrint("***Cancelling Current Launch Item: {}".format(self.currentLaunchItem.getProperty('pgmTitle')))
            while self.t.isAlive() and count > 0:
                self.t.cancel()
                xbmc.sleep(600)
                count -= 1
            DbgPrint("***Countdown Thread Killed - count{}".format(count))
            self.t = None
            self.currentLaunchItem = None

    def Launch(self, listitem):
        global VACATIONMODE_VALUE
        if listitem is None:
            return

        if VACATIONMODE_VALUE == True:
            DbgPrint("**Vacation Mode Active...")
            return

        self.killThread()

        preroll_time = int(ADDON.getSetting('preroll_time'))
        alarmtime = self.strDate2TimeStamp(listitem.getProperty('pgmAlarmtime'))
        td = alarmtime - datetime.now() - timedelta(seconds=self.clockStartTime + 2)
        if td.days >= 0:
            DbgPrint("****td: {}\t{}".format(td, listitem.getProperty('pgmTitle')))
            self.currentLaunchItem = listitem
            self.t = Timer(td.total_seconds() - preroll_time, self.launchCountDown, [listitem])
            self.t.name = "Thread-CountdownLaunch"
            self.t.start()

    imap={True:'*', False:''}

    def sortData(self):
        global VACATIONMODE_VALUE
        if VACATIONMODE_VALUE == True:
            DbgPrint("**Vacation Mode Active...")
            return

        DbgPrint("******miniClient sortData Called...")
        self.plList.sort(key=lambda item: str(int(item['suspendedFlag'])) + item['alarmtime'])

        for n, d in enumerate(self.plList):
            myLog("******{}:({}){}".format(n, d['alarmtime'], self.imap[d['suspendedFlag']] +  d['title']))

        self.signal.set()

    def searchByID(self, id):
        try:
            DbgPrint("********len(self.plList): {}".format(len(self.plList)))
            for n, item in enumerate(self.plList):
                DbgPrint("*******searchByID item:{}".format(item))
                itemID = item['id']
                DbgPrint("****itemID: {}\n****itemID == id: {}".format(itemID, itemID == id))
                if itemID == id:
                    DbgPrint("****SearchByID returning n: {}".format(n))
                    return n
        except Exception as e:
            DbgPrint("****SearchByID Unexpected Error:{}: n={} : item={}".format(str(e), n, item))

        DbgPrint("SearchByID: Should only get here if there is an ERROR....")
        raise Exception("Item Not Found")

    def closeConnection(self):
        if self.client is not None:
            self.client.closeConnection()

    def run(self):
        from time import sleep
        count = 10
        while count > 0:
            self.connectToServer()
            if self.client is not None:
                DbgPrint("****Calling GetVactionMode")
                self.client.getVacationmode()
                sleep(1)
                DbgPrint("****Calling GetPlayList")
                self.signal.clear()
                self.client.GetPlayList()  # type: PL_Client
                break
            count = count - 1
            xbmc.sleep(1000)

        if self.client is None:
            msg = "****miniClient Could not connect to Server...cnt: {}".format(count)
            raise Exception(msg)

        xbmcgui.Dialog().notification(LTVPL, GETTEXT(30063)) #"miniClient Service Started..."
        DbgPrint("***Banner:{}".format(GETTEXT(30063)))
        if len(self.plList) > 0:
            self.signal.set()

        while True:
            DbgPrint("****miniClient Waiting...")
            self.signal.wait()
            DbgPrint("*****miniClient Run Launching Coundown....")
            if not self.stopFlag:
                listitem = self.BuildListItem()
                if listitem is not None:
                    self.Launch(listitem)
                else:
                    self.killThread()

                self.signal.clear()
            else:
                break
        myLog("*****miniClient Exiting Run...")
        self.Stop()

    def Stop(self):
        DbgPrint("*********miniClient Shutdown Started.....")
        self.stopFlag = True
        if self.t is not None:
            self.t.cancel()
        xbmc.sleep(100)
        self.closeConnection()
        DbgPrint("*********miniClient Stopped.....")

    def launchCountDown(self, listitem):
        DbgPrint("*******Launching Countdown...")
        if not isDialogActive(COUNTDOWNTAG):
            ui = Countdown(self.addonID, self.client, listitem, self.clockStartTime, self.abortChChange)
            ui.doModal()
            clearDialogActive(COUNTDOWNTAG)
            del ui

    def strDate2TimeStamp(self, tdata):
        fmt = "%Y-%m-%d %H:%M:%S"
        import time
        ts = datetime(*(time.strptime(tdata, fmt)[0: 6]))
        return ts


def launchCountDown(addonID, listitem, clockstarttime):
    DbgPrint("*******Launching Countdown...")
    ui = Countdown(addonID, listitem, clockstarttime)
    ui.doModal()
    del ui


# @TS_decorator
def StartCountdownService(addonID, clockstarttime=15, abortChChange=None):
    if not isDialogActive(MINICLIENTTAG):
        mc = miniClient(addonID, clockstarttime, abortChChange)
        xbmc.sleep(500)
        mc.start()
        clearDialogActive(MINICLIENTTAG)
        return mc

    raise Exception("miniClient Already Active")

