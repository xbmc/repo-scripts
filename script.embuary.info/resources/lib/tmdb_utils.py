#!/usr/bin/python
# coding: utf-8

########################

import json
import sys
import xbmc
import xbmcgui
import requests
import datetime

''' Python 2<->3 compatibility
'''
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from resources.lib.helper import *

########################

API_KEY = ADDON.getSettingString('tmdb_api_key')
API_URL = 'https://api.themoviedb.org/3/'
IMAGEPATH = 'https://image.tmdb.org/t/p/original'
COUNTRY_CODE = ADDON.getSettingString('country_code')
DEFAULT_LANGUAGE = ADDON.getSettingString('language_code')
FALLBACK_LANGUAGE = 'en'

OMDB_API_KEY = ADDON.getSettingString('omdb_api_key')
OMDB_URL = 'http://www.omdbapi.com/'

########################

def omdb_call(imdbnumber=None,title=None,year=None,content_type=None):
    omdb = {}

    if imdbnumber:
        url = '%s?i=%s&apikey=%s' % (OMDB_URL,imdbnumber,OMDB_API_KEY)
    elif title and year and content_type:
        url = '%s?t=%s&year=%s&type=%s&apikey=%s' % (OMDB_URL,title,year,content_type,OMDB_API_KEY)
    else:
        return omdb

    omdb_cache = get_cache(url)

    if omdb_cache:
        return omdb_cache

    else:
        try:
            request = requests.get(url)
            result = request.json()

            omdb['awards'] = result.get('Awards')
            omdb['imdbRating'] = result.get('imdbRating')
            omdb['imdbVotes'] = result.get('imdbVotes')
            omdb['DVD'] = date_format(result.get('DVD'))

            delete_keys = [key for key,value in omdb.items() if value == 'N/A' or value == 'NA']
            for key in delete_keys:
                del omdb[key]

            for rating in result['Ratings']:
                if rating['Source'] == 'Rotten Tomatoes':
                    omdb['rotten'] = rating['Value'][:-1]
                elif rating['Source'] == 'Metacritic':
                    omdb['metacritic'] = rating['Value'][:-4]

        except Exception as error:
            log('OMDB Error: %s' % error)
            pass

        else:
            write_cache(url,omdb)

        return omdb


def tmdb_call(request_url,error_check=False,error=ADDON.getLocalizedString(32019)):
    try:
        for i in range(1,10):
            request = requests.get(request_url)
            if not str(request.status_code).startswith('5'):
                break
            log('TMDb server error: Code ' + str(request.status_code))
            xbmc.sleep(500)

        if request.status_code == 401:
            error = ADDON.getLocalizedString(32022)
            raise Exception

        elif request.status_code == 404:
            raise Exception

        elif request.status_code != requests.codes.ok:
            error = 'Code ' + str(request.status_code)
            raise Exception

        result = request.json()

        if error_check:
            if len(result) == 0: raise Exception
            if 'results' in result and len(result['results']) == 0: raise Exception

        return result

    except Exception:
        tmdb_error(error)


def tmdb_query(action=None,call=None,get=None,use_language=True,language=DEFAULT_LANGUAGE,error_check=False,**kwargs):
    kwargs['api_key'] = API_KEY

    if use_language:
        kwargs['language'] = language

    if get is not None:
        call = call + '/' + get

    if call is not None:
        action = action + '/' + call

    url = API_URL + action
    url = '{0}?{1}'.format(url, urlencode(kwargs))

    return tmdb_call(url,error_check)


def tmdb_search(call,query,year=None,include_adult='false'):
    #/search/{call}?api_key=&language=&query={query}&page=1&include_adult=false
    if call == 'person':
        result = tmdb_query(action='search',
                            call=call,
                            query=query,
                            include_adult=include_adult,
                            error_check=True
                            )

    elif call == 'movie':
        result = tmdb_query(action='search',
                            call=call,
                            query=query,
                            year=year,
                            include_adult=include_adult,
                            error_check=True
                            )

    elif call == 'tv':
        result = tmdb_query(action='search',
                            call=call,
                            query=query,
                            first_air_date_year=year,
                            error_check=True
                            )

    try:
        return result['results']
    except TypeError:
        return ''


def tmdb_find(call,external_id):
    #/find/{id}?api_key=&language=en-US&external_source=tvdb_id
    if external_id.startswith('tt'):
        external_source = 'imdb_id'
    else:
        external_source = 'tvdb_id'

    result = tmdb_query(action='find',
                        call=str(external_id),
                        external_source=external_source,
                        use_language=False
                        )

    if call == 'movie':
        result = result['movie_results']
    else:
        result = result['tv_results']

    if not result:
        tmdb_error(ADDON.getLocalizedString(32019))

    return result


