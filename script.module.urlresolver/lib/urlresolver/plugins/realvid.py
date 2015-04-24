"""
realvid urlresolver plugin

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
import re
from urlresolver import common

class RealvidResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "Realvid"
    domains = ["realvid.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?realvid.net)/(?:embed-)?([0-9a-zA-Z]+)(?:-\d+x\d+.html)?'
    
    def get_url(self,host,media_id): 
        return 'http://realvid.net/embed-%s-640x400.html' % (media_id)

    def get_host_and_id(self,url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self,url,host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

    def get_media_url(self,host,media_id):
        web_url = self.get_url(host, media_id)
        link = self.net.http_GET(web_url).content
        if link.find('404 Not Found') >= 0:
            raise UrlResolver.ResolverError('The requested video was not found.')

        video_link = str(re.compile('file[: ]*"(.+?)"').findall(link)[0])
        if len(video_link) > 0:
            return video_link
        else:
            raise UrlResolver.ResolverError('No playable video found.')
