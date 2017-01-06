import xbmc
import xbmcgui
import xbmcaddon
import inspect
import json

addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
language = addonSettings.getLocalizedString


def logMsg(title, msg, level=1):
    logLevel = int(addonSettings.getSetting("logLevel"))
    WINDOW = xbmcgui.Window(10000)
    WINDOW.setProperty('logLevel', str(logLevel))
    if logLevel >= level:
        if logLevel == 2:  # inspect.stack() is expensive
            try:
                xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg),level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')),level=xbmc.LOGNOTICE)
        else:
            try:
                xbmc.log(title + " -> " + str(msg),level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(title + " -> " + str(msg.encode('utf-8')),level=xbmc.LOGNOTICE)

def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, try_encode(params)))
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        jsonobject = jsonobject['result']
        if jsonobject.has_key('movies'):
            return jsonobject['movies']
        elif jsonobject.has_key('tvshows'):
            return jsonobject['tvshows']
        elif jsonobject.has_key('episodes'):
            return jsonobject['episodes']

def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding,"ignore")
    except:
        return text

def try_decode(text, encoding="utf-8"):
    try:
        return text.decode(encoding,"ignore")
    except:
        return text
