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

import os, sys
from threading import Event as Signal, Thread
from datetime import datetime as dt, timedelta
import locale
import copy
import sys

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

import xbmc
import xbmcaddon
import xbmcgui

from util import ADDON, ADDONID, ADDON_PATH, ADDON_NAME, XMLPATH, FANART_PATH, BGDIMAGE, LTVPL_HEADER, GETTEXT, setUSpgmDate, getRegionDatetimeFmt
from resources.lib.Data.PlayListItem import PlayListItem
from resources.PL_Client import PL_Client, genericDecode
from resources.lib.Utilities.Messaging import Cmd, NotificationAction,DEBUGMODE,TRUE,VACATIONMODE
from resources.lib.Network.SecretSauce import *
from utility import myLog, TS_decorator, setDialogActive, clearDialogActive, isDialogActive
from resources.lib.Utilities.DebugPrint import DbgPrint, DEBUGMODE, setDebugMode, getDebugMode
import contextmenu
from ListItemPlus import ListItemPlus
from keymapper import setActivationKey, reloadKeyMaps
from BusyDialog import BusyDialog, BusyDialog2

__Version__ = "1.1.1"

MAIN_DIALOGTAG = "LTVPL_MAINDIALOG_VISIBLE"
MODULEDEBUGMODE = True
VACATIONMODE_VALUE = False
try:
    MODULEDEBUGMODE = ADDON.getSetting(DEBUGMODE) == TRUE
    VACATIONMODE_VALUE = ADDON.getSetting(VACATIONMODE) == TRUE
except: pass

RECURRENCE_OPTIONS = [(GETTEXT(30050),'Once'), (GETTEXT(30051),'Daily'), (GETTEXT(30052),'Weekdays'), (GETTEXT(30053),'Weekends'), (GETTEXT(30054),'Weekly'), (GETTEXT(30055),'Monthly')]

YELLOW              =   'FFBBBB00'
ORANGE              =   'FFBB6600'
ITEM_BGDCOLOR       =   '33FF00FF'
HDR_BGDCOLOR        =   'FFAA0000'
LTVPL               =   'Live TV Playlist'

#Control IDs
PAGE_SIZE                   = 10
CLOSE_BUTTON                = 20
SCROLL_BAR                  = 17
MAIN_LIST                   = 800

ACTION_MOVE_LEFT            = 1
ACTION_MOVE_RIGHT           = 2
ACTION_MOVE_UP              = 3
ACTION_MOVE_DOWN            = 4
ACTION_PAGE_UP              = 5
ACTION_PAGE_DOWN            = 6
ACTION_SELECT_ITEM          = 7
ACTION_PREVIOUS_MENU        = 10
ACTION_NAV_BACK             = 92
ACTION_CONTEXT_MENU         = 117
ACTION_MOUSE_LEFT_CLICK     = 100
ACTION_MOUSE_RIGHT_CLICK    = 101

JUSTIFY_LEFT                = 0
JUSTIFY_CENTER              = 2
JUSTIFY_RIGHT               = 1

MENU_DELETE_ITEM            = 0
MENU_SKIP_ITEM              = 1
MENU_SUSPEND_ITEM           = 2
MENU_EDIT_ITEM              = 3

WINDOW_TV_GUIDE             = 10702

BUSYDIALOG_SLEEPTIME        = 330 #time in miliseconds
BUSYDIALOG_TIMEOUT          = 3 #time in seconds

HDR_FORMAT = [(GETTEXT(30030), 100, JUSTIFY_CENTER, 'Date'), (GETTEXT(30031), 100, JUSTIFY_CENTER, 'Time'),
              (GETTEXT(30032), 100, JUSTIFY_CENTER, 'Ch'), (GETTEXT(30033), 120, JUSTIFY_CENTER, 'Frequency'),
              (GETTEXT(30034), 200, JUSTIFY_LEFT, 'Description'), (GETTEXT(30035), 120, JUSTIFY_CENTER, 'Expires On'),
              (GETTEXT(30036), 100, JUSTIFY_CENTER, 'suspendedFlag')]

HDR_FORMAT_EXTENDED = HDR_FORMAT +[('alarmtime',0,0,'alarmtime')]

