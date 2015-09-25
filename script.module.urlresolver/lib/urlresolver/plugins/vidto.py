"""    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
    
    Special thanks for help with this resolver go out to t0mm0, jas0npc,
    mash2k3, Mikey1234,voinage and of course Eldorado. Cheers guys :)
"""

import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import xbmc
from lib import jsunpack

class VidtoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidto"
    domains = ["vidto.me"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
            'Referer': web_url,
            'User-Agent': common.IE_USER_AGENT
        }

        html = self.net.http_GET(web_url).content
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)"', html)
        if r:
            for name, value in r:
                data[name] = value
            data['referer'] = web_url
        data['imhuman'] = 'Proceed to video'
        xbmc.sleep(6000)  # don't replace with countdown, crashes on linux
        html = self.net.http_POST(web_url, data, headers=headers).content
        match = re.search('(eval\(function.*)\s*</script>', html, re.DOTALL)
        if match:
            packed_data = match.group(1)
            js_data = jsunpack.unpack(packed_data)
            max_label = 0
            stream_url = ''
            for match in re.finditer('label:\s*"(\d+)p"\s*,\s*file:\s*"([^"]+)', js_data):
                label, link = match.groups()
                if int(label) > max_label:
                    stream_url = link
                    max_label = int(label)
            if stream_url:
                return stream_url
            else:
                raise UrlResolver.ResolverError("File Link Not Found")
        else:
            raise UrlResolver.ResolverError("Packed Data Not Found")
        
    def get_url(self, host, media_id):
        return 'http://vidto.me/%s.html' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9A-Za-z]+)',url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidto.me/' +
                        '[0-9A-Za-z]+', url) or 'vidto.me' in host)
