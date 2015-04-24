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

import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class VidUpResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidup.org"
    domains = ["vidup.org"]
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        # http://vidup.org/embed.php?file=f50163b6&w=550&h=420&bg=http://www.animestatic.tv/images/animestatic.jpg
        self.pattern = 'http://((?:www.)?vidup.org)/embed.php?.*?file=([0-9a-zA-Z\-_\.]+).*?'
    
    def get_url(self, host, media_id):
            return 'http://vidup.org/embed.php?file=%s' % (media_id)
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
    
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        common.addon.log_debug(web_url)
        resp = self.net.http_GET(web_url)
        html = resp.content
        r = re.search('clip:\s*\n*\s*\{\s*\n*\s*\s*\n*\s*url\s*:\s*"(.+?)",\s*\n*\s*provider:', html)
        if r:
            stream_url = r.group(1)  # stream_url = urllib.unquote_plus(r.group(1))
        else:
            raise UrlResolver.ResolverError('no file located')
        return stream_url
