
import os
import xbmc
import xbmcgui
from resources.lib.fileops import listDirectory

KODIMONITOR = xbmc.Monitor()
SKINVALUESLIST = {'default': {'config': 'sliced', 'res': '720p', 'diagw': 400, 'toph': 50, 'bottomh': 10, 'itemh': 45},
                  'skin.ace2': {'config': 'sliced', 'res': '1080i', 'diagw': 600, 'toph': 95, 'bottomh': 0, 'itemh': 45},
                  'skin.aeonmq8': {'config': 'sliced', 'res': '1080i', 'diagw': 600, 'toph': 75, 'bottomh': 0, 'itemh': 60},
                  'skin.aeon.nox.silvo': {'config': 'sliced', 'res': '1080i', 'diagw': 600, 'toph': 80, 'bottomh': 50, 'itemh': 60},
                  'skin.aeon.tajo': {'config': 'scaled', 'res': '1080i', 'diagw': 600, 'diagb': 130, 'itemh': 60},
                  'skin.amber': {'config': 'scaled', 'res': '1080i', 'diagw': 525, 'diagb': 120, 'itemh': 60},
                  'skin.apptv': {'config': 'scaled', 'res': '1080i', 'diagw': 770, 'diagb': 83, 'itemh': 72},
                  'skin.arctic.horizon': {'config': 'scaled', 'res': '1080i', 'diagw': 506, 'diagb': 90, 'itemh': 70},
                  'skin.arctic.zephyr.2': {'config': 'scaled', 'res': '1080i', 'diagw': 506, 'diagb': 90, 'itemh': 70},
                  'skin.aura': {'config': 'scaled', 'res': '1080i', 'diagw': 506, 'diagb': 90, 'itemh': 70},
                  'skin.bello.7': {'config': 'sliced', 'res': '720p', 'diagw': 405, 'toph': 75, 'bottomh': 22, 'itemh': 37},
                  'skin.box': {'config': 'fixed', 'res': '720p'},
                  'skin.confluence': {'config': 'sliced', 'res': '720p', 'diagw': 400, 'toph': 60, 'bottomh': 25, 'itemh': 40},
                  'skin.estuary': {'config': 'sliced', 'res': '1080i', 'diagw': 600, 'toph': 75, 'bottomh': 0, 'itemh': 70},
                  'skin.embuary-leia': {'config': 'sliced', 'res': '1080i', 'diagw': 500, 'toph': 111, 'bottomh': 61, 'itemh': 50},
                  'skin.eminence.2': {'config': 'sliced', 'res': '1080i', 'diagw': 550, 'toph': 82, 'bottomh': 20, 'itemh': 82},
                  'skin.ftv': {'config': 'scaled', 'res': '1080i', 'diagw': 540, 'diagb': 156, 'itemh': 76},
                  'skin.pellucid': {'config': 'sliced', 'res': '1080i', 'diagw': 640, 'toph': 108, 'bottomh': 20, 'itemh': 72},
                  'skin.quartz': {'config': 'scaled', 'res': '1080i', 'diagw': 590, 'diagb': 158, 'itemh': 60},
                  'skin.rapier': {'config': 'sliced', 'res': '720p', 'diagw': 400, 'toph': 69, 'bottomh': 32, 'itemh': 37},
                  'skin.revolve': {'config': 'scaled', 'res': '1080i', 'diagw': 558, 'diagb': 95, 'itemh': 40},
                  'skin.transparency': {'config': 'sliced', 'res': '1080i', 'diagw': 600, 'toph': 100, 'bottomh': 36, 'itemh': 52},
                  'skin.unity': {'config': 'fixed', 'res': '720p'},
                  'skin.xperience1080': {'config': 'fixed', 'res': '1080i'}
                  }


