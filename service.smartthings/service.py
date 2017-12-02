#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Smartthing Monitor.
#
# Smartthing Monitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartthing Monitor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smartthing Monitor.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, time, datetime, re, traceback
import urllib, urllib2, socket, requests, random
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup

# Plugin Info
ADDON_ID      = 'service.smartthings'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

# Globals
BASE_URL      = 'https://graph.api.smartthings.com/'
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"
USERNAME      = (REAL_SETTINGS.getSetting('User_Email')  or None)
PASSWORD      = REAL_SETTINGS.getSetting('User_Password')
HUB_URL       = (REAL_SETTINGS.getSetting('Hub_URL') or None)
HUB_NAME      = (REAL_SETTINGS.getSetting('Select_Hub')  or None)
DEVICE_LST    = (REAL_SETTINGS.getSetting('Select_Devices') or None)
MONITOR_KEYS  = ['Status','Switch','Acceleration','Motion','Contact','Battery','Temperature']
EVENTS        = REAL_SETTINGS.getSetting('Monitor_Events') == "true"
IGNORE        = REAL_SETTINGS.getSetting('Disable_Notify') == "true"
MON_SWT       = REAL_SETTINGS.getSetting('Monitor_Switch') == "true"
MON_MOT       = REAL_SETTINGS.getSetting('Monitor_Motion') == "true"
MON_STAT      = REAL_SETTINGS.getSetting('Monitor_Status') == "true"
MON_ACCL      = REAL_SETTINGS.getSetting('Monitor_Accelerate') == "true"
MON_BATT      = [False,50,40,30,20,10][int(REAL_SETTINGS.getSetting('Monitor_Battery'))]
MON_TEMP      = REAL_SETTINGS.getSetting('Monitor_Temperature') == "true"
TEMP_MIN      = float(REAL_SETTINGS.getSetting('Temperature_MIN'))
TEMP_MAX      = float(REAL_SETTINGS.getSetting('Temperature_MAX'))

#inspired by https://github.com/MikeFez/SmartThings-DeviceInfo-Scraper
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

def chunks(lst, num):
    for i in range(0, len(lst), num):
        yield lst[i:i + num]

def isBusyDialog():
    return bool(xbmc.getCondVisibility('Window.IsActive(busydialog)'))

def show_busy_dialog():
    if not isBusyDialog(): xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy_dialog():
    while isBusyDialog():
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        xbmc.sleep(100)
           
def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    if len(retval) > 0: return retval    
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)
    
def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def notification(str1, header=ADDON_NAME):
    xbmcgui.Dialog().notification(header, str1, ICON, 4000)

def selectDialog(multi, list, header=ADDON_NAME, autoclose=0, preselect=None, useDetails=False):
    if multi == True:
        if not preselect: preselect = []
        return xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else:
        if not preselect: preselect = -1
        return xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
        
def getProperty(string1):
    return xbmcgui.Window(10000).getProperty(string1)
          
def setProperty(string1, value):
    xbmcgui.Window(10000).setProperty(string1, value)
    
def clearProperty(string1):
    xbmcgui.Window(10000).clearProperty(string1)
     
class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.pendingChange = False

        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        self.pendingChange = True

