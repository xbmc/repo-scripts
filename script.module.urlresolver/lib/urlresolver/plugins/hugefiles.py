'''
Hugefiles urlresolver plugin
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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
from urlresolver import common
from lib import captcha_lib

class HugefilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "hugefiles"
    domains = ["hugefiles.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        url = self.get_url(host, media_id)
        common.addon.log_debug('HugeFiles - Requesting GET URL: %s' % url)
        html = self.net.http_GET(url).content
        if 'File Not Found' in html:
            raise UrlResolver.ResolverError('File Not Found or removed')

        #Set POST data values
        data = {}
        r = re.findall(r'type="hidden"\s+name="([^"]+)"\s+value="([^"]+)', html)
        if r:
            for name, value in r:
                data[name] = value
        else:
            raise UrlResolver.ResolverError('Cannot find data values')
        
        data['method_free'] = 'Free Download'

        data.update(captcha_lib.do_captcha(html))

        common.addon.log_debug('HugeFiles - Requesting POST URL: %s DATA: %s' % (url, data))
        html = self.net.http_POST(url, data).content
        r = re.search('fileUrl\s*=\s*"([^"]+)', html)
        if r:
            return r.group(1)

        raise UrlResolver.ResolverError('Unable to resolve HugeFiles Link')
        
    def get_url(self, host, media_id):
        return 'http://hugefiles.net/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?hugefiles.net/' +
                         '[0-9A-Za-z]+', url) or
                         'hugefiles' in host)
