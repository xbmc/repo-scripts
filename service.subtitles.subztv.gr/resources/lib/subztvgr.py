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


import urllib,urlparse,re,os

from lamlib import cache
from lamlib import cleantitle
from lamlib import client
from lamlib import control


class subztvgr:
    def __init__(self):
        self.list = []


    def get(self, query):
        try:
            match = re.findall('(.+?) \((\d{4})\)$', query)

            if len(match) > 0:

                title, year = match[0][0], match[0][1]

                query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(title))).split())

                url = 'http://subztv.gr/search?q=%s' % urllib.quote_plus(query)

                result = client.request(url)
                result = re.sub(r'[^\x00-\x7F]+', ' ', result)

                url = client.parseDOM(result, 'div', attrs = {'id': 'movies'})[0]
                url = re.findall('(/movies/\d+)', url)
                url = [x for y,x in enumerate(url) if x not in url[:y]]
                url = [urlparse.urljoin('http://subztv.gr', i) for i in url]
                url = url[:3]

                for i in url:
                    c = cache.get(self.cache, 2200, i)

                    if not c == None:
                        if cleantitle.get(c[0]) == cleantitle.get(title) and c[1] == year:
                            try: item = self.r
                            except: item = client.request(i)
                            break


            else:

                title, season, episode = re.findall('(.+?) S(\d+)E(\d+)$', query)[0]

                season, episode = '%01d' % int(season), '%01d' % int(episode)

                query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(title))).split())

                url = 'http://subztv.gr/search?q=%s' % urllib.quote_plus(query)

                result = client.request(url)
                result = re.sub(r'[^\x00-\x7F]+', ' ', result)

                url = client.parseDOM(result, 'div', attrs = {'id': 'series'})[0]
                url = re.findall('(/series/\d+)', url)
                url = [x for y,x in enumerate(url) if x not in url[:y]]
                url = [urlparse.urljoin('http://subztv.gr', i) for i in url]
                url = url[:3]

                for i in url:
                    c = cache.get(self.cache, 2200, i)

                    if not c == None:
                        if cleantitle.get(c[0]) == cleantitle.get(title):
                            item = i ; break

                item = '%s/seasons/%s/episodes/%s' % (item, season, episode)
                item = client.request(item)


            item = re.sub(r'[^\x00-\x7F]+', ' ', item)
            items = client.parseDOM(item, 'tr', attrs = {'data-id': '\d+'})
        except:
            return

        for item in items:
            try:
                if not 'img/el.png' in item: raise Exception()

                name = client.parseDOM(item, 'td', attrs = {'class': '.+?'})[-1]
                name = name.split('>')[-1].strip()
                name = re.sub('\s\s+', ' ', name)
                name = client.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = re.findall('\'(http(?:s|)\://.+?)\'', item)[-1]
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'source': 'subztvgr', 'rating': 5})
            except:
                pass

        return self.list


    def cache(self, i):
        try:
            self.r = client.request(i)
            self.r = re.sub(r'[^\x00-\x7F]+', ' ', self.r)
            t = re.findall('(?:\"|\')original_title(?:\"|\')\s*:\s*(?:\"|\')(.+?)(?:\"|\')', self.r)[0]
            y = re.findall('(?:\"|\')year(?:\"|\')\s*:\s*(?:\"|\'|)(\d{4})', self.r)[0]
            return (t, y)
        except:
            pass


    def download(self, path, url):
        try:
            result = client.request(url)

            f = os.path.splitext(urlparse.urlparse(url).path)[1][1:]
            f = os.path.join(path, 'file.%s' % f)

            with open(f, 'wb') as subFile:
                subFile.write(result)
            subFile.close()

            dirs, files = control.listDir(path)

            if len(files) == 0: return

            control.execute('Extract("%s","%s")' % (f, path))

            for i in range(0, 10):
                try:
                    dirs, files = control.listDir(path)
                    if len(files) > 1: break
                    control.sleep(1000)
                except:
                    pass

            control.deleteFile(f)

            subtitle = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])][0]

            subtitle = os.path.join(path, subtitle.decode('utf-8'))

            return subtitle
        except:
            pass


