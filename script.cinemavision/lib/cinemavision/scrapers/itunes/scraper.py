"""
     Apple Trailers Kodi Addon
    Copyright (C) 2016 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
import urllib2
import urlparse
import json
import time
import datetime
from email.utils import parsedate_tz
import xml.etree.ElementTree as ET

BASE_URL = 'http://trailers.apple.com/trailers'
COVER_BASE_URL = 'http://trailers.apple.com'
MOVIES_URL = BASE_URL + '/home/feeds/%s.json'
TRAILERS_URL = BASE_URL + '/feeds/data/%s.json'
XML_URL = BASE_URL + '/home/xml/current.xml'
USER_AGENT = 'iTunes'
BROWSER_UA = 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'
XHR = {'X-Requested-With': 'XMLHttpRequest'}
SOURCES = ['src', 'srcAlt']
RATINGS = {'NOT YET RATED': 'NR', 'NOTYETRATED': 'NR', 'PG13': 'PG-13', 'NC17': 'NC-17'}
CACHE_LIMITS = [24, 12, 8]


class Scraper(object):
    def __init__(self):
        self.extras = self.__get_extras()

    def get_all_movies(self, limit=0):
        return self.__get_movies('studios', limit)

    def get_most_popular_movies(self, limit=0):
        return self.__get_movies('most_pop', limit)

    def get_exclusive_movies(self, limit=0):
        return self.__get_movies('exclusive', limit)

    def get_most_recent_movies(self, limit=0):
        return self.__get_movies('just_added', limit)

    def __get_movie_id(self, url):
        headers = {'User-Agent': BROWSER_UA}
        html = self.__get_url(url, headers)
        match = re.search('''var\s+FilmId\s+=\s*['"]([^"']+)''', html)
        if match:
            return match.group(1)

    def __get_movies(self, source, limit):
        for i, movie in enumerate(self.__get_json(MOVIES_URL % (source))):
            if limit and i >= limit:
                break
            meta = {}
            meta['mediatype'] = 'movie'
            meta['title'] = meta['originaltitle'] = movie['title']
            premiered = self.__date(movie.get('releasedate'))
            if premiered:
                meta['premiered'] = premiered
                meta['year'] = meta['premiered'][-4:]
            meta['releasedatetime'] = self.__datetime(movie.get('releasedate'))
            meta['releasedate'] = self.__date(movie.get('releasedate'))
            meta['postdate'] = self.__recent_date(movie['trailers'])
            meta['poster'] = self.__make_poster(movie['poster'])
            meta['fanart'] = self.__make_background(movie['poster'])
            meta['studio'] = movie.get('studio', '')
            rating = movie.get('rating', '').upper()
            meta['mpaa'] = RATINGS.get(rating, rating)
            meta['director'] = movie.get('directors', '')
            meta['genre'] = ', '.join(movie.get('genre', []))
            meta['cast'] = movie.get('actors', [])
            meta['location'] = movie.get('location', '')
            if 'trailers' in movie and movie['trailers']:
                post_date = max([self.__date(trailer['postdate']) for trailer in movie['trailers']])
            else:
                post_date = ''
            meta['date'] = post_date
            meta['tagline'] = movie.get('moviesite', '')

            extras = self.extras.get(meta['title'], {})
            meta['movie_id'] = extras.get('id', '')
            meta['plot'] = meta['plotoutline'] = extras.get('plot', '')
            if 'duration' in extras and extras['duration']:
                meta['duration'] = extras['duration']
            yield meta

    def get_trailers(self, location, movie_id):
        page_url = urlparse.urljoin(BASE_URL, location)
        if not movie_id.isdigit():
            movie_id = self.__get_movie_id(page_url)

        if movie_id:
            headers = {'User-Agent': BROWSER_UA, 'Referer': page_url}
            headers.update(XHR)
            js_data = self.__get_json(TRAILERS_URL % (movie_id), headers)
            try:
                page = self.__get_page(js_data['page'])
            except:
                page = {}
            try:
                details = self.__get_details(js_data['details'])
            except:
                details = {}
            try:
                reviews = self.__get_reviews(js_data['reviews'])
            except:
                reviews = {}
            if 'clips' in js_data:
                for clip in js_data['clips']:
                    meta = {}
                    meta.update(page)
                    meta.update(details)
                    meta.update(reviews)

                    if page['movie_title']:
                        meta['title'] = '%s (%s)' % (page['movie_title'], clip.get('title', 'Trailer'))
                    else:
                        meta['title'] = clip.get('title', 'Trailer')
                    meta['studio'] = clip.get('artist', '')
                    meta['thumb'] = clip.get('screen', clip.get('thumb', ''))
                    if 'runtime' in clip:
                        meta['duration'] = self.__get_duration(clip['runtime'], mult=1)
                    if 'posted' in clip:
                        meta['premiered'] = clip['posted']
                    meta['streams'] = self.__get_streams(clip)
                    yield meta

    def __get_extras(self):
        xml = self.__get_url(XML_URL)
        xml = re.sub('[^\x00-\x7F]', '', xml)
        xml = re.sub('[\x01-\x08\x0B-\x0C\x0E-\x1F]', '', xml)
        root = ET.fromstring(xml)
        plots = {}
        for movie in root.findall('.//movieinfo'):
            info = movie.find('info')
            title = info.find('title').text
            if title:
                desc = info.find('description')
                desc = '' if desc is None else desc.text
                runtime = info.find('runtime')
                duration = '' if runtime is None else self.__get_duration(runtime.text)
                plots[title] = {'id': movie.get('id', ''), 'plot': desc, 'duration': duration}
        return plots

    def __get_page(self, page):
        movie_title = page.get('movie_title', '')
        mpaa_rating = page.get('movie_rating', '').upper()
        mpaa_rating = RATINGS.get(mpaa_rating, mpaa_rating)
        meta = {'movie_title': movie_title, 'mpaa': mpaa_rating}
        release_date = page.get('release_date', '')
        if release_date:
            release_date = '%s.%s.%s' % (release_date[-2:], release_date[5:7], release_date[0:4])
            meta['premiered'] = release_date
            meta['year'] = release_date[-4:]
        return meta

    def __get_details(self, details):
        try:
            plot = details['locale']['en']['synopsis']
        except:
            plot = ''
        try:
            directors = self.__get_cast(details['locale']['en']['castcrew']['directors'])
        except:
            directors = []
        try:
            writers = self.__get_cast(details['locale']['en']['castcrew']['writers'])
        except:
            writers = []
        try:
            cast = self.__get_cast(details['locale']['en']['castcrew']['actors'])
        except:
            cast = []
        try:
            genre = self.__get_genre(details['genres'])
        except:
            genre = []
        return {'plot': plot, 'director': ', '.join(directors), 'writer': ', '.join(writers), 'cast': cast, 'genre': ', '.join(genre)}

    def __get_reviews(self, reviews):
        rating = reviews.get('rating', '')
        votes = reviews('count', '')
        return {'rating': rating, 'votes': votes}

    def __get_streams(self, clip):
        streams = {}
        if 'versions' in clip and 'enus' in clip['versions'] and 'sizes' in clip['versions']['enus']:
            sizes = clip['versions']['enus']['sizes']
            for key in sizes:
                for source in SOURCES:
                    if source in sizes[key] and sizes[key][source]:
                        streams[key] = sizes[key][source]
                        break
        return streams

    def __get_cast(self, cast):
        return [person.get('name', '') for person in cast]

    def __get_genre(self, genres):
        return [genre.get('name', '') for genre in genres]

    def __get_duration(self, runtime, mult=60):
        duration = 0
        for time_ in runtime.split(':')[::-1]:
            try:
                time_ = int(time_)
            except:
                time_ = 0
            duration += time_ * mult
            mult *= 60
        return duration

    def __date(self, date_str):
            if date_str:
                d = parsedate_tz(date_str)
                return '%02d.%02d.%04d' % (d[2], d[1], d[0])
            return ''

    def __datetime(self, date_str):
        if date_str:
            try:
                d = parsedate_tz(date_str)
                return datetime.datetime.fromtimestamp(time.mktime(d[:9]))
            except:
                import traceback
                traceback.print_exc()

        return None

    def __recent_date(self, t_list):
        d = max((parsedate_tz(d['postdate']) for d in t_list))
        return '%02d.%02d.%04d' % (d[2], d[1], d[0])

    def __make_poster(self, url):
        if not url.startswith('http'):
            url = urlparse.urljoin(COVER_BASE_URL, url)
        return url.replace('poster', 'poster-xlarge')

    def __make_background(self, url):
        if not url.startswith('http'):
            url = urlparse.urljoin(COVER_BASE_URL, url)
        return url.replace('poster', 'background')

    def __get_json(self, url, headers=None):
        try:
            html = self.__get_url(url, headers)
            return json.loads(html)
        except ValueError:
            return {}

    def __get_url(self, url, headers=None):
        if headers is None:
            headers = {'User-Agent': USER_AGENT}

        req = urllib2.Request(url, None, headers)
        html = urllib2.urlopen(req).read()
        return html