class STHUB(object):
    def __init__(self):
        self.lastEvent  = None
        self.chkIntval  = 720.0
        self.hubName    = HUB_NAME
        self.hubURL     = HUB_URL
        self.username   = USERNAME
        self.password   = PASSWORD
        self.deviceLST  = DEVICE_LST if DEVICE_LST is None else DEVICE_LST.split('|') 
        self.configured = False
        self.nextCHK    = datetime.datetime.now()
        self.session    = requests.Session()
        self.url        = self.login()
        if self.url is None: return notification(LANGUAGE(30003))
        if self.hubURL is None: return notification(LANGUAGE(30020)) 

        
    def wizard(self):
        log("wizard")
        self.username = inputDialog(LANGUAGE(30001))
        self.password = inputDialog(LANGUAGE(30002),opt=xbmcgui.ALPHANUM_HIDE_INPUT)
        REAL_SETTINGS.setSetting('User_Email',self.username)
        REAL_SETTINGS.setSetting('User_Password',self.password)

        
    def login(self):
        log("login")
        if self.username is None: return None#self.wizard() # firstrun wizard
        login_data = {"username": self.username,
                      "password": self.password}       
        r = self.session.post("https://auth-global.api.smartthings.com/sso/authenticate", data=login_data)
        if r.status_code == 401: return None
        return self.resolveURL()

        
    def resolveURL(self):
        res = self.session.get(BASE_URL+"location/list")
        res.raise_for_status()
        location_rows = BeautifulSoup(res.text, "html.parser").find('tbody').findAll('tr')
        for row in location_rows:
            try: 
                url = (row.find('a')['href']).replace('/show/','/')
                self.configured = True
                return url
            except: pass
        return None

        
    def getHubs(self):
        log("getHubs, Gathering list of locations...")
        try:
            show_busy_dialog()
            res = self.session.get(BASE_URL+"location/list")
            res.raise_for_status()
            location_rows = BeautifulSoup(res.text, "html.parser").find('tbody').findAll('tr')
            location_dict = {}
            for row in location_rows:
                location_link = row.find('a')
                location_dict[location_link.contents[0].strip()] = location_link['href'].split(":443/location/")[0]
            location_keys = list(location_dict.keys())
            hub    = 0 if self.hubName is None else location_keys.index(self.hubName)
            hide_busy_dialog()
            select = selectDialog(False, location_keys, LANGUAGE(30006), preselect=hub)
            if select > -1:        
                self.hubName = location_keys[select]
                self.hubURL  = location_dict[self.hubName]
                REAL_SETTINGS.setSetting('Hub_URL', self.hubURL)
                REAL_SETTINGS.setSetting('Select_Hub', self.hubName)
                if self.deviceLST is None: return self.getDeviceList() 
            self.openSettings()
        except Exception as e: 
            log("getHubs, Failed " + str(e), xbmc.LOGERROR)
        hide_busy_dialog()
            
        
    def getDeviceList(self, ALL=False, OPEN=True):
        log("getDeviceList, Gathering list of devices...")
        try:
            if self.hubURL is None: return notification(LANGUAGE(30004))
            show_busy_dialog()
            res = self.session.get(self.hubURL+"/device/list")
            res.raise_for_status()
            device_page = BeautifulSoup(res.text, "html.parser")
            device_rows = device_page.find('tbody').findAll('tr')
            device_dict = {}
            for row in device_rows:
                device_link = row.find('a')
                device_dict[device_link.contents[0].strip()] = device_link['href']
            device_keys = sorted(list(device_dict.keys()))
            device_select = []
            hide_busy_dialog()
            if ALL: return device_keys
            if self.deviceLST is None: self.deviceLST = []
            for device in self.deviceLST:
                try: device_select.append(device_keys.index(device))
                except: pass
            select  = selectDialog(True, device_keys, LANGUAGE(30005), preselect=device_select)
            if select > -1:
                for sel in select: self.deviceLST.append(device_keys[sel])
            REAL_SETTINGS.setSetting('Select_Devices','|'.join(self.deviceLST))
            if OPEN: self.openSettings()
        except Exception as e: 
            log("getDeviceList, Failed " + str(e), xbmc.LOGERROR)
        hide_busy_dialog()
            

    def getDeviceInfo(self, deviceLST=None):
        log("getDeviceInfo, Gathering device info...")
        try:
            res = self.session.get(self.hubURL+"/device/list")
            res.raise_for_status()
            device_page = BeautifulSoup(res.text, "html.parser")
            device_rows = device_page.find('tbody').findAll('tr')
            device_dict = {}
            for row in device_rows:
                device_link = row.find('a')
                device_dict[device_link.contents[0].strip()] = device_link['href']
            device_keys = list(device_dict.keys())
            for device in device_keys:
                deviceJSON = {}
                deviceJSON['name'] = device
                if deviceLST and device not in deviceLST: continue
                log("Gathering device information for [%s]"%device)
                res = self.session.get(self.hubURL+device_dict[device])
                res.raise_for_status()
                full_device_page = BeautifulSoup(res.text, "html.parser")
                report_table_html = full_device_page.findAll('tr', {'class': 'fieldcontain'})
                for item in report_table_html:
                    if "Current States" in item.getText(): data_items = item.findAll('li', {'class': 'property-value'})
                for item in data_items:
                    data_type = item.find('a').contents[0].title()
                    try: data_value = float(item.find('strong').contents[0].split(" ")[0])
                    except ValueError: data_value = item.find('strong').contents[0].split(" ")[0]
                    if data_type == 'Checkinterval' and data_value < self.chkIntval: self.chkIntval = data_value
                    deviceJSON[data_type] = data_value
                yield deviceJSON
        except Exception as e: log("getDeviceInfo, Failed " + str(e), xbmc.LOGERROR)

        
    def getEvents(self, deviceLST=None, LAST=True, ALL=False):
        log("getEvents")
        try:
            events = []
            res = self.session.get(self.resolveURL()+"/events")
            res.raise_for_status()
            event_page = BeautifulSoup(res.text, "html.parser")
            event_rows = event_page.findAll('a', {'class': 'tooltip-init'})
            event_rows = [x['title'] for x in event_rows]
            event_rows = list(chunks(event_rows,3))
            for event in event_rows:
                try:
                    if ALL:
                        events.append(event[2])
                    else:
                        device = (([x for x in deviceLST if x in event[2]])[0])
                        if event[2].startswith(device):
                            if LAST: return event[2]
                            else: events.append(event[2])
                except: pass
        except Exception as e: log("checkEvents, Failed " + str(e), xbmc.LOGERROR)
        return events
           
           
    def checkEvents(self):
        try:
            event = (self.getEvents(self.deviceLST) or None)
            if event != self.lastEvent:
                self.lastEvent = event
                notification(event)
            return True
        except Exception as e: log("checkEvents, Failed " + str(e), xbmc.LOGERROR)
        return False
        
           
    def chkDeviceStatus(self):
        deviceInfo = list(self.getDeviceInfo(self.deviceLST))
        for device in deviceInfo:
            battery     = (device.get('Battery',None) or None)
            temperature = (device.get('Temperature',None) or None)
            if MON_TEMP and temperature is not None:
                if (temperature > TEMP_MAX or temperature < TEMP_MIN): notification('%s Temperature is %f'%(device['name'],temperature))
            if MON_BATT and battery is not None:
                if (battery) <= MON_BATT: notification('%s Battery is %d'%(device['name'],int(battery)))
        self.nextCHK = datetime.datetime.now() + datetime.timedelta(seconds=self.chkIntval)
        log('chkDeviceStatus, nextCHK = ' + str(self.nextCHK))
        return True
                
              
    def startService(self):
        log('startService')
        self.myMonitor = Monitor()
        #Random start delay, avoid all services from starting at the same time.
        self.myMonitor.waitForAbort(random.randint(5, 30))
        while not self.myMonitor.abortRequested():
            # Don't run while setting menu is opened.
            if not self.configured:
                log('startService, settings not configured')
                self.myMonitor.waitForAbort(5)
                continue
                
            if xbmcgui.getCurrentWindowDialogId() in [10140,10103,12000]:
                log('startService, settings dialog opened')
                self.myMonitor.waitForAbort(15)
                continue 
                
            if self.myMonitor.pendingChange or self.myMonitor.waitForAbort(5): 
                log('startService, waitForAbort/pendingChange')
                break

            # Don't run while playing.
            if xbmc.Player().isPlayingVideo() and IGNORE:
                log('startService, ignore during playback')
                self.myMonitor.waitForAbort(5)
                continue
                
            if EVENTS: self.checkEvents()
            if datetime.datetime.now() >= self.nextCHK: self.chkDeviceStatus()
                
        if self.myMonitor.pendingChange:
            notification(LANGUAGE(30007))
            self.restartService()
            
        
    def restartService(self):
        log('restartService')
        #adapted from advised method https://forum.kodi.tv/showthread.php?tid=248758
        xbmc.sleep(500)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":false}, "id": 1}'%(ADDON_ID))
        xbmc.sleep(500)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":true}, "id": 1}'%(ADDON_ID))
            
             
    def openSettings(self):
        log('openSettings')
        return REAL_SETTINGS.openSettings()

try: mode = sys.argv[1]
except: mode = None

if __name__ == '__main__':
    if mode == '-Hub': STHUB().getHubs()
    elif mode == '-Device': STHUB().getDeviceList()
    else: STHUB().startService()    