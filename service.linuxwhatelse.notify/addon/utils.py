import json

import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()


def translate(id):
    return addon.getLocalizedString(id)


def log(*args, **kwargs):
    if not kwargs or 'lvl' not in kwargs:
        lvl = xbmc.LOGDEBUG

    else:
        lvl = kwargs['lvl']

    msg = '[%s] ' % addon.getAddonInfo('id')
    msg += ' '.join(str(x) for x in args)

    xbmc.log(msg, level=lvl)


def execute_jsonrpc(method, params=None):
    data = {}
    data['id'] = 1
    data['jsonrpc'] = '2.0'
    data['method'] = method
    if params:
        data['params'] = params

    data = json.dumps(data)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)

    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']

        return response

    except KeyError:
        return None
