# -*- coding: utf-8 -*-

import re
import requests
from bs4 import BeautifulSoup

# This is totally stolen from script.xbmc.subtitles plugin !
REGEX_EXPRESSIONS = [
    r'[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
    r'[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                # foo.1x09
    r'[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',     # foo.109
    r'([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
    r'[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
    r'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',         # Season 01 - Episode 02
    r'Season ([0-9]+) Episode ([0-9]+)[^\\/]*',           # Season 01 Episode 02
    r'[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
    r'[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',           #foo_[s01]_[e01]
    r'[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',  #foo, s01e01, foo.s01.e01, foo.s01-e01
    r's([0-9]+)ep([0-9]+)[^\\/]*',                        #foo - s01ep03, foo - s1ep03
    r'[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
    r'[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
    ]

MYEPISODE_URL = "https://www.myepisodes.com"
MAX_LOGIN_ATTEMPTS = 3

def sanitize(title, replace):
    for char in ['[', ']', '_', '(', ')', '.', '-']:
        title = title.replace(char, replace)
    return title

def logged(func):
    def wrapper(*args, **kwargs):
        mye = args[0]
        if not mye.is_logged:
            mye.login()
        return func(*args, **kwargs)
    return wrapper

class MyEpisodes(object):

    def __init__(self, userid, password):
        self.userid = userid.encode('utf-8', 'replace')
        self.password = password
        self.req = requests.Session()
        self.title_is_filename = False
        self.is_logged = False
        self.shows = {}

    def __del__(self):
        self.req.close()

    def __repr__(self):
        return "MyEpisodes('%s', '%s')" % (self.userid, self.password)

    def login(self):
        login_attempts = MAX_LOGIN_ATTEMPTS
        login_data = {
            'username' : self.userid,
            'password' : self.password,
            'action' : "Login",
            'u': ""
        }

        while login_attempts > 0 and not self.is_logged:
            data = self.req.post("%s/login/" % MYEPISODE_URL, data=login_data)
            # Quickly check if it seems we are logged on.
            if self.userid.lower() in data.content.lower():
                self.is_logged = True
                return
            login_attempts -= 1

    @logged
    def populate_shows(self):
        self.shows.clear()

        # Populate shows with the list of show_ids in our account
        data = self.req.get("%s/myshows/list/" % MYEPISODE_URL)
        if data is None:
            return False
        soup = BeautifulSoup(data.content, 'html.parser')
        mylist = soup.find("table", {"class": "mylist"})
        mylist_tr = mylist.findAll("tr")[1:]

        for row in mylist_tr:
            # Avoid shows marked as ignored
            ignore_checkbox = row.find('input', {'type':'checkbox'})
            if ignore_checkbox.get('checked') is not None:
                continue

            link = row.find('a', {'href': True})
            link_url = link.get('href')
            showid = int(link_url.split('/')[2])

            show_name = link.text.strip()
            sanitized_show_name = sanitize(show_name, '')
            if sanitized_show_name != show_name:
                self.shows[sanitized_show_name.lower()] = showid

            self.shows[show_name.lower()] = showid

        return True

    def find_show_link(self, data, show_name, strict=False):
        if data is None:
            return None

        soup = BeautifulSoup(data, 'html.parser')
        show_href = None
        show_name = show_name.lower()

        for link in soup.findAll("a", href=True):
            if link.string is None:
                continue

            link_text = link.string.lower()
            if self.title_is_filename:
                link_text = sanitize(link_text, ' ')

            if strict:
                if link_text != show_name:
                    continue
                show_href = link.get('href')
                break

            if link_text.startswith(show_name):
                show_href = link.get('href')
                break

        return show_href

    @logged
    def find_show_id(self, show_name):
        # Try to find the ID of the show in our account first
        name = show_name.lower()

        self.populate_shows()

        match_show = {k:v for k, v in self.shows.items() if name in k or name.startswith(k)}

        if len(match_show) == 1:
            return list(match_show.values())[0]

        # We loop through a the dict of match possibilities and we search
        # strictly for the show name.
        for key, value in match_show.items():
            if key == name:
                return value

        # You should really never fall there, at this point, the show should be
        # in your account, except if you disabled the auto add feature.

        # It's not in our account yet ?
        # Try Find a show through its name and report its id
        search_data = {
            'tvshow' : name,
            'action' : 'Search',
            }
        data = self.req.post("%s/search/" % MYEPISODE_URL, data=search_data)

        show_href = self.find_show_link(data.content, name)
        if show_href is None:
            # Try to lookup the list of all the shows to find the exact title
            data = self.req.post("%s/shows.php" % MYEPISODE_URL,
                                 params={"list": name[0].upper()})
            show_href = self.find_show_link(data.content, name, strict=True)

        # Really did not find anything :'(
        if show_href is None:
            return None

        try:
            show_id = int(show_href.split('/')[2])
        except IndexError:
            return None

        if show_id is None:
            return None

        return show_id

    # This is totally stolen from script.xbmc.subtitles plugin !
    def get_info(self, file_name):
        title = None
        episode = None
        season = None
        self.title_is_filename = False

        for regex in REGEX_EXPRESSIONS:
            response_file = re.findall(regex, file_name)
            if response_file:
                season = response_file[0][0]
                episode = response_file[0][1]
            else:
                continue
            title = re.split(regex, file_name)[0]
            title = sanitize(title, ' ')
            title = title.strip()
            self.title_is_filename = True
            return title.title(), season, episode

        return None, None, None

    def add_show(self, show_id):
        return self._add_del_show(show_id)

    def del_show(self, show_id):
        return self._add_del_show(show_id, mode="del")

    @logged
    def _add_del_show(self, show_id, mode="add"):
        add_del_data = {
            "action": mode,
            "showid": show_id
        }
        data = self.req.post("%s/ajax/service.php" % MYEPISODE_URL,
                             params={"mode": "show_manage"}, data=add_del_data)
        if data is None:
            return False

        # Update list
        self.populate_shows()

        return True

    def set_episode_watched(self, show_id, season, episode):
        return self._set_episode_un_watched(show_id, season, episode)

    def set_episode_unwatched(self, show_id, season, episode):
        return self._set_episode_un_watched(show_id,
                                            season,
                                            episode,
                                            watched=False)

    @logged
    def _set_episode_un_watched(self, show_id, season, episode, watched=True):
        key = "V%d-%d-%d" % (int(show_id), int(season), int(episode))
        # If you are wondering why the lower and conversion to str, it's
        # because the backend of MyEpisodes is so smart that it doesn't
        # understand "True" but only "true"...
        un_watched_data = {key: str(watched).lower()}
        data = self.req.post("%s/ajax/service.php" % MYEPISODE_URL,
                             params={"mode": "eps_update"}, data=un_watched_data)
        if data.status_code != 200:
            return False
        return True