ContextMenuItems  = [(GETTEXT(30020), MENU_SKIP_ITEM, 'Skip Event'), (GETTEXT(30021), MENU_SUSPEND_ITEM, 'Suspend Event'),
                     (GETTEXT(30022), MENU_EDIT_ITEM, 'Edit Event'), (GETTEXT(30023), MENU_DELETE_ITEM, 'Delete Event')]
ContextMenuItems2 = [(GETTEXT(30020), MENU_SKIP_ITEM, 'Skip Event'), (GETTEXT(30024), MENU_SUSPEND_ITEM, 'Enable Event'),
                     (GETTEXT(30022), MENU_EDIT_ITEM, 'Edit Event'), (GETTEXT(30023), MENU_DELETE_ITEM, 'Delete Event')]


locale.setlocale(locale.LC_ALL, '')
myLog("addonname: {}".format(ADDON_NAME))
myLog("addonID: {}".format(ADDONID))
myLog("xmlpath: {}".format(XMLPATH))
myLog("addonpath: {}".format(ADDON_PATH))
myLog("bgdimage: {}".format(BGDIMAGE))


class myBusyDialog(object):
    def __init__(self, startPct = 0):
        self.stopFlag = False
        self.dialog = BusyDialog2(ADDONID)
        self.percent = startPct
        self.maxcount = BUSYDIALOG_TIMEOUT * 1000 / BUSYDIALOG_SLEEPTIME

    @TS_decorator
    def show(self):
        count = 0
        percent = self.percent
        self.dialog.show()
        DbgPrint("***Busy Dialog Show")

        while not self.stopFlag and count < self.maxcount and not self.dialog.iscanceled():
            self.dialog.update(percent)
            self.percent = percent = (percent + 5) % 100
            count += 1
            xbmc.sleep(BUSYDIALOG_SLEEPTIME)

            DbgPrint("***Busy Dialog Close")
        self.dialog.close()

    def getPercent(self):
        return self.percent

    @TS_decorator
    def DelayedStop(self, delay):
        totalMS = delay * 1000
        xbmc.sleep(totalMS)
        self.stopFlag = True
        DbgPrint("****{} Second Delayed Busy Dialog Closing".format(delay))

    def Stop(self, delay=0):
        DbgPrint("******Dialog Stop Delay = {}".format(delay))
        if delay == 0:
            self.stopFlag = True
            DbgPrint("****Busy Dialog Closing")
        else:
            self.DelayedStop(delay)


def strTimeStamp(tData):
    """
    :type alarmtime: datetime
    :return: tuple(strDate, strTime)
    """
    # TODO customize date per regional value
    try:
        dateformat = "{:" + getRegionDatetimeFmt() + "}"
        strDate = dateformat.format(tData)
        strTime = "{:%I:%M %p}".format(tData)
    except:
        strDate = strTime = ''

    return (strDate, strTime)

def _germanAM_PM_Fix(data):
    pos = data.lower().find('vormittags')
    if pos > 0:
        data = data[:pos] + 'AM'
    else:
        pos = data.lower().find('nachmittags')
        if pos > 0:
            data = data[:pos] + 'PM'

    return data


