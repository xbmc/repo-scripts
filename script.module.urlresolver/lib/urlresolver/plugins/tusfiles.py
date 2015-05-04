"""
    urlresolver XBMC Addon
    Copyright (C) 2015 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from lib import jsunpack

class TusfilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "tusfiles"
    domains = ['tusfiles.net']

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        direct_url = 'http://%s/%s' % (host, media_id)
        for web_url in [self.get_url(host, media_id), direct_url]:
            html = self.net.http_GET(web_url).content
            for match in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
                js_data = jsunpack.unpack(match.group(1))
                match2 = re.search('<param\s+name="src"\s*value="([^"]+)', js_data)
                if match2:
                    return match2.group(1)

        raise UrlResolver.ResolverError('Unable to locate link')

    def get_url(self, host, media_id):
        return 'http://%s/embed-%s.html' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.search('//(?:www.)?tusfiles.net/(embed-)?[0-9a-z]+', url) or 'tusfiles' in host
