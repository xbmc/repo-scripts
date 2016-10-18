# -*- coding: utf-8 -*-

import cookielib
import datetime
import re
import time
import urllib
import urllib2
import zlib
import json

import bs4

from SubtitleHelper import log

class SubtitleOption(object):
    def __init__(self, subtitle_option_row):
        onclick_action_string = subtitle_option_row.find("td", { "class" : "desktop" }).find("button").get("onclick")
        params_match = re.match("downloadSub\(\'(?P<option_id>\w*)\',(?P<sub_id>\d+),", onclick_action_string)
        if not params_match:
            return

        self.name      = subtitle_option_row.find("td", { "class" : "version" }).contents[1].strip()
        self.option_id = params_match.group("option_id")
        self.sub_id    = params_match.group("sub_id")

    def __repr__(self):
        return "%s" % self.name

class TVShowPage():
    def __init__(self, data):
        self.data = data

    def fetch_url(self, season_number, episode_number):
        subtitle_soup = bs4.BeautifulSoup(self.data, "html.parser")
        episode_options = subtitle_soup(
            "div", {
                'id': 'tabs4-season%s' % season_number
            }
        )[0].findAll("a")

        episode_option = next((episode_option for episode_option in episode_options if (episode_option.contents[0] == u'פרק %s' % episode_number)), None)
        if not episode_option:
            return None

        return episode_option['href']

class SubtitlesPage():
    def __init__(self, data):
        self.options = self._parse_options(data)

    def _parse_options(self, data):
        subtitles_soup = bs4.BeautifulSoup(data, "html.parser")
        subtitle_options_rows = subtitles_soup.findAll("tr", {"id" : re.compile('dlRow_.*')})
    
        return map(lambda subtitle_option_row: SubtitleOption(subtitle_option_row), subtitle_options_rows)

class Response(object):
    def __init__(self, response):
        self.data = self._handle_data(response)
        self.headers = response.headers

    def _handle_data(self, resp):
        data = resp.read()
        if len(data) != 0:
            try:
                data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
            except zlib.error:
                pass
        return data


class FirefoxURLHandler(object):
    """
    Firefox user agent class
    """
    def __init__(self):
        cookie = "torec.cookie"
        cj = cookielib.MozillaCookieJar(cookie)

        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(),
            urllib2.HTTPCookieProcessor(cj)
        )
        self.opener.addheaders = [
            (
                'User-agent', (
                    'Mozilla/4.0 (compatible; MSIE 6.0; '
                    'Windows NT 5.2; .NET CLR 1.1.4322)'
                ),

            )
        ]

    def login(self):
        username = __addon__.getSetting("username")
        password = __addon__.getSetting("password")
        login_data_ = {
            "ref": "/Default.asp?",
            "Form": "True",
            "site": "true",
            "username": username,
            "password": password,
            "login": "submit"
        }
        login_data = urllib.urlencode(login_data_)
        login_url = "http://www.torec.net/login.asp"
        response = self.opener.open(login_url, login_data)
        content = ''.join(response.readlines())
        return username in content

