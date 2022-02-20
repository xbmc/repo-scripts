import collections
from collections import abc
import json
import xbmc
import xbmcaddon
from datetime import datetime
from urllib.parse import parse_qs

try:
    # The result is not needed, it is just to prep the datetime module
    # to avoid ImportError from datetime.now()
    datetime.strptime('2112-04-01', '%Y-%m-%d')
except TypeError:
    # With the error, datetime.now() MAY still encounter an ImportError,
    #  use pykodi.datetime_now() to sleep it off
    # REVIEW: does this still happen in py3?
    pass

_main_addon = None
def get_main_addon():
    global _main_addon
    if not _main_addon:
        _main_addon = xbmcaddon.Addon()
    return _main_addon

def localize(messageid):
    if isinstance(messageid, str):
        return messageid
    if messageid >= 32000 and messageid < 33000:
        return get_main_addon().getLocalizedString(messageid)
    return xbmc.getLocalizedString(messageid)

def datetime_now():
    ''' Catches ImportError (due to an import lock) and sleeps it off. '''
    # REVIEW: does this still happen in py3?
    try:
        return datetime.now()
    except ImportError:
        xbmc.sleep(50)
        return datetime_now()

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command)

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json.loads(json_result)

def get_base_json_request(method):
    return {'jsonrpc': '2.0', 'method': method, 'params': {}, 'id': 1}

ignoredtypes = ('', 'addons', 'sources', 'plugin')
def get_pathinfo(path):
    result = {}
    if path.startswith('/') or '://' not in path:
        path_type = 'other'
        query = None
    else:
        path_type, db_path = path.split('://', 1)
        db_path = db_path.split('?', 1)
        query = parse_qs(db_path[1]) if len(db_path) > 1 else None
        db_path = db_path[0].rstrip('/').split('/')
        result['path'] = db_path

    if path_type in ignoredtypes:
        return
    if query and query.get('xsp'):
        try:
            query['xsp'] = json.loads(query['xsp'][0])
        except ValueError:
            del query['xsp']

    result['type'] = path_type
    if query:
        result['query'] = query

    return result

def log(message, level=xbmc.LOGDEBUG):
    if not isinstance(message, str):
        message = json.dumps(message, cls=LogJSONEncoder)

    file_message = '[%s] %s' % (get_main_addon().getAddonInfo('id'), message)
    xbmc.log(file_message, level)

def get_busydialog():
    return DialogBusy()

class LogJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['skipkeys'] = True
        kwargs['ensure_ascii'] = False
        kwargs['indent'] = 2
        kwargs['separators'] = (',', ': ')
        super(LogJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, abc.Mapping):
            return dict((key, obj[key]) for key in obj.keys())
        if isinstance(obj, collections.Iterable):
            return list(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

class DialogBusy(object):
    def __init__(self):
        self.visible = False
        window = 'busydialognocancel'
        self._activate = 'ActivateWindow({0})'.format(window)
        self._close = 'Dialog.Close({0})'.format(window)

    def create(self):
        xbmc.executebuiltin(self._activate)
        self.visible = True

    def close(self):
        xbmc.executebuiltin(self._close)
        self.visible = False

    def __del__(self):
        if self.visible:
            try:
                xbmc.executebuiltin(self._close)
            except AttributeError:
                pass
