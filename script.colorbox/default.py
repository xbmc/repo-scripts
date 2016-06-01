import sys
import os
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_LANGUAGE = ADDON.getLocalizedString
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
EXTRAFANART_LIMIT = 4
EXTRATHUMB_LIMIT = 4
HOME = xbmcgui.Window(10000)
sys.path.append(xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'lib')))

from Utils import *


class Main:

    def __init__(self):
        log("version %s started" % ADDON_VERSION)
        self._init_vars()
        self._parse_argv()
        if self.infos:
            self._StartInfoActions()
        if self.control == "plugin":
            xbmcplugin.endOfDirectory(self.handle)
        while self.daemon and not xbmc.abortRequested:
            self.image_now = xbmc.getInfoLabel("Player.Art(thumb)")
            self.image_now_fa = xbmc.getInfoLabel("MusicPlayer.Property(Fanart_Image)")
            self.image_now_cfa = xbmc.getInfoLabel("ListItem.Art(fanart)")
            self.image_now_cpa = xbmc.getInfoLabel("ListItem.Art(poster)")
            if not HOME.getProperty("cpa_ignore_set") and self.image_now_cpa != self.image_prev_cpa:
                try:
                    self.image_prev_cpa = self.image_now_cpa
                    HOME.setProperty(self.prefix + 'ImageUpdating', '0')
                    image = Filter_Distort(self.image_now_cpa, self.delta_x, self.delta_y)
                    HOME.setProperty(self.prefix + 'ImageFiltercpa', image)
                except:
                    log("Could not process image for cpa daemon")
            if not HOME.getProperty("cfa_ignore_set") and self.image_now_cfa != self.image_prev_cfa:
                try:
                    self.image_prev_cfa = self.image_now_cfa
                    HOME.setProperty(self.prefix + 'ImageUpdating', '0')
                    if HOME.getProperty("cfa_daemon_set") == 'Blur':
                        image, imagecolor = Filter_Image(self.image_now_cfa, self.radius)
                        HOME.setProperty(self.prefix + 'ImageFiltercfa1', image)
                        HOME.setProperty(self.prefix + "ImageColorcfa1", imagecolor)
                    elif HOME.getProperty("cfa_daemon_set") == 'Pixelate':
                        image = Filter_Pixelate(self.image_now_cfa, self.pixels)
                        HOME.setProperty(self.prefix + 'ImageFiltercfa2', image)
                        HOME.setProperty(self.prefix + "ImageColorcfa2", Random_Color())
                    elif HOME.getProperty("cfa_daemon_set") == 'Posterize':
                        image = Filter_Posterize(self.image_now_cfa, self.bits)
                        HOME.setProperty(self.prefix + 'ImageFiltercfa3', image)
                        HOME.setProperty(self.prefix + "ImageColorcfa3", Random_Color())
                    elif HOME.getProperty("cfa_daemon_set") == 'Distort':
                        image = Filter_Distort(self.image_now_cfa, self.delta_x, self.delta_y)
                        HOME.setProperty(self.prefix + 'ImageFiltercfa4', image)
                        HOME.setProperty(self.prefix + "ImageColorcfa4", Random_Color())
                except:
                    log("Could not process image for cfa daemon")
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')
            if self.image_now != self.image_prev and xbmc.Player().isPlayingAudio():
                try:
                    self.image_prev = self.image_now
                    image, imagecolor = Filter_Image(self.image_now, self.radius)
                    HOME.setProperty(self.prefix + 'ImageFilter1', image)
                    HOME.setProperty(self.prefix + "ImageColor1", imagecolor)
                    image = Filter_Pixelate(self.image_now, self.pixels)
                    HOME.setProperty(self.prefix + 'ImageFilter2', image)
                    HOME.setProperty(self.prefix + "ImageColor2", Random_Color())
                    image = Filter_Posterize(self.image_now, self.bits)
                    HOME.setProperty(self.prefix + 'ImageFilter3', image)
                    HOME.setProperty(self.prefix + "ImageColor3", Random_Color())
                except:
                    log("Could not process image for f daemon")
            if self.image_now_fa != self.image_prev_fa and xbmc.Player().isPlayingAudio():
                try:
                    self.image_prev_fa = self.image_now_fa
                    image, imagecolor = Filter_Image(self.image_now_fa, self.radius)
                    HOME.setProperty(self.prefix + 'ImageFilterfa1', image)
                    HOME.setProperty(self.prefix + "ImageColorfa1", imagecolor)
                    image = Filter_Pixelate(self.image_now_fa, self.pixels)
                    HOME.setProperty(self.prefix + 'ImageFilterfa2', image)
                    HOME.setProperty(self.prefix + "ImageColorfa2", Random_Color())
                    image = Filter_Posterize(self.image_now_fa, self.bits)
                    HOME.setProperty(self.prefix + 'ImageFilterfa3', image)
                    HOME.setProperty(self.prefix + "ImageColorfa3", Random_Color())
                except:
                    log("Could not process image for fa daemon")
            else:
                xbmc.sleep(300)

    def _StartInfoActions(self):
        for info in self.infos:
            if info == 'firstrun':
                ColorboxFirstRun()
            elif info == 'randomcolor':
                imagecolor = Random_Color()
                HOME.setProperty(self.prefix + "ImageColor", imagecolor)
            elif info == 'bluronly':
                HOME.clearProperty(self.prefix + 'ImageFilter')
                image = Filter_ImageOnly(self.id, self.radius)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
            elif info == 'blur':
                HOME.clearProperty(self.prefix + 'ImageFilter')
                image, imagecolor = Filter_Image(self.id, self.radius)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + "ImageColor", imagecolor)
            elif info == 'pixelate':
                imagecolor = Random_Color()
                HOME.setProperty(self.prefix + "ImageColor", imagecolor)
                image = Filter_Pixelate(self.id, self.pixels)
                if image  != "":
                    HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')
            elif info == 'twotone':
                image = Filter_Twotone(self.id, self.black, self.white)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')
            elif info == 'posterize':
                image = Filter_Posterize(self.id, self.bits)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')
            elif info == 'fakelight':
                image = Filter_Fakelight(self.id, self.pixels)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')
            elif info == 'distort':
                image = Filter_Distort(self.id, self.delta_x, self.delta_y)
                HOME.setProperty(self.prefix + 'ImageFilter', image)
                HOME.setProperty(self.prefix + 'ImageUpdating', '1')

    def _init_vars(self):
        self.window = xbmcgui.Window(10000)  # Home Window
        self.control = None
        self.infos = []
        self.id = ""
        self.dbid = ""
        self.prefix = ""
        self.radius = 5
        self.bits = 2
        self.pixels = 20
        self.container = 518
        self.black = "#000000"
        self.white = "#FFFFFF"
        self.delta_x = 50
        self.delta_y = 90
        self.daemon = False
        self.image_now = ""
        self.image_now_fa = ""
        self.image_now_cfa = ""
        self.image_now_cpa = ""
        self.image_prev = ""
        self.image_prev_fa = ""
        self.image_prev_cfa = ""
        self.image_prev_cpa = ""
        self.autoclose = ""

    def _parse_argv(self):
        args = sys.argv
        for arg in args:
            arg = arg.replace("'\"", "").replace("\"'", "")
            if arg == 'script.colorbox':
                continue
            elif arg.startswith('info='):
                self.infos.append(arg[5:])
            elif arg.startswith('id='):
                self.id = RemoveQuotes(arg[3:])
            elif arg.startswith('dbid='):
                self.dbid = int(arg[5:])
            elif arg.startswith('daemon='):
                self.daemon = True
            elif arg.startswith('prefix='):
                self.prefix = arg[7:]
                if not self.prefix.endswith("."):
                    self.prefix = self.prefix + "."
            elif arg.startswith('radius='):
                self.radius = int(arg[7:])
            elif arg.startswith('pixels='):
                self.pixels = int(arg[7:])
            elif arg.startswith('bits='):
                self.bits = int(arg[5:])
            elif arg.startswith('black='):
                self.black = RemoveQuotes(arg[6:])
            elif arg.startswith('white='):
                self.white = RemoveQuotes(arg[6:])
            elif arg.startswith('delta_x='):
                self.delta_x = int(arg[8:])
            elif arg.startswith('delta_y='):
                self.delta_y = int(arg[8:])
            elif arg.startswith('container='):
                self.container = RemoveQuotes(arg[10:])

class ColorBoxMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onPlayBackStarted(self):
        pass
        # HOME.clearProperty(self.prefix + 'ImageFilter')
        # Notify("test", "test")
        # image, imagecolor = Filter_Image(self.id, self.radius)
        # HOME.setProperty(self.prefix + 'ImageFilter', image)
        # HOME.setProperty(self.prefix + "ImageColor", imagecolor)


if __name__ == "__main__":
    Main()
log('finished')
