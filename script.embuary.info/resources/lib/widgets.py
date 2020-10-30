#!/usr/bin/python
# coding: utf-8

########################

import routing
from xbmcgui import ListItem
from xbmcplugin import *
from datetime import date

from resources.lib.helper import *
from resources.lib.tmdb import *
from resources.lib.trakt import *
from resources.lib.localdb import *
from resources.lib.nextaired import *

########################

INDEX_MENU = {
    'discover': {
        'name': 'The Movie DB - ' + ADDON.getLocalizedString(32049),
        'route': 'discover',
        'folder': True,
        'menu': [
            { 'name': ADDON.getLocalizedString(32050), 'call': 'movie'},
            { 'name': ADDON.getLocalizedString(32051), 'call': 'tv' },
            { 'name': ADDON.getLocalizedString(32057), 'call': 'person' }
        ]
    },
    'movie': {
        'name': 'The Movie DB - ' + xbmc.getLocalizedString(342),
        'route': 'movie_listing',
        'folder': True,
        'menu': [
            { 'name': ADDON.getLocalizedString(32042), 'call': 'trending' },
            { 'name': ADDON.getLocalizedString(32029), 'call': 'top_rated' },
            { 'name': ADDON.getLocalizedString(32030), 'call': 'now_playing' },
            { 'name': ADDON.getLocalizedString(32031), 'call': 'upcoming' },
            { 'name': ADDON.getLocalizedString(32032), 'call': 'popular' },
        ]
    },
    'tv': {
        'name': 'The Movie DB - ' + xbmc.getLocalizedString(20343),
        'route': 'tv_listing',
        'folder': True,
        'menu': [
            { 'name': ADDON.getLocalizedString(32043), 'call': 'trending' },
            { 'name': ADDON.getLocalizedString(32033), 'call': 'top_rated' },
            { 'name': ADDON.getLocalizedString(32034), 'call': 'popular' },
            { 'name': ADDON.getLocalizedString(32035), 'call': 'airing_today' },
            { 'name': ADDON.getLocalizedString(32036), 'call': 'on_the_air' }
        ]
    },
    'nextaired': {
        'name': 'Trakt.tv - ' + ADDON.getLocalizedString(32059),
        'route': 'nextaired',
        'folder': True,
        'menu': [
            { 'name': ADDON.getLocalizedString(32058), 'day': 'week' },
            { 'name': xbmc.getLocalizedString(33006), 'day': 'today' },
        ],
        'days': [
            xbmc.getLocalizedString(11),
            xbmc.getLocalizedString(12),
            xbmc.getLocalizedString(13),
            xbmc.getLocalizedString(14),
            xbmc.getLocalizedString(15),
            xbmc.getLocalizedString(16),
            xbmc.getLocalizedString(17)
        ]
    },
    'search': {
        'name': xbmc.getLocalizedString(137),
        'route': 'search',
        'folder': False
    }
}

DISCOVER_INDEX = {
    'movie': [
        { 'name': ADDON.getLocalizedString(32050), 'option': 'all' },
        { 'name': ADDON.getLocalizedString(32052), 'option': 'year', 'param': 'year' },
        { 'name': ADDON.getLocalizedString(32053), 'option': 'genre', 'param': 'with_genres' },
    ],
    'tv': [
        { 'name': ADDON.getLocalizedString(32051), 'option': 'all' },
        { 'name': ADDON.getLocalizedString(32054), 'option': 'year', 'parmam': 'first_air_date_year' },
        { 'name': ADDON.getLocalizedString(32055), 'option': 'genre', 'param': 'with_genres' }
    ]
}

DEFAULT_ART = {
    'icon': 'DefaultFolder.png',
    'thumb': 'special://home/addons/script.embuary.info/resources/icon.png'
}

########################

plugin = routing.Plugin()

