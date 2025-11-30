#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import platform
import sys
import traceback

import rollbar
import xbmcgui

from . import ADDONVERSION, ROLLBAR_API_KEY, KODIVERSION, ADDONPATH, ADDON
from .language import get_string as _
from .kodiutils import log


def process_exception(exc, level="critical", error="", logging=False):
    log(f"[SCRIPT.SERVICE.HUE] *** EXCEPTION ***:  Type: {type(exc)},\n Exception: {exc},\n Error: {error},\n Traceback: {traceback.format_exc()}")
    if ADDON.getSettingBool("error_reporting"):
        if _error_report_dialog(exc):
            _report_error(level, error, exc, logging)

'''
    if exc is RequestException:
        log("[SCRIPT.SERVICE.HUE] RequestException, not reporting to rollbar")
        notification(_("Hue Service"), _("Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
    else:
'''


def _error_report_dialog(exc):
    response = xbmcgui.Dialog().yesnocustom(heading=_("Hue Service Error"), message=_("The following error occurred:") + f"\n[COLOR=red]{exc}[/COLOR]\n" + _("Automatically report this error?"), customlabel=_("Never report errors"))
    if response == 2:
        log("[SCRIPT.SERVICE.HUE] Error Reporting disabled")
        ADDON.setSettingBool("error_reporting", False)
        return False
    return response


def _report_error(level="critical", error="", exc="", logging=False):
    if any(val in ADDONVERSION for val in ["dev", "alpha", "beta"]):
        env = "dev"
    else:
        env = "production"

    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
        'error': error,
        'exc': traceback.format_exc()
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip=False, code_version="v" + ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser, bridgeIP, bridge_user, bridge_ip, server.host', environment=env, handler="thread")
    if logging:
        rollbar.report_message(exc, extra_data=data, level=level)
    else:
        rollbar.report_exc_info(sys.exc_info(), extra_data=data, level=level)
