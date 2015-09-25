'''
vidplay urlresolver plugin
Copyright (C) 2013 Lynx187

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

import re
import urllib2
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from lib import captcha_lib

class VidplayResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidplay"
    domains = ["vidplay.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        embed_url = 'http://vidplay.net/vidembed-%s' % (media_id)
        response = urllib2.urlopen(embed_url)
        if response.getcode() == 200 and response.geturl() != embed_url and response.geturl()[-3:].lower() in ['mp4', 'avi', 'mkv']:
            return response.geturl() + '|User-Agent=%s' % (common.IE_USER_AGENT)

        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        if re.search('File Not Found ', html):
            raise UrlResolver.ResolverError('File Not Found or removed')

        data = {}
        r = re.findall(r'type="hidden".*?name="([^"]+)".*?value="([^"]+)', html)
        if r:
            for name, value in r:
                data[name] = value
        else:
            raise UrlResolver.ResolverError('Unable to resolve vidplay Link')

        data.update(captcha_lib.do_captcha(html))

        common.addon.log_debug('VIDPLAY - Requesting POST URL: %s with data: %s' % (web_url, data))
        html = self.net.http_POST(web_url, data).content
        r = re.search('id="downloadbutton".*?href="([^"]+)', html)
        if r:
            stream_url = r.group(1)
        else:
            r = re.search("file\s*:\s*'([^']+)", html)
            if r:
                stream_url = r.group(1)
            else:
                raise UrlResolver.ResolverError('Unable to resolve VidPlay Link')

        if stream_url:
            return stream_url + '|User-Agent=%s' % (common.IE_USER_AGENT)
        else:
            raise UrlResolver.ResolverError('Unable to resolve link')

    def get_url(self, host, media_id):
        return 'http://vidplay.net/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('http://(.+?)/embed-([\w]+)-', url)
        if r:
            return r.groups()
        else:
            r = re.search('//(.+?)/([\w]+)', url)
            if r:
                return r.groups()
            else:
                return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidplay.net/' +
                         '[0-9A-Za-z]+', url) or
                         'vidplay' in host)