# entrypoint
@plugin.route('/')
def index():
    for i in ['discover', 'movie', 'tv', 'nextaired', 'search']:
        item =  INDEX_MENU[i]
        li_item = ListItem(item['name'])
        li_item.setArt(DEFAULT_ART)
        xbmcplugin.addDirectoryItem(plugin.handle,
                         plugin.url_for(eval(item['route'])),
                         li_item, item['folder'])

    _sortmethods()
    xbmcplugin.endOfDirectory(plugin.handle)


# actions
@plugin.route('/info/<call>/<idtype>/<tmdbid>')
def dialog(call,idtype,tmdbid):
    if idtype == 'tmdb':
        execute('RunScript(script.embuary.info,call=%s,tmdb_id=%s)' % (call, tmdbid))
    elif idtype == 'external':
        execute('RunScript(script.embuary.info,call=%s,external_id=%s)' % (call, tmdbid))


@plugin.route('/search')
def search():
    execute('RunScript(script.embuary.info)')


# next aired
@plugin.route('/nextaired')
@plugin.route('/nextaired/<day>')
def nextaired(day=None):
    if not day:
        for i in INDEX_MENU['nextaired'].get('menu'):
            li_item = ListItem(i.get('name'))
            li_item.setArt(DEFAULT_ART)
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(nextaired, i.get('day')),
                             li_item, True)

        utc = arrow.utcnow()
        local_date = utc.to(TIMEZONE)

        kodi_locale = json_call('Settings.GetSettingValue', params={'setting': 'locale.language'})
        kodi_locale = kodi_locale['result']['value'][-5:]

        for i in range(6):
            local_date = local_date.shift(days=1)
            translated_date = local_date.format(fmt='dddd, D. MMMM YYYY', locale=kodi_locale)
            tmp_day_str, tmp_day = date_weekday(local_date)

            li_item = ListItem(translated_date)
            li_item.setArt(DEFAULT_ART)
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(nextaired, tmp_day),
                             li_item, True)

        _category(category=INDEX_MENU['nextaired']['name'])

    else:
        _nextaired(day)

    _sortmethods()
    xbmcplugin.endOfDirectory(plugin.handle)

def _nextaired(day):
    if day == 'today':
        day_str, day = date_weekday()

    next_aired = NextAired()
    next_aired_results = next_aired.get(str(day))

    if day == 'week':
        next_aired_results = sort_dict(next_aired_results, 'airing')

    #log(next_aired_results,force=True,json=True)

    for i in next_aired_results:
        try:

            if day != 'week' and day is not None:
                label = '%s %sx%s. %s' % (i['showtitle'], i['season_number'], i['episode_number'], i['name'])
            else:
                kodi_date = date_format(i['airing'])
                label = '%s, %s: %s %sx%s. %s' % (i['weekday'], kodi_date, i['showtitle'], i['season_number'], i['episode_number'], i['name'])

            season = str(i.get('season_number', ''))
            episode = str(i.get('episode_number', ''))
            airing_date = i.get('airing', '')
            airing_time = i.get('airing_time', '')
            plot = i.get('overview') or xbmc.getLocalizedString(19055)

            overview = [date_format(airing_date) + ' ' + airing_time, plot]
            overview ='[CR]'.join(filter(None, overview))

            thumb = IMAGEPATH + i.get('still_path') if i.get('still_path') else ''
            if not thumb:
                thumb = i['localart'].get('landscape') or i['localart'].get('fanart') or ''

            li_item = ListItem(label)
            li_item.setArt(i.get('localart'))
            li_item.setArt({'icon': 'DefaultVideo.png', 'thumb': thumb})
            li_item.setInfo('video', {'title': i.get('name') or xbmc.getLocalizedString(13205),
                                      'tvshowtitle': i.get('showtitle') or xbmc.getLocalizedString(13205),
                                      'plot': overview,
                                      'premiered': airing_date,
                                      'season': season,
                                      'episode': episode,
                                      'status': i.get('status', ''),
                                      'country': i.get('country', ''),
                                      'studio': i.get('network', ''),
                                      'duration': i.get('runtime', 0),
                                      'mediatype': 'episode'}
                                      )
            li_item.setProperty('AirDay', i['weekday'])
            li_item.setProperty('AirTime', airing_time)
            li_item.setProperty('IsPlayable', 'false')

            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(dialog, 'tv', 'tmdb', i['show_id']), li_item)

        except Exception as error:
            pass

    if day == 'week':
        category = INDEX_MENU['nextaired']['menu'][0]['name']
    else:
        category = INDEX_MENU['nextaired']['days'][int(day)]

    _category(content='videos', category=category)


