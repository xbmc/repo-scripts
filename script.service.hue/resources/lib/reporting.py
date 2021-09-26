import platform
import sys

import rollbar
import xbmc
import xbmcgui

from resources.lib import ADDONVERSION, ROLLBAR_API_KEY, KODIVERSION, ADDONPATH, ADDON
from resources.lib.language import get_string as _


def process_exception(exc, level="critical"):
    if ADDON.getSettingBool("error_reporting"):
        if _error_report_dialog(exc):
            _report_error(level)


def _error_report_dialog(exc):
    response = xbmcgui.Dialog().yesnocustom(heading=_("Hue Service Error"), message=_("The following error occurred:") + f"\n[COLOR=red]{exc}[/COLOR]\n" + _("Automatically report this error?"), customlabel=_("Never report errors"))
    if response == 2:
        xbmc.log("[script.service.hue] Error Reporting disabled")
        ADDON.setSettingBool("error_reporting", False)
        return False
    return response


def _report_error(level="critical"):
    if "dev" in ADDONVERSION:
        env = "dev"
    else:
        env = "production"

    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip=False, code_version=ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser, bridgeIP', environment=env)
    rollbar.report_exc_info(sys.exc_info(), extra_data=data, level=level)
