import sys
import json
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE = ADDON.getLocalizedString

def log(txt):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class MAIN():
    def __init__(self, *args, **kwargs):
        log('script version %s started' % ADDONVERSION)
        params = kwargs['params']
        self._parse_argv(params)
        favourites = self._get_favs()
        if favourites:
            if self.PROPERTY == '':
                self._set_properties(favourites)
            else:
                self._select_favourite(favourites)
        log('script stopped')

    def _parse_argv(self, params):
        try:
            params = dict(arg.split('=') for arg in params[1].split('&'))
        except:
            params = {}
        log('params: %s' % params)
        self.PROPERTY = params.get('property', '')
        self.CHANGETITLE = params.get('changetitle', '')
        self.PLAY = params.get('playlists', False)

    def _get_favs(self):
        data = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.GetFavourites", "params":{"properties":["window", "windowparameter", "thumbnail", "path"]}, "id":1}')
        favs = json.loads(data)
        if 'result' in favs:
            return favs['result']['favourites']

    def _set_properties(self, listing):
        self.WINDOW = xbmcgui.Window(10000)
        oldcount = 0
        try:
            oldcount = int(self.WINDOW.getProperty('favourite.count'))
        except:
            pass
        for idx_count in range(1,oldcount + 1):
            self.WINDOW.clearProperty('favourite.%d.path' % (idx_count))
            self.WINDOW.clearProperty('favourite.%d.name' % (idx_count))
            self.WINDOW.clearProperty('favourite.%d.thumb' % (idx_count))
        self.WINDOW.setProperty('favourite.count', str(len(listing)))
        for count, item in enumerate(listing):
            name = item['title']
            ftype = item['type']
            thumb = item['thumbnail']
            if item['type'] == 'media':
                path = 'PlayMedia("%s")' % item['path']
            elif item['type'] == 'window':
                path = 'ActivateWindow(%s,"%s",return)' % (item['window'], item['windowparameter'])
            elif item['type'] == 'script':
                path = 'RunScript("%s")' % item['path']
            elif item['type'] == 'androidapp':
                path = 'StartAndroidActivity("%s")' % item['path']
            else:
                continue
            if 'playlists/music' in path or 'playlists/video' in path:
                thumb = 'DefaultPlaylist.png'
                if self.PLAY:
                    path = 'PlayMedia("%s")' % item['path']
            self.WINDOW.setProperty('favourite.%d.path' % (count + 1,) , path)
            self.WINDOW.setProperty('favourite.%d.name' % (count + 1,) , name)
            self.WINDOW.setProperty('favourite.%d.thumb' % (count + 1,) , thumb)

    def _select_favourite(self, items):
        listitems = []
        clear = xbmcgui.ListItem(LANGUAGE(32001))
        clear.setArt({'icon':'DefaultAddonNone.png'})
        listitems.append(clear)
        for item in items:
            listitem = xbmcgui.ListItem(item['title'])
            if item['type'] == 'media':
                path = 'PlayMedia("%s")' % item['path']
            elif item['type'] == 'window':
                path = 'ActivateWindow(%s,"%s",return)' % (item['window'], item['windowparameter'])
            elif item['type'] == 'script':
                path = 'RunScript("%s")' % item['path']
            elif item['type'] == 'androidapp':
                path = 'StartAndroidActivity("%s")' % item['path']
            else:
                continue
            if 'playlists/music' in path or 'playlists/video' in path:
                listitem.setArt({'icon':'DefaultPlaylist.png'})
                listitem.setProperty('Icon', 'DefaultPlaylist.png')
            else:
                listitem.setArt({'icon': item['thumbnail']})
                listitem.setProperty('Icon', item['thumbnail'])
            listitem.setProperty('Path', path)
            if item['type'] == 'window':
                listitem.setProperty('AbsPath', item['windowparameter'])
            else:
                listitem.setProperty('AbsPath', item['path'])
            listitem.setProperty('Type', item['type'])
            listitems.append(listitem)
        # add a dummy item with no action assigned
        listitem = xbmcgui.ListItem(LANGUAGE(32002))
        listitem.setProperty('Path', 'noop')
        listitems.append(listitem)
        num = xbmcgui.Dialog().select(xbmc.getLocalizedString(1036), listitems, useDetails=True)
        if num > 0:
            fav_path = listitems[num].getProperty('Path')
            fav_label = listitems[num].getLabel()
            fav_abspath = listitems[num].getProperty('AbsPath')
            fav_icon = listitems[num].getProperty('Icon')
            fav_type = listitems[num].getProperty('Type')
            # by default, playlists are opened not played
            if fav_type == 'window' and 'playlists/music' in fav_abspath or 'playlists/video' in fav_abspath:
                retBool = xbmcgui.Dialog().yesno(xbmc.getLocalizedString(559), LANGUAGE(32000))
                if retBool:
                    fav_path = 'PlayMedia("%s")' % fav_abspath
            if self.CHANGETITLE == 'true':
                keyboard = xbmc.Keyboard(fav_label, xbmc.getLocalizedString(528), False)
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    fav_label = keyboard.getText()
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, 'Path',), fav_path,))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, 'List',), fav_abspath,))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, 'Label',), fav_label,))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, 'Icon',), fav_icon,))
        elif num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, 'Path',))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, 'List',))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, 'Label',))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, 'Icon',))