# discover
@plugin.route('/discover')
@plugin.route('/discover/<directory>')
@plugin.route('/discover/<directory>/<option>')
@plugin.route('/discover/<directory>/<option>/<filterby>')
@plugin.route('/discover/<directory>/<option>/<filterby>/<page>')
def discover(directory=None,option=None,filterby=None,page=1,pages=1):
    if not directory:
        for i in INDEX_MENU['discover'].get('menu'):
            li_item = ListItem(i.get('name'))
            li_item.setArt(DEFAULT_ART)
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(discover, i.get('call')),
                             li_item, True)

        _category(category=INDEX_MENU['discover']['name'])

    else:
        category = _dict_match('name', INDEX_MENU['discover']['menu'], 'call', directory)

        if _previouspage(page):
            li_item = ListItem(ADDON.getLocalizedString(32056))
            li_item.setArt(DEFAULT_ART)
            li_item.setProperty('SpecialSort', 'top')
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(discover, directory, option, filterby, int(page)-1),
                             li_item, True)

        if directory == 'person':
            result, pages = _query('person', 'popular', params={'page': page})

            if result:
                _add(result, 'person')

            _category(directory, category)

        elif not option:
            for i in DISCOVER_INDEX[directory]:
                li_item = ListItem(i.get('name'))
                li_item.setArt(DEFAULT_ART)
                xbmcplugin.addDirectoryItem(plugin.handle,
                                 plugin.url_for(discover, directory, i.get('option')),
                                 li_item, True)

            _category(category=category)

        elif option == 'all':
            result, pages = _query('discover', directory, params={'page': page})

            if result:
                _add(result, directory)

            _category(directory, category)

        elif option in ['genre', 'year'] and not filterby:
            option_results, filter_value, icon = _discover_option(directory, option)

            for i in option_results:
                li_item = ListItem(i.get('name'))
                li_item.setArt({'icon': icon})

                xbmcplugin.addDirectoryItem(plugin.handle,
                                 plugin.url_for(discover, directory, option, i.get(filter_value)),
                                 li_item, True)

            _category(directory, category)

        else:
            filter_param = _dict_match('param', DISCOVER_INDEX[directory], 'option', option)
            result, pages = _query('discover', directory, params={filter_param: filterby, 'page': page})

            if result:
                _add(result, directory)

            _category(directory, category + ' (' + filterby + ')')

        if _nextpage(page, pages):
            li_item = ListItem(xbmc.getLocalizedString(33078))
            li_item.setArt(DEFAULT_ART)
            li_item.setProperty('SpecialSort', 'bottom')
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(discover, directory, option, filterby, int(page)+1),
                             li_item, True)

    _sortmethods()
    xbmcplugin.endOfDirectory(plugin.handle)


def _discover_option(call,option):
    if option == 'genre':
        tmdb = tmdb_query(action='genre',
                          call=call,
                          get='list'
                          )

        return tmdb['genres'], 'id', 'DefaultGenre.png'

    elif option == 'year':
        cur_year = date.today().year
        index = cur_year
        years = []

        for i in range(cur_year - 1900 + 1):
            years.append({'name': str(index)})
            index -= 1

        return years, 'name', 'DefaultYear.png'

    elif option == 'keyword':
        keyboard = xbmc.Keyboard()
        keyboard.doModal()

        if keyboard.isConfirmed():
            return keyboard.getText(),


# common
@plugin.route('/movie')
@plugin.route('/movie/<call>')
@plugin.route('/movie/<call>/<page>')
def movie_listing(call=None,page=1,pages=1):
    _listing('movie', call, page, pages)

