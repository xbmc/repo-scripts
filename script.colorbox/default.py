import os, sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from threading import Thread
ADDON =             xbmcaddon.Addon()
ADDON_VERSION =     ADDON.getAddonInfo('version')
ADDON_LANGUAGE =    ADDON.getLocalizedString
ADDON_PATH =        ADDON.getAddonInfo('path').decode("utf-8")
ADDON_ID =          ADDON.getAddonInfo('id')
ADDON_DATA_PATH =   os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID))
HOME =              xbmcgui.Window(10000)
from resources.lib import Utils
ColorBox_function_map = {
        'blur':         Utils.blur,
        'pixelate':     Utils.pixelate,
        'shiftblock':   Utils.shiftblock,
        'pixelnone':    Utils.pixelnone,
        'pixelwaves':   Utils.pixelwaves,
        'pixelrandom':  Utils.pixelrandom,
        'pixelfile':    Utils.pixelfile,
        'pixelfedges':  Utils.pixelfedges,
        'pixeledges':   Utils.pixeledges,
        'fakelight':    Utils.fakelight,
        'twotone':      Utils.twotone,
        'posterize':    Utils.posterize,
        'distort':      Utils.distort}
ColorBox_settings_map = {
        'pixelsize':        Utils.set_pixelsize,
        'bitsize':          Utils.set_bitsize,
        'blursize':         Utils.set_blursize,
        'black':            Utils.set_black,
        'white':            Utils.set_white,
        'quality':          Utils.set_quality}
