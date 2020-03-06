#!/usr/bin/python
# coding: utf-8

########################

import requests

from resources.lib.helper import *
from resources.lib.tvdb import *
from resources.lib.trakt import *
from resources.lib.localdb import *

########################

class NextAired():
    def __init__(self):
        utc_date = arrow.utcnow()
        local_date = utc_date.to(TIMEZONE)
        self.date_today = utc_date.strftime('%Y-%m-%d')

        local_media = get_local_media()
        self.local_media = local_media['shows']

        for item in self.local_media:
            del item['playcount']
            del item['watchedepisodes']

        cache_key = 'nextaired_' + self.date_today + '_' + md5hash(self.local_media)
        self.airing_items = get_cache(cache_key)

        if not self.airing_items:
            self.valid_days = []
            tmp_day = local_date
            for i in range(7):
                self.valid_days.append(tmp_day.strftime('%Y-%m-%d'))
                tmp_day = tmp_day.shift(days=1)

            airing_items = {}
            airing_items['week'] = []
            airing_items['0'] = []
            airing_items['1'] = []
            airing_items['2'] = []
            airing_items['3'] = []
            airing_items['4'] = []
            airing_items['5'] = []
            airing_items['6'] = []

            self.airing_items = airing_items
            self.getdata()

        if self.airing_items:
            write_cache(cache_key, self.airing_items, 24)

    def get(self,day=None):
        if day is not None and day in self.airing_items:
            return self.airing_items[day]
        else:
            return self.airing_items['week']

    def getdata(self):
        if not self.local_media:
            return

        local_media_data = []
        for item in self.local_media:
            local_media_data.append([item.get('tmdbid'), item.get('tvdbid'), item.get('imdbnumber'), item.get('art'), item.get('title'), item.get('originaltitle'), item.get('year')])

        tvdb_api = TVDB_API()
        trakt_results = trakt_api('/calendars/all/shows/' + self.date_today + '/8?extended=full&countries=' + COUNTRY_CODE.lower() + '%2Cus')

        if trakt_results:
            for item in trakt_results:
                airing_date, airing_time = utc_to_local(item.get('first_aired'))
                weekday, weekday_code = date_weekday(airing_date)

                ''' Because Trakt is using UTC dates it's possible that the airing item is already in the past
                    for some timezones. Let's compare the converted airing date and only pick the ones for the
                    users timezone.
                '''
                if airing_date not in self.valid_days:
                    continue

                show = item.get('show', {})
                episode = item.get('episode', {})

                tvshowtitle = show.get('title')
                network = show.get('network')
                country = show.get('country')
                status = show.get('status')
                runtime = episode.get('runtime') * 60 if episode.get('runtime') else 0
                year = show.get('year')
                tmdb_id = show.get('ids', {}).get('tmdb')
                tvdb_id = show.get('ids', {}).get('tvdb')
                imdb_id = show.get('ids', {}).get('imdb')
                tvdb_id_episode = episode.get('ids', {}).get('tvdb')

                for i in local_media_data:
                    if str(tmdb_id) == i[0] or str(tvdb_id) == i[1] or str(imdb_id) == i[2] or (tvshowtitle in [i[4], i[5]] and year == i[6]):
                        tvdb_cache_key = 'nextaired_tvdb_episode_' + COUNTRY_CODE + '_' + str(tvdb_id_episode)
                        tvdb_query = get_cache(tvdb_cache_key)

                        if not tvdb_query:
                            tvdb_query = tvdb_api.call('/episodes/' + str(tvdb_id_episode))

                            if tvdb_query:
                                write_cache(tvdb_cache_key, tvdb_query, 48)

                        if tvdb_query and not tvdb_query['overview'] and COUNTRY_CODE != 'US':
                            tvdb_fallback_cache_key = 'nextaired_tvdb_episode_US_' + str(tvdb_id_episode)
                            tvdb_query = get_cache(tvdb_fallback_cache_key)

                            if not tvdb_query:
                                tvdb_query = tvdb_api.call('/episodes/' + str(tvdb_id_episode), lang='us')

                                if tvdb_query:
                                    write_cache(tvdb_fallback_cache_key, tvdb_query, 48)


                        if tvdb_query:
                            tvdb_query['localart'] = i[3]
                            tvdb_query['showtitle'] = i[4] or i[5]
                            tvdb_query['airing'] = airing_date
                            tvdb_query['airing_time'] = airing_time
                            tvdb_query['weekday'] = weekday
                            tvdb_query['weekday_code'] = weekday_code
                            tvdb_query['network'] = network
                            tvdb_query['country'] = country
                            tvdb_query['status'] = status
                            tvdb_query['runtime'] = runtime

                            self.airing_items['week'].append(tvdb_query)
                            self.airing_items[str(weekday_code)].append(tvdb_query)

                        break