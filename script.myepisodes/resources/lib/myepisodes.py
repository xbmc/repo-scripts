#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import cookielib
import re
import urllib, urllib2, urlparse

# This is totally stolen from script.xbmc.subtitles plugin !
REGEX_EXPRESSIONS = [
    '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
    '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09
    '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
    '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
    '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
    'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',
    '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
    '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                 #foo_[s01]_[e01]
    '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',        #foo, s01e01, foo.s01.e01, foo.s01-e01
    's([0-9]+)ep([0-9]+)[^\\/]*',                              #foo - s01ep03, foo - s1ep03
    '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
    '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
    ]

MYEPISODE_URL = "http://www.myepisodes.com"

class MyEpisodes(object):

    def __init__(self, userid, password):
        self.userid = userid
        self.password = password
        self.shows = []

        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', 'Lynx/2.8.1pre.9 libwww-FM/2.14')
        ]

    def send_req(self, url, data = None):
        try:
            response = self.opener.open(url, data)
            return ''.join(response.readlines())
        except:
            return None

    def login(self):
        login_data = urllib.urlencode({
            'username' : self.userid,
            'password' : self.password,
            'action' : "Login",
            })
        login_url = "%s/%s" % (MYEPISODE_URL, "login.php")
        data = self.send_req(login_url, login_data)
        # Quickly check if it seems we are logged on.
        if (data is None) or (self.userid not in data):
            return False

        return True

    def get_show_list(self):
        # Populate shows with the list of show_ids in our account
        wasted_url = "%s/%s" % (MYEPISODE_URL, "life_wasted.php")
        data = self.send_req(wasted_url)
        if data is None:
            return False
        soup = BeautifulSoup(data)
        mylist = soup.find("table", {"class": "mylist"})
        mylist_tr = mylist.findAll("tr")[1:-1]
        for row in mylist_tr:
            link = row.find('a', {'href': True}).get('href')
            showid = urlparse.parse_qs(link)['showid'][0]
            self.shows.append(int(showid))
        return True

    def find_show_link(self, data, show_name, strict=False):
        if data is None:
            return None
        soup = BeautifulSoup(data)
        show_href = None
        show_name = show_name.lower()
        for link in soup.findAll("a", href=True):
            if link.string is None:
                continue
            if strict:
                if link.string.lower() == show_name:
                    show_href = link.get('href')
                    break
            else:
                if link.string.lower().startswith(show_name):
                    show_href = link.get('href')
                    break
        return show_href

    def find_show_id(self, show_name):
        # find a show through its name and report its id
        search_data = urllib.urlencode({
            'tvshow' : show_name,
            'action' : 'Search myepisodes.com',
            })
        search_url = "%s/%s" % (MYEPISODE_URL, "search.php")
        data = self.send_req(search_url, search_data)
        show_href = self.find_show_link(data, show_name)

        if show_href is None:
            # Try to lookup the list of all the shows to find the exact title
            list_url = "%s/%s?list=%s" % (MYEPISODE_URL, "shows.php",
                    show_name[0].upper())
            data = self.send_req(list_url)
            show_href = self.find_show_link(data, show_name, strict=True)

        # Really did not find anything :'(
        if show_href is None:
            return None

        show_url = urlparse.urlparse(show_href)
        params = urlparse.parse_qs(show_url.query)
        if 'showid' not in params:
            return None
        return int(params['showid'][0].strip())

    # This is totally stolen from script.xbmc.subtitles plugin !
    def get_info(self, file_name):
        title = None
        episode = None
        season = None
        for regex in REGEX_EXPRESSIONS:
            response_file = re.findall(regex, file_name)
            if len(response_file) > 0 :
                season = response_file[0][0]
                episode = response_file[0][1]
            else:
                continue
            title = re.split(regex, file_name)[0]
            for char in ['[', ']', '_', '(', ')', '.', '-']:
                title = title.replace(char, ' ')
            title = title.strip()
            return title, season, episode
        return None, None, None

    def add_show(self, show_id):
        # Try to add the show to your account.
        url = "%s/views.php?type=manageshow&mode=add&showid=%d" % (
                MYEPISODE_URL, show_id)
        data = self.send_req(url)
        if data is None:
            return False
        return True

    def set_episode_watched(self, show_id, season, episode):
        pre_url = "%s/myshows.php?action=Update" % MYEPISODE_URL
        seen_url = "%s&showid=%d&season=%02d&episode=%02d&seen=1" % (pre_url,
                show_id, int(season), int(episode))
        data = self.send_req(seen_url)
        if data is None:
            return False
        return True

