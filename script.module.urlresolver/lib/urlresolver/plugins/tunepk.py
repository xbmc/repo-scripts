'''
tunepk urlresolver plugin
Copyright (C) 2013 icharania

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import os
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, urllib
from urlresolver import common

logo=os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class TunePkResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "tune.pk"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            link = self.net.http_GET(web_url).content

            if link.find('404 Not Found') >= 0:
                err_title = 'Content not available.'
                err_message = 'The requested video was not found.'
                common.addon.log_error(self.name + ' - fetching %s - %s - %s ' % (web_url,err_title,err_message))
                xbmc.executebuiltin('XBMC.Notification([B][COLOR white]'+__name__+'[/COLOR][/B] - '+err_title+',[COLOR red]'+err_message+'[/COLOR],8000,'+logo+')')
                return self.unresolvable(1, err_message)

            videoUrl = []
            # borrowed from AJ's turtle-x
            html = link.replace('\n\r', '').replace('\r', '').replace('\n', '')
            sources = re.compile("{(.+?)}").findall(re.compile("sources:(.+?)]").findall(html)[0])
            for source in sources:
                video_link = str(re.compile('file[: ]*"(.+?)"').findall(source)[0])
                videoUrl.append(video_link)


            vUrl = ''
            vUrlsCount = len(videoUrl)
            if vUrlsCount > 0:
                q = self.get_setting('quality')
                if q == '0':
                    # Highest Quality
                    vUrl = videoUrl[0]
                elif q == '1':
                    # Medium Quality
                    vUrl = videoUrl[(int)(vUrlsCount / 2)]
                elif q == '2':
                    # Lowest Quality
                    vUrl = videoUrl[vUrlsCount - 1]

                return vUrl

            else:
                return self.unresolvable(0, 'No playable video found.')
        except urllib2.URLError, e:
            return self.unresolvable(3, str(e))
        except Exception, e:
            return self.unresolvable(0, str(e))


    def get_url(self, host, media_id):
        return 'http://embed.tune.pk/play/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/player/embed_player\.php\?vid\=(\w+)', url)
        return r.groups()

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www\.)?tune.pk/player/embed_player\.php\?vid\=(\w+)', url) or \
               self.name in host

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Video Quality" id="%s_quality" ' % self.__class__.__name__
        xml += 'type="enum" values="High|Medium|Low" default="0" />\n'
        return xml
