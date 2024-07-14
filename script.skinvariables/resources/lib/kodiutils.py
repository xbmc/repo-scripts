# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmcgui
import jurialmunkey.logger as jurialmunkey_logger
import jurialmunkey.plugin as jurialmunkey_plugin
import jurialmunkey.dialog as jurialmunkey_dialog
from contextlib import contextmanager


KODIPLUGIN = jurialmunkey_plugin.KodiPlugin('script.skinvariables')
ADDON = KODIPLUGIN._addon
get_localized = KODIPLUGIN.get_localized


LOGGER = jurialmunkey_logger.Logger(
    log_name='script.skinvariables - ',
    notification_head=f'SkinVariables {get_localized(257)}',
    notification_text=get_localized(2104),
    debug_logging=False)
kodi_log = LOGGER.kodi_log
BusyDialog = jurialmunkey_dialog.BusyDialog
busy_decorator = jurialmunkey_dialog.busy_decorator


@contextmanager
def isactive_winprop(name, value='True', windowid=10000):
    xbmcgui.Window(windowid).setProperty(name, value)
    try:
        yield
    finally:
        xbmcgui.Window(windowid).clearProperty(name)


class ProgressDialog(jurialmunkey_dialog.ProgressDialog):
    @staticmethod
    def kodi_log(msg, level=0):
        kodi_log(msg, level)
