# -*- coding: utf-8 -*-

'''
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
'''


import urllib,re,os

from lamlib import cache
from lamlib import cleantitle
from lamlib import client
from lamlib import control


class xsubstv:
    def __init__(self):
        self.list = []
        self.user = control.setting('xsubstv.user')
        self.password = control.setting('xsubstv.pass')


    def get(self, query):
        try:
            title, season, episode = re.findall('(.+?) S(\d+)E(\d+)$', query)[0]

            season, episode = '%01d' % int(season), '%02d' % int(episode)

            title = re.sub('^THE\s+|^A\s+', '', title.strip().upper())
            title = cleantitle.get(title)

            url = 'http://www.xsubs.tv/series/all.xml'

            srsid = cache.get(self.cache, 48, url)
            srsid = [i[0] for i in srsid if title == i[1]][0]

            url = 'http://www.xsubs.tv/series/%s/main.xml' % srsid

            result = client.request(url)
            ssnid = client.parseDOM(result, 'series_group', ret='ssnid', attrs = {'ssnnum': season})[0]

            url = 'http://www.xsubs.tv/series/%s/%s.xml' % (srsid, ssnid)

            result = client.request(url)

            items = client.parseDOM(result, 'subg')
            items = [(client.parseDOM(i, 'etitle', ret='number'), i) for i in items]
            items = [i[1] for i in items if len(i[0]) > 0 and i[0][0] == episode][0]
            items = re.findall('(<sr .+?</sr>)', items)
        except:
            return

        for item in items:
            try:
                p = client.parseDOM(item, 'sr', ret='published_on')[0]
                if p == '': raise Exception()

                name = client.parseDOM(item, 'sr')[0]
                name = name.rsplit('<hits>', 1)[0]
                name = re.sub('</.+?><.+?>|<.+?>', ' ', name).strip()
                name = '%s %s' % (query, name)
                name = client.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = client.parseDOM(item, 'sr', ret='rlsid')[0]
                url = 'http://www.xsubs.tv/xthru/getsub/%s' % url
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'source': 'xsubstv', 'rating': 5})
            except:
                pass

        return self.list


    def cache(self, url):
        try:
            result = client.request(url)
            result = re.sub(r'[^\x00-\x7F]+', ' ', result)

            result = zip(client.parseDOM(result, 'series', ret='srsid'), client.parseDOM(result, 'series'))
            result = [(i[0], cleantitle.get(i[1])) for i in result]

            return result
        except:
            pass


    def cookie(self):
        try:
            login = 'http://www.xsubs.tv/xforum/account/signin/'

            token = client.request(login)
            token = client.parseDOM(token, 'input', ret='value', attrs = {'name': 'csrfmiddlewaretoken'})[0]

            headers = {'Cookie': 'csrftoken=%s' % token}

            post = {'username': self.user, 'password': self.password, 'csrfmiddlewaretoken': token, 'next': ''}
            post = urllib.urlencode(post)

            c = client.request(login, post=post, headers=headers, output='cookie')
            return c
        except:
            pass


    def download(self, path, url):
        try:
            cookie = None

            anonymous = (self.user == '' or self.password == '')

            code, result = client.request(url, output='response', error=True)

            if code == '429' and anonymous == True:
                control.dialog.ok(str('xsubs.tv'), str(result), str(''))
                return
            elif anonymous == False:
                cookie = cache.get(self.cookie, 6)

            result, headers, content, cookie = client.request(url, cookie=cookie, output='extended')

            subtitle = content['Content-Disposition']
            subtitle = re.findall('"(.+?)"', subtitle)[0]

            try: subtitle = os.path.join(path, subtitle)
            except: subtitle = os.path.join(str(path), subtitle)

            if not subtitle.endswith('.srt'): raise Exception()

            file = open(subtitle, 'wb') ; file.write(result) ; file.close()

            return subtitle
        except:
            pass


