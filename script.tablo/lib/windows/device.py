import xbmcgui
import kodigui

from lib import tablo
from lib import util
from lib.util import T


WM = None


class DeviceWindow(kodigui.BaseWindow):
    name = 'DEVICE'
    xmlFile = 'script-tablo-device.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    DISCONNECT_BUTTON_ID = 100
    DRIVE_WIDTH = 680

    def onFirstInit(self):
        self.setProperty('device.name', tablo.API.device.displayName)
        self.setProperty('board.type', tablo.API.device.boardType)

        if tablo.API.hasSubscription():
            if tablo.API.subscription.get('state') == 'trial':
                expDT = tablo.api.processDate(tablo.API.subscription.get('expires'))
                interval = expDT - tablo.api.now()
                intervalDisp = util.longDurationToText(tablo.api.compat.timedelta_total_seconds(interval))
                expDisp = expDT.strftime('%B %d, %Y')
                self.setProperty('subscription.title', T(32104))
                self.setProperty(
                    'subscription.description',
                    T(32105).format(interval=intervalDisp, expiration=expDisp)
                )
            elif tablo.subscription.get('state') == 'subscribed':
                self.setProperty('subscription.title', T(32106))
                self.setProperty('subscription.description', T(32107))
        else:
            self.setProperty('subscription.title', T(32108))
            self.setProperty('subscription.description', T(32109))

        self.updateHDInfo()

        if not tablo.API.serverInfo:
            tablo.API.getServerInfo()

        self.setProperty('firmware', tablo.API.serverInfo.get('version', u'[COLOR FFFF8080]{0}[/COLOR]'.format(T(32110))))
        self.setProperty('ip.address', tablo.API.serverInfo.get('local_address', ''))
        si = tablo.API.serverInfo.get('server_id', '')
        if si:
            self.setProperty('mac.address', '{0}:{1}:{2}:{3}:{4}:{5}'.format(si[4:6], si[6:8], si[8:10], si[10:12], si[12:14], si[14:16]))

        self.setProperty('addon.version', util.ADDON.getAddonInfo('version'))

    def onWindowFocus(self):
        self.updateHDInfo()

    def updateHDInfo(self):
        try:
            hdinfo = tablo.API.server.harddrives.get()
        except:
            hdinfo = None
            util.ERROR()

        if not hdinfo:
            return

        controlID = 200
        for i, drive in enumerate(hdinfo):
            if not drive.get('connected'):
                continue

            if controlID > 200:
                break

            self.setProperty('drive.{0}'.format(i), drive['name'])
            self.setProperty('drive.{0}.used'.format(i), u'{0} {1}'.format(util.simpleSize(drive['usage']), T(32111)))
            self.setProperty('drive.{0}.left'.format(i), u'{0} {1}'.format(util.simpleSize(drive['size'] - drive['usage']), T(32112)))
            control = self.getControl(controlID)
            w = int((drive['usage'] / float(drive['size'])) * self.DRIVE_WIDTH)
            control.setWidth(w)
            if self.DRIVE_WIDTH - w < 200:
                self.setProperty('drive.{0}.almost_full'.format(i), '1')
                control = self.getControl(controlID + 1)
                control.setWidth((w / 2) - 15)
                control = self.getControl(controlID + 2)
                control.setWidth((w / 2) - 15)
            else:
                control = self.getControl(controlID + 1)
                control.setWidth(w - 10)
                controlID += 100

    def onAction(self, action):
        try:
            if action in(xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                WM.showMenu()
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.DISCONNECT_BUTTON_ID:
            util.clearTabloDeviceID()
            WM.disconnect()