def getEPG_Data(win=None):
    dateformat = getRegionDatetimeFmt()
    DbgPrint("***DateFormat: {}". format(dateformat))

    pgmTitle = xbmc.getInfoLabel('Listitem.Title')
    DbgPrint("***pgmTitle: {}".format(pgmTitle))
    fullPgmDate = xbmc.getInfoLabel('Listitem.Date')
    DbgPrint("***fullPgmDate: {}".format(fullPgmDate))
    pgmDate = copy.copy(fullPgmDate)
    pos=pgmDate.find(' ')
    if pos > 0:
        pgmDate = pgmDate[:pos]
    DbgPrint("***pgmDate: {}".format(pgmDate))
    pgmTime = xbmc.getInfoLabel('Listitem.StartTime')
    pgmCh = xbmc.getInfoLabel('Listitem.ChannelNumberLabel')
    pgmIcon = xbmc.getInfoLabel('Listitem.Icon')
    DbgPrint("Locale: {}".format(locale.getlocale()))
    DbgPrint("Default Locale: {}".format(locale.getdefaultlocale()))

    #Initially try a 12 hour clock
    try:
        liDateTime = dt.strptime(fullPgmDate, dateformat)
    except Exception as e:
        DbgPrint("Error Msg: {}".format(str(e)))

        fullPgmDate = _germanAM_PM_Fix(fullPgmDate)

        if os.name == 'nt':
            dateformat = dateformat.replace('%#', '%')
        else:
            dateformat = dateformat.replace('%-', '%')
        DbgPrint("new DateFormat: {}".format(dateformat))
        myLog("Listitem.Date: {}".format(pgmDate))
        try:
            liDateTime = dt.strptime(fullPgmDate, dateformat)
        except Exception as e2:
            #Now try a 24 hour clock
            DbgPrint("Error Msg: {}".format(e2.message))
            dateformat = getRegionDatetimeFmt()
            dateformat = dateformat.replace('-', '')
            liDateTime = dt.strptime(fullPgmDate, dateformat)

    # calculate USpgmDate - a region independent datetime object
    USpgmDate = liDateTime.strftime("%m/%d/%Y")
    DbgPrint("***liDateTime: {}".format(liDateTime))
    DbgPrint("***USpgmDate: {}".format(USpgmDate))
    diff = liDateTime - dt.now()

    pgmTime = _germanAM_PM_Fix(pgmTime)

    myLog("****item title: {} ".format(pgmTitle))
    myLog("****item date: {} ".format(pgmDate))
    myLog("****item time: {} ".format(pgmTime))
    myLog("****item ch: {} ".format(pgmCh))
    myLog("****item icon: {} ".format(pgmIcon))
    myLog("****Listitem.Date: {}".format(xbmc.getInfoLabel('Listitem.Date')))

    if win is not None:
        win.setProperty('pgmTitle', pgmTitle)
        win.setProperty('pgmDate', pgmDate)
        win.setProperty('USpgmDate', USpgmDate)
        win.setProperty('pgmTime', pgmTime)
        win.setProperty('pgmCh', pgmCh)
        win.setProperty('pgmIcon', pgmIcon)
        win.setProperty('pgmExpiration', '')
        return diff.days >= 0 and diff.seconds > 60
    else:
        data = {}
        data['pgmTitle']        = pgmTitle
        data['pgmDate']         = pgmDate
        data['USpgmDate']       = USpgmDate
        data['pgmTime']         = pgmTime
        data['pgmCh']           = pgmCh
        data['pgmIcon']         = pgmIcon
        data['pgmExpiration']   = ''
        status = diff.days >= 0 and diff.seconds > 60
        return(status, data)





def checkForEPG():
    bEPGflag = xbmc.getCondVisibility("Window.IsVisible(tvguide)")
    bTvSearchflag = xbmc.getCondVisibility("Window.IsVisible(tvsearch)")

    return bEPGflag or bTvSearchflag



def getHdrKeys():
    keys = [w[0].split()[0] for w in HDR_FORMAT]
    return keys

def getHdrKeysExtended():
    DbgPrint("***HDR_FORMAT_EXTENDED:{}".format(HDR_FORMAT_EXTENDED))
    keys = [w[3].split()[0] for w in HDR_FORMAT_EXTENDED]
    DbgPrint("***keys:{}".format(keys))
    return keys

def BuildHeader():
    item = xbmcgui.ListItem()
    for val in HDR_FORMAT:
        strval = "{} ".format(val[0])
        myLog(strval)
        label = val[0].split()[0]
        item.setProperty(label, val[0])

    return item



