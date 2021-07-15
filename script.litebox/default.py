import os, sys, re
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from functools import reduce
from threading import Thread
ADDON =             xbmcaddon.Addon()
ADDON_VERSION =     ADDON.getAddonInfo('version')
ADDON_LANGUAGE =    ADDON.getLocalizedString
ADDON_PATH =        ADDON.getAddonInfo('path')
ADDON_ID =          ADDON.getAddonInfo('id')
ADDON_DATA_PATH =   os.path.join(xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID))
HOME =              xbmcgui.Window(10000)
from resources.lib import utils
ColorBox_settings_map = {
        'pixelsize':    utils.set_pixelsize,
        'bitsize':      utils.set_bitsize,
        'black':        utils.set_black,
        'white':        utils.set_white,
        'blursize':     utils.set_blursize,
        'lgint':        utils.set_lgint,
        'lgsteps':      utils.set_lgsteps,
        'comp':         utils.set_comp,
        'main':         utils.set_main,
        'quality':      utils.set_quality}
class ColorBoxMain:
    def __init__(self):
        utils.log("version %s started" % ADDON_VERSION)
        self._init_vars()
        self._parse_argv()
        if not xbmcvfs.exists(ADDON_DATA_PATH):
            xbmcvfs.mkdir(ADDON_DATA_PATH)
        if self.control == "plugin":
            xbmcplugin.endOfDirectory(self.handle)
        utils.Load_Colors_Dict()
        monitor = xbmc.Monitor()
        while self.daemon and not monitor.abortRequested():
            FIVE_daemon_set = HOME.getProperty("FIVE_daemon_set")
            if not FIVE_daemon_set == '':
                self.image_now_FIVE = xbmc.getInfoLabel("Control.GetLabel(7975)")
                if (self.image_now_FIVE != self.image_prev_FIVE and self.image_now_FIVE != "") or HOME.getProperty("FIVE_daemon_fire"):
                    HOME.setProperty('Daemon_FIVE_ImageUpdating', self.image_now_FIVE)
                    HOME.clearProperty("FIVE_daemon_fire")
                    #HOME.clearProperty("ImageFilterFIVE")
                    try:
                        HOME.setProperty('ImageFilterFIVE', utils.ColorBox_go_map(self.image_now_FIVE, FIVE_daemon_set))
                    except Exception as e:
                        utils.log("5err: %s img: %s" % (e,self.image_now_FIVE))
                    else:
                        self.image_prev_FIVE = self.image_now_FIVE
                        HOME.setProperty("OldImageColorFIVE", HOME.getProperty("ImageColorFIVE"))
                        HOME.setProperty("OldImageCColorFIVE", HOME.getProperty("ImageCColorFIVE"))
                        HOME.setProperty('ImageFIVE', self.image_now_FIVE)
                        tm1 = Thread(target=utils.Color_Only, args=(self.image_now_FIVE, "ImageColorFIVE", "ImageCColorFIVE"))
                        tm1.start()
                    HOME.setProperty('Daemon_FIVE_ImageUpdating', '')
            cfa_daemon_set = HOME.getProperty("cfa_daemon_set")
            #curr_window = xbmc.getInfoLabel("Window.Property(xmlfile)")
            if not cfa_daemon_set == '':
                self.image_now_cfa = xbmc.getInfoLabel("ListItem.Art(fanart)")
                if (self.image_now_cfa != self.image_prev_cfa and self.image_now_cfa != "") or HOME.getProperty("cfa_daemon_fire"):
                    HOME.setProperty('Daemon_cfa_ImageUpdating', self.image_now_cfa)
                    HOME.clearProperty("cfa_daemon_fire")
                    #HOME.clearProperty("ImageFiltercfa")
                    try:
                        HOME.setProperty('ImageFiltercfa', utils.ColorBox_go_map(self.image_now_cfa, cfa_daemon_set))
                    except Exception as e:
                        utils.log("cerr: %s img: %s" % (e,self.image_now_cfa))
                    else:
                        self.image_prev_cfa = self.image_now_cfa
                        HOME.setProperty("OldImageColorcfa", HOME.getProperty("ImageColorcfa"))
                        HOME.setProperty("OldImageCColorcfa", HOME.getProperty("ImageCColorcfa"))
                        tf = Thread(target=utils.Color_Only, args=(self.image_now_cfa, "ImageColorcfa", "ImageCColorcfa"))
                        tf.start()
                    HOME.setProperty('Daemon_cfa_ImageUpdating', '')
            NINE_manual_set = HOME.getProperty("NINE_manual_set")
            if (NINE_manual_set != '' and NINE_manual_set != self.prefix_prev_NINE) or HOME.getProperty("NINE_daemon_fire"):
                HOME.setProperty('NINE_manual_set', '')
                try:
                    HOME.clearProperty("NINE_daemon_fire")
                    self.prefix_prev_NINE = NINE_manual_set
                    info = ""
                    id = ""
                    set = ""
                    var = ""
                    prefix = ""
                    for larg in self.prefix_prev_NINE.strip().split('|'):
                        for arg in larg.strip().split(','):
                            arg = arg.replace('"', "")
                            if arg.startswith('info='):
                                info = utils.Remove_Quotes(arg[5:])
                            elif arg.startswith('id='):
                                id = utils.Remove_Quotes(arg[3:])
                            elif arg.startswith('set='):
                                set = utils.Remove_Quotes(arg[4:])
                            elif arg.startswith('var='):
                                var = utils.Remove_Quotes(arg[4:])
                            elif arg.startswith('prefix='):
                                prefix = arg[7:]
                                if not prefix.endswith("."):
                                    prefix = prefix + "."
                        if info != "":
                            HOME.setProperty(prefix + 'ImageFilterNINE', utils.ColorBox_go_map(id, info))
                            HOME.setProperty(prefix + "ImageNINE", id)
                            imagecolor, cimagecolor = utils.Color_Only_Manual(id, prefix + "ImageColorNINE")
                            HOME.setProperty(prefix + "ImageColorNINE", imagecolor)
                            HOME.setProperty(prefix + "ImageCColorNINE", cimagecolor)
                        elif var != "":
                            ColorBox_settings_map[var](set)
                except Exception as e:
                    utils.log("9err: %s img: %s" % (e,self.prefix_prev_NINE))
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
        HOME.setProperty("OldImageColorNINE", "FFffffff")
        HOME.setProperty("ImageColorNINE", "FFffffff")
        HOME.setProperty("OldImageCColorNINE", "FFffffff")
        HOME.setProperty("ImageCColorNINE", "FFffffff")
        self.window =           xbmcgui.Window(10000)
        self.control =          None
        self.daemon =           False
        self.image_now_FIVE =   ""
        self.image_now_cfa =    ""
        self.image_now_NINE =   ""
        self.image_prev_FIVE =  ""
        self.image_prev_cfa =   ""
        self.image_prev_NINE =  ""
        self.prefix_prev_NINE = ""
        self.autoclose =        ""
    def _parse_argv(self):
        args = sys.argv
        self.infos = []
        self.ColorBox_multis = []
        for arg in args:
            arg = arg.replace('"', "")
            if arg == 'script.colorbox':
                continue
            elif arg.startswith('daemon='):
                self.daemon = True
                utils.log("daemon started")
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
        arg = arg.replace('"', "")
        if arg == 'script.colorbox':
            continue
        elif arg.startswith('daemon='):
            ColorBoxMain()
        elif arg.startswith('info='):
            infom = utils.Remove_Quotes(arg[5:])
        elif arg.startswith('id='):
            idm = utils.Remove_Quotes(arg[3:])
        elif arg.startswith('var='):
            varm = utils.Remove_Quotes(arg[4:])
        elif arg.startswith('quality='):
            ColorBox_settings_map['quality'](utils.Remove_Quotes(arg[8:]))
        elif arg.startswith('blursize='):
            ColorBox_settings_map['blursize'](utils.Remove_Quotes(arg[9:]))
        elif arg.startswith('prefix='):
            prefixm = arg[7:]
            if not prefixm.endswith("."):
                prefixm = prefixm + "."