def tmdb_item_details(action,tmdb_id,get=None,append_to_response=None,use_language=True,include_image_language=None):
    #{action}/{id}?api_key=&language=
    #{action}/{id}/{get}?api_key=&language=
    result = tmdb_query(action=action,
                        call=str(tmdb_id),
                        get=get,
                        append_to_response=append_to_response,
                        use_language=use_language,
                        include_image_language=include_image_language
                        )

    return result


def tmdb_select_dialog(list,call):
    indexlist = []
    selectionlist = []

    if call == 'person':
        default_img = 'DefaultActor.png'
        img = 'profile_path'
        label = 'name'
        label2 = ''

    elif call == 'movie':
        default_img = 'DefaultVideo.png'
        img = 'poster_path'
        label = 'title'
        label2 = 'tmdb_get_year(item.get("release_date",""))'

    elif call == 'tv':
        default_img = 'DefaultVideo.png'
        img = 'poster_path'
        label = 'name'
        label2 = 'first_air_date'
        label2 = 'tmdb_get_year(item.get("first_air_date",""))'

    else:
        return

    index = 0
    for item in list:
        icon = IMAGEPATH + item[img] if item[img] is not None else ''
        list_item = xbmcgui.ListItem(item[label])
        list_item.setArt({'icon': default_img,'thumb': icon})

        try:
            list_item.setLabel2(str(eval(label2)))
        except Exception:
            pass

        selectionlist.append(list_item)
        indexlist.append(index)
        index += 1

    busydialog(close=True)

    selected = DIALOG.select(xbmc.getLocalizedString(424), selectionlist, useDetails=True)

    if selected == -1:
        return -1

    busydialog()

    return indexlist[selected]


def tmdb_select_dialog_small(list):
    indexlist = []
    selectionlist = []

    index = 0
    for item in list:
        list_item = xbmcgui.ListItem(item)
        selectionlist.append(list_item)
        indexlist.append(index)
        index += 1

    busydialog(close=True)

    selected = DIALOG.select(xbmc.getLocalizedString(424), selectionlist, useDetails=False)

    if selected == -1:
        return -1

    busydialog()

    return indexlist[selected]


def tmdb_calc_age(birthday,deathday=None):
    if deathday is not None:
        ref_day = deathday.split("-")
    elif birthday:
        date = datetime.date.today()
        ref_day = [date.year, date.month, date.day]
    else:
        return ''

    born = birthday.split('-')
    age = int(ref_day[0]) - int(born[0])

    if len(born) > 1:
        diff_months = int(ref_day[1]) - int(born[1])
        diff_days = int(ref_day[2]) - int(born[2])

        if diff_months < 0 or (diff_months == 0 and diff_days < 0):
            age -= 1

    return age


def tmdb_error(message=ADDON.getLocalizedString(32019)):
    busydialog(close=True)
    DIALOG.ok(ADDON.getLocalizedString(32000),message)


def tmdb_check_localdb(local_items,title,originaltitle,year,imdbnumber=False):
    found_local = False
    local = {'dbid': -1, 'playcount': 0, 'watchedepisodes': '', 'episodes': '', 'unwatchedepisodes': '', 'file': ''}

    if local_items:
        for item in local_items:
            dbid = item['dbid']
            playcount = item['playcount']
            episodes = item.get('episodes','')
            watchedepisodes = item.get('watchedepisodes','')
            file = item.get('file','')

            if imdbnumber and item['imdbnumber'] == imdbnumber:
                found_local = True
                break

            try:
                if int(item['year']) == int(tmdb_get_year(year)):
                    if item['originaltitle'] == originaltitle or item['title'] == originaltitle or item['title'] == title:
                        found_local = True
                        break

            except ValueError:
                pass

    if found_local:
        local['dbid'] = dbid
        local['file'] = file
        local['playcount'] = playcount
        local['episodes'] = episodes
        local['watchedepisodes'] = watchedepisodes
        local['unwatchedepisodes'] = episodes - watchedepisodes if episodes else ''

    return local


