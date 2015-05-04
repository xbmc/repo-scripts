'''
Allmyvideos urlresolver plugin
Copyright (C) 2013 Vinnydude

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
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class VidSpotResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidspot"
    domains = ["vidspot.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        url = self.get_url(host, media_id)
        html = self.net.http_GET(url).content

        data = {}
        r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
        for name, value in r:
            data[name] = value
            
        html = self.net.http_POST(url, data).content
        
        r = re.search('"sources"\s*:\s*\[(.*?)\]', html, re.DOTALL)
        if r:
            fragment = r.group(1)
            stream_url = None
            for match in re.finditer('"file"\s*:\s*"([^"]+)', fragment):
                stream_url = match.group(1)
            
            if stream_url:
                return stream_url
            else:
                raise UrlResolver.ResolverError('could not find file')
        else:
            raise UrlResolver.ResolverError('could not find sources')
        
    def get_url(self, host, media_id):
        return 'http://vidspot.net/%s' % media_id 

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidspot.net/[0-9A-Za-z]+', url) or re.match('http://(www.)?vidspot.net/embed-[0-9A-Za-z]+[\-]*\d*[x]*\d*.*[html]*', url) or 'vidspot' in host)
