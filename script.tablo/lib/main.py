import tablo
import windows
import util
import backgroundthread


def start():
    util.LOG('[- START -----------------------] [{0}]'.format(util.ADDON.getAddonInfo('version')))
    util.setGlobalProperty('guide.filter', '')
    util.setGlobalProperty('section', '')

    with util.Cron(interval=5):
        bw = windows.BackgroundWindow.create()
        connected = False
        ID = util.loadTabloDeviceID()
        if ID:
            tablo.API.discover()
            connected = tablo.API.selectDevice(ID)

        while True:
            if not connected:
                if connected is None:
                    w = windows.ConnectWindow.open(updating=True)
                    del w
                    connected = False
                    if ID:
                        tablo.API.discover()
                        connected = tablo.API.selectDevice(ID)
                    continue
                else:
                    w = windows.ConnectWindow.open()
                    if w.exit or not tablo.API.deviceSelected():
                        return
                    del w

            if tablo.API.getUpdateStatus():
                util.DEBUG_LOG('Updating ({0})'.format(tablo.API.device.name))
                connected = None
                continue

            windows.WM.start()

            if windows.WM.exit:
                break

            connected = False

        bw.show()
        bw.setProperty('busy', '1')

        backgroundthread.BGThreader.shutdown()

        bw.doClose()
        del bw

    util.LOG('[- END -------------------------]')