class GUI(xbmcgui.WindowXMLDialog):
    def __new__(cls, defaultSkin, defaultRes, bDialog, queue):
        return super(GUI, cls).__new__(cls, 'mainDialog.xml', xbmcaddon.Addon(ADDONID).getAddonInfo('path'),
                                       defaultSkin, defaultRes)

    def __init__(self, defaultSkin, defaultRes, bDialog, queue, *args, **kwargs):
        super(GUI, self).__init__(*args, **kwargs)

        address = ('localhost', ServerPort)
        self.client = None
        self.signal = Signal()
        self.blockNotification = False
        self.shutdown = False
        self.currentPos = (0, 0)
        self.setProperty('Go', '0')
        myLog("***Showing Busy Dialog")
        self.bDialog = bDialog
        self.queue = queue
        self.connectToServer()
        self.clearList()
        self.toolboxBusyDialog = None

        setDialogActive(MAIN_DIALOGTAG)

    def xlateRecurrenceOptions(self, optEng):
        for opt in RECURRENCE_OPTIONS:
            if optEng == opt[1]:
                return opt[0]

    def closeBusyDialog(self):
        myLog("****closeBusyDialog Called...")
        self.bDialog.Stop()
        del self.bDialog


    def connectToServer(self):
        try:
            address = (ServerHost, ServerPort)
            self.client = PL_Client(address)
            myLog("**Client Connected")
            self.client.addDataReceivedEventHandler(self.onResponseReceived)
            self.client.addNotificationReceivedEventHandler(self.onNotificationReceived)
        except: pass

    def BuildHeader(self):
        for val in HDR_FORMAT:
            label = val[3].split()[0]
            self.setProperty(label, val[0])

    def onInit(self):
        global VACATIONMODE_VALUE
        super(GUI, self).onInit()
        self.list = self.getControl(MAIN_LIST) # type: xbmcgui.ControlList
        # now we are going to add all the items we have defined to the list control
        # Wait for data to come from the server before proceeding
        self.signal.clear()
        if self.client is not None:
            myLog("***Calling GetPlaylist....")
            self.client.GetPlayList()
        winID = xbmcgui.getCurrentWindowDialogId()
        self.queue.put(winID)
        myLog("*******My WinID is {}......".format(winID))
        # define a temporary list where we are going to add all the listitems to
        # listitems = []
        self.setProperty('windowtitle', GETTEXT(30072))
        self.BuildHeader()

        # by Default the built-in container already contains one item, the 'up' (..) item, let's remove that one
        self.clearList()
        self.signal.wait(30.0)  # playlist has been set
        myLog("***Got the Playlist")

        # self.addItems(listitems)
        self.sortItemListByDate()
        myLog("***Finshed Processing Playlist...")
        self.setProperty('Go', '1')
        # give kodi a bit of (processing) time to add all items to the container
        VACATIONMODE_VALUE = ADDON.getSetting(VACATIONMODE) == TRUE
        self.setVacationModeProperty()
        xbmc.sleep(100)
        self.setCurrentListPosition(0)
        self.setFocusId(MAIN_LIST)
        self.closeBusyDialog()

    def setVacationModeProperty(self):
        if VACATIONMODE_VALUE == True:
            val = GETTEXT(30037)
        else:
            val = GETTEXT(30038)
        DbgPrint("val: {}".format(val))
        self.setProperty('vacationMode', val)
        ADDON.setSetting(VACATIONMODE, str(VACATIONMODE_VALUE).lower())


    def onClick(self, controlId):
        DbgPrint("***onClick ctl: {}".format(controlId))
        if controlId == 20:
            self.closeDialog()

    def closeDialog(self):
        window_id = xbmcgui.getCurrentWindowId()
        if self.client is not None:
            self.client.closeConnection()

        self.shutdown = True
        self.close()
        xbmc.sleep(100)


    def ShutdownState(self):
        myLog("******ShutdownState: {}".format(self.shutdown))
        return self.shutdown

    def launchEditor(self, data):
        import EPGcapture
        EPGcapture.showDialog(ADDONID, editData=data)

    def extractData(self, item):
        data = {}
        for tag in ListItemPlus.tags:
            value = item.getProperty(tag)
            tmpval = {tag: value}
            data.update(tmpval)

        return data

    def onAction(self, action):
        actionID = action.getId()

        if type(actionID) == int:
            myLog("***Main onAction actionID: {:d}".format(actionID))
        else:
            myLog("****Main onAction actionID: {:d}".format(actionID.getId()))


        if actionID == ACTION_MOVE_LEFT or actionID == ACTION_MOVE_RIGHT:
            pass

        elif actionID == ACTION_CONTEXT_MENU or actionID == ACTION_MOUSE_RIGHT_CLICK:
            self.openSettingsDialog()

        elif actionID == ACTION_NAV_BACK or actionID == ACTION_PREVIOUS_MENU:
            self.closeDialog()

        elif actionID == ACTION_MOVE_DOWN and self.getFocusId() == MAIN_LIST:
            index = self.list.getSelectedPosition()
            myLog("***Main ActionDown: {:d}".format(index))
            if index == self.list.size():
                self.setCurrentListPosition(0)

        elif actionID == ACTION_MOVE_UP and self.getFocusId() == MAIN_LIST:
            index = self.list.getSelectedPosition()
            myLog("***Main ActionUp: {:d}".format(index))
            if index < 0:
                self.setCurrentListPosition(self.list.size() - 1)

        elif actionID == ACTION_SELECT_ITEM or actionID == ACTION_MOUSE_LEFT_CLICK:
            pos = self.list.getSelectedPosition()
            if pos < 0:
                return

            item = ListItemPlus(self.list.getListItem(pos))
            myLog("***********>Item Selected: {} at {}".format(item.getProperty('Description'), self.currentPos))
            suspendedFlag = item.getProperty('suspendedFlag') == 'True'

            if VACATIONMODE_VALUE == False:
                if not suspendedFlag:
                    cmd = contextmenu.showMenu(ADDONID, ContextMenuItems, self.ShutdownState)
                else:
                    cmd = contextmenu.showMenu(ADDONID, ContextMenuItems2, self.ShutdownState)

                myLog("************Cmd:{}".format(cmd))
                if cmd is not None:
                    id = item.getProperty('ID')
                    self.toolboxBusyDialog = myBusyDialog()
                    if cmd == MENU_DELETE_ITEM:
                        dialog = xbmcgui.Dialog()
                        if dialog.yesno(LTVPL, GETTEXT(30067).format(item.getProperty('Description'))):
                            myLog("******Delete Event Selected")
                            self.toolboxBusyDialog.show()
                            xbmc.sleep(250)
                            self.client.RemovePlayListItem(id)
                            self.sortItemListByDate()
                            dialog.notification(LTVPL, GETTEXT(30060)) #"Delete Operation Successful"
                        else:
                            dialog.notification(LTVPL, GETTEXT(30061), xbmcgui.NOTIFICATION_INFO) #"Delete Operation Cancelled!"

                    elif cmd == MENU_SKIP_ITEM:
                        myLog("******Skip Event Selected")
                        self.toolboxBusyDialog.show()
                        self.client.SkipPlayListItem(id)

                    elif cmd == MENU_SUSPEND_ITEM:
                        myLog("******Suspend Event Selected")
                        self.toolboxBusyDialog.show()
                        self.suspendPlayListItem(self.list.getListItem(pos))
                        self.toolboxBusyDialog.Stop()
                        self.toolboxBusyDialog = None

                    elif cmd == MENU_EDIT_ITEM:
                        myLog("******Edit Event Selected")
                        self.launchEditor(item.Data)
            else:
                self.showVacationModeDialog()


    def onFocus(self, ctrlID):
        if ctrlID == MAIN_LIST:
            ctrl = self.getControl(ctrlID)
            self.currentPos = ctrl.getPosition()
            myLog("******CurrentPos: {}\tctrlID: {}".format(self.currentPos, ctrlID))

    def getItemList(self):
        maxitems = self.list.size()
        ilist = [self.list.getListItem(pos) for pos in range(maxitems)]
        return ilist

    def sortItemListByDate(self):
        # TODO sort does not respect region date format
        itemlist = self.getItemList()
        if len(itemlist) > 0:
            newlist = sorted(itemlist, key=lambda item: item.getProperty('alarmtime'))
            self.list.reset()
            self.list.addItems(newlist)
            # self.list_items = newlist


    def findItemByID(self, id):
        maxitems = self.list.size()
        for i in range(maxitems):
            item = self.list.getListItem(i)
            if id == item.getProperty('ID'):
                return (item, i)

        # raise (Exception("Item ID {} Not Found".format(id)))
        raise Exception

    def updateItemByID(self, id, data):

        hdrkeys = getHdrKeysExtended()
        dateformat = xbmc.getRegion('dateshort')

        try:
            item, pos = self.findItemByID(id)
            DbgPrint("******updateItemByID - found id:{} at pos:{}".format(id, pos))
            if item is not None:

                update = ListItemPlus(dateformat=dateformat)
                update.Data = data
                setUSpgmDate(self)
                self.xlateFrequencyValue(data, update)


                SF = 'suspendedFlag'
                DESC = 'Description'
                suspendFlag = update.getProperty(SF)
                title = update.getProperty(DESC)

                if suspendFlag == 'True':
                    if title[0] != "*":
                        update.setProperty(DESC, "*" + title)
                else:
                    if title[0] == "*":
                        update.setProperty(DESC, title[1:])


                DbgPrint("****update item: {}".format(update.Data))
                for key in hdrkeys:
                    DbgPrint("***CompareProperties: {}\n1 {}\n2 {}".format(key, item.getProperty(key),update.getProperty(key)))
                    if item.getProperty(key) != update.getProperty(key):
                        DbgPrint("*******ChangedProperty:{}:{}".format(key, update.getProperty(key)))
                        item.setProperty(key, update.getProperty(key))
        except Exception as e:
            DbgPrint("Error in updateItemByID: {}".format(str(e)))

        self.sortItemListByDate()

    def removeItemByID(self, id):
        try:
            myLog("**********Calling findItemByID......")
            pos = self.findItemByID(id)[1]
            myLog("***removeItemByID Found itemID:{} at pos:{}".format(id, pos))

            try:
                self.list.removeItem(pos)
                self.sortItemListByDate()
            except Exception as e:
                myLog(e)
        except Exception as e:
            myLog(str(e))


    def addNewItem(self, data):
        try:
            dateformat = xbmc.getRegion('dateshort')
            item = ListItemPlus(dateformat=dateformat)
            item.Data = data
            setUSpgmDate(self)
            self.xlateFrequencyValue(data, item)
            self.list.addItem(item)
            self.list_items.append(item)
            self.sortItemListByDate()
        except: pass

    def clearItems(self):
        self.clearList()

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
                DbgPrint("****self.removeItemByID({})".format(id))
                self.removeItemByID(id)

            elif cmd == NotificationAction.ItemAdded:
                DbgPrint("****self.addNewItem({})".format(data))
                cmd, data = genericDecode(data)
                self.addNewItem(data)

            elif cmd == NotificationAction.ItemUpdated:
                cmd, data = genericDecode(data)
                try:
                    id = data['id']
                except:
                    id = data
                DbgPrint("****self.updateItemByID({},{})".format(id, data))
                self.updateItemByID(id, data)

            elif cmd == NotificationAction.VacationMode:
                global VACATIONMODE_VALUE

                DbgPrint("VacationMode: {}".format(data))
                try:
                    VACATIONMODE_VALUE = data['SetVacationMode']
                except:
                    VACATIONMODE_VALUE = data

                self.setVacationModeProperty()

            if self.toolboxBusyDialog is not None:
                self.toolboxBusyDialog.Stop()
                self.toolboxBusyDialog = None

        except Exception as e:
            DbgPrint("onNotification Error Message:{}".format(str(e)))


    def xlateFrequencyValue(self, data, obj):
        # translate recurrenceinterval to current language
        recurrenceIntervalValue = data['recurrenceInterval'].capitalize()
        recurrenceIntervalValue = self.xlateRecurrenceOptions(recurrenceIntervalValue)
        obj.setProperty('Frequency', recurrenceIntervalValue)


    def onResponseReceived(self, cmd, data):
        myLog("**DataResponse Received: {}".format(data))

        if cmd == Cmd.GetChannelList:
            pass

        elif cmd == Cmd.GetPlayList:
            dateformat = xbmc.getRegion('dateshort')
            dataSetData = data
            ilist = []
            try:
                dataSetData[VACATIONMODE]
                del dataSetData[VACATIONMODE]
            except Exception as e:
                pass

            for key in dataSetData:
                myLog("**Data: {}".format(dataSetData[key]))
                obj = ListItemPlus(dateformat=dateformat)
                obj.Data = dataSetData[key]
                setUSpgmDate(obj)
                # translate recurrenceinterval to current language
                self.xlateFrequencyValue(dataSetData[key], obj)

                try:
                    SF = 'suspendedFlag'
                    DESC = 'Description'
                    suspendFlag = obj.getProperty(SF)
                    title = obj.getProperty(DESC)

                    if suspendFlag == 'True':
                        if title[0] != "*":
                            obj.setProperty(DESC, "*" + title)
                    else:
                        if title[0] == "*":
                            obj.setProperty(DESC, title[1:])
                except Exception as e:
                    DbgPrint("Data Received Error: {}".format(str(e)))

                ilist.append(obj)

            self.list_items = ilist
            self.list.addItems(ilist)
            self.signal.set()

        elif cmd == Cmd.AddPlayListItem:
            myLog("********onResponseReceived.addPlayListItem: {}".format(data))
            self.addNewItem(data)

        elif cmd == Cmd.UpdatePlayListItem or cmd == Cmd.SkipEvent:
            myLog("********onResponseReceived.UpdatePlayListItem: {}".format(data))
            id = data['id']
            self.updateItemByID(id, data)

        elif cmd == Cmd.RemovePlayListItem:
            myLog("********onResponseReceived.RemovePlayListItem: {}".format(data))
            id = data
            self.removeItemByID(id)

        elif cmd == Cmd.GetChGroupList:
            pass

    def suspendPlayListItem(self, item):
        SF='suspendedFlag'
        DESC='Description'

        suspendFlag = item.getProperty(SF)
        id = item.getProperty('ID')
        title = item.getProperty(DESC)

        DbgPrint("********SuspendFlag: {}".format(suspendFlag))

        if suspendFlag == 'True':
            item.setProperty(SF,'False')
            self.client.enablePlayListItem(id)
            if title[0] == "*":
                item.setProperty(DESC, title[1:])
        else:
            item.setProperty(SF, 'True')
            self.client.suspendPlayListItem(id)
            if title[0] != "*":
                item.setProperty(DESC, "*" + title)


    def openSettingsDialog(self):
        xbmc.executebuiltin("Addon.OpenSettings({})".format(ADDONID))

    def showVacationModeDialog(self):
        xbmcgui.Dialog().notification(LTVPL, GETTEXT(30062)) #"Vacation Mode is Active..."

