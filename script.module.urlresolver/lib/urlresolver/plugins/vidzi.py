'''
vidzi urlresolver plugin
Copyright (C) 2014 Eldorado

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
from lib import jsunpack
from urlresolver import common

class VidziResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidzi"
    domains = ["vidzi.tv"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content

        if '404 Not Found' in html:
            raise UrlResolver.ResolverError('File Not Found or removed')

        r = re.search('file\s*:\s*"([^"]+)', html)
        if r:
            return r.group(1) + '|Referer=http://vidzi.tv/nplayer/jwplayer.flash.swf'
        else:
            for match in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
                js_data = jsunpack.unpack(match.group(1))
                r = re.search('file\s*:\s*"([^"]+)', js_data)
                if r:
                    return r.group(1)
                
        raise UrlResolver.ResolverError('Unable to locate link')

    def get_url(self, host, media_id):
        return 'http://%s/embed-%s.html' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www\.|embed-)?(.+?)/(?:embed-)?([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www\.|embed-)?vidzi.tv/(?:embed-)?[0-9A-Za-z]+', url) or 'vidzi' in host)
