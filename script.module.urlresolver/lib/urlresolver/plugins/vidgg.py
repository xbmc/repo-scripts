"""
vid.gg urlresolver plugin
Copyright (C) 2015 steev

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
from urlresolver import common
import re
import urllib

class VidggResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vid.gg"
    domains = ["www.vid.gg", "vidgg.to"]
    pattern = 'http://((?:www\.)?vid(?:\.gg|gg\.to))/(?:embed/\?id=|video/)([0-9a-z]+)'

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        html = self.net.http_GET(web_url).content
        r = re.search('flashvars\.filekey="(.+?)"', html)
        if r:
            filekey = r.group(1)
        else:
            raise UrlResolver.ResolverError("File Not Found or removed")

        api_call = "http://www.vidgg.to/api/player.api.php?{0}&file={1}&key={2}".format(
            "numOfErrors=0&cid=1&cid2=undefined&pass=undefined&user=undefined",
            media_id,
            urllib.quote_plus(filekey).replace(".", "%2E")
        )

        api_html = self.net.http_GET(api_call).content
        rapi = re.search("url=(.+?)&title=", api_html)
        if rapi:
            return rapi.group(1)
        
        raise UrlResolver.ResolverError("File Not Found or removed")

    def get_url(self, host, media_id):
        return 'http://www.vidgg.to/video/%s' % media_id
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or 'vid.gg' in host
