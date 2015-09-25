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

import re, urllib, urllib2, os
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from lib import unwise

class NowvideoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "nowvideo"
    domains = ["nowvideo.eu", "nowvideo.ch", "nowvideo.sx", "nowvideo.co", "nowvideo.li"]
    pattern = '((?:http://|www.|embed.)?nowvideo.(?:eu|sx|ch|co|li))/(?:mobile/video\.php\?id=|video/|embed\.php\?.*?v=)([0-9a-z]+)'

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        match1 = re.search('flashvars\.file[_]*key\s*=\s*([^;]+)', html)
        match2 = re.search('flashvars\.file\s*=\s*"([^"]+)', html)
        
        #get stream url from api
        if match1 and match2:
            match = re.search('var\s+%s\s*=\s*"([^"]+)' % (match1.group(1)), html)
            if match:
                api = 'http://www.nowvideo.sx/api/player.api.php?key=%s&file=%s' % (match.group(1), match2.group(1))
                html = self.net.http_GET(api).content
                r = re.search('url=([^&]+)', html)
                if r:
                    return urllib.unquote(r.group(1))
                else:
                    raise UrlResolver.ResolverError('File Not Found or removed')
                
    def get_url(self, host, media_id):
        return 'http://embed.nowvideo.sx/embed.php?v=%s' % media_id

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.search(self.pattern, url) or 'nowvideo' in host
