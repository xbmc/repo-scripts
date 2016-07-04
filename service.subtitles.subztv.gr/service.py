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
import urllib,urlparse,re,os

from resources.lib import subztvgr
from lamlib import control
from lamlib import workers


class search:
    def __init__(self):
        self.list = []

    def run(self, query=None):

        if not 'Greek' in str(langs).split(','):
            control.directory(int(sys.argv[1]))
            control.infoDialog(control.lang(32002).encode('utf-8'))
            return


        if query == None:
            title = control.infoLabel('VideoPlayer.Title')

            if not re.search(r'[^\x00-\x7F]+', title) == None:
                title = control.infoLabel('VideoPlayer.OriginalTitle')

            year = control.infoLabel('VideoPlayer.Year')

            tvshowtitle = control.infoLabel('VideoPlayer.TVshowtitle')

            season = control.infoLabel('VideoPlayer.Season')

            episode = control.infoLabel('VideoPlayer.Episode')

            if 's' in episode.lower():
                season, episode = '0', episode[-1:]

            if not tvshowtitle == '': # episode
                query = '%s S%02dE%02d' % (tvshowtitle, int(season), int(episode))
            elif not year == '': # movie
                query = '%s (%s)' % (title, year)
            else: # file
                query, year = xbmc.getCleanMovieTitle(title)
                if not year == '': query = '%s (%s)' % (query, year)

        self.query = query


        threads = []

        threads.append(workers.Thread(self.subztvgr))

        [i.start() for i in threads]

        for i in range(0, 10 * 2):
            try:
                is_alive = [x.is_alive() for x in threads]
                if all(x == False for x in is_alive): break
                if xbmc.abortRequested == True: break
                control.sleep(500)
            except:
                pass


        if len(self.list) == 0:
            control.directory(int(sys.argv[1]))
            return


        for i in self.list:
            try:
                name, url, source, rating = i['name'], i['url'], i['source'], i['rating']

                u = {'action': 'download', 'url': url, 'source': source}
                u = '%s?%s' % (sys.argv[0], urllib.urlencode(u))

                item = control.item(label='Greek', label2=name, iconImage=str(rating), thumbnailImage='el')
                item.setProperty('sync',  'false')
                item.setProperty('hearing_imp', 'false')

                control.addItem(handle=int(sys.argv[1]), url=u, listitem=item, isFolder=False)
            except:
                pass

        control.directory(int(sys.argv[1]))


    def subztvgr(self):
        self.list.extend(subztvgr.subztvgr().get(self.query))


class download:
    def run(self, url, source):

        path = os.path.join(control.dataPath, 'temp')
        path = path.decode('utf-8')

        control.deleteDir(os.path.join(path, ''), force=True)

        control.makeFile(control.dataPath)

        control.makeFile(path)

        subtitle = subztvgr.subztvgr().download(path, url)

        if not subtitle == None:
            item = control.item(label=subtitle)
            control.addItem(handle=int(sys.argv[1]), url=subtitle, listitem=item, isFolder=False)

        control.directory(int(sys.argv[1]))



params = dict(urlparse.parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')

source = params.get('source')

url = params.get('url')

query = params.get('searchstring')

langs = params.get('languages')



if action == None or action == 'search':
    search().run()

elif action == 'manualsearch':
    search().run(query)

elif action == 'download':
    download().run(url, source)


