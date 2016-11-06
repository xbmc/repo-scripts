# Credits to CF2009 for the original favourites script.

import os, sys, re
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from xml.dom.minidom import parse

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
LANGUAGE     = ADDON.getLocalizedString

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()
        found, favourites = self._read_file()
        if self.PROPERTY == '':
            self._set_properties(favourites)
        else:
            self._select(favourites)
        if found:
            self.doc.unlink()

    def _parse_argv(self):
        try:
            params = dict(arg.split("=") for arg in sys.argv[ 1 ].split("&"))
        except:
            params = {}
        log("### params: %s" % params)
        self.PROPERTY = params.get("property", "")
        self.CHANGETITLE = params.get("changetitle", "")
        self.PLAY = params.get("playlists", False)

    def _read_file(self):
        # Set path
        self.fav_file = xbmc.translatePath('special://profile/favourites.xml').decode("utf-8")
        # Check to see if file exists
        if xbmcvfs.exists(self.fav_file):
            found = True
            self.doc = parse(self.fav_file)
            favourites = self.doc.documentElement.getElementsByTagName('favourite')
        else:
            found = False
            favourites = []
        return found, favourites

    def _set_properties(self, listing):
        self.WINDOW = xbmcgui.Window(10000)
        oldcount = 0
        try:
            oldcount = int(self.WINDOW.getProperty("favourite.count"))
        except:
            pass
        for idx_count in range(1,oldcount + 1):
            self.WINDOW.clearProperty("favourite.%d.path" % (idx_count))
            self.WINDOW.clearProperty("favourite.%d.name" % (idx_count))
            self.WINDOW.clearProperty("favourite.%d.thumb" % (idx_count))
        self.WINDOW.setProperty("favourite.count", str(len(listing)))
        for count, favourite in enumerate(listing):
            name = favourite.attributes[ 'name' ].nodeValue
            path = favourite.childNodes [ 0 ].nodeValue
            if ('RunScript' not in path) and ('StartAndroidActivity' not in path) and ('pvr://' not in path) and (',return' not in path):
                path = path.rstrip(')')
                path = path + ',return)'
            if 'playlists/music' in path or 'playlists/video' in path:
                thumb = "DefaultPlaylist.png"
                if self.PLAY:
                    if 'playlists/music' in path:
                        path = path.replace('ActivateWindow(10502,', 'PlayMedia(')
                    else:
                        path = path.replace('ActivateWindow(10025,', 'PlayMedia(')
            else:
                try:
                    thumb = favourite.attributes[ 'thumb' ].nodeValue
                except:
                    thumb = "DefaultFolder.png"
            self.WINDOW.setProperty("favourite.%d.path" % (count + 1,) , path)
            self.WINDOW.setProperty("favourite.%d.name" % (count + 1,) , name)
            self.WINDOW.setProperty("favourite.%d.thumb" % (count + 1,) , thumb)

    def _select(self, items):
        listitems = []
        listitems.append(xbmcgui.ListItem(LANGUAGE(32001), iconImage="DefaultAddonNone.png"))
        for item in items:
            listitem = xbmcgui.ListItem(item.attributes[ 'name' ].nodeValue)
            fav_path = item.childNodes [ 0 ].nodeValue
            try:
                if 'playlists/music' in fav_path or 'playlists/video' in fav_path:
                    listitem.setIconImage("DefaultPlaylist.png")
                    listitem.setProperty("Icon", "DefaultPlaylist.png")
                else:
                    listitem.setIconImage(item.attributes[ 'thumb' ].nodeValue)
                    listitem.setProperty("Icon", item.attributes[ 'thumb' ].nodeValue)
            except:
                pass
            if ('RunScript' not in fav_path) and ('StartAndroidActivity' not in fav_path) and ('pvr://' not in fav_path) and (',return' not in fav_path):
                fav_path = fav_path.rstrip(')')
                fav_path = fav_path + ',return)'
            listitem.setProperty("Path", fav_path)
            listitems.append(listitem)
        # add a dummy item with no action assigned
        listitem = xbmcgui.ListItem(LANGUAGE(32002))
        listitem.setProperty("Path", 'noop')
        listitems.append(listitem)
        num = xbmcgui.Dialog().select(xbmc.getLocalizedString(1036), listitems, useDetails=True)
        if num > 0:
            fav_path = listitems[num].getProperty("Path")
            result = re.search('"(.*?)"', fav_path)
            if result:
                fav_abspath = result.group(0)
            else:
                fav_abspath = ''
            fav_label = listitems[num].getLabel()
            if 'playlists/music' in fav_path or 'playlists/video' in fav_path:
                retBool = xbmcgui.Dialog().yesno(xbmc.getLocalizedString(559), LANGUAGE(32000))
                if retBool:
                    if 'playlists/music' in fav_path:
                        fav_path = fav_path.replace('ActivateWindow(10502,', 'PlayMedia(')
                    else:
                        fav_path = fav_path.replace('ActivateWindow(10025,', 'PlayMedia(')
            if self.CHANGETITLE == "true":
                keyboard = xbmc.Keyboard(fav_label, xbmc.getLocalizedString(528), False)
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    fav_label = keyboard.getText()
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, "Path",), fav_path.decode('string-escape'),))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, "List",), fav_abspath.decode('string-escape'),))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, "Label",), fav_label,))
            fav_icon = listitems[num].getProperty("Icon")
            if fav_icon:
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ('%s.%s' % (self.PROPERTY, "Icon",), fav_icon,))
        elif num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, "Path",))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, "List",))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, "Label",))
            xbmc.executebuiltin('Skin.Reset(%s)' % '%s.%s' % (self.PROPERTY, "Icon",))

if (__name__ == "__main__"):
    log('script version %s started' % ADDONVERSION)
    Main()
log('script stopped')
