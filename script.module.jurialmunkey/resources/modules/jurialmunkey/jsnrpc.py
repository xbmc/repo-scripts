from xbmc import executeJSONRPC
from jurialmunkey.parser import try_int


def get_jsonrpc(method=None, params=None, query_id=1):
    if not method:
        return {}
    query = {
        "jsonrpc": "2.0",
        "method": method,
        "id": query_id}
    if params:
        query["params"] = params
    try:
        from json import dumps, loads
        jrpc = executeJSONRPC(dumps(query))
        response = loads(jrpc)
    except Exception as exc:
        from jurialmunkey.logger import Logger
        Logger(log_name='[script.module.jurialmunkey]').kodi_log(f'JSONRPC Error:\n{exc}', 1)
        response = {}
    if 'error' in response:
        from jurialmunkey.logger import Logger
        Logger(log_name='[script.module.jurialmunkey]').kodi_log(f'JSONRPC Error:\n{query}\n{response}', 1)
    return response


def get_library(dbtype=None, properties=None, filterr=None):
    if dbtype == "movie":
        method = "VideoLibrary.GetMovies"
    elif dbtype == "tvshow":
        method = "VideoLibrary.GetTVShows"
    elif dbtype == "episode":
        method = "VideoLibrary.GetEpisodes"
    else:
        return

    params = {"properties": properties or ["title"]}
    if filterr:
        params['filter'] = filterr

    response = get_jsonrpc(method, params)
    return response.get('result')


def get_num_credits(dbtype, person):
    if dbtype == 'movie':
        filterr = {
            "or": [
                {"field": "actor", "operator": "contains", "value": person},
                {"field": "director", "operator": "contains", "value": person},
                {"field": "writers", "operator": "contains", "value": person}]}
    elif dbtype == 'tvshow':
        filterr = {
            "or": [
                {"field": "actor", "operator": "contains", "value": person},
                {"field": "director", "operator": "contains", "value": person}]}
    elif dbtype == 'episode':
        filterr = {
            "or": [
                {"field": "actor", "operator": "contains", "value": person},
                {"field": "director", "operator": "contains", "value": person},
                {"field": "writers", "operator": "contains", "value": person}]}
    else:
        return
    response = get_library(dbtype, filterr=filterr)
    try:
        return response['limits']['total']
    except (AttributeError, KeyError):
        return 0


def get_details(dbid, dbtype, key):
    json_info = get_jsonrpc(
        method=f'VideoLibrary.Get{dbtype.capitalize()}Details',
        params={f'{dbtype}id': dbid, "properties": [key]})
    try:
        return json_info['result'][f'{dbtype}details'][key]
    except (AttributeError, KeyError):
        return


def set_tags(dbid=None, dbtype=None, tags=None):
    if not dbid or not dbtype or not tags:
        return

    old_db_tags = set(get_details(dbid, dbtype, key='tag') or [])
    new_db_tags = old_db_tags | set(tags)

    if new_db_tags == old_db_tags:
        return

    return get_jsonrpc(
        method=f'VideoLibrary.Set{dbtype.capitalize()}Details',
        params={f'{dbtype}id': dbid, "tag": list(new_db_tags)})


def set_watched(dbid=None, dbtype=None, plays=1):
    if not dbid or not dbtype:
        return

    playcount = get_details(dbid, dbtype, key='playcount') or 0
    playcount = try_int(playcount) + plays

    return get_jsonrpc(
        method=f'VideoLibrary.Set{dbtype.capitalize()}Details',
        params={f'{dbtype}id': dbid, "playcount": playcount})


def set_playprogress(filename, position, total):
    method = "Files.SetFileDetails"
    params = {"file": filename, "media": "video", "resume": {"position": position, "total": total}}
    return get_jsonrpc(method=method, params=params)


def get_directory(url, properties=None):
    method = "Files.GetDirectory"
    properties = properties or [
        "title", "year", "originaltitle", "imdbnumber", "premiered", "streamdetails", "size",
        "firstaired", "season", "episode", "showtitle", "file", "tvshowid", "thumbnail"]
    params = {
        "directory": url,
        "media": "files",
        "properties": properties}
    response = get_jsonrpc(method, params)
    try:
        return response['result']['files'] or [{}]
    except KeyError:
        return [{}]
