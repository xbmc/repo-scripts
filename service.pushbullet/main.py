import lib.common

__addon__        = lib.common.__addon__
__addonpath__    = lib.common.__addonpath__

from lib.common import *


def sendEphemeralTest():
    pushbullet = initPBClient()

    # TODO: get image from notification2push class (when created)
    # xbmc icon (used as ephemerals icon)
    import os
    xbmcImgPath = os.path.join(__addonpath__, 'resources', 'media', 'xbmc.jpg')

    import base64
    with open(xbmcImgPath, "rb") as imgFile:
        xbmcImgEncoded = base64.b64encode(imgFile.read())


    ephemeralMsg = {'title': localise(30102), 'body': localise(30103), 'icon': xbmcImgEncoded}

    if len(pushbullet.sendEphemeral(ephemeralMsg)) == 0:
        log('Ephemeral push sended: %s - %s' % (ephemeralMsg['title'], ephemeralMsg['body']))
    else:
        log('Ephemeral push NOT send: %s - %s' % (ephemeralMsg['title'], ephemeralMsg['body']), xbmc.LOGERROR)

    pushbullet.close()


def initPBClient():
    from lib.pushbullet import Pushbullet

    accessToken = __addon__.getSetting('pb_access_token')
    deviceIden = __addon__.getSetting('pb_client_iden')

    # init pushbullet
    pushbullet = Pushbullet(access_token=accessToken)
    pushbullet.setDeviceIden(deviceIden)

    return pushbullet


def handleArg(arg):
    if arg == 'SEND_EPHEMERAL_TEST':
        sendEphemeralTest()


def main():
    __addon__.openSettings()


if __name__ == '__main__':
    try:
        args = None
        if len(sys.argv) > 1:
            args = sys.argv[1:]

        if args:
            handleArg(args[0])
        else:
            main()

    except:
        traceError()