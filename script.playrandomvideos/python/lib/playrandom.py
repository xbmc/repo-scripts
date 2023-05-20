import xbmcgui
from datetime import timedelta

from . import quickjson
from .pykodi import datetime_now, get_main_addon, localize as L
from .player import get_player
from .generators import get_generator

SELECTWATCHMODE_HEADING = 32010
WATCHMODE_ALLVIDEOS_TEXT = 16100
WATCHMODE_UNWATCHED_TEXT = 16101
WATCHMODE_WATCHED_TEXT = 16102
WATCHMODE_WATCHEDBEFORE_TEXT = 32910
WATCHMODE_ASKME_TEXT = 36521
ADD_SOURCE_HEADER = 32011
ADD_SOURCE_MESSAGE = 32012

WATCHMODE_ALLVIDEOS = 'all videos'
WATCHMODE_UNWATCHED = 'unwatched'
WATCHMODE_WATCHED = 'watched'
WATCHMODE_WATCHEDBEFORE = 'watched before'
WATCHMODE_ASKME = 'ask me'
# Same order as settings
WATCHMODES = (WATCHMODE_ALLVIDEOS, WATCHMODE_UNWATCHED, WATCHMODE_WATCHED, WATCHMODE_WATCHEDBEFORE, WATCHMODE_ASKME)
WATCHMODE_NONE = 'none'

unplayed_filter = {'field': 'playcount', 'operator': 'is', 'value': '0'}
played_filter = {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}
noextras_filter = {'field': 'season', 'operator': 'isnot', 'value': '0'}


def play(pathinfo):
    content, info = _parse_path(pathinfo)
    if not content:
        xbmcgui.Dialog().notification(L(34201), pathinfo['full path'])
        return
    singlevideo = pathinfo.get('singlevideo', False)
    showbusy = get_main_addon().getSetting('hidebusydialog') == 'false'
    try:
        get_player(get_generator(content, info, singlevideo), showbusy).run()
    except quickjson.JSONException as ex:
        # json_result['error']['code'] == -32602 is the best we get, invalid params
        if content == 'other' and ex.json_result.get('error', {}).get('code', 0) == -32602 \
                and not any(1 for source in quickjson.get_sources('video') if info['path'].startswith(source['file'])):
            xbmcgui.Dialog().ok(L(ADD_SOURCE_HEADER), L(ADD_SOURCE_MESSAGE).format(info['path']))
        else:
            raise

def _build_watched_before_filter(content):
    # Don't play video that has been watched in the past x months
    if content == "tvshows":
        months = int(get_main_addon().getSetting('tvplayedmonths'))
    if content == "movies":
        months = int(get_main_addon().getSetting('movieplayedmonths'))

    # jsonrpc stopped playing nicely when combining 'notinthelast' with the other operators in our filter, so falling back to 'lessthan'
    #lastwatched_filter = {'field': 'lastplayed', 'operator': 'notinthelast', 'value': months*30}
    watchbeforedate = (datetime_now() - timedelta(days=months*30)).isoformat(' ')
    lastwatched_filter = {'field': 'lastplayed', 'operator': 'lessthan', 'value': watchbeforedate}
    return lastwatched_filter

