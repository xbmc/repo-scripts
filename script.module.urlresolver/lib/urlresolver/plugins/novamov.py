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

import re, urllib
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from lib import unwise

class NovamovResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "novamov"
    domains = [ "novamov.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        html = unwise.unwise_process(html)
        filekey = unwise.resolve_var(html, "flashvars.filekey")
        
        #get stream url from api
        api = 'http://www.novamov.com/api/player.api.php?key=%s&file=%s' % (filekey, media_id)
        html = self.net.http_GET(api).content
        r = re.search('url=(.+?)&title', html)
        if r:
            stream_url = urllib.unquote(r.group(1))
        else:
            r = re.search('file no longer exists', html)
            if r:
                raise UrlResolver.ResolverError('File Not Found or removed')
            raise UrlResolver.ResolverError('Failed to parse url')
        
        return stream_url

    def get_url(self, host, media_id):
        return 'http://www.novamov.com/video/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//((?:www\.|embed\.)?novamov\.com)\/(?:(?:video/)|(?:embed\.php\?[\w\=\&]*v\=))(\w+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.|embed.)?novamov.com/(video/|embed.php\?)', url) or 'novamov' in host
