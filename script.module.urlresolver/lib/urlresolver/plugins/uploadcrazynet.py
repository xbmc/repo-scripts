"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib
from urlresolver import common
import re

class UploadCrazyResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "uploadcrazy.net"
    domains = ["uploadcrazy.net"]
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:embeds.)?uploadcrazy.net)/(\D+.php\?file=[0-9a-zA-Z\-_]+)[&]*'
    
    def get_url(self, host, media_id):
            return 'http://embeds.uploadcrazy.net/%s' % (media_id)
            #return 'http://embeds.uploadcrazy.net/embed.php?file=%s' % (media_id)
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
    
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        common.addon.log(web_url)
        resp = self.net.http_GET(web_url)
        html = resp.content
        r = re.search("'file'\s*:\s*'(.+?)'", html)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
        else:
            raise UrlResolver.ResolverError('no file located')
        return stream_url
