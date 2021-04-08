import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import os
import sys
import requests
import json

addon_handle = int(sys.argv[1])
xbmcplugin.setContent(addon_handle, 'videos')
addonID = 'script.domoticz.scenes'
addonVersion = '0.0.8'
addonDate = "24 Maart 2021"

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')

LIB_DIR = xbmc.translatePath(os.path.join(xbmcaddon.Addon(id=addonID).getAddonInfo('path'), 'resources', 'lib'))
sys.path.append(LIB_DIR)

# Get plugin settings
DEBUG = xbmcaddon.Addon(id=addonID).getSetting('debug')

if (DEBUG) == 'true':
    xbmc.log("[ADDON] %s v%s (%s) is starting, ARGV = %s" % (addonID, addonVersion, addonDate, repr(sys.argv)),
             xbmc.LOGINFO)

domoticz_host = xbmcaddon.Addon(id=addonID).getSetting('domoticz_host')
domoticz_user = xbmcaddon.Addon(id=addonID).getSetting('domoticz_user')
domoticz_pass = xbmcaddon.Addon(id=addonID).getSetting('domoticz_pass')
domoticz_port = xbmcaddon.Addon(id=addonID).getSetting('domoticz_port')
domoticz_group = xbmcaddon.Addon(id=addonID).getSetting('group')

win = xbmcgui.Window()
width = win.getWidth()
height = win.getHeight()

screenheight = xbmcgui.getScreenHeight()
screenwidth = xbmcgui.getScreenWidth()
windowId = xbmcgui.getCurrentWindowId()
dialogId = xbmcgui.getCurrentWindowDialogId()


def get_params():
    param = {}
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


params = get_params()


def show_notification(msg):
    xbmc.executebuiltin('Notification(' + __addonname__ + ',' + msg + ',5000,' + __icon__ + ')')


def get_scenes(host, port, useSsl, username=None, password=None):
    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    if useSsl == True:
        protocol = 'https://'
    else:
        protocol = 'http://'
    url = protocol + host + ':' + str(port) + '/json.htm?' + setcreds + 'type=scenes'
    try:
        result = requests.get(url)
    except:
        return -1

    answer = result.content

    jsonResult = json.loads(answer)
    deviceResult = jsonResult['result']
    return(deviceResult)


def get_favorite_devices_dict(host, port, useSsl, username=None, password=None):
    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    if useSsl == True:
        protocol = 'https://'
    else:
        protocol = 'http://'
    url = protocol + host + ':' + str(port) + '/json.htm?' + setcreds + 'type=devices&used=true&filter=all&favorite=1'
    try:
        result = requests.get(url)
    except:
        return -1

    answer = result.content

    jsonResult = json.loads(answer)
    deviceResult = jsonResult['result']
    return(deviceResult)


def get_all_devices_dict(host, port, useSsl, username=None, password=None):
    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    if useSsl == True:
        protocol = 'https://'
    else:
        protocol = 'http://'

    url = protocol + host + ':' + str(port) + '/json.htm?' + setcreds + 'type=devices&used=true&displayhidden=1'
    try:
        result = requests.get(url)
    except:
        return -1

    answer = result.content

    jsonResult = json.loads(answer)
    deviceResult = jsonResult['result']

    return(deviceResult)


def get_version(host, port, useSsl, verifySsl, username=None, password=None):
    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    if useSsl == True:
        protocol = 'https://'
    else:
        protocol = 'http://'

    url = protocol + host + ':' + str(port) + '/json.htm?' + setcreds + 'type=command&param=getversion'
    try:
        result = requests.get(url, verify=verifySsl)
    except:
        return -1

    answer = result.content
    jsonResult = json.loads(answer)
    return(jsonResult)


def get_all_switches(host, port, useSsl, username=None, password=None):
    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    if useSsl == True:
        protocol = 'https://'
    else:
        protocol = 'http://'
    url = protocol + host + ':' + str(port) + '/json.htm?' + setcreds + 'type=devices&filter=light&used=true&order=Name'

    try:
        result = requests.get(url)
    except:
        return -1

    answer = result.content

    jsonResult = json.loads(answer)
    deviceResult = jsonResult['result']
    return(deviceResult)


