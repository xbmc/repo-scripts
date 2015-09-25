'''
xfileload urlresolver plugin
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
'''

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
from urlresolver import common
from lib import captcha_lib

class XFileLoadResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "xfileload"
    domains = ["xfileload.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        data = {}
        r = re.findall(r'type="hidden"\s*name="([^"]+)"\s*value="([^"]+)', html)
        for name, value in r:
            data[name] = value
        data.update(captcha_lib.do_captcha(html))

        html = self.net.http_POST(web_url, data).content
            
        if '>File Download Link Generated<' in html:
            # find the href on the same line as the download button image
            r = re.search('href="([^"]+).*?downdown\.png', html)
            if r:
                return  r.group(1) + '|User-Agent=%s' % (common.IE_USER_AGENT)
                        
        raise UrlResolver.ResolverError('Unable to locate link')

    def get_url(self, host, media_id):
        return 'http://%s/%s' % (host, media_id)
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://((?:www.)?xfileload.com)/(?:f/)?([0-9A-Za-z]+)', url) or 'xfileload' in host
