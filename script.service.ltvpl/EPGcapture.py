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
#
from datetime import datetime, timedelta
from threading import Event as Signal

import xbmc
import xbmcaddon
import xbmcgui
from addon import strTimeStamp, RECURRENCE_OPTIONS
from util import LTVPL_HEADER
from resources.PL_Client import PL_Client
from resources.lib.Data.PlayListItem import PlayListItem, RecurrenceOptions
from resources.lib.Network.SecretSauce import *
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Utilities.Messaging import Cmd
from util import GETTEXT, setUSpgmDate, getRegionDatetimeFmt
from utility import setDialogActive, isDialogActive, clearDialogActive, myLog

__Version__ = "1.1.2"

ACTION_NAV_BACK = 92
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_CONTEXT_MENU = 117

ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_UP = 3
ACTION_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_MOUSE_DOUBLE_CLICK = 103
ACTION_MOUSE_MOVE = 107

CLOSE_BUTTON = 3001
IMAGE_CONTROL = 200
SUBMIT_BUTTON = 210
CANCEL_BUTTON = 211
FREQ_SELECTOR = 300
EXP_DATE_BUTTON = 400
ShowAndGetDate = 1

EPG_DIALOGTAG = "LTVPL_EPGDIALOG_VISIBLE"
LTVPL = 'Live TV Playlist'

addon = xbmcaddon.Addon()

VACATIONMODE = False
try:
    MODULEDEBUGMODE = addon.getSetting('debugmode') == 'true'
    VACATIONMODE = addon.getSetting('vacationmode') == 'true'
except Exception as e: pass

# RECURRENCE_OPTIONS = [(GETTEXT(30050),'Once'), (GETTEXT(30051),'Daily'), (GETTEXT(30052),'Weekdays'), (GETTEXT(30053),'Weekends'), (GETTEXT(30054),'Weekly'), (GETTEXT(30055),'Monthly')]



def getDateItem(strDate, strTime):
    dateval = strDate + " " + strTime
    DbgPrint("***dateval: {}".format(dateval))
    fmt = getRegionDatetimeFmt()
    try:
        retval = datetime.strptime(dateval, fmt)
    except Exception as e:
        fmt = fmt.replace('-','')
        retval = datetime.strptime(dateval, fmt)

    return retval

def strDate2TimeStamp(tdata):
    fmt = "%Y-%m-%d %H:%M:%S"
    import time
    ts = datetime(*(time.strptime(tdata, fmt)[0: 6]))
    return ts

def calstrDate2TimeStamp(tdata):
    fmt = "%m/%d/%Y"
    import time
    ts = datetime(*(time.strptime(tdata, fmt)[0: 6]))
    ts = ts + timedelta(days=1) - timedelta(seconds=1)
    return ts


