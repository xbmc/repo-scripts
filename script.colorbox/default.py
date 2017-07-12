import os, sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import re
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
        'pixelsize':    Utils.set_pixelsize,
        'bitsize':      Utils.set_bitsize,
        'blursize':     Utils.set_blursize,
        'black':        Utils.set_black,
        'white':        Utils.set_white,
        'quality':      Utils.set_quality}
ColorBox_strip =        ('[CR]', ' '), ('<BR>', ' '), ('<br>', ' '), ('&#10;', ' '), ('&&#10;', ' ')
#ColorBox_strip =       ('[B]', ''), ('[/B]', ''), ('[CR]', ' ')
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
            Utils.Show_Percentage()
            #HOME.setProperty('WidgetNameLabelVar', xbmc.getInfoLabel("Control.GetLabel(7973)").replace("[CR]", " "))
            #HOME.setProperty('HomeHeaderSubline', xbmc.getInfoLabel("Control.GetLabel(7974)").replace("[CR]", " "))
            HOME.setProperty('LabelFilterTWO', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, xbmc.getInfoLabel("Control.GetLabel(7972)")).strip()))
            HOME.setProperty('LabelFilterTHREE', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, xbmc.getInfoLabel("Control.GetLabel(7973)")).strip()))
            HOME.setProperty('LabelFilterFOUR', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, xbmc.getInfoLabel("Control.GetLabel(7974)")).strip()))
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
            self.manual_set_NINE = HOME.getProperty("NINE_manual_set")
            if self.manual_set_NINE != '' and self.manual_set_NINE != self.prefix_prev_NINE or HOME.getProperty("NINE_daemon_fire"):
                try:
                    HOME.setProperty('Daemon_NINE_ImageUpdating', '0')
                    HOME.clearProperty("NINE_daemon_fire")
                    self.prefix_prev_NINE = self.manual_set_NINE
                    self.info = ""
                    self.id = ""
                    self.set = ""
                    self.var = ""
                    self.prefix = ""
                    for larg in self.manual_set_NINE.strip().split('|'):
                        for arg in larg.strip().split(','):
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
            if self.ColorBox_multis != []:
                for line in self.ColorBox_multis:
                    self.idm, self.wpnam, self.mfx = line.strip().split('|')
                    self.image_now_MULTI = xbmc.getInfoLabel("Control.GetLabel(" + str(self.idm) + ")")
                    if self.image_now_MULTI != HOME.getProperty(self.wpnam) and self.image_now_MULTI != "":
                        try:
                            HOME.setProperty(self.wpnam + "ImageFilter", ColorBox_function_map[self.mfx](self.image_now_MULTI))
                            HOME.setProperty(self.wpnam + "Image", self.image_now_MULTI)
                            imagecolor, cimagecolor = Utils.Color_Only_Manual(self.image_now_MULTI)
                            HOME.setProperty(self.wpnam + "ImageColor", imagecolor)
                            HOME.setProperty(self.wpnam + "ImageCColor", cimagecolor)
                        except:
                            Utils.log("Could not process image for image_now_MULTI daemon %s" % self.wpnam)
            monitor.waitForAbort(0.2)
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
        self.manual_set_NINE =  ""
        self.prefix_prev_NINE = ""
        self.autoclose =        ""
    def _parse_argv(self):
        args = sys.argv
        self.infos = []
        self.ColorBox_multis = []
        for arg in args:
            arg = arg.replace("'\"", "").replace("\"'", "")
            if arg == 'script.colorbox':
                continue
            elif arg.startswith('multis='):
                self.multim = Utils.Remove_Quotes(arg[7:])
                self.ColorBox_multis = self.multim.split(":")
            elif arg.startswith('daemon='):
                self.daemon = True
class ColorBoxMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    def onPlayBackStarted(self):
        pass
if __name__ == "__main__":
    args =		sys.argv
    infom =		""
    idm =		""
    varm =		120
    prefixm	=	""
    for arg in args:
        arg = arg.replace("'\"", "").replace("\"'", "")
        if arg == 'script.colorbox':
            continue
        elif arg.startswith('daemon='):
            ColorBoxMain()
        elif arg.startswith('info='):
            infom = Utils.Remove_Quotes(arg[5:])
        elif arg.startswith('id='):
            idm = Utils.Remove_Quotes(arg[3:])
        elif arg.startswith('var='):
            varm = Utils.Remove_Quotes(arg[4:])
        elif arg.startswith('quality='):
            ColorBox_settings_map['quality'](Utils.Remove_Quotes(arg[8:]))
        elif arg.startswith('blursize='):
            ColorBox_settings_map['blursize'](Utils.Remove_Quotes(arg[9:]))
        elif arg.startswith('pixelsize='):
            ColorBox_settings_map['pixelsize'](Utils.Remove_Quotes(arg[10:]))
        elif arg.startswith('bitsize='):
            ColorBox_settings_map['bitsize'](Utils.Remove_Quotes(arg[8:]))
        elif arg.startswith('black='):
            ColorBox_settings_map['black'](Utils.Remove_Quotes(arg[6:]))
        elif arg.startswith('white='):
            ColorBox_settings_map['white'](Utils.Remove_Quotes(arg[6:]))
        elif arg.startswith('prefix='):
            prefixm = arg[7:]
            if not prefixm.endswith("."):
                prefixm = prefixm + "."
    if infom == 'randomcolor':
        HOME.setProperty(prefixm + "ImageColor", Utils.Random_Color())
        HOME.setProperty(prefixm + "ImageCColor", Utils.Complementary_Color(HOME.getProperty(prefixm + "ImageColor")))
    elif infom == 'shuffle' and idm != '':
        us1 = Thread(target=Utils.Shuffle_Set, args=(idm,varm))
        us1.start()
    elif infom != "" and idm != "":
        try:
            HOME.setProperty(prefixm + "ImageFilter", ColorBox_function_map[infom](idm))
            HOME.setProperty(prefixm + "Image", idm)
            imagecolor, cimagecolor = Utils.Color_Only_Manual(idm)
            HOME.setProperty(prefixm + "ImageColor", imagecolor)
            HOME.setProperty(prefixm + "ImageCColor", cimagecolor)
        except:
            Utils.log("Could not process image for go_RUNSCRIPT_COLORBOX")