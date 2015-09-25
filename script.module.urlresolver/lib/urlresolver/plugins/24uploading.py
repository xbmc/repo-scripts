"""
grifthost urlresolver plugin
Copyright (C) 2015 tknorris

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
from lib import captcha_lib
import re

MAX_TRIES = 3

class TwentyFourUploadingResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "24uploading"
    domains = ["24uploading.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = '//((?:www.)?24uploading\.com)/([0-9a-zA-Z/]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        
        tries = 0
        while tries < MAX_TRIES:
            data = {}
            for match in re.finditer('input type="hidden" name="([^"]+)" value="([^"]+)', html):
                key, value = match.groups()
                data[key] = value
            data['method_free'] = 'Free Download'
            data.update(captcha_lib.do_captcha(html))
            
            html = self.net.http_POST(web_url, form_data=data).content
            match = re.search('class="btn_down.*?href="([^"]+)', html, re.DOTALL)
            if match:
                return match.group(1)
            tries += 1

        raise UrlResolver.ResolverError('Unable to resolve 24uploading link. Filelink not found.')

    def get_url(self, host, media_id):
            return 'http://24uploading.com/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or self.name  in host
