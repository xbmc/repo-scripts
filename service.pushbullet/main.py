import lib.common
from lib import util

__addon__        = lib.common.__addon__
__addonpath__    = lib.common.__addonpath__
__addonid__      = lib.common.__addonid__

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

def loadTokenFromFile():
    import OAuthHelper
    
    token = OAuthHelper.getToken(__addonid__,from_file=True)
    if token: saveToken(token)

def deviceNameExists(client,name):
    from lib import pbclient
    try:
        for d in client.getDevicesList():
            if not d.get('active'): continue
            if name == d.get('nickname'): return True
        return False
    except pbclient.PushbulletException, e:
        showError(e.message)
        return None
    
def addNewDevice(client,device):
    import xbmcgui
    from lib import pbclient
    
    #TODO: Check for existing device nickname and handle    
    
    device.name = xbmcgui.Dialog().input('{0}:'.format(localise(32065)),device.name or localise(32066)) or device.name
    if not device.name: return False
    
    while deviceNameExists(client,device.name):
        device.name = xbmcgui.Dialog().input(localise(32067),device.name or '')
        if not device.name: return
        
    try:
        client.addDevice(device)
    except pbclient.PushbulletException, e:
        util.LOG('FAILED TO ADD DEVICE: {0}'.format(device.name))
        showError(e.message)
        return False
    return True

def linkDevice():
    import xbmcgui
    from lib import pbclient
    from lib import devices
    
    token = util.getSetting('pb_access_token')
    
    if not token:
        xbmcgui.Dialog().ok(localise(32068), localise(32069),localise(32070))
        return
        
    client = pbclient.Client(token)
    deviceMap = {}
    try:
        for d in client.getDevicesList():
            if not d.get('active'): continue
            deviceMap[d['iden']] = d['nickname']
    except pbclient.PushbulletException, e:
        showError(e.message)
        return
    
    idx = xbmcgui.Dialog().select(localise(32071),deviceMap.values() + [localise(32072)])
    if idx < 0: return
    
    dev = devices.KodiDevice(None,util.getSetting('pb_client_nickname') or None)
    if idx == len(deviceMap):
        if not addNewDevice(client,dev): return
    else:
        dev.ID = deviceMap.keys()[idx]
        dev.name = deviceMap.values()[idx] or dev.name
        
    util.setSetting('pb_client_iden',dev.ID)
    util.setSetting('pb_client_nickname',dev.name)
    util.LOG('DEVICE LINKED: {0}'.format(dev.name))
    xbmcgui.Dialog().ok(localise(32073), '{0}: '.format(localise(32074)), '  [B]{0}[/B]'.format(dev.name), localise(32075))

def renameDevice():
    import xbmcgui
    from lib import devices
    from lib import pbclient
    from lib import util
    
    dev = devices.getDefaultKodiDevice(util.getSetting('pb_client_iden'),util.getSetting('pb_client_nickname'))
    if not dev or not dev.ID:
        xbmcgui.Dialog().ok(localise(32076),localise(32077))
    name = xbmcgui.Dialog().input('{0}:'.format(localise(32078)),dev.name or '')
    if not name: return
    if name == dev.name: return
    
    token = util.getSetting('pb_access_token')
    
    client = pbclient.Client(token)
    
    while deviceNameExists(client,name):
        name = xbmcgui.Dialog().input(localise(32079),dev.name or '')
        if not name: return
        if name == dev.name: return

    if not token:
        xbmcgui.Dialog().ok(localise(32068),localise(32080),localise(32081))
        return
        
    try:
        if client.updateDevice(dev,nickname=name):
            util.setSetting('pb_client_nickname',dev.name)
            xbmcgui.Dialog().ok(localise(32062),'{0}: '.format(localise(32082)),'',dev.name)
            
    except pbclient.PushbulletException, e:
        showError(e.message)

def selectDevice():
    from lib import gui, pbclient

    token = util.getSetting('pb_access_token')

    client = pbclient.Client(token)

    ID = gui.selectDevice(client,extra=localise(32083))
    if ID == None: return
    util.setSetting('selected_device',ID)

def saveToken(token):
    util.setSetting('pb_access_token',token)

def authorize():
    import OAuthHelper
    
    token = OAuthHelper.getToken(__addonid__)
    if token:
        saveToken(token)
        if not util.getSetting('pb_client_iden'):
            linkDevice()

def handleArg(arg):
    if arg == 'SEND_EPHEMERAL_TEST':
        sendEphemeralTest()
    elif arg == 'LINK_DEVICE':
        linkDevice()
    elif arg == 'RENAME_DEVICE':
        renameDevice()
    elif arg == 'TOKEN_FROM_FILE':
        loadTokenFromFile()
    elif arg == 'SELECT_DEVICE':
        selectDevice()
    elif arg == 'AUTHORIZE':
        authorize()
    elif arg == 'MAP':
        from lib.maps import Maps
        Maps().doMap()

def main():
    if not util.getToken():
        import xbmcgui
        xbmcgui.Dialog().ok(localise(32084),localise(32085),localise(32086))
        util.ADDON.openSettings()
        return
        
    if not util.getSetting('pb_client_iden'):
        import xbmcgui
        xbmcgui.Dialog().ok(localise(32084),localise(32087),localise(32088),localise(32089))
        util.ADDON.openSettings()
        return

    from lib import gui
    gui.start()


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