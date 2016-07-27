import collections
import sys
import xbmc

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

movie_properties = ['imdbnumber', 'tag']

nostingertags_filter = {'and': [{'field': 'tag', 'operator':'isnot', 'value':'duringcreditsstinger'}, {'field': 'tag', 'operator':'isnot', 'value':'aftercreditsstinger'}]}

def get_movies(sort_method='sorttitle', ascending=True, limit=None, properties=None, listfilter=None):
    json_request = get_base_json_request('VideoLibrary.GetMovies')
    json_request['params']['properties'] = properties if properties != None else movie_properties
    json_request['params']['sort'] = {'method': sort_method, 'order': 'ascending' if ascending else 'descending'}
    if listfilter:
        json_request['params']['filter'] = listfilter
    if limit:
        json_request['params']['limits'] = {'end': limit}

    json_result = execute_jsonrpc(json_request)
    if _check_json_result(json_result, 'movies', json_request):
        return json_result['result']['movies']
    else:
        return []

def get_movie_details(movie_id, properties=None):
    json_request = get_base_json_request('VideoLibrary.GetMovieDetails')
    json_request['params']['movieid'] = movie_id
    json_request['params']['properties'] = properties if properties != None else movie_properties

    json_result = json.loads(xbmc.executeJSONRPC(json.dumps(json_request)))

    if _check_json_result(json_result, 'moviedetails', json_request):
        return json_result['result']['moviedetails']

def set_movie_details(movie_id, **movie_details):
    json_request = get_base_json_request('VideoLibrary.SetMovieDetails')
    json_request['params']['movieid'] = movie_id
    for param, value in movie_details.iteritems():
        json_request['params'][param] = value

    json_result = execute_jsonrpc(json_request)
    _check_json_result(json_result, 'OK', json_request)

def get_base_json_request(method):
    return {'jsonrpc': '2.0', 'method': method, 'params': {}, 'id': 1}

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command)

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json.loads(json_result, cls=UTF8JSONDecoder)

def _check_json_result(json_result, result_key, json_request):
    if 'error' in json_result:
        raise JSONException(json_request, json_result)

    return 'result' in json_result and result_key in json_result['result']

class JSONException(Exception):
    def __init__(self, json_request, json_result):
        self.json_request = json_request
        self.json_result = json_result

        message = "There was an error with a JSON-RPC request.\nRequest: "
        message += json.dumps(json_request, skipkeys=True, ensure_ascii=False, indent=2, cls=LogJSONEncoder)
        message += "\nResult: "
        message += json.dumps(json_result, skipkeys=True, ensure_ascii=False, indent=2, cls=LogJSONEncoder)

        if isinstance(message, unicode):
            message = message.encode('utf-8')
        super(JSONException, self).__init__(message)

class LogJSONEncoder(json.JSONEncoder):
    def default(self, obj):
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
