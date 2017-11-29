# -*- coding: utf-8 -*-

import cookielib
import datetime
import re
import urllib
import urllib2
import zlib
import json
import itertools

import bs4

import xbmc
from SubtitleHelper import log

class SubtitleOption(object):
    def __init__(self, subtitle_option_row):
        onclick_action_string = subtitle_option_row.find("td", { "class" : "desktop" }).find("button").get("onclick")
        if not onclick_action_string:
            return

        params_match = re.search("\((?P<sub_id>\d+),\'(?P<option_id>\w*)\',", onclick_action_string)
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
        season_div    = subtitle_soup("div", { 'id': 'tabs4-season%s' % season_number })
        if not season_div:
            return None

        episode_options = season_div[0].findAll("a")
        episode_option = next((episode_option for episode_option in episode_options if ((episode_option.contents[0] == u'פרק %s' % episode_number) or (episode_option.contents[0] == u'פרק %s - אחרון לעונה' % episode_number))), None)
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
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
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

class TorecGuestTokenGenerator():
    def __init__(self, sub_id, handle_daylight_saving_skew):
        self.sub_id = sub_id
        self.handle_daylight_saving_skew = handle_daylight_saving_skew

    def generate_ticket(self):
        return self._gen_fake_encoded_ticket(self.sub_id, 90)

    def _gen_plain_ticket(self, sub_id, secs_ago):
        t = datetime.datetime.now() - datetime.timedelta(seconds=secs_ago)
        if self.handle_daylight_saving_skew:
            t -= datetime.timedelta(hours = 1)

        st = t.strftime("%m/%d/%Y %-I:%M:%S %p")
        st = re.sub("(^|/| )0", r"\1", st)
        return "{}_sub{}".format(st, sub_id)

    def _encode_ticket(self, plain_ticket):
        return ''.join(
            format(ord(p) + ord(o), 'X')
            for p, o in zip(plain_ticket, itertools.cycle("imet"))
            )

    def _decode_ticket(self, ticket): 
        split_ticket = re.findall('..', ticket)

        return ''.join(
            chr(int(p, 16) - ord(o))
            for p, o in zip(split_ticket, itertools.cycle("imet"))
            )

    def _gen_fake_encoded_ticket(self, sub_id, secs_ago):
        return self._encode_ticket(self._gen_plain_ticket(sub_id, secs_ago))

class TorecSubtitlesDownloader(FirefoxURLHandler):
    MAXIMUM_WAIT_TIME_MSEC = 13 * 1000

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
            "screen_width": 1680,
            "subId": sub_id,
            "current_datetime": current_time
        }

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

    def _request_subtitle(self, sub_id):
        params = {
            "sub_id"  : sub_id, 
            "s"       : 1440
        }

        response = self.opener.open("%s/ajax/sub/guest_time.asp" % self.BASE_URL, urllib.urlencode(params))
        return response.read()

    def _extract_code(self, rcode):
        rcodes = re.findall(".", rcode)
        
        return ''.join([str(ord(rcodes[i]) - 68) for i in xrange(len(rcodes))])

    def _request_code(self, sub_id, option_id):
        params = {
            "sub_id"  : sub_id, 
            "codes"   : option_id,
        }

        response      = self.opener.open("%s/ajax/sub/t7/guest_dl_popup.asp" % self.BASE_URL, urllib.urlencode(params))
        response_data = response.read()

        code_match = re.search("code=(\w{4})", response_data)
        if not code_match:
            return None

        code = code_match.group(1)
        return code

    def _confirm_download_code(self, sub_id, option_id):
        rcode = self._request_code(sub_id, option_id)
        if not rcode:
            return

        code = self._extract_code(rcode)

        params = {
            "sub_id" : sub_id, 
            "code"   : code,
            "rcode"  : rcode
        }

        response      = self.opener.open("%s/ajax/sub/t7/guest_dl_code.asp" % self.BASE_URL, urllib.urlencode(params))
        response_data = response.read()

    def _try_get_download_link(self, sub_id, option_id, guest_token):
        encoded_params = urllib.urlencode({
                "sub_id":     sub_id,
                "code":       option_id,
                "sh":         "yes",
                "guest":      guest_token,
                "timewaited": 13
        })

        response = self.opener.open("%s/ajax/sub/t7/downloadun.asp" % self.BASE_URL, encoded_params)

        download_link = response.read()
        if download_link and "sdls.asp" in download_link:
            return download_link
        else:
            return None

    def _get_download_link_with_regular_token(self, sub_id, option_id):
        guest_token = self._request_subtitle(sub_id)

        download_link  = None
        waited_msec    = 0.0

        # Torec website may delay download up to 13 seconds
        while (not xbmc.abortRequested) and (waited_msec < self.MAXIMUM_WAIT_TIME_MSEC):
            download_link = self._try_get_download_link(sub_id, option_id, guest_token) 
            if download_link:
                break

            xbmc.sleep(500)
            waited_msec += 500
        
        log(__name__, "received link after sleeping %f seconds" % (waited_msec / 1000.0))

        return download_link

    def get_download_link(self, sub_id, option_id):
        self._confirm_download_code(sub_id, option_id)

        log(__name__, "trying to retrieve download link with skewed generated guest token")
        generated_time_skewed_guest_token = TorecGuestTokenGenerator(sub_id, True).generate_ticket()
        download_link = self._try_get_download_link(sub_id, option_id, generated_time_skewed_guest_token)
        if download_link:
            return download_link

        log(__name__, "trying to retrieve download link with generated guest token")
        generated_guest_token = TorecGuestTokenGenerator(sub_id, False).generate_ticket()
        download_link = self._try_get_download_link(sub_id, option_id, generated_guest_token)
        if download_link:
            return download_link

        log(__name__, "trying to retrieve download link with guest token request")
        return self._get_download_link_with_regular_token(sub_id, option_id)
        

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
