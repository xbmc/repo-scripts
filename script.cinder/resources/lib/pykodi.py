import collections
import sys
import xbmc
import xbmcaddon

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command, ensure_ascii=False)
        if isinstance(jsonrpc_command, unicode):
            jsonrpc_command = jsonrpc_command.encode('utf-8')

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json.loads(json_result, cls=UTF8JSONDecoder)

def get_base_json_request(method):
    return {'jsonrpc': '2.0', 'method': method, 'params': {}, 'id': 1}

def log(message, level=xbmc.LOGDEBUG):
    addonid = xbmcaddon.Addon().getAddonInfo('id')

    if isinstance(message, (dict, list, tuple)):
        message = json.dumps(message, skipkeys=True, ensure_ascii=False, indent=2, cls=LogJSONEncoder)
        if isinstance(message, unicode):
            message = message.encode('utf-8')
    elif isinstance(message, unicode):
        message = message.encode('utf-8')
    elif not isinstance(message, str):
        message = str(message)

    file_message = '[%s] %s' % (addonid, message)
    xbmc.log(file_message, level)

class LogJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (dict, list, basestring)):
            return obj
        if isinstance(obj, collections.Mapping):
            return dict((key, obj[key]) for key in obj.keys())
        if isinstance(obj, collections.Iterable):
            return list(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

class UTF8JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(UTF8JSONDecoder, self).__init__(*args, **kwargs)

    def raw_decode(self, s, idx=0):
        result, end = super(UTF8JSONDecoder, self).raw_decode(s)
        result = self._json_unicode_to_str(result)
        return result, end

    def _json_unicode_to_str(self, jsoninput):
        if isinstance(jsoninput, dict):
            return dict((self._json_unicode_to_str(key), self._json_unicode_to_str(value)) for key, value in jsoninput.iteritems())
        elif isinstance(jsoninput, list):
            return [self._json_unicode_to_str(item) for item in jsoninput]
        elif isinstance(jsoninput, unicode):
            return jsoninput.encode('utf-8')
        else:
            return jsoninput