def switch_scene(host, port, idx, useSsl=False, username=None, password=None):
    if useSsl is True:
        base_url = "https://" + host + ":" + str(port)
    else:
        base_url = "http://" + host + ":" + str(port)

    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    url = base_url + "/json.htm?" + setcreds + "type=command&param=switchscene&idx=" + str(idx) + "&switchcmd=On"
    f = open(r"c:\tmp\debug.txt", "a")
    f.write(url + "\n")
    f.close()
    requests.get(url=url)


def switch_switch(host, port, idx, useSsl=False, username=None, password=None):
    if useSsl is True:
        base_url = "https://" + host + ":" + str(port)
    else:
        base_url = "http://" + host + ":" + str(port)

    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    url = base_url + "/json.htm?" + setcreds + "type=command&param=switchlight&idx=" + str(idx) + "&switchcmd=Toggle"
    f = open(r"c:\tmp\debug.txt", "a")
    f.write(url + "\n")
    f.close()
    requests.get(url=url)


def switch_dimmer(host, port, idx, state, useSsl=False, username=None, password=None):
    if useSsl is True:
        base_url = "https://" + host + ":" + str(port)
    else:
        base_url = "http://" + host + ":" + str(port)

    if username is not None:
        setcreds = 'username=' + username + '&password=' + password + '&'
    else:
        setcreds = ''

    url = base_url + "/json.htm?" + setcreds + "type=command&param=switchlight&idx=" + str(idx) + "&switchcmd=Set%20Level&level=" + state
    f = open(r"c:\tmp\debug.txt", "a")
    f.write(url + "\n")
    f.close()
    requests.get(url=url)


def get_list(optionsDict):
    optionsList = []
    for line in optionsDict:
        optionsList.append(line['Name'])
    optionsList.append("------End of list------")
    return optionsList


if str(domoticz_group) == '0':
    optionsDict = get_scenes(host=domoticz_host, port=domoticz_port, useSsl=False)
    optionsList = get_list(optionsDict=optionsDict)

elif str(domoticz_group) == '1':
    optionsDict = get_all_switches(host=domoticz_host, port=domoticz_port, useSsl=False)
    optionsList = get_list(optionsDict=optionsDict)

elif str(domoticz_group) == '2':
    optionsDict = get_favorite_devices_dict(host=domoticz_host, port=domoticz_port, useSsl=False)
    optionsList = get_list(optionsDict=optionsDict)

else:
    show_notification("Unknown grouping. Using all switches in stead")
    optionsDict = get_all_switches(host=domoticz_host, port=domoticz_port, useSsl=False)
    optionsList = get_list(optionsDict=optionsDict)


answer = xbmcgui.Dialog().select(heading="Domoticz Scenes in Kodi", list=optionsList)
action = optionsList[answer]


def get_idx(optionsDict, action):
    for line in optionsDict:
        Name = line['Name']
        if Name == action:
            idx = line['idx']
            return idx


def get_favorites_idx(optionsDict, action):
    for line in optionsDict:
        Name = line['Name']
        if Name == action:
            idx = line['idx']
            type = line['Type']
            return idx, type


if action != "------End of list------":
    if str(domoticz_group) == '0':
        idx = get_idx(optionsDict=optionsDict, action=action)
        switch_scene(host=domoticz_host, port=domoticz_port, idx=idx, useSsl=False)
    elif str(domoticz_group) == '1':
        idx = get_idx(optionsDict=optionsDict, action=action)
        switch_switch(host=domoticz_host, port=domoticz_port, idx=idx, useSsl=False)
    elif str(domoticz_group) == '2':
        idx, type = get_favorites_idx(optionsDict=optionsDict, action=action)
        if type == 'Scene':
            switch_scene(host=domoticz_host, port=domoticz_port, idx=idx, useSsl=False)
        if type == 'Light/Switch':
            switch_switch(host=domoticz_host, port=domoticz_port, idx=idx)
        if type == 'Color Switch':
            switch_switch(host=domoticz_host, port=domoticz_port, idx=idx)
    else:
        idx = get_idx(optionsDict=optionsDict, action=action)
        switch_switch(host=domoticz_host, port=domoticz_port, idx=idx, useSsl=False)