def tmdb_handle_person(item):
    if item.get('gender') == 2:
        gender = 'male'
    elif item.get('gender') == 1:
        gender = 'female'
    else:
        gender = ''

    icon = IMAGEPATH + item['profile_path'] if item['profile_path'] is not None else ''
    list_item = xbmcgui.ListItem(label=item['name'])
    list_item.setProperty('birthday', date_format(item.get('birthday')))
    list_item.setProperty('deathday', date_format(item.get('deathday')))
    list_item.setProperty('age', str(tmdb_calc_age(item.get('birthday',''),item.get('deathday',None))))
    list_item.setProperty('biography', tmdb_fallback_info(item,'biography'))
    list_item.setProperty('place_of_birth', item.get('place_of_birth',''))
    list_item.setProperty('known_for_department', item.get('known_for_department',''))
    list_item.setProperty('gender', gender)
    list_item.setProperty('id', str(item.get('id','')))
    list_item.setProperty('call', 'person')
    list_item.setArt({'icon': 'DefaultActor.png','thumb': icon})

    return list_item


def tmdb_handle_movie(item,local_items,full_info=False):
    icon = IMAGEPATH + item['poster_path'] if item['poster_path'] is not None else ''
    backdrop = IMAGEPATH + item['backdrop_path'] if item['backdrop_path'] is not None else ''

    label = item['title'] or item['original_title']
    originaltitle = item.get('original_title','')
    imdbnumber = item.get('imdb_id','')
    premiered = item.get('release_date') if item.get('release_date',0) != '0' else ''
    duration = item.get('runtime') * 60 if item.get('runtime',0) > 0 else ''
    local_info = tmdb_check_localdb(local_items,label,originaltitle,premiered,imdbnumber)
    dbid = local_info['dbid']
    is_local = True if dbid > 0 else False

    list_item = xbmcgui.ListItem(label=label)
    list_item.setInfo('video', {'title': label,
                                'originaltitle': originaltitle,
                                'dbid': dbid,
                                'playcount': local_info['playcount'],
                                'imdbnumber': imdbnumber,
                                'rating': item.get('vote_average',''),
                                'votes': item.get('vote_count',''),
                                'premiered': premiered,
                                'mpaa': tmdb_get_cert(item),
                                'tagline': item.get('tagline',''),
                                'duration': duration,
                                'plot': tmdb_fallback_info(item,'overview'),
                                'director': tmdb_join_items_by(item.get('crew',''),key_is='job',value_is='Director'),
                                'writer': tmdb_join_items_by(item.get('crew',''),key_is='department',value_is='Writing'),
                                'country': tmdb_join_items(item.get('production_countries','')),
                                'genre': tmdb_join_items(item.get('genres','')),
                                'studio': tmdb_join_items(item.get('production_companies','')),
                                'mediatype': 'movie'}
                                 )
    list_item.setArt({'icon': 'DefaultVideo.png','thumb': icon,'fanart': backdrop})
    list_item.setProperty('role', item.get('character',''))
    list_item.setProperty('budget', format_currency(item.get('budget')))
    list_item.setProperty('revenue', format_currency(item.get('revenue')))
    list_item.setProperty('file', local_info.get('file',''))
    list_item.setProperty('id', str(item.get('id','')))
    list_item.setProperty('call', 'movie')

    if full_info and OMDB_API_KEY and imdbnumber:
        omdb = omdb_call(imdbnumber)
        if omdb:
            list_item.setProperty('rating.metacritic', omdb.get('metacritic'))
            list_item.setProperty('rating.rotten', omdb.get('rotten'))
            list_item.setProperty('rating.imdb', omdb.get('imdbRating'))
            list_item.setProperty('votes.imdb', omdb.get('imdbVotes'))
            list_item.setProperty('awards', omdb.get('awards'))
            list_item.setProperty('release', omdb.get('DVD'))

    return list_item, is_local


