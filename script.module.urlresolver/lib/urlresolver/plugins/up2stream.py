"""
up2stream urlresolver plugin
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
import re
import urllib2

class NoRedirection(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response

class Up2StreamResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "up2stream"
    domains = ["www.up2stream.com"]
    pattern = '//((?:www\.)?up2stream.com)/view.php\?ref=([0-9]+)'

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
                   'User-Agent': common.IE_USER_AGENT
        }
        opener = urllib2.build_opener(NoRedirection)
        urllib2.install_opener(opener)
        html = self.net.http_GET(web_url, headers=headers).content
        match = re.search('<iframe[^>]*src="([^"]+)', html, re.I)
        if match:
            ad_url = 'http://up2stream.com' + match.group(1)
            _html = self.net.http_GET(ad_url, headers=headers).content
        
        match = re.search('<source[^>]*src="([^"]+)', html, re.I)
        if match:
            return match.group(1) + '|User-Agent=%s&Referer=%s' % (common.IE_USER_AGENT, web_url)
        
        raise UrlResolver.ResolverError("File Not Found or removed")

    def get_url(self, host, media_id):
        return 'http://up2stream.com/view.php?ref=%s' % media_id
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or 'up2stream' in host
