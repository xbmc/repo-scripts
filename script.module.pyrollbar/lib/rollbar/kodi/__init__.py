import json
import platform

import xbmc
import xbmcaddon
import xbmcgui

import rollbar


addon = xbmcaddon.Addon('script.module.pyrollbar')


def _kodi_version():
    query = dict(jsonrpc='2.0',
                 method='Application.GetProperties',
                 params=dict(properties=['version', 'name']),
                 id=1)
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response['result']['version']


def error_report_requested(exc):
    return xbmcgui.Dialog().yesno(
        addon.getLocalizedString(32001),
        addon.getLocalizedString(32002),
        "[COLOR=red]{}[/COLOR]".format(exc),
        addon.getLocalizedString(32003)
    )


def report_error(access_token, version=None, url=None):
    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': _kodi_version(),
        'url': url,
    }
    rollbar.init(access_token, code_version=version)
    rollbar.report_exc_info(extra_data=data)