@plugin.route('/tv')
@plugin.route('/tv/<call>')
@plugin.route('/tv/<call>/<page>')
def tv_listing(call=None,page=1,pages=1):
    _listing('tv', call, page, pages)

def _listing(directory, call, page, pages):
    route = '%s_listing' % directory
    category = _dict_match('name', INDEX_MENU[directory]['menu'], 'call', call)

    if _previouspage(page):
        li_item = ListItem(ADDON.getLocalizedString(32056))
        li_item.setArt(DEFAULT_ART)
        li_item.setProperty('SpecialSort', 'top')
        xbmcplugin.addDirectoryItem(plugin.handle,
                         plugin.url_for(eval(route), call, int(page)-1),
                         li_item, True)

    if not call:
        result = None
        for i in INDEX_MENU[directory].get('menu'):
            li_item = ListItem(i.get('name'))
            li_item.setArt(DEFAULT_ART)
            xbmcplugin.addDirectoryItem(plugin.handle,
                             plugin.url_for(eval(route), i.get('call')),
                             li_item, True)

        _category(category=INDEX_MENU[directory]['name'])

    elif call == 'trending':
        result, pages = _query('trending', directory, 'week', params={'page': page})

    else:
        result, pages = _query(directory, call, params={'page': page})

    if result:
        _add(result, directory)
        _category(directory, category)

    if _nextpage(page, pages):
        li_item = ListItem(xbmc.getLocalizedString(33078))
        li_item.setArt(DEFAULT_ART)
        li_item.setProperty('SpecialSort', 'bottom')
        xbmcplugin.addDirectoryItem(plugin.handle,
                         plugin.url_for(eval(route), call, int(page)+1),
                         li_item, True)

    _sortmethods()
    xbmcplugin.endOfDirectory(plugin.handle)

#helpers
def _dict_match(get,source,key,value):
    result = [i.get(get) for i in source if i.get(key) == value]
    if result:
        return result[0]


def _add(items,call):
    local_items = get_local_media()

    if call == 'tv':
        for item in items:
            list_item, is_local = tmdb_handle_tvshow(item, local_items=local_items.get('shows', []))
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(dialog, 'tv', 'tmdb', item['id']), list_item)

    elif call == 'movie':
        for item in items:
            list_item, is_local = tmdb_handle_movie(item, local_items=local_items.get('movies', []))
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(dialog, 'movie', 'tmdb', item['id']), list_item)

    elif call == 'person':
        for item in items:
            list_item = tmdb_handle_person(item)
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(dialog, 'person', 'tmdb', item['id']), list_item)

def _category(content='',category='',call=None,info=None):
    if content == 'tv':
        plugincontent = 'tvshows'
    elif content == 'movie':
        plugincontent = 'movies'
    elif content == 'person':
        plugincontent = 'actors'
    elif content:
        plugincontent = content
    else:
        plugincontent = ''

    set_plugincontent(content=plugincontent, category=category)


def _query(content_type,call,get=None,params=None,get_details=False):
    args = {'region': COUNTRY_CODE}
    if params:
        args.update(params)

    cache_key = 'widget' + content_type + str(call) + str(get) + str(args)
    tmdb = get_cache(cache_key)

    if not tmdb:
        tmdb = tmdb_query(action=content_type,
                          call=call,
                          get=get,
                          params=args
                          )

    if tmdb:
        write_cache(cache_key,tmdb,3)

    if not get_details:
        try:
            return tmdb.get('results'), tmdb.get('total_pages')
        except Exception:
            return [], 1

    else:
        return tmdb


def _nextpage(page,pages):
    if int(page) < int(pages) and condition('Window.IsVisible(MyVideoNav.xml)'):
        return True
    return False


def _previouspage(page):
    if int(page) > 1 and condition('Window.IsVisible(MyVideoNav.xml) + !Container.HasParent'):
        return True
    return False


def _sortmethods():
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)