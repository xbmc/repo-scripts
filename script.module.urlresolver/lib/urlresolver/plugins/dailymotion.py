'''
dailymotion urlresolver plugin
Copyright (C) 2011 cyrus007

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, urllib
from urlresolver import common

class DailymotionResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "dailymotion"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            link = self.net.http_GET(web_url).content
        except urllib2.URLError, e:
            common.addon.log_error(self.name + '- got http error %d fetching %s' %
                                   (e.code, web_url))
            return False
        sequence = re.compile('"sequence":"(.+?)"').findall(link)
        newseqeunce = urllib.unquote(sequence[0]).decode('utf8').replace('\\/', '/')
        imgSrc = re.compile('og:image" content="(.+?)"').findall(link)
        if(len(imgSrc) == 0):
                imgSrc = re.compile('/jpeg" href="(.+?)"').findall(link)
        dm_low = re.compile('"sdURL":"(.+?)"').findall(newseqeunce)
        dm_high = re.compile('"hqURL":"(.+?)"').findall(newseqeunce)
        videoUrl = ''
        if(len(dm_high) == 0):
                videoUrl = dm_low[0]
        else:
                videoUrl = dm_high[0]
        return videoUrl

    def get_url(self, host, media_id):
        return 'http://www.dailymotion.com/video/%s' % media_id
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/video/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            r = re.search('//(.+?)/swf/([0-9A-Za-z]+)', url)
            if r:
                return r.groups()
            else:
                return False


    def valid_url(self, url, host):
        return re.match('http://(www.)?dailymotion.com/video/[0-9A-Za-z]+', url) or \
               re.match('http://(www.)?dailymotion.com/swf/[0-9A-Za-z]+', url) or self.name in host
