# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from traceback import print_exc

import xbmc
import xbmcgui

from . import jsonrpc
from .common import log
from .constants import ADDON
from .constants import ADDON_NAME
from .constants import LANGUAGE


class ShowDialog(xbmcgui.WindowXMLDialog):
    """
    PRETTY SELECT DIALOG
    """

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args)
        self.listing = kwargs.get('listing')
        self.window_title = kwargs.get('window_title')
        self.more = kwargs.get('more')
        self.result = -1
        self.list = None

    def onInit(self):  # pylint: disable=invalid-name
        try:
            self.list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            log(print_exc())
            self.list = self.getControl(3)

        if self.more is True:
            self.getControl(5).setLabel(xbmc.getLocalizedString(21452))
        else:
            self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.window_title)

        try:
            # Set Cancel label (Kodi 17+)
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
        except RuntimeError:
            pass

        for item in self.listing:
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2(),
                                        offscreen=True)
            listitem.setArt({
                'icon': item.getProperty('icon'),
                'thumb': item.getProperty('thumbnail')
            })
            listitem.setProperty('Addon.Summary', item.getLabel2())
            self.list.addItem(listitem)

        self.setFocus(self.list)

    def onAction(self, action):  # pylint: disable=invalid-name
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448,):
            self.result = -1
            self.close()

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if control_id == 5:
            self.result = -2
        elif control_id in (3, 6):
            num = self.list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, control_id):  # pylint: disable=invalid-name
        pass


def toggle_debug_logging(enable=False):
    # return None on error
    response = jsonrpc.get_settings()
    if not response:
        return None

    logging_enabled = True
    for item in response['result']['settings']:
        if item['id'] == 'debug.showloginfo':
            logging_enabled = item['value'] is True
            break

    if (not enable and logging_enabled) or (enable and not logging_enabled):
        response = jsonrpc.debug_show_log_info(enable is True)
        if not response:
            return None

        logging_enabled = not logging_enabled

    return logging_enabled == enable


def enable_logging():
    system_debug = False
    script_debug = False
    if system_debug:
        system_debug = toggle_debug_logging(enable=True) is True
    if script_debug:
        ADDON.setSettingBool('enable_logging', True)
        script_debug = True

    return system_debug, script_debug


def disable_logging(system_debug, script_debug):
    if system_debug or script_debug:
        # Disable any logging we enabled
        if system_debug:
            toggle_debug_logging(enable=False)
        if script_debug:
            ADDON.setSettingBool('enable_logging', False)


def offer_log_upload(message_id):
    result = False
    dialog = xbmcgui.Dialog()

    # Offer to upload a debug log
    if xbmc.getCondVisibility('System.HasAddon(script.kodi.loguploader)'):
        result = dialog.yesno(ADDON_NAME, '[CR]'.join([LANGUAGE(message_id), LANGUAGE(32093)]))
        if result:
            xbmc.executebuiltin('RunScript(script.kodi.loguploader)')

    else:
        dialog.ok(ADDON_NAME, '[CR]'.join([LANGUAGE(message_id), LANGUAGE(32094)]))

    return result is True
