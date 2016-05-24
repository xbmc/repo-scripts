import cookielib
import datetime
import re
import time
import urllib
import urllib2
import zlib

import bs4
import xbmc
import xbmcaddon

from SubtitleHelper import log

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version')  # Module version
__scriptname__ = __addon__.getAddonInfo('name')
__language__ = __addon__.getLocalizedString

class SubtitleOption(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id

    def __repr__(self):
        return "%s" % self.name

class SubtitlePage(object):
    def __init__(self, id, name, url, data):
        self.id = id
        self.name = name
        self.url = url
        self.options = self._parse_options(data)

    def _parse_options(self, data):
        subtitle_soup = bs4.BeautifulSoup(data, "html.parser")
        subtitle_options = subtitle_soup(
            "div", {
                'class': 'download_box'
            }
        )[0].findAll("option")
        filtered_subtitle_options = filter(
            lambda x: x.get("value") is not None, subtitle_options
        )
        return map(
            lambda x: SubtitleOption(x.string.strip(), x["value"]),
            filtered_subtitle_options
        )


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
        if username not in content:
            xbmc.executebuiltin(
                (u'Notification(%s,%s)' %
                 (__scriptname__, __language__(32005))).encode('utf-8')

            )
            return False
        return True


class TorecSubtitlesDownloader(FirefoxURLHandler):
    DEFAULT_SEPERATOR = " "
    BASE_URL          = "http://www.torec.net"
    SUBTITLE_PATH     = "sub.asp?sub_id="
    USER_AUTH_JS_URL  = "http://www.torec.net/gjs/subw.js"
    DEFAULT_COOKIE    = (
        "Torec_NC_sub_%(subId)s=sub=%(current_datetime)s; Torec_NC_s="
        "%(screen_width)d"
    )

    def __init__(self):
        super(TorecSubtitlesDownloader, self).__init__()

    def _build_default_cookie(self, sub_id):
        current_time = datetime.datetime.now().strftime("%m/%d/%Y+%I:%M:%S+%p")
        return self.DEFAULT_COOKIE % {
            "screen_width": 1760,
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

         return self.opener.open("%s/ajax/sub/guest_time.asp" % self.BASE_URL, urllib.urlencode(params)).read()

    def search(self, movie_name):
        santized_name = self.sanitize(movie_name)
        log(__name__, "Searching for %s" % santized_name)
        subtitle_page = self.search_by_movie_name(santized_name)
        if subtitle_page is None:
            log(__name__, "Couldn't find relevant subtitle page")
            return None
        else:
            log(__name__, "Found relevant meta data")
            return subtitle_page

    def search_by_movie_name(self, movie_name):
        """
        Search for movie subtitle

        :param movie_name:
        :return:
        """
        response = self.opener.open(
            "%s/ssearch.asp" % self.BASE_URL,
            urllib.urlencode({"search": movie_name})
        )
        data = response.read()
        match = re.search('sub\.asp\?sub_id=(\w+)', data)
        if not match:
            return None

        id_ = match.groups()[0]
        sub_url = "%s/%s%s" % (self.BASE_URL, self.SUBTITLE_PATH, id_)
        subtitle_data = self.opener.open(sub_url)
        subtitle_data = subtitle_data.read()
        return SubtitlePage(id_, movie_name, sub_url, subtitle_data)

    def get_download_link(self, sub_id, option_id):        
        subw_text = self.opener.open(self.USER_AUTH_JS_URL).read()
        params    = {
            "sub_id":     sub_id,
            "code":       option_id,
            "sh":         "yes",
            "guest":      self._request_subtitle(sub_id),
            "timewaited": self._get_time_waited(subw_text),
            "userAuth":   self._get_user_auth(subw_text)
        }

        response = self.opener.open("%s/ajax/sub/downloadun.asp" % self.BASE_URL, urllib.urlencode(params))
        return response.read()

    def download(self, download_link):
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
        return re.sub('[\.\[\]\-]', self.DEFAULT_SEPERATOR, cleaned_name)

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

    def get_best_match_id(self, name, subtitle_page):
        most_relevant_option = self.find_most_relevant_option(
            name, subtitle_page.options
        )
        return (
            most_relevant_option.id if most_relevant_option is not None else
            None
        )
