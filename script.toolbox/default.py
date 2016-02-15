import sys
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.Utils import *

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_LANGUAGE = ADDON.getLocalizedString
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
EXTRAFANART_LIMIT = 4
EXTRATHUMB_LIMIT = 4
HOME = xbmcgui.Window(10000)


class Main:

    def __init__(self):
        log("version %s started" % ADDON_VERSION)
        xbmc.executebuiltin('SetProperty(toolbox_running,True,home)')
        self._init_vars()
        self._parse_argv()
        if self.infos:
            self.StartInfoActions(self.infos, self.params)
        elif not len(sys.argv) > 1:
            self.selection_dialog()
        xbmc.executebuiltin('ClearProperty(toolbox_running,home)')
        while self.params.get("daemon", False) and not xbmc.abortRequested:
            self.image_now = xbmc.getInfoLabel("Player.Art(thumb)")
            if self.image_now != self.image_prev:
                self.image_prev = self.image_now
                image, imagecolor = Filter_Image(self.image_now, int(self.params.get("radius", 5)))
                HOME.setProperty(self.params.get("prefix", "") + 'ImageFilter', image)
                HOME.setProperty(self.params.get("prefix", "") + "ImageColor", imagecolor)
            else:
                xbmc.sleep(300)

    def StartInfoActions(self, infos, params):
        prettyprint(params)
        prettyprint(infos)
        for info in self.infos:
            if info == 'playmovie':
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %i }, "options":{ "resume": %s } }, "id": 1 }' % (int(params["dbid"]), self.resume))
            elif info == 'playepisode':
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %i }, "options":{ "resume": %s }  }, "id": 1 }' % (int(params["dbid"]), self.resume))
            elif info == 'playmusicvideo':
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "musicvideoid": %i } }, "id": 1 }' % int(params["dbid"]))
            elif info == 'playalbum':
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %i } }, "id": 1 }' % int(params["dbid"]))
            elif info == 'playsong':
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "songid": %i } }, "id": 1 }' % int(params["dbid"]))
            elif info == 'favourites':
                if params.get("id", ""):
                    favourites = GetFavouriteswithType(params.get("id", ""))
                else:
                    favourites = GetFavourites()
                    HOME.setProperty('favourite.count', str(len(favourites)))
                    if len(favourites) > 0:
                        HOME.setProperty('favourite.1.name', favourites[-1]["Label"])
                passDataToSkin('Favourites', favourites, params.get("prefix", ""), self.window)
            elif info == 'selectdialog':
                CreateDialogSelect(params.get("header"))
            elif info == 'exportskinsettings':
                export_skinsettings(params.get("text"))
            elif info == 'importskinsettings':
                import_skinsettings()
            elif info == 'extrathumbmovie':
                AddArtToLibrary("extrathumb", "Movie", "extrathumbs", EXTRATHUMB_LIMIT)
            elif info == 'extrafanartmovie':
                AddArtToLibrary("extrafanart", "Movie", "extrafanart", EXTRAFANART_LIMIT)
            elif info == 'extrafanarttvshow':
                AddArtToLibrary("extrafanart", "TVShow", "extrafanart", EXTRAFANART_LIMIT)
            elif info == 'okdialog':
                CreateDialogOK(params.get("header"), params.get("text"))
            elif info == 'builtin':
                xbmc.executebuiltin(params.get("id", ""))
            elif info == 'yesnodialog':
                CreateDialogYesNo(params.get("header"), params.get("text"), params.get("nolabel", ""), params.get("yeslabel", ""), params.get("noaction"), params.get("yesaction", ""))
            elif info == 'notification':
                CreateNotification(params.get("header"), params.get("text"), params.get("icon", xbmcgui.NOTIFICATION_INFO), int(params.get("time", 5000)), params.get("sound", True))
            elif info == 'textviewer':
                xbmcgui.Dialog().textviewer(heading=remove_quotes(params.get("header")),
                                            text=remove_quotes(params.get("text")))
            elif info == "infopanel":
                open_info_panel()
            elif info == "sortletters":
                listitems = GetSortLetters(self.path, params.get("id", ""))
                passDataToSkin('SortLetters', listitems, params.get("prefix", ""), self.window)
            elif info == 'jumptoletter':
                JumpToLetter(params.get("id", ""))
            elif info == 'blur':
                HOME.clearProperty(params.get("prefix", "") + 'ImageFilter')
                log("Blur image %s with radius %i" % (params.get("id", ""), int(params.get("radius", 5))))
                image, imagecolor = Filter_Image(params.get("id", ""), int(params.get("radius", 5)))
                HOME.setProperty(params.get("prefix", "") + 'ImageFilter', image)
                HOME.setProperty(params.get("prefix", "") + "ImageColor", imagecolor)

    def _init_vars(self):
        self.window = xbmcgui.Window(10000)  # Home Window
        self.resume = "false"
        self.image_now = ""
        self.image_prev = ""
        self.params = {}

    def _parse_argv(self):
        args = sys.argv
        self.infos = []
        for arg in args:
            if arg == 'script.toolbox':
                continue
            if arg.startswith('info='):
                self.infos.append(arg[5:])
            else:
                try:
                    self.params[arg.split("=")[0].lower()] = "=".join(arg.split("=")[1:]).strip()
                except:
                    pass

    def selection_dialog(self):
        modeselect = [ADDON_LANGUAGE(32001), ADDON_LANGUAGE(32002), ADDON_LANGUAGE(32003),
                      ADDON_LANGUAGE(32014), ADDON_LANGUAGE(32015), ADDON_LANGUAGE(32018), ADDON_LANGUAGE(32017)]
        dialogSelection = xbmcgui.Dialog()
        selection = dialogSelection.select(ADDON_LANGUAGE(32004), modeselect)
        if selection == 0:
            export_skinsettings()
        elif selection == 1:
            import_skinsettings()
        elif selection == 2:
            xbmc.executebuiltin("Skin.ResetSettings")
        elif selection == 3:
            AddArtToLibrary("extrathumb", "Movie", "extrathumbs", EXTRATHUMB_LIMIT)
        elif selection == 4:
            AddArtToLibrary("extrafanart", "Movie", "extrafanart", EXTRAFANART_LIMIT)
        # elif selection == 5:
        # AddArtToLibrary("extrathumb","TVShow", "extrathumbs")
        elif selection == 5:
            AddArtToLibrary("extrafanart", "TVShow", "extrafanart", EXTRAFANART_LIMIT)
        elif selection == 6:
            AddArtToLibrary("extrathumb", "Movie", "extrathumbs", EXTRATHUMB_LIMIT)
            AddArtToLibrary("extrafanart", "Movie", "extrafanart", EXTRAFANART_LIMIT)
            AddArtToLibrary("extrafanart", "TVShow", "extrafanart", EXTRAFANART_LIMIT)


if __name__ == "__main__":
    Main()
log('finished')