class Dialog:

    def start(self, settings, title='', buttons=None):
        self.SETTINGS = settings
        self.TITLE = title
        self.BUTTONS = buttons
        self.LOGLINES = []
        if self.SETTINGS['use_custom_skin_menu']:
            return self._custom()
        else:
            return self._built_in()

    def _built_in(self):
        self.LOGLINES = []
        self.LOGLINES.append('using built-in dialog box')
        d_return = xbmcgui.Dialog().select(self.TITLE, self.BUTTONS)
        self.LOGLINES.append(
            'the final returned value from the dialog box is: %s' % str(d_return))
        if d_return == -1:
            d_return = None
        return d_return, self.LOGLINES

    def _custom(self):
        self.LOGLINES = []
        current_skin = xbmc.getSkinDir()
        skin, skin_values = self._get_skin_info(current_skin)
        self.LOGLINES.append('using skin values of:')
        self.LOGLINES.append(skin_values)
        display = Show('script.harmony.control-menu.xml', self.SETTINGS['ADDONPATH'], skin, skin_values['res'],
                       skin_values=skin_values, title=self.TITLE, buttons=self.BUTTONS)
        display.show()
        while not display.CLOSED and not KODIMONITOR.abortRequested():
            self.LOGLINES.append(
                'the current returned value from display is: %s' % str(display.DIALOGRETURN))
            self.LOGLINES.append(
                'the current returned close status from display is: %s' % str(display.CLOSED))
            if display.DIALOGRETURN is not None:
                break
            KODIMONITOR.waitForAbort(1)
        self.LOGLINES = self.LOGLINES + display.LOGLINES
        self.LOGLINES.append(
            'the final returned value from display is: %s' % str(display.DIALOGRETURN))
        self.LOGLINES.append(
            'the final returned close status from display is: %s' % str(display.CLOSED))
        d_return = display.DIALOGRETURN
        del display
        return d_return, self.LOGLINES

    def _get_skin_info(self, current_skin):
        default_skin = 'Default'
        skin_list, loglines = listDirectory(os.path.join(
            self.SETTINGS['ADDONPATH'], 'resources', 'skins'), thefilter='folders')
        self.LOGLINES = self.LOGLINES + loglines
        if current_skin in skin_list:
            self.LOGLINES.append(
                'found %s in list of skins, returning it as the skin' % current_skin)
            default_skin = current_skin
        elif self.SETTINGS['include_skin_mods']:
            keep_trying = True
            skin_glue = 2
            skin_parts = current_skin.split('.')
            while keep_trying:
                skin_test = '.'.join(skin_parts[:skin_glue])
                if skin_test in skin_list:
                    default_skin = skin_test
                    keep_trying = False
                skin_glue += 1
                if skin_glue > len(skin_parts):
                    keep_trying = False
        self.LOGLINES.append('returning %s as the skin for skin %s' % (
            default_skin, current_skin))
        return default_skin, SKINVALUESLIST.get(default_skin.lower())


class Show(xbmcgui.WindowXMLDialog):

    def __init__(self, xml_file, script_path, defaultSkin, defaultRes, skin_values=None, title='', buttons=None):
        """Shows a Kodi WindowXMLDialog."""
        self.DIALOGRETURN = None
        self.CLOSED = False
        self.ACTION_PREVIOUS_MENU = 10
        self.ACTION_NAV_BACK = 92
        self.SKINVALUES = skin_values
        self.TITLE = title
        if buttons:
            self.BUTTONS = buttons
        else:
            self.BUTTONS = []
        self.LOGLINES = []

    def onInit(self):
        x, y, bottom_y = self._get_coordinates()
        self.getControl(10071).setLabel(self.TITLE)
        the_button = None
        try:
            the_list = self.getControl(10070)
        except RuntimeError:
            the_list = None
            the_button = 10080
        self.LOGLINES.append('The button is set to %s' % str(the_button))
        for button_text in self.BUTTONS:
            if the_button:
                self.LOGLINES.append('adding %s as label for button %s' % (
                    button_text, str(the_button)))
                self.getControl(the_button).setLabel(button_text)
                the_button += 1
                self.LOGLINES.append(
                    'The button value is set to %s' % str(the_button))
            else:
                self.LOGLINES.append('adding item %s' % button_text)
                the_list.addItem(xbmcgui.ListItem(button_text))
        if the_button:
            while the_button <= 10089:
                self.getControl(the_button).setVisible(False)
                the_button += 1
        if x and y:
            self.getControl(10072).setPosition(x, y)
        if bottom_y:
            if self.SKINVALUES['config'] == 'sliced':
                self.getControl(10073).setPosition(0, bottom_y)
            elif self.SKINVALUES['config'] == 'scaled':
                self.getControl(10073).setHeight(bottom_y)
        if the_list:
            self.setFocus(self.getControl(10070))

    def onAction(self, action):
        if action in [self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK]:
            self.CLOSED = True
            self.close()

    def onClick(self, controlID):
        try:
            self.DIALOGRETURN = self.getControl(
                controlID).getSelectedPosition()
        except AttributeError:
            self.DIALOGRETURN = self.getControl(controlID).getId() - 10080
        self.close()

    def _get_coordinates(self):
        if self.SKINVALUES['config'] == 'scaled':
            dialog_height = (
                len(self.BUTTONS) * self.SKINVALUES['itemh']) + self.SKINVALUES['diagb']
            bottom_y = dialog_height
        elif self.SKINVALUES['config'] == 'sliced':
            dialog_height = (len(
                self.BUTTONS) * self.SKINVALUES['itemh']) + self.SKINVALUES['toph'] + self.SKINVALUES['bottomh']
            if self.SKINVALUES['bottomh']:
                bottom_y = dialog_height - self.SKINVALUES['bottomh']
            else:
                bottom_y = 0
        else:
            return 0, 0, 0
        if self.SKINVALUES['res'] == '720p':
            screen_width = 1280
            screen_height = 720
        else:
            screen_width = 1920
            screen_height = 1080
        x = (screen_width - self.SKINVALUES['diagw']) // 2
        y = (screen_height - dialog_height) // 2
        self.LOGLINES.append(
            'returning x: %s, y: %s, bottom_y: %s' % (x, y, bottom_y))
        return x, y, bottom_y
