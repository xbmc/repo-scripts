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
    name = "cheesestream.com"
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        # http://cheesestream.com/embed_ext/videoweed/4f4d5748c8f56&width=600&height=438
        #self.pattern = 'http://((?:embed.)?cheesestream.com)/embed[_ext]*/([0-9a-zA-Z/\?=]+)[\&]*'
        self.pattern = 'http://((?:www.)?cheesestream.com)/embed[_ext]*/([0-9a-zA-Z/\?=]+)[\&]*'
        self.pattern2 = 'http://(embed.cheesestream.com)/([0-9a-zA-Z/\?=]+)[\&]*'
        #self.pattern = 'http://((?:www.)?cheesestream.com)/embed/(.+?)'
    
    def get_url(self, host, media_id):
            # http://embed.cheesestream.com/f0O8nd?client_file_id=349851
            if '/' in media_id:
            	return 'http://cheesestream.com/embed_ext/%s' % (media_id)
            elif '?client_file_id=' in media_id:
            	#return 'http://embed.cheesestream.com/%s?client_file_id=%s' % (media_id.split("?client_file_id=")[0],media_id.split("?client_file_id=")[1])
            	return 'http://embed.cheesestream.com/%s' % (media_id)
            else:
            	return 'http://embed.cheesestream.com/%s' % (media_id)
    
    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        if 'embed.cheesestream.com/' in url: self.pattern=self.pattern2
        return re.match(self.pattern, url) or self.name in host
    
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        post_url = web_url
        hostname = self.name
        common.addon.log(media_id)
        common.addon.log(web_url)
        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
        except urllib2.URLError, e:
            common.addon.log_error(hostname+': got http error %d fetching %s' % (e.code, web_url))
            return self.unresolvable(code=3, msg='Exception: %s' % e) #return False
        r = re.search("'file'\s*:\s*'(.+?)'", html)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
        else:
            common.addon.log_error(hostname+': stream url not found')
            return self.unresolvable(code=0, msg='no file located') #return False
        return stream_url
	