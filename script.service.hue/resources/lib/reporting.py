#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import platform
import sys
import traceback


import rollbar
import xbmc
import xbmcgui
from qhue import QhueException
from requests import RequestException

from . import ADDONVERSION, ROLLBAR_API_KEY, KODIVERSION, ADDONPATH, ADDON
from .kodiutils import notification
from .language import get_string as _


def process_exception(exc, level="critical", error=""):
    xbmc.log(f"[script.service.hue] Exception: {type(exc)}, {exc}, {error}, {traceback.format_exc()}")

    if type(exc) == QhueException and exc.type_id in ["3", "7"]:  # 3: resource not found, 7: invalid value for parameter
        xbmc.log("[script.service.hue] Qhue resource not found, not reporting to rollbar")
        notification(_("Hue Service"), _("ERROR: Scene or Light not found, it may have changed or been deleted. Check your configuration."), icon=xbmcgui.NOTIFICATION_ERROR)
    elif type(exc) == RequestException:
        xbmc.log("[script.service.hue] RequestException, not reporting to rollbar")
        notification(_("Hue Service"), _("Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
    else:
        if ADDON.getSettingBool("error_reporting"):
            if _error_report_dialog(exc):
                _report_error(level, error, exc)


def _error_report_dialog(exc):
    response = xbmcgui.Dialog().yesnocustom(heading=_("Hue Service Error"), message=_("The following error occurred:") + f"\n[COLOR=red]{exc}[/COLOR]\n" + _("Automatically report this error?"), customlabel=_("Never report errors"))
    if response == 2:
        xbmc.log("[script.service.hue] Error Reporting disabled")
        ADDON.setSettingBool("error_reporting", False)
        return False
    return response


def _report_error(level="critical", error="", exc=""):
    if any(val in ADDONVERSION for val in ["dev", "alpha", "beta"]):
        env = "dev"
    else:
        env = "production"

    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
        'error': error,
        'exc': exc
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip=False, code_version="v" + ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser, bridgeIP, bridge_user, bridge_ip, server.host', environment=env)
    rollbar.report_exc_info(sys.exc_info(), extra_data=data, level=level)
