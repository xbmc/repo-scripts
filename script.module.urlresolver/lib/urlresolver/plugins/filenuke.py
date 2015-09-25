'''
sharesix urlresolver plugin
Copyright (C) 2014 tknorris

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
import urllib2
from urlresolver import common

class FilenukeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "filenuke"
    domains = ["filenuke.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
                   'User-Agent': common.IE_USER_AGENT
        }

        html = self.net.http_GET(web_url, headers=headers).content
        r = re.search('<a[^>]*id="go-next"[^>*]href="([^"]+)', html)
        if r:
            next_url = 'http://' + host + r.group(1)
            print next_url
            html = self.net.http_GET(next_url, headers=headers).content
        
        if 'file you were looking for could not be found' in html:
            raise UrlResolver.ResolverError('File Not Found or removed')
        
        r = re.search("var\s+lnk\d+\s*=\s*'(.*?)'", html)
        if r:
            stream_url = r.group(1) + '|User-Agent=%s' % (common.IE_USER_AGENT)
            return stream_url
        else:
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
        return re.match('http://((?:www.)?filenuke.com)/(?:f/)?([0-9A-Za-z]+)', url) or 'filenuke' in host
