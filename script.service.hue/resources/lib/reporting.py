import json
import platform
import sys

import xbmc
import xbmcgui

import rollbar
from . import logger, ADDON, ADDONVERSION, ROLLBAR_API_KEY, ADDONID,KODIVERSION, ADDONPATH

def _kodi_version():
    query = dict(jsonrpc='2.0',
                 method='Application.GetProperties',
                 params=dict(properties=['version', 'name']),
                 id=1)
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response['result']['version']


def error_report_requested(exc):
    return xbmcgui.Dialog().yesno(
        heading="{} {}".format(ADDONID, ADDON.getLocalizedString(30043)),
        message=ADDON.getLocalizedString(30080) +
        "\n[COLOR=red]{}[/COLOR]\n".format(exc) +
        ADDON.getLocalizedString(30081)
    )


def report_error(url=None):
    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
        #'kodi': _kodi_version(),
        'url': url,
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip="anonymize", code_version=ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser')
    rollbar.report_exc_info(sys.exc_info(), extra_data=data)


def process_exception(exc):
    if error_report_requested(exc):
        report_error()
