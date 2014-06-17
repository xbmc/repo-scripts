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
import urllib,urllib2
from urlresolver import common
import re

class FilenukeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "auengine.com"
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?auengine.com)/embed.php\?file=([0-9a-zA-Z\-_]+)[&]*'
    
    def get_url(self, host, media_id):
            return 'http://www.auengine.com/embed.php?file=%s' % (media_id) #&w=800&h=600
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
    
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        post_url = web_url
        hostname = self.name
        common.addon.log(web_url)
        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
        except urllib2.URLError, e:
            common.addon.log_error(hostname+': got http error %d fetching %s' % (e.code, web_url))
            return self.unresolvable(code=3, msg='Exception: %s' % e) #return False
        #print html
        r = re.search("url\s*:\s*'(.+?)'\s*\n*\s*,\s*\n*\s*autoPlay", html)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
        else:
            common.addon.log_error(hostname+': stream url not found')
            return self.unresolvable(code=0, msg='no file located') #return False
        return stream_url
	