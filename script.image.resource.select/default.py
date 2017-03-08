import sys, os
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json
from xml.dom.minidom import parseString
from operator import itemgetter

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD          = ADDON.getAddonInfo('path').decode('utf-8')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        TYPE, PROP = self._parse_argv()
        if TYPE and PROP:
            ITEMS = self._get_addons(TYPE)
            self._select(ITEMS, TYPE, PROP)

    def _parse_argv(self):
        TYPE = None
        try:
            params = dict(arg.split('=') for arg in sys.argv[ 1 ].split('&'))
        except:
            params = {}
        log('params: %s' % params)
        TYPE = params.get('type', '')
        PROP = params.get('property', '')
        return TYPE, PROP

    def _get_addons(self, TYPE):
        listitems = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"type": "kodi.resource.images", "properties": ["name", "summary", "thumbnail", "path"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('addons'):
            addons = json_response['result']['addons']
            for item in sorted(addons, key=itemgetter('name')):
                if item['addonid'].startswith(TYPE):
                    name = item['name']
                    icon = item['thumbnail']
                    addonid = item['addonid']
                    path = item['path']
                    summary = item['summary']
                    extension, subfolders = self._get_data(path)
                    listitem = xbmcgui.ListItem(label=name, label2=addonid, iconImage='DefaultAddonImages.png', thumbnailImage=icon)
                    listitem.setProperty('extension', extension)
                    listitem.setProperty('subfolders', subfolders)
                    listitem.setProperty('Addon.Summary', summary)
                    listitems.append(listitem)
        return listitems

    def _get_data(self, path):
        infoxml = os.path.join(path, 'info.xml')
        try:
            info = xbmcvfs.File(infoxml)
            data = info.read()
            info.close()
            xmldata = parseString(data)
            extension = xmldata.documentElement.getElementsByTagName('format')[0].childNodes[0].data
            subfolders = xmldata.documentElement.getElementsByTagName('subfolders')[0].childNodes[0].data
            return extension, subfolders
        except:
            return 'png', 'false'

    def _select(self, addonlist, category, string):
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(15109), iconImage='DefaultAddon.png')
        addonlist.insert(0, listitem)
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(21452))
        listitem.setProperty('more', 'true')
        addonlist.append(listitem)
        num = xbmcgui.Dialog().select(xbmc.getLocalizedString(424), addonlist, useDetails=True)
        if num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.name'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.path'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.ext'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.multi'))
        elif num > 0:
            item = addonlist[num]
            if item.getProperty('more') == 'true':
                xbmc.executebuiltin('ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/,return)')
            else:
                name = item.getLabel()
                addonid = item.getLabel2()
                extension = '.%s' % item.getProperty('extension')
                subfolders = item.getProperty('subfolders')
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.name'), name))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.path'), 'resource://%s/' % addonid))
                if subfolders == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % (string + '.multi'))
                    xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.ext'))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.multi'))
                    xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.ext'), extension))

if (__name__ == '__main__'):
    log('script version %s started' % ADDONVERSION)
    Main()
log('script stopped')