class ColorBoxMain:
    def __init__(self):
        Utils.log("version %s started" % ADDON_VERSION)
        self._init_vars()
        self._parse_argv()
        if not xbmcvfs.exists(ADDON_DATA_PATH):
            # addon data path does not exist...create it
            xbmcvfs.mkdir(ADDON_DATA_PATH)
        if self.control == "plugin":
            xbmcplugin.endOfDirectory(self.handle)
        Utils.Load_Colors_Dict()
        monitor = xbmc.Monitor()
        while self.daemon and not monitor.abortRequested():
            if xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)") != self.show_watched:
                self.show_watched = xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)")
                Utils.Show_Percentage()
            self.prefix_now_NINE = HOME.getProperty("NINE_manual_set")
            if self.prefix_now_NINE != '' and self.prefix_now_NINE != self.prefix_prev_NINE or HOME.getProperty("NINE_daemon_fire"):
                try:
                    HOME.setProperty('Daemon_NINE_ImageUpdating', '0')
                    HOME.clearProperty("NINE_daemon_fire")
                    self.prefix_prev_NINE = self.prefix_now_NINE
                    self.info = ""
                    self.var = ""
                    for arg in self.prefix_now_NINE.strip().split(','):
                        arg = arg.replace("'\"", "").replace("\"'", "")
                        if arg.startswith('info='):
                            self.info = Utils.Remove_Quotes(arg[5:])
                        elif arg.startswith('id='):
                            self.id = Utils.Remove_Quotes(arg[3:])
                        elif arg.startswith('set='):
                            self.set = Utils.Remove_Quotes(arg[4:])
                        elif arg.startswith('var='):
                            self.var = Utils.Remove_Quotes(arg[4:])
                        elif arg.startswith('prefix='):
                            self.prefix = arg[7:]
                            if not self.prefix.endswith("."):
                                self.prefix = self.prefix + "."
                    if self.info != "":
                        HOME.setProperty(self.prefix + "ImageFilterNINE", ColorBox_function_map[self.info](self.id))
                        HOME.setProperty(self.prefix + "ImageNINE", self.id)
                        HOME.setProperty('Daemon_NINE_ImageUpdating', '1')
                        imagecolor, cimagecolor = Utils.Color_Only_Manual(self.id)
                        HOME.setProperty(self.prefix + "ImageColorNINE", imagecolor)
                        HOME.setProperty(self.prefix + "ImageCColorNINE", cimagecolor)
                    elif self.var != "":
                        #change various settings
                        ColorBox_settings_map[self.var](self.set)
                except:
                    Utils.log("Could not process image for NINE daemon")
            FIVE_daemon_set = HOME.getProperty("FIVE_daemon_set")
            if not FIVE_daemon_set == 'None':
                self.image_now_FIVE = xbmc.getInfoLabel("Control.GetLabel(7975)")
                if self.image_now_FIVE != self.image_prev_FIVE and self.image_now_FIVE != "" or HOME.getProperty("FIVE_daemon_fire"):
                    try:
                        HOME.setProperty('Daemon_FIVE_ImageUpdating', '0')
                        HOME.clearProperty("FIVE_daemon_fire")
                        self.image_prev_FIVE = self.image_now_FIVE
                        HOME.setProperty("OldImageColorFIVE", HOME.getProperty("ImageColorFIVE"))
                        HOME.setProperty("OldImageCColorFIVE", HOME.getProperty("ImageCColorFIVE"))
                        HOME.setProperty('ImageFilterFIVE', ColorBox_function_map[FIVE_daemon_set](self.image_now_FIVE))
                        HOME.setProperty('ImageFIVE', self.image_now_FIVE)
                        HOME.setProperty('Daemon_FIVE_ImageUpdating', '1')
                        tm1 = Thread(target=Utils.Color_Only, args=(self.image_now_FIVE, "ImageColorFIVE", "ImageCColorFIVE"))
                        tm1.start()
                    except:
                        Utils.log("Could not process image for FIVE daemon")
            cfa_daemon_set = HOME.getProperty("cfa_daemon_set")
            #curr_window = xbmc.getInfoLabel("Window.Property(xmlfile)")
            if not cfa_daemon_set == 'None':
                self.image_now_cfa = xbmc.getInfoLabel("ListItem.Art(fanart)")
                if self.image_now_cfa != self.image_prev_cfa and self.image_now_cfa != "" or HOME.getProperty("cfa_daemon_fire"):
                    try:
                        HOME.setProperty('DaemonFanartImageUpdating', '0')
                        HOME.clearProperty("cfa_daemon_fire")
                        self.image_prev_cfa = self.image_now_cfa
                        HOME.setProperty("OldImageColorcfa", HOME.getProperty("ImageColorcfa"))
                        HOME.setProperty("OldImageCColorcfa", HOME.getProperty("ImageCColorcfa"))
                        HOME.setProperty('ImageFiltercfa', ColorBox_function_map[cfa_daemon_set](self.image_now_cfa))
                        HOME.setProperty('DaemonFanartImageUpdating', '1')
                        tf = Thread(target=Utils.Color_Only, args=(self.image_now_cfa, "ImageColorcfa", "ImageCColorcfa"))
                        tf.start()
                    except:
                        Utils.log("Could not process image for cfa daemon")
            if not HOME.getProperty("SEVEN_daemon_set") == 'None':
                self.image_now_SEVEN = xbmc.getInfoLabel("Control.GetLabel(7977)")
                if self.image_now_SEVEN != self.image_prev_SEVEN and self.image_now_SEVEN != "":
                    try:
                        self.image_prev_SEVEN = self.image_now_SEVEN
                        HOME.setProperty("OldImageColorSEVEN", HOME.getProperty("ImageColorSEVEN"))
                        HOME.setProperty("OldImageCColorSEVEN", HOME.getProperty("ImageCColorSEVEN"))
                        tm3 = Thread(target=Utils.Color_Only, args=(self.image_now_SEVEN, "ImageColorSEVEN", "ImageCColorSEVEN"))
                        tm3.start()
                    except:
                        Utils.log("Could not process image for SEVEN daemon")
            if not HOME.getProperty("EIGHT_daemon_set") == 'None':
                self.image_now_EIGHT = xbmc.getInfoLabel("Control.GetLabel(7978)")
                if self.image_now_EIGHT != self.image_prev_EIGHT and self.image_now_EIGHT != "" or HOME.getProperty("EIGHT_daemon_fire"):
                    try:
                        HOME.setProperty('Daemon_EIGHT_ImageUpdating', '0')
                        HOME.clearProperty("EIGHT_daemon_fire")
                        self.image_prev_EIGHT = self.image_now_EIGHT
                        HOME.setProperty("OldImageColorEIGHT", HOME.getProperty("ImageColorEIGHT"))
                        HOME.setProperty("OldImageCColorEIGHT", HOME.getProperty("ImageCColorEIGHT"))
                        HOME.setProperty('ImageFilterEIGHT', ColorBox_function_map[EIGHT_daemon_set](self.image_now_EIGHT))
                        HOME.setProperty('ImageEIGHT', self.image_now_EIGHT)
                        HOME.setProperty('Daemon_EIGHT_ImageUpdating', '1')
                        tm4 = Thread(target=Utils.Color_Only, args=(self.image_now_EIGHT, "ImageColorEIGHT", "ImageCColorEIGHT"))
                        tm4.start()
                    except:
                        Utils.log("Could not process image for EIGHT daemon")
            monitor.waitForAbort(0.2)
    def _StartInfoActions(self):
        for info in self.infos:
            if info == 'randomcolor':
                HOME.setProperty(self.prefix + "ImageColor", Utils.Random_Color())
                HOME.setProperty(self.prefix + "ImageCColor", Utils.Complementary_Color(HOME.getProperty(self.prefix + "ImageColor")))
            elif info == 'percentage':
                Utils.Show_Percentage()
    def _init_vars(self):
        HOME.setProperty("OldImageColorFIVE", "FFffffff")
        HOME.setProperty("ImageColorFIVE", "FFffffff")
        HOME.setProperty("OldImageCColorFIVE", "FFffffff")
        HOME.setProperty("ImageCColorFIVE", "FFffffff")
        HOME.setProperty("OldImageColorcfa", "FFffffff")
        HOME.setProperty("ImageColorcfa", "FFffffff")
        HOME.setProperty("OldImageCColorcfa", "FFffffff")
        HOME.setProperty("ImageCColorcfa", "FFffffff")
        HOME.setProperty("OldImageColorSEVEN", "FFffffff")
        HOME.setProperty("ImageColorSEVEN", "FFffffff")
        HOME.setProperty("OldImageColorEIGHT", "FFffffff")
        HOME.setProperty("ImageColorEIGHT", "FFffffff")
        HOME.setProperty("OldImageColorNINE", "FFffffff")
        HOME.setProperty("ImageColorNINE", "FFffffff")
        HOME.setProperty("OldImageCColorSEVEN", "FFffffff")
        HOME.setProperty("ImageCColorSEVEN", "FFffffff")
        HOME.setProperty("OldImageCColorEIGHT", "FFffffff")
        HOME.setProperty("ImageCColorEIGHT", "FFffffff")
        HOME.setProperty("OldImageCColorNINE", "FFffffff")
        HOME.setProperty("ImageCColorNINE", "FFffffff")
        self.window =           xbmcgui.Window(10000)  # Home Window
        self.control =          None
        self.id =               ""
        self.prefix =           ""
        self.daemon =           False
        self.show_watched =     ""
        self.image_now_FIVE =   ""
        self.image_now_cfa =    ""
        self.image_now_SEVEN =  ""
        self.image_now_EIGHT =  ""
        self.image_now_NINE =   ""
        self.image_prev_FIVE =  ""
        self.image_prev_cfa =   ""
        self.image_prev_SEVEN = ""
        self.image_prev_EIGHT = ""
        self.image_prev_NINE =  ""
        self.prefix_now_NINE =  ""
        self.prefix_prev_NINE = ""
        self.autoclose =        ""
    def _parse_argv(self):
        args = sys.argv
        self.infos = []
        for arg in args:
            arg = arg.replace("'\"", "").replace("\"'", "")
            if arg == 'script.colorbox':
                continue
            elif arg.startswith('daemon='):
                self.daemon = True
class ColorBoxMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    def onPlayBackStarted(self):
        pass
        # HOME.clearProperty(self.prefix + 'ImageFilter')
        # Notify("test", "test")
        # image, imagecolor, cimagecolor = Filter_blur(self.id, self.radius)
        # HOME.setProperty(self.prefix + 'ImageFilter', image)
        # HOME.setProperty(self.prefix + "ImageColor", imagecolor)
if __name__ == "__main__":
    args = sys.argv
    infos = []
    for arg in args:
        arg = arg.replace("'\"", "").replace("\"'", "")
        if arg == 'script.colorbox':
            continue
        elif arg.startswith('daemon='):
            ColorBoxMain()