class captureEpgItem(xbmcgui.WindowXMLDialog):

    def __new__(cls, addonID, shutdownCallback, stopbusydialogcallback, editData, epgData):
        return super(captureEpgItem, cls).__new__(cls, 'ltvpl-captureEpgItem.xml',
                                                  xbmcaddon.Addon(addonID).getAddonInfo('path'))

    def __init__(self, addonID, shutdownCallback=None, stopbusydialogcallback=None, editData=None, epgData=None):
        super(captureEpgItem, self).__init__()
        self.addonID = addonID
        self.freqSelect = None

        if shutdownCallback is not None:
            DbgPrint("***shutdonwcallback set")
            self.shutdownCallback = shutdownCallback
        else:
            DbgPrint("***shutdonwcallback not set")
            self.shutdownCallback = self.noop

        self.signal = Signal()
        address = (ServerHost, ServerPort)
        self.client = PL_Client(address)
        self.client.addErrorReceivedEventHandler(self.onErrorNotification)
        self.client.addDataReceivedEventHandler(self.onResponseReceived)

        if stopbusydialogcallback is not None:
            self.stopbusydialogcallback = stopbusydialogcallback
        else:
            self.stopbusydialogcallback = self.noop

        self.editmode = False
        if editData is None:
            if epgData is not None:
                self.dataOkFlag = epgData[0]
                data = epgData[1]
                for item in data:
                    self.setProperty(item, data[item])
        else:
            self.processEditData(editData)
            self.editmode = True

        setDialogActive(EPG_DIALOGTAG)


    def noop(self):
        pass

    def processEditData(self, data):
        self.setProperty('pgmTitle', data['Description'])
        strDate = data['Date']
        strTime = data['Time']
        self.setProperty('pgmDate', strDate)
        self.setProperty('pgmTime', strTime)
        self.setProperty('pgmCh', data['Ch'])
        self.setProperty('pgmIcon', '')
        self.setProperty('pgmID', data['ID'])

        try:
            expiry = data['Expires']
            strDate = ''
            if expiry != 'None':
                strDate, _ = strTimeStamp(strDate2TimeStamp(expiry))

            self.setProperty('pgmExpiration', strDate)
        except Exception as e:
            DbgPrint(e)

        self.setProperty('pgmFrequency', data['Frequency'])

    def closeBusyDialog(self):
        if self.stopbusydialogcallback is not None:
            self.stopbusydialogcallback()

    def onInit(self):
        #Headings
        self.setProperty('date', GETTEXT(30040))
        self.setProperty('time', GETTEXT(30041))
        self.setProperty('ch', GETTEXT(30042))
        self.setProperty('title', GETTEXT(30043))
        self.setProperty('expiry', GETTEXT(30044))
        self.setProperty('submit',GETTEXT(30045))
        self.setProperty('cancel', GETTEXT(30046))
        self.setProperty('frequency', GETTEXT(30033))

        if not self.editmode:
            if not self.dataOkFlag:
                myLog("*****EPG Data is Stale....")
                xbmcgui.Dialog().notification(LTVPL_HEADER, GETTEXT(30064)) #cannot add item
                self.closeBusyDialog()
                self.closeDialog()

            super(captureEpgItem, self).onInit()
            flag = False
            if self.shutdownCallback is not None:
                flag = self.shutdownCallback()

            DbgPrint("*******onInit ShutdownState:{}".format(flag))
            if flag:
                self.closeDialog()

            url = self.getProperty('pgmIcon')
            DbgPrint("***url:" + url + "***")

            ctrl = self.getControl(IMAGE_CONTROL)
            ctrl.setImage(url)
            DbgPrint("****Image Set")

        self.selectctrl = self.getControl(FREQ_SELECTOR)
        for item in RECURRENCE_OPTIONS:
            self.selectctrl.addItem(xbmcgui.ListItem(item[0]))

        self.setFocus(self.selectctrl)
        xbmc.executebuiltin("Action(Right)")
        xbmc.executebuiltin("Action(Left)")
        #
        if self.editmode:
            try:
                setUSpgmDate(self)
                freq = self.getProperty('pgmFrequency').lower()
                pos = [n for n, x in enumerate(RECURRENCE_OPTIONS) if freq == x[0].lower()][0]
                self.selectctrl.selectItem(pos)
            except Exception as e:
                DbgPrint(e)

        self.closeBusyDialog()

    @staticmethod
    def onErrorNotification(opstatus, errMsg):
        xbmc.log("EPGcapture Error Message Received: {}:{}".format(str(opstatus), errMsg))
        if opstatus.value >= 30000:
            msg = GETTEXT(opstatus.value).format(errMsg)
            xbmcgui.Dialog().notification(LTVPL, msg, icon=xbmcgui.NOTIFICATION_ERROR)
        else:
            xbmcgui.Dialog().notification("Live TV Playlist Error", errMsg, icon=xbmcgui.NOTIFICATION_ERROR)

    def closeDialog(self):
        self.close()
        if self.client is not None:
            self.client.closeConnection()

        xbmc.sleep(100)


    def onResponseReceived(self, cmd, data):
        xbmc.log("**DataResponse Received: {}".format(data))
        #
        if cmd == Cmd.AddPlayListItem or Cmd.UpdatePlayListItem:
            self.signal.set()

    def onAction(self, action):
        actionId = action.getId()

        if actionId in [ACTION_CONTEXT_MENU, ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            return self.closeDialog()

        elif actionId == ACTION_SELECT_ITEM or actionId == ACTION_MOUSE_LEFT_CLICK:
            ctrl = self.getControl(SUBMIT_BUTTON)
            myLog("***Frequency Selected")
            self.setFocus(ctrl)

        elif actionId == ACTION_MOUSE_RIGHT_CLICK:
            ctrl = self.getControl(FREQ_SELECTOR)
            ctrl.setEnabled(True)

        super(captureEpgItem, self).onAction(action)


    def xlateRecurrenceOptions(self, optvalue):
        for opt in RECURRENCE_OPTIONS:
            DbgPrint("***opt:{}".format(opt))
            if optvalue == opt[0].upper():
                return opt[1]

    def createPlaylistObj(self):
        alarmtime = getDateItem(self.getProperty('pgmDate'), self.getProperty('pgmTime'))
        ch = self.getProperty('pgmCh')
        title = self.getProperty('pgmTitle')
        if self.freqSelect is None:
            selectctrl = self.getControl(FREQ_SELECTOR)
            tmp = selectctrl.getSelectedItem().getLabel().upper()
            DbgPrint("***tmpvalue:{}".format(tmp))
            selectedFreq = self.xlateRecurrenceOptions(tmp).upper()
        else:
            selectedFreq = self.freqSelect

        DbgPrint("selectedFreq:{}".format(selectedFreq))
        freq = RecurrenceOptions[selectedFreq]
        expDate = self.getProperty('pgmExpiration')

        if expDate == '':
            expDate = None
        else:
            expDate = calstrDate2TimeStamp(expDate)
        DbgPrint("***alarmtime={}, ch={}, title={}, recurrenceInterval={}, expiryDate={}".format(alarmtime, ch, title, freq, expDate))
        obj = PlayListItem(alarmtime=alarmtime, ch=ch, title=title, recurrenceInterval=freq, expiryDate=expDate)
        if self.editmode:
            obj.id = self.getProperty('pgmID')

        return obj

    def sendRequest(self, cmd, obj):
        if self.client is not None:
            icon = self.getProperty("pgmIcon")
            title = obj.title
            self.signal.clear()
            if cmd == Cmd.AddPlayListItem:
                self.client.AddPlayListObj(obj)
                if self.signal.wait(5.0):
                    xbmcgui.Dialog().notification(LTVPL_HEADER, GETTEXT(30065).format(title), icon=icon) #Added Succesfully
                else:
                    xbmc.log("******Added Item Error")
            elif cmd == Cmd.UpdatePlayListItem:
                self.client.UpdatePlayListObj(obj)
                if self.signal.wait(20.0):
                    xbmcgui.Dialog().notification(LTVPL_HEADER, GETTEXT(30066).format(title), icon=icon) #Updated Successfully
                else:
                    xbmc.log("******Update Item Error")

    def activateDateDialog(self):
        # TODO customize date per regional value
        today = datetime.today().strftime("%d/%m/%Y")
        retval = xbmcgui.Dialog().numeric(ShowAndGetDate, 'Expiration Date (DD/MM/YYYY)', today)
        retval = retval.replace(' ', '0')
        strExpDate = datetime.strptime(retval, "%d/%m/%Y").strftime("%m/%d/%Y")

        return strExpDate

    def onClick(self, controlId):
        if controlId == CLOSE_BUTTON or controlId == CANCEL_BUTTON:
            self.closeDialog()

        elif controlId == EXP_DATE_BUTTON:
            strExpDate = self.activateDateDialog()
            self.setProperty('pgmExpiration', strExpDate)

        elif controlId == SUBMIT_BUTTON:
            try:
                obj = self.createPlaylistObj()
                if self.editmode:
                    self.sendRequest(Cmd.UpdatePlayListItem, obj)
                else:
                    self.sendRequest(Cmd.AddPlayListItem, obj)
            except Exception as e:
                DbgPrint("***Exception:{}".format(str(e)))
                DbgPrint("***USpgmDate Property: {}".format(self.getProperty('USpgmDate')))
                xbmcgui.Dialog().notification(LTVPL_HEADER, str(e), xbmcgui.NOTIFICATION_ERROR)
            self.closeDialog()

        elif controlId == FREQ_SELECTOR:
            selectctrl = self.getControl(FREQ_SELECTOR)
            tmp = selectctrl.getSelectedItem().getLabel().upper()
            self.freqSelect = self.xlateRecurrenceOptions(tmp).upper()
            selectctrl.setEnabled(False)



def showDialog(addonID, shutdownCallback=None, stopbusydialogcallback=None, editData = None, epgData=None):
    if not isDialogActive(EPG_DIALOGTAG):
        if not VACATIONMODE:
            ui = captureEpgItem(addonID, shutdownCallback, stopbusydialogcallback=stopbusydialogcallback, editData=editData, epgData=epgData)
            ui.doModal()
            xbmc.log("******captureEPG Post doModal......")
            clearDialogActive(EPG_DIALOGTAG)
            del ui
        else:
            xbmcgui.Dialog().notification(LTVPL,GETTEXT(30062)) #Vacation Mode Active
