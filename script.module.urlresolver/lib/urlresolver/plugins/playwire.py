'''
playwire urlresolver plugin
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

import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import xml.etree.ElementTree as ET

class PlaywireResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "playwire"
    domains = ["playwire.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        link = self.net.http_GET(web_url).content
        if web_url.endswith('xml'):  # xml source
            root = ET.fromstring(link)
            stream = root.find('src')
            if stream is not None:
                return stream.text
            else:
                accessdenied = root.find('Message')
                if accessdenied is not None:
                    raise UrlResolver.ResolverError('You do not have permission to view this content')

                raise UrlResolver.ResolverError('No playable video found.')
        else:  # json source
            r = re.search('"src":"(.+?)"', link)
            if r:
                return r.group(1)
            else:
                raise UrlResolver.ResolverError('No playable video found.')

    def get_url(self, host, media_id):
        if not 'v2' in host:
            return 'http://%s/embed/%s.xml' % (host, media_id)
        else:
            return 'http://%s/config/%s.json' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search('//(.+?/\d+)/embed/(\d+)\.html', url)
        if not r:
            r = re.search('//(.+?/\d+)/config/(\d+)\.json', url)
        return r.groups()

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www\.)?cdn.playwire.com/\d+/embed/\d+\.html', url) or \
               re.match('http://(www\.)?cdn.playwire.com/v2/\d+/config/\d+\.json', url) or \
               self.name in host

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        return xml
