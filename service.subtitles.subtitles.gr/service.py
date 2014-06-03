# -*- coding: utf-8 -*-

'''
    Subtitles.gr XBMC Addon
    Copyright (C) 2014 lambda

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

import urllib,urllib2,re,os,threading,zipfile,StringIO,shutil,unicodedata,time
import xbmc,xbmcplugin,xbmcgui,xbmcaddon,xbmcvfs
try:    import CommonFunctions
except: import commonfunctionsdummy as CommonFunctions

common              = CommonFunctions
language            = xbmcaddon.Addon().getLocalizedString
addonName           = xbmcaddon.Addon().getAddonInfo("name")
addonId             = xbmcaddon.Addon().getAddonInfo("id")
dataPath            = xbmc.translatePath('special://profile/addon_data/%s' % (addonId))
tempData            = os.path.join(dataPath,'temp')


class getUrl(object):
    def __init__(self, url, close=True, proxy=None, post=None, mobile=False, referer=None, cookie=None, output='', timeout='10'):
        if not proxy is None:
            proxy_handler = urllib2.ProxyHandler({'http':'%s' % (proxy)})
            opener = urllib2.build_opener(proxy_handler, urllib2.HTTPHandler)
            opener = urllib2.install_opener(opener)
        if output == 'cookie' or not close == True:
            import cookielib
            cookie_handler = urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar())
            opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
            opener = urllib2.install_opener(opener)
        if not post is None:
            request = urllib2.Request(url, post)
        else:
            request = urllib2.Request(url,None)
        if mobile == True:
            request.add_header('User-Agent', 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_0 like Mac OS X; en-us) AppleWebKit/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8A293 Safari/6531.22.7')
        else:
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0')
        if not referer is None:
            request.add_header('Referer', referer)
        if not cookie is None:
            request.add_header('cookie', cookie)
        response = urllib2.urlopen(request, timeout=int(timeout))
        if output == 'cookie':
            result = str(response.headers.get('Set-Cookie'))
        elif output == 'geturl':
            result = response.geturl()
        else:
            result = response.read()
        if close == True:
            response.close()
        self.result = result

class Thread(threading.Thread):
    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self)
    def run(self):
        self._target(*self._args)

class getRating(object):
    def __init__(self, downloads):
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

        self.result = rating

class main:
    def __init__(self):
        params = {}
        splitparams = sys.argv[2][sys.argv[2].find('?') + 1:].split('&')
        for param in splitparams:
            if (len(param) > 0):
                splitparam = param.split('=')
                key = splitparam[0]
                try:    value = splitparam[1].encode("utf-8")
                except: value = splitparam[1]
                params[key] = value

        try:        action = urllib.unquote_plus(params["action"])
        except:     return
        try:        langs = urllib.unquote_plus(params["languages"])
        except:     langs = None
        try:        url = urllib.unquote_plus(params["url"])
        except:     url = None
        try:        source = urllib.unquote_plus(params["source"])
        except:     source = None
        try:        name = urllib.unquote_plus(params["name"])
        except:     name = None
        try:        query = urllib.unquote_plus(params["searchstring"])
        except:     query = None

        if langs is None:
            pass
        elif not 'Greek' in langs.split(","):
            xbmcgui.Dialog().notification(addonName.encode("utf-8"), language(32002).encode("utf-8"), xbmcgui.NOTIFICATION_WARNING, 3000, sound=False)
            return

        if action == 'search':                    actions().search()
        elif action == 'manualsearch':            actions().search(query)
        elif action == 'download':                actions().download(url, source, name)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        return

class actions:
    def search(self, query=None):
        if query == None:
            title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
            if title == '': title = xbmc.getInfoLabel("VideoPlayer.Title")
            year = xbmc.getInfoLabel("VideoPlayer.Year")

            show = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
            season = xbmc.getInfoLabel("VideoPlayer.Season")
            episode = xbmc.getInfoLabel("VideoPlayer.Episode")
            if 's' in episode.lower(): season, episode = '0', episode[-1:]

            if not year == '': # movie
                query = '%s (%s)' % (title, year)
            elif not show == '': # episode
                query = show + ' S' + '%02d' % int(season) + 'E' + '%02d' % int(episode)
            else: # file
                query, year = xbmc.getCleanMovieTitle(title)
                if not year == '': query = '%s (%s)' % (query, year)

        query = unicodedata.normalize('NFKD', unicode(unicode(query, 'utf-8'))).encode('ascii','ignore')
        subtitleList = subtitles().get(query)

        if subtitleList == None:
            xbmcgui.Dialog().notification(addonName.encode("utf-8"), language(32001).encode("utf-8"), xbmcgui.NOTIFICATION_ERROR, 3000, sound=False)
            return

        for i in subtitleList:
            try:
                name, url, source, rating = i['name'], i['url'], i['source'], i['rating']
                u = '%s?action=download&url=%s&source=%s&name=%s' % (sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(source), urllib.quote_plus(name))
                item = xbmcgui.ListItem(label='Greek', label2=name, iconImage=str(rating), thumbnailImage='el')
                item.setProperty("sync",  'false')
                item.setProperty("hearing_imp", 'false')
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)
            except:
                pass

    def download(self, url, source, name):
        subtitle = download().run(url, source, name)
        if subtitle == None: return
        item = xbmcgui.ListItem(label=subtitle)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=subtitle,listitem=item,isFolder=False)

class subtitles:
    def __init__(self):
        self.list = []

    def get(self, query):
        self.query = query

        threads = []
        threads.append(Thread(self.xsubstv))
        threads.append(Thread(self.subztv))
        threads.append(Thread(self.subtitlesgr))
        [i.start() for i in threads]
        [i.join() for i in threads]

        filter = []
        filter += [i for i in self.list if i['source'] == 'xsubstv']
        filter += [i for i in self.list if i['source'] == 'subztv']
        filter += [i for i in self.list if i['source'] == 'subtitlesgr']
        self.list = filter

        return self.list

    def xsubstv(self):
        try:
            url = 'http://www.xsubs.tv/series/all.xml'
            q = re.compile(r"(.*) S(\d+)E(\d+)", re.IGNORECASE).findall(self.query)[0]

            result = getUrl(url).result
            url = re.compile('(<series .+?</series>)').findall(result)
            url = [i for i in url if re.sub('\n|(A|a|The|the)\s|\s(|[(])(UK|US|AU|A|a|The|the)(|[)])$|([[]|[(])\d{4}([]]|[)])|\s(vs|v[.])\s|(:|;|-|"|,|\'|\.|\?)|\s', '', common.parseDOM(i, "series")[0]).lower() == re.sub('\n|(A|a|The|the)\s|\s(|[(])(UK|US|AU|A|a|The|the)(|[)])$|([[]|[(])\d{4}([]]|[)])|\s(vs|v[.])\s|(:|;|-|"|,|\'|\.|\?)|\s', '', q[0]).lower()][0]
            show = common.parseDOM(url, "series")[0]
            srsid = common.parseDOM(url, "series", ret="srsid")[0]
            url = 'http://www.xsubs.tv/series/%s/main.xml' % srsid

            result = getUrl(url).result
            ssnid = common.parseDOM(result, "series_group", ret="ssnid", attrs = { "ssnnum": '%01d' % int(q[1]) })[0]
            url = 'http://www.xsubs.tv/series/%s/%s.xml' % (srsid, ssnid)

            result = getUrl(url).result
            result = re.compile('(.+?)<etitle number="%02d"' % int(q[2])).findall(result)[0]
            result = result.split('</etitle>')[-1]
            subtitles = re.compile('(<sr .+?</sr>)').findall(result)
        except:
            return

        for subtitle in subtitles:
            try:
                p = common.parseDOM(subtitle, "sr", ret="published_on")[0]
                if p == '': raise Exception()

                name = common.parseDOM(subtitle, "sr")[0]
                name = name.rsplit('<hits>', 1)[0]
                name = re.sub('</.+?><.+?>|<.+?>', ' ', name).strip()
                name = '[xsubs.tv] %s S%02dE%02d %s' % (show, int(q[1]), int(q[2]), name)
                name = common.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = common.parseDOM(subtitle, "sr", ret="rlsid")[0]
                url = 'http://www.xsubs.tv/xthru/getsub/%s' % url
                url = common.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'source': 'xsubstv', 'rating': 5})
            except:
                pass

    def subztv(self):
        try:
            q = re.compile(r"(.*) S(\d+)E(\d+)", re.IGNORECASE).findall(self.query)[0]
            query = q[0] + ' Season ' + '%02d' % int(q[1]) + ' Episode ' + '%02d' % int(q[2])

            query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(query))).split())
            url = 'http://subz.blog-spot.gr/?wpdmtask=get_downloads&search=%s' % urllib.quote_plus(query)

            result = getUrl(url).result
            url = common.parseDOM(result, "a", ret="href")
            url = [i for i in url if '-season-%02d-' % int(q[1]) in i and'-episode-%02d-' % int(q[2]) in i][0]

            result = getUrl(url).result
            result = common.parseDOM(result, "table", attrs = { "class": "wpdm-filelist.+?" })[0]
            subtitles = common.parseDOM(result, "tr")
        except:
            return

        for subtitle in subtitles:
            try:
                name = common.parseDOM(subtitle, "td")[0]
                if name == 'English' or name.endswith('.rar'): raise Exception()
                elif name.endswith('.srt'): name = name.rsplit('.srt', 1)[0]
                elif name.endswith('.zip'): name = name.rsplit('.zip', 1)[0]
                name = '[subz.tv] %s' % name
                name = common.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = common.parseDOM(subtitle, "a", ret="href")[0]
                url = common.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'source': 'subztv', 'rating': 5})
            except:
                pass

    def subtitlesgr(self):
        try:
            query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(self.query))).split())
            url = 'http://www.subtitles.gr/search.php?name=%s&sort=downloads+desc' % urllib.quote_plus(query)

            result = getUrl(url).result
            result = result.decode('iso-8859-7').encode('utf-8').replace('\n','')
            subtitles = re.compile('(<img src=.+?flags/el.gif.+?</tr>)').findall(result)
        except:
            return

        for subtitle in subtitles:
            try:
                try: uploader = common.parseDOM(subtitle, "a", attrs = { "class": "link_from" })[0]
                except: uploader = 'other'
                if (uploader == 'Εργαστήρι Υποτίτλων'.decode('iso-8859-7') or uploader == 'subs4series'): raise Exception()
                elif uploader == 'movieplace': uploader = 'GreekSubtitles'
                elif uploader == '': uploader = 'other'

                try: downloads = common.parseDOM(subtitle, "td", attrs = { "class": "latest_downloads" })[0]
                except: downloads = '0'
                downloads =re.sub('[^0-9]', '', downloads)

                name = common.parseDOM(subtitle, "a", attrs = { "onclick": "runme.+?" })[0]
                name = ' '.join(re.sub('<.+?>', '', name).split())
                name = '[%s] %s [%s DLs]' % (uploader, name, downloads)
                name = common.replaceHTMLCodes(name)
                name = name.encode('utf-8')

                url = common.parseDOM(subtitle, "a", ret="href", attrs = { "onclick": "runme.+?" })[0]
                url = url.split('"')[0]
                url = common.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                rating = getRating(downloads).result

                self.list.append({'name': name, 'url': url, 'source': 'subtitlesgr', 'rating': rating})
            except:
                pass

class download:
    def run(self, url, source, name):
        try: shutil.rmtree(tempData)
        except: pass
        try: os.makedirs(tempData)
        except: pass

        if source == 'xsubstv':
            subtitle = self.xsubstv(url)
        elif source == 'subztv':
            subtitle = self.subztv(url)
        elif source == 'subtitlesgr':
            subtitle = self.subtitlesgr(url)

        if not subtitle == None:
            return subtitle

    def xsubstv(self, url):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0')
            response = urllib2.urlopen(request, timeout=10)
            read = response.read()
            response.close()

            subtitle = response.info()["Content-Disposition"]
            subtitle = re.compile('"(.+?)"').findall(subtitle)[0]

            if subtitle.endswith('.srt'):
                subtitle = os.path.join(tempData, subtitle)
                file = open(subtitle, 'wb')
                file.write(read)
                file.close()
                return subtitle
        except:
            try: shutil.rmtree(tempData)
            except: pass

    def subztv(self, url):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0')
            response = urllib2.urlopen(request, timeout=10)
            read = response.read()
            response.close()

            subtitle = response.info()["Content-Disposition"]
            subtitle = re.compile('"(.+?)"').findall(subtitle)[0]

            if subtitle.endswith('.srt'):
                subtitle = os.path.join(tempData, subtitle)
                file = open(subtitle, 'wb')
                file.write(read)
                file.close()
                return subtitle

            elif subtitle.endswith('.zip'):
                zip = zipfile.ZipFile(StringIO.StringIO(read))
                files = zip.namelist()
                srt = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])]
                subtitle = os.path.join(tempData,os.path.basename(srt[0]))
                read = zip.open(srt[0]).read()
                file = open(subtitle, 'wb')
                file.write(read)
                file.close()
                return subtitle
        except:
            try: shutil.rmtree(tempData)
            except: pass

    def subtitlesgr(self, url):
        try:
            url = re.findall('/(\d+)/', url + '/', re.I)[-1]
            url = 'http://www.findsubtitles.eu/getp.php?id=%s' % url
            url = getUrl(url, output='geturl').result

            data = urllib2.urlopen(url, timeout=10).read()
            zip = zipfile.ZipFile(StringIO.StringIO(data))
            files = zip.namelist()
            files = [i for i in files if i.startswith('subs/')]
            srt = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])]
            rar = [i for i in files if any(i.endswith(x) for x in ['.rar', '.zip'])]

            if len(srt) > 0:
                subtitle = os.path.join(tempData,os.path.basename(srt[0]))
                read = zip.open(srt[0]).read()
                file = open(subtitle, 'wb')
                file.write(read)
                file.close()
                return subtitle
            elif len(rar) > 0:
                rarfile = os.path.join(tempData,os.path.basename(rar[0]))
                read = zip.open(rar[0]).read()
                file = open(rarfile, 'wb')
                file.write(read)
                file.close()
                xbmc.executebuiltin('Extract("%s","%s")' % (rarfile, tempData))
                time.sleep(1)
                files = os.listdir(tempData)
                subtitle = [i for i in files if any(i.endswith(x) for x in ['.srt', '.sub'])][0]
                subtitle = os.path.join(tempData,subtitle)
                return subtitle
        except:
            try: shutil.rmtree(tempData)
            except: pass


main()