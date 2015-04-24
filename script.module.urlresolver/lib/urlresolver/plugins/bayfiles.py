'''
Bayfiles urlresolver plugin
Copyright (C) 2013 voinage

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
import re,urllib2,os,json,time,sys
from urlresolver import common
from time import time as wait

class BayfilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "bayfiles"
    domains = [ "bayfiles.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
                                
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        found = re.search(r'var vfid = (\d+);\s*var delay = (\d+);', html)
        vfid, delay = found.groups()
        response = json.loads(self.net.http_POST('http://bayfiles.com/ajax_download', {"_": wait() * 1000, "action": "startTimer", "vfid": vfid}).content)
        common.addon.show_countdown(int(delay), '[B][COLOR orange]BAYFILES[/COLOR][/B]', '')
        html = self.net.http_POST('http://bayfiles.com/ajax_download', {"token": response['token'], "action": "getLink", "vfid": vfid}).content
        final_link = re.search(r"javascript:window.location.href = '([^']+)';", html)
        if final_link:
            return final_link.group(1)
        else:
            raise UrlResolver.ResolverError('Unable to resolve link')
       
    def get_url(self, host, media_id):
        return 'http://%s.com/file/uMXL/%s'%(host,media_id)
        
    def get_host_and_id(self, url):
        r = re.match(r'http://(bayfiles).com/file/uMXL/([a-zA-Z0-9._/]+)',url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match(r'http://(bayfiles).com/file/uMXL/([a-zA-Z0-9._/]+)', url) or 'bayfiles' in host)
