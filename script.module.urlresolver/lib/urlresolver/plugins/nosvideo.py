'''
Nosvideo urlresolver plugin
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
from lib import jsunpack

class NosvideoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "nosvideo"
    domains = ["nosvideo.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        url = self.get_url(host, media_id)
        html = self.net.http_GET(url).content
        if 'File Not Found' in html:
            raise UrlResolver.ResolverError('File Not Found')

        headers = {
            'Referer': url
        }

        data = {}
        r = re.findall(r'type="hidden" name="(.+?)"\s* value="(.+?)"', html)
        for name, value in r:
            data[name] = value
        data.update({'method_free': 'Free Download'})

        html = self.net.http_POST(url, data, headers=headers).content

        r = re.search('(eval\(function\(p,a,c,k,e,[dr].*)', html)
        if r:
            js = jsunpack.unpack(r.group(1))
            r = re.search('playlist=(.*)&config=', js)
            if r:
                html = self.net.http_GET(r.group(1)).content
                r = re.search('<file>\s*(.*)\s*</file>', html)
                if r:
                    return r.group(1)
                else:
                    raise UrlResolver.ResolverError('Unable to locate video file')
            else:
                raise UrlResolver.ResolverError('Unable to locate playlist')
        else:
            raise UrlResolver.ResolverError('Unable to locate packed data')

    def get_url(self, host, media_id):
        return 'http://nosvideo.com/?v=%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:\?v\=|embed/)?([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?nosvideo.com/' +
                         '(?:\?v\=|embed/)[0-9A-Za-z]+', url) or
                         'nosvideo' in host)