def _parse_path(pathinfo):
    content = None
    skip_path = False
    result = {}
    filters = []
    if pathinfo['type'] == 'videodb':
        path_len = len(pathinfo['path'])
        firstpath = pathinfo['path'][0] if path_len else None
        content = firstpath
        if not path_len:
            skip_path = True
        elif path_len > 1:
            category = pathinfo['path'][1]
            if firstpath in ('tvshows', 'inprogresstvshows'):
                content = 'tvshows'
                seriesfilter = None
                if category == 'titles' and path_len <= 2:
                    # 'xsp' 'rules' are passed from library nodes
                    if _has_xsprules(pathinfo):
                        seriesfilter = pathinfo['query']['xsp']['rules']
                elif category == 'titles' or path_len > 3 or firstpath == 'inprogresstvshows':
                    # points to specific show, disregard any series filter
                    index_of_tvshowid = 1 if firstpath == 'inprogresstvshows' else \
                        2 if category == 'titles' else 3

                    if path_len > index_of_tvshowid:
                        result['tvshowid'] = int(pathinfo['path'][index_of_tvshowid])
                    if path_len > index_of_tvshowid + 1:
                        season = int(pathinfo['path'][index_of_tvshowid + 1])
                        if season >= 0:
                            result['season'] = season
                elif path_len > 2:
                    # contains series filter criteria
                    seriesfilter = _filter_from_path(category, pathinfo)

                if seriesfilter:
                    filters.append({'field': 'tvshow', 'operator': 'is', 'value':
                        [series['label'] for series in quickjson.get_tvshows(seriesfilter)]})
            elif firstpath in ('movies', 'musicvideos'):
                if category == 'titles':
                    if _has_xsprules(pathinfo):
                        filters.append(pathinfo['query']['xsp']['rules'])
                elif path_len > 2:
                    filters.append(_filter_from_path(category, pathinfo))
        elif firstpath == 'inprogresstvshows': # added in Krypton
            content = 'tvshows'
            filters.append({'field': 'tvshow', 'operator': 'is', 'value': [series['label'] for series
                in quickjson.get_tvshows({'field': 'inprogress', 'operator':'true', 'value':''})]})
    elif pathinfo['type'] == 'library':
        path_len = len(pathinfo['path'])
        # TODO: read these from the actual XML files? This falls apart when Kodi changes them
        #  or even when the viewer changes nodes!
        if path_len < 2:
            skip_path = True
        elif 'inprogressshows.xml' in pathinfo['path']:
            content = 'tvshows'
            filters.append({'field': 'tvshow', 'operator': 'is', 'value': [series['label'] for series
                in quickjson.get_tvshows({'field': 'inprogress', 'operator':'true', 'value':''})]})
        elif any(1 for p in ('recentlyaddedmovies.xml', 'recentlyaddedepisodes.xml',
                'recentlyaddedmusicvideos.xml') if p in pathinfo['path']):
            content = 'other'
            result['path'] = pathinfo['full path']
        elif pathinfo['path'][1] == 'tvshows':
            content = 'tvshows'
        elif pathinfo['path'][1] == 'movies':
            content = 'movies'
        elif pathinfo['path'][1] == 'musicvideos':
            content = 'musicvideos'
        elif pathinfo['path'][1] in ('files.xml', 'playlists.xml', 'addons.xml'):
            skip_path = True
    elif pathinfo['type'] == 'special':
        # TODO: Playlists could also be usefully parsed
        if not pathinfo['path'] or pathinfo['path'][0] == 'videoplaylists':
            skip_path = True

    if skip_path:
        return None, None

    if not content:
        content = 'other'
        result['path'] = pathinfo['full path']

    # DEPRECATED: forcewatchmode is deprecated in 1.1.0
    watchmode = _get_watchmode(pathinfo.get('watchmode') or pathinfo.get('forcewatchmode'), content)
    result['watchmode'] = watchmode
    if watchmode == WATCHMODE_NONE:
        return None, None

    if watchmode == WATCHMODE_UNWATCHED:
        filters.append(unplayed_filter)
    elif watchmode == WATCHMODE_WATCHED:
        filters.append(played_filter)
    elif watchmode == WATCHMODE_WATCHEDBEFORE:
        lastwatched_filter = _build_watched_before_filter(content)
        filters.append(lastwatched_filter)

    if content == 'tvshows' and get_main_addon().getSetting('exclude_extras') == 'true':
        filters.append(noextras_filter)
    if get_main_addon().getSetting('continuous_play') == 'true':
        result['continuous_play'] = True
    if get_main_addon().getSetting('fallback_watchedstatus') == 'true':
        result['fallback_watchedstatus'] = True

    if filters:
        result['filters'] = filters
    return (content, result)

def _get_pathcategory(category):
    if category == 'countries':
        return 'country'
    if category in ('genres', 'years', 'actors', 'studios', 'tags', 'directors', 'sets', 'artists', 'albums'):
        return category[:-1]
    return category

def _filter_from_path(category, pathinfo):
    value = pathinfo.get('label', pathinfo['path'][2] if len(pathinfo['path']) > 2 else '?')
    return {'field': _get_pathcategory(category), 'operator': 'is', 'value': value}

def _has_xsprules(pathinfo):
    return 'query' in pathinfo and 'xsp' in pathinfo['query'] and 'rules' in pathinfo['query']['xsp']

def _get_watchmode(pathwatchmode, content):
    watchmode = None
    if pathwatchmode:
        # skip 'all videos' from path, prefer add-on settings
        if pathwatchmode.lower() in (WATCHMODE_UNWATCHED, WATCHMODE_WATCHED, WATCHMODE_WATCHEDBEFORE, WATCHMODE_ASKME):
            watchmode = pathwatchmode.lower()
        elif pathwatchmode == L(WATCHMODE_UNWATCHED_TEXT):
            watchmode = WATCHMODE_UNWATCHED
        elif pathwatchmode == L(WATCHMODE_WATCHED_TEXT):
            watchmode = WATCHMODE_WATCHED
        elif pathwatchmode == L(WATCHMODE_WATCHEDBEFORE_TEXT):
            watchmode == WATCHMODE_WATCHEDBEFORE
        elif pathwatchmode == L(WATCHMODE_ASKME_TEXT):
            watchmode = WATCHMODE_ASKME

    if not watchmode:
        addonsetting = ('watchmodemovies' if content == 'movies' else
            'watchmodetvshows' if content == 'tvshows' else
            'watchmodemusicvideos' if content == 'musicvideos' else
            'watchmodeother' if content == 'other' else None)

        if addonsetting:
            try:
                watchmode = WATCHMODES[int(get_main_addon().getSetting(addonsetting))]
            except ValueError:
                pass

    if watchmode == WATCHMODE_ASKME:
        return _ask_me()
    elif watchmode:
        return watchmode
    else:
        return WATCHMODE_ALLVIDEOS

def _ask_me():
    options = [L(WATCHMODE_ALLVIDEOS_TEXT), L(WATCHMODE_UNWATCHED_TEXT), L(WATCHMODE_WATCHED_TEXT)]
    selectedindex = xbmcgui.Dialog().select(L(SELECTWATCHMODE_HEADING), options)

    if selectedindex == 0:
        return WATCHMODE_ALLVIDEOS
    elif selectedindex == 1:
        return WATCHMODE_UNWATCHED
    elif selectedindex == 2:
        return WATCHMODE_WATCHED
    else:
        return WATCHMODE_NONE
