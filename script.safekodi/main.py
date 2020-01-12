import sys
import os
import xbmcaddon
import xbmcplugin
from urllib import urlencode
import xbmcgui
import xbmc
import requests
try:
    import json
except:
    import simplejson as json
import uuid

from urlparse import parse_qsl
 
ADDON       = xbmcaddon.Addon()
CWD = ADDON.getAddonInfo('path').decode('utf-8')
#addonname   = ADDON.getAddonInfo('name')
#SKIN = ADDON.getSetting('skin')

addon_url = sys.argv[0]
addon_handle = int(sys.argv[1])

def get_addon(addonid):
    resp = requests.get(
        "https://safekodi.com:5555/checkAddon",
        params={
            "addon": addonid
        }
    )
    return resp


def post_addon(addon_list, user_setting):
    payload = {"uid": uuid.getnode(), "addon_list":addon_list, "user_setting": user_setting}
    resp = requests.post(
        "https://safekodi.com:5555/addonList",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    return resp


SETTING_ID_TO_COLLECT = []
EXTRA_SETTINGS = [
    'network.usehttpproxy', 
    'network.httpproxytype', 
    'addons.unknownsources',
    'network.bandwidth', 
    'general.addonupdates',
    'locale.language',
    'locale.audiolanguage',
    'locale.subtitlelanguage',
    'services.webserver'
]
def get_setting(extra=True):
    json_cmd = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Settings.GetSettings',
        'params': {
            'level': 'expert'
        }
    }
    res = json.loads(xbmc.executeJSONRPC(json.dumps(json_cmd)))
    try:
        res = res['result']['settings']
        ret = []
        for r in res:
            if r['id'] in SETTING_ID_TO_COLLECT:
                ret.append(r)
            if extra and r['id'] in EXTRA_SETTINGS:
                ret.append(r)
        return ret
    except:
        return res


def get_skin():
    json_cmd = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Settings.GetSettingValue',
        'params': {
            'setting': 'lookandfeel.skin'
        }
    }
    res = json.loads(xbmc.executeJSONRPC(json.dumps(json_cmd)))
    try:
        return res['result']['value']
    except:
        return ''


def set_skin_default():
    json_cmd = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Settings.SetSettingValue',
        'params': {
            'setting': 'lookandfeel.skin',
            'value': 'skin.estuary'
        }
    }
    xbmc.executeJSONRPC(json.dumps(json_cmd))


def get_installed_addons_info():
    json_cmd = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Addons.GetAddons',
        'params': {
            'installed': True,
            'properties': ['dependencies', 'version','extrainfo', 'disclaimer','name','path','rating','summary','description', 'author', 'enabled']
        }
    }
    res = json.loads(xbmc.executeJSONRPC(json.dumps(json_cmd)))
    try:
        return res['result']['addons']
    except:
        return res


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.
    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(addon_url, urlencode(kwargs))


def list_categories(categories, addon_list):
    """
    Create the list of addons in the Kodi interface.
    """
    # Iterate through categories
    for aid in categories.keys():
        addon_msg, mark = 'Oops...\nAddon not in our database. \nPlease come back later\n', 'unknown.png'
        try:
            if 'OK' in categories[aid]:
                addon_status = json.loads('[' + categories[aid].split('[')[1].split(']')[0] + ']')
                addon_msg = ''
                if len(addon_status) == 0:
                    addon_msg = 'This addon is safe!\n'
                    mark = 'safe.png'
                if 'kodi' in addon_status:
                    addon_msg = 'This is a Kodi official addon!\n'
                    mark = 'safe.png'
                if 'ad' in addon_status:
                    addon_msg += 'This addon may contain some ads.\n'
                    mark = 'warning.png'
                if 'track' in addon_status:
                    addon_msg += 'This addon may contain some tracking links which lead to privacy leakage.\n'
                    mark = 'warning.png'
                if 'threat' in addon_status:
                    addon_msg += 'This addon may lead to some malacious URLs!\n'
                    mark = 'danger.png'
                if 'ipban' in addon_status:
                    addon_msg += 'This addon may communicate with malacious servers!\n'
                    mark = 'danger.png'
                if 'ban' in addon_status:
                    addon_msg += 'This addon is banned by the Kodi official!\n'
                    mark = 'danger.png'
                # TODO: delete this, just for debug
                #addon_msg += aid + ', ' + str(addon_status)
            elif 'Connection errror!' in categories[aid]:
                addon_msg, mark = 'Oops...\nConnection error! \nPlease check your network configurations.\n', 'unknown.png'
            else:
                pass
            addon_msg += '\n\n' + 'Addon description:\n' + addon_list[aid]['description']
        except Exception as e:
            print(e)
            addon_msg = 'Error!\n' + str(addon_status) + '\n' + str(e)
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=addon_list[aid]['name'], label2=addon_msg)
        infolabels = { "title": addon_list[aid]['name'], "mpaa": addon_msg, "Plot": addon_msg }
        list_item.setInfo( type="Video", infoLabels=infolabels )
        image_path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', mark)
        list_item.setArt({
            'thumb': image_path, 
            'icon': image_path, 
            'fanart': image_path, 
        })
        url = get_url(action='disable', aid=aid, name=addon_list[aid]['name'], mark=mark)
        is_folder = False
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(addon_handle, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_SIZE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_GENRE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_STUDIO)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_PROGRAM_COUNT)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(addon_handle)