class TorecSubtitlesDownloader(FirefoxURLHandler):
    DEFAULT_SEPERATOR = " "
    BASE_URL          = "http://www.xn--9dbf0cd.net"
    SUBTITLE_PATH     = "sub.asp?sub_id="
    DEFAULT_COOKIE    = (
        "Torec_NC_sub_%(subId)s=sub=%(current_datetime)s; Torec_NC_s="
        "%(screen_width)d"
    )

    def __init__(self):
        super(TorecSubtitlesDownloader, self).__init__()

    def _build_default_cookie(self, sub_id):
        current_time = datetime.datetime.now().strftime("%m/%d/%Y+%I:%M:%S+%p")
        return self.DEFAULT_COOKIE % {
            "screen_width": 1440,
            "subId": sub_id,
            "current_datetime": current_time
        }

    def _get_user_auth(self, subw_text):
        return re.search(r"userAuth='(.*)';", subw_text).group(1)

    def _get_time_waited(self, subw_text):
        return re.search(r"seconds\s+=\s+(\d+);", subw_text).group(1)

    def _request_subtitle(self, sub_id):
        params = {
            "sub_id"  : sub_id, 
            "s"       : 1440
        }

        response = self.opener.open("%s/ajax/sub/guest_time.asp" % self.BASE_URL, urllib.urlencode(params))
        return response.read()

    def _fetch_main_url(self, name):
        log(__name__, "fetching main url for name %s" % name)
        search_response = self.opener.open(
            "%s/ajax/search/acSearch.asp" % self.BASE_URL,
            urllib.urlencode({"query": name }))

        suggestions = search_response.read()
        if not suggestions:
            log(__name__, "couldn't find suggestions for query %s" % name)
            return None

        try:
            json_suggestions = json.loads(suggestions)
            return json_suggestions["suggestions"][0]["data"]
        except ValueError, e:
            return None

    def _fetch_episode_url(self, series_url, season_number, episode_number):
        series_page_response = self.opener.open(
            "%s/%s" % (self.BASE_URL, series_url))
        series_page_data = series_page_response.read()

        tvshow_page = TVShowPage(series_page_data)
        return tvshow_page.fetch_url(season_number, episode_number)

    def _fetch_subtitles_options(self, subtitles_page_url):
        subtitles_page_response = self.opener.open("%s/%s" % (self.BASE_URL, subtitles_page_url))
        subtitles_page_data = subtitles_page_response.read()

        subtitles_page = SubtitlesPage(subtitles_page_data)
        return subtitles_page.options

    def search_tvshow(self, tvshow_name, season_number, episode_number):
        main_url = self._fetch_main_url(tvshow_name)
        if not main_url:
            log(__name__, "couldn't find main URL for %s" % tvshow_name)
            return None

        episode_url = self._fetch_episode_url(main_url, season_number, episode_number)
        if not episode_url:
            log(__name__, "couldn't find episode URL for tvshow name %s, season %s episode %s" % (tvshow_name, season_number, episode_number))
            return None            
        
        return self._fetch_subtitles_options(episode_url)

    def search_movie(self, movie_name):
        main_url = self._fetch_main_url(movie_name)
        if not main_url:
            log(__name__, "couldn't find main URL for %s" % movie_name)
            return None

        return self._fetch_subtitles_options(main_url)

    def get_download_link(self, sub_id, option_id):
        params    = {
            "sub_id":     sub_id,
            "code":       option_id,
            "sh":         "yes",
            "guest":      self._request_subtitle(sub_id),
            "timewaited": 9
        }

        response = self.opener.open("%s/ajax/sub/downloadun.asp" % self.BASE_URL, urllib.urlencode(params))
        return response.read()

    def download(self, download_link):
        if not download_link:
            log(__name__, "no download link found")
            return None, None

        response = self.opener.open(
            "%s%s" % (self.BASE_URL, download_link)
        )
        data = response.read()
        file_name = re.search(
            "filename=(.*)", response.headers["content-disposition"]
        ).groups()[0]
        return data, file_name

    def sanitize(self, name):
        cleaned_name = re.sub('[\']', '', name.upper())
        return re.sub('[\.\[\]]', self.DEFAULT_SEPERATOR, cleaned_name)

    def find_most_relevant_option(self, name, subtitles_options):
        tokenized_name = self.sanitize(name).split()
        # Find the most likely subtitle (the subtitle which adheres to most of
        # the movie properties)
        max_likelihood = 0
        most_relevant_option = None
        for option in subtitles_options:
            subtitle_name = self.sanitize(option.name).split()
            subtitle_likelihood = 0
            for token in subtitle_name:
                if token in tokenized_name:
                    subtitle_likelihood += 1
                if subtitle_likelihood > max_likelihood:
                    max_likelihood = subtitle_likelihood
                    most_relevant_option = option

        return most_relevant_option

    def get_best_match_id(self, name, subtitles_options):
        most_relevant_option = self.find_most_relevant_option(name, subtitles_options)

        return (most_relevant_option.option_id if most_relevant_option is not None else None)
