import xbmc
import xbmcgui
import xbmcaddon
import json
import platform
import re

# Constants

def STRING():
    return 0

def BOOL():
    return 1

def NUM():
    return 2

def writeLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (xbmcaddon.Addon().getAddonInfo('id'), message.encode('utf-8')), level)


class Notify(object):

    def __init__(self):
        self.prev_header = ''
        self.prev_message = ''

    def notify(self, header, message, icon=xbmcgui.NOTIFICATION_INFO, dispTime=5000, repeat=False):
        if repeat or (header != self.prev_header or message != self.prev_message):
            xbmcgui.Dialog().notification(header.encode('utf-8'), message.encode('utf-8'), icon, dispTime)
        else:
            writeLog('Message content is same as before, don\'t show notification')
        self.prev_header = header
        self.prev_message = message


class release(object):

    def __init__(self):
        self.platform = platform.system()
        self.hostname = platform.node()
        if self.platform == 'Linux':
            with open('/etc/os-release', 'r') as _file:
                item = {}
                for _line in _file:
                    parameter, value = _line.split('=')
                    item[parameter] = value

        self.osname = item.get('NAME')
        self.osid = item.get('ID')
        self.osversion = item.get('VERSION_ID')

def dialogOK(header, message):
    xbmcgui.Dialog().ok(header.encode('utf-8'), message.encode('utf-8'))

def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))

def getAddonSetting(setting, sType=STRING, multiplicator=1):
    if sType == BOOL:
        _ret =  True if xbmcaddon.Addon().getSetting(setting).upper() == 'TRUE' else False
    elif sType == NUM:
        try:
            _ret = int(re.match('\d+', xbmcaddon.Addon().getSetting(setting)).group()) * multiplicator
        except AttributeError:
            _ret = 0
    else:
        _ret = xbmcaddon.Addon().getSetting(setting)
    # writeLog('Load setting %s [%s]: %s' % (setting, re.compile("<type '(.+?)'>", re.DOTALL).findall(str(type(_ret)))[0], _ret))
    return _ret