def disable_addon(aid, name, mark):
    yes = False
    if mark == 'safe.png':
        yes = xbmcgui.Dialog().yesno(
            heading='Disable Addon',
            line1='''
            Addon %s is safe according to the Safekodi database. It is not neccessary to disable this addon. 
            Do you want to disable this addon anyway?' 
            ''' % name
        )
    elif mark == 'unknown.png':
        yes = xbmcgui.Dialog().yesno(
            heading='Disable Addon',
            line1='''
            The safety of addon %s has not been identified yet. 
            Do you want to disable this addon?' 
            ''' % name
        )
    else:
        yes = xbmcgui.Dialog().yesno(
            heading='Disable Addon',
            line1='''
            Addon %s is not safe according to our test. Disable or unistall the addon would be recommended.
            Do you want to disable this addon?' 
            ''' % name
        )

    if yes:
        json_cmd = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.SetAddonEnabled',
            'params': {
                'addonid': aid,
                'enabled': False
                }
            }
        res = json.loads(xbmc.executeJSONRPC(json.dumps(json_cmd)))
        if 'result' in res and res['result'] == 'OK':
            xbmcgui.Dialog().ok('Success', 'Addon %s has been disabled.' % (name))
        else:
            xbmcgui.Dialog().ok('Failed', 'Addon %s has not been disabled.\n%s' % (name, str(res)))
        post_addon([aid], {'action': 'disable addon'})
        
        

def entry():
    skin = get_skin()
    xbmc.log(str(skin), xbmc.LOGNOTICE)
    if skin != 'skin.estuary':
        switch = xbmcgui.Dialog().yesno(
            heading='Switch skin',
            line1='SafeKodi would work better with the default skin Estuary. But current skin setting is %s. Would you like to switch to the default skin?' % str(skin)
        )
        if switch:
            set_skin_default()

    extra = xbmcgui.Dialog().yesno(
        heading='Would you like to participate in our study?', 
        line1='''
        We\'re trying to understand the ecosystem of Kodi. Would you like to share with us some of your Kodi system settings? Please be assured that the settings will be submitted anonymously and no personal data will be included.\n\n
        Hi, We\'re a research group in the Northwestern University. We\'re currently conducting a research regarding the Kodi usage, and we need your help! we would appreciate a lot if you would like to share with us some of your Kodi settings. More specifically, if 'Yes' is selected, the following settings will be sent anonymously: 
        if http proxy is enabled,
        the type of http proxy,
        if network bandwidth is limited,
        if installations from unknown sources are allowed,
        if auto updates for addons are enabled,
        interface language,
        preferred audio language,
        preferre subtitle language,
        if remote control is enabled.
        Thank you for your participation!
        ''',
        nolabel='No', yeslabel="Yes"#, autoclose=15000
    )

    user_setting = get_setting(extra)
    xbmc.log(str(user_setting), xbmc.LOGDEBUG)

    addon_list = get_installed_addons_info()
    xbmc.log(str(addon_list), xbmc.LOGDEBUG)

    # report to safekodi
    try:
        resp = post_addon(addon_list, user_setting)
    except Exception as e: 
        xbmc.log(str(e), xbmc.LOGDEBUG)

    # get the addon status from safekodi
    addon_status = {}
    addon_info = {}
    for addon in addon_list:
        try:
            resp = get_addon(addon['addonid'])
            addon_status[addon['addonid']] = resp.content
        except requests.ConnectionError:
            addon_status[addon['addonid']] = 'Connection errror!'

        addon_info[addon['addonid']] = {
            'name': addon['name'],
            'description': addon['description']
        }

    list_categories(addon_status, addon_info)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'disable':
            disable_addon(params['aid'], params['name'], params['mark'])
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        entry()


if __name__ == "__main__":
    router(sys.argv[2][1:])
