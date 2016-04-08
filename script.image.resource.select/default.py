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
        w = Gui('DialogSelect.xml', CWD, listing=addonlist, category=category, string=string)
        w.doModal()
        del w

class Gui(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get('listing')
        self.type = kwargs.get('category')
        self.property = kwargs.get('string')

    def onInit(self):
        self.container = self.getControl(6)
        self.button = self.getControl(5)
        self.cancel = self.getControl(7)
        self.getControl(3).setVisible(False)
        self.getControl(1).setLabel(xbmc.getLocalizedString(20464) % xbmc.getLocalizedString(536))
        self.button.setLabel(xbmc.getLocalizedString(21452))
        self.cancel.setLabel(xbmc.getLocalizedString(222))
        listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(15109), iconImage='DefaultAddon.png')
        self.container.addItem(listitem)
        self.container.addItems(self.listing)
        self.setFocus(self.container)

    def onAction(self, action):
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448,):
            self.close()

    def onClick(self, controlID):
        if controlID == 6:
            num = self.container.getSelectedPosition()
            if num == 0:
                xbmc.executebuiltin('Skin.Reset(%s)' % (self.property + '.name'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (self.property + '.path'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (self.property + '.ext'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (self.property + '.multi'))
            else:
                item = self.container.getSelectedItem()
                name = item.getLabel()
                addonid = item.getLabel2()
                extension = '.%s' % item.getProperty('extension')
                subfolders = item.getProperty('subfolders')
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.property + '.name'), name))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.property + '.path'), 'resource://%s/' % addonid))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((self.property + '.ext'), extension))
                if subfolders == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % (self.property + '.multi'))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % (self.property + '.multi'))
            xbmc.sleep(100)
            self.close()
        elif controlID == 5:
            xbmc.executebuiltin('ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/,return)')
            xbmc.sleep(100)
            self.close()
        elif controlID == 7:
            self.close()

    def onFocus(self, controlID):
        pass


if (__name__ == '__main__'):
    log('script version %s started' % ADDONVERSION)
    Main()
log('script stopped')