def tmdb_handle_tvshow(item,local_items,full_info=False):
    icon = IMAGEPATH + item['poster_path'] if item['poster_path'] is not None else ''
    backdrop = IMAGEPATH + item['backdrop_path'] if item['backdrop_path'] is not None else ''

    label = item['name'] or item['original_name']
    originaltitle = item.get('original_name','')
    premiered = item.get('first_air_date') if item.get('first_air_date',0) != '0' else ''
    imdbnumber = item['external_ids']['imdb_id'] if item.get('external_ids') else ''
    tvdb_id = item['external_ids']['tvdb_id'] if item.get('external_ids') else ''
    local_info = tmdb_check_localdb(local_items,label,originaltitle,premiered,tvdb_id)
    dbid = local_info['dbid']
    is_local = True if dbid > 0 else False

    list_item = xbmcgui.ListItem(label=label)
    list_item.setInfo('video', {'title': label,
                                'originaltitle': originaltitle,
                                'dbid': dbid,
                                'playcount': local_info['playcount'],
                                'status': item.get('status',''),
                                'rating': item.get('vote_average',''),
                                'votes': item.get('vote_count',''),
                                'imdbnumber': imdbnumber,
                                'premiered': premiered,
                                'mpaa': tmdb_get_cert(item),
                                'season': str(item.get('number_of_seasons','')),
                                'episode': str(item.get('number_of_episodes','')),
                                'plot': tmdb_fallback_info(item,'overview'),
                                'director': tmdb_join_items(item.get('created_by','')),
                                'genre': tmdb_join_items(item.get('genres','')),
                                'studio': tmdb_join_items(item.get('networks','')),
                                'mediatype': 'tvshow'}
                                )
    list_item.setArt({'icon': 'DefaultVideo.png','thumb': icon,'fanart': backdrop})
    list_item.setProperty('TotalEpisodes', str(local_info['episodes']))
    list_item.setProperty('WatchedEpisodes', str(local_info['watchedepisodes']))
    list_item.setProperty('UnWatchedEpisodes', str(local_info['unwatchedepisodes']))
    list_item.setProperty('role', item.get('character',''))
    list_item.setProperty('tvdb_id', str(tvdb_id))
    list_item.setProperty('id', str(item.get('id','')))
    list_item.setProperty('call', 'tv')

    if full_info and OMDB_API_KEY and imdbnumber:
        omdb = omdb_call(imdbnumber)
        if omdb:
            list_item.setProperty('rating.metacritic', omdb.get('metacritic'))
            list_item.setProperty('rating.rotten', omdb.get('rotten'))
            list_item.setProperty('rating.imdb', omdb.get('imdbRating'))
            list_item.setProperty('votes.imdb', omdb.get('imdbVotes'))

    return list_item, is_local


def tmdb_fallback_info(item,key):
    key_value = item.get(key)

    if key_value:
        return key_value.replace('&amp;', '&')

    try:
        for translation in item['translations']['translations']:
            if translation.get('iso_639_1') == FALLBACK_LANGUAGE:
                if translation['data'][key]:
                    key_value = translation['data'][key]
                    return key_value.replace('&amp;', '&')

    except Exception:
        pass

    return ''


def tmdb_handle_images(item):
    icon = IMAGEPATH + item['file_path'] if item['file_path'] is not None else ''
    list_item = xbmcgui.ListItem(label=str(item['width']) + 'x' + str(item['height']) + 'px')
    list_item.setArt({'icon': 'DefaultPicture.png','thumb': icon})
    list_item.setProperty('call', 'image')

    return list_item


def tmdb_handle_credits(item):
    icon = IMAGEPATH + item['profile_path'] if item['profile_path'] is not None else ''
    list_item = xbmcgui.ListItem(label=item['name'])
    list_item.setLabel2(item['label2'])
    list_item.setArt({'icon': 'DefaultActor.png','thumb': icon})
    list_item.setProperty('id', str(item.get('id','')))
    list_item.setProperty('call', 'person')

    return list_item


def tmdb_handle_yt_videos(item):
    icon = 'https://img.youtube.com/vi/%s/0.jpg' % str(item['key'])
    list_item = xbmcgui.ListItem(label=item['name'])
    list_item.setLabel2(item.get('type',''))
    list_item.setArt({'icon': 'DefaultVideo.png','thumb': icon})
    list_item.setProperty('ytid', str(item['key']))
    list_item.setProperty('call', 'youtube')

    return list_item


def tmdb_join_items_by(item,key_is,value_is,key='name'):
    values = []
    for value in item:
        if value[key_is] == value_is:
            values.append(value[key])

    return get_joined_items(values)


def tmdb_join_items(item,key='name'):
    values = []
    for value in item:
        values.append(value[key])

    return get_joined_items(values)


def tmdb_get_year(item):
    try:
        year = str(item)[:-6]
        return year
    except Exception:
        return ''


def tmdb_get_cert(item):
    try:
        if COUNTRY_CODE == 'DE':
            prefix = 'FSK '
        else:
            prefix = ''

        if item.get('content_ratings'):
            for cert in item['content_ratings']['results']:
                if cert['iso_3166_1'] == COUNTRY_CODE:
                    mpaa = prefix + cert['rating']
                    return mpaa

        elif item.get('release_dates'):
            for cert in item['release_dates']['results']:
                if cert['iso_3166_1'] == COUNTRY_CODE:
                    mpaa = cert['release_dates'][0]['certification']
                    return mpaa

        else:
            return ''

    except Exception:
        return ''