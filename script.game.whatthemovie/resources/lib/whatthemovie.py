#
#     Copyright (C) 2011 Team WTM4XBMC
#     http://github.com/wtm4xbmc
#
# This Program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This Program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this script; see the file LICENSE.txt.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# http://www.gnu.org/copyleft/gpl.html
#
#

import re
import urllib
import urllib2
import cookielib
import threading
import Queue
from BeautifulSoup import BeautifulSoup


class WhatTheMovie(object):

    MAIN_URL = 'http://whatthemovie.com'

    OFFLINE_DEBUG = False
    OFFLINE_SHOT = {'shot_id': u'156827',
                    'requested_as': 'random',
                    'self_posted': False,
                    'bookmarked': False,
                    'favourite': False,
                    'gives_point': {'ff': False,
                                    'all': False},
                    'already_solved': False,
                    'tags': [u'tag1'],
                    'posted_by': u'Hagentinho',
                    'sotd': False,
                    'lang_list': {'hidden': [u'dk', u'et', u'fi', u'gr'],
                                  'main': [u'de', u'fr', u'en', u'es', u'pt'],
                                  'all': [u'dk', u'et', u'fi', u'gr',
                                          u'de', u'fr', u'en', u'es', u'pt']},
                    'solved': {'status': True,
                               'count': 1280,
                               'first_by': u'Mimimi'},
                    'image_url': (u'http://static.whatthemovie.com/'
                                  u'system/images/stills/normal/73/'
                                  u'7e4a854279aaf150d0fe0841f459c4.jpg'),
                    'shot_type': 2,
                    'date': (2011, 5, 14),
                    'nav': {'last': u'160987', 'prev_unsolved': u'157009',
                            'next': u'156819', 'next_unsolved': u'156819',
                            'prev': u'157009', 'first': u'1'},
                    'voting': {'votes': u'93',
                               'own_rating': None,
                               'overall_rating': u'7.90'},
                    'solvable': False,
                    'redirected': False}
    OFFLINE_ANSWER = {'title': 'Fluch der Karibik',
                      'is_right': True,
                      'title_year': (u'Pirates of the Caribbean: '
                                     u'At World\'s End (2007)')}

    def __init__(self, user_agent):
        # Get browser stuff
        self.cookies = cookielib.LWPCookieJar()
        processor = urllib2.HTTPCookieProcessor(self.cookies)
        self.opener = urllib2.build_opener(processor)
        self.opener.addheaders = [('user-agent', user_agent)]
        # Set empty returns
        self.shot = dict()
        self.last_shots = list()
        self.image_download_path = None
        self.running = False

    def login(self, user, password, cookie_path):
        logged_in = False
        if self.OFFLINE_DEBUG:
            return 'auth'
        try:
            self.cookies.revert(cookie_path)
            cookie_found = True
        except IOError:
            cookie_found = False
        if cookie_found:
            logged_in_user = self._getUsername()
            if logged_in_user == user:
                logged_in = 'cookie'
        if not logged_in:
            login_url = '%s/user/login' % self.MAIN_URL
            data_dict = dict()
            data_dict['name'] = user
            data_dict['upassword'] = password
            data = urllib.urlencode(data_dict)
            html = self.opener.open(login_url, data).read()
            logged_in_user = self._getUsername()
            if logged_in_user:
                logged_in = 'auth'
                self.cookies.save(cookie_path)
        return logged_in

    def setImagePath(self, image_download_path):
        self.image_download_path = image_download_path

    def start(self, num_workers=3, num_init_jobs=3, callback=None):
        self.callback = callback
        self.num_workers = num_workers
        self.num_init_jobs = num_init_jobs
        self.workers = [self.Scraper(self.opener, self.image_download_path,
                        self.callback) for i in range(self.num_workers)]
        for worker in self.workers:
            worker.start()
        for job in range(self.num_init_jobs):
            self.Scraper.jobs.put('random')
        self.running = True

    def stop(self):
        self.Scraper.exit_requested = True
        for i in range(self.num_workers):
            self.Scraper.jobs.put('exit')
        for worker in self.workers:
            worker.join()
        self.running = False

    def _getUsername(self, html=None):
        # only retrieve if there is no previous retrieve which we can use
        if not html:
            html = self.opener.open(self.MAIN_URL).read()
        tree = BeautifulSoup(html)
        section = tree.find('li', attrs={'class': 'secondary_nav',
                                         'style': 'margin-left: 0'})
        if section:
            username = section.a.span.string
        else:
            username = None
        return username

    def setRandomOptions(self, settings):
        if self.OFFLINE_DEBUG:
            return
        option_url = '%s/shot/setrandomoptions' % self.MAIN_URL
        self._sendAjaxReq(option_url, settings)

    def _sendAjaxReq(self, url, data_dict=None):
        if data_dict:
            post_data = urllib.urlencode(data_dict)
        else:
            post_data = ' '
        req = urllib2.Request(url, post_data)
        req.add_header('Accept', 'text/javascript, */*')
        req.add_header('Content-Type',
                       'application/x-www-form-urlencoded; charset=UTF-8')
        req.add_header('X-Requested-With', 'XMLHttpRequest')
        response = self.opener.open(req).read()
        response_c = response.replace('&amp;', '&').decode('unicode-escape')
        return response_c

    def getShot(self, shot_request):
        if not self.running:
            self.start()
        if self.OFFLINE_DEBUG:
            return self.OFFLINE_SHOT

        # We dont have to get a new shot
        if shot_request == 'back':
            if self.last_shots:
                self.Scraper.next_shots_lock.acquire()
                self.Scraper.next_shots.insert(0, self.shot)
                if self.callback:
                    self.callback(len(self.Scraper.next_shots))
                self.Scraper.next_shots_lock.release()
                self.shot = self.last_shots.pop()

        # We need to get a new shot (from preload or a fresh one)
        else:
            # if there is already a shot - put it in list of last_shots
            if self.shot:  
                self.last_shots.append(self.shot)

            # We need a new shot via 'random'
            if shot_request == 'random':
                # Check if there aren't enough 'random' shots in the preloads
                num_random_preloads = len([s for s in self.Scraper.next_shots \
                                           if s['requested_as'] == 'random'])
                if num_random_preloads - 1 < self.num_init_jobs:
                    self.Scraper.jobs.put(shot_request)

            # We need a new shot via shot_id
            elif shot_request.isdigit():
                self.Scraper.jobs.put(shot_request)

            # We need a new shot via navi_key
            elif self.shot and shot_request in self.shot['nav'].keys():
                if not self.shot['nav'][shot_request]:
                    # check if it is a unsolved request and try without
                    if (shot_request[-9:] == '_unsolved'
                        and self.shot['nav'][shot_request[:-9]]):
                        request = shot_request[:-9]
                        shot_request = self.shot['nav'][request]
                else:
                    shot_request = self.shot['nav'][shot_request]
                self.Scraper.jobs.put(shot_request)


            # delete actual shot because we want a new one
            self.shot = None
            self.Scraper.new_shot_condition.acquire()
            # as long as we dont have a shot which we want (ex. 'random')
            while not self.shot:
                # lock the list of preloaded shots
                self.Scraper.next_shots_lock.acquire()
                # search in already preloaded shots for one we want
                for i, shot in enumerate(self.Scraper.next_shots):
                    # if this is a shot we want
                    if shot['requested_as'] == shot_request:
                        # save the shot we want and delete from list
                        self.shot = self.Scraper.next_shots.pop(i)
                        if self.callback:
                            self.callback(len(self.Scraper.next_shots))
                        # stop searching in the list of preloaded shots
                        break
                # relase the lock - new shots can now be inserted from workers
                self.Scraper.next_shots_lock.release()
                # if our search was successfull leave the waiting state
                if self.shot:
                    break
                # there was no shot we want - wait for a new
                self.Scraper.new_shot_condition.wait()
            self.Scraper.new_shot_condition.release()
        return self.shot

    def guessShot(self, shot_id, title_guess):
        if self.OFFLINE_DEBUG:
            if title_guess.lower() == self.OFFLINE_ANSWER['title'].lower():
                return self.OFFLINE_ANSWER
            else:
                return {'is_right': False}
        answer = dict()
        answer['is_right'] = False
        post_url = '%s/shot/%s/guess' % (self.MAIN_URL, shot_id)
        post_dict = {'guess': title_guess.encode('utf8').replace(',', '')}
        response_c = self._sendAjaxReq(post_url, post_dict)
        # ['right'|'wrong']
        if response_c[6:11] == 'right':
            answer['is_right'] = True
            answer['title_year'] = response_c.split('"')[3]
            if self.shot['shot_id'] == shot_id:
                if not self.shot['already_solved']:
                    self.shot['already_solved'] = True
                self.shot['gives_point'] = {'ff': False,
                                            'all': False}
        return answer

    def rateShot(self, shot_id, user_rate, rerated='false'):
        if self.OFFLINE_DEBUG:
            self.OFFLINE_SHOT['voting']['own_rating'] = str(user_rate)
            return
        url = '%s/shot/%s/rate.js' % (self.MAIN_URL, shot_id)
        user_rate_5 = float(user_rate) / 2
        rating_dict = dict()
        rating_dict['identity'] = 'shot_rating_stars_%s' % shot_id
        rating_dict['rated'] = user_rate_5
        rating_dict['rerated'] = rerated
        self._sendAjaxReq(url, rating_dict)
        if self.shot['shot_id'] == shot_id:
            self.shot['voting']['own_rating'] = str(user_rate)

    def bookmarkShot(self, shot_id, new_state):
        if self.OFFLINE_DEBUG:
            self.OFFLINE_SHOT['bookmarked'] = new_state
            return
        if new_state == True:
            url = '%s/shot/%s/watch' % (self.MAIN_URL, shot_id)
        else:
            url = '%s/shot/%s/unwatch' % (self.MAIN_URL, shot_id)
        self._sendAjaxReq(url)
        if self.shot['shot_id'] == shot_id:
            self.shot['bookmarked'] = new_state

    def favouriteShot(self, shot_id, new_state):
        if self.OFFLINE_DEBUG:
            self.OFFLINE_SHOT['favourite'] = new_state
            return
        if new_state == True:
            url = '%s/shot/%s/fav' % (self.MAIN_URL, shot_id)
        else:
            url = '%s/shot/%s/unfav' % (self.MAIN_URL, shot_id)
        self._sendAjaxReq(url)
        if self.shot['shot_id'] == shot_id:
            self.shot['favourite'] = new_state

    def solveShot(self, shot_id):
        if self.OFFLINE_DEBUG:
            return self.OFFLINE_ANSWER['title']
        url = '%s/shot/%s/showsolution' % (self.MAIN_URL, shot_id)
        ajax_answer = self._sendAjaxReq(url)
        r = '<strong>(?P<solution>.+)\.\.\.</strong>'
        solved_title = re.search(r, ajax_answer).group('solution')
        if self.shot['shot_id'] == shot_id:
            self.shot['already_solved'] = True
        return solved_title

    def getScore(self, username):
        score = {'ff_score': 0,
                 'all_score': 0}
        if self.OFFLINE_DEBUG:
            return score
        profile_url = '%s/user/%s/' % (self.MAIN_URL, username)
        html = self.opener.open(profile_url).read()
        tree = BeautifulSoup(html)
        box = tree.find('div', attrs={'class': 'box_white'})
        r = ('>(?P<ff_score>[0-9]+) Feature Film.*'
             '>(?P<all_score>[0-9]+) Snapshot')
        if re.search(r, str(box.p)):
            score_dict = re.search(r, str(box.p)).groupdict()
            score = {'ff_score': int(score_dict['ff_score']),
                     'all_score': int(score_dict['all_score'])}
        return score

    class Scraper(threading.Thread):

        jobs = Queue.Queue()
        next_shots = list()
        next_shots_lock = threading.Lock()
        new_shot_condition = threading.Condition()
        exit_requested = False

        def __init__(self, opener, image_download_path, callback=None):
            self.opener = opener
            self.callback = callback
            self.image_download_path = image_download_path
            threading.Thread.__init__(self)

        def run(self):
            while not self.exit_requested:
                job = WhatTheMovie.Scraper.jobs.get()
                if job == 'exit':
                    break
                # scrape the shot - this will take some time
                is_new = False
                while not is_new:
                    shot = self.scrapeShot(job)
                    WhatTheMovie.Scraper.next_shots_lock.acquire()
                    if shot['shot_id'] in [s['shot_id'] for s in WhatTheMovie.Scraper.next_shots]:
                        pass
                    else:
                        is_new = True
                    WhatTheMovie.Scraper.next_shots_lock.release()
                # lock the list of shots
                WhatTheMovie.Scraper.next_shots_lock.acquire()
                # save the shot
                WhatTheMovie.Scraper.next_shots.append(shot)
                # tell that a new shot was inserted
                WhatTheMovie.Scraper.new_shot_condition.acquire()
                WhatTheMovie.Scraper.new_shot_condition.notify()
                WhatTheMovie.Scraper.new_shot_condition.release()
                if self.callback:
                    self.callback(len(WhatTheMovie.Scraper.next_shots))
                WhatTheMovie.Scraper.next_shots_lock.release()
                WhatTheMovie.Scraper.jobs.task_done()

        def scrapeShot(self, shot_request):
            self.shot = dict()
            shot_url = '%s/shot/%s' % (WhatTheMovie.MAIN_URL, shot_request)
            html = self.opener.open(shot_url).read()
            tree = BeautifulSoup(html)
            # id
            shot_id = tree.find('li', attrs={'class': 'number'}).string.strip()
            # prev/next
            nav = dict()
            section = tree.find('ul', attrs={'id': 'nav_shots'}).findAll('li')
            nav_types = ((0, 'first'), (1, 'prev'), (2, 'prev_unsolved'),
                         (4, 'next_unsolved'), (5, 'next'), (6, 'last'))
            for i, nav_type in nav_types:
                if section[i].a:
                    nav[nav_type] = section[i].a['href'][6:]
                else:
                    nav[nav_type] = None
            # image url
            image_url = tree.find('img',
                                  alt='guess this movie snapshot')['src']
            subst_image_url = 'http://static.whatthemovie.com/images/subst'
            if self.image_download_path:
                if not image_url.startswith(subst_image_url):
                    local_image_file = '%s%s.jpg' % (self.image_download_path,
                                                     shot_id)
                    urllib.urlretrieve(image_url, local_image_file, )
                    image_url = local_image_file
            # languages
            lang_list = dict()
            lang_list['main'] = list()
            lang_list['hidden'] = list()
            section = tree.find('ul', attrs={'class': 'language_flags'})
            langs_main = section.findAll(lambda tag: len(tag.attrs) == 0)
            for lang in langs_main:
                if lang.img:
                    lang_list['main'].append(lang.img['src'][-6:-4])
            langs_hidden = section.findAll('li',
                                           attrs={'class': 'hidden_languages'})
            for lang in langs_hidden:
                if lang.img:
                    lang_list['hidden'].append(lang.img['src'][-6:-4])
            lang_list['all'] = lang_list['main'] + lang_list['hidden']
            # date
            shot_date = None
            section = tree.find('ul', attrs={'class': 'nav_date'})
            if section:
                r = ('<a href="/overview/(?P<year>[0-9]+)/'
                     '(?P<month>[0-9]+)/(?P<day>[0-9]+)">')
                date_match = re.search(r, unicode(section))
                if date_match:
                    date_dict = date_match.groupdict()
                    if date_dict:
                        shot_date = (int(date_dict['year']),
                                     int(date_dict['month']),
                                     int(date_dict['day']))
            # posted by
            sections = tree.find('ul',
                                 attrs={'class': 'nav_shotinfo'}).findAll('li')
            if sections[0].a:
                posted_by = sections[0].a.string
            else:
                posted_by = None
            # solved
            solved = dict()
            try:
                solved_string, solved_count = sections[1].string[8:].split()
                if solved_string == 'solved':
                    solved['status'] = True
                    solved['count'] = int(solved_count.strip('()'))
            except:
                solved['status'] = False
                solved['count'] = 0
            try:
                solved['first_by'] = sections[2].a.string
            except:
                solved['first_by'] = None
            # already solved + own_shot
            already_solved = False
            self_posted = False
            js_list = tree.findAll('script',
                                   attrs={'type': 'text/javascript'},
                                   text=re.compile('guess_problem'))
            if js_list:
                message = str(js_list)
                if re.search('already solved', message):
                    already_solved = True
                elif re.search('You posted this', message):
                    self_posted = True
            # voting
            voting = dict()
            section = tree.find('script',
                                attrs={'type': 'text/javascript'},
                                text=re.compile('tt_shot_rating_stars'))
            r = ('<strong>(?P<overall_rating>[0-9.]+|hidden)</strong> '
                 '\((?P<votes>[0-9]+) votes\)'
                 '(<br>Your rating: <strong>(?P<own_rating>[0-9.]+)</strong)?')
            if section:
                voting = re.search(r, section).groupdict()
            # tags
            tags = list()
            tags_list = tree.find('ul', attrs={'id':
                                               'shot_tag_list'}).findAll('li')
            for tag in tags_list:
                if tag.a:
                    tags.append(tag.a.string)
            # shot_type
            section = tree.find('h2', attrs={'class':
                                             'topbar_title'}).string.strip()
            shot_type = 0  # Unknown
            if section == 'New Submissions':
                shot_type = 1
            elif section == 'Feature Films':
                shot_type = 2
            elif section == 'The Archive':
                shot_type = 3
            elif section == 'Rejected Snapshots':
                shot_type = 4
            elif section == 'The Vault':
                shot_type = 5
            elif section == 'Deleted':
                shot_type = 6
            # gives_point
            gives_point = {'ff': False,
                           'all': False}
            if not already_solved and not self_posted:
                gives_point['all'] = True
                if shot_type == 2:
                    gives_point['ff'] = True
            # bookmarked
            if tree.find('li', attrs={'id': 'watchbutton'}):
                bookmark_link = tree.find('li', attrs={'id': 'watchbutton'}).a
                try:
                    if bookmark_link['class'] == 'active':
                        bookmarked = True
                except KeyError:
                    bookmarked = False
            else:
                bookmarked = None  # Not logged in
            # favourite
            if tree.find('li', attrs={'class': 'love'}):
                favourite_link = tree.find('li', attrs={'class': 'love'}).a
                try:
                    if favourite_link['class'] == 'active':
                        favourite = True
                except KeyError:
                    favourite = False
            else:
                favourite = None  # Not logged in
            # Snapshot of the Day
            sotd = False
            if tree.find('div', attrs={'class': 'sotd_banner'}):
                sotd = True
            # Solvable
            solvable = False
            section = tree.find('li', attrs={'id': 'solutionbutton'})
            if section is not None:
                try:
                    if section.a['class'] == 'inactive':
                        solvable = False
                except KeyError:
                    solvable = True
            # redirected
            redirected = False
            section = tree.find('div', attrs={'class':
                                              re.compile('flash_message')})
            if section:
                message = section.string
                redirected = 1
                if re.search('you are not allowed', message):
                    redirected = 2
                if re.search('No such snapshot', message):
                    redirected = 3
            # create return dict
            self.shot['shot_id'] = shot_id
            self.shot['image_url'] = image_url
            self.shot['lang_list'] = lang_list
            self.shot['posted_by'] = posted_by
            self.shot['solved'] = solved
            self.shot['date'] = shot_date
            self.shot['already_solved'] = already_solved
            self.shot['self_posted'] = self_posted
            self.shot['voting'] = voting
            self.shot['tags'] = tags
            self.shot['shot_type'] = shot_type
            self.shot['gives_point'] = gives_point
            self.shot['nav'] = nav
            self.shot['bookmarked'] = bookmarked
            self.shot['favourite'] = favourite
            self.shot['sotd'] = sotd
            self.shot['solvable'] = solvable
            self.shot['redirected'] = redirected
            self.shot['requested_as'] = shot_request
            return self.shot