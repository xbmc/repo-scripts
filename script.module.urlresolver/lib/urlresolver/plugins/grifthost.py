"""
grifthost urlresolver plugin
Copyright (C) 2015 tknorris

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
"""

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import xbmc
from urlresolver import common
from lib import jsunpack
import re

class GrifthostResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "grifthost"
    domains = ["grifthost.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = '//((?:www.)?grifthost\.com)/(?:embed-)?([0-9a-zA-Z/]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        
        data = {}
        for match in re.finditer('input type="hidden" name="([^"]+)" value="([^"]+)', html):
            key, value = match.groups()
            data[key] = value
        data['method_free'] = 'Proceed to Video'
        
        html = self.net.http_POST(web_url, form_data=data).content
        
        stream_url = ''
        for match in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
            js_data = jsunpack.unpack(match.group(1))
            match2 = re.search('<param\s+name="src"\s*value="([^"]+)', js_data)
            if match2:
                stream_url = match2.group(1)
            else:
                match2 = re.search('file\s*:\s*"([^"]+)', js_data)
                if match2:
                    stream_url = match2.group(1)
            
        if stream_url:
            return stream_url + '|User-Agent=%s&Referer=%s' % (common.IE_USER_AGENT, web_url)

        raise UrlResolver.ResolverError('Unable to resolve grifthost link. Filelink not found.')

    def get_url(self, host, media_id):
            return 'http://grifthost.com/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or self.name  in host
