import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import sys
import requests
from requests.auth import HTTPBasicAuth
import json

addon_handle = int(sys.argv[1])
xbmcplugin.setContent(addon_handle, 'videos')
addonID = 'script.domoticz.scenes'
addonVersion = '0.0.21'
addonDate = "26/10/2023"

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
__language__ = xbmcaddon.Addon().getLocalizedString

# Get plugin settings
DEBUG = xbmcaddon.Addon(id=addonID).getSetting('debug')

if (DEBUG) == 'true':
    xbmc.log("[ADDON] %s v%s (%s) is starting, ARGV = %s" % (addonID, addonVersion, addonDate, repr(sys.argv)),
             xbmc.LOGINFO)

domoticz_host = xbmcaddon.Addon(id=addonID).getSetting('domoticz_host')
domoticz_user = xbmcaddon.Addon(id=addonID).getSetting('domoticz_user')
domoticz_pass = xbmcaddon.Addon(id=addonID).getSetting('domoticz_pass')
domoticz_port = xbmcaddon.Addon(id=addonID).getSetting('domoticz_port')
domoticz_ssl = xbmcaddon.Addon(id=addonID).getSetting('SSL')
domoticz_ignore_ssl = xbmcaddon.Addon(id=addonID).getSetting('ignore_SSL')
domoticz_group = xbmcaddon.Addon(id=addonID).getSetting('group')


def domoticz_submit(query):
    server = domoticz_host
    port = domoticz_port
    usr = domoticz_user
    pwd = domoticz_pass
    ssl = domoticz_ssl
    server = server.replace("http://", "")
    server = server.replace("https://", "")

    if ssl == "true":
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + server + ":" + str(port) + "/json.htm?" + query

    if domoticz_ignore_ssl == "true":
        requests.packages.urllib3.disable_warnings()
        if not usr and not pwd:
            r = requests.get(url=url, verify=False)
        else:
            r = requests.get(url=url, auth=(usr, pwd), verify=False)
    else:
        if not usr and not pwd:
            r = requests.get(url=url, verify=True)
        else:
            r = requests.get(url=url, auth=(usr, pwd), verify=False)

    if r.status_code == 200:
        result = r.text
        data = json.loads(result)
        return data


def domoticz_get_version():
    query = "type=command&param=getversion"
    r = domoticz_submit(query=query)
    return r


def domoticz_scenes_and_groups():
    domoticz_version = domoticz_get_version()
    if domoticz_version['Revision'] > 15453 or domoticz_version['version'] == "2023.2 (build 15457)":
        query = "type=command&param=getscenes"
    else:
        query = 'type=scenes'

    r = domoticz_submit(query=query)

    devices = r['result']
    scenes_and_groups = []
    groups_list = []
    scenes_list = []
    for dev in devices:
        scenes_and_groups.append(dev)
        if dev['Type'] == "Group":
            groups_list.append(dev)
        elif dev['Type'] == "Scene":
            scenes_list.append(dev)

    data = {"Groups": {"result": groups_list}, "Scenes": {"result": scenes_list}, "Groups and Scenes": {"result": scenes_and_groups}}
    return data


def domoticz_favorites():
    domoticz_version = domoticz_get_version()
    if domoticz_version['Revision'] > 15453 or domoticz_version['version'] == "2023.2 (build 15457)":
        query = "type=command&param=getdevices&used=true&filter=all&favorite=1"
    else:
        query = 'type=devices&used=true&filter=all&favorite=1'
    r = domoticz_submit(query=query)
    return r


def domoticz_light_switches():
    domoticz_version = domoticz_get_version()
    if domoticz_version['Revision'] > 15453 or domoticz_version['version'] == "2023.2 (build 15457)":
        query = "type=command&param=getdevices&filter=light&used=true&order=Name"
    else:
        query = 'type=devices&filter=light&used=true&order=Name'
    r = domoticz_submit(query=query)
    return r


def domoticz_start_scene(idx):
    query = "type=command&param=switchscene&idx=" + str(idx) + "&switchcmd=On"
    r = domoticz_submit(query=query)
    return r


def domoticz_toggle_group(idx):
    query = "type=command&param=switchscene&idx=" + str(idx) + "&switchcmd=Toggle"
    r = domoticz_submit(query=query)
    return r


def domoticz_toggle_switch(idx):
    query = "type=command&param=switchlight&idx=" + str(idx) + "&switchcmd=Toggle"
    r = domoticz_submit(query=query)
    return r


def create_optionsList(optionsDict):
    optionsList = []
    for line in optionsDict:
        optionsList.append(line['Name'])
    return optionsList


def get_idx(optionsDict, action):
    for line in optionsDict['result']:
        Name = line['Name']
        if Name == action:
            idx = line['idx']
            return idx


def get_group_scene_idx_type(optionsDict, action):
    for dev in optionsDict['result']:
        if dev['Name'] == action:
            if "Type" in dev:
                return dev['idx'], dev['Type']


def get_favorites_idx(optionsDict, action):
    for line in optionsDict['result']:
        Name = line['Name']
        if Name == action:
            idx = line['idx']
            type = line['Type']
            return idx, type


def create_optionsDict():
    if str(domoticz_group) == '0':
        data = domoticz_scenes_and_groups()
        optionsDict = data["Groups and Scenes"]
        optionsList = create_optionsList(optionsDict=optionsDict['result'])

    elif str(domoticz_group) == '1':
        optionsDict = domoticz_light_switches()
        optionsList = create_optionsList(optionsDict=optionsDict['result'])

    elif str(domoticz_group) == '2':
        optionsDict = domoticz_favorites()
        optionsList = create_optionsList(optionsDict=optionsDict['result'])

    else:
        optionsDict = domoticz_light_switches()
        optionsList = create_optionsList(optionsDict=optionsDict['result'])

    return optionsDict, optionsList


title = __addon__.getLocalizedString(30498)

domoticz_version = domoticz_get_version()
optionsDict, optionsList = create_optionsDict()

answer = xbmcgui.Dialog().select(heading=title, list=optionsList)
action = optionsList[answer]


def run():
    if action in optionsList:
        if str(domoticz_group) == '0':
            idx, groupType = get_group_scene_idx_type(optionsDict=optionsDict, action=action)
            if groupType == "Scene":
                domoticz_start_scene(idx=idx)
            if groupType == "Group":
                domoticz_toggle_group(idx=idx)
        elif str(domoticz_group) == '1':
            idx = get_idx(optionsDict=optionsDict, action=action)
            domoticz_toggle_switch(idx=idx)
        elif str(domoticz_group) == '2':
            idx, type = get_favorites_idx(optionsDict=optionsDict, action=action)
            if type == 'Scene':
                domoticz_start_scene(idx=idx)
            if type == 'Group':
                domoticz_toggle_group(idx=idx)
            if type == 'Light/Switch':
                domoticz_toggle_switch(idx=idx)
            if type == 'Color Switch':
                domoticz_toggle_switch(idx=idx)
        else:
            idx = get_idx(optionsDict=optionsDict, action=action)
            domoticz_toggle_switch(idx=idx)




