import os
import threading
import xbmc
import xbmcgui
import kodigui
from lib import tablo
from lib import util
from lib.util import T


class ConnectWindow(kodigui.BaseWindow):
    xmlFile = 'script-tablo-connect.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.updating = kwargs.get('updating')
        self.exit = True
        self.abort = False

    def onFirstInit(self):
        if self.updating and len(tablo.API.devices.tablos) < 2:
            name = tablo.API.device and tablo.API.device.name or 'Tablo'
            self.setProperty('updating', name)
            self.setProperty('tablo.found', '1')
            self.setProperty('initialized', '1')
            self._waitForUpdate()
            self.doClose()
        else:
            if self.updating:
                name = tablo.API.device and tablo.API.device.name or 'Tablo'
                xbmcgui.Dialog().ok(T(32100), T(32101).format(name))
            self.setProperty('updating', '')
            self.setProperty('tablo.found', '')
            self.setProperty('initialized', '')
            self.connect()

    def connect(self):
        self.deviceList = kodigui.ManagedControlList(self, 200, 1)
        self.searchButton = self.getControl(300)

        self.start()

    def waitForUpdate(self):
        threading.Thread(target=self._waitForUpdate).start()

    def _waitForUpdate(self):
        m = xbmc.Monitor()
        while not m.waitForAbort(1):
            if self.abort:
                util.DEBUG_LOG('Exited while waiting for update')
                break

            status = tablo.API.getUpdateStatus()
            if status and status[0] != 'error':
                disp = status[0].title()
                if status[0] == 'downloading' and status[1] is not None:
                    disp = '{0} {1}%'.format(disp, int(status[1] * 100))
                self.setProperty('update.status', disp)
                continue
            else:
                break
        else:
            util.DEBUG_LOG('Shutdown while waiting for update')

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                self.abort = True
                self.doClose()
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == 300:
            self.showDevices()
        elif controlID == 200:
            mli = self.deviceList.getSelectedItem()
            if tablo.API.selectDevice(mli.dataSource.ID):
                util.saveTabloDeviceID(mli.dataSource.ID)
                self.exit = False
                self.doClose()
            else:
                xbmcgui.Dialog().ok(T(32102), T(32103).format(tablo.API.device.displayName))

    def start(self):
        self.showDevices()

    def addTestDevice(self):
        testPath = os.path.join(util.PROFILE, 'test.server')
        if not os.path.exists(testPath):
            return

        util.DEBUG_LOG('TEST SERVER DATA FOUND - ADDING TO DEVICES')

        with open(testPath, 'r') as f:
            ip, port = f.read().strip().split(':', 1)

        device = tablo.discovery.TabloDevice({'private_ip': ip})
        device.port = port
        device.name = 'TEST'
        device.boardType = 'duo'
        device.version = '9.0.0'
        # device.updateInfoFromDevice()

        tablo.API.devices.tablos.append(device)

    def deviceVersionAllowed(self, device):
        try:
            return util.Version(device.version) >= util.Version('2.2.9')
        except:
            util.ERROR()

        return True

    def deviceTypeAllowed(self, device):
        return device.boardType != "android"

    def showDevices(self):
        self.setProperty('tablo.found', '')
        self.deviceList.reset()
        tablo.API.discover()
        self.addTestDevice()
        for device in sorted(tablo.API.devices.tablos, key=lambda x: x.displayName):
            if not self.deviceVersionAllowed(device):
                util.DEBUG_LOG('Skipping device because of low version: {0}'.format(device))
                continue
            if not self.deviceTypeAllowed(device):
                util.DEBUG_LOG('Skipping device because of type: {0}'.format(device))
                continue

            self.deviceList.addItem(kodigui.ManagedListItem(device.displayName, device.boardType, data_source=device))

        self.setProperty('initialized', '1')

        self.setProperty('tablo.found', '1')

        if self.deviceList.size():
            self.setFocusId(200)
        else:
            self.setFocusId(300)
