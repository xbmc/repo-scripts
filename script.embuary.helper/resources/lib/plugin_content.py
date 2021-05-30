#!/usr/bin/python
# coding: utf-8

########################

import random
import xbmcvfs

from resources.lib.helper import *
from resources.lib.library import *
from resources.lib.image import *

########################

class PluginContent(object):
    def __init__(self,params,li):
        self.params = params
        self.dbtitle = remove_quotes(params.get('title'))
        self.dblabel = remove_quotes(params.get('label'))
        self.dbtype = remove_quotes(params.get('type'))
        self.exclude = remove_quotes(params.get('exclude'))
        self.dbcontent = remove_quotes(params.get('content'))
        self.dbid = remove_quotes(params.get('dbid'))
        self.idtype = remove_quotes(params.get('idtype'))
        self.season = remove_quotes(params.get('season'))
        self.tag = remove_quotes(params.get('tag'))
        self.playlist = remove_quotes(params.get('playlist'))
        self.unwatched = remove_quotes(params.get('unwatched'))
        self.limit = remove_quotes(params.get('limit'))
        self.retry_count = 1
        self.li = li

        if self.limit:
            self.limit = int(self.limit)

        if self.dbtype:
            if self.dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
                library = 'Video'
            else:
                library = 'Audio'

            self.method_details = '%sLibrary.Get%sDetails' % (library, self.dbtype)
            self.method_item = '%sLibrary.Get%ss' % (library, self.dbtype)
            self.param = '%sid' % self.dbtype
            self.key_details = '%sdetails' % self.dbtype
            self.key_items = '%ss' % self.dbtype
            self.properties = JSON_MAP.get('%s_properties' % self.dbtype)

        self.sort_lastplayed = {'order': 'descending', 'method': 'lastplayed'}
        self.sort_recent = {'order': 'descending', 'method': 'dateadded'}
        self.sort_random = {'method': 'random'}

        self.filter_unwatched = {'field': 'playcount', 'operator': 'lessthan', 'value': '1'}
        self.filter_watched = {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}
        self.filter_unwatched_episodes = {'field': 'numwatched', 'operator': 'lessthan', 'value': ['1']}
        self.filter_watched_episodes = {'field': 'numwatched', 'operator': 'greaterthan','value': ['0']}
        self.filter_no_specials = {'field': 'season', 'operator': 'greaterthan', 'value': '0'}
        self.filter_inprogress = {'field': 'inprogress', 'operator': 'true', 'value': ''}
        self.filter_not_inprogress = {'field': 'inprogress', 'operator': 'false', 'value': ''}
        self.filter_tag = {'operator': 'is', 'field': 'tag', 'value': self.tag}
        self.filter_title = {'operator': 'is', 'field': 'title', 'value': self.dbtitle}

        if self.playlist:
            playlist_li = []
            for item in self.playlist.split('  '): # params parsing replaces ++ with a double whitespace
                playlist_li.append({'operator': 'is', 'field': 'playlist', 'value': item})

            self.filter_playlist  = {'or': playlist_li}

        else:
            self.filter_playlist = None

    ''' by dbid to get all available listitems
    '''
    def getbydbid(self):
        try:
            if self.dbtype == 'tvshow' and self.idtype in ['season', 'episode']:
                self.dbid = self._gettvshowid()

            json_query = json_call(self.method_details,
                                properties=self.properties,
                                params={self.param: int(self.dbid)}
                                )

            result = json_query['result'][self.key_details]

            if self.dbtype == 'episode':
                try:
                    season_query = json_call('VideoLibrary.GetSeasons',
                                             properties=JSON_MAP['season_properties'],
                                             sort={'order': 'ascending', 'method': 'season'},
                                             params={'tvshowid': int(result.get('tvshowid'))}
                                             )

                    season_query = season_query['result']['seasons']

                    for season in season_query:
                        if season.get('season') == result.get('season'):
                            result['season_label'] = season.get('label')
                            break

                except Exception:
                    pass

        except Exception as error:
            log('Get by DBID: No result found: %s' % error)
            return

        add_items(self.li,[result],type=self.dbtype)
        plugin_category = 'DBID #' + str(self.dbid) + ' (' + self.dbtype + ')'
        set_plugincontent(content=self.key_items, category=plugin_category)


    ''' by custom args to parse own json
    '''
    def getbyargs(self):
        limit = self.limit or None
        filter_args = remove_quotes(self.params.get('filter_args')) or None
        sort_args = remove_quotes(self.params.get('sort_args')) or None
        plugin_category = self.params.get('category_label')

        filters = []
        if filter_args is not None:
            filters.append(eval(filter_args))
        if self.tag:
            filters.append(self.filter_tag)

        if sort_args is not None:
            sort_args = eval(sort_args)

        try:
            json_query = json_call(self.method_item,
                                   properties=self.properties,
                                   sort=sort_args, limit=limit,
                                   query_filter={'and': filters} if filters else None
                                   )

            result = json_query['result'][self.key_items]

        except Exception as error:
            log('Get by args: No result found: %s' % error)
            return

        add_items(self.li, result, type=self.dbtype)
        set_plugincontent(content=self.key_items, category=plugin_category)


    ''' resource helper to create a list will all existing and matching resource images
    '''
    def getresourceimages(self):
        resource_addon = self.params.get('addon')
        resource_dir = xbmcvfs.translatePath('resource://%s/' % resource_addon)

        string = remove_quotes(self.params.get('string'))
        separator = remove_quotes(self.params.get('separator'))

        if separator:
            values = string.split(separator)
        else:
            values = string.splitlines()

        for item in values:
            for filename in ['%s.jpg' % item, '%s.png' % item]:
                filepath = resource_dir + filename
                if xbmcvfs.exists(filepath):
                    list_item = xbmcgui.ListItem(label=item, offscreen=True)
                    list_item.setArt({'icon': filepath})
                    self.li.append(('', list_item, False))
                    break

            set_plugincontent(content='files', category=resource_addon)


    ''' season widgets to display library content that fit a special seasson or date
    '''
    def getseasonal(self):
        xmas = ['xmas', 'christmas', 'x-mas', 'santa claus', 'st. claus', 'happy holidays', 'st. nick', 'Weihnacht',
                'fest der liebe', 'heilige nacht', 'heiliger abend', 'heiligabend', 'nikolaus', 'christkind', 'Noël',
                'Meilleurs vœux', 'feliz navidad', 'joyeux noel', 'Natale', 'szczęśliwe święta', 'Veselé Vánoce',
                'Vrolijk kerstfeest', 'Kerstmis', 'Boże Narodzenie', 'Kalėdos', 'Crăciun'
                ]

        horror = ['ужас', 'užas', 'rædsel', 'horror', 'φρίκη', 'õudus', 'kauhu', 'horreur', 'užas',
                  'borzalom', 'hryllingi', 'ホラー', 'siaubas', 'verschrikking', 'skrekk', 'przerażenie',
                  'groază', 'фильм ужасов', 'hrôza', 'grozo', 'Skräck', 'korku', 'жах', 'halloween'
                  ]

        starwars = ['Star Wars', 'Krieg der Sterne', 'Luke Skywalker', 'Darth Vader', 'Jedi ', 'Ewoks',
                    'Starwars', 'Kylo Ren', 'Yoda ', 'Chewbacca', 'Anakin Skywalker', 'Han Solo', 'r2-d2',
                    'bb-8', 'Millennium Falcon', 'Millenium Falke', 'Stormtrooper', 'Sturmtruppler'
                    ]

        startrek = ['Star Trek', 'Captain Kirk', 'Cpt. Kirk', 'James Kirk', 'James T. Kirk', 'James Tiberius Kirk',
                    'Jean-Luc Picard', 'Commander Spock', 'Deep Space Nine', 'Deep Space 9', 'Raumschiff Enterprise',
                    'Raumschiff Voyager', 'Klingonen', 'Klingons', 'Commander Data', 'Commander Geordi La Forge',
                    'Counselor Deanna Troi', 'William Thomas Riker', 'Captain Benjamin Sisko', 'Cpt. Benjamin Sisko',
                    'Captain Kathryn Janeway', 'Cpt. Kathryn Janeway'
                    ]

        use_episodes = False
        add_episodes = False

        filters = []
        filters_episode = []
        list_type = self.params.get('list')

        if list_type == 'xmas':
            use_episodes = True
            plugin_category = ADDON.getLocalizedString(32032)
            for keyword in xmas:
                filters.append({'operator': 'contains', 'field': 'title', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'originaltitle', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'plot', 'value': keyword})
                filters_episode.append({'operator': 'contains', 'field': 'title', 'value': keyword})
                filters_episode.append({'operator': 'contains', 'field': 'plot', 'value': keyword})

        elif list_type == 'horror':
            add_episodes = True
            plugin_category = ADDON.getLocalizedString(32033)
            filters_episode.append({'operator': 'contains', 'field': 'plot', 'value': 'Halloween'})
            filters_episode.append({'operator': 'contains', 'field': 'title', 'value': 'Halloween'})
            filters.append({'operator': 'contains', 'field': 'title', 'value': 'Halloween'})
            filters.append({'operator': 'contains', 'field': 'originaltitle', 'value': 'Halloween'})
            for keyword in horror:
                filters.append({'operator': 'contains', 'field': 'genre', 'value': keyword})

        elif list_type == 'starwars':
            plugin_category = ADDON.getLocalizedString(32034)
            for keyword in starwars:
                filters.append({'operator': 'contains', 'field': 'title', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'originaltitle', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'plot', 'value': keyword})

        elif list_type == 'startrek':
            plugin_category = ADDON.getLocalizedString(32035)
            for keyword in startrek:
                filters.append({'operator': 'contains', 'field': 'title', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'originaltitle', 'value': keyword})
                filters.append({'operator': 'contains', 'field': 'plot', 'value': keyword})

        else:
            return

        limit = self.limit or 26

        if self.dbtype != 'tvshow':
            json_query = json_call('VideoLibrary.GetMovies',
                                   properties=JSON_MAP['movie_properties'],
                                   sort=self.sort_random, limit=limit,
                                   query_filter={'or': filters}
                                   )
            try:
                json_query = json_query['result']['movies']
            except Exception:
                log('Movies by seasonal keyword: No movies found.')
            else:
                add_items(self.li, json_query, type='movie')

        if self.dbtype != 'movie':
            if add_episodes:
                limit = int(limit/2)

            if not use_episodes:
                json_query = json_call('VideoLibrary.GetTVShows',
                                       properties=JSON_MAP['tvshow_properties'],
                                       sort=self.sort_random, limit=limit,
                                       query_filter={'or': filters}
                                       )
                try:
                    json_query = json_query['result']['tvshows']
                except Exception:
                    log('TV shows by seasonal keyword: No shows found.')
                else:
                    add_items(self.li, json_query, type='tvshow')

            if use_episodes or add_episodes:
                json_query = json_call('VideoLibrary.GetEpisodes',
                                       properties=JSON_MAP['episode_properties'],
                                       sort=self.sort_random, limit=limit,
                                       query_filter={'or': filters_episode}
                                       )
                try:
                    json_query = json_query['result']['episodes']
                except Exception:
                    log('Episodes by seasonal keyword: No episodes found.')
                else:
                    add_items(self.li, json_query, type='episode')

        random.shuffle(self.li)
        set_plugincontent(content='videos', category=plugin_category)


    ''' get seasons of a show
    '''
    def getseasons(self):
        if not self.dbid:
            get_dbid = json_call('VideoLibrary.GetTVShows',
                                 properties=['title'], limit=1,
                                 query_filter=self.filter_title
                                 )

            try:
                tvshow_dbid = get_dbid['result']['tvshows'][0]['tvshowid']
            except Exception:
                log('Get seasons by TV show: Show not found')
                return

        else:
            if self.idtype in ['season', 'episode']:
                tvshow_dbid = self._gettvshowid()
            else:
                tvshow_dbid = self.dbid

        season_query = json_call('VideoLibrary.GetSeasons',
                                 properties=JSON_MAP['season_properties'],
                                 sort={'order': 'ascending', 'method': 'season'},
                                 params={'tvshowid': int(tvshow_dbid)}
                                 )

        try:
            season_query = season_query['result']['seasons']
            if not len(season_query) > 1 and self.params.get('allseasons') == 'false':
                return

        except Exception:
            log('Get seasons by TV show: No seasons found')
        else:
            add_items(self.li, season_query, type='season')
            set_plugincontent(content='seasons', category=season_query[0].get('showtitle'))


    ''' get more episodes from the same season
    '''
    def getseasonepisodes(self):
        if not self.dbid:
            get_dbid = json_call('VideoLibrary.GetTVShows',
                                 properties=['title'], limit=1,
                                 query_filter=self.filter_title
                                 )

            try:
                tvshow_dbid = get_dbid['result']['tvshows'][0]['tvshowid']
            except Exception:
                log('Get more episodes by season: Show not found')
                return

        else:
            if self.idtype == 'episode':
                tvshow_dbid = self._gettvshowid()
            else:
                tvshow_dbid = self.dbid

        episode_query = json_call('VideoLibrary.GetEpisodes',
                                  properties=JSON_MAP['episode_properties'],
                                  sort={'order': 'ascending', 'method': 'episode'},
                                  query_filter={'operator': 'is', 'field': 'season', 'value': self.season},
                                  params={'tvshowid': int(tvshow_dbid)}
                                  )

        try:
            episode_query = episode_query['result']['episodes']
        except Exception:
            log('Get more episodes by season: No episodes found')
        else:
            add_items(self.li, episode_query, type='episode')
            plugin_category = episode_query[0].get('showtitle') + ' - ' + xbmc.getLocalizedString(20373) + ' ' + str(episode_query[0].get('season'))
            set_plugincontent(content='episodes', category=plugin_category)


    ''' get nextup of inprogress TV shows
    '''
    def getnextup(self):
        filters = [self.filter_inprogress]
        if self.tag:
            filters.append(self.filter_tag)
        if self.playlist:
            filters.append(self.filter_playlist)

        json_query = json_call('VideoLibrary.GetTVShows',
                               properties=['title', 'lastplayed'],
                               sort=self.sort_lastplayed, limit=25,
                               query_filter={'and': filters}
                               )

        try:
            json_query = json_query['result']['tvshows']
        except Exception:
            log('Get next up episodes: No TV shows found')
            return

        for episode in json_query:
                use_last_played_season = True
                last_played_query = json_call('VideoLibrary.GetEpisodes',
                                              properties=['seasonid', 'season'],
                                              sort={'order': 'descending', 'method': 'lastplayed'}, limit=1,
                                              query_filter={'and': [{'or': [self.filter_inprogress, self.filter_watched]}, self.filter_no_specials]},
                                              params={'tvshowid': int(episode['tvshowid'])}
                                              )

                if last_played_query['result']['limits']['total'] < 1:
                     use_last_played_season = False

                ''' Return the next episode of last played season
                '''
                if use_last_played_season:
                    episode_query = json_call('VideoLibrary.GetEpisodes',
                                              properties=JSON_MAP['episode_properties'],
                                              sort={'order': 'ascending', 'method': 'episode'}, limit=1,
                                              query_filter={'and': [self.filter_unwatched, {'field': 'season', 'operator': 'is', 'value': str(last_played_query['result']['episodes'][0].get('season'))}]},
                                              params={'tvshowid': int(episode['tvshowid'])}
                                              )

                    if episode_query['result']['limits']['total'] < 1:
                        use_last_played_season = False

                ''' If no episode is left of the last played season, fall back to the very first unwatched episode
                '''
                if not use_last_played_season:
                    episode_query = json_call('VideoLibrary.GetEpisodes',
                                              properties=JSON_MAP['episode_properties'],
                                              sort={'order': 'ascending', 'method': 'episode'}, limit=1,
                                              query_filter={'and': [self.filter_unwatched, self.filter_no_specials]},
                                              params={'tvshowid': int(episode['tvshowid'])}
                                              )

                try:
                    episode_details = episode_query['result']['episodes']
                except Exception:
                    log('Get next up episodes: No next episodes found for %s' % episode['title'])
                else:
                    add_items(self.li, episode_details, type='episode')
                    set_plugincontent(content='episodes', category=ADDON.getLocalizedString(32008))


    ''' get recently added episodes of unwatched shows
    '''
    def getnewshows(self):
        show_all = get_bool(self.params.get('showall'))

        if show_all:
            filter = self.filter_tag if self.tag else None
            plugin_category = ADDON.getLocalizedString(32010)

        else:
            filters = [self.filter_unwatched]
            if self.tag:
                filters.append(self.filter_tag)
            filter = {'and': filters}
            plugin_category = ADDON.getLocalizedString(32015)


        json_query = json_call('VideoLibrary.GetTVShows',
                               properties=['episode', 'watchedepisodes'],
                               sort=self.sort_recent, limit=25,
                               query_filter=filter
                               )

        try:
            json_query = json_query['result']['tvshows']
        except Exception:
            log('Get new media: No TV shows found')
            return

        for tvshow in json_query:
            try:
                unwatchedepisodes = get_unwatched(tvshow['episode'], tvshow['watchedepisodes'])
                append_tvshow = False

                if show_all:
                    ''' All recently added episodes. Watched state is ignored and only items added of the same date
                        will be grouped.
                    '''
                    episode_query = json_call('VideoLibrary.GetEpisodes',
                                              properties=JSON_MAP['episode_properties'],
                                              sort=self.sort_recent, limit=2,
                                              params={'tvshowid': int(tvshow['tvshowid'])}
                                              )

                    episode_query = episode_query['result']['episodes']

                    try:
                        if not get_date(episode_query[0]['dateadded']) == get_date(episode_query[1]['dateadded']):
                            raise Exception
                        append_tvshow = True

                    except Exception:
                        add_items(self.li, [episode_query[0]], type='episode')

                elif unwatchedepisodes == 1:
                    ''' Recently added episodes based on unwatched or in progress TV shows. Episodes will be grouped
                        if more than one unwatched episode is available.
                    '''
                    episode_query = json_call('VideoLibrary.GetEpisodes',
                                              properties=JSON_MAP['episode_properties'],
                                              sort=self.sort_recent,limit=1,
                                              query_filter=self.filter_unwatched,
                                              params={'tvshowid': int(tvshow['tvshowid'])}
                                              )

                    episode_query = episode_query['result']['episodes']
                    add_items(self.li,episode_query, type='episode')

                else:
                    append_tvshow = True

                ''' Group episodes to show if more than one valid episode is available
                '''
                if append_tvshow:
                    tvshow_query = json_call('VideoLibrary.GetTVShowDetails',
                                             properties=JSON_MAP['tvshow_properties'],
                                             params={'tvshowid': int(tvshow['tvshowid'])}
                                             )

                    tvshow_query = tvshow_query['result']['tvshowdetails']
                    add_items(self.li, [tvshow_query], type='tvshow')

                set_plugincontent(content='tvshows', category=plugin_category)

            except Exception as error:
                log('Get new media: Not able to parse data for show %s - %s' % (tvshow, error))
                pass


    ''' get custom media by genre
    '''
    def getbygenre(self):
        genre = remove_quotes(self.params.get('genre'))

        if not genre:
            genres = []

            if self.dbtype != 'tvshow':
                movies_genres_query = json_call('VideoLibrary.GetGenres',
                                                sort={'method': 'label'},
                                                params={'type': 'movie'}
                                                )
                try:
                    for item in movies_genres_query['result']['genres']:
                        genres.append(item.get('label'))
                except Exception:
                    log('Get movies by genre: no genres found')

            if self.dbtype != 'movie':
                tvshow_genres_query = json_call('VideoLibrary.GetGenres',
                                                sort={'method': 'label'},
                                                params={'type': 'tvshow'}
                                                )
                try:
                    for item in tvshow_genres_query['result']['genres']:
                        genres.append(item.get('label'))
                except Exception:
                    log('Get TV shows by genre: no genres found')

            if genres:
                genre = random.choice(genres)

        if genre:
            filters = [{'operator': 'contains', 'field': 'genre', 'value': genre}]
            if self.unwatched == 'True':
                filters.append(self.filter_unwatched)
            if self.tag:
                filters.append(self.filter_tag)

            if self.dbtype != 'tvshow':
                json_query = json_call('VideoLibrary.GetMovies',
                                       properties=JSON_MAP['movie_properties'],
                                       sort=self.sort_random, limit=10,
                                       query_filter={'and': filters}
                                       )
                try:
                    json_query = json_query['result']['movies']
                except Exception:
                    log('Movies by genre %s: No movies found.' % genre)
                else:
                    add_items(self.li, json_query, type='movie', searchstring=genre)

            if self.dbtype != 'movie':
                json_query = json_call('VideoLibrary.GetTVShows',
                                       properties=JSON_MAP['tvshow_properties'],
                                       sort=self.sort_random, limit=10,
                                       query_filter={'and': filters}
                                       )
                try:
                    json_query = json_query['result']['tvshows']
                except Exception:
                    log('TV shows by genre %s: No shows found.' % genre)
                else:
                    add_items(self.li, json_query, type='tvshow', searchstring=genre)

            if not self.li:
                self._retry('getbygenre')

            random.shuffle(self.li)

            set_plugincontent(content='videos', category=ADDON.getLocalizedString(32009))


    ''' get inprogress media
    '''
    def getinprogress(self):
        filters = [self.filter_inprogress]
        if self.tag:
            filters.append(self.filter_tag)
        if self.playlist:
            filters.append(self.filter_playlist)

        if self.dbtype != 'tvshow':
            json_query = json_call('VideoLibrary.GetMovies',
                                   properties=JSON_MAP['movie_properties'],
                                   sort=self.sort_lastplayed,
                                   query_filter={'and': filters}
                                   )
            try:
                json_query = json_query['result']['movies']
            except Exception:
                log('In progress media: No movies found.')
            else:
                add_items(self.li, json_query, type='movie')

        if self.dbtype != 'movie':
            json_query = json_call('VideoLibrary.GetEpisodes',
                                   properties=JSON_MAP['episode_properties'],
                                   sort=self.sort_lastplayed,
                                   query_filter={'and': filters}
                                   )
            try:
                json_query = json_query['result']['episodes']
            except Exception:
                log('In progress media: No episodes found.')
            else:
                add_items(self.li, json_query, type='episode')

        set_plugincontent(content='videos', category=ADDON.getLocalizedString(32013))


    ''' genres listing with 4 posters of each available genre content
    '''
    def getgenre(self):
        json_query = json_call('VideoLibrary.GetGenres',
                               sort={'method': 'label'},
                               params={'type': self.dbtype}
                               )
        try:
            json_query = json_query['result']['genres']
        except KeyError:
            log('Get genres: No genres found')
            return

        genres = []
        for genre in json_query:
            filters = [{'operator': 'is', 'field': 'genre', 'value': genre['label']}]
            if self.tag:
                filters.append(self.filter_tag)

            genre_items = json_call(self.method_item,
                                    properties=['art'],
                                    sort=self.sort_recent, limit=4,
                                    query_filter={'and': filters}
                                    )

            try:
                genre_items = genre_items['result'][self.key_items]
                if not genre_items:
                    raise Exception

            except Exception:
                continue

            posters = {}
            index = 0
            try:
                for art in genre_items:
                    poster = 'poster.%s' % index
                    posters[poster] = art['art'].get('poster', '')
                    index += 1
            except Exception:
                pass

            genre['art'] = posters

            generated_thumb = CreateGenreThumb(genre['label'], posters)
            if generated_thumb:
                genre['art']['thumb'] = str(generated_thumb)

            if self.tag:
                xsp = '{"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]},{"field":"tag","operator":"is","value":["%s"]}]},"type":"%ss"}' % (genre['label'], self.tag, self.dbtype)
            else:
                xsp = '{"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"%ss"}' % (genre['label'],self.dbtype)

            genre['url'] = 'videodb://{0}s/titles/?xsp={1}'.format(self.dbtype, url_quote(xsp))

            genres.append(genre)

        add_items(self.li, genres, type='genre')
        set_plugincontent(content='videos', category=xbmc.getLocalizedString(135))


    ''' get movies by director
    '''
    def getdirectedby(self):
        if self.dbid:
            json_query = json_call('VideoLibrary.GetMovieDetails',
                                   properties=['title', 'director'],
                                   params={'movieid': int(self.dbid)}
                                   )

        try:
            directors = json_query['result']['moviedetails']['director']
            title = json_query['result']['moviedetails']['title']
            joineddirectors = ' / '.join(directors)
        except Exception:
            log('Movies by director: No director found')
            return

        filters=[]
        for director in directors:
            filters.append({'operator': 'is', 'field': 'director', 'value': director})

        json_query = json_call('VideoLibrary.GetMovies',
                               properties=JSON_MAP['movie_properties'],
                               sort=self.sort_random,
                               query_filter={'and': [{'or': filters}, {'operator': 'isnot', 'field': 'title', 'value': title}]}
                               )
        try:
            json_query = json_query['result']['movies']
        except Exception:
            log('Movies by director %s: No additional movies found' % joineddirectors)
            self._retry('getdirectedby')
            return

        add_items(self.li, json_query, type='movie', searchstring=joineddirectors)
        plugin_category = ADDON.getLocalizedString(32029) + ' ' + joineddirectors
        set_plugincontent(content='movies', category=plugin_category)


    ''' get items by actor
    '''
    def getitemsbyactor(self):
        ''' Pick random actor of provided DBID item
        '''
        if self.dbid:
            json_query = json_call(self.method_details,
                                   properties=['title', 'cast'],
                                   params={self.param: int(self.dbid)}
                                   )

            try:
                cast = json_query['result'][self.key_details]['cast']
                exclude = json_query['result'][self.key_details]['label']

                if not cast:
                    raise Exception

            except Exception:
                log('Items by actor: No cast found')
                return

            cast_range=[]
            i = 0
            for actor in cast:
                if i > 3:
                    break
                cast_range.append(actor['name'])
                i += 1

            actor = ''.join(random.choice(cast_range))

        else:
            actor = self.dblabel
            exclude = self.exclude

        if actor:
            filters = [{'operator': 'is', 'field': 'actor', 'value': actor}]
            if exclude:
                filters.append({'operator': 'isnot', 'field': 'title', 'value': exclude})

            if self.dbcontent != 'tvshow':
                movie_query = json_call('VideoLibrary.GetMovies',
                                        properties=JSON_MAP['movie_properties'],
                                        sort=self.sort_random,
                                        query_filter={'and': filters}
                                        )

                try:
                    movie_query = movie_query['result']['movies']
                except Exception:
                    log('Items by actor %s: No movies found' % actor)
                else:
                    add_items(self.li, movie_query, type='movie', searchstring=actor)

            if self.dbcontent != 'movie':
                tvshow_query = json_call('VideoLibrary.GetTVShows',
                                         properties=JSON_MAP['tvshow_properties'],
                                         sort=self.sort_random,
                                         query_filter={'and': filters}
                                         )

                try:
                    tvshow_query = tvshow_query['result']['tvshows']
                except Exception:
                    log('Items by actor %s: No shows found' % actor)
                else:
                    add_items(self.li, tvshow_query, type='tvshow', searchstring=actor)

            ''' Retry if query is based on dbid and a random actor
            '''
            if self.dbid and not self.li:
                self._retry('getitemsbyactor')

            plugin_category = ADDON.getLocalizedString(32030) + ' ' + actor
            set_plugincontent(content='videos', category=plugin_category)

            random.shuffle(self.li)


    ''' because you watched xyz
    '''
    def getsimilar(self):
        ''' Based on show or movie of the database
        '''
        if self.dbid:
            json_query = json_call(self.method_details,
                                   properties=['title', 'genre'],
                                   params={self.param: int(self.dbid)}
                                   )

        ''' Based on a random one of the last 10 watched items
        '''
        if not self.dbid:
            if self.dbtype == 'tvshow':
                query_filter={'or': [self.filter_watched, self.filter_watched_episodes]}
            else:
                query_filter=self.filter_watched

            json_query = json_call(self.method_item,
                                   properties=['title', 'genre'],
                                   sort={'method': 'lastplayed','order': 'descending'}, limit=10,
                                   query_filter=query_filter
                                   )

        ''' Get the genres of the selected item
        '''
        try:
            if self.dbid:
                title = json_query['result'][self.key_details]['title']
                genres = json_query['result'][self.key_details]['genre']
            else:
                similar_list = []
                for x in json_query['result'][self.key_items]:
                    if x['genre']:
                        similar_list.append(x)

                item_pos = self.params.get('pos')
                if not item_pos:
                    random.shuffle(similar_list)
                    i = 0
                else:
                    i = int(item_pos)

                title = similar_list[i]['title']
                genres = similar_list[i]['genre']

            if not genres:
                raise Exception

        except Exception:
            log ('Get similar: Not able to get genres')
            return

        random.shuffle(genres)

        ''' Get movies or shows based on one or two genres of selected watched item
        '''
        filters = [{'operator': 'isnot', 'field': 'title', 'value': title}, {'operator': 'is', 'field': 'genre', 'value': genres[0]}]
        if len(genres) > 1:
            filters.append({'operator': 'is', 'field': 'genre', 'value': genres[1]})
        if self.tag:
            filters.append(self.filter_tag)

        json_query = json_call(self.method_item,
                               properties=self.properties,
                               sort=self.sort_random, limit=15,
                               query_filter={'and': filters}
                               )

        try:
            json_query = json_query['result'][self.key_items]
        except KeyError:
            log('Get similar: No matching items found')
            self._retry('getsimilar')
            return

        add_items(self.li, json_query, type=self.dbtype, searchstring=title)
        plugin_category = ADDON.getLocalizedString(32031) + ' ' + title
        set_plugincontent(content='%ss' % self.dbtype, category=plugin_category)


    ''' get cast of item
    '''
    def getcast(self):
        try:
            if self.dbtitle:
                json_query = json_call(self.method_item,
                                       properties=['cast'],
                                       limit=1,
                                       query_filter=self.filter_title
                                       )

            elif self.dbid:
                if self.dbtype == 'tvshow' and self.idtype in ['season', 'episode']:
                    self.dbid = self._gettvshowid()

                json_query = json_call(self.method_details,
                                       properties=['cast'],
                                       params={self.param: int(self.dbid)}
                                       )

            if self.key_details in json_query['result']:
                cast = json_query['result'][self.key_details]['cast']

                ''' Fallback to TV show cast if episode has no cast stored
                '''
                if not cast and self.dbtype == 'episode':
                    tvshow_id = self._gettvshowid(idtype='episode', dbid=self.dbid)

                    json_query = json_call('VideoLibrary.GetTVShowDetails',
                                           properties=['cast'],
                                           params={'tvshowid': int(tvshow_id)}
                                           )

                    cast = json_query['result']['tvshowdetails']['cast']

            else:
                cast = json_query['result'][self.key_items][0]['cast']

            if not cast:
                raise Exception

        except Exception:
            log('Get cast: No cast found.')
            return

        add_items(self.li, cast, type='cast')


    ''' get full cast of movie set
    '''
    def getsetcast(self):
        movies = json_call('VideoLibrary.GetMovieSetDetails',
                           params={'setid': int(self.dbid)})

        try:
            movies = movies['result']['setdetails']['movies']
        except KeyError:
            return

        cast_list = {}
        for movie in movies:
            dbid = movie.get('movieid')
            dbtitle = movie.get('title')

            json_query = json_call('VideoLibrary.GetMovieDetails',
                                   properties=['cast'],
                                   params={'movieid': dbid}
                                   )
            try:
                cast = json_query['result']['moviedetails']['cast']
            except KeyError:
                continue

            for actor in cast:
                actor_name = actor.get('name')
                actor_role = actor.get('role')
                actor_thumbnail = actor.get('thumbnail')

                if actor_name not in cast_list:
                    cast_list[actor_name] = {'thumbnail': actor.get('thumbnail')}

                if not cast_list[actor_name].get('thumbnail') and actor_thumbnail:
                    cast_list[actor_name].update({'thumbnail': actor_thumbnail})

                if actor_role:
                    roles = cast_list[actor_name].get('roles', [])

                    if actor_role not in roles:
                        roles.append(actor_role)
                        cast_list[actor_name].update({'roles': roles})


        cast_cleaned = []
        for actor in cast_list:
            cast_cleaned.append({'name': actor,
                                 'thumbnail': cast_list[actor].get('thumbnail'),
                                 'role': get_joined_items(cast_list[actor].get('roles', []))
                                 })

        add_items(self.li, cast_cleaned, type='cast')


    ''' jump to letter for smsjump navigation
    '''
    def jumptoletter(self):
        if xbmc.getInfoLabel('Container.NumItems'):
            all_letters = []
            for i in range(int(xbmc.getInfoLabel('Container.NumItems'))):
                all_letters.append(xbmc.getInfoLabel('Listitem(%s).SortLetter' % i).upper())

            if len(all_letters) > 1:
                numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
                alphabet = ['#', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
                letter_count = 0
                first_number = False

                for item in numbers:
                    if item in all_letters:
                        letter_count += 1
                        first_number = item
                        break

                for item in alphabet:
                    if item in all_letters:
                        letter_count += 1

                if letter_count < 2:
                    return

                for letter in alphabet:
                    li_item = xbmcgui.ListItem(label=letter, offscreen=True)

                    if letter == '#' and first_number:
                        li_path = 'plugin://script.embuary.helper/?action=smsjump&letter=0'
                        li_item.setProperty('IsNumber', first_number)
                        append = True

                    elif letter in all_letters:
                        li_path = 'plugin://script.embuary.helper/?action=smsjump&letter=%s' % letter
                        append = True

                    elif get_bool(self.params.get('showall', 'true')):
                        li_path = ''
                        li_item.setProperty('NotAvailable', 'true')
                        append = True

                    else:
                        append = False

                    if append:
                        self.li.append((li_path, li_item, False))


    ''' get a list of items with existing fanart for backgrounds based on a playlist
    '''
    def getfanartsbypath(self):
        path = get_clean_path(self.params.get('path'))

        json_query = json_call('Files.GetDirectory',
                               properties=['art', 'title'],
                               params={'directory': path}
                               )

        try:
            for item in json_query['result']['files']:
                arts = item.get('art', {})

                if not arts.get('fanart'):
                    continue

                li_item = xbmcgui.ListItem(label=item.get('title'), offscreen=True)
                li_item.setArt(arts)
                self.li.append(('', li_item, False))

        except Exception:
            return

    ''' get path stats of playlists etc
    '''
    def getpathstats(self):
        path = get_clean_path(self.params.get('path'))
        prop_prefix = self.params.get('prefix', 'Stats')

        played = 0
        numitems = 0
        inprogress = 0
        episodes = 0
        watchedepisodes = 0
        tvshowscount = 0
        tvshows = []

        json_query = json_call('Files.GetDirectory',
                               properties=['playcount', 'resume', 'episode', 'watchedepisodes', 'tvshowid'],
                               params={'directory': path, 'media': 'video'}
                               )

        try:
            for item in json_query['result']['files']:
                if 'type' not in item:
                    continue

                if item['type'] == 'episode':
                    episodes += 1
                    if item['playcount'] > 0:
                        watchedepisodes += 1
                    if item['tvshowid'] not in tvshows:
                        tvshows.append(item['tvshowid'])
                        tvshowscount += 1

                elif item['type'] == 'tvshow':
                    episodes += item['episode']
                    watchedepisodes += item['watchedepisodes']
                    tvshowscount += 1

                else:
                    numitems += 1
                    if 'playcount' in list(item.keys()):
                        if item['playcount'] > 0:
                            played += 1
                        if item['resume']['position'] > 0:
                            inprogress += 1

        except Exception:
            pass

        winprop('%s_Watched' % prop_prefix, str(played))
        winprop('%s_Count' % prop_prefix, str(numitems))
        winprop('%s_TVShowCount' % prop_prefix, str(tvshowscount))
        winprop('%s_InProgress' % prop_prefix, str(inprogress))
        winprop('%s_Unwatched' % prop_prefix, str(numitems - played))
        winprop('%s_Episodes' % prop_prefix, str(episodes))
        winprop('%s_WatchedEpisodes' % prop_prefix, str(watchedepisodes))
        winprop('%s_UnwatchedEpisodes' % prop_prefix, str(episodes - watchedepisodes))


    ''' function to return the TV show id based on a season or episode id
    '''
    def _gettvshowid(self,dbid=None,idtype=None):
        try:
            if not dbid:
                dbid = self.dbid

            if not idtype:
                idtype = self.idtype

            if idtype == 'season':
                method_details = 'VideoLibrary.GetSeasonDetails'
                param = 'seasonid'
                key_details = 'seasondetails'
            elif idtype == 'episode':
                method_details = 'VideoLibrary.GetEpisodeDetails'
                param = 'episodeid'
                key_details = 'episodedetails'
            else:
                raise Exception

            json_query = json_call(method_details,
                                   properties=['tvshowid'],
                                   params={param: int(dbid)}
                                   )

            result = json_query['result'][key_details]
            dbid = result.get('tvshowid')

            return dbid

        except Exception:
            return ''


    ''' retry loop for random based widgets if previous run has not returned any single item
    '''
    def _retry(self,type):
        log('Retry to get content (%s)' % str(self.retry_count))

        if self.retry_count < 5:
            self.retry_count += 1
            getattr(self, type)()

        else:
            log('No content found. Stop retrying.')
            self.retry_count = 1