@TS_decorator
def showMainDialog(queue, bDialog):
    myLog("*********Calling Main Dialog")
    if not isDialogActive(MAIN_DIALOGTAG):
        bDialog.show()
        ui = GUI('Default', '720p', bDialog, queue)
        ui.doModal()
        myLog("***Main I'm After doModal()")
        clearDialogActive(MAIN_DIALOGTAG)
        del ui
        del bDialog



@TS_decorator
def showEPGCaptureDialog(epgData, bDialog):
    DbgPrint("***showEPGCaptureDialog Called")
    EPGcapture.showDialog(ADDONID, epgData=epgData, shutdownCallback=bDialog.Stop)


@TS_decorator
def ShowBusyDialog(bDialog, queue, tmpBD):
    winID = queue.get(True, None)
    myLog("****Activating Busy Dialog...: {}".format(winID))
    tmpBD.Stop()
    # bDialog.show()
    myLog("****Main winID: {}".format(winID))
    # bDialog.show()


def showVacationModeDialog():
    xbmcgui.Dialog().notification(LTVPL, GETTEXT(30062)) #Vacation Mode Active


class doSettings(object):
    def __init__(self):
        self.signal = Signal()
        self.svrVacationMode = None
        self.client = None

    def __call__(self):
        from time import sleep
        global VACATIONMODE_VALUE


        VACATIONMODE_VALUE = ADDON.getSetting(VACATIONMODE) == TRUE
        dbgmode = ADDON.getSetting(DEBUGMODE) == TRUE

        try:
            self.connectToServer()
            self.signal.clear()
            self.client.getVacationmode()
            self.signal.wait(30.0)

            if VACATIONMODE_VALUE != self.svrVacationMode:
                self.signal.clear()
                self.client.setVacationmode(VACATIONMODE_VALUE)
                self.signal.wait(30.0)

            self.client.closeConnection()
            self.client = None

        except Exception as e:
            DbgPrint("doSettings Error: {}".format(str(e)))
            if self.client is not None:
                self.client.closeConnection()

    def connectToServer(self):
        address = (ServerHost, ServerPort)
        self.client = PL_Client(address)
        self.client.addDataReceivedEventHandler(self.onResponseReceived)

    def onResponseReceived(self, cmd, data):
        if cmd == Cmd.GetVacationMode:
            self.svrVacationMode = data

        self.signal.set()

if (__name__ == '__main__'):
    import EPGcapture
    queue = Queue()
    DbgPrint("len(sys.argv)={}".format(len(sys.argv)))

    if len(sys.argv) > 1:
        if sys.argv[1] == 'keymap':
            setActivationKey()
        elif sys.argv[1] == 'reloadkeymaps':
            reloadKeyMaps()
    else:
        bDialog = myBusyDialog()
        if checkForEPG():
            if VACATIONMODE_VALUE == False:
                epgData = getEPG_Data()
                bDialog.show()
                xbmc.sleep(2000)
                showEPGCaptureDialog(epgData, bDialog)
            else:
                showVacationModeDialog()
        else:
            showMainDialog(queue, bDialog)
