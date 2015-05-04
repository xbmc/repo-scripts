'''
Stagevu urlresolver plugin
Copyright (C) 2011 anilkuj

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

class StagevuResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "stagevu"
    domains = [ "stagevu.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        link = self.net.http_GET(web_url).content
        p = re.compile('<embed type="video/divx" src="(.+?)"')
        match = p.findall(link)
        if match:
            return match[0]
        else:
            raise UrlResolver.ResolverError('File Not Found or removed')

    def get_url(self, host, media_id):
        return 'http://www.stagevu.com/video/%s' % media_id 

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/video/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?stagevu.com/video/' +
                         '[0-9A-Za-z]+', url) or
                         'stagevu' in host)
