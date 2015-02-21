'''
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
import urllib2
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from lib import jsunpack

class LetwatchResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "letwatch.us"
    domains = ["letwatch.us"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            html = self.net.http_GET(web_url).content

            if html.find('404 Not Found') >= 0:
                raise Exception('File Removed')

            packed = re.search('(eval\(function.*?)\s*</script>', html, re.DOTALL)
            if packed:
                js = jsunpack.unpack(packed.group(1))
            else:
                js = html

            link = re.search('file\s*:\s*"([^"]+)', js)
            if link:
                common.addon.log_debug('letwatch.us Link Found: %s' % link.group(1))
                return link.group(1)

            raise Exception('Unable to find letwatch.us video')

        except urllib2.URLError, e:
            return self.unresolvable(3, str(e))
        except Exception, e:
            return self.unresolvable(0, str(e))

    def get_url(self, host, media_id):
        return 'http://letwatch.us/embed-%s-640x400.html' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(letwatch.us)/(?:embed-)?(\w+)', url)
        return r.groups()

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://letwatch.us/(?:embed-)?\w+', url) or self.name in host
