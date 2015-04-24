'''
jumbofiles urlresolver plugin
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

class JumbofilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "jumbofiles"
    domains = [ "jumbofiles.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        common.addon.log_debug('jumbofiles: in get_media_url %s %s' % (host, media_id))
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content

        if 'file has been removed' in html:
            raise UrlResolver.ResolverError('File has been removed.')

        form_values = {}
        for i in re.finditer('<input type="hidden" name="(.+?)" value="(.+?)">', html):
            form_values[i.group(1)] = i.group(2)

        html = self.net.http_POST(web_url, form_data=form_values).content
        match = re.search('ACTION="(.+?)"', html)
        if match:
            return match.group(1)
        else:
            raise UrlResolver.ResolverError('failed to parse link')

    def get_url(self, host, media_id):
        common.addon.log('jumbofiles: in get_url %s %s' % (host, media_id))
        return 'http://www.jumbofiles.com/%s' % media_id
        
    def get_host_and_id(self, url):
        common.addon.log('jumbofiles: in get_host_and_id %s' % (url))
        r = re.search('//(.+?)/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?jumbofiles.com/' +
                         '[0-9A-Za-z]+', url) or
                         'jumbofiles' in host)
