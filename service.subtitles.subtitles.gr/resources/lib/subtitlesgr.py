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


import xbmc
import urllib,urllib2,urlparse,zipfile,StringIO,re,os

from lamlib import client
from lamlib import control


class subtitlesgr:
    def __init__(self):
        self.list = []


    def get(self, query):
        try:
            filter = ['freeprojectx', 'subs4series', 'Εργαστήρι Υποτίτλων'.decode('iso-8859-7')]

            query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(query))).split())


            url = 'http://www.subtitles.gr/search.php?name=%s&sort=downloads+desc' % urllib.quote_plus(query)

            result = client.request(url)
            result = result.decode('iso-8859-7').encode('utf-8')

            items = client.parseDOM(result, 'tr', attrs = {'on.+?': '.+?'})
        except:
            return

        for item in items:
            try:
                if not 'flags/el.gif' in item: raise Exception()

                try: uploader = client.parseDOM(item, 'a', attrs = {'class': 'link_from'})[0].strip()
                except: uploader = 'other'

                if uploader in filter: raise Exception()

                if uploader == '': uploader = 'other'

                try: downloads = client.parseDOM(item, 'td', attrs = {'class': 'latest_downloads'})[0]
                except: downloads = '0'
                downloads = re.sub('[^0-9]', '', downloads)

                name = client.parseDOM(item, 'a', attrs = {'onclick': 'runme.+?'})[0]
                name = ' '.join(re.sub('<.+?>', '', name).split())
                name = '[%s] %s [%s DLs]' % (uploader, name, downloads)
                name = client.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = client.parseDOM(item, 'a', ret='href', attrs = {'onclick': 'runme.+?'})[0]
                url = url.split('"')[0].split('\'')[0].split(' ')[0]
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                rating = self._rating(downloads)

                self.list.append({'name': name, 'url': url, 'source': 'subtitlesgr', 'rating': rating})
            except:
                pass

        return self.list


    def _rating(self, downloads):
        try: rating = int(downloads)
        except: rating = 0

        if (rating < 100):
            rating = 1
        elif (rating >= 100 and rating < 200):
            rating = 2
        elif (rating >= 200 and rating < 300):
            rating = 3
        elif (rating >= 300 and rating < 400):
            rating = 4
        elif (rating >= 400):
            rating = 5

        return rating


    def download(self, path, url):
        try:
            url = re.findall('/(\d+)/', url + '/', re.I)[-1]
            url = 'http://www.findsubtitles.eu/getp.php?id=%s' % url
            url = client.request(url, output='geturl')

            data = urllib2.urlopen(url, timeout=10).read()
            zip = zipfile.ZipFile(StringIO.StringIO(data))
            files = zip.namelist()
            files = [i for i in files if i.startswith('subs/')]
            srt = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])]
            rar = [i for i in files if any(i.endswith(x) for x in ['.rar', '.zip'])]


            if len(srt) > 0:
                result = zip.open(srt[0]).read()

                subtitle = os.path.basename(srt[0])

                subtitle = os.path.join(path, subtitle.decode('utf-8'))

                with open(subtitle, 'wb') as subFile:
                    subFile.write(result)

                return subtitle


            elif len(rar) > 0:
                result = zip.open(rar[0]).read()

                f = os.path.splitext(urlparse.urlparse(rar[0]).path)[1][1:]
                f = os.path.join(path, 'file.%s' % f)

                with open(f, 'wb') as subFile:
                    subFile.write(result)

                dirs, files = control.listDir(path)

                if len(files) == 0: return

                control.execute('Extract("%s","%s")' % (f, path))

                for i in range(0, 10):
                    try:
                        dirs, files = control.listDir(path)
                        if len(files) > 1: break
                        if xbmc.abortRequested == True: break
                        control.sleep(1000)
                    except:
                        pass

                control.deleteFile(f)

                subtitle = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])][0]

                subtitle = os.path.join(path, subtitle.decode('utf-8'))

                return subtitle

        except:
            pass


