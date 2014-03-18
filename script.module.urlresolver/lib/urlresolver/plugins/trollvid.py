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
import re,xbmc

class FilenukeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "trollvid.net"
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:sv\d*.)?trollvid.net)/embed.php.file=([0-9a-zA-Z]+)' # http://sv3.trollvid.net/embed.php?file=([0-9a-zA-Z]+)&
    
    def get_url(self, host, media_id):
            return 'http://sv3.trollvid.net/embed.php?file=%s&w=800&h=600&bg=' % (media_id)
    
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
        common.addon.log(media_id)
        common.addon.log(web_url)
        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
        except urllib2.URLError, e:
            common.addon.log_error(hostname+': got http error %d fetching 1st url %s' % (e.code, web_url))
            return self.unresolvable(code=3, msg='Exception: %s' % e) #return False
        
        #try:
        #	data = {}; r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html); data['usr_login']=''
        #	for name, value in r: data[name] = value
        #	data['imhuman']='Proceed to video'; data['btn_download']='Proceed to video'
        #	xbmc.sleep(2000)
        #	html = self.net.http_POST(post_url, data).content
        #except urllib2.URLError, e:
        #    common.addon.log_error(hostname+': got http error %d fetching 2nd url %s' % (e.code, web_url))
        #    return self.unresolvable(code=3, msg='Exception: %s' % e) #return False
        
        r = re.search('clip\s*:\s*\n*\s*{\s*\n*\s*\n*\s*\n*\s*url\s*:\s*"(http.+?)"', html)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
            #stream_url = str(r.group(1))
            print stream_url
        else:
            common.addon.log_error(hostname+': stream url not found')
            return self.unresolvable(code=0, msg='no file located') #return False
        return stream_url
