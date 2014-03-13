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

import urllib,urllib2,re,os,zipfile,StringIO,shutil,unicodedata,time
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

class getRating(object):
    def __init__(self, downloads):
        try: rating = int(downloads)
        except: rating = 0

        if (rating < 50):
            rating = 1
        elif (rating >= 50 and rating < 100):
            rating = 2
        elif (rating >= 100 and rating < 150):
            rating = 3
        elif (rating >= 150 and rating < 200):
            rating = 4
        elif (rating >= 200 and rating < 250):
            rating = 5
        elif (rating >= 250 and rating < 300):
            rating = 6
        elif (rating >= 300 and rating < 350):
            rating = 7
        elif (rating >= 350 and rating < 400):
            rating = 8
        elif (rating >= 400 and rating < 450):
            rating = 9
        elif (rating >= 450):
            rating = 10

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
        try:        name = urllib.unquote_plus(params["name"])
        except:     name = None
        try:        url = urllib.unquote_plus(params["url"])
        except:     url = None
        try:        query = urllib.unquote_plus(params["searchstring"])
        except:     query = None

        if langs is None:
            pass
        elif not 'Greek' in langs.split(","):
            xbmcgui.Dialog().notification(addonName.encode("utf-8"), language(32002).encode("utf-8"), xbmcgui.NOTIFICATION_WARNING, 3000, sound=False)
            return

        if action == 'search':                    actions().search()
        elif action == 'manualsearch':            actions().search(query)
        elif action == 'download':                actions().download(url, name)

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
                name, url, rating = i['name'], i['url'], i['rating']
                u = '%s?action=download&url=%s&name=%s' % (sys.argv[0], url, name)
                item = xbmcgui.ListItem(label='Greek', label2=name, iconImage=str(rating), thumbnailImage='el')
                item.setProperty("sync",  'false')
                item.setProperty("hearing_imp", 'false')
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)
            except:
                pass

    def download(self, url, name):
        subtitle = subtitles().download(url, name)
        if subtitle == None: return
        item = xbmcgui.ListItem(label=subtitle)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=subtitle,listitem=item,isFolder=False)

class subtitles:
    def __init__(self):
        self.list = []

    def get(self, query):
        try:
            query = ' '.join(urllib.unquote_plus(re.sub('%\w\w', ' ', urllib.quote_plus(query))).split())
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
                if (uploader == 'Εργαστήρι Υποτίτλων' or uploader == 'subs4series'): raise Exception()
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
                url = common.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                rating = getRating(downloads).result

                self.list.append({'name': name, 'url': url, 'rating': rating})
            except:
                pass

        return self.list

    def download(self, url, name):
        try:
            try: shutil.rmtree(tempData)
            except: pass
            try: os.makedirs(tempData)
            except: pass

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