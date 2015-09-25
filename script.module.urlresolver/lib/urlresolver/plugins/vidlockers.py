"""
vidlockers urlresolver plugin
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

class VidlockersResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidlockers"
    domains = ["vidlockers.ag"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?vidlockers.ag)/([A-Za-z0-9]+)/.*?'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        form_values = {}
        stream_url = ''
        for i in re.finditer('<input type="hidden" name="([^"]+)" value="([^"]+)', html):
            form_values[i.group(1)] = i.group(2)

        xbmc.sleep(2000)
        html = self.net.http_POST(web_url, form_data=form_values).content
        
        r = re.search('file\s*:\s*"([^"]+)', html)
        if r:
            stream_url = r.group(1)
        
        for match in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
            js_data = jsunpack.unpack(match.group(1))
            match2 = re.search('<param\s+name="src"\s*value="([^"]+)', js_data)
            if match2:
                stream_url = match2.group(1)
            else:
                match2 = re.search('<embed.*?type="video.*?src="([^"]+)', js_data)
                if match2:
                    stream_url = match2.group(1)
            
        if stream_url:
            return stream_url + '|User-Agent=%s&Referer=%s' % (common.IE_USER_AGENT, web_url)

        raise UrlResolver.ResolverError('Unable to resolve vidlockers link. Filelink not found.')

    def get_url(self, host, media_id):
            return 'http://vidlockers.ag/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or 'vidlockers' in host
